from fastapi import FastAPI
from src.posts.router import router as posts_router

app = FastAPI()

app.include_router(posts_router)

# Add more routers if needed

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
