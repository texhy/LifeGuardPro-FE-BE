"""
State Schema for Plan-and-Execute Agent (Phase 1)

This module defines the typed state structure for the planning system.
All planning information is stored here as a single source of truth.

Confidence: 95% ✅

Author: Plan-and-Execute Implementation
Phase: 1 (Planning Only - No Tool Execution)
"""

from typing import Literal, Optional, List, Dict, Any, TypedDict
from datetime import datetime
import copy


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================

# Supported intent types
IntentName = Literal[
    "rag",       # Search knowledge base
    "pricing",   # Get pricing information
    "quote",     # Send email quote with payment links
    "booking"    # Schedule meeting/consultation
]

# Tool names that can be called
ToolName = Literal[
    "rag_search",
    "get_pricing",
    "quote_send_email",
    "book_meeting"
]

# Next action types
NextAction = Literal[
    "ASK_SLOT",  # Need to ask user for missing info
    "READY",     # Ready to execute (would execute in Phase 2)
    "NONE"       # No action needed or can't help
]


# ============================================================================
# SLOT STRUCTURES (Per-Intent)
# ============================================================================

class PricingSlots(TypedDict, total=False):
    """
    Slots for pricing intent
    
    Required for get_pricing:
    - buyer_category
    - course_slug (with course_variant_ok=True)
    - quantity (default 1 for individual)
    """
    # Core identification
    buyer_category: Literal["individual", "employer_or_instructor"]
    course_slug: str  # e.g., "swimming-pool-lifeguard-12ft"
    course_title: str  # e.g., "Swimming Pool Lifeguard (12 ft)"
    course_variant_ok: bool  # True if exact match found
    
    # Quantity
    quantity: int  # Number of students (default 1)
    
    # Pricing options
    price_option: Literal[
        "published",                    # Standard published pricing
        "lowest_price_guarantee",       # LPG special
        "inflation_buster",             # Inflation buster deal
        "unpublished_specials"          # Hidden deals
    ]
    published_variant: Optional[Literal["4A", "4B"]]  # For group pricing
    
    # Special qualifications (may unlock better pricing)
    has_LGIT: Optional[bool]  # Lifeguard Instructor Trainer
    has_WSITD: Optional[bool]  # Water Safety Instructor Trainer Director


class RAGSlots(TypedDict, total=False):
    """
    Slots for RAG (knowledge search) intent
    
    Required for rag_search:
    - query (the actual search query)
    """
    query: str  # Search query text
    topic: Optional[str]  # Categorized topic (course, policy, location, etc.)
    keywords: Optional[List[str]]  # Extracted keywords


class QuoteSlots(TypedDict, total=False):
    """
    Slots for quote/email intent
    
    Required for quote_send_email:
    - user_email (from state.user_email)
    - course_slug
    - quantity
    - pricing confirmed
    """
    course_slug: str
    course_title: str
    quantity: int
    price_option: Literal["4A", "4B", "individual"]
    unit_price: float  # Filled after get_pricing called
    total_price: float  # Calculated
    user_confirmed: bool  # User explicitly said "yes, send it"


class BookingSlots(TypedDict, total=False):
    """
    Slots for meeting/booking intent
    
    Required for book_meeting:
    - user_email (from state.user_email)
    - meeting_purpose
    """
    meeting_purpose: str  # "course selection", "group inquiry", etc.
    preferred_date: Optional[str]  # "tomorrow", "2025-10-20", "next Monday"
    preferred_time: Optional[str]  # "2pm", "morning", "14:00"
    duration_minutes: int  # Default 30
    user_confirmed: bool  # User said "yes, book it"


# ============================================================================
# PLANNED CALL STRUCTURE
# ============================================================================

class PlannedCall(TypedDict, total=False):
    """
    Represents a tool call that would be executed
    
    In Phase 1: execute is always False
    In Phase 2+: execute can be True when preconditions met
    """
    tool: ToolName  # Which tool to call
    args: Dict[str, Any]  # Arguments for the tool
    preconditions_met: bool  # All required info available?
    missing: List[str]  # What's missing (if preconditions_met=False)
    execute: bool  # Should execute? (Always False in Phase 1)
    note: Optional[str]  # Planner notes (error sims, hints)
    priority: int  # Execution order (default 0, higher = later)


# ============================================================================
# MAIN CONVERSATION STATE
# ============================================================================

class ConversationState(TypedDict, total=False):
    """
    Main state for the conversation
    
    This is the single source of truth for:
    - What the user wants (intents)
    - What information we have (slots)
    - What we plan to do (planned_calls)
    - What happens next (next_action)
    """
    # Messages (from graph)
    messages: List[Any]  # List of HumanMessage/AIMessage objects
    
    # User information (from collect_user_info)
    user_name: Optional[str]
    user_email: Optional[str]
    user_phone: Optional[str]
    user_info_collected: bool
    
    # Intent detection
    intents: List[IntentName]  # e.g., ["pricing", "rag"]
    intent_confidence: Dict[str, float]  # e.g., {"pricing": 0.92, "rag": 0.61}
    
    # Query classification (NEW - for intelligent response routing)
    query_type: str  # "broad_general", "process_walkthrough", "comparison", "recommendation_with_context", "specific_question"
    user_context: Dict[str, Any]  # {age, profession, role, physical_capability, goal} - if recommendation_with_context
    comparison_items: List[str]  # ["bls", "cpr"] - if comparison
    process_domain: Optional[str]  # "pricing", "certification", "enrollment" - if process_walkthrough
    
    # Slots for each intent
    pricing_slots: PricingSlots
    rag_slots: RAGSlots
    quote_slots: QuoteSlots
    booking_slots: BookingSlots
    
    # Planned tool calls (Phase 1: none executed)
    planned_calls: List[PlannedCall]
    
    # Next action logic
    next_action: NextAction  # ASK_SLOT, READY, or NONE
    slot_question: Optional[str]  # Question to ask if ASK_SLOT
    
    # Planner notes & debugging
    notes: List[str]  # Planner hints, error simulations, etc.
    planner_errors: List[str]  # JSON parse errors, validation errors
    
    # Tool results (Phase 2+)
    tool_results: Dict[str, Any]  # {tool_name: result}
    execution_errors: List[str]  # Errors during tool execution
    
    # Phase 2.2: Multi-Query Expansion fields
    expanded_queries: List[Dict[str, Any]]  # [{query: str, weight: float}]
    expansion_confidence: float
    coverage_score: float
    
    # Phase 2.2: Retrieval fields
    retrieved_chunks: List[Dict[str, Any]]
    retrieval_method: str  # "vector_only", "hybrid_rrf_mmr"
    retrieval_confidence: float
    bm25_candidates: int
    vector_candidates: int
    rrf_fused_count: int
    mmr_final_count: int
    
    # Phase 2.3: CoVe verification fields
    verified_claims: List[Dict[str, Any]]
    coVe_confidence: float
    supported_claims_count: int
    unresolved_claims_count: int
    contradicted_claims_count: int
    
    # Phase 2.4: Response enhancement fields
    response_confidence: float
    citations: List[Dict[str, Any]]
    hedged_statements: List[str]
    removed_statements: List[str]
    low_confidence_warning: bool
    
    # Error tracking
    retrieval_failure_reason: Optional[str]
    partial_results: bool
    failed_tools: List[str]
    contradictions_found: int
    
    # Final response
    final_response: Optional[str]
    
    # Metadata
    turn_count: int  # How many turns in this conversation
    last_updated: str  # ISO timestamp


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_empty_state() -> ConversationState:
    """
    Create a new empty state with defaults
    
    Returns:
        Empty ConversationState with default values
    """
    return {
        "messages": [],
        "intents": [],
        "intent_confidence": {},
        
        # Query classification (NEW)
        "query_type": "specific_question",  # Default to specific
        "user_context": {},  # Empty by default
        "comparison_items": [],  # Empty by default
        "process_domain": None,  # Null by default
        
        "pricing_slots": {},
        "rag_slots": {},
        "quote_slots": {},
        "booking_slots": {},
        "planned_calls": [],
        "next_action": "NONE",
        "notes": [],
        "planner_errors": [],
        
        # Phase 2.1: Execution fields
        "tool_results": {},
        "execution_errors": [],
        
        # Phase 2.2: MQE and retrieval fields (empty for now)
        "expanded_queries": [],
        "retrieved_chunks": [],
        "retrieval_method": "",
        
        # Phase 2.3: CoVe fields (empty for now)
        "verified_claims": [],
        
        # Phase 2.4: Response fields (empty for now)
        "citations": [],
        "hedged_statements": [],
        "removed_statements": [],
        "failed_tools": [],
        
        # User info
        "user_info_collected": False,
        
        # Metadata
        "turn_count": 0,
        "last_updated": datetime.now().isoformat()
    }


def validate_state(state: ConversationState) -> bool:
    """
    Validate state structure
    
    Args:
        state: State to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check required fields
        assert "messages" in state, "Missing 'messages' field"
        assert "intents" in state, "Missing 'intents' field"
        assert "next_action" in state, "Missing 'next_action' field"
        
        # Validate next_action
        valid_actions = ["ASK_SLOT", "READY", "NONE"]
        assert state["next_action"] in valid_actions, \
            f"Invalid next_action: {state['next_action']}"
        
        # If ASK_SLOT, must have slot_question
        if state["next_action"] == "ASK_SLOT":
            assert state.get("slot_question"), "ASK_SLOT requires slot_question"
        
        # Validate intents
        valid_intents = ["rag", "pricing", "quote", "booking"]
        for intent in state.get("intents", []):
            assert intent in valid_intents, f"Invalid intent: {intent}"
        
        # Validate planned_calls
        for i, call in enumerate(state.get("planned_calls", [])):
            assert "tool" in call, f"planned_calls[{i}] missing 'tool'"
            assert "args" in call, f"planned_calls[{i}] missing 'args'"
            assert "preconditions_met" in call, \
                f"planned_calls[{i}] missing 'preconditions_met'"
        
        return True
        
    except AssertionError as e:
        print(f"❌ State validation failed: {e}")
        return False


def merge_planner_output(
    state: ConversationState,
    planner_output: Dict[str, Any]
) -> ConversationState:
    """
    Merge planner output into existing state
    
    This is the CRITICAL function that updates state
    based on what the planner LLM returns.
    
    Args:
        state: Current state
        planner_output: JSON from planner LLM
        
    Returns:
        Updated state (new dict, immutable pattern)
    """
    # Create new state (immutable update)
    new_state = copy.deepcopy(state)
    
    # Update intents (max 4 to prevent hallucinations)
    if "intents" in planner_output:
        new_state["intents"] = planner_output["intents"][:4]
    
    # Update intent confidence
    if "intent_confidence" in planner_output:
        new_state["intent_confidence"] = planner_output["intent_confidence"]
    
    # NEW: Update query classification fields (replace each turn)
    if "query_type" in planner_output:
        new_state["query_type"] = planner_output["query_type"]
    
    if "user_context" in planner_output:
        new_state["user_context"] = planner_output["user_context"]
    
    if "comparison_items" in planner_output:
        new_state["comparison_items"] = planner_output["comparison_items"]
    
    if "process_domain" in planner_output:
        new_state["process_domain"] = planner_output["process_domain"]
    
    # Update pricing slots (merge, don't replace)
    if "pricing_slots" in planner_output:
        ps = new_state.get("pricing_slots", {})
        # Only update non-None values
        for k, v in planner_output["pricing_slots"].items():
            if v is not None:
                ps[k] = v
        new_state["pricing_slots"] = ps
    
    # Update rag slots
    if "rag_slots" in planner_output:
        rs = new_state.get("rag_slots", {})
        for k, v in planner_output["rag_slots"].items():
            if v is not None:
                rs[k] = v
        new_state["rag_slots"] = rs
    
    # Update quote slots
    if "quote_slots" in planner_output:
        qs = new_state.get("quote_slots", {})
        for k, v in planner_output["quote_slots"].items():
            if v is not None:
                qs[k] = v
        new_state["quote_slots"] = qs
    
    # Update booking slots
    if "booking_slots" in planner_output:
        bs = new_state.get("booking_slots", {})
        for k, v in planner_output["booking_slots"].items():
            if v is not None:
                bs[k] = v
        new_state["booking_slots"] = bs
    
    # Update planned calls (replace, not merge)
    if "planned_calls" in planner_output:
        new_state["planned_calls"] = planner_output["planned_calls"]
    
    # Update next action
    if "next_action" in planner_output:
        new_state["next_action"] = planner_output["next_action"]
    
    # Update slot question
    if "slot_question" in planner_output:
        new_state["slot_question"] = planner_output["slot_question"]
    
    # Add notes (append, keep last 20)
    if "notes" in planner_output:
        existing_notes = new_state.get("notes", [])
        new_state["notes"] = (existing_notes + planner_output["notes"])[-20:]
    
    # Add errors if present
    if "planner_errors" in planner_output:
        existing_errors = new_state.get("planner_errors", [])
        new_state["planner_errors"] = (existing_errors + planner_output["planner_errors"])[-10:]
    
    # Update metadata
    new_state["turn_count"] = state.get("turn_count", 0) + 1
    new_state["last_updated"] = datetime.now().isoformat()
    
    return new_state


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Types
    'IntentName',
    'ToolName',
    'NextAction',
    
    # Slot structures
    'PricingSlots',
    'RAGSlots',
    'QuoteSlots',
    'BookingSlots',
    
    # Call structure
    'PlannedCall',
    
    # Main state
    'ConversationState',
    
    # Helper functions
    'create_empty_state',
    'validate_state',
    'merge_planner_output'
]

