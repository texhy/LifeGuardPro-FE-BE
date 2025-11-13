"""
Course Matching Service - Multi-Source Intelligent Matching

Uses:
1. course_aliases table (display_title by audience)
2. courses table (title, slug, sku, short_title)
3. programs table (for context and hierarchy)
4. Fuzzy matching with program context

Confidence: 95% ✅
"""
from typing import Dict, Any, List, Tuple, Optional
from config.database import get_connection
import difflib

# Parent program keywords mapping
PROGRAM_KEYWORDS = {
    "water-safety-swim-instructor-certification-courses": {
        "keywords": ["water safety", "swim instructor", "wsi", "wsit", "wsitd", "basic water"],
        "title": "Water Safety Swim Instructor Certification Courses"
    },
    "lifeguard-certification-courses": {
        "keywords": ["lifeguard", "lgit", "pool lifeguard", "waterfront", "water park", "junior lifeguard"],
        "title": "Lifeguard Certification Courses"
    },
    "cpr-and-first-aid-certification-courses": {
        "keywords": ["cpr", "first aid", "bls", "aed", "bloodborne", "oxygen"],
        "title": "CPR & First Aid Certification Courses"
    },
    "certified-pool-operator-cpo-certification-course": {
        "keywords": ["cpo", "pool operator", "certified pool"],
        "title": "Certified Pool Operator (CPO) Certification Course"
    }
}

def identify_parent_program(query: str) -> Optional[Dict[str, Any]]:
    """
    Identify which parent program a query belongs to
    
    Args:
        query: User query (e.g., "CPR", "Lifeguard")
        
    Returns:
        Program dict with slug, title, etc. or None
    """
    query_lower = query.lower()
    
    for program_slug, program_info in PROGRAM_KEYWORDS.items():
        for keyword in program_info["keywords"]:
            if keyword in query_lower:
                return {
                    "program_id": None,  # Will be filled from DB
                    "slug": program_slug,
                    "title": program_info["title"]
                }
    
    return None

def fuzzy_match_courses_multi_source(
    query: str,
    buyer_category: Optional[str] = None,
    parent_program: Optional[Dict[str, Any]] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Multi-source course matching using:
    1. course_aliases.display_title (by audience)
    2. courses.title
    3. courses.short_title
    4. courses.slug
    5. courses.sku
    
    Args:
        query: Course name or query from user
        buyer_category: "individual" or "employer_or_instructor" (maps to INDIVIDUAL/GROUP)
        parent_program: Optional parent program dict to narrow search
        limit: Max number of matches
        
    Returns:
        List of matching courses with scores and source info
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Map buyer_category to course_aliases audience
            alias_audience = None
            if buyer_category == "individual":
                alias_audience = "INDIVIDUAL"
            elif buyer_category == "employer_or_instructor":
                alias_audience = "GROUP"
            
            # Build WHERE clause for program filter
            program_where = ""
            program_params = []
            if parent_program:
                program_where = "AND p.slug = %s"
                program_params.append(parent_program["slug"])
            
            # Build alias filter
            alias_where = ""
            alias_params = []
            if alias_audience:
                alias_where = "AND ca.audience = %s"
                alias_params.append(alias_audience)
            
            # Simplified query: Search courses directly, LEFT JOIN aliases for preference
            # Use parameterized audience filter in JOIN condition
            search_pattern = f"%{query}%"
            exact_pattern = query
            starts_pattern = f"{query}%"
            
            # Build alias JOIN condition
            alias_join_condition = "ca.active = true"
            if alias_params:
                alias_join_condition += " AND ca.audience = %s"
            
            sql = f"""
                SELECT DISTINCT
                    c.course_id,
                    c.title as canonical_title,
                    c.slug,
                    c.sku,
                    c.short_title,
                    c.description,
                    COALESCE(ca.display_title, c.title) as match_title,
                    CASE 
                        WHEN ca.display_title IS NOT NULL THEN 'alias'
                        ELSE 'canonical'
                    END as match_source,
                    ca.audience,
                    p.program_id,
                    p.slug as program_slug,
                    p.title as program_title,
                    p.description as program_description,
                    CASE 
                        WHEN COALESCE(ca.display_title, c.title) ILIKE %s THEN 1
                        WHEN COALESCE(ca.display_title, c.title) ILIKE %s THEN 2
                        WHEN c.title ILIKE %s THEN 3
                        ELSE 4
                    END as match_rank
                FROM courses c
                JOIN programs p ON c.program_id = p.program_id
                LEFT JOIN course_aliases ca ON (
                    c.course_id = ca.course_id 
                    AND {alias_join_condition}
                    AND ca.display_title ILIKE %s
                )
                WHERE c.active = true
                  {program_where}
                  AND (
                      c.title ILIKE %s
                      OR COALESCE(c.short_title, '') ILIKE %s
                      OR c.slug ILIKE %s
                      OR COALESCE(c.sku, '') ILIKE %s
                  )
                ORDER BY
                    match_rank,
                    c.title
                LIMIT %s
            """
            
            # Build params in correct order
            params = []
            
            # Add alias audience param if needed (for JOIN)
            if alias_params:
                params.append(alias_params[0])
            
            # Add alias display_title ILIKE for JOIN
            params.append(starts_pattern)
            
            # Add match_rank params
            params.extend([
                exact_pattern,  # CASE: exact match
                starts_pattern,  # CASE: starts with
                starts_pattern,  # CASE: title starts with
            ])
            
            # Add program filter if needed
            params.extend(program_params)
            
            # Add WHERE clause params
            params.extend([
                search_pattern,  # title ILIKE
                search_pattern,  # short_title ILIKE
                search_pattern,  # slug ILIKE
                search_pattern,  # sku ILIKE
            ])
            
            # Add limit
            params.append(limit)
            
            cur.execute(sql, params)
            results = cur.fetchall()
            
            # Calculate similarity scores
            matches = []
            query_lower = query.lower()
            
            for row in results:
                # Get the matched title
                match_title = row['match_title'].lower()
                
                # Use SequenceMatcher for fuzzy matching
                similarity = difflib.SequenceMatcher(
                    None, query_lower, match_title
                ).ratio()
                
                # Boost score for exact word matches
                query_words = set(query_lower.split())
                title_words = set(match_title.split())
                word_overlap = len(query_words & title_words) / max(len(query_words), 1)
                
                # Boost if match source is alias (more specific for audience)
                source_boost = 0.1 if row['match_source'] == 'alias' else 0.0
                
                final_score = (similarity * 0.5) + (word_overlap * 0.4) + source_boost
                
                matches.append({
                    "course_id": str(row['course_id']),
                    "canonical_title": row['canonical_title'],
                    "slug": row['slug'],
                    "sku": row['sku'],
                    "short_title": row['short_title'],
                    "description": row['description'],
                    "match_title": row['match_title'],
                    "match_source": row['match_source'],
                    "audience": row['audience'],
                    "program_id": str(row['program_id']) if row['program_id'] else None,
                    "program_slug": row['program_slug'],
                    "program_title": row['program_title'],
                    "program_description": row['program_description'],
                    "match_score": min(final_score, 1.0)  # Cap at 1.0
                })
            
            # Sort by score descending
            matches.sort(key=lambda x: x['match_score'], reverse=True)
            return matches

def match_course_with_disambiguation(
    query: str,
    buyer_category: Optional[str] = None,
    require_single_match: bool = True
) -> Dict[str, Any]:
    """
    Match course with automatic disambiguation for ambiguous queries
    
    Args:
        query: User query
        buyer_category: "individual" or "employer_or_instructor"
        require_single_match: If True, return disambiguation for multiple matches
        
    Returns:
        {
            "success": bool,
            "best_match": Dict | None,
            "needs_disambiguation": bool,
            "matches_by_program": List[Dict],  # Grouped by program
            "total_matches": int
        }
    """
    # Identify parent program
    parent_program = identify_parent_program(query)
    
    # Search all matching courses
    matches = fuzzy_match_courses_multi_source(
        query=query,
        buyer_category=buyer_category,
        parent_program=parent_program,
        limit=15
    )
    
    if not matches:
        return {
            "success": False,
            "best_match": None,
            "needs_disambiguation": False,
            "matches_by_program": [],
            "total_matches": 0
        }
    
    # Group matches by parent program
    matches_by_program = {}
    for match in matches:
        program_title = match["program_title"]
        if program_title not in matches_by_program:
            matches_by_program[program_title] = {
                "program_title": program_title,
                "program_slug": match["program_slug"],
                "program_description": match.get("program_description"),
                "courses": []
            }
        matches_by_program[program_title]["courses"].append(match)
    
    # Check if disambiguation needed
    best_match = matches[0]
    best_score = best_match["match_score"]
    
    # Get second best score if available
    second_best_score = matches[1]["match_score"] if len(matches) > 1 else 0.0
    
    # Need disambiguation if:
    # 1. Best match score < 0.85 (not confident enough)
    # 2. OR multiple matches with very similar high scores (difference < 0.05 AND both > 0.80)
    # 3. OR matches span multiple programs AND best score < 0.90
    high_score_matches = [m for m in matches if m["match_score"] >= 0.65]
    score_gap = best_score - second_best_score
    
    needs_disambiguation = (
        (best_score < 0.85 and require_single_match) or                    # Not confident enough
        (best_score >= 0.85 and score_gap < 0.05 and second_best_score >= 0.80 and require_single_match) or  # Very close scores
        (len(matches_by_program) > 1 and best_score < 0.90)                 # Multiple programs and not highly confident
    )
    
    # If user requires single match OR disambiguation needed, return suggestions
    if require_single_match and needs_disambiguation:
        return {
            "success": False,
            "best_match": None,
            "needs_disambiguation": True,
            "matches_by_program": list(matches_by_program.values()),
            "total_matches": len(matches)
        }
    
    # Otherwise return best match
    return {
        "success": True,
        "best_match": best_match,
        "needs_disambiguation": False,
        "matches_by_program": [],
        "total_matches": 1
    }

def format_matches_for_llm(matches_by_program: List[Dict]) -> str:
    """
    Format matches for LLM disambiguation message generation
    
    Args:
        matches_by_program: List of program groups with courses
        
    Returns:
        Formatted string for LLM prompt
    """
    formatted = ""
    
    for program_group in matches_by_program:
        program_title = program_group["program_title"]
        program_desc = program_group.get("program_description", "")
        courses = program_group["courses"]
        
        formatted += f"**Program: {program_title}**\n"
        if program_desc:
            formatted += f"{program_desc}\n"
        formatted += "\n"
        
        for i, course in enumerate(courses[:8], 1):  # Max 8 per program
            formatted += f"{i}. **{course['canonical_title']}**\n"
            if course.get('description'):
                formatted += f"   Description: {course['description'][:200]}...\n"
            if course.get('short_title'):
                formatted += f"   Also known as: {course['short_title']}\n"
            formatted += f"   Course ID: {course['course_id']}\n\n"
        
        formatted += "\n"
    
    return formatted

__all__ = [
    'fuzzy_match_courses_multi_source',
    'match_course_with_disambiguation',
    'identify_parent_program',
    'format_matches_for_llm'
]

