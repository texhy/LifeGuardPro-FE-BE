"""
LLM refinement - Generate response with context

Confidence: 90% ✅
Limitations:
- GPT-4o-mini only (faster but less capable than GPT-4o)
- No streaming (full response only)
- Fixed system prompt (not adaptive)
- Last 10 messages only (context window management)

Features:
- Multi-turn conversation support
- RAG context integration
- User personalization (name/email)
- Intent-aware responses
- Source citation
- Off-topic handling
"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import os

# Lazy initialization
_llm = None

def get_llm():
    """
    Get or create ChatOpenAI instance (lazy initialization)
    
    Confidence: 98% ✅
    """
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,  # Slightly creative for natural responses
            api_key=os.getenv("OPENAI_API_KEY")
        )
    return _llm

def build_system_prompt(state: Dict[str, Any]) -> str:
    """
    Build system prompt with context
    
    Confidence: 95% ✅
    
    Args:
        state: Current graph state
        
    Returns:
        str: Complete system prompt with RAG context, user info, and intent guidance
    """
    base_prompt = """You are a helpful assistant for LifeGuard-Pro, a lifeguard and CPR training company.

Your role:
- Answer questions about our courses clearly and professionally
- Be helpful, friendly, and concise
- If you don't know something, say so honestly
- Encourage users to visit our website for booking

Guidelines:
- Keep responses under 200 words unless more detail is needed
- Cite sources when using provided context
- Be encouraging about water safety training
- Use a professional but friendly tone"""
    
    # Add RAG context if available
    if state.get("rag_context"):
        base_prompt += f"\n\n=== RELEVANT INFORMATION ===\n{state['rag_context']}\n\nUse this information to answer the user's question accurately."
    
    # Add user info if available (personalization)
    if state.get("user_email"):
        name = state.get("user_name", "there")
        base_prompt += f"\n\nUser's name: {name}\nUser's email: {state['user_email']}"
        base_prompt += "\nPersonalize your response using their name when appropriate."
    
    # Add intent-specific guidance
    intent = state.get("intent", "INFO")
    if intent == "PRICING":
        base_prompt += "\n\n💰 PRICING QUERY: Focus on pricing information. Mention checking our pricing page for detailed rates. Be clear about what's included in courses."
    elif intent == "BOOKING":
        base_prompt += "\n\n📝 BOOKING REQUEST: Guide the user through the registration process. Provide clear next steps. Mention our registration page or contact information."
    elif intent == "INFO":
        base_prompt += "\n\nℹ️ INFORMATION QUERY: Provide comprehensive educational information. Be thorough but concise."
    
    return base_prompt

async def llm_refine(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate final response
    
    Confidence: 90% ✅
    
    This is the main response generation node that:
    1. Handles off-topic requests
    2. Builds context from RAG results
    3. Personalizes with user info
    4. Maintains multi-turn conversation
    5. Generates natural language response
    6. Adds source citations
    
    Args:
        state: Current graph state with context
        
    Returns:
        Updated state with final response
        
    State Updates:
        - messages: Appends AI response
        - final_response: str (the actual response text)
    """
    if not state.get("messages"):
        return state
    
    # Handle blocked input (from guardrails)
    if state.get("blocked"):
        # Response already set by guardrails
        return state
    
    # Handle off-topic requests
    if not state.get("on_topic", True):
        off_topic_response = AIMessage(
            content="I'm here to help with LifeGuard-Pro's aquatic safety and training services! 🏊\n\n"
                   "**I can assist with:**\n"
                   "• Lifeguard certification (pool, waterfront, water park)\n"
                   "• CPR & First Aid training\n"
                   "• Water safety & swimming instruction\n"
                   "• Pool operator (CPO) certification\n"
                   "• Course pricing, locations, and schedules\n"
                   "• Career opportunities and requirements\n\n"
                   "**Try asking:**\n"
                   "• \"How do I become a lifeguard?\"\n"
                   "• \"What CPR courses do you offer?\"\n"
                   "• \"How much is lifeguard training?\"\n"
                   "• \"Where can I take courses in [your state]?\"\n\n"
                   "What would you like to know about our training programs?"
        )
        
        print("🚫 Off-topic query - providing helpful redirection")
        
        return {
            **state,
            "messages": state["messages"] + [off_topic_response],
            "final_response": off_topic_response.content
        }
    
    # Build conversation history (multi-turn context!)
    conversation = []
    
    # Add system prompt with all context
    system_prompt = build_system_prompt(state)
    conversation.append(SystemMessage(content=system_prompt))
    
    # Add message history (last 10 messages for context window management)
    # This enables multi-turn conversation!
    recent_messages = state["messages"][-10:]
    for msg in recent_messages:
        if hasattr(msg, 'type'):
            if msg.type == "human":
                conversation.append(HumanMessage(content=msg.content))
            elif msg.type == "ai":
                conversation.append(AIMessage(content=msg.content))
        elif isinstance(msg, HumanMessage):
            conversation.append(msg)
        elif isinstance(msg, AIMessage):
            conversation.append(msg)
    
    try:
        # Generate response with LLM
        llm = get_llm()
        
        print(f"🤖 Generating response (Intent: {state.get('intent', 'INFO')})...")
        
        response = await llm.ainvoke(conversation)
        
        # Build final response text
        response_text = response.content
        
        # Add sources if available
        if state.get("rag_sources") and len(state["rag_sources"]) > 0:
            sources_text = "\n\n📚 **Sources:**\n" + "\n".join([
                f"{i+1}. {s['title'] or s['url']}"
                for i, s in enumerate(state["rag_sources"][:3])
            ])
            response_text += sources_text
        
        ai_message = AIMessage(content=response_text)
        
        print(f"✅ Response generated ({len(response_text)} chars)")
        
        return {
            **state,
            "messages": state["messages"] + [ai_message],
            "final_response": response_text
        }
        
    except Exception as e:
        print(f"❌ LLM refinement error: {e}")
        import traceback
        traceback.print_exc()
        
        # Provide fallback response
        error_response = AIMessage(
            content="I'm having trouble generating a response right now. Please try again in a moment."
        )
        
        return {
            **state,
            "messages": state["messages"] + [error_response],
            "final_response": error_response.content,
            "llm_error": str(e)
        }

def format_response_with_sources(response: str, sources: list) -> str:
    """
    Format response with source citations
    
    Confidence: 95% ✅
    
    Args:
        response: LLM-generated response
        sources: List of source metadata
        
    Returns:
        str: Formatted response with citations
    """
    if not sources:
        return response
    
    sources_text = "\n\n📚 **Sources:**\n" + "\n".join([
        f"{i+1}. {s.get('title') or s.get('url')}"
        for i, s in enumerate(sources[:3])
    ])
    
    return response + sources_text

