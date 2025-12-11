"""Email Classification Request/Response Schemas"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class EmailPayload(BaseModel):
    """Email payload from n8n Gmail automation"""
    subject: str = Field(default="", description="Email subject")
    text: str = Field(default="", description="Plain text content of the email")
    html: str = Field(default="", description="HTML content of the email")
    from_email: Optional[str] = Field(None, description="Sender email address")
    from_name: Optional[str] = Field(None, description="Sender name")
    to_email: Optional[str] = Field(None, description="Recipient email address")
    thread_id: str = Field(..., description="Gmail thread ID")
    message_id: str = Field(..., description="Gmail message ID")


class EmailClassificationResponse(BaseModel):
    """Response from email classification endpoint"""
    category: str = Field(..., description="Email category (e.g., 'general', 'inquiry', 'booking', etc.)")
    auto_reply: bool = Field(..., description="Whether to send an automatic reply")
    reply_text: Optional[str] = Field(None, description="Auto-reply text if auto_reply is True")
    labels: List[str] = Field(default_factory=list, description="Gmail labels to apply")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the classification")

