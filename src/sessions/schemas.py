from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from .models import Message, MessageRole, SessionMetadata

class ChatRequest(BaseModel):
    """Chat request schema"""
    message: str
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    """Chat response schema"""
    message: str
    session_id: str
    sources: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SessionResponse(BaseModel):
    """Session response schema"""
    id: str
    messages: List[Message]
    metadata: SessionMetadata
    message_count: int
    
    @classmethod
    def from_session(cls, session):
        return cls(
            id=session.id,
            messages=session.messages,
            metadata=session.metadata,
            message_count=len(session.messages)
        )

class CreateMessageRequest(BaseModel):
    """Request to create a new message"""
    content: str
    role: MessageRole = MessageRole.USER
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SessionListResponse(BaseModel):
    """Response for listing sessions"""
    sessions: List[SessionResponse]
    total: int
    page: int
    page_size: int
