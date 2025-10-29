"""
Session Service - PostgreSQL Database-Backed
Replaces in-memory storage with persistent database storage
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from config.database import get_connection
from services.user_service import UserService
from services.summary_service import SummaryService
from langchain_core.messages import HumanMessage, AIMessage
import json
import uuid

class SessionServiceDB:
    """
    Database-backed session service with:
    - User management (find/create users)
    - Session persistence in PostgreSQL
    - Message tracking
    - Session summary retrieval for returning users
    """
    
    def __init__(self):
        self.user_service = UserService()
        self.summary_service = SummaryService()
    
    async def create_session(
        self,
        session_id: str,
        user_name: str,
        user_email: str,
        user_phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create new session in PostgreSQL
        
        1. Find or create user (check if returning)
        2. Retrieve past session summaries (if returning user)
        3. Create new session record
        4. Return session data with past_context
        """
        # Step 1: Find or create user
        user = await self.user_service.find_or_create_user(
            email=user_email,
            name=user_name,
            phone=user_phone
        )
        
        # Step 2: Get past summaries if returning user
        past_summaries = []
        if user['is_returning']:
            past_summaries = await self.summary_service.get_user_past_summaries(
                user_id=user['id'],
                limit=3  # Last 3 sessions
            )
        
        # Step 3: Create session in database
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Generate UUID for database
                db_session_id = str(uuid.uuid4())
                
                # Create session record
                cur.execute("""
                    INSERT INTO sessions (id, user_id, cookie_sid, state, metadata)
                    VALUES (%s::uuid, %s::uuid, %s, %s, %s)
                    RETURNING id, started_at
                """, (
                    db_session_id,
                    user['id'],
                    session_id,  # cookie_sid = API session ID
                    json.dumps({
                        "user_name": user_name,
                        "user_email": user_email,
                        "user_phone": user_phone,
                        "messages": [],
                        "is_returning": user['is_returning']
                    }),
                    json.dumps({
                        "user_agent": None,
                        "ip_address": None
                    })
                ))
                
                result = cur.fetchone()
                
                return {
                    "session_id": session_id,  # Return cookie_sid for API
                    "db_session_id": str(result['id']),
                    "user_id": user['id'],
                    "user_name": user_name,
                    "user_email": user_email,
                    "user_phone": user_phone,
                    "is_returning": user['is_returning'],
                    "past_summaries": past_summaries,  # ✅ Context for LLM!
                    "messages": [],
                    "created_at": result['started_at'].isoformat()
                }
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session from PostgreSQL by cookie_sid
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        s.id,
                        s.user_id,
                        s.cookie_sid,
                        s.state,
                        s.metadata,
                        s.started_at,
                        s.last_seen_at
                    FROM sessions s
                    WHERE s.cookie_sid = %s AND s.ended_at IS NULL
                """, (session_id,))
                
                row = cur.fetchone()
                if not row:
                    return None
                
                state = row['state'] or {}
                
                # Get messages for this session
                cur.execute("""
                    SELECT role, content, created_at
                    FROM messages
                    WHERE session_id = %s::uuid
                    ORDER BY created_at ASC
                """, (str(row['id']),))
                
                messages_data = cur.fetchall()
                
                # Convert to LangChain message objects
                messages = []
                for msg_row in messages_data:
                    content_data = msg_row['content']
                    if isinstance(content_data, dict):
                        content = content_data.get('content', '')
                    else:
                        content = str(content_data)
                    
                    if msg_row['role'] == 'user':
                        messages.append(HumanMessage(content=content))
                    elif msg_row['role'] == 'assistant':
                        messages.append(AIMessage(content=content))
                
                return {
                    "session_id": session_id,
                    "db_session_id": str(row['id']),
                    "user_id": str(row['user_id']) if row['user_id'] else None,
                    "user_name": state.get("user_name"),
                    "user_email": state.get("user_email"),
                    "user_phone": state.get("user_phone"),
                    "is_returning": state.get("is_returning", False),
                    "messages": messages,
                    "created_at": row['started_at'].isoformat(),
                    "last_seen_at": row['last_seen_at'].isoformat()
                }
    
    async def update_session(
        self,
        session_id: str,
        messages: List = None,
        user_name: str = None,
        user_email: str = None,
        user_phone: str = None
    ):
        """
        Update session state and store messages in PostgreSQL
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Get session
                cur.execute("""
                    SELECT id, state
                    FROM sessions
                    WHERE cookie_sid = %s
                """, (session_id,))
                
                row = cur.fetchone()
                if not row:
                    return
                
                db_session_id = row['id']
                state = row['state'] or {}
                
                # Update state
                if user_name:
                    state['user_name'] = user_name
                if user_email:
                    state['user_email'] = user_email
                if user_phone:
                    state['user_phone'] = user_phone
                
                # Save updated state
                cur.execute("""
                    UPDATE sessions 
                    SET state = %s, last_seen_at = NOW()
                    WHERE id = %s::uuid
                """, (json.dumps(state), str(db_session_id)))
                
                # Store new messages
                if messages:
                    # Get existing message count
                    cur.execute("""
                        SELECT COUNT(*) as count FROM messages WHERE session_id = %s::uuid
                    """, (str(db_session_id),))
                    existing_count = cur.fetchone()['count']
                    
                    # Only store NEW messages (messages added since last update)
                    new_messages = messages[existing_count:]
                    
                    for msg in new_messages:
                        if hasattr(msg, 'type'):
                            role = 'user' if msg.type == 'human' else 'assistant'
                            content = msg.content if hasattr(msg, 'content') else str(msg)
                        else:
                            role = 'assistant'
                            content = str(msg)
                        
                        cur.execute("""
                            INSERT INTO messages (session_id, role, content)
                            VALUES (%s::uuid, %s, %s)
                        """, (
                            str(db_session_id),
                            role,
                            json.dumps({"content": content})
                        ))
    
    async def end_session(self, session_id: str):
        """
        End session and generate summary
        
        1. Mark session as ended
        2. Generate session summary
        3. Create embedding for summary
        4. Store in session_summaries table
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Get session and messages
                cur.execute("""
                    SELECT id, user_id, started_at
                    FROM sessions
                    WHERE cookie_sid = %s AND ended_at IS NULL
                """, (session_id,))
                
                session = cur.fetchone()
                if not session:
                    return
                
                db_session_id = str(session['id'])
                
                # Get all messages
                cur.execute("""
                    SELECT role, content
                    FROM messages
                    WHERE session_id = %s::uuid
                    ORDER BY created_at ASC
                """, (db_session_id,))
                
                messages = cur.fetchall()
                
                # Convert to message objects for summary
                message_objects = []
                for msg in messages:
                    content_data = msg['content']
                    content = content_data.get('content', '') if isinstance(content_data, dict) else str(content_data)
                    
                    if msg['role'] == 'user':
                        message_objects.append(HumanMessage(content=content))
                    else:
                        message_objects.append(AIMessage(content=content))
                
                # Extract metadata for summary
                topics = []
                courses_mentioned = []
                # You can enhance this with more sophisticated extraction
                
                duration = (datetime.now(timezone.utc) - session['started_at']).total_seconds()
                
                metadata = {
                    "message_count": len(messages),
                    "duration_seconds": int(duration),
                    "topics": topics,
                    "courses_mentioned": courses_mentioned
                }
                
                # Generate and store summary
                if message_objects:
                    await self.summary_service.create_session_summary(
                        session_id=db_session_id,
                        messages=message_objects,
                        metadata=metadata
                    )
                
                # Mark session as ended
                cur.execute("""
                    UPDATE sessions 
                    SET ended_at = NOW()
                    WHERE id = %s::uuid
                """, (db_session_id,))
    
    async def delete_session(self, session_id: str):
        """Delete/end session"""
        await self.end_session(session_id)

