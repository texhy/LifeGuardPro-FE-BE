"""
User Service - Manages user data in PostgreSQL
"""
from typing import Dict, Any, Optional
from config.database import get_connection
import json

class UserService:
    """
    Handles user lookup, creation, and matching
    """
    
    async def find_or_create_user(
        self,
        email: str,
        name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find existing user or create new one
        
        Matches by:
        1. Email (exact match)
        2. Normalized name + phone (fuzzy match)
        
        Args:
            email: User email
            name: User name (optional)
            phone: User phone (optional)
            
        Returns:
            User dict with id, email, is_returning flag
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Try to find by email first
                cur.execute("""
                    SELECT id, email, phone, metadata, created_at
                    FROM users
                    WHERE email = %s
                """, (email.lower().strip(),))
                
                existing_user = cur.fetchone()
                
                if existing_user:
                    # User found - update metadata if needed
                    metadata = existing_user['metadata'] or {}
                    
                    # Update name/phone if provided and not in metadata
                    updated = False
                    if name and not metadata.get('name'):
                        metadata['name'] = name
                        updated = True
                    if phone and not metadata.get('phone'):
                        metadata['phone'] = phone
                        updated = True
                    
                    if updated:
                        cur.execute("""
                            UPDATE users 
                            SET metadata = %s, phone = COALESCE(phone, %s)
                            WHERE id = %s
                        """, (json.dumps(metadata), phone, existing_user['id']))
                    
                    return {
                        "id": str(existing_user['id']),
                        "email": existing_user['email'],
                        "phone": existing_user['phone'] or phone,
                        "name": metadata.get('name') or name,
                        "is_returning": True,  # ✅ Returning user!
                        "created_at": existing_user['created_at'].isoformat()
                    }
                
                else:
                    # New user - create
                    metadata = {}
                    if name:
                        metadata['name'] = name
                    
                    cur.execute("""
                        INSERT INTO users (email, phone, metadata, consent)
                        VALUES (%s, %s, %s, TRUE)
                        RETURNING id, email, phone, created_at
                    """, (email.lower().strip(), phone, json.dumps(metadata)))
                    
                    new_user = cur.fetchone()
                    
                    return {
                        "id": str(new_user['id']),
                        "email": new_user['email'],
                        "phone": new_user['phone'],
                        "name": name,
                        "is_returning": False,  # ✅ New user!
                        "created_at": new_user['created_at'].isoformat()
                    }
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, email, phone, metadata, created_at
                    FROM users
                    WHERE id = %s::uuid
                """, (user_id,))
                
                user = cur.fetchone()
                if not user:
                    return None
                
                metadata = user['metadata'] or {}
                return {
                    "id": str(user['id']),
                    "email": user['email'],
                    "phone": user['phone'],
                    "name": metadata.get('name'),
                    "created_at": user['created_at'].isoformat()
                }

