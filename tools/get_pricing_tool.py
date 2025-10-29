"""
Pricing Lookup Tool for Agent

Confidence: 95% ✅

Features:
- Fuzzy course name matching (ILIKE)
- Individual pricing (quantity=1)
- Group tiered pricing (quantity>=2)
- Shows both 4A and 4B options
- Formatted output for LLM consumption
"""
from langchain.tools import tool
from config.database import get_connection
from typing import Optional

@tool
async def get_pricing(course_name: str, quantity: int = 1) -> str:
    """
    Get pricing information for a LifeGuard-Pro course.
    
    Use this tool when user asks about:
    - "how much", "what's the cost", "pricing", "price"
    - Group discounts or tiered pricing
    - Specific quantities ("for 10 students")
    
    Args:
        course_name: Name of the course (fuzzy match supported)
            Examples: "Junior Lifeguard", "CPR", "BLS", "First Aid"
        quantity: Number of students (default: 1)
            - 1 = individual pricing
            - 2+ = group pricing (shows all applicable tiers)
    
    Returns:
        str: Formatted pricing information with options
    
    Examples:
        get_pricing("Junior Lifeguard", 1)
        → Individual price: $125.00
        
        get_pricing("CPR", 10)
        → Group pricing for 10 students with options 4A and 4B
    """
    try:
        print(f"💰 Pricing Tool: Looking up '{course_name}' for {quantity} student(s)")
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                # ================================================================
                # 1. FIND COURSE (fuzzy match on title or SKU)
                # ================================================================
                cur.execute("""
                    SELECT course_id, title, sku, slug
                    FROM courses
                    WHERE active = true
                      AND (title ILIKE %s OR sku ILIKE %s OR slug ILIKE %s)
                    ORDER BY 
                        CASE 
                            WHEN title ILIKE %s THEN 1  -- Exact match first
                            WHEN title ILIKE %s THEN 2  -- Starts with
                            ELSE 3                       -- Contains
                        END,
                        title
                    LIMIT 1
                """, (
                    f"%{course_name}%",
                    f"%{course_name}%",
                    f"%{course_name}%",
                    course_name,
                    f"{course_name}%"
                ))
                
                course = cur.fetchone()
                
                if not course:
                    return f"❌ Course not found: '{course_name}'\n\nTry: 'Lifeguard', 'CPR', 'First Aid', 'Water Safety', etc.\n\nTip: Use rag_search to explore available courses first!"
                
                course_id = course['course_id']
                course_title = course['title']
                course_sku = course['sku'] or 'N/A'
                
                print(f"  ✅ Found: {course_title} (SKU: {course_sku})")
                
                # ================================================================
                # 2. GET PRICING BASED ON QUANTITY
                # ================================================================
                
                if quantity == 1:
                    # INDIVIDUAL PRICING
                    cur.execute("""
                        SELECT unit_price, currency, effective_from, effective_to
                        FROM price_individual
                        WHERE course_id = %s
                          AND effective_from <= CURRENT_DATE
                          AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
                        ORDER BY effective_from DESC
                        LIMIT 1
                    """, (course_id,))
                    
                    price = cur.fetchone()
                    
                    if price:
                        result = f"""💰 **{course_title}**
SKU: {course_sku}

**Individual Price:** ${price['unit_price']:.2f} {price['currency']} per person

💡 **Group Pricing:** For 2 or more students, group discounts are available!
   Ask: "What's the price for [X] students for {course_title}?"

📚 **To Register:** Use rag_search to find registration links and course details."""
                        
                        print(f"  ✅ Individual price: ${price['unit_price']:.2f}")
                        return result
                    else:
                        return f"⚠️  No current individual pricing available for **{course_title}**\n\nPlease contact LifeGuard-Pro for pricing information."
                
                else:
                    # GROUP PRICING (tiered)
                    cur.execute("""
                        SELECT 
                            pg.price_option,
                            pg.currency,
                            pgt.min_qty,
                            pgt.max_qty,
                            pgt.unit_price
                        FROM price_group pg
                        JOIN price_group_tier pgt ON pg.price_group_id = pgt.price_group_id
                        WHERE pg.course_id = %s
                          AND pg.effective_from <= CURRENT_DATE
                          AND (pg.effective_to IS NULL OR pg.effective_to >= CURRENT_DATE)
                          AND pgt.min_qty <= %s
                          AND (pgt.max_qty IS NULL OR pgt.max_qty >= %s)
                        ORDER BY pg.price_option, pgt.min_qty
                    """, (course_id, quantity, quantity))
                    
                    matching_tiers = cur.fetchall()
                    
                    if matching_tiers:
                        result = f"""💰 **{course_title}**
SKU: {course_sku}

**Group Pricing for {quantity} students:**

"""
                        # Group by option (4A, 4B)
                        options = {}
                        for tier in matching_tiers:
                            option = tier['price_option']
                            if option not in options:
                                options[option] = []
                            options[option].append(tier)
                        
                        # Format each option
                        for option, tiers in sorted(options.items()):
                            # Get the first matching tier (should only be one for a given quantity)
                            tier = tiers[0]
                            total_price = tier['unit_price'] * quantity
                            qty_range = f"{tier['min_qty']}-{tier['max_qty'] or '∞'}"
                            
                            result += f"""**Option {option}:** ${tier['unit_price']:.2f} per person (for {qty_range} students)
   • ${tier['unit_price']:.2f} × {quantity} students = **${total_price:.2f} {tier['currency']} total**

"""
                        
                        # Add comparison if multiple options
                        if len(options) > 1:
                            best_option = min(options.items(), key=lambda x: x[1][0]['unit_price'])
                            result += f"💡 **Best Value:** Option {best_option[0]} offers the lowest price for {quantity} students!\n\n"
                        
                        result += f"📚 **To Register:** Use rag_search to find registration details and course information."
                        
                        print(f"  ✅ Found {len(matching_tiers)} pricing tier(s) for {quantity} students")
                        return result
                    else:
                        # No matching tier, show all available tiers
                        cur.execute("""
                            SELECT 
                                pg.price_option,
                                pgt.min_qty,
                                pgt.max_qty,
                                pgt.unit_price,
                                pg.currency
                            FROM price_group pg
                            JOIN price_group_tier pgt ON pg.price_group_id = pgt.price_group_id
                            WHERE pg.course_id = %s
                              AND pg.effective_from <= CURRENT_DATE
                              AND (pg.effective_to IS NULL OR pg.effective_to >= CURRENT_DATE)
                            ORDER BY pg.price_option, pgt.min_qty
                        """, (course_id,))
                        
                        all_tiers = cur.fetchall()
                        
                        if all_tiers:
                            result = f"""⚠️  No exact pricing tier for {quantity} students for **{course_title}**

**Available Group Pricing Tiers:**

"""
                            options = {}
                            for tier in all_tiers:
                                option = tier['price_option']
                                if option not in options:
                                    options[option] = []
                                options[option].append(tier)
                            
                            for option, tiers in sorted(options.items()):
                                result += f"**Option {option}:**\n"
                                for tier in tiers[:3]:  # Show first 3 tiers
                                    qty_range = f"{tier['min_qty']}-{tier['max_qty'] or '∞'}"
                                    result += f"  • {qty_range} students: ${tier['unit_price']:.2f} per person\n"
                                if len(tiers) > 3:
                                    result += f"  • ... and {len(tiers)-3} more tiers\n"
                                result += "\n"
                            
                            result += "💡 Contact LifeGuard-Pro for custom pricing or larger groups."
                            return result
                        else:
                            return f"⚠️  No group pricing available for **{course_title}**\n\nPlease contact LifeGuard-Pro for group pricing information."
    
    except Exception as e:
        print(f"  ❌ Pricing tool error: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error looking up pricing: {str(e)}\n\nPlease try again or contact LifeGuard-Pro directly."

