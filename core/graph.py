"""
Bot v3 RAG Improved - FULL Advanced RAG Pipeline

Confidence: 88% ✅

Architecture:
1. LLM Guardrails - Context-aware safety check
2. Collect User Info - Get email/phone
3. Planner - Intent detection, slot filling
4. Executor - Tool execution (RAG, Pricing, Quote, Booking)
5. Responder - Response generation

NEW RAG Pipeline (Phase 2 & 3 Complete):
- Multi-Query Expansion (MQE) - 3-5 query variations
- BM25 Keyword Search - Exact matches
- Vector Semantic Search - Semantic understanding
- RRF Fusion - Merge BM25 + Vector rankings
- MMR Diversity - Select 10 diverse chunks
- CoVe Verification - Verify all claims

This implements the FULL plan from rag_implementation.md!
"""
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END

# Import nodes
from nodes.llm_guardrails import llm_guardrail
# REMOVED: collect_user_info - Now collected at startup in main.py
from core.planner_node import planner_node  # Full node wrapper
from core.executor_node import executor_node
from core.react_responder import react_responder_node

# Import state schema
from core.state_schema import ConversationState, create_empty_state, merge_planner_output

# ================================================================
# STATE SCHEMA
# ================================================================

class GraphState(TypedDict):
    """
    Bot v3 RAG Improved - State Schema
    
    Combines old chatbot fields with new Plan-and-Execute architecture
    
    Confidence: 90% ✅
    """
    # Messages (multi-turn conversation)
    messages: Annotated[list[BaseMessage], add_messages]
    
    # Guardrails
    blocked: bool
    block_reason: str | None
    
    # User info
    user_email: str | None
    user_name: str | None
    user_phone: str | None
    info_requested: bool
    info_request_count: int
    needs_info: bool
    info_skipped: bool
    skip_reason: str | None
    
    # Plan-and-Execute fields (from state_schema.py)
    intents: list
    intent_confidence: dict
    
    # Query classification (NEW - for intelligent response routing)
    query_type: str
    user_context: dict
    comparison_items: list
    process_domain: str | None
    
    pricing_slots: dict
    rag_slots: dict
    quote_slots: dict
    booking_slots: dict
    planned_calls: list
    next_action: str
    slot_question: str | None
    notes: list
    planner_errors: list
    
    # Tool execution fields (Phase 2 & 3)
    tool_results: dict
    execution_errors: list
    
    # Phase 2 & 3 RAG fields (MQE + Hybrid + RRF + MMR)
    expanded_queries: list
    expansion_confidence: float
    coverage_score: float
    retrieved_chunks: list
    retrieval_method: str
    retrieval_confidence: float
    bm25_candidates: int
    vector_candidates: int
    rrf_fused_count: int
    mmr_final_count: int
    
    # Phase 4 CoVe fields
    verified_claims: list
    coVe_confidence: float
    supported_claims_count: int
    unresolved_claims_count: int
    contradicted_claims_count: int
    
    # Final response
    final_response: str | None
    agent_error: str | None
    
    # Metadata
    turn_count: int
    last_updated: str

# ================================================================
# ROUTING FUNCTIONS
# ================================================================

def route_after_guardrail(state: GraphState) -> Literal["planner", "end"]:
    """
    Route after LLM guardrail check
    
    Confidence: 100% ✅
    
    Flow:
    - If blocked → END (response already set by guardrail)
    - If safe → planner (user info already collected at startup)
    """
    if state.get("blocked"):
        print("🚫 Input blocked by guardrail → END")
        return "end"
    
    print("✅ Input safe → planner")
    return "planner"


def route_after_planner(state: GraphState) -> Literal["executor", "end"]:
    """
    Route after planner
    
    Flow:
    - If next_action == READY → executor (execute tools)
    - If next_action == ASK_SLOT → END (need more info from user)
    - Otherwise → END (no clear action)
    
    Confidence: 95% ✅
    """
    next_action = state.get("next_action", "NONE")
    
    if next_action == "READY":
        print("✅ Plan ready → executor")
        return "executor"
    elif next_action == "ASK_SLOT":
        print("❓ Need more info → END (response already set)")
        return "end"
    else:
        print("⏹  No clear action → END")
        return "end"

# ================================================================
# BUILD WORKFLOW
# ================================================================

print("="*80)
print("🔧 Building Bot v3 RAG Improved - FULL Pipeline")
print("="*80)

workflow = StateGraph(GraphState)

# Add 4 nodes (REMOVED: collect_user_info - now done at startup)
print("\n📦 Adding nodes:")
workflow.add_node("llm_guardrail", llm_guardrail)
print("  ✅ Node 1: llm_guardrail (LLM-based safety check)")

workflow.add_node("planner", planner_node)
print("  ✅ Node 2: planner (intent detection, slot filling, planning)")

workflow.add_node("executor", executor_node)
print("  ✅ Node 3: executor (tool execution - RAG + Pricing + Quote + Booking)")

workflow.add_node("responder", react_responder_node)
print("  ✅ Node 4: responder (ReACT Universal LLM Intelligence)")

# Define edges
print("\n🔗 Adding edges:")

workflow.set_entry_point("llm_guardrail")
print("  ✅ Entry point: llm_guardrail")

workflow.add_conditional_edges(
    "llm_guardrail",
    route_after_guardrail,
    {
        "planner": "planner",
        "end": END
    }
)
print("  ✅ Conditional: llm_guardrail → [planner | END]")

workflow.add_conditional_edges(
    "planner",
    route_after_planner,
    {
        "executor": "executor",
        "end": END
    }
)
print("  ✅ Conditional: planner → [executor | END]")

workflow.add_edge("executor", "responder")
print("  ✅ Edge: executor → responder")

workflow.add_edge("responder", END)
print("  ✅ Final: responder → END")

# Compile
print("\n⚙️  Compiling graph...")
app = workflow.compile()
print("✅ Bot v3 RAG Improved - Workflow compiled successfully!")

print("\n" + "="*80)
print("📊 WORKFLOW SUMMARY - Bot v3 RAG Improved")
print("="*80)
print("Flow: guardrail → planner → executor → responder → END")
print("(User info collected at startup)")
print("\nNodes: 4")
print("  1. llm_guardrail - Safety check")
print("  2. planner - Intent detection, slot filling, planning")
print("  3. executor - Execute tools")
print("  4. responder - ReACT Universal LLM Intelligence")
print("\n🚀 RAG Pipeline (FULL - All Phases):")
print("  ✅ Phase 2: Multi-Query Expansion (MQE) - 3-5 query variations")
print("  ✅ Phase 3.1: BM25 Search - Keyword matching")
print("  ✅ Phase 3.2: Vector Search - Semantic retrieval")
print("  ✅ Phase 3.3: RRF Fusion - Merge BM25 + Vector rankings")
print("  ✅ Phase 3.4: MMR Diversity - Select 10 diverse chunks (70-100% unique docs)")
print("  ✅ Phase 4: CoVe Verification - Verify all claims")
print("  ✅ Phase 5: Response - Use verified claims only")
print("\n🔧 Available Tools: 4 (all executable)")
print("  ✅ rag_search - Full advanced RAG (MQE → Hybrid → RRF → MMR → CoVe)")
print("  ✅ get_pricing - Price lookup (individual + group, 724 prices)")
print("  ✅ quote_send_email - Quote generation with payment links")
print("  ✅ book_meeting - Schedule virtual meetings")
print("\n📊 Detailed Logging:")
print("  • Each RAG phase logs detailed metrics")
print("  • See: MQE variations, BM25/Vector candidates, RRF fusion, MMR diversity, CoVe claims")
print("  • Full transparency at every step!")
print("="*80)
print()
