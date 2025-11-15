from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime


class TaskProgress(BaseModel):
    """Schema for task progress tracking"""
    job_id: str
    status: str  # pending, processing, chunking, indexing, completed, failed
    total_documents: Optional[int] = None
    processed_documents: Optional[int] = None
    successful_documents: Optional[int] = None
    failed_documents: Optional[int] = None
    documents_left: Optional[int] = None
    current_file: Optional[str] = None
    estimated_time_remaining_seconds: Optional[int] = None
    progress_percentage: Optional[float] = None
    error_message: Optional[str] = None
    total_time_seconds: Optional[float] = None
    updated_at: Optional[float] = None


class IngestionJobRequest(BaseModel):
    """Request schema for starting an ingestion job"""
    folder_path: str
    file_types: Optional[List[str]] = ["pdf", "json"]
    pipeline_type: Literal["recursive_overlap", "semantic"] = "recursive_overlap"


class IngestionJobResponse(BaseModel):
    """Response schema for ingestion job creation"""
    job_id: str
    status: str
    message: str


class SingleFileIngestionRequest(BaseModel):
    """Request schema for single file ingestion"""
    file_path: str
    file_type: Optional[str] = None
    pipeline_type: Literal["recursive_overlap", "semantic"] = "recursive_overlap"
