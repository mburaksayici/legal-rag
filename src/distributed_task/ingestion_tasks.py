import os
import time
import traceback
import logging
from typing import List, Dict, Any
from celery import current_task, group, chord
from celery.exceptions import Ignore

from src.distributed_task.celery_app import celery_app
from src.distributed_task.progress_tracker import ProgressTracker
from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline

# Configure logger for ingestion tasks
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@celery_app.task(bind=True)
def process_single_document_task(self, file_path: str, master_job_id: str, pipeline_type: str = "recursive_overlap"):
    """
    Celery subtask to process a single document
    
    Args:
        file_path: Path to the file to process
        master_job_id: ID of the master task for progress tracking
        pipeline_type: Type of pipeline to use ("recursive_overlap" or "semantic")
    """
    task_id = self.request.id
    filename = os.path.basename(file_path)
    logger.info(f"🔷 [Task {task_id}] Starting process_single_document_task for: {filename}")
    logger.info(f"🔷 [Task {task_id}] Master job ID: {master_job_id}")
    logger.info(f"🔷 [Task {task_id}] Full file path: {file_path}")
    logger.info(f"🔷 [Task {task_id}] Pipeline type: {pipeline_type}")
    
    start_time = time.time()
    
    try:
        # Get the appropriate pipeline based on type
        if pipeline_type == "recursive_overlap":
            from src.data_preprocess_pipelines.data_preprocessrecursiveoverlap import data_preprocess_recursive_overlap_pipeline
            pipeline = data_preprocess_recursive_overlap_pipeline
        elif pipeline_type == "semantic":
            from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline
            pipeline = data_preprocess_semantic_pipeline
        else:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")
        
        # Process the single document using the selected pipeline
        logger.info(f"🔷 [Task {task_id}] Calling {pipeline_type} pipeline.run_single_doc()...")
        result = pipeline.run_single_doc(file_path)
        
        processing_time = time.time() - start_time
        logger.info(f"🔷 [Task {task_id}] Processing completed in {processing_time:.2f}s")
        logger.info(f"🔷 [Task {task_id}] Result: success={result['success']}, chars={result.get('character_count', 0)}, chunks={result.get('chunk_count', 0)}, nodes={result.get('node_count', 0)}")
        
        # Thread-safe progress update using atomic counters
        logger.info(f"🔷 [Task {task_id}] Updating progress tracker...")
        progress = ProgressTracker(master_job_id)
        
        # Calculate estimated time remaining
        current_progress = progress.get_progress(master_job_id)
        if current_progress:
            start_time_job = current_progress.get("start_time", time.time())
            elapsed_time = time.time() - start_time_job
            processed = current_progress.get("processed_documents", 0) + 1  # This will be incremented atomically
            total = current_progress.get("total_documents", 1)
            
            if processed > 1:  # Avoid division by zero
                avg_time_per_doc = elapsed_time / processed
                estimated_remaining = int(avg_time_per_doc * (total - processed))
            else:
                estimated_remaining = None
        else:
            estimated_remaining = None
        
        # Atomic increment of progress counters
        progress.increment_processed(
            success=result["success"],
            current_file=filename,
            estimated_time_remaining=estimated_remaining
        )
        
        logger.info(f"✅ [Task {task_id}] Task completed successfully for: {filename}")
        return result
        
    except Exception as e:
        error_message = f"Failed to process {file_path}: {str(e)}"
        logger.error(f"❌ [Task {task_id}] {error_message}")
        logger.error(f"❌ [Task {task_id}] Exception type: {type(e).__name__}")
        logger.error(f"❌ [Task {task_id}] Stack trace:\n{traceback.format_exc()}")
        
        # Still update progress even on failure (atomic increment)
        progress = ProgressTracker(master_job_id)
        progress.increment_processed(
            success=False,
            current_file=filename,
            estimated_time_remaining=None
        )
        
        return {
            "success": False,
            "error": error_message,
            "file_path": file_path,
            "character_count": 0
        }


@celery_app.task(bind=True)
def ingest_documents_task(self, folder_path: str, file_types: List[str] = None, pipeline_type: str = "recursive_overlap"):
    """
    Master Celery task that spawns subtasks for each document (fan-out pattern)
    
    Args:
        folder_path: Path to folder containing documents
        file_types: List of file extensions to process (default: ["pdf"])
        pipeline_type: Type of pipeline to use ("recursive_overlap" or "semantic")
    """
    if file_types is None:
        file_types = ["pdf"]
    
    job_id = self.request.id
    logger.info(f"🔶 [Master {job_id}] Starting ingest_documents_task")
    logger.info(f"🔶 [Master {job_id}] Folder path: {folder_path}")
    logger.info(f"🔶 [Master {job_id}] File types: {file_types}")
    logger.info(f"🔶 [Master {job_id}] Pipeline type: {pipeline_type}")
    
    progress = ProgressTracker(job_id)
    start_time = time.time()
    
    try:
        # Resolve to absolute path if a relative path is provided
        if not os.path.isabs(folder_path):
            logger.info(f"🔶 [Master {job_id}] Converting relative path to absolute...")
            folder_path = os.path.join(os.getcwd(), folder_path)
        folder_path = os.path.normpath(folder_path)
        logger.info(f"🔶 [Master {job_id}] Normalized folder path: {folder_path}")

        # Check if folder exists
        if not os.path.exists(folder_path):
            logger.error(f"❌ [Master {job_id}] Folder not found: {folder_path}")
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        logger.info(f"🔶 [Master {job_id}] Scanning folder for files...")
        
        # Get list of files to process
        all_files = []
        for file_type in file_types:
            files = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if f.lower().endswith(f".{file_type.lower()}")
            ]
            logger.info(f"🔶 [Master {job_id}] Found {len(files)} .{file_type} files")
            all_files.extend(files)
        
        if not all_files:
            logger.warning(f"⚠️ [Master {job_id}] No files found to process")
            progress.set_completed(0, 0, time.time() - start_time)
            return {"message": "No files found to process", "job_id": job_id}
        
        total_files = len(all_files)
        logger.info(f"🔶 [Master {job_id}] Total files to process: {total_files}")
        logger.info(f"🔶 [Master {job_id}] File list: {[os.path.basename(f) for f in all_files]}")
        
        # Initialize thread-safe atomic counters
        logger.info(f"🔶 [Master {job_id}] Initializing progress counters...")
        progress.initialize_counters(total_files, start_time)
        
        # Create subtasks for each document using Celery group (fan-out pattern)
        logger.info(f"🔶 [Master {job_id}] Creating {total_files} subtasks...")
        
        subtask_group = group(
            process_single_document_task.s(file_path, job_id, pipeline_type)
            for file_path in all_files
        )

        logger.info(f"🔶 [Master {job_id}] Scheduling {total_files} subtasks for parallel processing...")

        # Execute all subtasks in parallel (non-blocking)
        group_result = subtask_group.apply_async()
        logger.info(f"🔶 [Master {job_id}] Subtasks scheduled with group ID: {group_result.id}")

        logger.info(f"✅ [Master {job_id}] All subtasks scheduled successfully")
        logger.info(f"💡 [Master {job_id}] Each subtask will write to Qdrant independently")

        return {
            "job_id": job_id,
            "status": "processing",
            "total_files": total_files,
            "group_id": group_result.id
        }
        
    except Exception as e:
        error_message = f"Master task ingestion failed to schedule: {str(e)}"
        logger.error(f"❌ [Master {job_id}] {error_message}")
        logger.error(f"❌ [Master {job_id}] Exception type: {type(e).__name__}")
        logger.error(f"❌ [Master {job_id}] Stack trace:\n{traceback.format_exc()}")
        progress.set_failed(error_message)
        raise Ignore()


@celery_app.task(bind=True)
def ingest_single_file_task(self, file_path: str, file_type: str = None, pipeline_type: str = "recursive_overlap"):
    """
    Celery task to ingest a single file using the new pipeline
    
    Args:
        file_path: Path to the file to ingest
        file_type: File type (pdf, json) - auto-detected if not provided
        pipeline_type: Type of pipeline to use ("recursive_overlap" or "semantic")
    """
    job_id = self.request.id
    filename = os.path.basename(file_path)
    logger.info(f"🔶 [Single {job_id}] Starting ingest_single_file_task")
    logger.info(f"🔶 [Single {job_id}] File: {filename}")
    logger.info(f"🔶 [Single {job_id}] Full path: {file_path}")
    logger.info(f"🔶 [Single {job_id}] File type: {file_type}")
    logger.info(f"🔶 [Single {job_id}] Pipeline type: {pipeline_type}")
    
    progress = ProgressTracker(job_id)
    start_time = time.time()
    
    try:
        # Auto-detect file type if not provided
        if file_type is None:
            logger.info(f"🔶 [Single {job_id}] Auto-detecting file type...")
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension == ".pdf":
                file_type = "pdf"
            elif file_extension == ".json":
                file_type = "json"
            else:
                logger.error(f"❌ [Single {job_id}] Unsupported file extension: {file_extension}")
                raise ValueError(f"Unsupported file extension: {file_extension}")
            logger.info(f"🔶 [Single {job_id}] Detected file type: {file_type}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            logger.error(f"❌ [Single {job_id}] File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"🔶 [Single {job_id}] File exists, proceeding with ingestion...")
        
        # Initialize progress
        logger.info(f"🔶 [Single {job_id}] Initializing progress tracker...")
        progress.update_progress(
            total_documents=1,
            processed_documents=0,
            successful_documents=0,
            failed_documents=0,
            current_file=filename,
            status="processing"
        )
        
        # Get the appropriate pipeline based on type
        if pipeline_type == "recursive_overlap":
            from src.data_preprocess_pipelines.data_preprocessrecursiveoverlap import data_preprocess_recursive_overlap_pipeline
            pipeline = data_preprocess_recursive_overlap_pipeline
        elif pipeline_type == "semantic":
            from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline
            pipeline = data_preprocess_semantic_pipeline
        else:
            raise ValueError(f"Unknown pipeline type: {pipeline_type}")
        
        # Process the single document using the selected pipeline
        logger.info(f"🔶 [Single {job_id}] Calling {pipeline_type} pipeline.run_single_doc()...")
        result = pipeline.run_single_doc(file_path)
        
        successful = 1 if result["success"] else 0
        failed = 0 if result["success"] else 1
        
        logger.info(f"🔶 [Single {job_id}] Processing result: success={result['success']}")
        if result["success"]:
            logger.info(f"🔶 [Single {job_id}] Stats: {result.get('character_count', 0)} chars, {result.get('chunk_count', 0)} chunks, {result.get('node_count', 0)} nodes")
        else:
            logger.error(f"❌ [Single {job_id}] Error: {result.get('error', 'Unknown error')}")
        
        # Mark as completed
        total_time = time.time() - start_time
        logger.info(f"⏱️ [Single {job_id}] Total processing time: {total_time:.2f}s")
        progress.set_completed(successful, failed, total_time)
        
        logger.info(f"✅ [Single {job_id}] Task completed for: {filename}")
        
        return {
            "job_id": job_id,
            "status": "completed",
            "file_path": file_path,
            "successful": result["success"],
            "total_time_seconds": total_time,
            "character_count": result.get("character_count", 0),
            "chunk_count": result.get("chunk_count", 0),
            "node_count": result.get("node_count", 0),
            "error": result.get("error") if not result["success"] else None
        }
        
    except Exception as e:
        error_message = f"Single file ingestion failed: {str(e)}"
        logger.error(f"❌ [Single {job_id}] {error_message}")
        logger.error(f"❌ [Single {job_id}] Exception type: {type(e).__name__}")
        logger.error(f"❌ [Single {job_id}] Stack trace:\n{traceback.format_exc()}")
        progress.set_failed(error_message)
        raise Ignore()
