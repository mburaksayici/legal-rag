from fastapi import APIRouter, HTTPException
from typing import Optional
from .schemas import IngestFolderRequest, RetrievalRequest, RetrievalResponse, RetrievedDocument
from src.sessions.schemas import ChatRequest, ChatResponse, SessionResponse
from src.sessions.service import session_service
from src.sessions.models import MessageRole
from src.distributed_task.ingestion_tasks import ingest_documents_task, ingest_single_file_task
from src.distributed_task.progress_tracker import ProgressTracker
from src.distributed_task.schemas import (
    IngestionJobRequest, 
    IngestionJobResponse, 
    SingleFileIngestionRequest,
    TaskProgress
)
from src.evaluation.schemas import (
    StartEvaluationRequest,
    StartEvaluationResponse,
    EvaluationStatusResponse,
    EvaluationListResponse
)
from src.evaluation.service import EvaluationService
from datetime import datetime

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest):
    """Chat endpoint for sending messages using chat agent with session management."""
    try:
        # Get or create session
        session = await session_service.get_or_create_session(request.session_id)
        
        # Add user message to session
        session = await session_service.add_message_to_session(
            session.id, 
            request.message, 
            MessageRole.USER, 
            request.metadata
        )
        
        if not session:
            raise HTTPException(status_code=500, detail="Failed to add message to session")
        
        # Generate response using existing ChatCrew
        from src.agents.chat_agent.crew import ChatCrew
        crew = ChatCrew()
        answer, sources = crew.chat(question=request.message, context=None)
        
        # Add assistant response to session
        session = await session_service.add_message_to_session(
            session.id, 
            answer, 
            MessageRole.ASSISTANT
        )
        
        return ChatResponse(
            message=answer,
            session_id=session.id,
            sources=sources,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.get("/sessions/{session_id}", response_model=SessionResponse, tags=["chat"])
async def get_session(session_id: str):
    """Get session by id - loads from MongoDB to Redis if needed"""
    try:
        session = await session_service.get_session_by_id(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionResponse.from_session(session)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving session: {str(e)}")


# ===== RETRIEVAL ROUTES =====

@router.post("/retrieve", response_model=RetrievalResponse, tags=["retrieval"])
async def retrieve_documents(request: RetrievalRequest):
    """
    Retrieve documents from vector database with optional LLM processing.
    
    Parameters:
    - query: The search query
    - top_k: Number of documents to retrieve (default: 10)
    - use_query_enhancer: Enable query enhancement with LLM (default: False)
    - use_reranking: Enable LLM-based reranking (default: False)
    
    When both are False:
    - Direct vector similarity search only
    - Returns original similarity scores
    
    When enabled:
    - Query enhancement: Generates 3 enhanced query variations
    - Reranking: Uses gpt-4o-mini to rerank by relevance
    - Note: Original similarity scores are replaced by reranking scores
    
    Returns detailed information including document text, sources, scores, and metadata.
    """
    try:
        # Import here to avoid circular dependencies
        from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline
        from src.agents.retrieval_agent.agent import RetrievalAgent
        
        # Get embedding from pipeline
        embedding = data_preprocess_semantic_pipeline.embedding
        if embedding is None:
            raise HTTPException(
                status_code=500,
                detail="Embedding model not initialized"
            )
        
        # Use RetrievalAgent for all cases
        retrieval_agent = RetrievalAgent(embedding=embedding)
        
        if not retrieval_agent.is_available():
            raise HTTPException(
                status_code=503,
                detail="Vector database is not available or has no data"
            )
        
        # Retrieve documents with optional query enhancement and reranking
        detailed_results = retrieval_agent.retrieve(
            question=request.query,
            use_query_enhancer=request.use_query_enhancer,
            use_reranking=request.use_reranking,
            top_k=request.top_k
        )
        
        # Convert to response format
        documents = [
            RetrievedDocument(
                text=doc["text"],
                source=doc["source"],
                score=doc["score"],
                metadata=doc["metadata"]
            )
            for doc in detailed_results
        ]
        
        return RetrievalResponse(
            query=request.query,
            documents=documents,
            total_retrieved=len(documents)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Retrieval error: {str(e)}"
        )


# ===== INGESTION ROUTES =====

@router.post("/ingestion/start_job", response_model=IngestionJobResponse, tags=["ingestion"])
async def start_ingestion_job(request: IngestionJobRequest):
    """
    Start a new document ingestion job for a folder using fan-out pattern.
    Returns a job_id that can be used to track progress.
    """
    try:
        # Start the Celery task
        task = ingest_documents_task.delay(
            folder_path=request.folder_path,
            file_types=request.file_types
        )
        
        return IngestionJobResponse(
            job_id=task.id,
            status="started",
            message=f"Ingestion job started for folder: {request.folder_path}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start ingestion job: {str(e)}"
        )


@router.post("/ingestion/start_single_file", response_model=IngestionJobResponse, tags=["ingestion"])
async def start_single_file_ingestion(request: SingleFileIngestionRequest):
    """
    Start a new document ingestion job for a single file.
    Returns a job_id that can be used to track progress.
    """
    try:
        # Start the Celery task
        task = ingest_single_file_task.delay(
            file_path=request.file_path,
            file_type=request.file_type
        )
        
        return IngestionJobResponse(
            job_id=task.id,
            status="started",
            message=f"Single file ingestion job started for: {request.file_path}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start single file ingestion job: {str(e)}"
        )


@router.get("/ingestion/status/{job_id}", response_model=TaskProgress, tags=["ingestion"])
async def get_ingestion_status(job_id: str):
    """
    Get the current status and progress of an ingestion job.
    
    Args:
        job_id: The job ID returned when starting the ingestion job
        
    Returns:
        Current status including progress information, estimated time remaining,
        success/failure counts, and current file being processed.
    """
    try:
        # Get progress from Redis using ProgressTracker
        progress_data = ProgressTracker.get_progress(job_id)
        
        if progress_data:
            return TaskProgress(**progress_data)
        
        # If no Redis data, try to get from Celery
        from src.distributed_task.celery_app import celery_app
        task_result = celery_app.AsyncResult(job_id)
        
        if task_result.state == "PENDING":
            return TaskProgress(job_id=job_id, status="pending")
        elif task_result.state == "PROGRESS":
            meta = task_result.info or {}
            return TaskProgress(job_id=job_id, **meta)
        elif task_result.state == "SUCCESS":
            meta = task_result.info or {}
            return TaskProgress(
                job_id=job_id,
                status="completed",
                total_documents=meta.get("total_files"),
                processed_documents=meta.get("total_files"),
                successful_documents=meta.get("successful_files"),
                failed_documents=meta.get("failed_files"),
                documents_left=0,
                progress_percentage=100.0,
                total_time_seconds=meta.get("total_time_seconds")
            )
        elif task_result.state == "FAILURE":
            return TaskProgress(
                job_id=job_id,
                status="failed",
                error_message=str(task_result.info) if task_result.info else "Unknown error"
            )
        else:
            return TaskProgress(job_id=job_id, status=task_result.state.lower())
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job status: {str(e)}"
        )


@router.get("/ingestion/jobs", tags=["ingestion"])
async def list_active_ingestion_jobs():
    """
    List all active ingestion jobs (for debugging/monitoring purposes).
    """
    try:
        from src.redis.client import redis_client
        
        # Get all ingestion progress keys from Redis
        pattern = "ingestion_progress:*"
        keys = redis_client.client.keys(pattern)
        
        active_jobs = []
        for key in keys:
            job_id = key.replace("ingestion_progress:", "")
            progress_data = ProgressTracker.get_progress(job_id)
            
            if progress_data:
                active_jobs.append({
                    "job_id": job_id,
                    "status": progress_data.get("status"),
                    "progress_percentage": progress_data.get("progress_percentage"),
                    "updated_at": progress_data.get("updated_at")
                })
        
        return {"active_jobs": active_jobs}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list active jobs: {str(e)}"
        )


@router.post("/ingestion/sync", tags=["ingestion"])
def sync_ingest_single_file(request: SingleFileIngestionRequest):
    """
    Synchronous single file ingestion for debugging purposes.
    Use this endpoint to set breakpoints and debug processing speed.
    
    NOTE: This is a blocking operation - the request will not return until
    processing is complete. Use async endpoints for production workloads.
    """
    import time
    import os

    start_time = time.time()
    filename = os.path.basename(request.file_path)
    
    try:
        # Check if file exists
        if not os.path.exists(request.file_path):
            raise HTTPException(
                status_code=404,
                detail=f"File not found: {request.file_path}"
            )
        
        # Process the document synchronously using the pipeline
        from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline

        result = data_preprocess_semantic_pipeline.run_single_doc(request.file_path)
        
        processing_time = time.time() - start_time
        
        return {
            "status": "completed",
            "file_path": request.file_path,
            "filename": filename,
            "success": result.get("success", False),
            "processing_time_seconds": round(processing_time, 3),
            "character_count": result.get("character_count", 0),
            "chunk_count": result.get("chunk_count", 0),
            "node_count": result.get("node_count", 0),
            "error": result.get("error") if not result.get("success") else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Failed to process file: {str(e)}",
                "file_path": request.file_path,
                "processing_time_seconds": round(processing_time, 3)
            }
        )


# ===== EVALUATION ROUTES =====

@router.post("/evaluation/start", response_model=StartEvaluationResponse, tags=["evaluation"])
async def start_evaluation(request: StartEvaluationRequest):
    """
    Start a new evaluation job to test retrieval system performance.
    
    Parameters:
    - folder_path: Path to folder containing PDFs to evaluate
    - top_k: Number of documents to retrieve (default: 10)
    - use_query_enhancer: Enable query enhancement with LLM (default: False)
    - use_reranking: Enable LLM-based reranking (default: False)
    - num_questions_per_doc: Number of questions to generate per document (default: 1)
    
    Process:
    1. Reads PDFs from the specified folder
    2. Uses GPT-4o-mini to generate targeted questions from each PDF
    3. Runs retrieval with the specified parameters
    4. Stores results in MongoDB for metric calculation
    
    Returns evaluation_id that can be used to check status and results.
    """
    try:
        # Get embedding from pipeline
        from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline
        
        embedding = data_preprocess_semantic_pipeline.embedding
        if embedding is None:
            raise HTTPException(
                status_code=500,
                detail="Embedding model not initialized"
            )
        
        # Create evaluation service
        eval_service = EvaluationService(embedding=embedding)
        
        # Start evaluation
        response = await eval_service.start_evaluation(request)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start evaluation: {str(e)}"
        )


@router.get("/evaluations", response_model=EvaluationListResponse, tags=["evaluation"])
async def list_evaluations(limit: int = 50):
    """
    List all evaluations with their status and results.
    
    Args:
        limit: Maximum number of evaluations to return (default: 50)
        
    Returns:
        List of evaluations sorted by creation date (newest first)
    """
    try:
        # Get embedding from pipeline
        from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline
        
        embedding = data_preprocess_semantic_pipeline.embedding
        if embedding is None:
            raise HTTPException(
                status_code=500,
                detail="Embedding model not initialized"
            )
        
        # Create evaluation service
        eval_service = EvaluationService(embedding=embedding)
        
        # List evaluations
        evaluations = await eval_service.list_evaluations(limit=limit)
        
        return EvaluationListResponse(
            evaluations=evaluations,
            total=len(evaluations)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list evaluations: {str(e)}"
        )


@router.get("/evaluation/{evaluation_id}", response_model=EvaluationStatusResponse, tags=["evaluation"])
async def get_evaluation_status(evaluation_id: str):
    """
    Get the status and results of an evaluation.
    
    Args:
        evaluation_id: The evaluation ID returned when starting the evaluation
        
    Returns:
        Current status including:
        - Status (pending, running, completed, failed)
        - Retrieval parameters used
        - Number of documents processed
        - Results summary (hit_rate, MRR, etc.) if completed
        - Error message if failed
    """
    try:
        # Get embedding from pipeline
        from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline
        
        embedding = data_preprocess_semantic_pipeline.embedding
        if embedding is None:
            raise HTTPException(
                status_code=500,
                detail="Embedding model not initialized"
            )
        
        # Create evaluation service
        eval_service = EvaluationService(embedding=embedding)
        
        # Get evaluation status
        status = await eval_service.get_evaluation_status(evaluation_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation not found: {evaluation_id}"
            )
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get evaluation status: {str(e)}"
        )
