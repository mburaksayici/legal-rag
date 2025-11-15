from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from src.data_preprocess_pipelines.base import DataPreprocessBase
# Import session schemas
from src.sessions.schemas import ChatRequest, ChatResponse, SessionResponse

class IngestRequest(BaseModel):
    data: str  # or whatever structure to ingest

class IngestFolderRequest(BaseModel):
    folder_path: str = "assets/sample_pdfs"

# Legacy schemas for backward compatibility
class LegacyChatRequest(BaseModel):
    message: str
    session_id: Optional[str]

class LegacySessionResponse(BaseModel):
    id: str
    messages: List[str] = []

# Retrieval schemas
class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 10
    use_query_enhancer: bool = False
    use_reranking: bool = False
    pipeline_type: Literal["recursive_overlap", "semantic"] = "recursive_overlap"

class RetrievedDocument(BaseModel):
    text: str
    source: str
    score: Optional[float] = None
    metadata: Dict[str, Any] = {}

class RetrievalResponse(BaseModel):
    query: str
    documents: List[RetrievedDocument]
    total_retrieved: int
