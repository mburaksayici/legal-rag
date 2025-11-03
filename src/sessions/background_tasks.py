import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from src.redis.client import redis_client
from src.mongodb.client import mongodb_client
from src.sessions.models import SessionDocument, Session
from src.sessions.service import session_service
from src.config import SESSION_EXPIRY_MINUTES, SESSION_MIGRATION_INTERVAL_MINUTES

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
        """Main loop for session cleanup - runs based on SESSION_MIGRATION_INTERVAL_MINUTES"""
        while self.running:
            try:
                await self.cleanup_expired_sessions()
                # Sleep for configured interval before next cleanup
                sleep_seconds = SESSION_MIGRATION_INTERVAL_MINUTES * 60
                logger.info(f"Next session migration in {SESSION_MIGRATION_INTERVAL_MINUTES} minutes")
                await asyncio.sleep(sleep_seconds)
            except Exception as e:
                logger.error(f"Error in session cleanup loop: {e}")
                # Continue after error with same interval
                await asyncio.sleep(SESSION_MIGRATION_INTERVAL_MINUTES * 60)
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions and migrate to MongoDB"""
        try:
            logger.info("Starting periodic session migration to MongoDB")
            
            # Use SCAN to find all session keys in Redis
            pattern = "session:*"
            cursor = 0
            migrated_count = 0
            error_count = 0
            
            # SCAN through all session keys
            while True:
                cursor, keys = self.redis.client.scan(cursor, match=pattern, count=100)
                
                for key in keys:
                    try:
                        # Extract session_id from key (format: "session:session_id")
                        session_id = key.replace("session:", "")
                        
                        # Get session data from Redis
                        session_data = self.redis.get_session(session_id)
                        
                        if session_data:
                            # Convert to Session object
                            session = Session(**session_data)
                            
                            # Migrate to MongoDB (keeps in Redis too)
                            success = await session_service.save_session_to_mongodb(session)
                            
                            if success:
                                migrated_count += 1
                                logger.debug(f"Migrated session {session_id} to MongoDB")
                            else:
                                error_count += 1
                                logger.warning(f"Failed to migrate session {session_id}")
                    
                    except Exception as e:
                        error_count += 1
                        logger.error(f"Error migrating session {key}: {e}")
                
                # Break when cursor returns to 0 (full iteration complete)
                if cursor == 0:
                    break
            
            logger.info(f"Session migration completed: {migrated_count} migrated, {error_count} errors")
            
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
