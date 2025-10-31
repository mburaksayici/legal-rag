import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from src.redis.client import redis_client
from src.mongodb.client import mongodb_client
from src.sessions.models import SessionDocument
from src.sessions.service import session_service
from src.config import SESSION_EXPIRY_MINUTES

logger = logging.getLogger(__name__)

class SessionBackgroundTasks:
    """Background tasks for session management"""
    
    def __init__(self):
        self.redis = redis_client
        self.running = False
    
    async def start_background_tasks(self):
        """Start all background tasks"""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting session background tasks")
        
        # Start session cleanup task
        asyncio.create_task(self.session_cleanup_loop())
    
    async def stop_background_tasks(self):
        """Stop background tasks"""
        self.running = False
        logger.info("Stopping session background tasks")
    
    async def session_cleanup_loop(self):
        """Main loop for session cleanup - runs every minute"""
        while self.running:
            try:
                await self.cleanup_expired_sessions()
                # Sleep for 1 minute before next cleanup
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Error in session cleanup loop: {e}")
                await asyncio.sleep(60)  # Continue after error
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions and migrate to MongoDB"""
        try:
            # Note: Redis TTL automatically handles expiry, but we can implement
            # additional cleanup logic here if needed
            
            # For now, we'll implement a simple check for sessions that are about to expire
            # In a production environment, you might want to use Redis keyspace notifications
            # or implement a more sophisticated tracking mechanism
            
            logger.debug("Session cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
    
    async def migrate_expiring_sessions(self):
        """Migrate sessions that are about to expire to MongoDB"""
        try:
            # This is a placeholder for more advanced session migration logic
            # In practice, you might want to:
            # 1. Track active sessions in a Redis set
            # 2. Check TTL for each session
            # 3. Migrate sessions with low TTL to MongoDB
            
            pass
            
        except Exception as e:
            logger.error(f"Error migrating expiring sessions: {e}")
    
    async def cleanup_old_mongodb_sessions(self, days_old: int = 30):
        """Clean up old sessions from MongoDB (optional maintenance task)"""
        try:
            # Ensure MongoDB is initialized
            if not mongodb_client._initialized:
                await mongodb_client.initialize()
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Delete sessions older than cutoff_date
            result = await SessionDocument.find(
                SessionDocument.archived_at < cutoff_date
            ).delete()
            
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} old sessions from MongoDB")
            
        except Exception as e:
            logger.error(f"Error cleaning up old MongoDB sessions: {e}")

# Global background tasks instance
background_tasks = SessionBackgroundTasks()

# Redis keyspace notification handler (optional advanced feature)
class RedisExpiryHandler:
    """Handle Redis key expiry notifications for session migration"""
    
    def __init__(self):
        self.redis = redis_client
    
    async def setup_keyspace_notifications(self):
        """Setup Redis keyspace notifications for expired keys"""
        try:
            # Enable keyspace notifications for expired events
            await self.redis.client.config_set('notify-keyspace-events', 'Ex')
            logger.info("Redis keyspace notifications enabled")
        except Exception as e:
            logger.error(f"Error setting up keyspace notifications: {e}")
    
    async def handle_session_expiry(self, session_id: str):
        """Handle session expiry event"""
        try:
            # This would be called when a session expires in Redis
            # We can implement session migration logic here
            logger.info(f"Session {session_id} expired, migrating to MongoDB")
            await session_service.migrate_session_to_mongodb(session_id)
        except Exception as e:
            logger.error(f"Error handling session expiry for {session_id}: {e}")

# Global expiry handler instance
expiry_handler = RedisExpiryHandler()
