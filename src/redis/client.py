import redis
import json
import logging
from typing import Optional, Dict, Any
from src.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SESSION_EXPIRY_MINUTES

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self._client = None
    
    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True
            )
        return self._client
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from Redis"""
        try:
            data = self.client.get(f"session:{session_id}")
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            return None
    
    def set_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Set session data in Redis with TTL"""
        try:
            ttl_seconds = SESSION_EXPIRY_MINUTES * 60
            self.client.setex(
                f"session:{session_id}",
                ttl_seconds,
                json.dumps(session_data, default=str)
            )
            return True
        except Exception as e:
            logger.error(f"Error setting session {session_id}: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session from Redis"""
        try:
            self.client.delete(f"session:{session_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def get_session_ttl(self, session_id: str) -> int:
        """Get remaining TTL for session in seconds"""
        try:
            return self.client.ttl(f"session:{session_id}")
        except Exception as e:
            logger.error(f"Error getting TTL for session {session_id}: {e}")
            return -1
    
    def extend_session_ttl(self, session_id: str) -> bool:
        """Extend session TTL to full expiry time"""
        try:
            ttl_seconds = SESSION_EXPIRY_MINUTES * 60
            self.client.expire(f"session:{session_id}", ttl_seconds)
            return True
        except Exception as e:
            logger.error(f"Error extending TTL for session {session_id}: {e}")
            return False

# Global Redis client instance
redis_client = RedisClient()
