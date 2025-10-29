"""Chat Endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from api.schemas.chat import ChatMessage, ChatResponse
from services.chat_service_with_context import ChatServiceWithContext
from api.dependencies import get_chat_service

router = APIRouter()

@router.post("/message", response_model=ChatResponse)
async def send_message(
    message: ChatMessage,
    chat_service: ChatServiceWithContext = Depends(get_chat_service)
):
    """
    Send a message and receive bot response
    """
    try:
        response = await chat_service.process_message(message)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{session_id}/history")
async def get_chat_history(
    session_id: str,
    chat_service: ChatServiceWithContext = Depends(get_chat_service)
):
    """
    Retrieve conversation history for a session
    """
    history = await chat_service.get_history(session_id)
    if not history:
        raise HTTPException(status_code=404, detail="Session not found")
    return history

