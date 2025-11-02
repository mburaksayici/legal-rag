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
    
    async def list_all_sessions(self, limit: int = 100):
        """
        List all sessions from both Redis and MongoDB.
        
        Returns list of session summaries with:
        - session_id
        - created_at
        - message_count
        - last_activity
        - source (redis or mongodb)
        """
        try:
            sessions_list = []
            
            # Get sessions from MongoDB
            if not mongodb_client._initialized:
                await mongodb_client.initialize()
            
            # Query MongoDB for archived sessions
            session_docs = await SessionDocument.find_all().sort("-metadata.created_at").limit(limit).to_list()
            
            for doc in session_docs:
                # Get first user message
                first_message = ""
                for msg in doc.messages:
                    if msg.role == MessageRole.USER:
                        first_message = msg.content[:20] if msg.content else ""
                        break
                
                sessions_list.append({
                    "session_id": doc.session_id,
                    "created_at": doc.metadata.created_at.isoformat(),
                    "message_count": doc.metadata.message_count,
                    "last_activity": doc.metadata.last_activity.isoformat(),
                    "first_message": first_message,
                    "source": "mongodb"
                })
            
            # Try to get active sessions from Redis
            # Note: This is a simplified implementation
            # In production, you'd maintain a Redis set of active session IDs
            try:
                # Get all keys matching session pattern
                pattern = "session:*"
                keys = self.redis.client.keys(pattern)
                
                for key in keys[:limit]:
                    # Keys are already decoded as strings (decode_responses=True in Redis client)
                    session_id = key.replace("session:", "")
                    session_data = self.redis.get_session(session_id)
                    
                    if session_data:
                        # Check if already in list from MongoDB
                        if not any(s["session_id"] == session_id for s in sessions_list):
                            metadata = session_data.get("metadata", {})
                            messages = session_data.get("messages", [])
                            
                            # Get first user message
                            first_message = ""
                            for msg in messages:
                                if msg.get("role") == "user":
                                    first_message = msg.get("content", "")[:20]
                                    break
                            
                            sessions_list.append({
                                "session_id": session_id,
                                "created_at": metadata.get("created_at"),
                                "message_count": metadata.get("message_count", 0),
                                "last_activity": metadata.get("last_activity"),
                                "first_message": first_message,
                                "source": "redis"
                            })
            except Exception as redis_error:
                logger.warning(f"Could not fetch Redis sessions: {redis_error}")
            
            # Sort by last_activity descending
            sessions_list.sort(key=lambda x: x.get("last_activity", ""), reverse=True)
            
            return sessions_list[:limit]
            
        except Exception as e:
            logger.error(f"Error listing all sessions: {e}")
            return []
    
    async def cleanup_expired_sessions(self):
        """Background task to cleanup expired sessions"""
        # This would be implemented as a background task
        # For now, Redis TTL handles the expiry automatically
        pass

# Global session service instance
session_service = SessionService()
