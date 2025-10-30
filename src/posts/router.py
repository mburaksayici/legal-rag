from fastapi import APIRouter
from .schemas import IngestRequest, ChatRequest, SessionResponse

router = APIRouter()

@router.post("/ingest")
async def ingest(request: IngestRequest):
    """Ingest new data"""
    pass  # implement ingestion logic

@router.post("/chat")
async def chat(request: ChatRequest):
    """Chat endpoint for sending messages"""
    pass  # implement chat logic

@router.get("/sessions/{id}", response_model=SessionResponse)
async def get_session(id: str):
    """Get session by id"""
    pass  # implement retrieval logic
