"""MongoDB models for evaluation system."""
from beanie import Document
from pydantic import Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import uuid4


class EvaluationDocument(Document):
    """Stores evaluation metadata and configuration."""
    
    evaluation_id: str = Field(default_factory=lambda: str(uuid4()))
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
        indexes = ["evaluation_id", "status", "created_at"]


class QuestionAnswerDocument(Document):
    """Stores Q&A pairs and retrieval results for evaluation."""
    
    evaluation_id: str
    question: str
    ground_truth_text: str  # The fact/sentence from the PDF
    source_document_path: str  # Ground truth source path
    retrieved_documents: List[str] = []  # List of retrieved document paths
    hit: bool = False  # Was the source document in the retrieved results?
    rank: Optional[int] = None  # Position of source in retrieved results (1-indexed), None if not found
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "evaluation_qa_pairs"
        indexes = ["evaluation_id", "created_at"]

