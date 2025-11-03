import os
from dotenv import load_dotenv

load_dotenv()

# Existing configs
EMBEDDING_WEIGHTS_DIR = os.getenv('EMBEDDING_WEIGHTS_DIR', 'embedding_weights')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# MongoDB configuration
MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'saga_chat')

# Session configuration
SESSION_EXPIRY_MINUTES = int(os.getenv('SESSION_EXPIRY_MINUTES', 2))
SESSION_MIGRATION_INTERVAL_MINUTES = int(os.getenv('SESSION_MIGRATION_INTERVAL_MINUTES', 1))

# Chromadb configuration
CHROMADB_DB_PATH = os.getenv('CHROMADB_DB_PATH', './legal_chromadb')

# Qdrant configuration
QDRANT_HOST = os.getenv('QDRANT_HOST', 'localhost')
QDRANT_PORT = int(os.getenv('QDRANT_PORT', 6333))
QDRANT_COLLECTION_NAME = os.getenv('QDRANT_COLLECTION_NAME', 'legal_documents')