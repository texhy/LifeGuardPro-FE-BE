"""
Executor Node - Phase 2.1 (Tool Execution)

This node executes tools based on the planner's decisions.

Sub-Phase 2.1: Basic execution (RAG vector search only)
Sub-Phase 2.2+: Will add advanced retrieval techniques

Confidence: 95% ✅

Author: Phase 2 Implementation
"""

from typing import Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()

# Import tool executors
from core.rag_executor import execute_rag_search

# Import actual tools for execution
from tools.get_pricing_tool import get_pricing
from tools.get_all_services_tool import get_all_services
from tools.book_meeting_tool import book_meeting
from tools.quote_send_email_tool import quote_send_email


# ============================================================================
# TOOL EXECUTION FUNCTIONS
# ============================================================================

async def execute_pricing(args: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute pricing tool - Looks up course pricing in database
    
    Args:
        args: {
            course_name: str (optional, if course_slug not provided),
            course_slug: str (optional, preferred over course_name),
            quantity: int,
            buyer_category: str (optional)
        }
        state: Current conversation state
        
    Returns:
        {success: bool, data: str, error: str, needs_disambiguation: bool}
    """
    try:
        print(f"  💰 Calling get_pricing tool...")
        
        # Extract arguments - prioritize course_slug over course_name
        course_slug = args.get("course_slug")
        course_name = args.get("course_name") or args.get("course")  # Support legacy 'course' key
        quantity = args.get("quantity", 1)
        
        # Get buyer_category from args, state, or infer from quantity
        buyer_category = args.get("buyer_category")
        if not buyer_category:
            # Try to get from state pricing_slots
            buyer_category = state.get("pricing_slots", {}).get("buyer_category")
        if not buyer_category:
            # Infer from quantity
            buyer_category = "individual" if quantity == 1 else "employer_or_instructor"
        
        # Validate that at least one identifier is provided
        if not course_slug and not course_name:
            return {
                "success": False,
                "data": None,
                "error": "Missing required argument: either course_slug or course_name must be provided"
            }
        
        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity < 1:
                quantity = 1
        except (ValueError, TypeError):
            quantity = 1
        
        # Build tool arguments - prioritize course_slug
        tool_args = {
            "quantity": quantity,
            "buyer_category": buyer_category
        }
        
        if course_slug:
            tool_args["course_slug"] = course_slug
            print(f"     Using course_slug: {course_slug}")
        else:
            tool_args["course_name"] = course_name
            print(f"     Using course_name: {course_name}")
        
        # Call the actual tool
        result = await get_pricing.ainvoke(tool_args)
        
        # Check if result is a disambiguation message (contains emoji or specific patterns)
        # Also check if it's actual pricing (has $ or 💰 emoji)
        has_pricing = "$" in result or "💰" in result
        needs_disambiguation = (
            ("❓" in result or 
             "multiple courses" in result.lower() or
             "which one" in result.lower() or
             "options" in result.lower()) 
            and not has_pricing  # If it has pricing, it's not disambiguation
        )
        
        print(f"  ✅ Pricing tool returned: {len(result)} characters")
        print(f"     Has pricing markers: ${has_pricing} (${'$' in result}, 💰{'💰' in result})")
        
        if needs_disambiguation:
            print(f"  ❓ Disambiguation needed - returning suggestions to user")
        elif has_pricing:
            print(f"  💰 Pricing found in result - marking as success")
        
        return {
            "success": has_pricing or (not needs_disambiguation and not result.startswith("❌")),  # Success if has pricing or not error
            "data": result,  # Formatted pricing string or disambiguation message
            "error": None if (has_pricing or not result.startswith("❌")) else "Pricing lookup failed",
            "needs_disambiguation": needs_disambiguation
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


async def execute_all_services(args: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute get_all_services tool - Retrieves ALL services hierarchically
    
    Args:
        args: {
            buyer_category: str (optional),
            program_slug: str (optional) - Filter by program
        }
        state: Current conversation state
        
    Returns:
        {success: bool, data: str, error: str}
    """
    try:
        print(f"  📋 Calling get_all_services tool...")
        
        # Get buyer_category from args, state, or use None
        buyer_category = args.get("buyer_category")
        if not buyer_category:
            # Try to get from state pricing_slots
            buyer_category = state.get("pricing_slots", {}).get("buyer_category")
        if not buyer_category:
            # Try to get from state all_services_slots
            buyer_category = state.get("all_services_slots", {}).get("buyer_category")
        
        # Get program_slug from args or state (for filtered queries)
        program_slug = args.get("program_slug")
        if not program_slug:
            program_slug = state.get("program_slug")
        
        # Build tool arguments
        tool_args = {}
        if buyer_category:
            tool_args["buyer_category"] = buyer_category
        if program_slug:
            tool_args["program_slug"] = program_slug
            print(f"     Filtering by program_slug: {program_slug}")
        
        # Call the actual tool
        result = await get_all_services.ainvoke(tool_args)
        
        print(f"  ✅ All services tool returned: {len(result)} characters")
        
        return {
            "success": not result.startswith("❌"),  # Success if not error
            "data": result,  # Formatted services list
            "error": None if not result.startswith("❌") else "Failed to retrieve services"
        }
        
    except Exception as e:
        print(f"  ❌ All services tool error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "data": None,
            "error": f"All services lookup failed: {str(e)}"
        }


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
        state: Current conversation state (can provide user_email, user_name, user_phone)
        
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
                "error": "Missing required argument: user_email (not in args or state)"
            }
        
        if not user_name:
            return {
                "success": False,
                "data": None,
                "error": "Missing required argument: user_name (not in args or state)"
            }
        
        # Validate quantity
        try:
            quantity = int(quantity)
            if quantity < 1:
                quantity = 1
        except (ValueError, TypeError):
            quantity = 1
        
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
        state: Current conversation state (can provide user_email, user_name, user_phone)
        
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
                "error": "Missing required argument: user_email (not in args or state)"
            }
        
        if not user_name:
            return {
                "success": False,
                "data": None,
                "error": "Missing required argument: user_name (not in args or state)"
            }
        
        # Build tool arguments
        tool_args = {
            "user_email": user_email,
            "user_name": user_name
        }
        
        # Add optional fields from args
        optional_fields = [
            "user_phone", "preferred_date", "preferred_time",
            "meeting_type", "duration_minutes", "timezone"
        ]
        
        for field in optional_fields:
            if args.get(field):
                tool_args[field] = args[field]
            elif field == "user_phone" and state.get(field):
                # Only pull user_phone from state if not in args
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


# ============================================================================
# MAIN EXECUTOR NODE
# ============================================================================

async def executor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute planned tool calls
    
    This node:
    1. Checks if execution should proceed (next_action == DY)
    2. Gets all planned calls with execute=True
    3. Executes each tool in priority order
    4. Stores results in state.tool_results
    5. Handles errors gracefully
    
    Confidence: 95% ✅
    
    Args:
        state: Current graph state with planned_calls
        
    Returns:
        Updated state with tool_results
    """
    print(f"\n{'='*60}")
    print(f"⚙️  EXECUTOR NODE (Phase 2.1 - Tool Execution)")
    print(f"{'='*60}")
    
    # Step 1: Check if we should execute
    next_action = state.get("next_action", "NONE")
    
    if next_action != "READY":
        print(f"⏭  Skipping execution: next_action={next_action}")
        print(f"   (Only execute when next_action=READY)")
        print(f"{'='*60}\n")
        return state
    
    # Step 2: Get planned calls
    planned_calls = state.get("planned_calls", [])
    
    if not planned_calls:
        print(f"⏭  No planned calls to execute")
        print(f"{'='*60}\n")
        return state
    
    # Step 3: Filter to executable calls
    executable_calls = [
        call for call in planned_calls 
        if call.get("execute", False) and call.get("preconditions_met", False)
    ]
    
    if not executable_calls:
        print(f"⏭  No executable calls (all have execute=False or preconditions not met)")
        print(f"{'='*60}\n")
        return state
    
    print(f"\n📋 Found {len(executable_calls)} executable calls:")
    for i, call in enumerate(executable_calls, 1):
        print(f"   {i}. {call['tool']} (priority: {call.get('priority', 0)})")
    
    # Step 4: Sort by priority (lower priority = execute first)
    executable_calls.sort(key=lambda x: x.get("priority", 0))
    
    # Step 5: Execute each tool
    tool_results = {}
    execution_errors = []
    
    for i, call in enumerate(executable_calls, 1):
        tool_name = call["tool"]
        args = call["args"]
        
        print(f"\n🔧 Executing call {i}/{len(executable_calls)}: {tool_name}")
        print(f"   Args: {args}")
        
        try:
            # Route to appropriate executor
            if tool_name == "rag_search":
                result = await execute_rag_search(args, state)
                tool_results["rag_search"] = result
                
                # Show result summary
                if result.get("success"):
                    num_chunks = len(result.get("chunks", []))
                    confidence = result.get("retrieval_confidence", 0)
                    print(f"   ✅ Success: {num_chunks} chunks retrieved")
                    print(f"   📊 Confidence: {confidence:.2%}")
                else:
                    error = result.get("error", "Unknown error")
                    print(f"   ❌ Failed: {error}")
                    execution_errors.append(f"rag_search: {error}")
            
            elif tool_name == "get_pricing":
                result = await execute_pricing(args, state)
                tool_results["get_pricing"] = result
                
                # Debug logging
                print(f"   📊 Pricing result details:")
                print(f"      success: {result.get('success')}")
                print(f"      needs_disambiguation: {result.get('needs_disambiguation')}")
                print(f"      has_data: {bool(result.get('data'))}")
                print(f"      data_length: {len(result.get('data', ''))}")
                if result.get('data'):
                    data_preview = result.get('data', '')[:100]
                    print(f"      data_preview: {data_preview}...")
                    print(f"      has_dollar: {'$' in result.get('data', '')}")
                    print(f"      has_emoji: {'💰' in result.get('data', '')}")
                
                if result.get("success"):
                    print(f"   ✅ Success: Pricing retrieved")
                elif result.get("needs_disambiguation"):
                    print(f"   ❓ Disambiguation: {len(result.get('data', ''))} chars")
                else:
                    error = result.get("error", "Unknown error")
                    print(f"   ❌ Failed: {error}")
                    execution_errors.append(f"get_pricing: {error}")
            
            elif tool_name == "get_all_services":
                result = await execute_all_services(args, state)
                tool_results["get_all_services"] = result
                
                if result.get("success"):
                    print(f"   ✅ Success: All services retrieved ({len(result.get('data', ''))} chars)")
                else:
                    error = result.get("error", "Unknown error")
                    print(f"   ❌ Failed: {error}")
                    execution_errors.append(f"get_all_services: {error}")
            
            elif tool_name == "quote_send_email":
                result = await execute_quote(args, state)
                tool_results["quote_send_email"] = result
                
                if not result.get("success"):
                    error = result.get("error", "Unknown error")
                    print(f"   ⚠️  Not implemented yet: {error}")
                    execution_errors.append(f"quote_send_email: {error}")
            
            elif tool_name == "book_meeting":
                result = await execute_booking(args, state)
                tool_results["book_meeting"] = result
                
                if not result.get("success"):
                    error = result.get("error", "Unknown error")
                    print(f"   ⚠️  Not implemented yet: {error}")
                    execution_errors.append(f"book_meeting: {error}")
            
            else:
                error_msg = f"Unknown tool: {tool_name}"
                print(f"   ❌ Error: {error_msg}")
                execution_errors.append(error_msg)
                tool_results[tool_name] = {
                    "success": False,
                    "error": error_msg
                }
        
        except Exception as e:
            error_msg = f"{tool_name} execution failed: {str(e)}"
            print(f"   ❌ Exception: {error_msg}")
            execution_errors.append(error_msg)
            tool_results[tool_name] = {
                "success": False,
                "error": error_msg
            }
            
            # Continue with other tools despite error
            import traceback
            traceback.print_exc()
    
    # Step 6: Update state with results
    print(f"\n📊 EXECUTION SUMMARY:")
    print(f"   Total calls executed: {len(executable_calls)}")
    print(f"   Successful: {sum(1 for r in tool_results.values() if r.get('success'))}")
    print(f"   Failed: {sum(1 for r in tool_results.values() if not r.get('success'))}")
    if execution_errors:
        print(f"   Errors: {len(execution_errors)}")
    print(f"{'='*60}\n")
    
    # Return updated state
    new_state = {
        **state,
        "tool_results": tool_results,
        "execution_errors": execution_errors
    }
    
    return new_state


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'executor_node',
    'execute_rag_search',
    'execute_pricing',
    'execute_quote',
    'execute_booking'
]

