"""MongoDB models for evaluation system."""
from beanie import Document
from pydantic import Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4
from bson import ObjectId


class QuestionDocument(Document):
    """Stores questions grouped by question_group_id for reuse across evaluations."""
    
    question_group_id: str  # UUID to group related questions
    question: str
    ground_truth_text: str  # The fact/sentence from the PDF
    source_document_path: str  # Ground truth source path
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "questions"
        indexes = ["question_group_id", "created_at"]


class EvaluationDocument(Document):
    """Stores evaluation metadata and configuration."""
    
    evaluation_id: str = Field(default_factory=lambda: str(uuid4()))
    question_group_id: str  # Reference to questions collection
    folder_path: str
    top_k: int
    use_query_enhancer: bool
    use_reranking: bool
    num_questions_per_doc: int = 1
    num_documents_processed: int = 0
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    results_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    class Settings:
        name = "evaluations"
        indexes = ["evaluation_id", "question_group_id", "status", "created_at"]


class EvaluationResultDocument(Document):
    """Stores retrieval results for each question in an evaluation."""
    
    evaluation_id: str
    question_id: str  # Reference to QuestionDocument._id
    retrieved_documents: List[str] = []  # List of retrieved document paths
    hit: bool = False  # Was the source document in the retrieved results?
    rank: Optional[int] = None  # Position of source in retrieved results (1-indexed), None if not found
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "evaluation_results"
        indexes = ["evaluation_id", "question_id", "created_at"]


# Keep old models for backwards compatibility (can be removed after migration)
class QuestionAnswerDocument(Document):
    """DEPRECATED: Use QuestionDocument + EvaluationResultDocument instead."""
    
    evaluation_id: str
    question: str
    ground_truth_text: str
    source_document_path: str
    retrieved_documents: List[str] = []
    hit: bool = False
    rank: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "evaluation_qa_pairs"
        indexes = ["evaluation_id", "created_at"]

