"""
Claim Extractor - Extract atomic claims from LLM response

An "atomic claim" is a single, verifiable statement.

Examples:
- Good: "CPO is a certification for pool operators"
- Bad: "CPO is a certification for pool operators that covers chemistry, 
        safety, and operations" (too many facts)

Confidence: 85% ✅

Author: Phase 4 (Stage 4.1) Implementation
"""

from langchain_openai import ChatOpenAI
from typing import List, Dict, Any
import os
import json
from collections import Counter

# Initialize LLM for claim extraction
# Use gpt-4o-mini for faster, cheaper extraction
claim_extractor_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,  # Deterministic
    api_key=os.getenv("OPENAI_API_KEY")
)


async def extract_claims(response_text: str) -> List[Dict[str, Any]]:
    """
    Extract atomic claims from response text
    
    Each claim should be:
    - Atomic (one fact only)
    - Verifiable (can check against source)
    - Complete (contains subject and predicate)
    
    Args:
        response_text: Draft response from LLM
        
    Returns:
        [
            {
                "claim": "CPO is a certification for pool operators",
                "claim_id": "claim_1",
                "category": "definition"
            },
            {
                "claim": "CPO certification covers pool chemistry",
                "claim_id": "claim_2",
                "category": "content"
            },
            ...
        ]
        
    Confidence: 85% ✅
    """
    print(f"        📝 Extracting claims from response...")
    
    prompt = f"""Extract all verifiable claims from this response.

**RULES FOR ATOMIC CLAIMS:**
1. Each claim must be ATOMIC (contain exactly ONE fact)
2. Each claim must be VERIFIABLE (can be checked against source text)
3. Break compound statements into SEPARATE claims
4. Include ALL claims (don't skip any information)
5. Each claim should be a complete sentence

**CLAIM CATEGORIES:**
- "definition": Defines what something is
- "content": Describes course content, curriculum
- "requirement": Prerequisites, requirements
- "pricing": Cost, price information
- "availability": Locations, dates, schedule
- "process": How to do something
- "general": Other information

**EXAMPLES:**

Response: "CPO is a certification for pool operators that covers chemistry and safety."
Claims:
[
  {{"claim": "CPO is a certification for pool operators", "claim_id": "claim_1", "category": "definition"}},
  {{"claim": "CPO certification covers chemistry", "claim_id": "claim_2", "category": "content"}},
  {{"claim": "CPO certification covers safety", "claim_id": "claim_3", "category": "content"}}
]

Response: "The course costs $499 and includes online materials."
Claims:
[
  {{"claim": "The course costs $499", "claim_id": "claim_1", "category": "pricing"}},
  {{"claim": "The course includes online materials", "claim_id": "claim_2", "category": "content"}}
]

**NOW EXTRACT FROM THIS RESPONSE:**

{response_text}

**OUTPUT (JSON array only, no other text):**"""
    
    try:
        result = await claim_extractor_llm.ainvoke(prompt)
        content = result.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse JSON
        claims = json.loads(content)
        
        # Validate structure
        if not isinstance(claims, list):
            print(f"        ⚠️  Claim extraction returned non-list: {type(claims)}")
            return []
        
        # Ensure each claim has required fields
        validated_claims = []
        for i, claim in enumerate(claims):
            if isinstance(claim, dict) and "claim" in claim:
                # Add missing fields
                if "claim_id" not in claim:
                    claim["claim_id"] = f"claim_{i+1}"
                if "category" not in claim:
                    claim["category"] = "general"
                
                validated_claims.append(claim)
        
        print(f"        ✅ Extracted {len(validated_claims)} atomic claims")
        
        # Show categories
        if validated_claims:
            categories = count_claims_by_category(validated_claims)
            print(f"           Categories: {dict(categories)}")
        
        return validated_claims
        
    except json.JSONDecodeError as e:
        print(f"        ❌ JSON parse error in claim extraction: {e}")
        print(f"           Raw content: {content[:200] if 'content' in locals() else 'N/A'}...")
        
        # Fallback: treat entire response as one claim
        return [
            {
                "claim": response_text,
                "claim_id": "claim_1",
                "category": "general",
                "extraction_error": str(e)
            }
        ]
    
    except Exception as e:
        print(f"        ❌ Claim extraction failed: {e}")
        
        # Fallback
        return [
            {
                "claim": response_text,
                "claim_id": "claim_1",
                "category": "general",
                "extraction_error": str(e)
            }
        ]


def count_claims_by_category(claims: List[Dict]) -> Dict[str, int]:
    """
    Count claims by category for analysis
    
    Args:
        claims: List of claims with category field
        
    Returns:
        {"definition": 2, "content": 3, "pricing": 1, ...}
        
    Confidence: 95% ✅
    """
    categories = [c.get("category", "general") for c in claims]
    return dict(Counter(categories))


def filter_claims_by_category(
    claims: List[Dict],
    categories: List[str]
) -> List[Dict]:
    """
    Filter claims to specific categories
    
    Args:
        claims: List of claims
        categories: Categories to keep
        
    Returns:
        Filtered list of claims
        
    Confidence: 95% ✅
    """
    return [c for c in claims if c.get("category") in categories]


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'extract_claims',
    'count_claims_by_category',
    'filter_claims_by_category'
]

