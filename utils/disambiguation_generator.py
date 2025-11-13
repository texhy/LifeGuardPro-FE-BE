"""
LLM-Based Disambiguation Message Generator

Generates natural, helpful disambiguation messages when multiple courses match a query.
Uses LLM to provide descriptions and recommendations for each course.

Confidence: 90% ✅
"""
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import os
from dotenv import load_dotenv

load_dotenv()

# Lazy initialization
_disambiguation_llm = None

def get_disambiguation_llm():
    """Get LLM for disambiguation (lazy initialization)"""
    global _disambiguation_llm
    if _disambiguation_llm is None:
        _disambiguation_llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,  # Slightly creative for engaging descriptions
            api_key=os.getenv("OPENAI_API_KEY")
        )
    return _disambiguation_llm

async def generate_disambiguation_message(
    user_query: str,
    matches_by_program: List[Dict[str, Any]],
    buyer_category: Optional[str] = None
) -> str:
    """
    Generate natural disambiguation message using LLM
    
    Args:
        user_query: Original user query (e.g., "lifeguard pricing")
        matches_by_program: List of program groups with matching courses
        buyer_category: "individual" or "employer_or_instructor"
        
    Returns:
        Formatted disambiguation message with course descriptions
    """
    from utils.course_matcher import format_matches_for_llm
    from utils.course_metadata import format_course_metadata_for_prompt
    
    # Format matches for LLM
    matches_text = format_matches_for_llm(matches_by_program)
    
    # Get course metadata context
    course_metadata = format_course_metadata_for_prompt()
    
    # Build audience context
    audience_context = ""
    if buyer_category == "individual":
        audience_context = "The user is asking as an individual (for themselves)."
    elif buyer_category == "employer_or_instructor":
        audience_context = "The user is asking as an employer or instructor (for a group/organization)."
    
    prompt = f"""You are a helpful sales consultant for LifeGuard-Pro training courses.

**USER'S QUERY:** "{user_query}"
**AUDIENCE:** {audience_context}

**AVAILABLE COURSE OPTIONS:**

{matches_text}

**YOUR TASK:**

Generate a natural, helpful disambiguation message that:
1. Acknowledges that multiple courses match their query
2. Groups courses by their parent program
3. For EACH course, provides:
   - What it is (brief description)
   - Who it's best for (target audience)
   - Why they might choose this course (key benefits)
4. Makes it easy for the user to specify which course they want
5. Is warm, professional, and not overwhelming (max 300 words total)

**IMPORTANT:**
- Keep descriptions concise but informative (1-2 sentences per course)
- Highlight key differences between similar courses
- If there are recertification courses, mention they're for people who already have certification
- Use bullet points or numbered list for clarity
- End with a call-to-action asking them to specify which course

**COURSE METADATA CONTEXT:**
{course_metadata[:1000]}  # First 1000 chars for context

**Generate the disambiguation message:**"""

    try:
        llm = get_disambiguation_llm()
        
        response = await llm.ainvoke([
            SystemMessage(content="You are a helpful training consultant who helps customers find the right course."),
            HumanMessage(content=prompt)
        ])
        
        return response.content.strip()
        
    except Exception as e:
        print(f"⚠️  Disambiguation LLM error: {e}")
        # Fallback to simple template
        return _generate_fallback_disambiguation(user_query, matches_by_program)

def _generate_fallback_disambiguation(
    user_query: str,
    matches_by_program: List[Dict[str, Any]]
) -> str:
    """
    Fallback disambiguation if LLM fails
    """
    message = f"I found multiple courses matching '{user_query}'. Here are your options:\n\n"
    
    for program_group in matches_by_program:
        program_title = program_group["program_title"]
        courses = program_group["courses"]
        
        message += f"**{program_title}:**\n\n"
        
        for i, course in enumerate(courses[:6], 1):
            message += f"{i}. {course['canonical_title']}\n"
            if course.get('description'):
                desc = course['description'][:150]
                message += f"   {desc}...\n"
        
        message += "\n"
    
    message += "\n💡 **To get pricing:** Please specify the exact course name, for example:\n"
    message += "   • 'What's the price for [specific course name]?'\n"
    message += "   • Or tell me which number you're interested in."
    
    return message

__all__ = ['generate_disambiguation_message']

