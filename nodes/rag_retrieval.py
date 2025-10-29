"""
RAG retrieval - Vector search in vector_db using OpenAI embeddings

Confidence: 95% ✅
Improvements:
- Uses OpenAI text-embedding-3-small (1536-dim)
- Matches document embeddings (consistent!)
- No GPU/heavy ML libraries needed
- Fast API-based embedding generation

Limitations:
- Requires OpenAI API key
- Adds ~100-200ms per query
- Costs ~$0.00002 per query
"""
from typing import Dict, Any, List
from langchain_openai import OpenAIEmbeddings
from config.database import get_connection
import os

# Lazy initialization
_embeddings = None

def get_embeddings():
    """
    Get or create OpenAI embeddings instance (lazy initialization)
    
    Confidence: 100% ✅
    
    Uses same model as document embeddings:
    - Model: text-embedding-3-small
    - Dimension: 1536
    - API-based (no GPU needed)
    """
    global _embeddings
    
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )
        print("✅ OpenAI embeddings initialized (text-embedding-3-small)")
    
    return _embeddings

async def rag_retrieval(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve relevant context from vector_db
    
    Confidence: 95% ✅
    
    Flow:
    1. Generate query embedding (OpenAI 3-small, 1536-dim)
    2. Vector search in chunks table (cosine distance)
    3. Return top-5 results with sources
    
    Args:
        state: Current graph state with messages
        
    Returns:
        Updated state with RAG context and sources
        
    State Updates:
        - rag_context: str (formatted context from chunks)
        - rag_sources: list (source URLs and titles)
        - rag_results_count: int (number of chunks retrieved)
    """
    if not state.get("messages"):
        return {
            **state,
            "rag_context": "",
            "rag_sources": [],
            "rag_results_count": 0
        }
    
    # Get last user message
    last_message = state["messages"][-1]
    user_query = last_message.content if hasattr(last_message, 'content') else str(last_message)
    
    # Handle empty query
    if not user_query.strip():
        return {
            **state,
            "rag_context": "",
            "rag_sources": [],
            "rag_results_count": 0
        }
    
    try:
        # Generate query embedding using OpenAI
        print(f"🔍 Generating OpenAI embedding for: '{user_query[:50]}...'")
        embeddings = get_embeddings()
        query_embedding = await embeddings.aembed_query(user_query)
        print(f"📊 Embedding generated: {len(query_embedding)} dimensions (OpenAI 3-small)")
        
        # Vector search in chunks table
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Cosine distance search
                # Both query and chunks are 1536-dim OpenAI embeddings ✅
                
                cur.execute("""
                    SELECT 
                        c.content,
                        c.chunk_index,
                        c.token_count,
                        d.url,
                        d.document_type,
                        d.title,
                        c.embedding <=> %s::vector as distance
                    FROM chunks c
                    JOIN documents d ON d.document_id = c.document_id
                    WHERE c.embedding IS NOT NULL
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT 5
                """, (query_embedding, query_embedding))
                
                results = cur.fetchall()
        
        print(f"✅ Retrieved {len(results)} chunks")
        
        # Build context string
        context_parts = []
        sources = []
        
        for i, result in enumerate(results, 1):
            # Format: [Source 1: Title] Content
            source_title = result['title'] or result['url']
            context_parts.append(
                f"[Source {i}: {source_title}]\n{result['content']}"
            )
            
            sources.append({
                "url": result["url"],
                "title": result["title"],
                "document_type": result["document_type"],
                "distance": float(result["distance"]),
                "chunk_index": result["chunk_index"],
                "token_count": result["token_count"]
            })
            
            # Debug: Show relevance
            print(f"  Source {i}: {source_title[:50]}... (distance: {result['distance']:.3f})")
        
        context = "\n\n---\n\n".join(context_parts)
        
        return {
            **state,
            "rag_context": context,
            "rag_sources": sources,
            "rag_results_count": len(results)
        }
        
    except Exception as e:
        print(f"❌ RAG retrieval error: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            **state,
            "rag_context": "",
            "rag_sources": [],
            "rag_results_count": 0,
            "rag_error": str(e)
        }

async def search_by_query(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Standalone vector search function
    
    Confidence: 95% ✅
    
    Args:
        query: Search query
        limit: Number of results (default 5)
        
    Returns:
        list: Search results with content and metadata
    """
    # Generate embedding using OpenAI
    embeddings = get_embeddings()
    query_embedding = await embeddings.aembed_query(query)
    
    # Search
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    c.content,
                    d.url,
                    d.title,
                    d.document_type,
                    c.embedding <=> %s::vector as distance
                FROM chunks c
                JOIN documents d ON d.document_id = c.document_id
                WHERE c.embedding IS NOT NULL
                ORDER BY c.embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, query_embedding, limit))
            
            return cur.fetchall()

def get_rag_stats(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get RAG retrieval statistics from state
    
    Confidence: 100% ✅
    
    Args:
        state: Graph state
        
    Returns:
        dict: Statistics about RAG retrieval
    """
    return {
        "results_count": state.get("rag_results_count", 0),
        "has_context": bool(state.get("rag_context")),
        "sources_count": len(state.get("rag_sources", [])),
        "avg_distance": sum(s["distance"] for s in state.get("rag_sources", [])) / len(state.get("rag_sources", [])) if state.get("rag_sources") else None
    }
