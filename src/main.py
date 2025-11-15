from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.posts.router import router as posts_router
from src.sessions.router import router as sessions_router
from src.mongodb.client import mongodb_client
from src.sessions.background_tasks import background_tasks
from src.vectordb.qdrant_db.manager import QdrantManager
from src.vectordb.qdrant_db.config import qdrant_host, qdrant_port, collection_name

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await mongodb_client.initialize()
    
    # Initialize Qdrant collection at startup
    try:
        qdrant_manager = QdrantManager(
            host=qdrant_host,
            port=qdrant_port,
            collection_name=collection_name
        )
        # Store in app state for potential future use
        app.state.qdrant_manager = qdrant_manager
        print(f"✓ Qdrant collection '{collection_name}' initialized")
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize Qdrant collection: {e}")
    
    await background_tasks.start_background_tasks()
    
    yield
    
    # Shutdown
    await background_tasks.stop_background_tasks()
    await mongodb_client.close()

app = FastAPI(lifespan=lifespan)

app.include_router(posts_router)
app.include_router(sessions_router)

# All routes are now organized in src/posts/router.py and src/sessions/router.py

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
