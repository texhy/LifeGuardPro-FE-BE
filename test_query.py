"""Test the actual SQL query"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config.database import get_connection

query = "lifeguard"
alias_audience = "INDIVIDUAL"
buyer_category = "individual"

# Build WHERE clause
program_where = ""
params_list = []

alias_where = ""
if alias_audience:
    alias_where = "AND ca.audience = %s"
    params_list.append(alias_audience)

search_pattern = f"%{query}%"
exact_pattern = query
starts_pattern = f"{query}%"

sql = f"""
    SELECT DISTINCT
        c.course_id,
        c.title as canonical_title,
        c.slug,
        c.sku,
        c.short_title,
        c.description,
        COALESCE(ca.display_title, c.title) as match_title,
        CASE 
            WHEN ca.display_title IS NOT NULL THEN 'alias'
            ELSE 'canonical'
        END as match_source,
        ca.audience,
        p.program_id,
        p.slug as program_slug,
        p.title as program_title,
        p.description as program_description,
        CASE 
            WHEN COALESCE(ca.display_title, c.title) ILIKE %s THEN 1
            WHEN COALESCE(ca.display_title, c.title) ILIKE %s THEN 2
            WHEN c.title ILIKE %s THEN 3
            ELSE 4
        END as match_rank
    FROM courses c
    JOIN programs p ON c.program_id = p.program_id
    LEFT JOIN course_aliases ca ON (
        c.course_id = ca.course_id 
        AND ca.active = true
        {alias_where}
    )
    WHERE c.active = true
      {program_where}
      AND (
          COALESCE(ca.display_title, c.title) ILIKE %s
          OR c.title ILIKE %s
          OR COALESCE(c.short_title, '') ILIKE %s
          OR c.slug ILIKE %s
          OR COALESCE(c.sku, '') ILIKE %s
      )
    ORDER BY
        match_rank,
        c.title
    LIMIT 10
"""

params = params_list + [
    exact_pattern,
    starts_pattern,
    starts_pattern,
    search_pattern,
    search_pattern,
    search_pattern,
    search_pattern,
    search_pattern,
    10
]

print("SQL Query:")
print(sql)
print(f"\nParams: {params}")

with get_connection() as conn:
    with conn.cursor() as cur:
        try:
            cur.execute(sql, params)
            results = cur.fetchall()
            print(f"\n✅ Query executed successfully!")
            print(f"   Found {len(results)} results")
            
            for i, row in enumerate(results[:5], 1):
                print(f"\n{i}. {row['canonical_title']}")
                print(f"   Match title: {row['match_title']}")
                print(f"   Source: {row['match_source']}")
                print(f"   Program: {row['program_title']}")
        except Exception as e:
            print(f"\n❌ Query failed: {e}")
            import traceback
            traceback.print_exc()

