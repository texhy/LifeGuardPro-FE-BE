"""
Test script for course matching integration
Tests the complete flow with actual API calls
"""
import requests
import json
import time
import sys

API_URL = "http://localhost:8000"
CHAT_ENDPOINT = f"{API_URL}/api/v1/chat/message"
SESSION_ENDPOINT = f"{API_URL}/api/v1/session/create"
SESSION_ID = None

def create_session():
    """Create a new session"""
    global SESSION_ID
    payload = {
        "user_name": "Test User",
        "user_email": f"test{int(time.time())}@example.com",
        "user_phone": None
    }
    
    print(f"\n{'='*80}")
    print(f"📝 Creating session...")
    print(f"{'='*80}")
    
    try:
        response = requests.post(SESSION_ENDPOINT, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        SESSION_ID = data.get('session_id')
        print(f"✅ Session created: {SESSION_ID}")
        print(f"   Status: {data.get('status', 'unknown')}")
        return SESSION_ID
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating session: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"   Response: {e.response.text}")
        return None

def send_message(message_text, session_id=None):
    """Send a message to the chat API"""
    if not session_id:
        session_id = SESSION_ID
    
    if not session_id:
        print("❌ No session ID available")
        return None
    
    payload = {
        "session_id": session_id,
        "message": message_text,
        "user_name": "Test User",
        "user_email": "test@example.com"
    }
    
    print(f"\n{'='*80}")
    print(f"📤 SENDING: {message_text}")
    print(f"{'='*80}")
    
    try:
        response = requests.post(CHAT_ENDPOINT, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Status: {response.status_code}")
        print(f"📊 Tool Calls: {data.get('tool_calls', [])}")
        print(f"🚫 Blocked: {data.get('blocked', False)}")
        
        response_text = data.get('response', '')
        print(f"\n📥 RESPONSE ({len(response_text)} chars):")
        print("-" * 80)
        print(response_text)
        print("-" * 80)
        
        return data
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Response: {e.response.text}")
        return None

def test_complete_flow():
    """Test the complete flow: services → pricing (ambiguous) → specific pricing"""
    
    print("\n" + "="*80)
    print("🧪 TESTING COURSE MATCHING INTEGRATION")
    print("="*80)
    
    # Create session first
    session_id = create_session()
    if not session_id:
        print("❌ Failed to create session - aborting tests")
        return
    
    print(f"\n📋 Using Session ID: {session_id}")
    print(f"📡 API Base URL: {API_URL}")
    
    # Test 1: Services query
    print("\n\n🔍 TEST 1: Services Query for Lifeguard")
    result1 = send_message("What are your services for lifeguard?")
    
    if not result1:
        print("❌ Test 1 failed - aborting")
        return
    
    time.sleep(2)  # Brief pause between requests
    
    # Test 2: Ambiguous pricing query (should trigger disambiguation)
    print("\n\n💰 TEST 2: Ambiguous Pricing Query (should trigger disambiguation)")
    result2 = send_message("What is your pricing for lifeguard?")
    
    if not result2:
        print("❌ Test 2 failed")
        return
    
    # Check if disambiguation was triggered
    response_text = result2.get('response', '').lower()
    has_disambiguation = (
        'multiple' in response_text or
        'which one' in response_text or
        'options' in response_text or
        '❓' in result2.get('response', '') or
        'here are' in response_text
    )
    
    if has_disambiguation:
        print("\n✅ DISAMBIGUATION TRIGGERED!")
        print("   The system correctly identified multiple lifeguard courses")
        print("   and asked the user to clarify which one they want.")
    else:
        print("\n⚠️  DISAMBIGUATION NOT TRIGGERED")
        print("   The response might have returned pricing directly")
        print("   or failed to detect ambiguity.")
    
    # Check if response contains course descriptions (LLM-generated)
    has_descriptions = (
        'best for' in response_text or
        'perfect for' in response_text or
        'ideal for' in response_text or
        'designed for' in response_text or
        'junior' in response_text or
        'swimming pool' in response_text or
        'shallow' in response_text
    )
    
    if has_descriptions:
        print("✅ LLM-GENERATED DESCRIPTIONS PRESENT!")
        print("   The disambiguation message includes helpful descriptions")
        print("   explaining what each course is and who it's for.")
    else:
        print("⚠️  DESCRIPTIONS NOT DETECTED")
        print("   The response might be using a fallback template")
        print("   or the LLM generation might have failed.")
    
    time.sleep(2)
    
    # Test 3: Specific pricing query (should return pricing directly)
    print("\n\n💵 TEST 3: Specific Pricing Query (should return pricing directly)")
    result3 = send_message("What's the price for Swimming Pool Lifeguard (max depth 12 ft.)?")
    
    if not result3:
        print("❌ Test 3 failed")
        return
    
    response_text3 = result3.get('response', '')
    has_pricing = '$' in response_text3 or 'price' in response_text3.lower()
    
    if has_pricing:
        print("\n✅ PRICING RETURNED!")
        print("   The system found a specific match and returned pricing.")
    else:
        print("\n⚠️  PRICING NOT RETURNED")
        print("   The response might indicate course not found or error.")
    
    # Summary
    print("\n\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"✅ Test 1 (Services): {'PASSED' if result1 else 'FAILED'}")
    print(f"{'✅' if has_disambiguation else '⚠️ '} Test 2 (Disambiguation): {'PASSED' if has_disambiguation else 'NEEDS REVIEW'}")
    print(f"{'✅' if has_descriptions else '⚠️ '} LLM Descriptions: {'PRESENT' if has_descriptions else 'NOT DETECTED'}")
    print(f"{'✅' if has_pricing else '⚠️ '} Test 3 (Specific Pricing): {'PASSED' if has_pricing else 'NEEDS REVIEW'}")
    print("="*80)

if __name__ == "__main__":
    try:
        test_complete_flow()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

