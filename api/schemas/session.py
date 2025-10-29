"""Session Schemas"""
from pydantic import BaseModel, EmailStr
from typing import Optional

class SessionCreate(BaseModel):
    user_name: str
    user_email: EmailStr
    user_phone: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    status: str

