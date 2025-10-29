"""
Vector Semantic Search Module

Implements semantic retrieval using OpenAI embeddings + pgvector.

Why Vector Search:
- Semantic understanding (handles synonyms, paraphrases)
- Context-aware
- High-quality OpenAI embeddings

Confidence: 92% ✅

Example:
    results = await vector_search("What is CPO?", limit=20)
    # Returns chunks ranked by cosine similarity
"""

from typing import List, Dict, Any
import os
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Import database connection
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.database import get_connection

# OpenAI client for embeddings
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def vector_search(
    query: str,
    limit: int = 20,
    include_embeddings: bool = True
) -> List[Dict[str, Any]]:
    """
    Vector semantic search using OpenAI embeddings + pgvector
    
    Steps:
    1. Embed query using OpenAI text-embedding-3-small
    2. Search PostgreSQL using pgvector <=> (cosine distance)
    3. Convert distance to similarity (1 - distance)
    4. Return top results with embeddings (for MMR later)
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        include_embeddings: If True, include embeddings in output (for MMR)
        
    Returns:
        List of chunks ranked by vector similarity:
        [
            {
                "chunk_id": int,
                "content": str,
                "vector_score": float,  # Similarity (0.0 to 1.0)
                "distance": float,      # Cosine distance
                "embedding": List[float],  # Only if include_embeddings=True
                "document_id": int,
                "document_title": str,
                "document_url": str,
                "document_type": str,
                "chunk_index": int,
                "retrieval_method": "vector"
            },
            ...
        ]
        
    Confidence: 92% ✅
    """
    
    try:
        # Step 1: Embed query
        embedding_response = client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        
        query_embedding = embedding_response.data[0].embedding
        
        # Step 2: Vector search in PostgreSQL
        with get_connection() as conn:
            with conn.cursor() as cursor:
                # pgvector similarity search
                # <=> means cosine distance in pgvector
                cursor.execute("""
                    SELECT 
                        c.id,
                        c.content,
                        c.document_id,
                        c.chunk_index,
                        d.title as document_title,
                        d.url as document_url,
                        d.document_type,
                        c.embedding <=> %s::vector as distance,
                        c.embedding
                    FROM chunks c
                    LEFT JOIN documents d ON c.document_id = d.document_id
                    WHERE c.embedding IS NOT NULL
                    ORDER BY distance ASC
                    LIMIT %s
                """, (query_embedding, limit))
                
                rows = cursor.fetchall()
                
                # Step 3: Format results
                chunks = []
                for row in rows:
                    distance = float(row['distance'])
                    similarity = 1.0 - distance  # Convert distance to similarity
                    
                    chunk = {
                        "chunk_id": row['id'],
                        "content": row['content'],
                        "vector_score": similarity,
                        "distance": distance,
                        "document_id": row['document_id'],
                        "document_title": row.get('document_title'),
                        "document_url": row.get('document_url'),
                        "document_type": row.get('document_type'),
                        "chunk_index": row.get('chunk_index'),
                        "retrieval_method": "vector"
                    }
                    
                    # Include embedding if requested (needed for MMR)
                    if include_embeddings and row['embedding'] is not None:
                        chunk["embedding"] = row['embedding']
                    
                    chunks.append(chunk)
                
                return chunks
                
    except Exception as e:
        print(f"     ❌ Vector search failed: {e}")
        import traceback
        traceback.print_exc()
        return []


async def vector_search_batch(
    queries: List[str],
    limit_per_query: int = 20,
    include_embeddings: bool = True
) -> List[Dict[str, Any]]:
    """
    Execute vector search for multiple queries
    
    Args:
        queries: List of query strings
        limit_per_query: Max results per query
        include_embeddings: Include embeddings in output
        
    Returns:
        Combined results from all queries
        
    Confidence: 90% ✅
    """
    
    all_results = []
    
    for query in queries:
        results = await vector_search(query, limit=limit_per_query, include_embeddings=include_embeddings)
        all_results.extend(results)
    
    return all_results


async def vector_search_internal(
    query: str,
    limit: int = 20,
    include_embeddings: bool = True,
    document_type_filter: str = None
) -> List[Dict[str, Any]]:
    """
    Vector semantic search on internal_chunks table
    
    Similar to vector_search but searches internal documents only.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        include_embeddings: If True, include embeddings in output (for MMR)
        document_type_filter: Filter by document_type (e.g., 'internal_faq')
        
    Returns:
        List of internal chunks ranked by vector similarity
        
    Confidence: 92% ✅
    """
    
    try:
        # Step 1: Embed query
        embedding_response = client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        
        query_embedding = embedding_response.data[0].embedding
        
        # Step 2: Vector search in internal_chunks
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
                        ic.embedding <=> %s::vector as distance,
                        ic.embedding
                    FROM internal_chunks ic
                    LEFT JOIN internal_documents id ON ic.document_id = id.document_id
                    WHERE ic.embedding IS NOT NULL
                """
                
                params = [query_embedding]
                
                # Add document_type filter if specified
                if document_type_filter:
                    base_query += " AND ic.document_type = %s"
                    params.append(document_type_filter)
                
                base_query += " ORDER BY distance ASC LIMIT %s"
                params.append(limit)
                
                cursor.execute(base_query, params)
                rows = cursor.fetchall()
                
                # Step 3: Format results
                chunks = []
                for row in rows:
                    distance = float(row['distance'])
                    similarity = 1.0 - distance
                    
                    chunk = {
                        "chunk_id": row['id'],
                        "content": row['content'],
                        "vector_score": similarity,
                        "distance": distance,
                        "document_id": row['document_id'],
                        "document_title": row.get('document_title'),
                        "document_type": row.get('document_type'),
                        "source_file": row.get('source_file'),
                        "chunk_index": row.get('chunk_index'),
                        "retrieval_method": "vector",
                        "source_type": "internal"
                    }
                    
                    # Include embedding if requested
                    if include_embeddings and row['embedding'] is not None:
                        chunk["embedding"] = row['embedding']
                    
                    chunks.append(chunk)
                
                return chunks
                
    except Exception as e:
        print(f"     ❌ Internal vector search failed: {e}")
        import traceback
        traceback.print_exc()
        return []


async def vector_search_unified(
    query: str,
    website_limit: int = 10,
    internal_limit: int = 10,
    include_embeddings: bool = True,
    include_internal: bool = True,
    document_type_filter: str = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Unified vector search across both website and internal chunks
    
    Args:
        query: Search query string
        website_limit: Max results from website chunks
        internal_limit: Max results from internal chunks
        include_embeddings: Include embeddings in output (for MMR)
        include_internal: Whether to include internal documents
        document_type_filter: Filter internal docs by type (e.g., 'internal_faq')
        
    Returns:
        Dictionary with separate lists:
        {
            "website": [...],
            "internal": [...],
            "combined": [...]
        }
        
    Confidence: 90% ✅
    """
    
    results = {
        "website": [],
        "internal": [],
        "combined": []
    }
    
    # Search website chunks
    website_results = await vector_search(
        query,
        limit=website_limit,
        include_embeddings=include_embeddings
    )
    
    # Add source_type marker
    for r in website_results:
        r["source_type"] = "website"
    
    results["website"] = website_results
    results["combined"].extend(website_results)
    
    # Search internal chunks (if enabled)
    if include_internal:
        internal_results = await vector_search_internal(
            query,
            limit=internal_limit,
            include_embeddings=include_embeddings,
            document_type_filter=document_type_filter
        )
        
        results["internal"] = internal_results
        results["combined"].extend(internal_results)
    
    return results


__all__ = ['vector_search', 'vector_search_batch', 'vector_search_internal', 'vector_search_unified']

