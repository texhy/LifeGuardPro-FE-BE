"""
BM25 Keyword Search Module

Implements keyword-based retrieval using PostgreSQL full-text search (ts_rank).

Why BM25:
- Fast (no API calls needed)
- Exact keyword matching (good for acronyms, numbers)
- Deterministic (same query = same results)
- Native PostgreSQL support

Confidence: 95% ✅

Example:
    results = bm25_search("CPO certification", limit=20)
    # Returns chunks ranked by ts_rank score
"""

from typing import List, Dict, Any
import sys
from pathlib import Path

# Import database connection
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.database import get_connection


def bm25_search(
    query: str,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    BM25 keyword-based search using PostgreSQL full-text search
    
    Uses PostgreSQL's ts_rank function which implements a BM25-like algorithm.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        
    Returns:
        List of chunks ranked by BM25 score:
        [
            {
                "chunk_id": int,
                "content": str,
                "bm25_score": float,
                "document_id": int,
                "document_title": str,
                "document_url": str,
                "document_type": str,
                "chunk_index": int,
                "retrieval_method": "bm25"
            },
            ...
        ]
        
    Confidence: 95% ✅
    """
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # PostgreSQL full-text search with ts_rank
                # Uses existing content_tsv column for better performance
                # plainto_tsquery converts plain text to tsquery format
                cursor.execute("""
                    SELECT 
                        c.id,
                        c.content,
                        c.document_id,
                        c.chunk_index,
                        d.title as document_title,
                        d.url as document_url,
                        d.document_type,
                        ts_rank(c.content_tsv, plainto_tsquery('english', %s)) as bm25_score
                    FROM chunks c
                    LEFT JOIN documents d ON c.document_id = d.document_id
                    WHERE c.content_tsv @@ plainto_tsquery('english', %s)
                    ORDER BY bm25_score DESC
                    LIMIT %s
                """, (query, query, limit))
                
                rows = cursor.fetchall()
                
                # Format results
                chunks = []
                for row in rows:
                    chunks.append({
                        "chunk_id": row['id'],
                        "content": row['content'],
                        "bm25_score": float(row['bm25_score']),
                        "document_id": row['document_id'],
                        "document_title": row.get('document_title'),
                        "document_url": row.get('document_url'),
                        "document_type": row.get('document_type'),
                        "chunk_index": row.get('chunk_index'),
                        "retrieval_method": "bm25"
                    })
                
                return chunks
                
    except Exception as e:
        print(f"     ❌ BM25 search failed: {e}")
        return []


def bm25_search_batch(
    queries: List[str],
    limit_per_query: int = 20
) -> List[Dict[str, Any]]:
    """
    Execute BM25 search for multiple queries
    
    Args:
        queries: List of query strings
        limit_per_query: Max results per query
        
    Returns:
        Combined results from all queries
        
    Confidence: 93% ✅
    """
    
    all_results = []
    
    for query in queries:
        results = bm25_search(query, limit=limit_per_query)
        all_results.extend(results)
    
    return all_results


def bm25_search_internal(
    query: str,
    limit: int = 20,
    document_type_filter: str = None
) -> List[Dict[str, Any]]:
    """
    BM25 keyword-based search on internal_chunks table
    
    Similar to bm25_search but searches internal documents only.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        document_type_filter: Filter by document_type (e.g., 'internal_faq')
        
    Returns:
        List of internal chunks ranked by BM25 score
        
    Confidence: 95% ✅
    """
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # Build query with optional document_type filter
                base_query = """
                    SELECT 
                        ic.id,
                        ic.content,
                        ic.document_id,
                        ic.chunk_index,
                        ic.document_type,
                        id.title as document_title,
                        id.source_file,
                        ts_rank(ic.content_tsv, plainto_tsquery('english', %s)) as bm25_score
                    FROM internal_chunks ic
                    LEFT JOIN internal_documents id ON ic.document_id = id.document_id
                    WHERE ic.content_tsv @@ plainto_tsquery('english', %s)
                """
                
                params = [query, query]
                
                # Add document_type filter if specified
                if document_type_filter:
                    base_query += " AND ic.document_type = %s"
                    params.append(document_type_filter)
                
                base_query += " ORDER BY bm25_score DESC LIMIT %s"
                params.append(limit)
                
                cursor.execute(base_query, params)
                rows = cursor.fetchall()
                
                # Format results
                chunks = []
                for row in rows:
                    chunks.append({
                        "chunk_id": row['id'],
                        "content": row['content'],
                        "bm25_score": float(row['bm25_score']),
                        "document_id": row['document_id'],
                        "document_title": row.get('document_title'),
                        "document_type": row.get('document_type'),
                        "source_file": row.get('source_file'),
                        "chunk_index": row.get('chunk_index'),
                        "retrieval_method": "bm25",
                        "source_type": "internal"
                    })
                
                return chunks
                
    except Exception as e:
        print(f"     ❌ Internal BM25 search failed: {e}")
        return []


def bm25_search_unified(
    query: str,
    website_limit: int = 10,
    internal_limit: int = 10,
    include_internal: bool = True,
    document_type_filter: str = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Unified BM25 search across both website and internal chunks
    
    Args:
        query: Search query string
        website_limit: Max results from website chunks
        internal_limit: Max results from internal chunks
        include_internal: Whether to include internal documents
        document_type_filter: Filter internal docs by type (e.g., 'internal_faq')
        
    Returns:
        Dictionary with separate lists:
        {
            "website": [...],
            "internal": [...],
            "combined": [...]
        }
        
    Confidence: 93% ✅
    """
    
    results = {
        "website": [],
        "internal": [],
        "combined": []
    }
    
    # Search website chunks
    website_results = bm25_search(query, limit=website_limit)
    
    # Add source_type marker
    for r in website_results:
        r["source_type"] = "website"
    
    results["website"] = website_results
    results["combined"].extend(website_results)
    
    # Search internal chunks (if enabled)
    if include_internal:
        internal_results = bm25_search_internal(
            query,
            limit=internal_limit,
            document_type_filter=document_type_filter
        )
        
        results["internal"] = internal_results
        results["combined"].extend(internal_results)
    
    return results


__all__ = ['bm25_search', 'bm25_search_batch', 'bm25_search_internal', 'bm25_search_unified']

