"""
Email Classification Service
Handles email classification logic with low coupling to other services
"""
import logging
from typing import Dict, Any, List
from api.schemas.email import EmailPayload, EmailClassificationResponse

logger = logging.getLogger(__name__)


class EmailClassificationService:
    """Service for classifying incoming emails"""
    
    def __init__(self):
        """Initialize the email classification service"""
        pass
    
    async def classify_email(self, email: EmailPayload) -> EmailClassificationResponse:
        """
        Classify an incoming email and determine appropriate actions
        
        Args:
            email: Email payload from n8n
            
        Returns:
            EmailClassificationResponse with classification results
        """
        try:
            # Extract email content for analysis (handle None/empty values)
            subject_lower = (email.subject or "").lower()
            text_lower = (email.text or "").lower()
            
            # Basic classification logic (can be enhanced with ML/AI later)
            category = self._determine_category(subject_lower, text_lower)
            auto_reply = self._should_auto_reply(category, subject_lower, text_lower)
            reply_text = self._generate_reply_text(category) if auto_reply else None
            labels = self._determine_labels(category)
            metadata = self._extract_metadata(email, category)
            
            return EmailClassificationResponse(
                category=category,
                auto_reply=auto_reply,
                reply_text=reply_text,
                labels=labels,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error classifying email: {str(e)}", exc_info=True)
            # Return default classification on error
            return EmailClassificationResponse(
                category="general",
                auto_reply=False,
                reply_text=None,
                labels=["Uncategorized"],
                metadata={"error": str(e)}
            )
    
    def _determine_category(self, subject: str, text: str) -> str:
        """
        Determine email category based on subject and content
        
        This is a basic implementation - can be enhanced with:
        - NLP/ML models
        - Keyword matching
        - Intent detection
        - Integration with chatbot for context
        """
        # Course inquiry keywords
        course_keywords = ["course", "training", "class", "learn", "certificate", 
                          "lifeguard", "cpr", "first aid", "booking", "enroll"]
        
        # Support/help keywords
        support_keywords = ["help", "support", "question", "issue", "problem", 
                           "assistance", "how to", "can't", "unable"]
        
        # Quote/pricing keywords
        quote_keywords = ["quote", "price", "cost", "pricing", "fee", "payment", 
                         "invoice", "bill", "charge"]
        
        # Check for course-related content
        if any(keyword in subject or keyword in text for keyword in course_keywords):
            if any(keyword in subject or keyword in text for keyword in quote_keywords):
                return "course_quote"
            return "course_inquiry"
        
        # Check for support requests
        if any(keyword in subject or keyword in text for keyword in support_keywords):
            return "support"
        
        # Check for quote requests
        if any(keyword in subject or keyword in text for keyword in quote_keywords):
            return "quote"
        
        # Default category
        return "general"
    
    def _should_auto_reply(self, category: str, subject: str, text: str) -> bool:
        """
        Determine if an automatic reply should be sent
        
        Args:
            category: Email category
            subject: Email subject
            text: Email text content
            
        Returns:
            True if auto-reply should be sent, False otherwise
        """
        # Auto-reply for certain categories
        auto_reply_categories = ["course_inquiry", "quote", "course_quote"]
        
        # Don't auto-reply to out-of-office, auto-replies, or newsletters
        skip_keywords = ["out of office", "automatic reply", "auto-reply", 
                        "unsubscribe", "newsletter", "noreply"]
        
        if any(keyword in subject.lower() or keyword in text.lower() 
               for keyword in skip_keywords):
            return False
        
        return category in auto_reply_categories
    
    def _generate_reply_text(self, category: str) -> str:
        """
        Generate automatic reply text based on category
        
        Args:
            category: Email category
            
        Returns:
            Reply text or None
        """
        replies = {
            "course_inquiry": (
                "Thank you for your interest in our lifeguard and CPR training courses! "
                "We have received your inquiry and will get back to you within 24 hours "
                "with detailed information about our courses and schedules."
            ),
            "quote": (
                "Thank you for requesting a quote. We have received your request and "
                "will prepare a detailed quote for you. Our team will contact you "
                "within 24 hours with pricing information."
            ),
            "course_quote": (
                "Thank you for your interest in our training courses! We have received "
                "your inquiry about course pricing and availability. Our team will "
                "contact you within 24 hours with detailed information and a quote."
            ),
        }
        
        return replies.get(category, None)
    
    def _determine_labels(self, category: str) -> List[str]:
        """
        Determine Gmail labels to apply based on category
        
        Args:
            category: Email category
            
        Returns:
            List of Gmail labels
        """
        label_mapping = {
            "course_inquiry": ["Course Inquiry", "Action Required"],
            "course_quote": ["Course Inquiry", "Quote Request", "Action Required"],
            "quote": ["Quote Request", "Action Required"],
            "support": ["Support", "Action Required"],
            "general": ["Uncategorized"]
        }
        
        return label_mapping.get(category, ["Uncategorized"])
    
    def _extract_metadata(self, email: EmailPayload, category: str) -> Dict[str, Any]:
        """
        Extract additional metadata from the email
        
        Args:
            email: Email payload
            category: Determined category
            
        Returns:
            Dictionary with metadata
        """
        return {
            "from_email": email.from_email,
            "from_name": email.from_name,
            "to_email": email.to_email,
            "thread_id": email.thread_id,
            "message_id": email.message_id,
            "subject": email.subject,
            "category": category,
            "text_length": len(email.text),
            "html_length": len(email.html)
        }

