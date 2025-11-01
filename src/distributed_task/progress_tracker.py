import time
import json
from typing import Optional
from celery import current_task

from src.redis.client import redis_client


class ProgressTracker:
    """Thread-safe helper class to manage task progress in Redis using atomic operations"""
    
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.redis_key = f"ingestion_progress:{job_id}"
        self.processed_key = f"ingestion_processed:{job_id}"
        self.successful_key = f"ingestion_successful:{job_id}"
        self.failed_key = f"ingestion_failed:{job_id}"
    
    def initialize_counters(self, total_documents: int, start_time: float):
        """Initialize atomic counters for a new job (called by master task only)"""
        pipe = redis_client.client.pipeline()
        pipe.set(self.processed_key, 0)
        pipe.set(self.successful_key, 0) 
        pipe.set(self.failed_key, 0)
        pipe.expire(self.processed_key, 3600)
        pipe.expire(self.successful_key, 3600)
        pipe.expire(self.failed_key, 3600)
        pipe.execute()
        
        # Initialize main progress data
        progress_data = {
            "job_id": self.job_id,
            "status": "processing",
            "total_documents": total_documents,
            "processed_documents": 0,
            "successful_documents": 0,
            "failed_documents": 0,
            "documents_left": total_documents,
            "current_file": "Starting parallel processing...",
            "progress_percentage": 0.0,
            "start_time": start_time,
            "updated_at": time.time()
        }
        
        redis_client.client.setex(
            self.redis_key,
            3600,
            json.dumps(progress_data, default=str)
        )
    
    def increment_processed(self, success: bool, current_file: str, estimated_time_remaining: Optional[int] = None):
        """Thread-safe increment of processed documents (called by subtasks)"""
        # Atomic increment operations
        pipe = redis_client.client.pipeline()
        pipe.incr(self.processed_key)
        if success:
            pipe.incr(self.successful_key)
        else:
            pipe.incr(self.failed_key)
        results = pipe.execute()
        
        # Get current counts
        processed = int(results[0])
        successful = int(redis_client.client.get(self.successful_key) or 0)
        failed = int(redis_client.client.get(self.failed_key) or 0)
        
        # Get total from main progress data
        current_progress = self.get_progress(self.job_id)
        if not current_progress:
            return  # Job might have been cleaned up
            
        total_documents = current_progress.get("total_documents", 1)
        start_time = current_progress.get("start_time", time.time())
        
        # Calculate progress
        progress_percentage = round((processed / total_documents) * 100, 2) if total_documents > 0 else 0
        documents_left = max(0, total_documents - processed)
        
        # Update main progress data with atomic counts
        progress_data = {
            "job_id": self.job_id,
            "status": "processing",
            "total_documents": total_documents,
            "processed_documents": processed,
            "successful_documents": successful,
            "failed_documents": failed,
            "documents_left": documents_left,
            "current_file": current_file,
            "estimated_time_remaining_seconds": estimated_time_remaining,
            "progress_percentage": progress_percentage,
            "start_time": start_time,
            "updated_at": time.time()
        }
        
        # Store updated progress
        redis_client.client.setex(
            self.redis_key,
            3600,
            json.dumps(progress_data, default=str)
        )
        
        # Also update Celery task state
        if current_task:
            current_task.update_state(
                state="PROGRESS",
                meta=progress_data
            )
    
    def update_progress(self, 
                       total_documents: int,
                       processed_documents: int,
                       successful_documents: int,
                       failed_documents: int,
                       current_file: Optional[str] = None,
                       estimated_time_remaining: Optional[int] = None,
                       status: str = "processing"):
        """Legacy method for backward compatibility - use increment_processed for thread safety"""
        progress_data = {
            "job_id": self.job_id,
            "status": status,
            "total_documents": total_documents,
            "processed_documents": processed_documents,
            "successful_documents": successful_documents,
            "failed_documents": failed_documents,
            "documents_left": total_documents - processed_documents,
            "current_file": current_file,
            "estimated_time_remaining_seconds": estimated_time_remaining,
            "progress_percentage": round((processed_documents / total_documents) * 100, 2) if total_documents > 0 else 0,
            "updated_at": time.time()
        }
        
        # Store in Redis with 1 hour expiry
        redis_client.client.setex(
            self.redis_key, 
            3600, 
            json.dumps(progress_data, default=str)
        )
        
        # Also update Celery task state
        if current_task:
            current_task.update_state(
                state="PROGRESS",
                meta=progress_data
            )
    
    def set_completed(self, successful_documents: int, failed_documents: int, total_time: float):
        """Mark task as completed and cleanup atomic counters"""
        progress_data = {
            "job_id": self.job_id,
            "status": "completed",
            "total_documents": successful_documents + failed_documents,
            "processed_documents": successful_documents + failed_documents,
            "successful_documents": successful_documents,
            "failed_documents": failed_documents,
            "documents_left": 0,
            "progress_percentage": 100,
            "total_time_seconds": total_time,
            "updated_at": time.time()
        }
        
        redis_client.client.setex(
            self.redis_key, 
            3600, 
            json.dumps(progress_data, default=str)
        )
        
        # Cleanup atomic counters
        self._cleanup_counters()
        
        if current_task:
            current_task.update_state(
                state="SUCCESS",
                meta=progress_data
            )
    
    def set_failed(self, error_message: str):
        """Mark task as failed and cleanup atomic counters"""
        progress_data = {
            "job_id": self.job_id,
            "status": "failed",
            "error_message": error_message,
            "updated_at": time.time()
        }
        
        redis_client.client.setex(
            self.redis_key, 
            3600, 
            json.dumps(progress_data, default=str)
        )
        
        # Cleanup atomic counters
        self._cleanup_counters()
        
        if current_task:
            current_task.update_state(
                state="FAILURE",
                meta=progress_data
            )
    
    def _cleanup_counters(self):
        """Clean up atomic counter keys"""
        pipe = redis_client.client.pipeline()
        pipe.delete(self.processed_key)
        pipe.delete(self.successful_key)
        pipe.delete(self.failed_key)
        pipe.execute()
    
    @classmethod
    def get_progress(cls, job_id: str) -> Optional[dict]:
        """Get progress data from Redis"""
        redis_key = f"ingestion_progress:{job_id}"
        progress_data = redis_client.client.get(redis_key)
        
        if progress_data:
            try:
                return json.loads(progress_data)
            except json.JSONDecodeError:
                return None
        return None
