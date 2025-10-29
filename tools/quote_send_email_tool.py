"""
Quote & Send Email Tool - StructuredTool Implementation

Confidence: 95% ✅

Purpose:
- Generate detailed price quotation
- Create payment links (Stripe + PayPal) 
- Send to user's email

NOTE: This is a MOCK implementation for testing.
Real implementation will integrate with:
- Stripe API (payment links)
- PayPal API (payment links)
- SendGrid/AWS SES (email sending)
- Pricing database (real prices)
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Literal, Optional
from langchain.tools import StructuredTool
from config.database import get_connection
import random

# ================================================================
# INPUT SCHEMA (Pydantic)
# ================================================================

class QuoteSendEmailInput(BaseModel):
    """Input schema for quote_send_email tool"""
    
    course_name: str = Field(
        description=(
            "Name of the course to quote. Can be full name, partial name, or abbreviation. "
            "Examples: 'Junior Lifeguard', 'CPR', 'BLS CPR for Healthcare Provider', 'Instructor'"
        )
    )
    
    quantity: int = Field(
        description=(
            "Number of students to enroll. "
            "1 = Individual pricing (flat rate). "
            "2+ = Group pricing (tiered, shows options 4A and 4B)."
        ),
        ge=1,  # Greater than or equal to 1
        le=1000  # Max 1000 students (reasonable limit)
    )
    
    pricing_option: Optional[Literal["4A", "4B"]] = Field(
        default=None,
        description=(
            "Group pricing option to use (4A or 4B). "
            "Only applicable for groups (quantity >= 2). "
            "4A typically has lower prices for larger groups. "
            "If not specified, defaults to 4A (better value)."
        )
    )
    
    user_email: EmailStr = Field(
        description="User's email address to send the quote to. Must be valid email format with @ symbol."
    )
    
    user_name: str = Field(
        description="User's full name for personalizing the quote email."
    )
    
    user_phone: Optional[str] = Field(
        default=None,
        description="User's phone number (optional). Include in quote for contact purposes."
    )
    
    payment_methods: list[Literal["stripe", "paypal"]] = Field(
        default_factory=lambda: ["stripe", "paypal"],
        description=(
            "Payment methods to include in the quote. "
            "Default: both Stripe and PayPal. "
            "Use ['stripe'] for credit card only, ['paypal'] for PayPal only."
        )
    )

# ================================================================
# MOCK IMPLEMENTATION
# ================================================================

async def _quote_send_email_impl(
    course_name: str,
    quantity: int,
    pricing_option: Optional[str] = None,
    user_email: str = "",
    user_name: str = "",
    user_phone: Optional[str] = None,
    payment_methods: list[str] = None
) -> str:
    """
    Mock implementation of quote generation and email sending
    
    For testing purposes - simulates the complete quote flow:
    1. Looks up pricing from database
    2. Generates payment links (mock URLs)
    3. Creates quote content
    4. Simulates sending email
    
    Real implementation will:
    - Query PostgreSQL for exact pricing
    - Call Stripe API to create payment link
    - Call PayPal API to create payment link
    - Generate PDF quote
    - Send email via SendGrid/AWS SES
    - Log to audit_events table
    
    Args:
        course_name: Course to quote
        quantity: Number of students
        pricing_option: '4A' or '4B' (for groups)
        user_email: Recipient email
        user_name: Recipient name
        user_phone: Recipient phone (optional)
        payment_methods: List of payment methods to include
    
    Returns:
        Success message with quote details for agent to relay to user
    """
    
    if payment_methods is None:
        payment_methods = ["stripe", "paypal"]
    
    try:
        print(f"📧 Quote Tool: Generating quote for '{course_name}' (qty: {quantity})")
        
        # ================================================================
        # STEP 1: Look up pricing from database
        # ================================================================
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Find course (fuzzy match)
                cur.execute("""
                    SELECT course_id, title, sku
                    FROM courses
                    WHERE active = true
                      AND (title ILIKE %s OR sku ILIKE %s)
                    ORDER BY title
                    LIMIT 1
                """, (f"%{course_name}%", f"%{course_name}%"))
                
                course = cur.fetchone()
                
                if not course:
                    print(f"  ❌ Course not found: {course_name}")
                    return f"❌ Course not found: '{course_name}'. Please use rag_search to find available courses first."
                
                course_title = course['title']
                course_sku = course['sku']
                course_id = course['course_id']
                
                print(f"  ✅ Found course: {course_title}")
                
                # Get pricing
                if quantity == 1:
                    # Individual pricing
                    cur.execute("""
                        SELECT unit_price, currency
                        FROM price_individual
                        WHERE course_id = %s
                          AND effective_from <= CURRENT_DATE
                          AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
                        ORDER BY effective_from DESC
                        LIMIT 1
                    """, (course_id,))
                    
                    price_row = cur.fetchone()
                    
                    if not price_row:
                        return f"⚠️ No pricing available for {course_title}. Please contact us directly."
                    
                    unit_price = float(price_row['unit_price'])
                    currency = price_row['currency']
                    total_price = unit_price
                    pricing_type = "Individual"
                    
                    print(f"  💰 Individual pricing: ${unit_price:.2f}")
                
                else:
                    # Group pricing
                    selected_option = pricing_option or "4A"
                    
                    cur.execute("""
                        SELECT pgt.unit_price, pg.currency
                        FROM price_group pg
                        JOIN price_group_tier pgt ON pg.price_group_id = pgt.price_group_id
                        WHERE pg.course_id = %s
                          AND pg.price_option = %s
                          AND pg.effective_from <= CURRENT_DATE
                          AND (pg.effective_to IS NULL OR pg.effective_to >= CURRENT_DATE)
                          AND pgt.min_qty <= %s
                          AND (pgt.max_qty IS NULL OR pgt.max_qty >= %s)
                        ORDER BY pgt.min_qty DESC
                        LIMIT 1
                    """, (course_id, selected_option, quantity, quantity))
                    
                    price_row = cur.fetchone()
                    
                    if not price_row:
                        return f"⚠️ No group pricing available for {quantity} students. Please contact us for a custom quote."
                    
                    unit_price = float(price_row['unit_price'])
                    currency = price_row['currency']
                    total_price = unit_price * quantity
                    pricing_type = f"Group (Option {selected_option})"
                    
                    print(f"  💰 Group pricing (Option {selected_option}): ${unit_price:.2f} per person")
        
        # ================================================================
        # STEP 2: Generate payment links (MOCK)
        # ================================================================
        
        # Mock Stripe payment link
        stripe_session_id = f"cs_test_{random.randint(100000, 999999)}"
        stripe_link = f"https://checkout.stripe.com/c/pay/{stripe_session_id}"
        
        # Mock PayPal payment link
        paypal_token = f"EC-{random.randint(10000000, 99999999)}"
        paypal_link = f"https://www.paypal.com/checkoutnow?token={paypal_token}"
        
        print(f"  💳 [MOCK] Generated Stripe link: {stripe_link}")
        print(f"  💰 [MOCK] Generated PayPal link: {paypal_link}")
        
        # ================================================================
        # STEP 3: Generate quote content
        # ================================================================
        
        quote_content = f"""
========================================
LIFEGUARD-PRO TRAINING QUOTE
========================================

Dear {user_name},

Thank you for your interest in LifeGuard-Pro training!

QUOTE DETAILS:
--------------
Course: {course_title}
SKU: {course_sku}
Pricing Type: {pricing_type}
Quantity: {quantity} student(s)
Unit Price: ${unit_price:.2f} {currency}
{'='*40}
TOTAL COST: ${total_price:.2f} {currency}
{'='*40}

PAYMENT OPTIONS:
--------------
"""
        
        if "stripe" in payment_methods:
            quote_content += f"""
💳 PAY WITH CREDIT CARD (Stripe):
{stripe_link}
(Secure payment processing with Visa, Mastercard, Amex, Discover)

"""
        
        if "paypal" in payment_methods:
            quote_content += f"""
💰 PAY WITH PAYPAL:
{paypal_link}
(Pay with PayPal balance or linked bank account)

"""
        
        quote_content += f"""
NEXT STEPS:
-----------
1. Review the quote details above
2. Click your preferred payment link
3. Complete the secure checkout
4. You'll receive course access details immediately!

CONTACT INFORMATION:
--------------------
Email: {user_email}
{f'Phone: {user_phone}' if user_phone else ''}

Questions? Reply to this email or call us at 1-800-LIFEGUARD

Best regards,
The LifeGuard-Pro Team
www.lifeguard-pro.org

========================================
Quote generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
========================================
"""
        
        # ================================================================
        # STEP 4: Mock send email
        # ================================================================
        
        print(f"  📨 [MOCK] Sending quote email to: {user_email}")
        print(f"  📄 [MOCK] Quote content: {len(quote_content)} characters")
        print(f"  ✅ [MOCK] Email sent successfully!")
        
        # ================================================================
        # STEP 5: Return success message for agent
        # ================================================================
        
        response = f"""✅ **Quote Sent Successfully!**

I've emailed a detailed quote to **{user_email}** with the following:

**Quote Summary:**
- **Course:** {course_title}
- **Quantity:** {quantity} student(s)
- **Pricing:** {pricing_type}
- **Unit Price:** ${unit_price:.2f} {currency}
- **Total Cost:** ${total_price:.2f} {currency}

**Payment Options Included:**
"""
        
        if "stripe" in payment_methods:
            response += f"- 💳 **Stripe** (Credit/Debit Card): Secure checkout link included\n"
        
        if "paypal" in payment_methods:
            response += f"- 💰 **PayPal**: Pay with PayPal balance or bank account\n"
        
        response += f"""
**What to do next:**
1. Check your email inbox: **{user_email}**
2. Review the quote details
3. Click your preferred payment link (Stripe or PayPal)
4. Complete the secure checkout process
5. You'll receive course access details immediately after payment!

**Quote ID:** QUOTE-{random.randint(10000, 99999)}
**Valid for:** 7 days

Need help with payment or have questions? Just ask! 🏊"""
        
        return response
        
    except Exception as e:
        print(f"  ❌ Quote tool error: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error generating quote: {str(e)}\n\nPlease try again or contact us directly at info@lifeguard-pro.org"

# ================================================================
# TOOL DEFINITION (StructuredTool)
# ================================================================

quote_send_email = StructuredTool.from_function(
    name="quote_send_email",
    func=_quote_send_email_impl,
    args_schema=QuoteSendEmailInput,
    description=(
        "Generate a detailed price quotation and send it to the user's email with secure payment links.\n\n"
        
        "🚨 **CRITICAL: ALWAYS CONFIRM BEFORE CALLING THIS TOOL!** 🚨\n\n"
        
        "**MANDATORY STEPS BEFORE CALLING:**\n\n"
        
        "1. **Show complete quote details:**\n"
        "   • Course name\n"
        "   • Quantity (number of students)\n"
        "   • Pricing option (4A/4B for groups, Individual for 1)\n"
        "   • Unit price per student\n"
        "   • Total cost in USD\n"
        "   • User's email address\n\n"
        
        "2. **Explain what will be sent:**\n"
        "   'The quote will include:'\n"
        "   • Detailed course breakdown\n"
        "   • Secure Stripe payment link\n"
        "   • PayPal payment option\n\n"
        
        "3. **Ask for explicit confirmation:**\n"
        "   'Shall I send this quote to your email?'\n\n"
        
        "4. **Wait for user response:**\n"
        "   User MUST say: 'yes', 'send it', 'looks good', 'confirmed', 'go ahead'\n\n"
        
        "5. **ONLY THEN call this tool**\n\n"
        
        "**If user makes changes:**\n"
        "- Update the details\n"
        "- Show updated confirmation\n"
        "- Ask for confirmation again\n"
        "- Then call this tool\n\n"
        
        "**DO NOT call this tool if:**\n"
        "- User hasn't seen or confirmed the details\n"
        "- User is just asking about pricing (use get_pricing instead)\n"
        "- User hasn't confirmed they want it emailed\n\n"
        
        "**The tool will:**\n"
        "- Look up exact pricing from database\n"
        "- Generate Stripe & PayPal payment links\n"
        "- Send personalized email to user\n\n"
        
        "**Returns:** Success message confirming quote was emailed."
    ),
    coroutine=_quote_send_email_impl
)

# ================================================================
# HELPER FUNCTIONS (for testing)
# ================================================================

async def test_quote_tool():
    """Test the quote tool directly"""
    result = await quote_send_email.ainvoke({
        "course_name": "Junior Lifeguard",
        "quantity": 1,
        "user_email": "test@example.com",
        "user_name": "Test User",
        "payment_methods": ["stripe", "paypal"]
    })
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_quote_tool())

