from fastapi import APIRouter, HTTPException
from typing import List
from .service import session_service
from .schemas import SessionResponse

router = APIRouter()


@router.get("/sessions", tags=["sessions"])
async def list_all_sessions(limit: int = 100):
    """
    List all sessions from both Redis (active) and MongoDB (archived).
    
    Args:
        limit: Maximum number of sessions to return (default: 100)
        
    Returns:
        List of sessions with basic information (id, created_at, message_count, last_activity)
    """
    try:
        sessions = await session_service.list_all_sessions(limit=limit)
        
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}", tags=["sessions"])
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

