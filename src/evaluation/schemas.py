"""Pydantic schemas for evaluation endpoints."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
from datetime import datetime


class StartEvaluationRequest(BaseModel):
    """Request to start a new evaluation."""
    folder_path: str = Field(..., description="Path to folder containing PDFs to evaluate")
    top_k: int = Field(10, description="Number of documents to retrieve")
    use_query_enhancer: bool = Field(False, description="Enable query enhancement with LLM")
    use_reranking: bool = Field(False, description="Enable LLM-based reranking")
    num_questions_per_doc: int = Field(1, description="Number of questions to generate per document")
    
    # Optional: Reuse questions from existing evaluation
    source_evaluation_id: Optional[str] = Field(
        None, 
        description="Reuse questions from this evaluation ID (mutually exclusive with question_group_id)"
    )
    question_group_id: Optional[str] = Field(
        None,
        description="Reuse questions from this question group ID (mutually exclusive with source_evaluation_id)"
    )
    
    @field_validator('question_group_id')
    @classmethod
    def validate_question_reuse(cls, v, info):
        """Ensure only one of source_evaluation_id or question_group_id is provided."""
        if v is not None and info.data.get('source_evaluation_id') is not None:
            raise ValueError("Cannot specify both source_evaluation_id and question_group_id")
        return v


class StartEvaluationResponse(BaseModel):
    """Response after starting evaluation."""
    evaluation_id: str
    question_group_id: str
    status: str
    message: str
    reused_questions: bool = False


class EvaluationStatusResponse(BaseModel):
    """Response for evaluation status check."""
    evaluation_id: str
    question_group_id: str
    status: str
    folder_path: str
    retrieve_params: Dict[str, Any]
    num_documents_processed: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    results_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    related_evaluation_ids: List[str] = Field(
        default_factory=list,
        description="List of other evaluation IDs that share the same questions"
    )


class EvaluationListResponse(BaseModel):
    """Response listing all evaluations."""
    evaluations: List[EvaluationStatusResponse]
    total: int


class QuestionOutput(BaseModel):
    """Structured output for question generation."""
    fact: str = Field(..., description="The specific fact or sentence from the document")
    question: str = Field(..., description="A question that targets this specific fact")

