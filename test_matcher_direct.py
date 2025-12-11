"""
Direct test of course matcher to debug issues
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.course_matcher import match_course_with_disambiguation

async def test_matcher():
    print("Testing course matcher directly...")
    
    try:
        result = match_course_with_disambiguation(
            query="lifeguard",
            buyer_category="individual",
            require_single_match=True
        )
        
        print(f"\nResult:")
        print(f"  Success: {result['success']}")
        print(f"  Needs disambiguation: {result['needs_disambiguation']}")
        print(f"  Total matches: {result['total_matches']}")
        if result.get('best_match'):
            print(f"  Best match: {result['best_match'].get('canonical_title', 'None')}")
        else:
            print(f"  Best match: None (disambiguation needed)")
        
        if result['needs_disambiguation']:
            print(f"\n  Matches by program: {len(result['matches_by_program'])}")
            for pg in result['matches_by_program']:
                print(f"    - {pg['program_title']}: {len(pg['courses'])} courses")
                for course in pg['courses'][:3]:
                    print(f"      * {course['canonical_title']} (score: {course['match_score']:.2f})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_matcher())

