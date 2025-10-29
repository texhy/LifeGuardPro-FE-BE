"""
Session Service - Manages session data
"""
from typing import Dict, Any, Optional
from datetime import datetime

class SessionService:
    def __init__(self):
        # In-memory storage (replace with Redis or PostgreSQL in production)
        self.sessions = {}
    
    async def create_session(
        self,
        session_id: str,
        user_name: str,
        user_email: str,
        user_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create new session"""
        self.sessions[session_id] = {
            "session_id": session_id,
            "user_name": user_name,
            "user_email": user_email,
            "user_phone": user_phone,
            "messages": [],
            "created_at": datetime.now().isoformat()
        }
        return self.sessions[session_id]
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    async def update_session(
        self,
        session_id: str,
        messages: list = None,
        user_name: str = None,
        user_email: str = None,
        user_phone: str = None
    ):
        """Update session data"""
        if session_id in self.sessions:
            if messages is not None:
                self.sessions[session_id]["messages"] = messages
            if user_name:
                self.sessions[session_id]["user_name"] = user_name
            if user_email:
                self.sessions[session_id]["user_email"] = user_email
            if user_phone:
                self.sessions[session_id]["user_phone"] = user_phone
            self.sessions[session_id]["updated_at"] = datetime.now().isoformat()
    
    async def delete_session(self, session_id: str):
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]

