"""Test database connection and check if courses exist"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config.database import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        # Check programs
        cur.execute("SELECT COUNT(*) as count FROM programs")
        programs_count = cur.fetchone()['count']
        print(f"Programs in DB: {programs_count}")
        
        # Check courses
        cur.execute("SELECT COUNT(*) as count FROM courses WHERE active = true")
        courses_count = cur.fetchone()['count']
        print(f"Active courses in DB: {courses_count}")
        
        # Check course_aliases
        cur.execute("SELECT COUNT(*) as count FROM course_aliases WHERE active = true")
        aliases_count = cur.fetchone()['count']
        print(f"Active course aliases in DB: {aliases_count}")
        
        # Sample courses with "lifeguard" in title
        cur.execute("""
            SELECT title, slug FROM courses 
            WHERE active = true 
            AND title ILIKE '%lifeguard%'
            LIMIT 5
        """)
        lifeguard_courses = cur.fetchall()
        print(f"\nSample lifeguard courses:")
        for course in lifeguard_courses:
            print(f"  - {course['title']} ({course['slug']})")
        
        # Check if programs are linked
        cur.execute("""
            SELECT COUNT(*) as count 
            FROM courses c
            JOIN programs p ON c.program_id = p.program_id
            WHERE c.active = true
        """)
        linked_count = cur.fetchone()['count']
        print(f"\nCourses linked to programs: {linked_count}")

