"""
Label Configuration for Email Classification

Defines internal labels, Gmail labels, prompts, and tool allowlists.
All label-specific behavior is configured here for easy iteration.
"""
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class LabelConfig:
    """Configuration for an email label"""
    id: str                # Internal label id, e.g. "BUY_NOW"
    gmail_label: str       # Actual Gmail label name you'll apply later
    description: str       # For classifier prompt
    system_prompt: str     # Label-specific prompt for reply generation
    allowed_tools: List[str]  # Tool IDs allowed for this label


# ============================================================================
# GENERIC EMAIL STYLE (Base prompt for all labels)
# ============================================================================

GENERIC_EMAIL_STYLE = """
You are an email assistant for Lifeguard-Pro, a company that sells lifeguard,
CPR, and first aid training. You always:

- Reply in a friendly, concise, professional tone.
- Use short paragraphs and bullet points where helpful.
- End with a clear next step (booking, payment, or information request).
"""


# ============================================================================
# LABEL-SPECIFIC PROMPTS
# ============================================================================

BUY_NOW_PROMPT = GENERIC_EMAIL_STYLE + """
This lead is READY TO BUY NOW or very close. Your goals:

- Confirm the exact course, location, and preferred date (if mentioned).
- If anything critical is missing, ask 1–3 focused questions.
- Provide a clear call-to-action: booking link and/or payment link.
- If price is relevant, briefly justify the value (certification, quality, etc.).
"""

BUY_LATER_PROMPT = GENERIC_EMAIL_STYLE + """
This lead is INTERESTED but wants to buy LATER.

Your goals:

- Acknowledge their timing constraints.
- Suggest specific future options (e.g., next course dates).
- Offer to set a reminder or follow-up.
- Keep the door open with a low-pressure, supportive tone.
"""

FOLLOW_UP_PROMPT = GENERIC_EMAIL_STYLE + """
This is a FOLLOW-UP email where we want to nudge the lead.

Your goals:

- Reference the previous conversation in 1 sentence.
- Give a short reminder of the benefits of the course.
- Ask a simple question that is easy to answer (yes/no or one detail).
- Keep it warm, not pushy.
"""

CUSTOMER_SERVICE_PROMPT = GENERIC_EMAIL_STYLE + """
This is a CUSTOMER SERVICE / SUPPORT request from a current or past student.

Your goals:

- Show empathy and clarity.
- Solve the problem using our policies (rescheduling, certificates, etc.).
- If you don't have enough info, ask 1–3 clear questions.
- Avoid sales pressure, focus on helpfulness.
"""

OBJECTION_PROMPT = GENERIC_EMAIL_STYLE + """
This email contains OBJECTIONS (price, schedule, location, etc.).

Your goals:

- Acknowledge and validate the concern.
- Address the objection with clear, specific information.
- If appropriate, offer alternatives (different dates, payment options, etc.).
- Invite them to ask further questions or book a quick call.
"""

NEUTRAL_PROMPT = GENERIC_EMAIL_STYLE + """
This is a NEUTRAL or general inquiry.

Your goals:

- Understand what they want (training type, location, timeline).
- Ask 2–3 focused questions to clarify.
- Briefly explain what Lifeguard-Pro offers.
- Invite them to continue the conversation or book a call.
"""


# ============================================================================
# LABEL CONFIGURATIONS
# ============================================================================

LABEL_CONFIGS: Dict[str, LabelConfig] = {
    "BUY_NOW": LabelConfig(
        id="BUY_NOW",
        gmail_label="3-Buy Now",
        description="Lead clearly wants to book/pay now or asap.",
        system_prompt=BUY_NOW_PROMPT,
        allowed_tools=["rag", "pricing", "booking", "payment_link"],
    ),
    "BUY_LATER": LabelConfig(
        id="BUY_LATER",
        gmail_label="4-Buy Later",
        description="Lead is interested but explicitly wants to wait or book later.",
        system_prompt=BUY_LATER_PROMPT,
        allowed_tools=["rag", "pricing", "booking", "get_all_services"],
    ),
    "FOLLOW_UP": LabelConfig(
        id="FOLLOW_UP",
        gmail_label="4.3-Follow-up message",
        description="We are following up on a previous offer or conversation.",
        system_prompt=FOLLOW_UP_PROMPT,
        allowed_tools=["rag", "pricing", "booking", "get_all_services"],
    ),
    "CUSTOMER_SERVICE": LabelConfig(
        id="CUSTOMER_SERVICE",
        gmail_label="13-Customer Service",
        description="Existing student needs help with a booking, certificate, or similar.",
        system_prompt=CUSTOMER_SERVICE_PROMPT,
        allowed_tools=["rag"],
    ),
    "OBJECTION": LabelConfig(
        id="OBJECTION",
        gmail_label="6-Objections",
        description="Lead raises objections or concerns (price, schedule, etc.).",
        system_prompt=OBJECTION_PROMPT,
        allowed_tools=["rag", "pricing", "booking"],
    ),
    "NEUTRAL": LabelConfig(
        id="NEUTRAL",
        gmail_label="7-Neutral",
        description="General question or unclear intent.",
        system_prompt=NEUTRAL_PROMPT,
        allowed_tools=["rag", "pricing", "get_all_services"],
    ),
}


def get_label_config(label_id: str) -> LabelConfig:
    """
    Get label configuration by ID
    
    Args:
        label_id: Label ID (e.g., "BUY_NOW")
        
    Returns:
        LabelConfig instance
        
    Raises:
        KeyError: If label_id not found
    """
    if label_id not in LABEL_CONFIGS:
        return LABEL_CONFIGS["NEUTRAL"]  # Fallback to NEUTRAL
    return LABEL_CONFIGS[label_id]


__all__ = ['LabelConfig', 'LABEL_CONFIGS', 'get_label_config']

