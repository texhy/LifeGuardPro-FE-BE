"""Chat Request/Response Schemas"""
from pydantic import BaseModel, Field
from typing import List, Optional

class ChatMessage(BaseModel):
    session_id: str = Field(..., description="Session ID")
    message: str = Field(..., description="User message")
    user_name: Optional[str] = Field(None, description="User name")
    user_email: Optional[str] = Field(None, description="User email")
    user_phone: Optional[str] = Field(None, description="User phone")

class ChatResponse(BaseModel):
    session_id: str
    response: str
    tool_calls: List[str] = []
    blocked: bool = False
    block_reason: Optional[str] = None
    status: str = "success"

class ChatHistory(BaseModel):
    session_id: str
    messages: List[dict]
    user_name: Optional[str] = None
    user_email: Optional[str] = None

