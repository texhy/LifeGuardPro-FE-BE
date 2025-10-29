"""
Chat Service - Orchestrates chat logic
"""
from typing import Dict, Any
from langchain_core.messages import HumanMessage

from core.graph import app as langgraph_app
from api.schemas.chat import ChatMessage, ChatResponse
from services.session_service import SessionService

class ChatService:
    def __init__(self, session_service=None):
        self.session_service = session_service or SessionService()
    
    async def process_message(self, message: ChatMessage) -> ChatResponse:
        """
        Process user message through LangGraph
        """
        # Get session
        session_data = await self.session_service.get_session(message.session_id)
        if not session_data:
            raise ValueError(f"Session {message.session_id} not found")
        
        # Build state
        state = {
            "messages": session_data["messages"] + [HumanMessage(content=message.message)],
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
        
        # Save updated session
        await self.session_service.update_session(
            message.session_id,
            messages=result.get("messages", []),
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
        
        # Extract tool calls from tool_results (tools that were successfully executed)
        tool_results = result.get("tool_results", {})
        executed_tools = [
            tool_name 
            for tool_name, tool_result in tool_results.items() 
            if tool_result.get("success", False)
        ]
        
        return ChatResponse(
            session_id=message.session_id,
            response=response_text,
            tool_calls=executed_tools,  # ✅ Now shows actual tools executed
            blocked=result.get("blocked", False),
            block_reason=result.get("block_reason"),
            status="success"
        )
    
    async def get_history(self, session_id: str) -> Dict[str, Any]:
        """Get conversation history"""
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
            "user_email": session.get("user_email")
        }

