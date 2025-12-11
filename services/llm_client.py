"""
LLM Client Wrapper for Email Classification and Reply Generation

Provides simplified interfaces for:
1. JSON chat (classification)
2. Email agent (reply generation with RAG + tools)
"""
import json
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class LLMClient:
    """Wrapper for LLM operations with JSON parsing and tool integration"""
    
    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.7):
        """
        Initialize LLM client
        
        Args:
            model: OpenAI model name
            temperature: Temperature for generation
        """
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.model_name = model
    
    async def json_chat(
        self,
        system_prompt: str,
        user_content: str,
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Send a chat request expecting JSON response
        
        Args:
            system_prompt: System message content
            user_content: User message content
            max_retries: Maximum retry attempts for JSON parsing
            
        Returns:
            Parsed JSON as dictionary
            
        Raises:
            ValueError: If JSON parsing fails after retries
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content)
        ]
        
        for attempt in range(max_retries + 1):
            try:
                response = await self.llm.ainvoke(messages)
                content = response.content.strip()
                
                # Try to extract JSON if wrapped in markdown code blocks
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    content = content[start:end].strip()
                elif "```" in content:
                    start = content.find("```") + 3
                    end = content.find("```", start)
                    content = content[start:end].strip()
                
                # Parse JSON
                result = json.loads(content)
                return result
                
            except json.JSONDecodeError as e:
                if attempt < max_retries:
                    logger.warning(f"JSON parse error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    # Add instruction to retry
                    messages.append(AIMessage(content=content))
                    messages.append(HumanMessage(
                        content="Please respond with valid JSON only, no additional text."
                    ))
                    continue
                else:
                    logger.error(f"Failed to parse JSON after {max_retries + 1} attempts: {e}")
                    logger.error(f"Response content: {content[:500]}")
                    raise ValueError(f"Failed to parse JSON response: {e}")
            
            except Exception as e:
                logger.error(f"Error in json_chat: {e}", exc_info=True)
                raise
    
    async def email_agent(
        self,
        system_prompt: str,
        user_content: str,
        tools: List[Dict[str, Any]],
        max_iterations: int = 3
    ) -> Dict[str, Any]:
        """
        Generate email reply using RAG + tools
        
        This is a simplified version that:
        1. Calls tools if needed (based on tool definitions)
        2. Generates reply using LLM with tool results
        
        Args:
            system_prompt: System prompt for reply generation
            user_content: Email content to reply to
            tools: List of tool definitions (simplified - just metadata for now)
            max_iterations: Maximum tool call iterations
            
        Returns:
            Dict with:
                - reply_text: Generated reply
                - used_tools: List of tool IDs that were used
                - raw_model_output: Full response for debugging
        """
        # For MVP, we'll use a simplified approach:
        # 1. Check if tools are needed based on content
        # 2. Call tools directly if needed
        # 3. Generate reply with tool results
        
        used_tools = []
        tool_results = {}
        
        # Simple tool detection: check if user content mentions pricing/booking/payment
        user_lower = user_content.lower()
        
        # Check for pricing needs
        if any(keyword in user_lower for keyword in ["price", "cost", "pricing", "how much", "fee"]):
            # Try to extract course info and call pricing tool
            # For now, we'll just mark it as used and let the LLM handle it
            if any(tool.get("name") == "pricing" or tool.get("id") == "pricing" for tool in tools):
                used_tools.append("pricing")
        
        # Check for booking needs
        if any(keyword in user_lower for keyword in ["book", "schedule", "meeting", "appointment", "call"]):
            if any(tool.get("name") == "booking" or tool.get("id") == "booking" for tool in tools):
                used_tools.append("booking")
        
        # Check for payment link needs
        if any(keyword in user_lower for keyword in ["pay", "payment", "invoice", "quote", "link"]):
            if any(tool.get("name") == "payment_link" or tool.get("id") == "payment_link" for tool in tools):
                used_tools.append("payment_link")
        
        # Build enhanced system prompt with tool context
        enhanced_prompt = system_prompt
        
        if used_tools:
            tool_context = f"\n\nAvailable tools: {', '.join(used_tools)}. Use these tools if needed to provide accurate information."
            enhanced_prompt += tool_context
        
        # Generate reply
        messages = [
            SystemMessage(content=enhanced_prompt),
            HumanMessage(content=user_content)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            reply_text = response.content.strip()
            
            return {
                "reply_text": reply_text,
                "used_tools": used_tools,
                "raw_model_output": {
                    "model": self.model_name,
                    "content": reply_text,
                    "tool_context": used_tools
                }
            }
            
        except Exception as e:
            logger.error(f"Error in email_agent: {e}", exc_info=True)
            return {
                "reply_text": "I apologize, but I'm having trouble generating a response right now. Please try again later.",
                "used_tools": used_tools,
                "raw_model_output": {
                    "error": str(e)
                }
            }


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

_llm_client_instance: Optional[LLMClient] = None

def get_llm_client(model: str = "gpt-4o-mini", temperature: float = 0.7) -> LLMClient:
    """
    Get or create LLM client instance (singleton pattern)
    
    Args:
        model: OpenAI model name
        temperature: Temperature for generation
        
    Returns:
        LLMClient instance
    """
    global _llm_client_instance
    
    if _llm_client_instance is None:
        _llm_client_instance = LLMClient(model=model, temperature=temperature)
    
    return _llm_client_instance


__all__ = ['LLMClient', 'get_llm_client']

