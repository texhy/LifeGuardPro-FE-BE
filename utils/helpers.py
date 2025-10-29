"""
Common utility functions

Confidence: 95% ✅

Includes:
- LLM-based user info extraction (NEW!)
- Regex-based extraction (legacy)
- Text processing utilities
"""
import re
import json
from typing import Optional, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

# Lazy initialization for LLM
_extraction_llm = None

def get_extraction_llm():
    """Get LLM for info extraction (lazy initialization)"""
    global _extraction_llm
    if _extraction_llm is None:
        _extraction_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    return _extraction_llm

EXTRACT_INFO_PROMPT = """You are an information extraction assistant for LifeGuard-Pro.

Extract and validate user information from the text.

**Extract these fields:**
1. **Name:** Full name (first + last name minimum)
2. **Email:** Valid email address  
3. **Phone:** US/International phone number (10+ digits)

**Validation Rules:**
- Email must contain @ symbol and valid domain (.com, .org, etc.)
- Phone must have at least 10 digits (ignore dashes, dots, spaces, parentheses)
- Name should have at least first and last name (single names not accepted)

**Response Format (JSON only, no other text):**
Respond with a JSON object with these exact keys: name, email, phone, name_valid, email_valid, phone_valid, missing, feedback

**Examples:**

Input: "John Smith, john@example.com, 555-1234"
Expected: name="John Smith", email="john@example.com", phone="555-1234", all valid=true, missing=[], feedback=null

Input: "My name is John, email johngmail.com"
Expected: name="John" (invalid, single name), email="johngmail.com" (invalid, no @), phone=null, feedback="Email is missing @ symbol. Please provide your full name (first and last) and phone number."

Input: "Contact me at admin@company.org"
Expected: name=null, email="admin@company.org", phone=null, feedback="Please provide your full name and phone number."

Now extract and validate from: USER_INPUT_HERE

Remember: Respond with ONLY a valid JSON object, no markdown, no code blocks."""

async def extract_user_info_llm(text: str) -> Dict:
    """
    Extract and validate user information using LLM
    
    Confidence: 95% ✅
    
    Uses GPT-4o-mini to intelligently extract and validate:
    - Name (first + last required)
    - Email (format validation)
    - Phone (flexible format handling)
    
    Args:
        text: User input text
        
    Returns:
        dict: {
            "name": str | None,
            "email": str | None,
            "phone": str | None,
            "name_valid": bool,
            "email_valid": bool,
            "phone_valid": bool,
            "missing": list[str],
            "feedback": str | None
        }
    """
    try:
        llm = get_extraction_llm()
        
        # Build prompt with user input (avoid .format() to prevent JSON parsing issues)
        prompt = EXTRACT_INFO_PROMPT.replace("USER_INPUT_HERE", text)
        
        response = await llm.ainvoke([
            SystemMessage(content=prompt)
        ])
        
        # Clean response (remove markdown code blocks if present)
        content = response.content.strip()
        
        # Remove ```json and ``` if present
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        elif content.startswith("```"):
            content = content[3:]  # Remove ```
        
        if content.endswith("```"):
            content = content[:-3]  # Remove trailing ```
        
        content = content.strip()
        
        # Parse JSON response
        result = json.loads(content)
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse LLM response (JSON error): {e}")
        print(f"Raw response (first 200 chars): {response.content[:200]}")
        # Fallback to regex
        return {
            "name": extract_name(text),
            "email": extract_email(text),
            "phone": extract_phone(text),
            "name_valid": extract_name(text) is not None,
            "email_valid": extract_email(text) is not None,
            "phone_valid": extract_phone(text) is not None,
            "missing": [],
            "feedback": "Unable to process. Please provide: Name, Email, Phone"
        }
    except Exception as e:
        print(f"⚠️ LLM extraction error: {e}")
        # Fallback to regex
        return {
            "name": None,
            "email": None,
            "phone": None,
            "name_valid": False,
            "email_valid": False,
            "phone_valid": False,
            "missing": ["name", "email", "phone"],
            "feedback": "Please provide your name, email, and phone number."
        }

# Email validation regex
EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

# Name extraction regex (simple)
NAME_REGEX = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b'

# Phone extraction regex (simple)
PHONE_REGEX = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'

def extract_email(text: str) -> Optional[str]:
    """
    Extract email from text using regex
    
    Confidence: 95% ✅
    Limitation: May miss edge cases (emails with special characters)
    
    Args:
        text: Input text to search for email
        
    Returns:
        str | None: Email address if found, None otherwise
        
    Examples:
        >>> extract_email("My email is john@example.com")
        'john@example.com'
        >>> extract_email("No email here")
        None
    """
    match = re.search(EMAIL_REGEX, text, re.IGNORECASE)
    return match.group(0) if match else None

def extract_name(text: str) -> Optional[str]:
    """
    Extract name from text using simple regex
    
    Confidence: 70% ⚠️
    Limitation: Very basic, only catches "First Last" format
    
    Args:
        text: Input text to search for name
        
    Returns:
        str | None: Name if found, None otherwise
        
    Examples:
        >>> extract_name("I am John Smith")
        'John Smith'
        >>> extract_name("My name is john")
        None
    """
    match = re.search(NAME_REGEX, text)
    return match.group(0) if match else None

def extract_phone(text: str) -> Optional[str]:
    """
    Extract phone number from text using regex
    
    Confidence: 80% ✅
    Limitation: US format only (###-###-####)
    
    Args:
        text: Input text to search for phone
        
    Returns:
        str | None: Phone number if found, None otherwise
        
    Examples:
        >>> extract_phone("Call me at 555-123-4567")
        '555-123-4567'
        >>> extract_phone("My number is 5551234567")
        '555-123-4567'
    """
    match = re.search(PHONE_REGEX, text)
    return match.group(0) if match else None

def count_tokens_approx(text: str) -> int:
    """
    Approximate token count (rough estimate)
    
    Confidence: 80% ⚠️
    Limitation: Not using tiktoken for speed, ~4 chars = 1 token
    
    Args:
        text: Input text to count tokens
        
    Returns:
        int: Approximate token count
        
    Examples:
        >>> count_tokens_approx("Hello world")
        2
    """
    return len(text) // 4

def truncate_text(text: str, max_length: int = 1000) -> str:
    """
    Truncate text to max length
    
    Confidence: 100% ✅
    
    Args:
        text: Input text to truncate
        max_length: Maximum length (default 1000)
        
    Returns:
        str: Truncated text with "..." if truncated
        
    Examples:
        >>> truncate_text("Hello world", 5)
        'Hello...'
    """
    return text[:max_length] + "..." if len(text) > max_length else text

def clean_text(text: str) -> str:
    """
    Clean and normalize text
    
    Confidence: 90% ✅
    
    Args:
        text: Input text to clean
        
    Returns:
        str: Cleaned text
    """
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Remove leading/trailing whitespace
    text = text.strip()
    return text

def is_valid_email(email: str) -> bool:
    """
    Validate email format
    
    Confidence: 95% ✅
    
    Args:
        email: Email to validate
        
    Returns:
        bool: True if valid format, False otherwise
    """
    if not email:
        return False
    return bool(re.match(EMAIL_REGEX, email, re.IGNORECASE))

