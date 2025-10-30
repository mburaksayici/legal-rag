from fastapi import APIRouter
from .schemas import IngestRequest, ChatRequest, SessionResponse, IngestFolderRequest

router = APIRouter()

@router.post("/ingest")
def ingest(request: IngestFolderRequest):
    """Ingest documents from a folder using semantic pipeline (first 5 docs)."""
    from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline
    data_preprocess_semantic_pipeline.run(request.folder_path)
    return {"status": "success", "folder": request.folder_path, "taken": 5}

@router.post("/chat")
def chat(request: ChatRequest):
    """Chat endpoint for sending messages using chat agent."""
    from src.agents.chat_agent.crew import ChatCrew
    crew = ChatCrew()
    answer = crew.chat(question=request.message, context=None)
    return {"message": answer, "session_id": request.session_id}

@router.get("/sessions/{id}", response_model=SessionResponse)
async def get_session(id: str):
    """Get session by id"""
    pass  # implement retrieval logic
