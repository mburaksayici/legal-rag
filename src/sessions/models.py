from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from beanie import Document
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    """Rich message model with metadata"""
    id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True

class SessionMetadata(BaseModel):
    """Session metadata"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    message_count: int = 0
    user_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

class Session(BaseModel):
    """Session model for API responses and Redis storage"""
    id: str
    messages: List[Message] = Field(default_factory=list)
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)
    
    def add_message(self, message: Message):
        """Add a message to the session"""
        self.messages.append(message)
        self.metadata.message_count += 1
        self.metadata.updated_at = datetime.utcnow()
        self.metadata.last_activity = datetime.utcnow()

class SessionDocument(Document):
    """MongoDB document model using Beanie"""
    session_id: str = Field(index=True, unique=True)
    messages: List[Message] = Field(default_factory=list)
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)
    archived_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "chat_sessions"
        indexes = [
            "session_id",
            "metadata.created_at",
            "archived_at"
        ]
    
    @classmethod
    async def from_session(cls, session: Session) -> "SessionDocument":
        """Create SessionDocument from Session"""
        return cls(
            session_id=session.id,
            messages=session.messages,
            metadata=session.metadata
        )
    
    def to_session(self) -> Session:
        """Convert SessionDocument to Session"""
        return Session(
            id=self.session_id,
            messages=self.messages,
            metadata=self.metadata
        )
