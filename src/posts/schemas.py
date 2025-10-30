from pydantic import BaseModel
from typing import List, Optional

class IngestRequest(BaseModel):
    data: str  # or whatever structure to ingest

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str]

class SessionResponse(BaseModel):
    id: str
    messages: List[str] = []
