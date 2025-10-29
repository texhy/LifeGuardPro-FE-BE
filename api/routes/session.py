"""Session Management Endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from api.schemas.session import SessionCreate, SessionResponse
from services.session_service_db import SessionServiceDB
from api.dependencies import get_session_service
from uuid import uuid4

router = APIRouter()

@router.post("/create", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    session_service: SessionServiceDB = Depends(get_session_service)
):
    """
    Create new chat session in database
    
    - Checks if user is returning (by email)
    - Retrieves past session summaries if returning
    - Creates session record in PostgreSQL
    """
    session_id = str(uuid4())
    session = await session_service.create_session(
        session_id=session_id,
        user_name=session_data.user_name,
        user_email=session_data.user_email,
        user_phone=session_data.user_phone
    )
    
    # Return session info with returning user flag
    status_msg = "returning_user" if session.get("is_returning") else "created"
    
    return SessionResponse(
        session_id=session_id,
        status=status_msg
    )

@router.get("/{session_id}")
async def get_session(
    session_id: str,
    session_service: SessionServiceDB = Depends(get_session_service)
):
    """Get session details from database"""
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    session_service: SessionServiceDB = Depends(get_session_service)
):
    """
    End session and generate summary
    
    - Marks session as ended in database
    - Generates conversation summary using LLM
    - Creates embedding for summary
    - Stores in session_summaries table (for future context)
    """
    await session_service.end_session(session_id)
    return {"status": "ended", "summary": "generated"}

@router.delete("/{session_id}")
async def delete_session(
    session_id: str,
    session_service: SessionServiceDB = Depends(get_session_service)
):
    """
    Delete/end session (same as end)
    Generates summary before ending
    """
    await session_service.delete_session(session_id)
    return {"status": "deleted"}

