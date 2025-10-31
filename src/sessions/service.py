import uuid
import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from src.redis.client import redis_client
from src.mongodb.client import mongodb_client
from .models import Session, SessionDocument, Message, MessageRole, SessionMetadata

logger = logging.getLogger(__name__)

class SessionService:
    """Service for managing chat sessions with Redis and MongoDB"""
    
    def __init__(self):
        self.redis = redis_client
    
    async def get_or_create_session(self, session_id: Optional[str] = None) -> Session:
        """Get existing session or create new one"""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Try to get from Redis first
        session = await self.get_session_from_redis(session_id)
        if session:
            # Extend TTL on access
            self.redis.extend_session_ttl(session_id)
            return session
        
        # Try to get from MongoDB
        session = await self.get_session_from_mongodb(session_id)
        if session:
            # Load back to Redis
            await self.save_session_to_redis(session)
            return session
        
        # Create new session
        session = Session(
            id=session_id,
            messages=[],
            metadata=SessionMetadata()
        )
        await self.save_session_to_redis(session)
        return session
    
    async def get_session_from_redis(self, session_id: str) -> Optional[Session]:
        """Get session from Redis"""
        try:
            session_data = self.redis.get_session(session_id)
            if session_data:
                return Session(**session_data)
            return None
        except Exception as e:
            logger.error(f"Error getting session from Redis: {e}")
            return None
    
    async def get_session_from_mongodb(self, session_id: str) -> Optional[Session]:
        """Get session from MongoDB"""
        try:
            # Ensure MongoDB is initialized
            if not mongodb_client._initialized:
                await mongodb_client.initialize()
            
            session_doc = await SessionDocument.find_one(
                SessionDocument.session_id == session_id
            )
            if session_doc:
                return session_doc.to_session()
            return None
        except Exception as e:
            logger.error(f"Error getting session from MongoDB: {e}")
            return None
    
    async def save_session_to_redis(self, session: Session) -> bool:
        """Save session to Redis"""
        try:
            session_data = session.dict()
            return self.redis.set_session(session.id, session_data)
        except Exception as e:
            logger.error(f"Error saving session to Redis: {e}")
            return False
    
    async def save_session_to_mongodb(self, session: Session) -> bool:
        """Save session to MongoDB"""
        try:
            # Ensure MongoDB is initialized
            if not mongodb_client._initialized:
                await mongodb_client.initialize()
            
            # Check if session already exists
            existing_doc = await SessionDocument.find_one(
                SessionDocument.session_id == session.id
            )
            
            if existing_doc:
                # Update existing document
                existing_doc.messages = session.messages
                existing_doc.metadata = session.metadata
                existing_doc.archived_at = datetime.utcnow()
                await existing_doc.save()
            else:
                # Create new document
                session_doc = await SessionDocument.from_session(session)
                await session_doc.insert()
            
            return True
        except Exception as e:
            logger.error(f"Error saving session to MongoDB: {e}")
            return False
    
    async def add_message_to_session(self, session_id: str, content: str, role: MessageRole = MessageRole.USER, metadata: dict = None) -> Optional[Session]:
        """Add a message to session"""
        try:
            session = await self.get_or_create_session(session_id)
            
            message = Message(
                role=role,
                content=content,
                metadata=metadata or {}
            )
            
            session.add_message(message)
            
            # Save back to Redis
            await self.save_session_to_redis(session)
            
            return session
        except Exception as e:
            logger.error(f"Error adding message to session: {e}")
            return None
    
    async def migrate_session_to_mongodb(self, session_id: str) -> bool:
        """Migrate session from Redis to MongoDB (called on expiry)"""
        try:
            session = await self.get_session_from_redis(session_id)
            if session:
                success = await self.save_session_to_mongodb(session)
                if success:
                    # Remove from Redis after successful migration
                    self.redis.delete_session(session_id)
                    logger.info(f"Session {session_id} migrated to MongoDB")
                return success
            return False
        except Exception as e:
            logger.error(f"Error migrating session to MongoDB: {e}")
            return False
    
    async def get_session_by_id(self, session_id: str) -> Optional[Session]:
        """Get session by ID (Redis first, then MongoDB)"""
        return await self.get_or_create_session(session_id)
    
    async def list_active_sessions(self) -> List[str]:
        """List active session IDs in Redis"""
        try:
            # This is a simple implementation - in production you might want to use Redis SCAN
            # For now, we'll return empty list as Redis doesn't have a direct way to list all keys
            # You could implement this with a separate Redis set to track active sessions
            return []
        except Exception as e:
            logger.error(f"Error listing active sessions: {e}")
            return []
    
    async def cleanup_expired_sessions(self):
        """Background task to cleanup expired sessions"""
        # This would be implemented as a background task
        # For now, Redis TTL handles the expiry automatically
        pass

# Global session service instance
session_service = SessionService()
