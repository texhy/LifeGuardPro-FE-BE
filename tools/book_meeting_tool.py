"""
Book Meeting Tool - StructuredTool Implementation

Confidence: 95% ✅

Purpose:
- Schedule virtual meetings/consultations
- Check availability (Google Calendar/Calendly)
- Create meeting links (Google Meet)
- Send calendar invites

NOTE: This is a MOCK implementation for testing.
Real implementation will integrate with:
- Google Calendar API (availability checking)
- Google Meet API (meeting link generation)
- SendGrid/AWS SES (calendar invite emails)
- Calendly API (alternative scheduling)
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal
from langchain.tools import StructuredTool
from datetime import datetime, timedelta
import random

# ================================================================
# INPUT SCHEMA (Pydantic)
# ================================================================

class BookMeetingInput(BaseModel):
    """Input schema for book_meeting tool"""
    
    user_email: EmailStr = Field(
        description="User's email address for sending the calendar invitation. Must be valid email format."
    )
    
    user_name: str = Field(
        description="User's full name to include in the meeting invitation and calendar event."
    )
    
    user_phone: Optional[str] = Field(
        default=None,
        description="User's phone number (optional). Include for SMS reminders before the meeting."
    )
    
    preferred_date: Optional[str] = Field(
        default=None,
        description=(
            "User's preferred date for the meeting. Can be flexible formats: "
            "'tomorrow', 'next Monday', '2025-10-15', 'next week', etc. "
            "If not specified, tool will suggest next available business day."
        )
    )
    
    preferred_time: Optional[str] = Field(
        default=None,
        description=(
            "User's preferred time for the meeting. Flexible formats: "
            "'2pm', '14:00', 'afternoon', 'morning', 'evening'. "
            "If not specified, tool will suggest 3-5 available time slots."
        )
    )
    
    meeting_type: Literal["consultation", "course_selection", "technical_support", "group_inquiry", "general"] = Field(
        default="consultation",
        description=(
            "Type of meeting to schedule:\n"
            "- 'consultation': General course selection help (most common)\n"
            "- 'course_selection': Help choosing the right course\n"
            "- 'technical_support': Technical issues or questions\n"
            "- 'group_inquiry': Corporate/group training discussion\n"
            "- 'general': Other inquiries"
        )
    )
    
    duration_minutes: int = Field(
        default=30,
        description=(
            "Meeting duration in minutes. Common options: 15, 30, or 60. "
            "Use 15 for quick questions, 30 for consultations (default), 60 for group/corporate discussions."
        ),
        ge=15,   # Minimum 15 minutes
        le=120   # Maximum 2 hours
    )
    
    timezone: str = Field(
        default="America/Los_Angeles",
        description=(
            "User's timezone for scheduling. Examples: "
            "'America/New_York' (Eastern), 'America/Chicago' (Central), "
            "'America/Denver' (Mountain), 'America/Los_Angeles' (Pacific). "
            "Try to infer from conversation or location. Default: Pacific Time."
        )
    )

# ================================================================
# MOCK IMPLEMENTATION
# ================================================================

async def _book_meeting_impl(
    user_email: str,
    user_name: str,
    user_phone: Optional[str] = None,
    preferred_date: Optional[str] = None,
    preferred_time: Optional[str] = None,
    meeting_type: str = "consultation",
    duration_minutes: int = 30,
    timezone: str = "America/Los_Angeles"
) -> str:
    """
    Mock implementation of meeting booking
    
    For testing purposes - simulates the complete booking flow:
    1. Checks availability (mock)
    2. Generates time slots
    3. Creates Google Meet link (mock)
    4. Sends calendar invite (mock)
    
    Real implementation will:
    - Connect to Google Calendar API for actual availability
    - Create real Google Meet/Zoom links
    - Send calendar invites via email (ICS format)
    - Support timezone conversion
    - Handle conflicts and rescheduling
    - Log to audit_events table
    
    Args:
        user_email: Recipient email for calendar invite
        user_name: User's name
        user_phone: Optional phone for SMS reminders
        preferred_date: User's preferred date (flexible format)
        preferred_time: User's preferred time (flexible format)
        meeting_type: Type of consultation
        duration_minutes: Meeting length (15-120 mins)
        timezone: User's timezone
    
    Returns:
        Success message with meeting details for agent to relay to user
    """
    
    try:
        print(f"📅 Booking Tool: Scheduling {meeting_type} for {user_name}")
        
        # ================================================================
        # STEP 1: Parse preferred date
        # ================================================================
        
        today = datetime.now()
        
        if preferred_date:
            print(f"  🗓️  User preferred date: {preferred_date}")
            
            # Mock date parsing (real implementation would use dateparser library)
            preferred_date_lower = preferred_date.lower()
            
            if "tomorrow" in preferred_date_lower:
                start_date = today + timedelta(days=1)
            elif "monday" in preferred_date_lower:
                # Next Monday
                days_ahead = 0 - today.weekday() + 7  # 0 = Monday
                if days_ahead <= 0:
                    days_ahead += 7
                start_date = today + timedelta(days=days_ahead)
            elif "next week" in preferred_date_lower:
                start_date = today + timedelta(days=7)
            elif "friday" in preferred_date_lower:
                # Next Friday
                days_ahead = 4 - today.weekday()  # 4 = Friday
                if days_ahead <= 0:
                    days_ahead += 7
                start_date = today + timedelta(days=days_ahead)
            else:
                # Try to parse as date (simplified)
                try:
                    # Format: YYYY-MM-DD
                    start_date = datetime.strptime(preferred_date, "%Y-%m-%d")
                except:
                    # Default to tomorrow
                    start_date = today + timedelta(days=1)
        else:
            # No preference, suggest next business day
            start_date = today + timedelta(days=1)
            
            # Skip weekends
            while start_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
                start_date += timedelta(days=1)
        
        print(f"  📅 Target date: {start_date.strftime('%Y-%m-%d')}")
        
        # ================================================================
        # STEP 2: Parse preferred time and generate slots
        # ================================================================
        
        available_slots = []
        
        if preferred_time:
            print(f"  🕐 User preferred time: {preferred_time}")
            
            # Mock time parsing
            preferred_time_lower = preferred_time.lower()
            
            if "morning" in preferred_time_lower:
                base_hour = 10
            elif "afternoon" in preferred_time_lower:
                base_hour = 14
            elif "evening" in preferred_time_lower:
                base_hour = 17
            elif "2pm" in preferred_time_lower or "14:00" in preferred_time_lower:
                base_hour = 14
            elif "10am" in preferred_time_lower or "10:00" in preferred_time_lower:
                base_hour = 10
            else:
                # Try to extract hour (simplified)
                base_hour = 14  # Default to 2pm
            
            # Create slot at preferred time
            selected_slot = start_date.replace(hour=base_hour, minute=0, second=0, microsecond=0)
            available_slots.append(selected_slot)
            
            # Add alternative slots (2 hours before/after)
            available_slots.append(start_date.replace(hour=base_hour-2, minute=0, second=0, microsecond=0))
            available_slots.append(start_date.replace(hour=base_hour+2, minute=0, second=0, microsecond=0))
            
        else:
            # No time preference, suggest business hours (10am, 12pm, 2pm)
            for hour in [10, 12, 14]:
                slot = start_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                available_slots.append(slot)
        
        # Use first slot as selected (or closest to preferred)
        selected_slot = available_slots[0]
        
        print(f"  ⏰ Selected time: {selected_slot.strftime('%I:%M %p')}")
        print(f"  ⏰ Alternative slots: {len(available_slots)-1}")
        
        # ================================================================
        # STEP 3: Generate Google Meet link (MOCK)
        # ================================================================
        
        # Mock Google Meet link
        meeting_code = f"{random.choice('abcdefghijklmnopqrstuvwxyz')}{random.choice('abcdefghijklmnopqrstuvwxyz')}{random.choice('abcdefghijklmnopqrstuvwxyz')}"
        meeting_id = f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(100, 999)}"
        meeting_link = f"https://meet.google.com/{meeting_code}-{meeting_id}"
        
        print(f"  🔗 [MOCK] Generated Google Meet link: {meeting_link}")
        
        # ================================================================
        # STEP 4: Format meeting details
        # ================================================================
        
        meeting_datetime_full = selected_slot.strftime("%A, %B %d, %Y at %I:%M %p")
        meeting_date_only = selected_slot.strftime("%A, %B %d, %Y")
        meeting_time_only = selected_slot.strftime("%I:%M %p")
        
        # ================================================================
        # STEP 5: Mock send calendar invite
        # ================================================================
        
        print(f"  📨 [MOCK] Sending calendar invite to: {user_email}")
        print(f"  📧 [MOCK] Calendar event created: {meeting_type} - {duration_minutes} min")
        print(f"  ✅ [MOCK] Invite sent successfully!")
        
        # ================================================================
        # STEP 6: Build response for agent
        # ================================================================
        
        response = f"""✅ **Meeting Scheduled Successfully!**

I've sent a calendar invitation to **{user_email}** with these details:

**📅 Meeting Information:**
- **Type:** {meeting_type.replace('_', ' ').title()}
- **Date:** {meeting_date_only}
- **Time:** {meeting_time_only} ({timezone})
- **Duration:** {duration_minutes} minutes
- **Platform:** Google Meet (virtual meeting)
- **Meeting Link:** {meeting_link}

**👤 Attendee:**
- Name: {user_name}
- Email: {user_email}
{f'- Phone: {user_phone}' if user_phone else ''}

**📧 What happens next:**
1. Check your email inbox ({user_email})
2. Open the calendar invitation
3. Accept/add to your calendar
4. Join the meeting at {meeting_time_only} using the Google Meet link
5. Our team expert will help you with {meeting_type.replace('_', ' ')}!

**Calendar invite sent to:** {user_email}
**Meeting ID:** {meeting_id}
"""
        
        # Add alternative time slots if user didn't specify exact time
        if not preferred_time or len(available_slots) > 1:
            response += "\n**✨ Other available times (if you need to reschedule):**\n"
            
            for i, slot in enumerate(available_slots[1:4], start=2):
                alt_datetime = slot.strftime("%A, %B %d at %I:%M %p")
                response += f"{i}. {alt_datetime} {timezone}\n"
            
            response += "\nNeed a different time? Just let me know and I'll reschedule! 📅"
        
        return response
        
    except Exception as e:
        print(f"  ❌ Booking tool error: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error scheduling meeting: {str(e)}\n\nPlease contact us directly at info@lifeguard-pro.org or call 1-800-LIFEGUARD to schedule."

# ================================================================
# TOOL DEFINITION (StructuredTool)
# ================================================================

book_meeting = StructuredTool.from_function(
    name="book_meeting",
    func=_book_meeting_impl,
    args_schema=BookMeetingInput,
    description=(
        "Schedule a virtual consultation with the LifeGuard-Pro team via Google Meet.\n\n"
        
        "🚨 **CRITICAL: ALWAYS CONFIRM BEFORE CALLING THIS TOOL!** 🚨\n\n"
        
        "**MANDATORY STEPS BEFORE CALLING:**\n\n"
        
        "1. **Understand what they need:**\n"
        "   Ask: 'I'd be happy to schedule a call! What would you like to discuss?'\n"
        "   Examples: course selection, group training, technical questions\n\n"
        
        "2. **Get time preferences (if not provided):**\n"
        "   Ask: 'When works best for you?'\n"
        "   Examples: 'tomorrow at 2pm', 'next Monday morning', 'anytime this week'\n"
        "   If user says 'anytime', offer to suggest available times\n\n"
        
        "3. **Show complete meeting details:**\n"
        "   • Meeting type (consultation/course selection/group inquiry)\n"
        "   • What they want to discuss\n"
        "   • Date (specific or 'next available')\n"
        "   • Time (specific or 'I'll suggest 3 options')\n"
        "   • Duration (usually 30 minutes)\n"
        "   • Platform (Google Meet - virtual)\n"
        "   • User's email address\n\n"
        
        "4. **Ask for explicit confirmation:**\n"
        "   'Shall I book this meeting for you?'\n\n"
        
        "5. **Wait for user response:**\n"
        "   User MUST say: 'yes', 'book it', 'confirmed', 'sounds good', 'please do'\n\n"
        
        "6. **ONLY THEN call this tool**\n\n"
        
        "**If user wants different time:**\n"
        "- Update the date/time\n"
        "- Show updated confirmation\n"
        "- Ask for confirmation again\n"
        "- Then call this tool\n\n"
        
        "**DO NOT call this tool if:**\n"
        "- User hasn't confirmed they want to book\n"
        "- User is just asking questions (use rag_search instead)\n"
        "- You haven't shown the meeting details\n"
        "- User hasn't explicitly asked to talk to someone\n\n"
        
        "**The tool will:**\n"
        "- Check available time slots\n"
        "- Create Google Meet link\n"
        "- Send calendar invitation to user's email\n"
        "- Suggest alternative times if needed\n\n"
        
        "**Returns:** Success message with meeting details and Google Meet link.\n\n"
        
        "**Note:** For rescheduling, call this tool again with new date/time."
    ),
    coroutine=_book_meeting_impl
)

# ================================================================
# HELPER FUNCTIONS (for testing)
# ================================================================

async def test_booking_tool():
    """Test the booking tool directly"""
    
    print("\n" + "="*80)
    print("🧪 TESTING BOOK_MEETING TOOL")
    print("="*80 + "\n")
    
    # Test 1: Simple booking (no preferences)
    print("Test 1: Simple booking (no preferences)")
    result1 = await book_meeting.ainvoke({
        "user_email": "test@example.com",
        "user_name": "John Smith",
        "user_phone": "555-123-4567",
    })
    print("\nResult:")
    print(result1)
    print("\n" + "-"*80 + "\n")
    
    # Test 2: With time preference
    print("Test 2: With preferred time (tomorrow at 2pm)")
    result2 = await book_meeting.ainvoke({
        "user_email": "sarah@company.com",
        "user_name": "Sarah Johnson",
        "preferred_date": "tomorrow",
        "preferred_time": "2pm",
        "meeting_type": "group_inquiry",
        "duration_minutes": 60
    })
    print("\nResult:")
    print(result2)
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_booking_tool())

