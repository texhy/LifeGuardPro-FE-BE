"""Email Classification Endpoints"""
from fastapi import APIRouter, HTTPException, Depends
from api.schemas.email import EmailPayload, EmailClassificationResponse
from services.email_service import EmailClassificationService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_email_service() -> EmailClassificationService:
    """Dependency injection for email service"""
    return EmailClassificationService()


@router.post("/classify-email", response_model=EmailClassificationResponse)
async def classify_email(
    payload: EmailPayload,
    email_service: EmailClassificationService = Depends(get_email_service)
):
    """
    Classify an incoming email from n8n Gmail automation
    
    This endpoint receives emails from n8n and classifies them to determine:
    - Category (course inquiry, quote, support, etc.)
    - Whether to send an auto-reply
    - What labels to apply in Gmail
    - Additional metadata
    
    Returns classification results that n8n can use for further automation.
    """
    try:
        from_email = payload.from_email or "unknown"
        subject_preview = (payload.subject or "")[:50]
        logger.info(f"Classifying email from {from_email}: {subject_preview}")
        
        result = await email_service.classify_email(payload)
        
        logger.info(f"Email classified as: {result.category}, auto_reply: {result.auto_reply}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing email classification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to classify email: {str(e)}"
        )

