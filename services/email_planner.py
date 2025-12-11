"""
Email Tool Planner Service

LLM-driven tool planning for email replies.
Analyzes email content and decides which tools to call.
"""
import logging
import json
from typing import Dict, Any, List, Optional
from api.schemas.email_test import EmailTestPayload, EmailClassificationResult
from email_classification.label_config import LabelConfig
from services.llm_client import LLMClient

logger = logging.getLogger(__name__)


# ============================================================================
# EMAIL PLANNER SYSTEM PROMPT
# ============================================================================

EMAIL_PLANNER_SYSTEM_PROMPT = """You are a tool planner for email reply generation at LifeGuard-Pro.

**CRITICAL: Output ONLY valid JSON. No prose. No explanations. JSON ONLY.**

**Your Job:**
1. Analyze the incoming email content
2. Determine which tools are needed to generate an accurate reply
3. Extract parameters for each tool
4. Create planned_calls (tool invocations)
5. Determine if all required information is available

**Available Tools:**

1. **rag_search(query: str)** - Search knowledge base
   - Use when: Email asks about courses, requirements, policies, locations, general info, "what", "how", "where", "tell me about"
   - Required: query (extract from email subject + body)
   - Example: rag_search({{"query": "CPR training requirements"}})
   
2. **get_pricing(course_name, course_slug, quantity, buyer_category)** - Get pricing
   - Use when: Email mentions price, cost, pricing, "how much", "$", "fee", "charge"
   - Required: course_name OR course_slug, quantity (default: 1)
   - Optional: buyer_category (auto-detect: "individual" if quantity=1, "employer_or_instructor" if quantity>=2)
   - Example: get_pricing({{"course_name": "CPR", "quantity": 10}})
   
3. **get_all_services(buyer_category)** - Get complete services list
   - Use when: Email asks "what services", "all courses", "what do you offer", "complete list", "everything you have"
   - Optional: buyer_category ("individual" or "employer_or_instructor")
   - Example: get_all_services({{"buyer_category": "individual"}})
   
4. **book_meeting(user_email, user_name, preferred_date, preferred_time, ...)** - Schedule meeting
   - Use when: Email explicitly wants to book/schedule (not just asking about it)
   - Required: user_email, user_name
   - Optional: preferred_date, preferred_time, meeting_type, duration_minutes
   - NOTE: Only plan if user explicitly wants to book (e.g., "book a call", "schedule meeting", "I want to talk")
   - Example: book_meeting({{"user_email": "john@example.com", "user_name": "John Smith"}})
   
5. **quote_send_email(course_name, quantity, user_email, user_name, ...)** - Generate quote with payment links
   - Use when: Email explicitly wants to pay, get invoice, payment link, "ready to pay", "send invoice"
   - Required: course_name, quantity, user_email, user_name
   - Optional: pricing_option (4A/4B), payment_methods
   - NOTE: Requires pricing info first - check if pricing_slots are filled
   - Example: quote_send_email({{"course_name": "CPR", "quantity": 10, "user_email": "manager@company.com", "user_name": "Manager"}})

**Label Context:**
This email is classified as: {label_id} ({category})
Allowed tools for this label: {allowed_tools}

**Tool Selection Rules:**
- If email asks general questions → Use rag_search
- If email asks about pricing → Use get_pricing (extract course + quantity)
- If email asks "what services" → Use get_all_services
- If email wants to book → Use book_meeting (only if explicit request)
- If email wants to pay → Use quote_send_email (requires pricing first)
- Multi-tool scenarios are allowed (e.g., rag + pricing)
- Only plan tools that are in allowed_tools list

**Parameter Extraction:**
- Extract course names from email text (look for: "CPR", "lifeguard", "BLS", "First Aid", "Junior Lifeguard", etc.)
- Extract quantity from patterns: "5 employees", "10 students", "for 3 people", "group of 20"
- Extract user info: email from from_email field, name from email signature or use "Customer"
- Extract dates/times: "tomorrow", "next week", "2pm", "morning", etc.
- For buyer_category: infer from quantity (1 = individual, 2+ = employer_or_instructor)

**Preconditions:**
- Set preconditions_met=true if all required parameters are available
- Set preconditions_met=false if missing critical info (e.g., course name for pricing)
- If preconditions_met=false, list missing parameters in "missing" array
- Set execute=true only if preconditions_met=true

**Output Format (JSON only):**
{{
  "intents": ["rag", "pricing"],
  "intent_confidence": {{"rag": 0.92, "pricing": 0.85}},
  "rag_slots": {{
    "query": "extracted query from email"
  }},
  "pricing_slots": {{
    "course_name": "CPR",
    "course_slug": null,
    "quantity": 10,
    "buyer_category": "employer_or_instructor"
  }},
  "get_all_services_slots": {{}},
  "booking_slots": {{}},
  "quote_slots": {{}},
  "planned_calls": [
    {{
      "tool": "rag_search",
      "args": {{"query": "..."}},
      "preconditions_met": true,
      "execute": true,
      "priority": 0,
      "note": "Search for course information"
    }}
  ],
  "next_action": "READY" | "ASK_SLOT" | "NONE",
  "missing_info": []
}}

**Examples:**

INPUT EMAIL:
Subject: What is CPR training?
Body: I want to know about CPR training and how much it costs for 10 employees.

OUTPUT:
{{
  "intents": ["rag", "pricing"],
  "intent_confidence": {{"rag": 0.92, "pricing": 0.88}},
  "rag_slots": {{
    "query": "CPR training what is it"
  }},
  "pricing_slots": {{
    "course_name": "CPR",
    "quantity": 10,
    "buyer_category": "employer_or_instructor"
  }},
  "planned_calls": [
    {{
      "tool": "rag_search",
      "args": {{"query": "CPR training what is it"}},
      "preconditions_met": true,
      "execute": true,
      "priority": 0
    }},
    {{
      "tool": "get_pricing",
      "args": {{"course_name": "CPR", "quantity": 10, "buyer_category": "employer_or_instructor"}},
      "preconditions_met": true,
      "execute": true,
      "priority": 1
    }}
  ],
  "next_action": "READY",
  "missing_info": []
}}

INPUT EMAIL:
Subject: Need pricing
Body: How much does it cost?

OUTPUT:
{{
  "intents": ["pricing"],
  "intent_confidence": {{"pricing": 0.75}},
  "pricing_slots": {{
    "course_name": null,
    "quantity": 1
  }},
  "planned_calls": [
    {{
      "tool": "get_pricing",
      "args": {{}},
      "preconditions_met": false,
      "execute": false,
      "missing": ["course_name"],
      "priority": 0
    }}
  ],
  "next_action": "ASK_SLOT",
  "missing_info": ["course_name"]
}}

**CRITICAL RULES:**
1. Output ONLY valid JSON (no markdown, no prose)
2. Always include: intents, intent_confidence, planned_calls, next_action
3. Set execute=true only when preconditions_met=true
4. Set next_action="READY" when all planned_calls have preconditions_met=true
5. Set next_action="ASK_SLOT" when any planned_call has preconditions_met=false
6. Only plan tools that are in allowed_tools list
7. Extract parameters intelligently from email content
8. Use priority to order execution (lower = execute first, typically rag before pricing)
"""


class EmailPlannerService:
    """Service for planning tool calls based on email content"""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize email planner service
        
        Args:
            llm_client: LLM client instance for planning
        """
        self.llm = llm_client
    
    async def plan_tools(
        self,
        email: EmailTestPayload,
        classification: EmailClassificationResult,
        label_config: LabelConfig
    ) -> Dict[str, Any]:
        """
        Plan which tools to call based on email content
        
        Args:
            email: Email payload
            classification: Classification result
            label_config: Label configuration with allowed tools
            
        Returns:
            Dict with planned_calls and metadata
        """
        try:
            # Build planner prompt
            system_prompt = EMAIL_PLANNER_SYSTEM_PROMPT.format(
                label_id=classification.label_id,
                category=classification.category,
                allowed_tools=", ".join(label_config.allowed_tools) if label_config.allowed_tools else "none"
            )
            
            # Build user content with email
            user_content = f"""Analyze this email and plan tool calls:

From: {email.from_email or "Unknown"}
Subject: {email.subject}
Body:
{email.text}

Plan which tools are needed to generate an accurate reply."""
            
            # Call LLM for planning
            logger.info(f"Planning tools for email: {classification.label_id}")
            planner_output = await self.llm.json_chat(
                system_prompt=system_prompt,
                user_content=user_content,
                max_retries=2
            )
            
            # Validate and normalize output
            validated_output = self._validate_planner_output(planner_output, label_config)
            
            logger.info(f"Planner output: {len(validated_output.get('planned_calls', []))} planned calls")
            for call in validated_output.get('planned_calls', []):
                logger.info(f"  - {call.get('tool')}: preconditions_met={call.get('preconditions_met')}, execute={call.get('execute')}")
            
            return validated_output
            
        except Exception as e:
            logger.error(f"Error in email planner: {e}", exc_info=True)
            # Return fallback plan
            return self._get_fallback_plan()
    
    def _validate_planner_output(
        self,
        planner_output: Dict[str, Any],
        label_config: LabelConfig
    ) -> Dict[str, Any]:
        """
        Validate and normalize planner output
        
        Args:
            planner_output: Raw planner output from LLM
            label_config: Label configuration
            
        Returns:
            Validated and normalized planner output
        """
        # Ensure required fields exist
        validated = {
            "intents": planner_output.get("intents", []),
            "intent_confidence": planner_output.get("intent_confidence", {}),
            "rag_slots": planner_output.get("rag_slots", {}),
            "pricing_slots": planner_output.get("pricing_slots", {}),
            "get_all_services_slots": planner_output.get("get_all_services_slots", {}),
            "booking_slots": planner_output.get("booking_slots", {}),
            "quote_slots": planner_output.get("quote_slots", {}),
            "planned_calls": [],
            "next_action": planner_output.get("next_action", "NONE"),
            "missing_info": planner_output.get("missing_info", [])
        }
        
        # Validate and filter planned_calls
        allowed_tool_map = {
            "rag_search": "rag",
            "get_pricing": "pricing",
            "get_all_services": "get_all_services",
            "book_meeting": "booking",
            "quote_send_email": "payment_link"
        }
        
        # Reverse map for checking allowed tools
        tool_id_to_name = {
            "rag": "rag_search",
            "pricing": "get_pricing",
            "get_all_services": "get_all_services",
            "booking": "book_meeting",
            "payment_link": "quote_send_email"
        }
        
        raw_planned_calls = planner_output.get("planned_calls", [])
        
        for call in raw_planned_calls:
            tool_name = call.get("tool", "")
            
            # Check if tool is allowed for this label
            tool_id = allowed_tool_map.get(tool_name)
            if not tool_id:
                # Try reverse lookup (tool_name might already be a tool_id)
                if tool_name in tool_id_to_name:
                    tool_id = tool_name
                    tool_name = tool_id_to_name[tool_name]
                else:
                    logger.warning(f"Unknown tool name: {tool_name}, skipping")
                    continue
            
            if tool_id not in label_config.allowed_tools:
                logger.warning(f"Planner suggested {tool_name} ({tool_id}) but it's not in allowed_tools for {label_config.id}, skipping")
                continue
            
            # Validate call structure
            if not isinstance(call, dict):
                continue
            
            if "tool" not in call:
                continue
            
            # Normalize call
            normalized_call = {
                "tool": tool_name,
                "args": call.get("args", {}),
                "preconditions_met": call.get("preconditions_met", False),
                "execute": call.get("execute", False),
                "priority": call.get("priority", 0),
                "note": call.get("note", ""),
                "missing": call.get("missing", [])
            }
            
            # Ensure execute is only true if preconditions_met is true
            if normalized_call["execute"] and not normalized_call["preconditions_met"]:
                normalized_call["execute"] = False
                logger.warning(f"Fixed execute flag for {tool_name}: preconditions_met=false but execute=true")
            
            validated["planned_calls"].append(normalized_call)
        
        # Determine next_action if not set correctly
        if validated["next_action"] not in ["READY", "ASK_SLOT", "NONE"]:
            # Auto-determine based on planned_calls
            all_met = all(
                call.get("preconditions_met", False)
                for call in validated["planned_calls"]
            )
            if validated["planned_calls"] and all_met:
                validated["next_action"] = "READY"
            elif validated["planned_calls"]:
                validated["next_action"] = "ASK_SLOT"
            else:
                validated["next_action"] = "NONE"
        
        return validated
    
    def _get_fallback_plan(self) -> Dict[str, Any]:
        """
        Get fallback plan when planner fails
        
        Returns:
            Default planner output
        """
        return {
            "intents": [],
            "intent_confidence": {},
            "rag_slots": {},
            "pricing_slots": {},
            "get_all_services_slots": {},
            "booking_slots": {},
            "quote_slots": {},
            "planned_calls": [],
            "next_action": "NONE",
            "missing_info": []
        }


__all__ = ['EmailPlannerService', 'EMAIL_PLANNER_SYSTEM_PROMPT']

