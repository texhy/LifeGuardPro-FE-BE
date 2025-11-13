"""
Session Summary Service - Manages session summaries with embeddings
"""
from typing import Dict, Any, Optional, List
from config.database import get_connection
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

class SummaryService:
    """
    Handles session summaries:
    - Generate summary at session end
    - Create embeddings for summaries
    - Retrieve past summaries for returning users
    """
    
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        self.summarizer = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    async def get_user_past_summaries(
        self,
        user_id: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get past session summaries for a returning user
        
        Args:
            user_id: User UUID
            limit: Number of recent summaries to retrieve
            
        Returns:
            List of past session summaries (most recent first)
        """
        print(f"\n🔍 SUMMARY RETRIEVAL DEBUG:")
        print(f"  → Looking for summaries for user_id: {user_id}")
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        ss.session_id,
                        ss.summary,
                        ss.metadata,
                        ss.created_at,
                        s.started_at,
                        s.ended_at
                    FROM session_summaries ss
                    JOIN sessions s ON s.id = ss.session_id
                    WHERE s.user_id = %s::uuid
                    ORDER BY ss.created_at DESC
                    LIMIT %s
                """, (user_id, limit))
                
                rows = cur.fetchall()
                print(f"  → Found {len(rows)} summary rows in database")
                
                summaries = []
                for row in rows:
                    metadata = row['metadata'] or {}
                    summary_dict = {
                        "session_id": str(row['session_id']),
                        "summary": row['summary'],
                        "topics": metadata.get('topics', []),
                        "courses_mentioned": metadata.get('courses_mentioned', []),
                        "intents": metadata.get('intents', []),
                        "created_at": row['created_at'].isoformat(),
                        "session_duration": metadata.get('duration_seconds', 0)
                    }
                    summaries.append(summary_dict)
                    print(f"    → Summary: {row['summary'][:80]}...")
                
                return summaries
    
    async def create_session_summary(
        self,
        session_id: str,
        messages: List[Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate and store session summary with embedding
        
        Args:
            session_id: Session UUID
            messages: List of conversation messages
            metadata: Additional metadata to store
            
        Returns:
            Summary dict with embedding
        """
        # Check if summary already exists for this session
        existing_summaries = []
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT summary FROM session_summaries WHERE session_id = %s::uuid
                """, (session_id,))
                row = cur.fetchone()
                if row:
                    existing_summaries.append(row['summary'])
        
        # Extract conversation text
        conversation_text = self._format_messages_for_summary(messages)
        
        # Generate summary using LLM (with existing summaries for cumulative context)
        summary = await self._generate_summary(conversation_text, existing_summaries if existing_summaries else None)
        
        # Create embedding
        embedding_vector = await self.embeddings.aembed_query(summary)
        
        # Store in database (upsert)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO session_summaries (session_id, summary, embedding, metadata)
                    VALUES (%s::uuid, %s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE
                    SET summary = EXCLUDED.summary,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata,
                        created_at = NOW()
                    RETURNING session_id, summary, created_at
                """, (
                    session_id,
                    summary,
                    embedding_vector,
                    json.dumps(metadata or {})
                ))
                
                result = cur.fetchone()
                
                return {
                    "session_id": str(result['session_id']),
                    "summary": result['summary'],
                    "created_at": result['created_at'].isoformat()
                }
    
    def _format_messages_for_summary(self, messages: List[Any]) -> str:
        """Format messages for summary generation"""
        formatted = []
        for msg in messages:
            if hasattr(msg, 'type'):
                role = msg.type
                content = msg.content if hasattr(msg, 'content') else str(msg)
            else:
                role = "unknown"
                content = str(msg)
            
            if role == "human":
                formatted.append(f"User: {content}")
            elif role == "ai":
                formatted.append(f"Assistant: {content}")
        
        return "\n".join(formatted)
    
    async def _generate_summary(self, conversation_text: str, existing_summaries: List[str] = None) -> str:
        """
        Generate summary using LLM
        
        Args:
            conversation_text: Current conversation text
            existing_summaries: List of previous summaries to merge (for cumulative context)
        """
        from langchain_core.messages import SystemMessage, HumanMessage
        
        # If there are existing summaries, merge them with the new conversation
        if existing_summaries:
            summary_context = "\n\n".join([f"Previous Summary {i+1}: {s}" for i, s in enumerate(existing_summaries)])
            prompt = f"""Analyze and summarize this customer interaction comprehensively.

**Previous Interaction Summaries:**
{summary_context}

**Current Session:**
{conversation_text}

Create a consolidated summary that:
1. Integrates key information from previous interactions
2. Highlights NEW questions, interests, or behaviors in this session
3. Identifies buyer intent and confidence (HIGH/MEDIUM/LOW based on engagement signals)
4. Notes specific courses/services discussed
5. Flags any follow-up actions needed

Provide a detailed summary in 3-4 sentences:"""
        else:
            # First-time summary
            prompt = f"""Summarize this customer service conversation comprehensively.

Conversation:
{conversation_text}

Include in your summary:
1. All questions asked by the user
2. Courses/services discussed in detail
3. Pricing inquiries and quantity/group size mentioned
4. Buyer intent assessment (HIGH/MEDIUM/LOW) with reasoning based on:
   - Explicit buying signals (e.g., "I want to enroll", "book me", "sign up")
   - Engagement depth (asking detailed pricing, comparing options)
   - Commitment level (specific dates, quantities, payment questions)
5. Any follow-up needed

Provide a detailed summary in 2-3 sentences:"""
        
        response = await self.summarizer.ainvoke([
            SystemMessage(content="You are an expert customer service analyst who creates detailed, actionable summaries."),
            HumanMessage(content=prompt)
        ])
        
        return response.content.strip()
    
    def format_past_summaries_for_context(self, summaries: List[Dict[str, Any]]) -> str:
        """
        Format past summaries into context string for LLM
        
        Args:
            summaries: List of past session summaries
            
        Returns:
            Formatted string for LLM context
        """
        if not summaries:
            return ""
        
        context_parts = ["**Previous Conversation History:**\n"]
        
        for i, summary in enumerate(summaries, 1):
            topics = summary.get('topics', [])
            courses = summary.get('courses_mentioned', [])
            
            context_parts.append(f"{i}. {summary['summary']}")
            if topics:
                context_parts.append(f"   Topics: {', '.join(topics)}")
            if courses:
                context_parts.append(f"   Courses: {', '.join(courses)}")
            context_parts.append("")
        
        return "\n".join(context_parts)

