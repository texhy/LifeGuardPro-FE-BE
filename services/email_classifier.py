"""
Email Classification Service

LLM-based email classification into internal labels (BUY_NOW, BUY_LATER, etc.)
"""
import logging
from typing import Tuple
from api.schemas.email_test import EmailTestPayload, EmailClassificationResult
from email_classification.label_config import LABEL_CONFIGS, get_label_config
from services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class EmailClassificationService:
    """Service for classifying incoming emails using LLM"""
    
    def __init__(self, llm_client: LLMClient):
        """
        Initialize email classification service
        
        Args:
            llm_client: LLM client instance for classification
        """
        self.llm = llm_client
    
    async def classify_email(self, email: EmailTestPayload) -> EmailClassificationResult:
        """
        Classify an incoming email into a label
        
        Args:
            email: Email payload with subject and text
            
        Returns:
            EmailClassificationResult with label_id, gmail_label, category, confidence
        """
        try:
            subject = (email.subject or "").strip()
            text = (email.text or "").strip()
            
            # 1) Rule-based pre-checks (auto-reply, bounce, etc.)
            if self._is_obvious_auto_reply(subject, text):
                logger.info("Email detected as auto-reply, returning NEUTRAL")
                cfg = LABEL_CONFIGS["NEUTRAL"]
                return EmailClassificationResult(
                    label_id=cfg.id,
                    gmail_label=cfg.gmail_label,
                    category="auto_reply",
                    confidence=0.99,
                )
            
            # 2) LLM-based classification
            labels_description = "\n".join(
                f"- {cfg.id}: {cfg.description} (Gmail label: {cfg.gmail_label})"
                for cfg in LABEL_CONFIGS.values()
            )
            
            available_label_ids = [cfg.id for cfg in LABEL_CONFIGS.values()]
            
            system_prompt = f"""You are an email triage assistant for Lifeguard-Pro, a company that sells lifeguard, CPR, and first aid training.

Your job is to read an incoming email and choose the single best label.

Available labels:
{labels_description}

Return a JSON object ONLY with the keys:
- "label_id": one of {available_label_ids}
- "category": a short high-level category such as "sales", "support", "neutral"
- "confidence": float between 0 and 1 representing your confidence

Guidelines:
- BUY_NOW: Lead explicitly wants to book/pay now or ASAP (e.g., "ready to book", "send payment link", "I want to enroll today")
- BUY_LATER: Lead is interested but wants to wait (e.g., "maybe next month", "not ready yet", "thinking about it")
- FOLLOW_UP: This is a follow-up to a previous conversation (e.g., "following up", "you mentioned", "as discussed")
- CUSTOMER_SERVICE: Existing student needs help (e.g., "lost certificate", "reschedule", "refund", "problem with")
- OBJECTION: Lead raises concerns (e.g., "too expensive", "schedule doesn't work", "location too far")
- NEUTRAL: General question or unclear intent (e.g., "what courses", "tell me more", "information")

Be decisive - choose the single best label based on the primary intent."""
            
            user_content = f"Subject: {subject}\n\nBody:\n{text}"
            
            raw = await self.llm.json_chat(
                system_prompt=system_prompt,
                user_content=user_content,
            )
            
            # Parse and validate result
            try:
                label_id = raw.get("label_id", "NEUTRAL")
                
                # Validate label_id exists
                if label_id not in LABEL_CONFIGS:
                    logger.warning(f"Invalid label_id '{label_id}' from LLM, falling back to NEUTRAL")
                    label_id = "NEUTRAL"
                
                cfg = get_label_config(label_id)
                
                category = raw.get("category", "unknown")
                confidence = float(raw.get("confidence", 0.5))
                
                # Clamp confidence to [0, 1]
                confidence = max(0.0, min(1.0, confidence))
                
                logger.info(f"Email classified as {label_id} (category: {category}, confidence: {confidence:.2f})")
                
                return EmailClassificationResult(
                    label_id=cfg.id,
                    gmail_label=cfg.gmail_label,
                    category=category,
                    confidence=confidence,
                )
                
            except (KeyError, ValueError, TypeError) as e:
                logger.error(f"Classification parsing error: {e}, raw={raw}")
                cfg = LABEL_CONFIGS["NEUTRAL"]
                return EmailClassificationResult(
                    label_id=cfg.id,
                    gmail_label=cfg.gmail_label,
                    category="fallback",
                    confidence=0.0,
                )
            
        except Exception as e:
            logger.error(f"Error classifying email: {str(e)}", exc_info=True)
            # Return default classification on error
            cfg = LABEL_CONFIGS["NEUTRAL"]
            return EmailClassificationResult(
                label_id=cfg.id,
                gmail_label=cfg.gmail_label,
                category="error",
                confidence=0.0,
            )
    
    def _is_obvious_auto_reply(self, subject: str, text: str) -> bool:
        """
        Check if email is an obvious auto-reply
        
        Args:
            subject: Email subject
            text: Email text content
            
        Returns:
            True if auto-reply detected
        """
        combined = (subject + " " + text).lower()
        keywords = [
            "out of office",
            "automatic reply",
            "auto-reply",
            "do not reply",
            "noreply",
            "no-reply",
            "vacation",
            "away from office"
        ]
        return any(keyword in combined for keyword in keywords)

