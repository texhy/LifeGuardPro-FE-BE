#!/bin/bash
# Quick API Test Script

API_URL="http://localhost:8000"

echo "🧪 Testing LifeGuard-Pro FastAPI"
echo "================================"
echo ""

# Test 1: Health check
echo "1️⃣  Testing health endpoint..."
HEALTH=$(curl -s "$API_URL/api/v1/health")
echo "Response: $HEALTH"
echo ""

# Test 2: Detailed health
echo "2️⃣  Testing detailed health endpoint..."
curl -s "$API_URL/api/v1/health/detailed" | python3 -m json.tool
echo ""

# Test 3: Create session
echo "3️⃣  Creating test session..."
SESSION_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/session/create" \
  -H "Content-Type: application/json" \
  -d '{
    "user_name": "Test User",
    "user_email": "test@example.com",
    "user_phone": "555-1234"
  }')

echo "$SESSION_RESPONSE" | python3 -m json.tool
SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")
echo ""
echo "✅ Session ID: $SESSION_ID"
echo ""

# Test 4: Send chat message
echo "4️⃣  Sending chat message..."
curl -s -X POST "$API_URL/api/v1/chat/message" \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"$SESSION_ID\",
    \"message\": \"What is CPO certification?\"
  }" | python3 -m json.tool
echo ""

echo "================================"
echo "✅ API tests complete!"
echo ""
echo "To run server: uvicorn api.main:app --reload --port 8000"
echo "API docs: http://localhost:8000/docs"

