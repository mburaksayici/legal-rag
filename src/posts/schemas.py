from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

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
