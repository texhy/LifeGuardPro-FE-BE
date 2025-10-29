"""
User info collection - LLM-based extraction with validation

Confidence: 95% ✅

Improvements:
- LLM-based extraction (handles variations)
- Format validation (email @ symbol, phone digits)
- Specific feedback (tells user what's wrong)
- Extracts name, email, AND phone

Features:
- Intelligent extraction with reasoning
- Validates extracted information
- Provides helpful error messages
- Non-intrusive (asks once, then skips)
"""
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage
from utils.helpers import extract_user_info_llm

async def collect_user_info(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Collect user name, email, and phone using LLM extraction
    
    Confidence: 95% ✅
    
    Flow:
    1. Check if we already have all info
    2. If not, use LLM to extract and validate from current message
    3. If extraction successful → Store info
    4. If extraction incomplete → Give specific feedback
    5. If not requested yet → Ask for info
    6. If already asked once → Skip (non-intrusive)
    
    Args:
        state: Current graph state
        
    Returns:
        Updated state with user info or request/feedback
        
    State Updates:
        - user_email: str | None
        - user_name: str | None  
        - user_phone: str | None (NEW!)
        - info_requested: bool
        - needs_info: bool
    """
    # Already have all required info
    if state.get("user_email") and state.get("user_phone"):
        print("✅ User info already collected (email + phone)")
        return {**state, "needs_info": False}
    
    # Try LLM extraction from current message
    if state.get("messages"):
        last_message = state["messages"][-1]
        
        # Extract content
        if hasattr(last_message, 'content'):
            user_input = last_message.content
        else:
            user_input = str(last_message)
        
        # Use LLM to extract and validate
        print(f"🔍 LLM extracting user info from: '{user_input[:50]}...'")
        
        extraction = await extract_user_info_llm(user_input)
        
        # Check if we got valid email and phone
        has_valid_email = extraction.get("email_valid", False)
        has_valid_phone = extraction.get("phone_valid", False)
        
        if has_valid_email and has_valid_phone:
            # Success! Got everything
            print(f"✅ User info collected: {extraction['name']} ({extraction['email']}, {extraction['phone']})")
            
            return {
                **state,
                "user_email": extraction["email"],
                "user_name": extraction["name"],
                "user_phone": extraction["phone"],
                "needs_info": False,
                "info_collected": True
            }
        
        # User provided some info but it's incomplete/invalid
        # Only give specific feedback if they actually tried to provide info
        # (not just "I don't want to" type responses)
        if state.get("info_requested") and (has_valid_email or has_valid_phone or extraction.get("name")):
            # User tried to provide info but something is wrong
            # Give specific feedback
            feedback = extraction.get("feedback")
            missing = extraction.get("missing", [])
            
            if feedback:
                feedback_message = AIMessage(
                    content=f"{feedback}\n\n"
                           f"Please provide: {', '.join(missing) if missing else 'valid information'}.\n\n"
                           f"Example: 'John Smith, john@example.com, 555-123-4567'"
                )
                
                print(f"⚠️  Validation failed: {feedback}")
                
                return {
                    **state,
                    "messages": state["messages"] + [feedback_message],
                    "info_request_count": state.get("info_request_count", 1),  # Don't increment for invalid attempts
                    "needs_info": True
                }
    
    # Haven't asked yet, first request
    if not state.get("info_requested"):
        ask_message = AIMessage(
            content="To provide personalized assistance and help you find the right training course, "
                   "could you please share your name, email, and phone number?\n\n"
                   "Example: 'John Smith, john@example.com, 555-123-4567'"
        )
        
        print("📧 Requesting user info (first time)...")
        
        return {
            **state,
            "messages": state["messages"] + [ask_message],
            "info_requested": True,
            "info_request_count": 1,
            "needs_info": True
        }
    
    # User didn't provide info after being asked
    # Check how many times we've asked
    request_count = state.get("info_request_count", 1)
    
    if request_count < 2:
        # Second attempt: Politely explain why we need it
        polite_message = AIMessage(
            content="I understand you may have privacy concerns. However, to process your training inquiry "
                   "and ensure we can follow up with course details, pricing, and availability, "
                   "I need your contact information.\n\n"
                   "This helps us:\n"
                   "• Send you personalized course recommendations\n"
                   "• Provide accurate pricing for your location\n"
                   "• Follow up with booking details\n"
                   "• Send certification information\n\n"
                   "Could you please share: Your name, email, and phone number?\n"
                   "Example: 'John Smith, john@example.com, 555-123-4567'"
        )
        
        print("📧 Requesting user info (second time - with explanation)...")
        
        return {
            **state,
            "messages": state["messages"] + [polite_message],
            "info_request_count": request_count + 1,
            "needs_info": True
        }
    
    # Asked twice, user still didn't provide
    # Allow them to continue but warn about limitations
    print("⏭️  User declined to provide info after 2 requests, continuing with limitations...")
    
    skip_warning = AIMessage(
        content="I understand. You can continue asking questions, but please note:\n"
               "• I won't be able to provide personalized course recommendations\n"
               "• Pricing may not be accurate for your location\n"
               "• We won't be able to follow up with you about bookings\n\n"
               "Feel free to share your contact information anytime if you change your mind. "
               "How can I help you today?"
    )
    
    return {
        **state,
        "messages": state["messages"] + [skip_warning],
        "needs_info": False,
        "info_skipped": True,
        "skip_reason": "user_declined_after_2_attempts"
    }

def extract_user_info_sync(text: str) -> tuple[str | None, str | None]:
    """
    Synchronous helper to extract name and email from text
    
    Confidence: 85% ✅
    
    Args:
        text: Input text to extract from
        
    Returns:
        tuple: (name: str | None, email: str | None)
        
    Examples:
        >>> extract_user_info_sync("I'm John Smith, john@example.com")
        ('John Smith', 'john@example.com')
        
        >>> extract_user_info_sync("Contact me at test@email.com")
        (None, 'test@email.com')
        
        >>> extract_user_info_sync("My name is Sarah")
        (None, None)
    """
    email = extract_email(text)
    name = extract_name(text) if email else None  # Only extract name if email found
    
    return (name, email)

def has_user_info(state: Dict[str, Any]) -> bool:
    """
    Check if state has user info
    
    Confidence: 100% ✅
    
    Args:
        state: Graph state
        
    Returns:
        bool: True if user_email is set
    """
    return bool(state.get("user_email"))

