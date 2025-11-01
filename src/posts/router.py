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
        
        # Get embedding from pipeline
        embedding = data_preprocess_semantic_pipeline.embedding
        if embedding is None:
            raise HTTPException(
                status_code=500,
                detail="Embedding model not initialized"
            )
        
        # Check if we need detailed results with scores (only when no LLM features)
        if not request.use_query_enhancer and not request.use_reranking:
            # Use SimpleQdrantRetriever directly for detailed results with scores
            from src.retrieval.simple_qdrant_retriever import SimpleQdrantRetriever
            
            retriever = SimpleQdrantRetriever(embedding=embedding)
            
            if not retriever.is_available():
                raise HTTPException(
                    status_code=503,
                    detail="Vector database is not available or has no data"
                )
            
            # Retrieve documents with detailed information including scores
            detailed_results = retriever.retrieve_detailed(
                query=request.query,
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
        else:
            # Use RetrievalAgent with optional LLM features
            from src.agents.retrieval_agent.agent import RetrievalAgent
            
            retrieval_agent = RetrievalAgent(embedding=embedding)
            
            # Retrieve using RetrievalAgent with optional features
            context_text, sources = retrieval_agent.retrieve(
                question=request.query,
                use_query_enhancer=request.use_query_enhancer,
                use_reranking=request.use_reranking,
                top_k=request.top_k
            )
            
            if not context_text:
                return RetrievalResponse(
                    query=request.query,
                    documents=[],
                    total_retrieved=0
                )
            
            # Parse the context back into individual documents
            document_texts = [doc.strip() for doc in context_text.split('\n\n') if doc.strip()]
            
            # Create documents with sources (no scores available after reranking)
            documents = []
            for i, text in enumerate(document_texts[:request.top_k]):
                doc = RetrievedDocument(
                    text=text,
                    source=sources[i] if i < len(sources) else "unknown",
                    score=None,  # Scores not available with LLM processing
                    metadata={"reranked": request.use_reranking, "enhanced": request.use_query_enhancer}
                )
                documents.append(doc)
        
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
