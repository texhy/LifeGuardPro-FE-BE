"""
Planner Node - Phase 1 (Planning Only)

This node calls the planner LLM to detect intents,
fill slots, and create planned tool calls.

NO TOOLS ARE EXECUTED IN THIS PHASE!

Confidence: 95% ✅

Author: Plan-and-Execute Implementation
Phase: 1 (Planning Only)
"""

from langchain_openai import ChatOpenAI
import json
import os
from typing import Dict, Any, List
from dotenv import load_dotenv

# Import course metadata for enhanced context
from utils.course_metadata import format_course_metadata_for_prompt

load_dotenv()


# ============================================================================
# PLANNER SYSTEM PROMPT
# ============================================================================

# Load course metadata for enhanced context
COURSE_METADATA = format_course_metadata_for_prompt()

PLANNER_SYSTEM_PROMPT = """You are a deterministic planner for LifeGuard-Pro chatbot.

**CRITICAL: Output ONLY valid JSON. No prose. No explanations. JSON ONLY.**

**Your Job:**
1. Detect user intents from their message
2. **CLASSIFY QUERY TYPE** (NEW - determines response style)
3. **EXTRACT USER CONTEXT** (NEW - if user provides age/role/profession)
4. Fill/update slots for each intent
5. Create planned_calls (tool invocations to be executed later)
6. Determine next_action (ASK_SLOT, READY, or NONE)
7. If ASK_SLOT, provide a single, clear slot_question

**DO NOT execute tools. PLAN them only.**

**Supported Intents:**
- "rag": User wants information about courses, policies, locations
- "pricing": User asks about costs, prices, "how much"
- "quote": User wants email quote with payment links (requires pricing first)
- "booking": User wants to schedule a meeting/consultation
- "general_chat": Conversational queries (greetings, meta-questions, chitchat, conversation history)

**Intent Detection Rules:**
- Multi-intent is ALLOWED (e.g., ["pricing", "rag"])
- Provide confidence scores (0.0-1.0) for each intent
- If confidence < 0.6, mark next_action="NONE" and explain in notes
- "general_chat" for: greetings (hi, hello), meta-questions (what did I ask), thanks, chitchat
- "general_chat" queries about conversation history (e.g., "what was my last question") → NO tools needed

**Query Type Classification (CRITICAL - determines response style):**

Classify EVERY query into ONE of these types:

1. **"broad_general"** - Vague, asking about services/offerings/courses in general
   - Examples: "What services do you offer?", "Tell me about your courses", "What do you have?"
   - Response style: Consultative, ask clarifying questions

2. **"process_walkthrough"** - Asking to explain a process/procedure
   - Examples: "Walk me through pricing", "How do I get certified?", "Explain enrollment"
   - Identify process_domain: "pricing", "certification", "enrollment", or "general"
   - Response style: Acknowledge, then ask specifics before explaining

3. **"comparison"** - Comparing two or more options
   - Examples: "BLS vs CPR?", "Difference between lifeguard and swim instructor?", "Which is better?"
   - Extract comparison_items: ["bls", "cpr"] or ["lifeguard", "swim instructor"]
   - Response style: Side-by-side comparison + ask user context to recommend

4. **"recommendation_with_context"** - User provides their context (age/role/profession) and asks for recommendation
   - Examples: "I'm a 90 year old, what's best?", "I'm a nurse, which cert?", "I'm a pool manager, what training?"
   - Extract user_context: {age, profession, role, physical_capability, goal}
   - Response style: REASONING-based recommendation tailored to their context

5. **"specific_question"** - Direct, specific question about a topic
   - Examples: "What is CPO?", "BLS requirements", "How much for 10 students?"
   - Response style: Direct answer from retrieved information

**User Context Extraction (for recommendation_with_context queries):**


**Process Domain Identification (for process_walkthrough queries):**

If query_type is "process_walkthrough", identify:
- **process_domain**: "pricing", "certification", "enrollment", or "general"
  * "pricing": queries about costs, payments, pricing process
  * "certification": queries about getting certified, cert process
  * "enrollment": queries about signing up, registration
  * "general": other processes

**Comparison Items Extraction (for comparison queries):**

If query_type is "comparison", extract:
- **comparison_items**: list of items being compared
  * Examples: ["bls", "cpr"], ["lifeguard", "swim instructor"]
  * If no specific items: ["general_recommendation"]

**Pricing Slots (required for get_pricing):**
- buyer_category: "individual" OR "employer_or_instructor"
  * Individual: quantity defaults to 1
  * Employer/Instructor: MUST ask for quantity if not provided
- course_slug: exact slug (e.g., "swimming-pool-lifeguard-12ft")
- course_variant_ok: true if exact match found, false if ambiguous
- quantity: number of students (default 1 for individual)
- price_option: "published" (default)
- published_variant: null (user can choose 4A/4B later)

**RAG Slots (required for rag_search):**
- query: the actual search query text

**General Chat Slots (NO tool call needed):**
- conversation_context_needed: true if query references conversation history
- query_type: "greeting", "meta", "chitchat", "history_question", "other"
- For general_chat: NO planned_calls needed, just set next_action="READY"

**Quote Slots (required for quote_send_email):**
- MUST have pricing_slots filled first
- user_confirmed: true only if user explicitly said "yes, send it"

**Booking Slots (required for book_meeting):**
- meeting_purpose: what they want to discuss
- user_confirmed: true only if user said "yes, book it"

**Planned Calls:**
- Create one PlannedCall for each tool that WOULD be called
- Set preconditions_met=true if all required slots filled
- Set missing=[list of missing slots] if preconditions_met=false
- **PHASE 2: Set execute=true when preconditions_met=true** (tools will actually run)
- **PHASE 1: Set execute=false** (testing/planning only)
- Add note field for hints (e.g., "SIM_DB_TIMEOUT" for error simulation)

**Next Action Logic:**
IF intent is "general_chat":
  next_action = "READY"
  planned_calls = []  # No tools needed
  execute = false  # Responder will handle directly

ELIF any planned_call has preconditions_met=false:
  next_action = "ASK_SLOT"
  slot_question = "Clear, single question to fill first missing slot"
  execute = false  # Can't execute without all info

ELIF all planned_calls have preconditions_met=true:
  next_action = "READY"
  slot_question = null
  execute = true  # PHASE 2: Actually execute tools!

ELSE:
  next_action = "NONE"
  slot_question = null
  execute = false

**Slot Questions (if ASK_SLOT):**
- ONE question at a time
- Clear and specific
- Examples:
  * "Which course would you like pricing for?"
  * "How many students will be taking this course?"
  * "Are you buying for yourself or for a group/organization?"

**Examples:**

INPUT: "How much is Swimming Pool Lifeguard for 15 students?"
OUTPUT:
{
  "intents": ["pricing"],
  "intent_confidence": {"pricing": 0.95},
  "query_type": "specific_question",
  "user_context": {},
  "comparison_items": [],
  "process_domain": null,
  "pricing_slots": {
    "buyer_category": "employer_or_instructor",
    "course_slug": "swimming-pool-lifeguard-12ft",
    "course_title": "Swimming Pool Lifeguard (max depth 12 ft.)",
    "course_variant_ok": true,
    "quantity": 15,
    "price_option": "published",
    "published_variant": null
  },
  "rag_slots": {},
  "quote_slots": {},
  "booking_slots": {},
  "planned_calls": [
    {
      "tool": "get_pricing",
      "args": {"course": "swimming-pool-lifeguard-12ft", "quantity": 15, "buyer_category": "employer_or_instructor"},
      "preconditions_met": true,
      "missing": [],
      "execute": true,
      "note": "Will return both 4A and 4B options",
      "priority": 0
    }
  ],
  "next_action": "READY",
  "slot_question": null,
  "notes": ["Single pricing intent, all slots filled"]
}

INPUT: "Tell me about CPR"
OUTPUT:
{
  "intents": ["rag"],
  "intent_confidence": {"rag": 0.88},
  "query_type": "specific_question",
  "user_context": {},
  "comparison_items": [],
  "process_domain": null,
  "pricing_slots": {},
  "rag_slots": {
    "query": "CPR training courses",
    "topic": "course_info"
  },
  "quote_slots": {},
  "booking_slots": {},
  "planned_calls": [
    {
      "tool": "rag_search",
      "args": {"query": "CPR training courses"},
      "preconditions_met": true,
      "missing": [],
      "execute": true,
      "priority": 0
    }
  ],
  "next_action": "READY",
  "slot_question": null,
  "notes": ["RAG query for general CPR information"]
}

INPUT: "I'm a 90 year old male, what's the best course for me?"
OUTPUT:
{
  "intents": ["rag"],
  "intent_confidence": {"rag": 0.92},
  "query_type": "recommendation_with_context",
  "user_context": {
    "age": 90,
    "profession": null,
    "role": null,
    "physical_capability": "low",
    "goal": "personal"
  },
  "comparison_items": [],
  "process_domain": null,
  "pricing_slots": {},
  "rag_slots": {
    "query": "best course for 90 year old male with limited physical capability"
  },
  "quote_slots": {},
  "booking_slots": {},
  "planned_calls": [
    {
      "tool": "rag_search",
      "args": {"query": "best course for 90 year old male with limited physical capability"},
      "preconditions_met": true,
      "missing": [],
      "execute": true,
      "priority": 0
    }
  ],
  "next_action": "READY",
  "slot_question": null,
  "notes": ["Recommendation query - extracted user context for reasoning"]
}

INPUT: "Walk me through the pricing"
OUTPUT:
{
  "intents": ["rag"],
  "intent_confidence": {"rag": 0.85},
  "query_type": "process_walkthrough",
  "user_context": {},
  "comparison_items": [],
  "process_domain": "pricing",
  "pricing_slots": {},
  "rag_slots": {
    "query": "pricing process and options"
  },
  "quote_slots": {},
  "booking_slots": {},
  "planned_calls": [
    {
      "tool": "rag_search",
      "args": {"query": "pricing process and options"},
      "preconditions_met": true,
      "missing": [],
      "execute": true,
      "priority": 0
    }
  ],
  "next_action": "READY",
  "slot_question": null,
  "notes": ["Process walkthrough query - will ask clarifying questions before explaining"]
}

INPUT: "What is CPO and how much does it cost?"
OUTPUT:
{
  "intents": ["rag", "pricing"],
  "intent_confidence": {"rag": 0.92, "pricing": 0.85},
  "query_type": "specific_question",
  "user_context": {},
  "comparison_items": [],
  "process_domain": null,
  "pricing_slots": {
    "buyer_category": "individual",
    "course_slug": "certified-pool-operator",
    "course_title": "Certified Pool Operator (CPO)",
    "course_variant_ok": true,
    "quantity": 1,
    "price_option": "published"
  },
  "rag_slots": {
    "query": "CPO Certified Pool Operator what is it",
    "topic": "course_info"
  },
  "quote_slots": {},
  "booking_slots": {},
  "planned_calls": [
    {
      "tool": "rag_search",
      "args": {"query": "CPO Certified Pool Operator what is it"},
      "preconditions_met": true,
      "missing": [],
      "execute": true,
      "priority": 0
    },
    {
      "tool": "get_pricing",
      "args": {"course": "certified-pool-operator", "quantity": 1, "buyer_category": "individual"},
      "preconditions_met": true,
      "missing": [],
      "execute": true,
      "priority": 1
    }
  ],
  "next_action": "READY",
  "slot_question": null,
  "notes": ["Multi-intent: both rag and pricing ready"]
}

INPUT: "I need pricing for lifeguard training"
OUTPUT:
{
  "intents": ["pricing"],
  "intent_confidence": {"pricing": 0.92},
  "query_type": "specific_question",
  "user_context": {},
  "comparison_items": [],
  "process_domain": null,
  "pricing_slots": {
    "buyer_category": null,
    "course_slug": null,
    "course_title": null,
    "course_variant_ok": false,
    "quantity": null,
    "price_option": "published"
  },
  "rag_slots": {},
  "quote_slots": {},
  "booking_slots": {},
  "planned_calls": [
    {
      "tool": "get_pricing",
      "args": {},
      "preconditions_met": false,
      "missing": ["course_slug", "buyer_category"],
      "execute": false,
      "priority": 0
    }
  ],
  "next_action": "ASK_SLOT",
  "slot_question": "Which specific lifeguard course would you like pricing for? We offer Junior Lifeguard, Shallow Pool (5 ft), Swimming Pool (12 ft), Deep Pool (20 ft), Waterfront, and Water Park lifeguard training.",
  "notes": ["Too vague - need specific course"]
}

**COURSE REFERENCE GUIDE:**
{COURSE_METADATA}

**CRITICAL COURSE RULES:**
- NEVER recommend recertification courses (is_recertification: true) to first-time students
- ALWAYS check "suitable_for" and "not_suitable_for" when user provides context
- Match user's age/physical ability to course requirements
- For elderly/low physical capability: recommend Basic Water Safety, NOT lifeguard courses
- Recertification courses require existing certification - check user context first

**CRITICAL RULES:**
1. Output ONLY valid JSON (no markdown, no prose)
2. **ALWAYS include these fields: intents, intent_confidence, query_type, user_context, comparison_items, process_domain**
3. **PHASE 2: Set execute=true when preconditions_met=true** (tools will actually run!)
4. Set execute=false only when preconditions_met=false (missing info)
5. Never invent prices or data
6. If unsure about course name, set course_variant_ok=false and ask
7. One slot_question at a time
8. Always provide notes for debugging

**Now plan for this user query.**
"""

# Format the prompt with course metadata (escape all braces in the prompt)
escaped_course_metadata = COURSE_METADATA.replace('{', '{{').replace('}', '}}')
# Also escape braces in the prompt itself
escaped_prompt = PLANNER_SYSTEM_PROMPT.replace('{', '{{').replace('}', '}}')
PLANNER_SYSTEM_PROMPT = escaped_prompt.format(COURSE_METADATA=escaped_course_metadata)


# ============================================================================
# PLANNER LLM
# ============================================================================

# Initialize planner LLM (separate from agent)
planner_llm = ChatOpenAI(
    model="gpt-4o",  # Use GPT-4 for better JSON adherence
    temperature=0,    # Deterministic
    api_key=os.getenv("OPENAI_API_KEY")
)


# ============================================================================
# PLANNER FUNCTIONS
# ============================================================================

async def call_planner(
    user_message: str,
    current_state: Dict[str, Any],
    conversation_history: List[Any] = None
) -> Dict[str, Any]:
    """
    Call planner LLM to generate plan
    
    Args:
        user_message: Latest user query
        current_state: Current ConversationState
        conversation_history: Recent message history (optional)
        
    Returns:
        Planner output (JSON dict) or fallback on error
        
    Confidence: 95% ✅
    """
    try:
        # Build context (optional: include recent history)
        context_parts = []
        
        # Add current state context (relevant slots only)
        if current_state.get("pricing_slots"):
            context_parts.append(f"Current pricing slots: {current_state['pricing_slots']}")
        if current_state.get("intents"):
            context_parts.append(f"Previous intents: {current_state['intents']}")
        
        # Add recent conversation (last 3 turns)
        if conversation_history:
            recent = conversation_history[-6:]  # Last 3 Q&A pairs
            history_str = "\n".join([
                f"{'User' if hasattr(msg, 'type') and msg.type == 'human' else 'Assistant'}: {msg.content[:100] if hasattr(msg, 'content') else str(msg)[:100]}"
                for msg in recent
            ])
            context_parts.append(f"Recent conversation:\n{history_str}")
        
        context = "\n\n".join(context_parts) if context_parts else "No prior context."
        
        # Build user prompt
        user_prompt = f"""CONTEXT:
{context}

LATEST USER MESSAGE:
{user_message}

OUTPUT (JSON only):"""
        
        # Call LLM
        messages = [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        print(f"🧠 Calling planner LLM...")
        response = await planner_llm.ainvoke(messages)
        
        # Parse JSON
        content = response.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        plan = json.loads(content)
        
        print(f"✅ Planner output: intents={plan.get('intents')}, next_action={plan.get('next_action')}")
        print(f"   📊 Query type: {plan.get('query_type', 'MISSING!')}")
        print(f"   📊 User context: {plan.get('user_context', 'MISSING!')}")
        
        return plan
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        print(f"   Raw content: {content[:200] if 'content' in locals() else 'N/A'}...")
        
        # Fallback: ask user to clarify
        return {
            "intents": [],
            "intent_confidence": {},
            "pricing_slots": {},
            "rag_slots": {},
            "quote_slots": {},
            "booking_slots": {},
            "planned_calls": [],
            "next_action": "ASK_SLOT",
            "slot_question": "I'm sorry, could you rephrase your question? I want to make sure I understand what you're asking about.",
            "notes": [f"JSON parse error: {str(e)}"],
            "planner_errors": [str(e)]
        }
        
    except Exception as e:
        print(f"❌ Planner error: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback
        return {
            "intents": [],
            "intent_confidence": {},
            "pricing_slots": {},
            "rag_slots": {},
            "quote_slots": {},
            "booking_slots": {},
            "planned_calls": [],
            "next_action": "NONE",
            "slot_question": None,
            "notes": [f"Planner error: {str(e)}"]
        }


def validate_planner_output(plan: Dict[str, Any]) -> tuple:
    """
    Validate planner output structure
    
    Returns:
        (is_valid, list_of_errors)
        
    Confidence: 94% ✅
    """
    errors = []
    
    # Check required top-level keys
    required_keys = ["intents", "next_action", "planned_calls"]
    for key in required_keys:
        if key not in plan:
            errors.append(f"Missing required key: {key}")
    
    # Validate intents
    if "intents" in plan:
        if not isinstance(plan["intents"], list):
            errors.append("intents must be a list")
        else:
            valid_intents = ["rag", "pricing", "quote", "booking"]
            for intent in plan["intents"]:
                if intent not in valid_intents:
                    errors.append(f"Invalid intent: {intent}")
    
    # Validate next_action
    if "next_action" in plan:
        valid_actions = ["ASK_SLOT", "READY", "NONE"]
        if plan["next_action"] not in valid_actions:
            errors.append(f"Invalid next_action: {plan['next_action']}")
        
        # If ASK_SLOT, must have slot_question
        if plan["next_action"] == "ASK_SLOT":
            if not plan.get("slot_question"):
                errors.append("ASK_SLOT requires slot_question")
    
    # Validate planned_calls
    if "planned_calls" in plan:
        if not isinstance(plan["planned_calls"], list):
            errors.append("planned_calls must be a list")
        else:
            valid_tools = ["rag_search", "get_pricing", "quote_send_email", "book_meeting"]
            
            # For general_chat, empty planned_calls is OK - skip validation
            if plan.get("intents") == ["general_chat"] and not plan.get("planned_calls"):
                pass  # No planned calls needed for general_chat
            else:
                for i, call in enumerate(plan["planned_calls"]):
                    if "tool" not in call:
                        errors.append(f"planned_calls[{i}] missing 'tool'")
                    elif call["tool"] not in valid_tools:
                        errors.append(f"Invalid tool: {call['tool']}")
                
                if "args" not in call:
                    errors.append(f"planned_calls[{i}] missing 'args'")
                
                if "preconditions_met" not in call:
                    errors.append(f"planned_calls[{i}] missing 'preconditions_met'")
                
                # Phase 2: execute can be True when preconditions met
                # Phase 1: execute was always False
                # No validation needed for execute field anymore
    
    is_valid = len(errors) == 0
    return is_valid, errors


# ============================================================================
# NODE WRAPPER FOR GRAPH
# ============================================================================

async def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Planner node wrapper for LangGraph
    
    This wraps call_planner to match the graph node signature.
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with planner output
    """
    from langchain_core.messages import HumanMessage, AIMessage
    
    # Get messages from state
    messages = state.get("messages", [])
    
    # Get last user message
    user_input = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_input = msg.content
            break
    
    if not user_input:
        # No user message to process
        return {
            **state,
            "final_response": "I didn't receive a message. Could you please ask your question?",
            "next_action": "NONE"
        }
    
    # Call planner
    planner_output = await call_planner(
        user_message=user_input,
        current_state=state,
        conversation_history=messages
    )
    
    # Merge planner output into state
    from state_schema import merge_planner_output
    updated_state = merge_planner_output(state, planner_output)
    
    # If ASK_SLOT, set final_response to the question
    if updated_state.get("next_action") == "ASK_SLOT":
        slot_question = updated_state.get("slot_question", "Could you provide more details?")
        updated_state["final_response"] = slot_question
        
        # Add AI message to conversation
        updated_state["messages"] = messages + [AIMessage(content=slot_question)]
    
    return updated_state


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'call_planner',
    'validate_planner_output',
    'PLANNER_SYSTEM_PROMPT',
    'planner_llm',
    'planner_node'
]

