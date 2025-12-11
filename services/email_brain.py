"""
Email Brain Service

Generates email replies using label-specific prompts and RAG + tools integration
Uses LLM-driven tool planning (similar to chatbot planner pattern)
"""
import logging
from typing import List, Dict, Any, Optional
from api.schemas.email_test import EmailTestPayload, EmailClassificationResult
from email_classification.label_config import get_label_config
from services.llm_client import LLMClient
from services.email_planner import EmailPlannerService

# Import tools for direct execution
from tools.rag_search_tool import rag_search
from tools.get_pricing_tool import get_pricing
from tools.get_all_services_tool import get_all_services
from tools.book_meeting_tool import book_meeting
from tools.quote_send_email_tool import quote_send_email

logger = logging.getLogger(__name__)


class EmailBrainService:
    """Service for generating email replies with label-specific prompts and tools"""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize email brain service
        
        Args:
            llm_client: LLM client instance for reply generation
        """
        self.llm = llm_client
        self.planner = EmailPlannerService(llm_client)
        
        # Tool registry mapping tool IDs to actual tool functions
        self.tool_registry = {
            "rag": {
                "id": "rag",
                "name": "rag_search",
                "function": rag_search,
                "description": "Search the knowledge base for course information, requirements, and FAQs"
            },
            "pricing": {
                "id": "pricing",
                "name": "get_pricing",
                "function": get_pricing,
                "description": "Look up course pricing information"
            },
            "get_all_services": {
                "id": "get_all_services",
                "name": "get_all_services",
                "function": get_all_services,
                "description": "Get complete list of all courses and services"
            },
            "booking": {
                "id": "booking",
                "name": "book_meeting",
                "function": book_meeting,
                "description": "Schedule a virtual consultation meeting"
            },
            "payment_link": {
                "id": "payment_link",
                "name": "quote_send_email",
                "function": quote_send_email,
                "description": "Generate a quote with payment links (Stripe/PayPal)"
            },
        }
    
    async def generate_reply(
        self,
        email: EmailTestPayload,
        classification: EmailClassificationResult,
    ) -> Dict[str, Any]:
        """
        Generate email reply using label-specific prompt and tools
        
        Args:
            email: Original email payload
            classification: Classification result with label_id
            
        Returns:
            Dict with:
                - reply_text: Generated reply
                - used_tools: List of tool IDs used
                - raw_model_output: Full response for debugging
        """
        try:
            # Get label configuration
            cfg = get_label_config(classification.label_id)
            
            # Step 1: Call planner to decide which tools to use
            logger.info(f"Calling email planner for label: {classification.label_id}")
            planner_result = await self.planner.plan_tools(
                email=email,
                classification=classification,
                label_config=cfg
            )
            
            planned_calls = planner_result.get("planned_calls", [])
            next_action = planner_result.get("next_action", "NONE")
            
            logger.info(f"Planner result: {len(planned_calls)} planned calls, next_action={next_action}")
            
            # Step 2: Execute tools from planned_calls
            tool_results = {}
            used_tools = []
            missing_info = []
            
            # Filter to executable calls
            executable_calls = [
                call for call in planned_calls
                if call.get("execute", True) and call.get("preconditions_met", True)
            ]
            
            # Sort by priority (lower = execute first)
            executable_calls.sort(key=lambda x: x.get("priority", 0))
            
            # Execute each tool
            for call in executable_calls:
                tool_name = call.get("tool", "")
                args = call.get("args", {})
                
                try:
                    logger.info(f"Executing tool: {tool_name} with args: {args}")
                    
                    if tool_name == "rag_search":
                        result = await rag_search.ainvoke(args)
                        tool_results["rag"] = result
                        used_tools.append("rag")
                        logger.info(f"RAG search completed, {len(result)} chars returned")
                    
                    elif tool_name == "get_pricing":
                        result = await get_pricing.ainvoke(args)
                        tool_results["pricing"] = result
                        used_tools.append("pricing")
                        logger.info(f"Pricing lookup completed")
                    
                    elif tool_name == "get_all_services":
                        result = await get_all_services.ainvoke(args)
                        tool_results["get_all_services"] = result
                        used_tools.append("get_all_services")
                        logger.info(f"Get all services completed")
                    
                    elif tool_name == "book_meeting":
                        # Ensure required fields are present
                        if not args.get("user_email") and email.from_email:
                            args["user_email"] = email.from_email
                        if not args.get("user_name"):
                            args["user_name"] = "Customer"
                        
                        result = await book_meeting.ainvoke(args)
                        tool_results["booking"] = result
                        used_tools.append("booking")
                        logger.info(f"Booking completed")
                    
                    elif tool_name == "quote_send_email":
                        # Ensure required fields are present
                        if not args.get("user_email") and email.from_email:
                            args["user_email"] = email.from_email
                        if not args.get("user_name"):
                            args["user_name"] = "Customer"
                        
                        result = await quote_send_email.ainvoke(args)
                        tool_results["payment_link"] = result
                        used_tools.append("payment_link")
                        logger.info(f"Quote generation completed")
                    
                except Exception as e:
                    logger.error(f"Tool {tool_name} execution error: {e}", exc_info=True)
                    tool_results[tool_name] = f"Error executing {tool_name}: {str(e)}"
            
            # Collect missing information from non-executable calls
            non_executable_calls = [
                call for call in planned_calls
                if not (call.get("execute", True) and call.get("preconditions_met", True))
            ]
            
            for call in non_executable_calls:
                missing = call.get("missing", [])
                if missing:
                    missing_info.extend(missing)
            
            # Get available tools for prompt formatting
            available_tools = self._get_tools_for_label(cfg.allowed_tools)
            
            # Build system prompt with tool results
            tool_results_text = self._format_tool_results(tool_results, available_tools)
            
            system_prompt = cfg.system_prompt + """

You have access to tools and their results. Use the information below to craft your reply.

Tool Results:
""" + tool_results_text + """

When you reply:
- Use the information from tools to provide accurate, specific answers.
- Do NOT mention the tools by name in your reply.
- Just write the final email the human should receive.
- Be natural, helpful, and professional.
- Include specific information from tools (prices, course details, links, etc.).
- If tool results contain errors, acknowledge that you're looking into it.
"""
            
            # Add missing information handling if needed
            if missing_info and next_action == "ASK_SLOT":
                missing_text = "\n\nMissing Information:\n"
                missing_text += "The following information is needed but not provided in the email:\n"
                for info in set(missing_info):  # Remove duplicates
                    missing_text += f"- {info}\n"
                missing_text += "\nAsk for this information in a friendly, helpful way in your reply."
                system_prompt += missing_text
            
            # Build user content with email context
            user_content = f"""Here is the incoming email you are replying to:

From: {email.from_email or "Unknown"}
To: {email.to_email or "Lifeguard-Pro"}
Subject: {email.subject}

Body:
{email.text}

Generate a helpful, professional reply based on the label classification ({classification.label_id}).
Use the tool results above to provide accurate information.
"""
            
            # Generate reply using LLM
            result = await self.llm.email_agent(
                system_prompt=system_prompt,
                user_content=user_content,
                tools=available_tools,
            )
            
            reply_text = result.get("reply_text", "").strip()
            
            # If no reply generated, provide fallback
            if not reply_text:
                reply_text = self._generate_fallback_reply(cfg, classification)
            
            return {
                "reply_text": reply_text,
                "used_tools": used_tools,
                "raw_model_output": result.get("raw_model_output", {}),
            }
            
        except Exception as e:
            logger.error(f"Error generating reply: {str(e)}", exc_info=True)
            # Return fallback reply
            cfg = get_label_config(classification.label_id)
            return {
                "reply_text": self._generate_fallback_reply(cfg, classification),
                "used_tools": [],
                "raw_model_output": {"error": str(e)},
            }
    
    def _format_tool_results(self, tool_results: Dict[str, str], available_tools: List[Dict]) -> str:
        """
        Format tool results for inclusion in system prompt
        
        Args:
            tool_results: Dict of tool_id -> result string
            available_tools: List of available tool definitions
            
        Returns:
            Formatted string with tool results
        """
        if not tool_results:
            return "No tools were executed."
        
        formatted = []
        for tool_id, result in tool_results.items():
            tool_name = next((t["name"] for t in available_tools if t["id"] == tool_id), tool_id)
            formatted.append(f"\n{tool_name.upper()} Results:\n{result}")
        
        return "\n".join(formatted)
    
    def _get_tools_for_label(self, allowed_tool_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get tool definitions for allowed tool IDs
        
        Args:
            allowed_tool_ids: List of tool IDs (e.g., ["pricing", "booking"])
            
        Returns:
            List of tool definition dicts
        """
        tools = []
        for tool_id in allowed_tool_ids:
            if tool_id in self.tool_registry:
                tools.append(self.tool_registry[tool_id])
        return tools
    
    def _generate_fallback_reply(self, cfg, classification: EmailClassificationResult) -> str:
        """
        Generate a fallback reply if LLM generation fails
        
        Args:
            cfg: LabelConfig instance
            classification: Classification result
            
        Returns:
            Fallback reply text
        """
        fallbacks = {
            "BUY_NOW": (
                "Thank you for your interest in our training courses! "
                "I'd be happy to help you with pricing and booking. "
                "Could you let me know which course you're interested in and your preferred dates?"
            ),
            "BUY_LATER": (
                "Thank you for your interest! I understand you're planning for the future. "
                "I'd be happy to send you information about our upcoming course dates and pricing. "
                "Feel free to reach out when you're ready to move forward!"
            ),
            "FOLLOW_UP": (
                "Thank you for following up! I'm here to help answer any questions you have. "
                "Is there anything specific you'd like to know more about?"
            ),
            "CUSTOMER_SERVICE": (
                "Thank you for reaching out! I'm sorry to hear you're experiencing an issue. "
                "I'll do my best to help resolve this. Could you provide a bit more detail about what you need?"
            ),
            "OBJECTION": (
                "Thank you for sharing your concerns. I'd be happy to address them and find a solution that works for you. "
                "Could you tell me a bit more about what's holding you back?"
            ),
            "NEUTRAL": (
                "Thank you for contacting Lifeguard-Pro! I'd be happy to help you with information about our training courses. "
                "What would you like to know more about?"
            ),
        }
        
        return fallbacks.get(cfg.id, fallbacks["NEUTRAL"])

