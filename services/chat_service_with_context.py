"""
Chat Service - Enhanced with Session Summary Context
Orchestrates chat logic and injects past conversation context for returning users
"""
from typing import Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage

from core.graph import app as langgraph_app
from api.schemas.chat import ChatMessage, ChatResponse
from services.session_service_db import SessionServiceDB
from services.summary_service import SummaryService

class ChatServiceWithContext:
    def __init__(self, session_service=None):
        self.session_service = session_service or SessionServiceDB()
        self.summary_service = SummaryService()
    
    async def process_message(self, message: ChatMessage) -> ChatResponse:
        """
        Process user message through LangGraph with context injection
        
        For returning users, injects past session summaries into context
        """
        # Get session
        session_data = await self.session_service.get_session(message.session_id)
        if not session_data:
            raise ValueError(f"Session {message.session_id} not found")
        
        # Check if returning user and get past summaries
        past_context = ""
        print(f"\n🔍 CONTEXT INJECTION DEBUG:")
        print(f"  → is_returning: {session_data.get('is_returning')}")
        print(f"  → user_id: {session_data.get('user_id')}")
        
        if session_data.get("is_returning") and session_data.get("user_id"):
            past_summaries = await self.summary_service.get_user_past_summaries(
                user_id=session_data["user_id"],
                limit=3
            )
            
            print(f"  → Found {len(past_summaries)} past summaries")
            if past_summaries:
                for i, summary in enumerate(past_summaries, 1):
                    print(f"    Summary {i}: {summary.get('summary', '')[:100]}...")
            
            if past_summaries:
                past_context = self.summary_service.format_past_summaries_for_context(past_summaries)
                print(f"  → Formatted context length: {len(past_context)} chars")
        
        # Build messages list with context injection
        messages_list = session_data["messages"].copy()
        
        print(f"  → Current messages in session: {len(messages_list)}")
        print(f"  → Message types: {[msg.type if hasattr(msg, 'type') else 'unknown' for msg in messages_list]}")
        
        # If returning user with past context, inject it before the first user message
        # Check if context was already injected by looking for a SystemMessage
        # (SystemMessage type is "system" in LangChain)
        has_context = any(
            hasattr(msg, 'type') and msg.type == "system" 
            for msg in messages_list
        )
        
        print(f"  → Has context already: {has_context}")
        print(f"  → Past context exists: {bool(past_context)}")
        
        if past_context and not has_context:
            # Add system message with past context
            context_message = SystemMessage(content=f"""CONTEXT: This user has chatted before. Here's their conversation history:

{past_context}

Use this context to provide personalized service. Reference past discussions when relevant, but don't be overly familiar.
""")
            messages_list.append(context_message)
            print(f"  ✅ Context SystemMessage injected!")
        else:
            if not past_context:
                print(f"  ⚠️  No past context to inject")
            if has_context:
                print(f"  ℹ️  Context already exists in messages")
        
        # Add current user message
        messages_list.append(HumanMessage(content=message.message))
        
        # Build state
        state = {
            "messages": messages_list,
            "user_name": message.user_name or session_data.get("user_name"),
            "user_email": message.user_email or session_data.get("user_email"),
            "user_phone": message.user_phone or session_data.get("user_phone"),
            "blocked": False,
            "block_reason": None,
            "info_requested": True,
            "info_request_count": 1,
            "needs_info": False,
            "info_skipped": False,
            "skip_reason": None,
            "intents": [],
            "intent_confidence": {},
            "query_type": "specific_question",
            "user_context": {},
            "comparison_items": [],
            "process_domain": None,
            "pricing_slots": {},
            "rag_slots": {},
            "quote_slots": {},
            "booking_slots": {},
            "planned_calls": [],
            "next_action": "NONE",
            "slot_question": None,
            "notes": [],
            "planner_errors": [],
            "tool_results": {},
            "execution_errors": [],
            "expanded_queries": [],
            "expansion_confidence": 0.0,
            "coverage_score": 0.0,
            "retrieved_chunks": [],
            "retrieval_method": "",
            "retrieval_confidence": 0.0,
            "bm25_candidates": 0,
            "vector_candidates": 0,
            "rrf_fused_count": 0,
            "mmr_final_count": 0,
            "verified_claims": [],
            "coVe_confidence": 0.0,
            "supported_claims_count": 0,
            "unresolved_claims_count": 0,
            "contradicted_claims_count": 0,
            "final_response": None,
            "agent_error": None,
            "turn_count": 0,
            "last_updated": ""
        }
        
        # Execute graph
        result = await langgraph_app.ainvoke(
            state,
            config={"configurable": {"thread_id": message.session_id}}
        )
        
        # Save updated session (messages)
        messages_to_save = result.get("messages", [])
        print(f"🔍 DEBUG: Saving {len(messages_to_save)} messages to DB")
        print(f"🔍 DEBUG: Message types: {[msg.type if hasattr(msg, 'type') else 'unknown' for msg in messages_to_save]}")
        await self.session_service.update_session(
            message.session_id,
            messages=messages_to_save,
            user_name=result.get("user_name"),
            user_email=result.get("user_email"),
            user_phone=result.get("user_phone")
        )
        
        # Extract response
        response_text = result.get("final_response", "")
        if not response_text:
            # Fallback to last AI message
            for msg in reversed(result.get("messages", [])):
                if hasattr(msg, 'type') and msg.type == "ai":
                    response_text = msg.content
                    break
        
        # Extract tool calls from tool_results
        tool_results = result.get("tool_results", {})
        executed_tools = [
            tool_name 
            for tool_name, tool_result in tool_results.items() 
            if tool_result.get("success", False)
        ]
        
        return ChatResponse(
            session_id=message.session_id,
            response=response_text,
            tool_calls=executed_tools,
            blocked=result.get("blocked", False),
            block_reason=result.get("block_reason"),
            status="success"
        )
    
    async def get_history(self, session_id: str) -> Dict[str, Any]:
        """Get conversation history from database"""
        session = await self.session_service.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session_id,
            "messages": [
                {
                    "type": msg.type if hasattr(msg, 'type') else "unknown",
                    "content": msg.content if hasattr(msg, 'content') else str(msg)
                }
                for msg in session.get("messages", [])
            ],
            "user_name": session.get("user_name"),
            "user_email": session.get("user_email"),
            "is_returning": session.get("is_returning", False)
        }
    
    async def end_session(self, session_id: str):
        """
        End session and generate summary
        """
        await self.session_service.end_session(session_id)

