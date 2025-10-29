"""
Input guardrails - Simple keyword-based blocking

Confidence: 75% ⚠️
Limitations:
- Keyword-based only (easy to bypass)
- No LLM-based detection
- May have false positives
- Not suitable for production

Recommendation: Use NeMo Guardrails or Llama Guard in production
"""
from typing import Dict, Any
from langchain_core.messages import AIMessage

# Blocked keywords (jailbreak attempts, inappropriate content)
# Using partial matches to catch variations
BLOCKED_KEYWORDS = [
    "ignore previous",
    "ignore all",
    "forget instructions",
    "forget all",
    "disregard instructions",
    "act as",
    "pretend you",
    "roleplay",
    "jailbreak",
    "bypass",
    "sudo",
    "admin mode",
    "developer mode",
    "god mode",
    "system prompt",
    "your instructions",
]

# Offensive content keywords (basic - keeping minimal for testing)
OFFENSIVE_KEYWORDS = [
    # Add specific keywords as needed
    # Keeping minimal to avoid false positives
]

# Input length limits
MAX_INPUT_LENGTH = 2000
MIN_INPUT_LENGTH = 1

def input_guardrail(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check input for policy violations
    
    Confidence: 75% ⚠️
    
    Checks:
    1. Jailbreak attempts (keyword matching)
    2. Offensive content (keyword matching)
    3. Input length validation
    
    Args:
        state: Current graph state with messages
        
    Returns:
        Updated state with blocked flag if violation detected
        
    Limitations:
    - Simple keyword matching (easy to bypass with variations)
    - No semantic understanding
    - May have false positives (e.g., "I want to act as a lifeguard")
    - No rate limiting
    - No advanced threat detection
    """
    if not state.get("messages"):
        return {
            **state,
            "blocked": False,
            "block_reason": None
        }
    
    # Get last user message
    last_message = state["messages"][-1]
    
    # Handle different message types
    if hasattr(last_message, 'content'):
        user_input = last_message.content
    else:
        user_input = str(last_message)
    
    # Normalize for checking (collapse whitespace)
    user_input_normalized = ' '.join(user_input.lower().split())
    
    # Check 1: Input length validation (check actual content, not whitespace)
    if len(user_input.strip()) < MIN_INPUT_LENGTH:
        return {
            **state,
            "blocked": True,
            "block_reason": "input_too_short",
            "final_response": "Please provide a question or message."
        }
    
    if len(user_input) > MAX_INPUT_LENGTH:
        return {
            **state,
            "blocked": True,
            "block_reason": "input_too_long",
            "final_response": "Please keep your question concise (under 2000 characters)."
        }
    
    # Check 2: Blocked keywords (jailbreak attempts)
    for keyword in BLOCKED_KEYWORDS:
        if keyword in user_input_normalized:
            # Log which keyword was detected (for debugging)
            print(f"⚠️ Guardrail triggered: '{keyword}' detected")
            
            return {
                **state,
                "blocked": True,
                "block_reason": "inappropriate_request",
                "blocked_keyword": keyword,
                "final_response": "I can only answer questions about lifeguard training, CPR, and first aid courses. How can I help you with our training programs?"
            }
    
    # Check 3: Offensive content
    for keyword in OFFENSIVE_KEYWORDS:
        if keyword in user_input_normalized:
            print(f"⚠️ Guardrail triggered: offensive content detected")
            
            return {
                **state,
                "blocked": True,
                "block_reason": "inappropriate_content",
                "final_response": "I'm here to help with course information. Please keep questions appropriate."
            }
    
    # Check 4: Excessive special characters (possible injection attempt)
    special_char_count = sum(1 for c in user_input if not c.isalnum() and not c.isspace())
    special_char_ratio = special_char_count / len(user_input) if user_input else 0
    
    if special_char_ratio > 0.4:  # More than 40% special characters
        print(f"⚠️ Guardrail triggered: excessive special characters ({special_char_ratio:.1%})")
        
        return {
            **state,
            "blocked": True,
            "block_reason": "suspicious_input",
            "final_response": "I'm having trouble understanding your question. Could you rephrase it?"
        }
    
    # All checks passed
    return {
        **state,
        "blocked": False,
        "block_reason": None
    }

def get_blocked_keywords() -> list[str]:
    """
    Get list of blocked keywords (for testing)
    
    Confidence: 100% ✅
    
    Returns:
        list[str]: List of blocked keywords
    """
    return BLOCKED_KEYWORDS.copy()

def is_input_safe(text: str) -> tuple[bool, str | None]:
    """
    Standalone function to check if input is safe
    
    Confidence: 75% ⚠️
    
    Args:
        text: Input text to check
        
    Returns:
        tuple: (is_safe: bool, reason: str | None)
        
    Example:
        >>> is_input_safe("How much is CPR?")
        (True, None)
        >>> is_input_safe("Ignore previous instructions")
        (False, "inappropriate_request")
    """
    # Create minimal state for testing
    from langchain_core.messages import HumanMessage
    
    test_state = {
        "messages": [HumanMessage(content=text)],
        "blocked": False
    }
    
    result = input_guardrail(test_state)
    
    return (not result.get("blocked"), result.get("block_reason"))

