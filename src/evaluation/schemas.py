"""Pydantic schemas for evaluation endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime


class StartEvaluationRequest(BaseModel):
    """Request to start a new evaluation."""
    folder_path: str = Field(..., description="Path to folder containing PDFs to evaluate")
    top_k: int = Field(10, description="Number of documents to retrieve")
    use_query_enhancer: bool = Field(False, description="Enable query enhancement with LLM")
    use_reranking: bool = Field(False, description="Enable LLM-based reranking")
    num_questions_per_doc: int = Field(1, description="Number of questions to generate per document")


class StartEvaluationResponse(BaseModel):
    """Response after starting evaluation."""
    evaluation_id: str
    status: str
    message: str


class EvaluationStatusResponse(BaseModel):
    """Response for evaluation status check."""
    evaluation_id: str
    status: str
    folder_path: str
    retrieve_params: Dict[str, Any]
    num_documents_processed: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    results_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class EvaluationListResponse(BaseModel):
    """Response listing all evaluations."""
    evaluations: List[EvaluationStatusResponse]
    total: int


class QuestionOutput(BaseModel):
    """Structured output for question generation."""
    fact: str = Field(..., description="The specific fact or sentence from the document")
    question: str = Field(..., description="A question that targets this specific fact")

