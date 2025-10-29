# 🔧 Tool Integration Plan - Pricing, Quote, & Booking

**Status:** 📋 Planning Phase  
**Date:** October 29, 2025  
**Goal:** Integrate 3 additional tools (pricing, quote, booking) into the lifeguard-pro-api with proper multi-intent handling

---

## 📊 Current State Analysis

### ✅ What's Already Working:
1. **Tool Files Exist**: All 4 tools are present in `lifeguard-pro-api/tools/`:
   - ✅ `rag_search_tool.py` (working)
   - ✅ `get_pricing_tool.py` (coded, not integrated)
   - ✅ `quote_send_email_tool.py` (coded, not integrated)
   - ✅ `book_meeting_tool.py` (coded, not integrated)

2. **Planner Handles Multi-Intent**: The planner already supports:
   - Multiple intents in one query
   - Priority assignment (lower = execute first)
   - Dependency tracking (e.g., quote needs pricing first)

3. **Executor Structure**: The executor node has routing logic for all 4 tools

### ❌ What's Missing:
1. **Tools Not Exported**: `tools/__init__.py` only exports `rag_search`
2. **Executor Functions Are Placeholders**: They return error messages instead of calling the actual tools
3. **No Tool Response Handling**: The chat service extracts tool calls but doesn't properly format tool-specific responses

---

## 🎯 Implementation Steps

### **Step 1: Export Tools in `__init__.py`**
**File:** `lifeguard-pro-api/tools/__init__.py`

**Current:**
```python
from .rag_search_tool import rag_search
__all__ = ['rag_search']
```

**Update to:**
```python
from .rag_search_tool import rag_search
from .get_pricing_tool import get_pricing
from .book_meeting_tool import book_meeting
from .quote_send_email_tool import quote_send_email

__all__ = [
    'rag_search',
    'get_pricing',
    'book_meeting',
    'quote_send_email'
]
```

**Why:** Makes tools importable throughout the application

---

### **Step 2: Implement Real Tool Execution**
**File:** `lifeguard-pro-api/core/executor_node.py`

**Current Issue:** Functions return placeholder errors:
```python
async def execute_pricing(args: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "error": "Pricing execution not implemented yet (Phase 2.2)"
    }
```

**Update to:**

#### 2.1 Add Tool Imports (Top of File)
```python
from tools.get_pricing_tool import get_pricing
from tools.book_meeting_tool import book_meeting
from tools.quote_send_email_tool import quote_send_email
```

#### 2.2 Implement `execute_pricing()`
```python
async def execute_pricing(args: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute pricing tool - Looks up course pricing in database
    
    Args:
        args: {course_name: str, quantity: int}
        state: Current conversation state
        
    Returns:
        {success: bool, data: str, error: str}
    """
    try:
        print(f"  💰 Calling get_pricing tool...")
        
        # Extract arguments
        course_name = args.get("course_name") or args.get("course")
        quantity = args.get("quantity", 1)
        
        if not course_name:
            return {
                "success": False,
                "data": None,
                "error": "Missing required argument: course_name"
            }
        
        # Call the actual tool
        result = await get_pricing.ainvoke({
            "course_name": course_name,
            "quantity": quantity
        })
        
        print(f"  ✅ Pricing tool returned: {len(result)} characters")
        
        return {
            "success": True,
            "data": result,  # Formatted pricing string from tool
            "error": None
        }
        
    except Exception as e:
        print(f"  ❌ Pricing tool error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "data": None,
            "error": f"Pricing lookup failed: {str(e)}"
        }
```

#### 2.3 Implement `execute_quote()`
```python
async def execute_quote(args: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute quote/email tool - Generates quote with payment links and sends email
    
    Args:
        args: {
            course_name: str,
            quantity: int,
            pricing_option: str (optional),
            user_email: str,
            user_name: str,
            user_phone: str (optional),
            payment_methods: list (optional)
        }
        state: Current conversation state
        
    Returns:
        {success: bool, data: str, error: str}
    """
    try:
        print(f"  📧 Calling quote_send_email tool...")
        
        # Extract required arguments
        course_name = args.get("course_name") or args.get("course")
        quantity = args.get("quantity", 1)
        user_email = args.get("user_email") or state.get("user_email")
        user_name = args.get("user_name") or state.get("user_name")
        
        # Validate required fields
        if not course_name:
            return {
                "success": False,
                "data": None,
                "error": "Missing required argument: course_name"
            }
        
        if not user_email:
            return {
                "success": False,
                "data": None,
                "error": "Missing required argument: user_email"
            }
        
        if not user_name:
            return {
                "success": False,
                "data": None,
                "error": "Missing required argument: user_name"
            }
        
        # Build tool arguments
        tool_args = {
            "course_name": course_name,
            "quantity": quantity,
            "user_email": user_email,
            "user_name": user_name
        }
        
        # Add optional fields
        if args.get("pricing_option"):
            tool_args["pricing_option"] = args["pricing_option"]
        
        if args.get("user_phone") or state.get("user_phone"):
            tool_args["user_phone"] = args.get("user_phone") or state.get("user_phone")
        
        if args.get("payment_methods"):
            tool_args["payment_methods"] = args["payment_methods"]
        
        # Call the actual tool
        result = await quote_send_email.ainvoke(tool_args)
        
        print(f"  ✅ Quote tool returned: {len(result)} characters")
        
        return {
            "success": True,
            "data": result,  # Success message with quote details
            "error": None
        }
        
    except Exception as e:
        print(f"  ❌ Quote tool error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "data": None,
            "error": f"Quote generation failed: {str(e)}"
        }
```

#### 2.4 Implement `execute_booking()`
```python
async def execute_booking(args: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute booking tool - Schedules virtual meeting/consultation
    
    Args:
        args: {
            user_email: str,
            user_name: str,
            user_phone: str (optional),
            preferred_date: str (optional),
            preferred_time: str (optional),
            meeting_type: str (optional, default: "consultation"),
            duration_minutes: int (optional, default: 30),
            timezone: str (optional, default: "America/Los_Angeles")
        }
        state: Current conversation state
        
    Returns:
        {success: bool, data: str, error: str}
    """
    try:
        print(f"  📅 Calling book_meeting tool...")
        
        # Extract required arguments
        user_email = args.get("user_email") or state.get("user_email")
        user_name = args.get("user_name") or state.get("user_name")
        
        # Validate required fields
        if not user_email:
            return {
                "success": False,
                "data": None,
                "error": "Missing required argument: user_email"
            }
        
        if not user_name:
            return {
                "success": False,
                "data": None,
                "error": "Missing required argument: user_name"
            }
        
        # Build tool arguments
        tool_args = {
            "user_email": user_email,
            "user_name": user_name
        }
        
        # Add optional fields
        optional_fields = [
            "user_phone", "preferred_date", "preferred_time",
            "meeting_type", "duration_minutes", "timezone"
        ]
        
        for field in optional_fields:
            if args.get(field):
                tool_args[field] = args[field]
            elif field in ["user_phone"] and state.get(field):
                tool_args[field] = state[field]
        
        # Call the actual tool
        result = await book_meeting.ainvoke(tool_args)
        
        print(f"  ✅ Booking tool returned: {len(result)} characters")
        
        return {
            "success": True,
            "data": result,  # Success message with meeting details
            "error": None
        }
        
    except Exception as e:
        print(f"  ❌ Booking tool error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "data": None,
            "error": f"Meeting booking failed: {str(e)}"
        }
```

---

### **Step 3: Verify Multi-Intent Priority Handling**
**File:** `lifeguard-pro-api/core/planner_node.py`

**Current Status:** ✅ Already implemented correctly

The planner already handles multi-intent with proper priority:

**Example from planner prompt:**
```json
{
  "planned_calls": [
    {
      "tool": "rag_search",
      "args": {"query": "CPR courses"},
      "execute": true,
      "priority": 0  // Execute FIRST (lower = first)
    },
    {
      "tool": "get_pricing",
      "args": {"course_name": "CPR", "quantity": 10},
      "execute": true,
      "priority": 1  // Execute SECOND
    }
  ]
}
```

**Priority Rules:**
- `priority: 0` = Highest priority (execute first)
- `priority: 1` = Medium priority
- `priority: 2` = Lower priority
- Tools are sorted by priority in executor (line 137)

**Multi-Intent Examples Already Supported:**

1. **RAG + Pricing** (Common):
   - User: "Tell me about CPR and how much for 10 students"
   - Planner creates: `rag_search` (priority: 0), `get_pricing` (priority: 1)

2. **Pricing + Quote** (Sequential):
   - User: "Send me a quote for BLS for 15 people"
   - Planner creates: `get_pricing` (priority: 0), `quote_send_email` (priority: 1)
   - Quote tool needs pricing data first

3. **RAG + Booking** (Independent):
   - User: "Tell me about instructor courses and book a call"
   - Planner creates: `rag_search` (priority: 0), `book_meeting` (priority: 1)

**No changes needed to planner!**

---

### **Step 4: Update Chat Service Response Formatting**
**File:** `lifeguard-pro-api/services/chat_service_with_context.py`

**Current Issue:** Tool calls are extracted but responses may not properly incorporate tool-specific data

**Review Current Logic:**
```python
# Line ~125: Extract tool_calls
tool_calls = []
for tool_name, tool_data in result.get("tool_results", {}).items():
    if tool_data.get("success"):
        tool_calls.append(tool_name)
```

**This is correct!** It extracts successful tool calls.

**Verify Response Generator:**
The `react_responder_node` should format responses based on tool results.

**Action:** Check if react_responder properly uses pricing/quote/booking data

---

### **Step 5: Testing Strategy**

#### 5.1 Single Tool Tests
Test each tool independently:

**Test 1: Pricing Only**
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-pricing-001",
    "message": "How much is CPR for 1 person?",
    "user_name": "Test User",
    "user_email": "test@example.com"
  }'
```

**Expected:**
- `tool_calls: ["get_pricing"]`
- Response contains pricing information

**Test 2: Booking Only**
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-booking-001",
    "message": "I want to schedule a call tomorrow at 2pm",
    "user_name": "Test User",
    "user_email": "test@example.com"
  }'
```

**Expected:**
- `tool_calls: ["book_meeting"]`
- Response confirms meeting scheduled

**Test 3: Quote Only**
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-quote-001",
    "message": "Send me a quote for Junior Lifeguard for 5 students",
    "user_name": "Test User",
    "user_email": "test@example.com"
  }'
```

**Expected:**
- `tool_calls: ["get_pricing", "quote_send_email"]` (multi-intent)
- Response confirms email sent

#### 5.2 Multi-Intent Tests

**Test 4: RAG + Pricing**
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-multi-001",
    "message": "Tell me about BLS and how much for 10 people",
    "user_name": "Test User",
    "user_email": "test@example.com"
  }'
```

**Expected:**
- `tool_calls: ["rag_search", "get_pricing"]`
- Priority: RAG (0), Pricing (1)
- Response includes course info + pricing

**Test 5: Pricing + Quote + Booking**
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-multi-002",
    "message": "Get me a quote for CPR for 20 students and book a call for tomorrow",
    "user_name": "Test User",
    "user_email": "test@example.com"
  }'
```

**Expected:**
- `tool_calls: ["get_pricing", "quote_send_email", "book_meeting"]`
- Priority: Pricing (0), Quote (1), Booking (2)
- Response confirms all actions

#### 5.3 Error Handling Tests

**Test 6: Missing Course Name**
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-error-001",
    "message": "How much does it cost?",
    "user_name": "Test User",
    "user_email": "test@example.com"
  }'
```

**Expected:**
- Planner asks for course name
- `next_action: "ASK_SLOT"`
- No tools executed yet

**Test 7: Invalid Course**
```bash
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-error-002",
    "message": "How much for XYZ course?",
    "user_name": "Test User",
    "user_email": "test@example.com"
  }'
```

**Expected:**
- Tool executes but returns "Course not found"
- Response suggests using rag_search

---

## 🔄 Priority & Dependency Rules

### Tool Execution Order (Priority System)

**Rule 1: RAG First (Informational Context)**
- When user asks "Tell me about X and Y"
- `rag_search` gets priority: 0
- Other tools get priority: 1+

**Rule 2: Pricing Before Quote**
- Quote needs pricing data
- `get_pricing` gets priority: 0
- `quote_send_email` gets priority: 1

**Rule 3: Independent Tools (Parallel Conceptually)**
- `rag_search` and `book_meeting` can be independent
- Execute in order: RAG (0), Booking (1)

**Rule 4: Complex Multi-Intent**
```
User: "Tell me about First Aid, get pricing for 15 students, send quote, and book a call"

Execution order:
1. rag_search (priority: 0)       - Info about First Aid
2. get_pricing (priority: 1)      - Get pricing data
3. quote_send_email (priority: 2) - Needs pricing from step 2
4. book_meeting (priority: 3)     - Schedule follow-up
```

### Dependency Validation

**In Planner:**
- Already validates slots before setting `execute: true`
- If quote is requested without pricing data, planner will:
  - Add both `get_pricing` and `quote_send_email` to planned_calls
  - Set proper priorities

**In Executor:**
- Tools execute sequentially (not parallel)
- Results from tool N are available to tool N+1 via `tool_results` in state

---

## 📋 Implementation Checklist

### Files to Modify:
- [ ] `tools/__init__.py` - Export all 4 tools
- [ ] `core/executor_node.py` - Implement 3 execution functions
- [ ] `services/chat_service_with_context.py` - Verify response extraction (likely OK)

### Files to Verify (Likely Already Correct):
- [ ] `core/planner_node.py` - Multi-intent & priority (already implemented)
- [ ] `core/react_responder.py` - Response formatting
- [ ] `core/graph.py` - Workflow routing

### Testing:
- [ ] Test 1: Pricing only
- [ ] Test 2: Booking only
- [ ] Test 3: Quote (multi-intent)
- [ ] Test 4: RAG + Pricing
- [ ] Test 5: Pricing + Quote + Booking
- [ ] Test 6: Error - missing slots
- [ ] Test 7: Error - invalid course

---

## 🎯 Expected Outcomes

### After Implementation:

1. **All 4 Tools Working:**
   - ✅ `rag_search` (already working)
   - ✅ `get_pricing` (will work after integration)
   - ✅ `quote_send_email` (will work after integration)
   - ✅ `book_meeting` (will work after integration)

2. **Multi-Intent Queries Handled:**
   - Planner detects multiple intents
   - Tools execute in priority order
   - Response incorporates all tool results

3. **Tool Calls Visible in API:**
   - `tool_calls` array populated correctly
   - Frontend can display which tools were used

4. **Error Handling:**
   - Missing arguments → Ask user
   - Invalid input → Graceful error message
   - Tool failure → Fallback response

---

## 🚀 Implementation Order

**Phase 1:** Core Integration (30 minutes)
1. Update `tools/__init__.py`
2. Update `core/executor_node.py`
3. Verify imports work

**Phase 2:** Testing Single Tools (20 minutes)
4. Test pricing tool
5. Test booking tool
6. Test quote tool (multi-intent)

**Phase 3:** Multi-Intent Testing (20 minutes)
7. Test RAG + Pricing
8. Test Pricing + Quote + Booking
9. Test error scenarios

**Phase 4:** Polish & Documentation (10 minutes)
10. Update API documentation
11. Add to test suite
12. Create examples in README

**Total Estimated Time:** ~80 minutes

---

## 📝 Notes

### Why Tools Are MOCK for Quote/Booking:
- **Quote Tool:** MOCK payment links (Stripe/PayPal)
  - Real version would call Stripe/PayPal APIs
  - Real version would send actual emails via SendGrid/AWS SES
  - For testing, returns formatted text with MOCK links

- **Booking Tool:** MOCK meeting scheduling
  - Real version would use Google Calendar API
  - Real version would create actual Google Meet links
  - For testing, returns formatted text with MOCK meeting details

### Database Requirements:
- **Pricing Tool:** Requires PostgreSQL with:
  - `courses` table (course_id, title, sku)
  - `price_individual` table (unit prices)
  - `price_group` table (group pricing)
  - `price_group_tier` table (tiered pricing)
  - ✅ Already set up from previous phases

### User Info Requirements:
- **Quote Tool:** Requires `user_email`, `user_name`
- **Booking Tool:** Requires `user_email`, `user_name`
- ✅ Already collected via session creation
- ✅ Available in state via `state["user_email"]`, `state["user_name"]`

---

## ✅ Success Criteria

Implementation is complete when:

1. ✅ All 4 tools can be called successfully
2. ✅ Multi-intent queries work with correct priority
3. ✅ `tool_calls` array populated in API responses
4. ✅ Error handling graceful for all edge cases
5. ✅ Test suite passes all 7 test scenarios
6. ✅ Documentation updated
7. ✅ No regression in existing RAG functionality

---

**Ready to proceed with implementation?**

Let me know if you want me to:
1. Start with Phase 1 (Core Integration)
2. Adjust the plan
3. Add more test cases

