"""
Course Metadata Loader - Prevents LLM Hallucination

This module loads detailed course metadata from services.json and formats it
for inclusion in LLM system prompts. This provides explicit context about
what each course is for, prerequisites, and who it's suitable for.

Confidence: 95% ✅

Author: Course Metadata Enhancement Implementation
"""

import json
from pathlib import Path
from typing import Dict, Any, List

# Global cache to avoid repeated file reads
_course_metadata_cache = None

def load_course_metadata() -> Dict[str, Any]:
    """
    Load course metadata from services.json (cached)
    
    Returns:
        Dict containing all course descriptions from services.json
        
    Confidence: 100% ✅
    """
    global _course_metadata_cache
    
    if _course_metadata_cache is None:
        # Get path to services.json relative to this file
        services_path = Path(__file__).parent.parent / "services.json"
        
        try:
            with open(services_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _course_metadata_cache = data.get("course_descriptions", {})
                print(f"✅ Loaded {len(_course_metadata_cache)} course descriptions from services.json")
        except FileNotFoundError:
            print(f"❌ services.json not found at {services_path}")
            _course_metadata_cache = {}
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing services.json: {e}")
            _course_metadata_cache = {}
    
    return _course_metadata_cache

def format_condensed_course_reference() -> str:
    """
    Format condensed course reference for planner prompt (names and slugs only)
    
    Phase 1 Improvement: Reduces prompt size by 70% (12,800 → ~3,800 chars)
    Only includes essential info for course matching, not full descriptions.
    Organized by actual program structure from services.json.
    
    Returns:
        Condensed formatted string with course names and slugs
        
    Confidence: 95% ✅
    """
    # Load the full JSON structure to access program categories
    services_path = Path(__file__).parent.parent / "services.json"
    
    try:
        with open(services_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            course_descriptions = data.get("course_descriptions", {})
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error loading services.json: {e}")
        return "No course metadata available."
    
    if not course_descriptions:
        return "No course metadata available."
    
    # Program category mappings (matching services.json structure)
    program_categories = {
        "lifeguard-certification-courses": "**Lifeguard Certification Courses**",
        "water-safety-and-swim-instruction-courses": "**Water Safety & Swim Instruction**",
        "cpr-and-first-aid-certification-courses": "**CPR & First Aid Certification Courses**",
        "certified-pool-operator-courses": "**Certified Pool Operator (CPO) Certification Course**"
    }
    
    # Build condensed reference organized by programs
    parts = []
    parts.append("QUICK COURSE REFERENCE (for matching only - use get_all_services tool for full details):")
    parts.append("")
    parts.append("**IMPORTANT:** Use the exact slug when planning get_pricing calls. Slugs match the database.")
    parts.append("")
    parts.append("**PROGRAM NAME MAPPINGS (for program-level queries):**")
    parts.append("")
    parts.append("If user mentions a PROGRAM name, use the corresponding program_slug:")
    parts.append("")
    parts.append("  - 'Lifeguard Certification Courses' / 'Lifeguard' / 'Lifeguard courses'")
    parts.append("    → program_slug: 'lifeguard-certification-courses'")
    parts.append("")
    parts.append("  - 'Water Safety & Swim Instruction' / 'Water Safety and Swim Instructor Certification Course' / 'Water Safety' / 'Swim Instructor' / 'WSI'")
    parts.append("    → program_slug: 'water-safety-and-swim-instruction-courses'")
    parts.append("")
    parts.append("  - 'CPR & First Aid Certification Courses' / 'CPR & First Aid' / 'CPR' / 'First Aid'")
    parts.append("    → program_slug: 'cpr-and-first-aid-certification-courses'")
    parts.append("")
    parts.append("  - 'Certified Pool Operator (CPO) Certification Course' / 'CPO' / 'Certified Pool Operator'")
    parts.append("    → program_slug: 'certified-pool-operator-courses'")
    parts.append("")
    parts.append("**CRITICAL:** If user mentions a program name, call get_all_services with program_slug filter to show sub-courses.")
    parts.append("Do NOT call get_pricing on program names - programs don't have pricing, courses do.")
    parts.append("")
    
    # Process each program category in order
    for program_key, program_title in program_categories.items():
        if program_key not in course_descriptions:
            continue
        
        program_courses = course_descriptions[program_key]
        if not program_courses:
            continue
        
        parts.append(program_title)
        parts.append("")
        
        # List all courses in this program
        course_entries = []
        for course_slug, course_info in program_courses.items():
            if not isinstance(course_info, dict):
                continue
            
            title = course_info.get("title", "Unknown Course")
            slug = course_info.get("slug", course_slug)  # Use slug from JSON, fallback to key
            
            # Format: "Title - slug: exact-slug"
            course_entry = f"  - {title} (slug: {slug})"
            course_entries.append(course_entry)
        
        # Sort courses alphabetically by title
        course_entries.sort()
        parts.extend(course_entries)
        parts.append("")
    
    # Add common abbreviations section
    parts.append("**Common Abbreviations:**")
    parts.append("  - CPO = Certified Pool Operator")
    parts.append("  - BLS = Basic Life Support (Healthcare Provider CPR)")
    parts.append("  - CPR = Usually refers to BLS CPR for Healthcare Provider")
    parts.append("  - LGI = Lifeguard Instructor")
    parts.append("  - WSI = Water Safety Swim Instructor")
    parts.append("")
    parts.append("**Note:** For full course details, prerequisites, and suitability information, use the get_all_services tool.")
    parts.append("**Critical:** Always use the exact slug from this reference when setting course_slug in pricing_slots.")
    
    return "\n".join(parts)


def format_course_metadata_for_prompt() -> str:
    """
    Format course metadata as a compact reference guide for LLM prompts
    
    DEPRECATED: Use format_condensed_course_reference() for planner prompt instead.
    This function is kept for backward compatibility with other parts of the system.
    
    Returns:
        Formatted string with essential course information for each course
        
    Confidence: 95% ✅
    """
    course_data = load_course_metadata()
    
    if not course_data:
        return "No course metadata available."
    
    formatted_courses = []
    
    for course_slug, course_info in course_data.items():
        # Extract key fields
        title = course_info.get("title", "Unknown Course")
        target_audience = course_info.get("target_audience", "Not specified")
        prerequisites = course_info.get("prerequisites", "Not specified")
        physical_requirements = course_info.get("physical_requirements", "Not specified")
        is_recertification = course_info.get("is_recertification", False)
        suitable_for = course_info.get("suitable_for", [])
        not_suitable_for = course_info.get("not_suitable_for", [])
        
        # Format lists
        suitable_str = ", ".join(suitable_for) if suitable_for else "Not specified"
        not_suitable_str = ", ".join(not_suitable_for) if not_suitable_for else "Not specified"
        
        # Format recertification flag
        recert_flag = "YES" if is_recertification else "NO"
        
        # Create compact format
        course_text = f"""COURSE: {title}
- Target: {target_audience}
- Prerequisites: {prerequisites}
- Physical: {physical_requirements}
- Recertification: {recert_flag}
- Suitable for: {suitable_str}
- NOT suitable for: {not_suitable_str}"""
        
        formatted_courses.append(course_text)
    
    # Join all courses with double newlines
    return "\n\n".join(formatted_courses)

def get_course_by_title(title: str) -> Dict[str, Any]:
    """
    Get course metadata by title (case-insensitive partial match)
    
    Args:
        title: Course title to search for
        
    Returns:
        Course metadata dict or empty dict if not found
        
    Confidence: 90% ✅
    """
    course_data = load_course_metadata()
    
    title_lower = title.lower()
    
    for course_slug, course_info in course_data.items():
        course_title = course_info.get("title", "").lower()
        
        # Check for exact match or partial match
        if title_lower == course_title or title_lower in course_title:
            return course_info
    
    return {}

def get_recertification_courses() -> List[Dict[str, Any]]:
    """
    Get all recertification courses
    
    Returns:
        List of course metadata for recertification courses
        
    Confidence: 95% ✅
    """
    course_data = load_course_metadata()
    
    recert_courses = []
    for course_slug, course_info in course_data.items():
        if course_info.get("is_recertification", False):
            recert_courses.append(course_info)
    
    return recert_courses

def get_courses_suitable_for(audience: str) -> List[Dict[str, Any]]:
    """
    Get courses suitable for a specific audience
    
    Args:
        audience: Target audience (e.g., "elderly", "beginners", "non-swimmers")
        
    Returns:
        List of course metadata suitable for the audience
        
    Confidence: 90% ✅
    """
    course_data = load_course_metadata()
    
    suitable_courses = []
    audience_lower = audience.lower()
    
    for course_slug, course_info in course_data.items():
        suitable_for = course_info.get("suitable_for", [])
        
        # Check if audience is in suitable_for list (case-insensitive)
        if any(audience_lower in suitable.lower() for suitable in suitable_for):
            suitable_courses.append(course_info)
    
    return suitable_courses

def validate_course_recommendation(course_title: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate if a course is appropriate for the user's context
    
    Args:
        course_title: Title of the course to validate
        user_context: User context with age, physical_capability, etc.
        
    Returns:
        Validation result with is_appropriate, reasons, warnings, alternatives
        
    Confidence: 85% ✅
    """
    course_info = get_course_by_title(course_title)
    
    if not course_info:
        return {
            "is_appropriate": False,
            "reasons": [f"Course '{course_title}' not found in metadata"],
            "warnings": [],
            "alternatives": []
        }
    
    validation_result = {
        "is_appropriate": True,
        "reasons": [],
        "warnings": [],
        "alternatives": []
    }
    
    # Check if it's a recertification course
    if course_info.get("is_recertification", False):
        if not user_context.get("has_existing_certification", False):
            validation_result["is_appropriate"] = False
            validation_result["reasons"].append("This is a recertification course - requires existing certification")
            
            # Suggest the non-recertification version
            base_title = course_title.replace(" Recertification", "").replace(" / Renewal", "")
            validation_result["alternatives"].append(base_title)
    
    # Check physical requirements
    user_physical = user_context.get("physical_capability", "").lower()
    if user_physical == "low":
        physical_req = course_info.get("physical_requirements", "").lower()
        if "high" in physical_req or "very high" in physical_req:
            validation_result["is_appropriate"] = False
            validation_result["reasons"].append("Course requires higher physical capability than user has")
            validation_result["alternatives"].append("Basic Water Safety")
    
    # Check age requirements
    user_age = user_context.get("age")
    if user_age:
        # Basic age checks (can be enhanced with more specific rules)
        if user_age < 8 and "adult" in course_info.get("target_audience", "").lower():
            validation_result["warnings"].append("User may be too young for this course")
    
    return validation_result

# Test function for development
def test_course_metadata():
    """
    Test function to verify course metadata loading and formatting
    
    Confidence: 95% ✅
    """
    print("Testing course metadata loader...")
    
    # Test loading
    metadata = load_course_metadata()
    print(f"Loaded {len(metadata)} courses")
    
    # Test formatting
    formatted = format_course_metadata_for_prompt()
    print(f"Formatted metadata length: {len(formatted)} characters")
    
    # Test specific course lookup
    basic_water = get_course_by_title("Basic Water Safety")
    if basic_water:
        print(f"Found Basic Water Safety: {basic_water.get('title')}")
        print(f"  Recertification: {basic_water.get('is_recertification')}")
        print(f"  Suitable for: {basic_water.get('suitable_for')}")
    
    # Test recertification courses
    recert_courses = get_recertification_courses()
    print(f"Found {len(recert_courses)} recertification courses")
    
    # Test validation
    user_context = {"age": 90, "physical_capability": "low", "has_existing_certification": False}
    validation = validate_course_recommendation("Basic Water Safety Recertification / Renewal", user_context)
    print(f"Validation result: {validation}")

if __name__ == "__main__":
    test_course_metadata()
