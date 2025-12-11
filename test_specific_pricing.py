"""Test specific course pricing lookup"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.course_matcher import match_course_with_disambiguation
from config.database import get_connection

# Test matching the specific course
query = "Swimming Pool Lifeguard (max depth 12 ft.)"

print("Testing specific course matching...")
result = match_course_with_disambiguation(
    query=query,
    buyer_category="individual",
    require_single_match=True
)

print(f"\nResult:")
print(f"  Success: {result['success']}")
print(f"  Needs disambiguation: {result['needs_disambiguation']}")
print(f"  Total matches: {result['total_matches']}")

if result['needs_disambiguation']:
    print(f"\n  Matches found ({len(result['matches_by_program'])} program groups):")
    for pg in result['matches_by_program']:
        print(f"\n    Program: {pg['program_title']}")
        for course in pg['courses'][:5]:
            print(f"      - {course['canonical_title']}")
            print(f"        Score: {course['match_score']:.2f}")
            print(f"        Slug: {course['slug']}")

if result.get('best_match'):
    best = result['best_match']
    print(f"\n  Best match:")
    print(f"    Title: {best['canonical_title']}")
    print(f"    Slug: {best['slug']}")
    print(f"    Course ID: {best['course_id']}")
    print(f"    Match score: {best['match_score']:.2f}")
    
    # Check if pricing exists
    course_id = best['course_id']
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT unit_price, currency
                FROM price_individual
                WHERE course_id = %s::uuid
                  AND effective_from <= CURRENT_DATE
                  AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
                ORDER BY effective_from DESC
                LIMIT 1
            """, (course_id,))
            
            price = cur.fetchone()
            if price:
                print(f"\n  ✅ Pricing found: ${price['unit_price']:.2f} {price['currency']}")
            else:
                print(f"\n  ⚠️  No pricing found for this course in price_individual table")
                
                # Check all courses with pricing
                cur.execute("""
                    SELECT COUNT(*) as count
                    FROM price_individual
                    WHERE effective_from <= CURRENT_DATE
                      AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
                """)
                total_prices = cur.fetchone()['count']
                print(f"  Total courses with pricing: {total_prices}")
else:
    print("  No match found")

