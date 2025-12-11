"""Test pricing lookup directly"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tools.get_pricing_tool import get_pricing
import asyncio

async def test():
    # Test 1: Ambiguous
    print("Test 1: Ambiguous query 'lifeguard'")
    result1 = await get_pricing.ainvoke({
        "course_name": "lifeguard",
        "quantity": 1,
        "buyer_category": "individual"
    })
    print(f"Result (first 200 chars): {result1[:200]}...")
    print(f"Has disambiguation: {'❓' in result1 or 'multiple' in result1.lower()}")
    print()
    
    # Test 2: Specific
    print("Test 2: Specific query")
    result2 = await get_pricing.ainvoke({
        "course_name": "Swimming Pool Lifeguard (max depth 12 ft.)",
        "quantity": 1,
        "buyer_category": "individual"
    })
    print(f"Result (first 300 chars): {result2[:300]}...")
    print(f"Has pricing: {'💰' in result2 or '$' in result2}")
    print(f"Has error: {'❌' in result2 or 'error' in result2.lower() or 'not available' in result2.lower()}")

asyncio.run(test())

