"""
Test script for course matching and disambiguation flow

Tests:
1. Services query for lifeguard
2. Pricing query for lifeguard (ambiguous)
3. Disambiguation response
4. Specific pricing query
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.course_matcher import match_course_with_disambiguation, identify_parent_program
from utils.disambiguation_generator import generate_disambiguation_message
from tools.get_pricing_tool import get_pricing

async def test_flow():
    print("="*80)
    print("TESTING COURSE MATCHING AND DISAMBIGUATION FLOW")
    print("="*80)
    
    # Test 1: Identify parent program
    print("\n1️⃣  TEST: Parent Program Identification")
    print("-" * 80)
    query1 = "lifeguard"
    program = identify_parent_program(query1)
    if program:
        print(f"✅ Query '{query1}' → Program: {program['title']}")
        print(f"   Slug: {program['slug']}")
    else:
        print(f"❌ No program identified for '{query1}'")
    
    # Test 2: Ambiguous query matching
    print("\n2️⃣  TEST: Ambiguous Query Matching")
    print("-" * 80)
    query2 = "lifeguard"
    match_result = match_course_with_disambiguation(
        query=query2,
        buyer_category="individual",
        require_single_match=True
    )
    
    print(f"Query: '{query2}'")
    print(f"Total matches: {match_result['total_matches']}")
    print(f"Needs disambiguation: {match_result['needs_disambiguation']}")
    
    if match_result['needs_disambiguation']:
        print(f"✅ Correctly identified as ambiguous")
        print(f"   Programs with matches: {len(match_result['matches_by_program'])}")
        
        for pg in match_result['matches_by_program']:
            print(f"\n   Program: {pg['program_title']}")
            print(f"   Courses: {len(pg['courses'])}")
            for course in pg['courses'][:3]:  # Show first 3
                print(f"     - {course['canonical_title']} (score: {course['match_score']:.2f})")
    else:
        print(f"❌ Should be ambiguous but wasn't detected")
    
    # Test 3: Generate disambiguation message
    print("\n3️⃣  TEST: LLM Disambiguation Message Generation")
    print("-" * 80)
    if match_result['needs_disambiguation']:
        try:
            disambiguation_msg = await generate_disambiguation_message(
                user_query=query2,
                matches_by_program=match_result['matches_by_program'],
                buyer_category="individual"
            )
            print("✅ Disambiguation message generated:")
            print("\n" + "-" * 80)
            print(disambiguation_msg[:500] + "..." if len(disambiguation_msg) > 500 else disambiguation_msg)
            print("-" * 80)
        except Exception as e:
            print(f"❌ Error generating disambiguation: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("⏭️  Skipped (no disambiguation needed)")
    
    # Test 4: Pricing tool with ambiguous query
    print("\n4️⃣  TEST: Pricing Tool - Ambiguous Query")
    print("-" * 80)
    try:
        pricing_result = await get_pricing.ainvoke({
            "course_name": "lifeguard",
            "quantity": 1,
            "buyer_category": "individual"
        })
        
        print("✅ Pricing tool response:")
        print("\n" + "-" * 80)
        print(pricing_result[:800] + "..." if len(pricing_result) > 800 else pricing_result)
        print("-" * 80)
        
        # Check if it's disambiguation or actual pricing
        if "❓" in pricing_result or "multiple" in pricing_result.lower():
            print("✅ Correctly returned disambiguation message")
        else:
            print("⚠️  Returned pricing directly (may be incorrect if ambiguous)")
            
    except Exception as e:
        print(f"❌ Error in pricing tool: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Specific query (should return pricing)
    print("\n5️⃣  TEST: Pricing Tool - Specific Query")
    print("-" * 80)
    try:
        pricing_result2 = await get_pricing.ainvoke({
            "course_name": "Swimming Pool Lifeguard (max depth 12 ft.)",
            "quantity": 1,
            "buyer_category": "individual"
        })
        
        print("✅ Pricing tool response:")
        print("\n" + "-" * 80)
        print(pricing_result2[:400] + "..." if len(pricing_result2) > 400 else pricing_result2)
        print("-" * 80)
        
        if "💰" in pricing_result2 or "$" in pricing_result2:
            print("✅ Correctly returned pricing information")
        else:
            print("⚠️  Did not return pricing (may be error or no price in DB)")
            
    except Exception as e:
        print(f"❌ Error in pricing tool: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_flow())

