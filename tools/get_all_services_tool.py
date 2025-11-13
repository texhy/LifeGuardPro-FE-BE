"""
Get All Services Tool - Comprehensive Services List

Retrieves ALL services organized hierarchically:
- 4 Parent Programs
- ~40 Sub-courses with descriptions and target audiences

Confidence: 95% ✅
"""
from langchain.tools import tool
from config.database import get_connection
from typing import Optional
from utils.course_metadata import load_course_metadata

@tool
async def get_all_services(buyer_category: Optional[str] = None) -> str:
    """
    Get ALL LifeGuard-Pro services organized by parent programs.
    
    Use this tool when user asks:
    - "What services do you offer?"
    - "Tell me about all your courses"
    - "What do you have?"
    - "Show me everything you offer"
    - "Complete list of services"
    
    Args:
        buyer_category: "individual" or "employer_or_instructor" (optional)
            If provided, shows audience-specific course names from aliases
    
    Returns:
        str: Formatted hierarchical list of all services with descriptions
    """
    try:
        print(f"📋 Getting ALL services (buyer_category: {buyer_category})")
        
        # Load course metadata for descriptions
        course_metadata = load_course_metadata()
        
        # Map buyer_category to alias audience
        alias_audience = None
        if buyer_category == "individual":
            alias_audience = "INDIVIDUAL"
        elif buyer_category == "employer_or_instructor":
            alias_audience = "GROUP"
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Query all programs with their courses
                query = """
                    SELECT 
                        p.program_id,
                        p.title as program_title,
                        p.slug as program_slug,
                        c.course_id,
                        c.title as course_title,
                        c.short_title,
                        c.slug as course_slug,
                        COALESCE(
                            CASE 
                                WHEN %s = 'INDIVIDUAL' THEN ca_ind.display_title
                                WHEN %s = 'GROUP' THEN ca_group.display_title
                                ELSE NULL
                            END,
                            c.title
                        ) as display_title
                    FROM programs p
                    LEFT JOIN courses c ON c.program_id = p.program_id AND c.active = true
                    LEFT JOIN course_aliases ca_ind ON ca_ind.course_id = c.course_id 
                        AND ca_ind.audience = 'INDIVIDUAL' 
                        AND ca_ind.active = true
                    LEFT JOIN course_aliases ca_group ON ca_group.course_id = c.course_id 
                        AND ca_group.audience = 'GROUP' 
                        AND ca_group.active = true
                    ORDER BY p.program_id, c.title NULLS LAST
                """
                
                cur.execute(query, (alias_audience, alias_audience))
                rows = cur.fetchall()
                
                if not rows:
                    return "❌ No services found in database."
                
                # Organize by programs
                programs_dict = {}
                for row in rows:
                    program_id = row['program_id']
                    program_title = row['program_title']
                    program_slug = row['program_slug']
                    
                    if program_id not in programs_dict:
                        programs_dict[program_id] = {
                            'title': program_title,
                            'slug': program_slug,
                            'courses': []
                        }
                    
                    # Add course if it exists (some programs might not have courses yet)
                    if row['course_id']:
                        course_slug = row['course_slug']
                        display_title = row['display_title'] or row['course_title']
                        short_title = row['short_title']
                        
                        # Get metadata for this course
                        course_meta = course_metadata.get(course_slug, {})
                        target_audience = course_meta.get('target_audience', 'General public')
                        is_recert = course_meta.get('is_recertification', False)
                        
                        programs_dict[program_id]['courses'].append({
                            'title': display_title,
                            'slug': course_slug,
                            'short_title': short_title,
                            'target_audience': target_audience,
                            'is_recertification': is_recert,
                            'metadata': course_meta
                        })
                
                # Format output
                output_parts = []
                output_parts.append("🏊 **LIFEGUARD-PRO COMPLETE SERVICES CATALOG**")
                output_parts.append("")
                output_parts.append("Here are all the training courses and certifications we offer:")
                output_parts.append("")
                
                program_count = 0
                total_courses = 0
                
                for program_id in sorted(programs_dict.keys()):
                    program = programs_dict[program_id]
                    program_count += 1
                    courses = program['courses']
                    total_courses += len(courses)
                    
                    # Program header
                    output_parts.append(f"**{program_count}. {program['title']}**")
                    output_parts.append("")
                    
                    if not courses:
                        output_parts.append("  _No courses available yet_")
                        output_parts.append("")
                        continue
                    
                    # List courses with descriptions
                    for i, course in enumerate(courses, 1):
                        course_title = course['title']
                        target_audience = course['target_audience']
                        is_recert = course['is_recertification']
                        
                        # Build description line
                        desc_parts = [f"**{course_title}**"]
                        
                        # Add target audience info
                        if target_audience and target_audience != 'General public':
                            desc_parts.append(f"- *Who is this for: {target_audience}*")
                        
                        # Mark recertification courses
                        if is_recert:
                            desc_parts.append("- *Recertification/Renewal course*")
                        
                        # Add additional metadata if available
                        meta = course.get('metadata', {})
                        if meta.get('suitable_for'):
                            suitable = ", ".join(meta['suitable_for'][:3])  # Limit to 3
                            if len(meta['suitable_for']) > 3:
                                suitable += "..."
                            desc_parts.append(f"- *Best for: {suitable}*")
                        
                        output_parts.append(f"  {i}. {' | '.join(desc_parts)}")
                    
                    output_parts.append("")  # Space between programs
                
                # Summary
                output_parts.append("")
                output_parts.append(f"📊 **Summary:** {program_count} parent programs, {total_courses} total courses available")
                output_parts.append("")
                output_parts.append("💡 **Tip:** Ask me about pricing for any specific course, or let me know if you're looking for individual or group training!")
                
                return "\n".join(output_parts)
                
    except Exception as e:
        print(f"❌ Error getting all services: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error retrieving services: {str(e)}"

