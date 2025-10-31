from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.posts.router import router as posts_router
from src.mongodb.client import mongodb_client
from src.sessions.background_tasks import background_tasks

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await mongodb_client.initialize()
    await background_tasks.start_background_tasks()
    
    yield
    
    # Shutdown
    await background_tasks.stop_background_tasks()
    await mongodb_client.close()

app = FastAPI(lifespan=lifespan)

app.include_router(posts_router)

# Add more routers if needed

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
