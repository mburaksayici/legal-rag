from fastapi import APIRouter, HTTPException
from typing import Optional
from .schemas import IngestFolderRequest
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

@router.post("/ingest", tags=["ingestion"])
def ingest(request: IngestFolderRequest):
    """
    Legacy ingest endpoint - now redirects to Celery-based ingestion.
    Use /ingestion/start_job for new async ingestion with progress tracking.
    """
    from src.distributed_task.ingestion_tasks import ingest_documents_task
    
    # Start the Celery task
    task = ingest_documents_task.delay(
        folder_path=request.folder_path,
        file_types=["pdf"]  # Default to PDF for backward compatibility
    )
    
    return {
        "status": "started", 
        "folder": request.folder_path, 
        "job_id": task.id,
        "message": "Ingestion started asynchronously. Use /ingestion/status/{job_id} to check progress."
    }

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
