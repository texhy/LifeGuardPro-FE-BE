"""
Email Test Endpoint

Test endpoint for email classification and reply generation
No database dependencies - pure logic for rapid iteration
"""
from fastapi import APIRouter, HTTPException, Depends
from api.schemas.email_test import EmailTestPayload, EmailTestResponse
from services.email_classifier import EmailClassificationService
from services.email_brain import EmailBrainService
from services.llm_client import get_llm_client, LLMClient
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_email_classifier(
    llm_client: LLMClient = Depends(get_llm_client),
) -> EmailClassificationService:
    """Dependency injection for email classifier"""
    return EmailClassificationService(llm_client)


def get_email_brain(
    llm_client: LLMClient = Depends(get_llm_client),
) -> EmailBrainService:
    """Dependency injection for email brain"""
    return EmailBrainService(llm_client)


@router.post("/email/test-process", response_model=EmailTestResponse)
async def test_process_email(
    payload: EmailTestPayload,
    classifier: EmailClassificationService = Depends(get_email_classifier),
    brain: EmailBrainService = Depends(get_email_brain),
):
    """
    Test endpoint for email classification and reply generation
    
    This endpoint:
    1. Classifies the email into a label (BUY_NOW, BUY_LATER, etc.)
    2. Generates a reply using label-specific prompts and tools
    3. Returns classification, reply, and tool usage info
    
    No database dependencies - pure logic for rapid iteration on prompts and labels.
    
    Args:
        payload: Email test payload with subject, text, and optional metadata
        
    Returns:
        EmailTestResponse with classification, reply_text, used_tools, and debug info
    """
    try:
        from_email = payload.from_email or "unknown"
        subject_preview = (payload.subject or "")[:50]
        logger.info(f"Processing test email from {from_email}: {subject_preview}")
        
        # Step 1: Classify email
        logger.info("Step 1: Classifying email...")
        classification = await classifier.classify_email(payload)
        logger.info(f"Classification result: {classification.label_id} ({classification.category}, confidence: {classification.confidence:.2f})")
        
        # Step 2: Generate reply
        logger.info("Step 2: Generating reply...")
        brain_result = await brain.generate_reply(payload, classification)
        logger.info(f"Reply generated ({len(brain_result['reply_text'])} chars), tools used: {brain_result['used_tools']}")
        
        # Step 3: Build response
        response = EmailTestResponse(
            classification=classification,
            reply_text=brain_result["reply_text"],
            used_tools=brain_result["used_tools"],
            raw_model_output=brain_result.get("raw_model_output"),
        )
        
        logger.info(f"✅ Email processing complete: {classification.label_id} -> {classification.gmail_label}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing test email: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process email: {str(e)}"
        )

