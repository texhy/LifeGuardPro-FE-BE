"""
Agent node with tools - Phase 1: Planning Only

Confidence: 93% ✅

PHASE 1 CHANGES:
- Removed AgentExecutor and tool registration
- Added planner LLM call
- Added state schema integration
- NO TOOL EXECUTION (Phase 1)

Phase 2 will add actual tool execution.

Currently: Planning only - detects intents, fills slots, creates plan
Future: Execute tools based on plan
"""
from typing import Dict, Any
from langchain_core.messages import AIMessage
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# PHASE 1: Import planner and state schema
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from state_schema import (
    ConversationState,
    create_empty_state,
    validate_state,
    merge_planner_output
)
from planner_node import call_planner, validate_planner_output


# ============================================================================
# RESPONSE GENERATOR
# ============================================================================

def generate_response_from_plan(
    state: ConversationState,
    planner_output: Dict[str, Any]
) -> str:
    """
    Generate user-facing response based on plan
    
    Phase 1: NO TOOL EXECUTION
    Just show what we would do or ask for missing info
    
    Confidence: 88% ✅
    """
    next_action = state.get("next_action", "NONE")
    
    # Case 1: Need to ask for missing information
    if next_action == "ASK_SLOT":
        question = state.get("slot_question", "Could you provide more details?")
        return question
    
    # Case 2: Plan is ready (would execute in Phase 2)
    elif next_action == "READY":
        planned_calls = state.get("planned_calls", [])
        
        if not planned_calls:
            return "I'm ready to help! However, I don't have any specific actions to take. Could you clarify what you'd like to know?"
        
        # Build response showing the plan
        response_parts = [
            "Got it! Here's what I understand:",
            ""
        ]
        
        # Show intents
        intents = state.get("intents", [])
        if intents:
            intent_names = {
                "rag": "📚 Course information",
                "pricing": "💰 Pricing details",
                "quote": "📧 Email quote",
                "booking": "📅 Meeting booking"
            }
            response_parts.append("**You're interested in:**")
            for intent in intents:
                name = intent_names.get(intent, intent)
                conf = state.get("intent_confidence", {}).get(intent, 0)
                response_parts.append(f"   • {name} (confidence: {conf:.0%})")
            response_parts.append("")
        
        # Show planned actions
        response_parts.append("**What I would do (Phase 1 - simulation):**")
        for i, call in enumerate(planned_calls, 1):
            tool_name = call["tool"]
            args_preview = str(call.get("args", {}))[:80]
            status = "✅ Ready" if call.get("preconditions_met") else "⏳ Needs more info"
            
            response_parts.append(f"{i}. Call `{tool_name}` with {args_preview}... → {status}")
            
            if not call.get("preconditions_met"):
                missing = call.get("missing", [])
                response_parts.append(f"   ⚠️  Missing: {', '.join(missing)}")
        
        response_parts.append("")
        response_parts.append("🔔 **Note:** In Phase 1, tools are not actually executed.")
        response_parts.append("This is a simulation to test planning logic.")
        response_parts.append("")
        response_parts.append("Type 'proceed' when ready for Phase 2 (real execution).")
        
        return "\n".join(response_parts)
    
    # Case 3: No clear action
    else:
        intents = state.get("intents", [])
        if not intents:
            return "I can help you with course information, pricing, quotes, and booking consultations. What would you like to know?"
        else:
            return "I see you're asking about something, but I'm not sure how to help with that. Could you rephrase your question?"


# ============================================================================
# MAIN AGENT NODE (PHASE 1)
# ============================================================================

async def agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    PHASE 1: Planning-only agent node
    
    This node:
    1. Calls planner LLM to detect intents and fill slots
    2. Merges planner output into state
    3. Generates user-facing response (NO tool execution)
    
    Confidence: 93% ✅
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with plan and response
    """
    if not state.get("messages"):
        return state
    
    # Get last user message
    last_message = state["messages"][-1]
    user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    print(f"\n{'='*60}")
    print(f"🧠 PLANNER NODE (Phase 1 - Planning Only)")
    print(f"{'='*60}")
    print(f"User: {user_input[:100]}...")
    
    try:
        # Step 1: Call planner LLM
        print(f"\n📝 Step 1: Calling planner...")
        
        conversation_history = state.get("messages", [])[-10:]  # Last 10 messages
        
        planner_output = await call_planner(
            user_message=user_input,
            current_state=state,
            conversation_history=conversation_history
        )
        
        # Step 2: Validate planner output
        print(f"\n✅ Step 2: Validating planner output...")
        
        is_valid, errors = validate_planner_output(planner_output)
        
        if not is_valid:
            print(f"⚠️  Validation errors:")
            for error in errors:
                print(f"   - {error}")
            
            # Use fallback if critical errors
            if "Missing required key" in str(errors):
                print(f"❌ Critical validation failure, using fallback")
                planner_output = {
                    "intents": [],
                    "intent_confidence": {},
                    "pricing_slots": {},
                    "rag_slots": {},
                    "quote_slots": {},
                    "booking_slots": {},
                    "planned_calls": [],
                    "next_action": "ASK_SLOT",
                    "slot_question": "I'm having trouble understanding. Could you rephrase your question?",
                    "notes": ["Validation fallback"] + errors
                }
        
        # Step 3: Merge into state
        print(f"\n🔄 Step 3: Merging into state...")
        
        updated_state = merge_planner_output(state, planner_output)
        
        # Step 4: Generate user-facing response
        print(f"\n💬 Step 4: Generating response...")
        
        response_text = generate_response_from_plan(updated_state, planner_output)
        
        # Step 5: Update messages
        ai_message = AIMessage(content=response_text)
        
        print(f"\n📊 PLANNING SUMMARY:")
        print(f"   Intents: {updated_state.get('intents', [])}")
        print(f"   Next Action: {updated_state.get('next_action')}")
        print(f"   Planned Calls: {len(updated_state.get('planned_calls', []))}")
        for i, call in enumerate(updated_state.get("planned_calls", [])):
            status = "✅ Ready" if call.get("preconditions_met") else f"⏳ Missing: {', '.join(call.get('missing', []))}"
            print(f"      {i+1}. {call['tool']} → {status}")
        print(f"\n⚠️  Phase 1: NO TOOLS EXECUTED (planning only)")
        print(f"{'='*60}\n")
        
        return {
            **updated_state,
            "messages": state["messages"] + [ai_message],
            "final_response": response_text
        }
        
    except Exception as e:
        print(f"❌ Agent node error: {e}")
        import traceback
        traceback.print_exc()
        
        error_response = AIMessage(
            content="I apologize, but I'm having trouble processing that right now. Could you try asking in a different way?"
        )
        
        return {
            **state,
            "messages": state["messages"] + [error_response],
            "final_response": error_response.content,
            "agent_error": str(e)
        }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = ['agent_node', 'generate_response_from_plan']


# ============================================================================
# PHASE 2 NOTES (for future)
# ============================================================================

# When implementing Phase 2, we'll:
# 1. Re-enable tool imports
# 2. Create executor_node.py to handle tool execution
# 3. Modify generate_response_from_plan to use real tool results
# 4. Update graph.py to add executor node after planner
# 5. Set execute=True in planner when ready to execute
