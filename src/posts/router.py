from fastapi import APIRouter, HTTPException
from .schemas import IngestFolderRequest
from src.sessions.schemas import ChatRequest, ChatResponse, SessionResponse
from src.sessions.service import session_service
from src.sessions.models import MessageRole
from datetime import datetime

router = APIRouter()

@router.post("/ingest")
def ingest(request: IngestFolderRequest):
    """Ingest documents from a folder using semantic pipeline (first 5 docs)."""
    from src.data_preprocess_pipelines.data_preprocess import data_preprocess_semantic_pipeline
    data_preprocess_semantic_pipeline.run(request.folder_path)
    return {"status": "success", "folder": request.folder_path, "taken": 5}

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat endpoint for sending messages using chat agent with session management."""
    try:
        # Get or create session
        session = await session_service.get_or_create_session(request.session_id)
        
        # Add user message to session
        session = await session_service.add_message_to_session(
            session.id, 
            request.message, 
            MessageRole.USER, 
            request.metadata
        )
        
        if not session:
            raise HTTPException(status_code=500, detail="Failed to add message to session")
        
        # Generate response using existing ChatCrew
        from src.agents.chat_agent.crew import ChatCrew
        crew = ChatCrew()
        answer = crew.chat(question=request.message, context=None)
        
        # Add assistant response to session
        session = await session_service.add_message_to_session(
            session.id, 
            answer, 
            MessageRole.ASSISTANT
        )
        
        return ChatResponse(
            message=answer,
            session_id=session.id,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session by id - loads from MongoDB to Redis if needed"""
    try:
        session = await session_service.get_session_by_id(session_id)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return SessionResponse.from_session(session)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving session: {str(e)}")
