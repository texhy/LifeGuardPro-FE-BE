"""Shared dependencies for API endpoints"""
from services.chat_service_with_context import ChatServiceWithContext
from services.session_service_db import SessionServiceDB

# Singleton instances to share state across endpoints
# Using DATABASE-BACKED session service (Option A)
_session_service = SessionServiceDB()
_chat_service = ChatServiceWithContext(session_service=_session_service)

def get_chat_service() -> ChatServiceWithContext:
    """Get chat service instance (database-backed with context injection)"""
    return _chat_service

def get_session_service() -> SessionServiceDB:
    """Get session service instance (database-backed)"""
    return _session_service
