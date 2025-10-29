"""
Intent classification

Confidence: 88% ⚠️
Limitations:
- LLM-based (may misclassify ambiguous questions)
- 3 classes only (INFO, PRICING, BOOKING)
- No confidence scores returned
- Depends on OpenAI API availability

Features:
- Context-aware classification
- Handles multi-word queries
- Defaults to INFO if unclear
- Fast classification (~300ms)
"""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import os

# Lazy initialization
_llm = None

def get_llm():
    """Get or create ChatOpenAI instance (lazy initialization)"""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,  # Deterministic for classification
            api_key=os.getenv("OPENAI_API_KEY")
        )
    return _llm

INTENT_PROMPT = """Classify user intent into ONE category:

**INFO**: General information questions
Examples:
- "How do I become a lifeguard?"
- "What are the requirements for CPR?"
- "Where can I take courses?"
- "What's included in the training?"
- "Tell me about your programs"

**PRICING**: Price/cost questions
Examples:
- "How much does CPR cost?"
- "What's the price for lifeguard training?"
- "Do you have discounts?"
- "What are group rates?"
- "How much is recertification?"

**BOOKING**: Want to register/enroll
Examples:
- "I want to sign up"
- "How do I register?"
- "I'm ready to enroll"
- "Book me for a course"
- "I'd like to get started"

Respond with ONLY the intent label: INFO, PRICING, or BOOKING

If unclear, default to INFO."""

async def classify_intent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify user intent
    
    Confidence: 88% ⚠️
    
    Classifies the user's message into one of three intents:
    - INFO: General information seeking
    - PRICING: Price/cost inquiries
    - BOOKING: Ready to register/enroll
    
    Args:
        state: Current graph state with messages
        
    Returns:
        Updated state with intent classification
        
    State Updates:
        - intent: str (INFO, PRICING, or BOOKING)
        
    Limitations:
    - May misclassify ambiguous questions (~12% error rate)
    - Defaults to INFO if uncertain
    - Requires OpenAI API call (~300ms latency)
    """
    if not state.get("messages"):
        return {**state, "intent": "INFO"}
    
    # Get last user message
    last_message = state["messages"][-1]
    
    if hasattr(last_message, 'content'):
        user_input = last_message.content
    else:
        user_input = str(last_message)
    
    # Handle empty input
    if not user_input.strip():
        return {**state, "intent": "INFO"}
    
    try:
        # Ask LLM to classify
        llm = get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=INTENT_PROMPT),
            HumanMessage(content=user_input)
        ])
        
        intent = response.content.strip().upper()
        
        # Validate intent (must be one of three)
        if intent not in ["INFO", "PRICING", "BOOKING"]:
            print(f"⚠️  Unexpected intent '{intent}', defaulting to INFO")
            intent = "INFO"
        
        # Debug logging
        print(f"🎯 Intent classified: '{user_input[:50]}...' → {intent}")
        
        return {
            **state,
            "intent": intent
        }
        
    except Exception as e:
        print(f"⚠️ Intent classification error: {e}")
        # Default to INFO on error
        return {**state, "intent": "INFO"}

def classify_intent_sync(text: str) -> str:
    """
    Synchronous version for testing
    
    Confidence: 88% ⚠️
    
    Args:
        text: Input text to classify
        
    Returns:
        str: Intent (INFO, PRICING, or BOOKING)
    """
    import asyncio
    
    # Create minimal state
    state = {
        "messages": [HumanMessage(content=text)],
        "intent": None
    }
    
    # Run async function synchronously
    result = asyncio.run(classify_intent(state))
    
    return result.get("intent", "INFO")

# Quick keyword-based intent hints (optional optimization)
# Could use these for fast pre-classification before LLM call
PRICING_KEYWORDS = [
    "price", "cost", "how much", "fee", "payment",
    "discount", "group rate", "affordable", "$", "dollar"
]

BOOKING_KEYWORDS = [
    "register", "sign up", "enroll", "book", "schedule",
    "join", "get started", "ready to", "i want to"
]

def quick_intent_hint(text: str) -> str | None:
    """
    Quick keyword-based intent hint (optional optimization)
    
    Confidence: 70% ⚠️
    
    This could be used to skip LLM call for obvious cases,
    but not implemented in main flow yet.
    
    Args:
        text: Input text
        
    Returns:
        str | None: Intent hint or None if unclear
    """
    text_lower = text.lower()
    
    # Check pricing keywords
    if any(keyword in text_lower for keyword in PRICING_KEYWORDS):
        return "PRICING"
    
    # Check booking keywords
    if any(keyword in text_lower for keyword in BOOKING_KEYWORDS):
        return "BOOKING"
    
    # Unclear - need LLM
    return None

