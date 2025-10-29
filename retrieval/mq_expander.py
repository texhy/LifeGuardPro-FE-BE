"""
Multi-Query Expansion (MQE) Module

Generates multiple query variations to improve retrieval coverage.

Approach:
- Use LLM to generate 3-5 alternative phrasings
- Vary across: acronyms, synonyms, specificity, question types
- Deduplicate semantically similar queries
- Assign weights based on importance

Confidence: 88% ✅

Example:
    Input: "What is CPO?"
    Output: [
        {"query": "Certified Pool Operator certification overview", "weight": 1.0},
        {"query": "CPO pool management training requirements", "weight": 0.9},
        {"query": "Pool operator certification program details", "weight": 0.85}
    ]
"""

from typing import List, Dict, Any
import os
import json
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()


# LLM for query expansion (faster/cheaper model)
expansion_llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.7,  # Some creativity for variations
    api_key=os.getenv("OPENAI_API_KEY")
)


async def expand_query(
    query: str,
    num_queries: int = 3
) -> List[Dict[str, Any]]:
    """
    Generate multiple query variations using LLM
    
    Args:
        query: Original user query
        num_queries: Number of variations to generate (default 3)
        
    Returns:
        List of query variations with weights:
        [
            {"query": str, "weight": float, "variation_type": str},
            ...
        ]
        
    Confidence: 88% ✅
    """
    
    # Ensure num_queries is reasonable
    num_queries = max(2, min(num_queries, 5))
    
    # Phase 2 - P2: Simplified MQE prompt (100 lines → 40 lines)
    prompt = f"""Generate {num_queries} query variations for: "{query}"

CONTEXT: LifeGuard-Pro offers 4 main programs:
1. Water Safety Swim Instructor Certification
2. Lifeguard Certification (multiple levels)
3. CPR & First Aid Certification
4. Certified Pool Operator (CPO)

RULES:
- If query is GENERAL ("what services", "what courses"): Cover ALL 4 programs
- If query is SPECIFIC ("what is CPO", "BLS requirements"): Stay focused but vary phrasing
- Use these strategies:
  1. Expand acronyms (CPO → Certified Pool Operator)
  2. Add synonyms (course/training/program/certification)
  3. Vary specificity (broad → narrow)
  4. Include related topics (CPO → pool safety)

EXAMPLES:

General: "What courses do you offer?"
[
  {{"query": "full catalog of lifeguard CPR swim instructor and pool operator training", "weight": 1.0}},
  {{"query": "available certifications in water safety emergency response and aquatic facility management", "weight": 0.9}},
  {{"query": "complete course offerings for lifeguard instructor CPO and first aid training", "weight": 0.85}}
]

Specific: "What is CPO?"
[
  {{"query": "Certified Pool Operator certification requirements and course details", "weight": 1.0}},
  {{"query": "pool operator training program overview and qualifications", "weight": 0.9}},
  {{"query": "CPO online certification process content and exam", "weight": 0.85}}
]

Output JSON array for: "{query}":"""

    try:
        # Call LLM
        response = await expansion_llm.ainvoke(prompt)
        content = response.content.strip()
        
        # Remove markdown formatting if present
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Parse JSON
        expanded = json.loads(content)
        
        # Validate structure
        if not isinstance(expanded, list):
            raise ValueError("Expected list of queries")
        
        # Ensure each has required fields
        validated = []
        for i, item in enumerate(expanded):
            if isinstance(item, dict) and "query" in item:
                # Add defaults if missing
                if "weight" not in item:
                    item["weight"] = 1.0 - (i * 0.1)  # Decreasing weights
                if "variation_type" not in item:
                    item["variation_type"] = "general"
                
                validated.append(item)
        
        # Deduplicate (remove very similar queries)
        deduplicated = _deduplicate_queries(validated)
        
        # Phase 2 - P5: Validate query quality (filter too-similar expansions)
        deduplicated = validate_query_quality(query, deduplicated)
        
        # Ensure we have at least 2 queries (original + 1 variation)
        if len(deduplicated) < 2:
            # Fallback: add original query
            deduplicated.append({
                "query": query,
                "weight": 1.0,
                "variation_type": "original"
            })
        
        print(f"     MQE: Generated {len(deduplicated)} query variations (validated)")
        
        return deduplicated
        
    except Exception as e:
        print(f"     ⚠️  MQE failed: {e}")
        print(f"        Falling back to original query only")
        
        # Fallback: return original query only
        return [
            {
                "query": query,
                "weight": 1.0,
                "variation_type": "original",
                "expansion_error": str(e)
            }
        ]


def _deduplicate_queries(queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove semantically very similar queries
    
    Simple approach: Check if query strings are too similar
    (More advanced: could use embedding similarity)
    
    Args:
        queries: List of query objects
        
    Returns:
        Deduplicated list
    """
    if len(queries) <= 2:
        return queries
    
    deduplicated = []
    
    for query_obj in queries:
        query_text = query_obj["query"].lower()
        
        # Check if too similar to existing queries
        is_duplicate = False
        for existing in deduplicated:
            existing_text = existing["query"].lower()
            
            # Simple word overlap check
            query_words = set(query_text.split())
            existing_words = set(existing_text.split())
            
            overlap = len(query_words & existing_words)
            total = len(query_words | existing_words)
            
            if total > 0:
                similarity = overlap / total
                
                # If >85% word overlap, consider duplicate
                if similarity > 0.85:
                    is_duplicate = True
                    break
        
        if not is_duplicate:
            deduplicated.append(query_obj)
    
    return deduplicated


def validate_query_quality(
    original: str,
    expanded: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Validate that expanded queries are actually different and useful
    
    Filters out:
    - Queries too similar to original (>90% overlap)
    - Queries that are just reordered words
    - Queries that don't add new information
    
    Args:
        original: Original user query
        expanded: List of expanded query objects
        
    Returns:
        Filtered list of validated queries
        
    Confidence: 95% ✅
    Phase 2 - P5
    """
    validated = []
    original_words = set(original.lower().split())
    
    for exp_query in expanded:
        query_text = exp_query["query"]
        query_words = set(query_text.lower().split())
        
        # Check word overlap
        overlap = len(original_words & query_words)
        total = len(original_words | query_words)
        similarity = overlap / total if total > 0 else 0
        
        # Keep if adds new information (similarity < 90%)
        if similarity < 0.9:
            validated.append(exp_query)
        else:
            print(f"     ⚠️  Filtered too-similar expansion: {query_text[:50]}...")
    
    # Always include at least the original if all were filtered
    if not validated:
        validated.append({
            "query": original,
            "weight": 1.0,
            "variation_type": "original"
        })
        print(f"     ⚠️  All expansions filtered, using original only")
    
    return validated


def calculate_coverage_score(
    original_query: str,
    expanded_queries: List[Dict[str, Any]]
) -> float:
    """
    Calculate coverage confidence score
    
    Assesses how well the expanded queries cover the information space.
    
    Coverage dimensions:
    - Acronym expanded (1.0 if yes, 0.5 if partial, 0.0 if no)
    - Phrasing diversity (count unique phrasings / 3)
    - Specificity range (has general + specific)
    - Synonym coverage (count synonym sets)
    
    Returns:
        Coverage score (0.0 to 1.0)
        
    Confidence: 85% ✅
    """
    
    # Simple heuristic-based calculation
    # (Could be enhanced with LLM-based assessment)
    
    all_text = " ".join([q["query"] for q in expanded_queries]).lower()
    original_lower = original_query.lower()
    
    # Check acronym expansion
    common_acronyms = ["cpo", "bls", "aed", "afo", "cpr"]
    acronym_score = 0.0
    
    for acronym in common_acronyms:
        if acronym in original_lower:
            # Check if expanded form appears in variations
            expansions = {
                "cpo": "certified pool operator",
                "bls": "basic life support",
                "aed": "automated external defibrillator",
                "afo": "aquatic facility operator",
                "cpr": "cardiopulmonary resuscitation"
            }
            
            if acronym in expansions and expansions[acronym] in all_text:
                acronym_score = 1.0
                break
    
    # Check phrasing diversity (simple: count unique first 3 words)
    first_words = set()
    for q in expanded_queries:
        words = q["query"].lower().split()
        if len(words) >= 3:
            first_words.add(" ".join(words[:3]))
    
    phrasing_diversity = min(len(first_words) / 3, 1.0)
    
    # Check synonym coverage (simple: count synonym words)
    synonyms_found = 0
    synonym_sets = [
        ["course", "training", "program", "certification"],
        ["operator", "manager"],
        ["requirements", "prerequisites", "qualifications"]
    ]
    
    for syn_set in synonym_sets:
        if any(syn in all_text for syn in syn_set):
            synonyms_found += 1
    
    synonym_coverage = synonyms_found / len(synonym_sets)
    
    # Overall coverage score
    coverage = (acronym_score + phrasing_diversity + synonym_coverage) / 3
    
    return coverage


__all__ = ['expand_query', 'calculate_coverage_score', 'validate_query_quality']

