import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from src.config import MONGODB_URL, MONGODB_DATABASE
from src.sessions.models import SessionDocument
from src.evaluation.models import EvaluationDocument, QuestionAnswerDocument
import logging

logger = logging.getLogger(__name__)

class MongoDBClient:
    def __init__(self):
        self._client = None
        self._database = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize MongoDB connection and Beanie ODM"""
        if self._initialized:
            return
        
        try:
            self._client = AsyncIOMotorClient(MONGODB_URL)
            self._database = self._client[MONGODB_DATABASE]
            
            # Initialize Beanie with document models
            await init_beanie(
                database=self._database,
                document_models=[SessionDocument, EvaluationDocument, QuestionAnswerDocument]
            )
            
            self._initialized = True
            logger.info("MongoDB connection initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing MongoDB: {e}")
            raise
    
    @property
    def client(self):
        return self._client
    
    @property
    def database(self):
        return self._database
    
    async def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._initialized = False

# Global MongoDB client instance
mongodb_client = MongoDBClient()

async def get_mongodb():
    """Dependency to get MongoDB client"""
    if not mongodb_client._initialized:
        await mongodb_client.initialize()
    return mongodb_client
