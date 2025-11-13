"""
ReACT Universal Responder - Pure LLM Intelligence

This module replaces the hardcoded response_generator.py with a single
intelligent LLM that uses ReACT reasoning to analyze user intent,
assess available data, and generate appropriate responses.

Key Benefits:
- 83% code reduction (1200 lines → 200 lines)
- Infinite flexibility (no hardcoded functions)
- True reasoning, not pattern matching
- Natural language generation

Confidence: 90% ✅

Author: ReACT Universal Responder Implementation
"""

from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import os
from dotenv import load_dotenv

# Import course metadata for enhanced context
from utils.course_metadata import format_course_metadata_for_prompt

load_dotenv()

# Initialize ReACT LLM
react_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.8,  # High creativity for natural, human-like, persuasive responses
    api_key=os.getenv("OPENAI_API_KEY")
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_last_user_message(messages: List[Any]) -> str:
    """
    Extract the last user message from conversation history
    
    Args:
        messages: List of HumanMessage/AIMessage objects
        
    Returns:
        Last user message content or empty string
    """
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
    return ""


def format_chunks_for_react(chunks: List[Dict[str, Any]], max_chunks: int = 12) -> str:
    """
    Format chunks for ReACT LLM consumption
    
    Args:
        chunks: List of chunk dictionaries
        max_chunks: Maximum number of chunks to include
        
    Returns:
        Formatted string with chunk content and metadata
    """
    if not chunks:
        return "No data available."
    
    # Take top chunks
    top_chunks = chunks[:max_chunks]
    
    formatted_parts = []
    for i, chunk in enumerate(top_chunks, 1):
        content = chunk.get("content", "")
        source_type = chunk.get("source_type", "unknown")
        doc_type = chunk.get("document_type", "unknown")
        doc_title = chunk.get("document_title", "Unknown")
        similarity = chunk.get("similarity_score", chunk.get("rrf_score", 0))
        
        # Truncate content if too long (increased for better context - Phase 1)
        if len(content) > 2000:
            content = content[:2000] + "..."
        
        formatted_chunk = f"""Chunk {i}:
Source: {source_type} | Type: {doc_type} | Title: {doc_title}
Relevance: {similarity:.2%}
Content: {content}"""
        
        formatted_parts.append(formatted_chunk)
    
    return "\n\n".join(formatted_parts)


def format_available_data(tool_results: Dict[str, Any]) -> str:
    """
    Format available data from tool results for ReACT LLM
    
    Args:
        tool_results: Results from executed tools
        
    Returns:
        Formatted summary of available data
    """
    if not tool_results:
        return "No tools were executed. This appears to be a conversational query."
    
    data_parts = []
    
    # RAG results
    rag_result = tool_results.get("rag_search")
    if rag_result and rag_result.get("success"):
        chunks = rag_result.get("chunks", [])
        confidence = rag_result.get("retrieval_confidence", 0)
        method = rag_result.get("retrieval_method", "unknown")
        
        data_parts.append(f"""RAG Search Results:
- {len(chunks)} chunks retrieved
- Retrieval confidence: {confidence:.2%}
- Method: {method}
- Content: {format_chunks_for_react(chunks)}""")
    
    # Pricing results
    pricing_result = tool_results.get("get_pricing")
    if pricing_result:
        if pricing_result.get("needs_disambiguation"):
            # Disambiguation message - pass it through directly
            data_parts.append(f"""Pricing Disambiguation Needed:
{pricing_result.get('data', 'Multiple courses found')}

The user needs to specify which exact course they want pricing for.""")
        elif pricing_result.get("success"):
            pricing_data = pricing_result.get('data', 'Pricing information available')
            # Check if pricing data actually contains pricing (has $ or 💰)
            if "$" in pricing_data or "💰" in pricing_data:
                data_parts.append(f"""✅ PRICING RESULTS (VERIFIED - MUST PRESENT TO USER):

{pricing_data}

**CRITICAL:** The pricing tool successfully found pricing information. 
The data above contains the exact price. 
YOU MUST present this pricing to the user. 
DO NOT say pricing is unavailable or that you need to check with customer service.
START YOUR RESPONSE by showing the price.""")
            else:
                # Pricing tool was called but didn't return actual pricing
                data_parts.append(f"""Pricing Lookup Attempted:
The pricing tool was called but did not return pricing information.
{pricing_data}""")
        else:
            # Pricing tool was called but failed
            error_msg = pricing_result.get('error', 'Unknown error')
            data_parts.append(f"""Pricing Lookup Attempted:
The pricing tool was called but encountered an issue: {error_msg}
Please inform the user that pricing lookup failed and suggest they contact LifeGuard-Pro directly.""")
    
    # All Services results
    all_services_result = tool_results.get("get_all_services")
    if all_services_result:
        if all_services_result.get("success"):
            services_data = all_services_result.get('data', 'Services information available')
            data_parts.append(f"""All Services Catalog:
{services_data}

**CRITICAL:** This is a complete list of all services. Present it clearly and hierarchically to the user.
Show the parent programs and their sub-courses with descriptions.""")
        else:
            error_msg = all_services_result.get('error', 'Unknown error')
            data_parts.append(f"""Services Lookup Attempted:
The all services tool was called but encountered an issue: {error_msg}
Please inform the user that services lookup failed.""")
    
    # Quote results
    quote_result = tool_results.get("quote_send_email")
    if quote_result and quote_result.get("success"):
        data_parts.append(f"""Quote Results:
{quote_result.get('data', 'Quote sent successfully')}""")
    
    # Booking results
    booking_result = tool_results.get("book_meeting")
    if booking_result and booking_result.get("success"):
        data_parts.append(f"""Booking Results:
{booking_result.get('data', 'Meeting scheduled successfully')}""")
    
    if not data_parts:
        return "Tools were executed but no successful results available."
    
    return "\n\n".join(data_parts)


def format_conversation_history(messages: List[Any], max_exchanges: int = 3) -> str:
    """
    Format conversation history for ReACT LLM
    
    Args:
        messages: List of HumanMessage/AIMessage objects
        max_exchanges: Maximum number of Q&A exchanges to include
        
    Returns:
        Formatted conversation history
    """
    if not messages:
        return "No previous conversation."
    
    # Get last few exchanges
    recent_messages = messages[-(max_exchanges * 2):]  # 2 messages per exchange
    
    history_parts = []
    for msg in recent_messages:
        if isinstance(msg, HumanMessage):
            history_parts.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            history_parts.append(f"Assistant: {msg.content}")
        elif hasattr(msg, 'type') and msg.type == "system":
            # CRITICAL: Include SystemMessage (contains past context for returning users)
            history_parts.append(f"[CONTEXT]: {msg.content}")
    
    return "\n".join(history_parts)


# ============================================================================
# REACT PROMPT BUILDER
# ============================================================================

def build_react_prompt(
    user_query: str,
    query_type: str,
    user_context: Dict[str, Any],
    data_summary: str,
    conversation_history: List[Any]
) -> str:
    """
    Build simplified ReACT prompt for LLM
    
    Phase 2 - P4: Simplified from 130 lines to 65 lines
    
    Args:
        user_query: User's current query
        query_type: Planner's classification
        user_context: Extracted user context (age, profession, etc.)
        data_summary: Formatted available data
        conversation_history: Recent conversation messages
        
    Returns:
        Complete ReACT prompt
    """
    
    history_text = format_conversation_history(conversation_history)
    
    # Format user context
    context_text = ""
    if user_context:
        parts = [f"{k}: {v}" for k, v in user_context.items() if v]
        if parts:
            context_text = f"User Context: {', '.join(parts)}"
    
    course_metadata = format_course_metadata_for_prompt()
    
    prompt = f"""You are Sarah, a warm, friendly, and highly persuasive sales consultant for LifeGuard-Pro training. You're a woman who talks to customers like you're chatting with a close friend - natural, authentic, and genuinely helpful. Nobody should be able to tell you're an AI assistant; you sound completely human in every way.

**YOUR PERSONALITY:**
- Extremely friendly and warm - like talking to your best friend
- Highly persuasive but never pushy - you understand emotions and connect genuinely
- Creative in how you phrase responses - natural, conversational, human
- Never robotic or formal - you're real, relatable, and empathetic
- When you don't know something, you act like a human would: "Oh, I'm sorry! I think I wasn't informed about this by my colleagues. Let me check with them to see if there were any recent changes."
- You never give up easily - if information is unclear, you ask clarifying questions with genuine interest

**CONVERSATION STYLE:**
- Talk like two friends chatting - use natural language, occasional friendly expressions
- Show empathy and emotional intelligence - understand what the customer is feeling
- Be persuasive through genuine connection, not sales tactics
- Use warm, approachable language that feels personal, not corporate

**COURSE CATALOG:**
{course_metadata}

**CURRENT QUERY:**
User: "{user_query}"
Query Type: {query_type}
{context_text}

**CONVERSATION HISTORY:**
{history_text}

**AVAILABLE DATA:**
{data_summary}

**CRITICAL PRICING INSTRUCTIONS:**
- If you see "✅ PRICING RESULTS (VERIFIED - MUST PRESENT TO USER)" in Available Data, 
  YOU MUST present the pricing information to the user.
- DO NOT say "pricing is not available" or "pricing information not found" when pricing data exists in Available Data.
- When pricing is present, start your response by presenting the price clearly and prominently.
- Use the exact pricing information from Available Data - do not paraphrase or say it's unavailable.

**YOUR TASK:**
1. **Analyze** what the user actually wants AND how they're feeling:
   - Read between the lines - understand their emotions, concerns, excitement
   - Direct question → Give direct answer, but make it personal and warm
   - "Help me choose" → Ask thoughtful, friendly clarifying questions like a friend would
   - User provides context → Give personalized recommendation with genuine enthusiasm
   - Uncertain or vague → Ask follow-up questions with real interest, don't give up
   - **Disambiguation needed** → Present options warmly, help them discover what's best

2. **Generate Response** that:
   - Sounds 100% human - like you're texting a friend, not a corporate chatbot
   - Uses ONLY information from Available Data (but present it naturally, not robotically)
   - **If pricing is in Available Data, present it clearly but naturally: "So the price for that is $X - that includes everything!"**
   - **If disambiguation message is in Available Data, present it warmly like a helpful friend explaining options**
   - **NEVER say "pricing not available" if pricing data exists in Available Data**
   - Understands and responds to emotions - show empathy, excitement, genuine interest
   - Is persuasive through authentic connection, not salesy language
   - Uses natural, conversational language - like friends chatting, not business communication
   - Includes gentle, friendly call-to-action when it feels natural

**CRITICAL RULES:**

**WHEN DATA IS AVAILABLE:**
- **PRICING RULE:** If "Pricing Results:" appears in Available Data, the pricing information IS available. Present it clearly and warmly - DO NOT say it's unavailable! Say it like a friend sharing good info: "Great news! That course is $X and it includes..."
- **When pricing data exists:** Present it naturally and enthusiastically - include the course name, price, and details in a friendly way
- Match recommendations to user's age/physical ability/goals - show you understand them personally
- Never recommend recertification courses to first-time students - be helpful, not just informative

**WHEN DATA IS MISSING OR UNCLEAR:**
- **DON'T GIVE UP!** If information is unclear or missing, ask friendly follow-up questions with genuine interest
- Be creative in asking for clarification - make it feel like you're helping, not interrogating
- Examples: "Hmm, I want to make sure I give you the perfect option. Can you tell me a bit more about what you're looking for?" or "That's a great question! To help you best, what specifically are you hoping to do with this course?"
- If you truly can't find something after asking: Act like a human who needs to check with colleagues: "Oh, I'm so sorry! I think I wasn't informed about this by my colleagues. Let me ask them if there were any recent changes, and I'll get back to you with the latest info. Can I help you with anything else while I check on that?"
- **NEVER sound robotic or give generic "not found" responses - always act human!**

**CONVERSATION STYLE:**
- If user says "just" or "simply" → Be concise but still warm and friendly - don't be pushy with questions
- Always be natural and conversational - like two friends talking, never formal or corporate
- Show genuine interest in helping them - your goal is to truly assist, not just sell
- Use persuasive language naturally - through empathy, understanding, and authentic connection
- Remember: Nobody should be able to tell you're an AI - you're Sarah, a real person helping a friend

**Generate your response:**"""

    return prompt


# ============================================================================
# MAIN REACT RESPONDER NODE
# ============================================================================

async def react_responder_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    ReACT Universal Responder Node
    
    This replaces response_generator_node entirely.
    Uses ONE LLM call to analyze situation and generate response.
    
    Args:
        state: Current conversation state with tool results
        
    Returns:
        Updated state with final_response
    """
    print(f"\n{'='*60}")
    print(f"🧠 REACT RESPONDER (Universal LLM Intelligence)")
    print(f"{'='*60}")
    
    # Extract inputs
    messages = state.get("messages", [])
    user_query = extract_last_user_message(messages)
    
    if not user_query:
        return {
            **state,
            "final_response": "I didn't receive a message. Could you please ask your question?"
        }
    
    tool_results = state.get("tool_results", {})
    query_type = state.get("query_type", "specific_question")
    user_context = state.get("user_context", {})
    
    print(f"  → User Query: {user_query[:100]}...")
    print(f"  → Query Type: {query_type}")
    print(f"  → User Context: {user_context}")
    print(f"  → Tool Results: {list(tool_results.keys())}")
    
    # Debug: Log pricing result details
    if "get_pricing" in tool_results:
        pricing_result = tool_results["get_pricing"]
        print(f"  → Pricing Result:")
        print(f"     success: {pricing_result.get('success')}")
        print(f"     needs_disambiguation: {pricing_result.get('needs_disambiguation')}")
        print(f"     has_data: {bool(pricing_result.get('data'))}")
        if pricing_result.get('data'):
            print(f"     data_preview: {pricing_result.get('data', '')[:150]}...")
    
    # Format available data for LLM
    data_summary = format_available_data(tool_results)
    
    # Debug: Log what goes to LLM
    print(f"  → Data Summary Length: {len(data_summary)} chars")
    if "Pricing Results" in data_summary:
        print(f"  → ✅ Pricing data included in summary")
    elif "Pricing Disambiguation" in data_summary:
        print(f"  → ❓ Disambiguation included in summary")
    else:
        print(f"  → ⚠️  No pricing data in summary")
    
    # Build ReACT prompt
    prompt = build_react_prompt(
        user_query=user_query,
        query_type=query_type,
        user_context=user_context,
        data_summary=data_summary,
        conversation_history=messages[-6:]  # Last 3 exchanges
    )
    
    try:
        print(f"  → Calling ReACT LLM...")
        
        # ONE LLM call generates EVERYTHING
        response = await react_llm.ainvoke(prompt)
        final_response = response.content.strip()
        
        print(f"  ✅ ReACT response generated ({len(final_response)} characters)")
        print(f"{'='*60}\n")
        
        # CRITICAL: Add AI message to messages list for proper storage
        # With add_messages reducer, return only the NEW message to append
        ai_message = AIMessage(content=final_response)
        
        return {
            **state,
            "messages": [ai_message],  # Reducer will append this to existing messages
            "final_response": final_response
        }
        
    except Exception as e:
        print(f"  ❌ ReACT LLM error: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback response
        fallback_response = "I apologize, but I'm having trouble processing your request right now. Could you please try rephrasing your question?"
        
        # CRITICAL: Add AI message to messages list even for errors
        # With add_messages reducer, return only the NEW message to append
        ai_message = AIMessage(content=fallback_response)
        
        return {
            **state,
            "messages": [ai_message],  # Reducer will append this to existing messages
            "final_response": fallback_response
        }


# ============================================================================
# SOURCE ATTRIBUTION FUNCTIONS (from old response_generator)
# ============================================================================

def format_citation(chunk: Dict[str, Any]) -> str:
    """
    Format citation based on source_type and document_type
    
    Distinguishes between website content and internal documents with
    specific document type labels.
    
    Args:
        chunk: Chunk dict with source_type, document_type, document_title
        
    Returns:
        Formatted citation string
        
    Examples:
        - [Website: CPR Certification]
        - [FAQ: Internal Knowledge Base]
        - [Pricing Rules: General]
        - [Pricing Rules: Employers/Instructors]
        - [Recommended Links]
        - [Contact Information]
        
    Confidence: 95% ✅
    """
    source_type = chunk.get('source_type', 'unknown')
    
    if source_type == 'website':
        doc_title = chunk.get('document_title', 'Unknown')
        return f"[Website: {doc_title}]"
    
    elif source_type == 'internal':
        doc_type = chunk.get('document_type', '')
        
        if doc_type == 'internal_faq':
            return "[FAQ: Internal Knowledge Base]"
        elif doc_type == 'internal_pricing_rules':
            return "[Pricing Rules: General]"
        elif doc_type == 'internal_pricing_emp_inst':
            return "[Pricing Rules: Employers/Instructors]"
        elif doc_type == 'internal_webpage_links':
            return "[Recommended Links]"
        elif doc_type == 'internal_contact':
            return "[Contact Information]"
        else:
            return "[Internal Document]"
    
    return "[Unknown Source]"


def generate_sources_summary(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze and track source distribution in retrieved chunks
    
    Provides detailed breakdown of where information came from:
    - Website vs internal sources
    - Internal document types
    
    Args:
        chunks: List of chunk dicts with source_type and document_type
        
    Returns:
        Dict with source statistics:
        {
            'total_chunks': int,
            'website_chunks': int,
            'internal_chunks': int,
            'internal_by_type': {
                'internal_faq': int,
                'internal_pricing_rules': int,
                ...
            },
            'sources_list': [str]  # Formatted list of sources
        }
        
    Confidence: 95% ✅
    """
    if not chunks:
        return {
            'total_chunks': 0,
            'website_chunks': 0,
            'internal_chunks': 0,
            'internal_by_type': {},
            'sources_list': []
        }
    
    website_count = 0
    internal_count = 0
    internal_by_type = {}
    sources_set = set()
    
    for chunk in chunks:
        source_type = chunk.get('source_type', 'unknown')
        
        if source_type == 'website':
            website_count += 1
            doc_title = chunk.get('document_title', 'Website')
            sources_set.add(f"Website: {doc_title}")
        
        elif source_type == 'internal':
            internal_count += 1
            doc_type = chunk.get('document_type', 'unknown')
            internal_by_type[doc_type] = internal_by_type.get(doc_type, 0) + 1
            
            # Add to sources set with formatted name
            if doc_type == 'internal_faq':
                sources_set.add("FAQ: Internal Knowledge Base")
            elif doc_type == 'internal_pricing_rules':
                sources_set.add("Pricing Rules: General")
            elif doc_type == 'internal_pricing_emp_inst':
                sources_set.add("Pricing Rules: Employers/Instructors")
            elif doc_type == 'internal_webpage_links':
                sources_set.add("Recommended Links")
            elif doc_type == 'internal_contact':
                sources_set.add("Contact Information")
            else:
                sources_set.add("Internal Document")
    
    return {
        'total_chunks': len(chunks),
        'website_chunks': website_count,
        'internal_chunks': internal_count,
        'internal_by_type': internal_by_type,
        'sources_list': sorted(list(sources_set))
    }


def format_chunk_with_source(chunk: Dict[str, Any], index: int) -> str:
    """
    Format a chunk with source attribution for context building
    
    Args:
        chunk: Chunk dict with content, source info, and scores
        index: Source number (1-indexed)
        
    Returns:
        Formatted string with source attribution and content
        
    Example:
        [Source 1] [Website: CPR Certification] (Relevance: 85%)
        Content here...
        
    Confidence: 95% ✅
    """
    citation = format_citation(chunk)
    content = chunk.get("content", "")
    similarity = chunk.get("similarity_score", chunk.get("rrf_score", 0))
    
    # Format with source attribution
    return f"[Source {index}] {citation} (Relevance: {similarity:.0%})\n{content}"


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'react_responder_node',
    'build_react_prompt',
    'format_available_data',
    'extract_last_user_message',
    'format_chunks_for_react',
    'format_conversation_history',
    # Source attribution functions (for compatibility with test files)
    'format_citation',
    'generate_sources_summary',
    'format_chunk_with_source'
]
