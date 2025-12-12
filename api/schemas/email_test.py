"""
Email Test Endpoint Schemas

Pydantic models for the /email/test-process endpoint
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class EmailTestPayload(BaseModel):
    """Input payload for email test processing"""
    subject: str = Field(..., description="Email subject line")
    text: str = Field(..., description="Plain text email body")
    html: Optional[str] = Field(None, description="HTML email body (optional)")
    from_email: Optional[str] = Field(None, description="Sender email address")
    to_email: Optional[str] = Field(None, description="Recipient email address")
    thread_id: Optional[str] = Field(None, description="Gmail thread ID")
    message_id: Optional[str] = Field(None, description="Gmail message ID")


class EmailClassificationResult(BaseModel):
    """Classification result from email classifier"""
    label_id: str = Field(..., description="Internal label ID (e.g., 'BUY_NOW', 'BUY_LATER')")
    gmail_label: str = Field(..., description="Gmail label name (e.g., '3-Buy Now')")
    category: str = Field(..., description="High-level category (e.g., 'sales', 'support', 'neutral')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence (0.0 to 1.0)")


class EmailTestResponse(BaseModel):
    """Complete response from email test processing"""
    classification: EmailClassificationResult = Field(..., description="Email classification result")
    reply_text: str = Field(..., description="Generated reply text")
    used_tools: List[str] = Field(default_factory=list, description="List of tool IDs that were used")
    raw_model_output: Optional[Dict[str, Any]] = Field(None, description="Raw model output for debugging")

