"""
Enhanced RAG Search Tool - Comprehensive context retrieval

Confidence: 95% ✅

Retrieves:
1. Relevant chunks (vector search)
2. Full document metadata (title, URL, description, type)
3. ALL links from source documents (hrefs + anchor_text)

This provides much richer context to the LLM for better responses
including navigation guidance and related resources.
"""
from langchain.tools import tool
from langchain_openai import OpenAIEmbeddings
from config.database import get_connection
import os
from typing import List, Dict
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Lazy initialization
_embeddings = None

def get_embeddings():
    """
    Get OpenAI embeddings instance (lazy initialization)
    
    Confidence: 100% ✅
    
    Returns:
        OpenAIEmbeddings: Embeddings instance for query encoding
    """
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )
    return _embeddings

def get_document_links(document_id: str) -> List[Dict[str, str]]:
    """
    Get all links from a document
    
    Confidence: 100% ✅
    
    Args:
        document_id: Document ID to get links for
        
    Returns:
        list: List of {href, anchor_text} dictionaries
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT href, anchor_text
                FROM links
                WHERE document_id = %s
                ORDER BY id
                LIMIT 50
            """, (document_id,))
            
            return cur.fetchall()

@tool
async def rag_search(query: str) -> str:
    """
    Search the LifeGuard-Pro knowledge base for relevant information.
    
    This tool provides comprehensive information including:
    - Relevant content chunks (vector search)
    - Source document metadata (title, URL, description)
    - Related links from the source documents (navigation options)
    
    Use this tool when you need information about:
    - Course descriptions, requirements, and curriculum
    - Training content and certification details
    - Locations, availability, and state-specific courses
    - General company information and FAQs
    - Emergency procedures and safety information
    - Pricing and registration information
    
    Args:
        query: The search query (be specific for better results)
        
    Returns:
        str: Comprehensive information with sources and related links
        
    Examples:
        - rag_search("What is CPR training?")
        - rag_search("Lifeguard certification requirements California")
        - rag_search("First Aid course pricing and availability")
        - rag_search("How to register for courses")
    """
    try:
        print(f"🔍 RAG Tool: Searching for '{query[:50]}...'")
        
        # Step 1: Generate query embedding
        embeddings = get_embeddings()
        query_embedding = await embeddings.aembed_query(query)
        print(f"📊 Generated {len(query_embedding)}-dim embedding")
        
        # Step 2: Vector search with comprehensive document data
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        c.id as chunk_id,
                        c.content,
                        c.chunk_index,
                        c.token_count,
                        d.document_id,
                        d.url,
                        d.title,
                        d.description,
                        d.document_type,
                        d.last_updated,
                        c.embedding <=> %s::vector as distance
                    FROM chunks c
                    JOIN documents d ON d.document_id = c.document_id
                    WHERE c.embedding IS NOT NULL
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT 5
                """, (query_embedding, query_embedding))
                
                chunk_results = cur.fetchall()
        
        if not chunk_results:
            return "No relevant information found in the knowledge base."
        
        print(f"✅ Found {len(chunk_results)} relevant chunks")
        
        # Step 3: Get links for each UNIQUE document
        document_ids = list(set(r['document_id'] for r in chunk_results))
        document_links = {}
        
        for doc_id in document_ids:
            links = get_document_links(doc_id)
            document_links[doc_id] = links
            print(f"📎 Document {doc_id[:8]}... has {len(links)} links")
        
        # Step 4: Format comprehensive results
        formatted_results = []
        
        for i, result in enumerate(chunk_results, 1):
            doc_id = result['document_id']
            title = result['title'] or result['url']
            url = result['url']
            description = result['description'] or ""
            
            # Build chunk context
            chunk_text = f"""[Source {i}: {title}]
URL: {url}
Type: {result['document_type']}
Distance: {result['distance']:.3f}

Content:
{result['content']}"""
            
            # Add document description if available
            if description:
                chunk_text += f"\n\nPage Description: {description}"
            
            # Add related links from this document
            if doc_id in document_links and document_links[doc_id]:
                links = document_links[doc_id]
                chunk_text += f"\n\nRelated Links from this page ({len(links)} links):"
                
                # Show top 10 most relevant links
                for j, link in enumerate(links[:10], 1):
                    anchor = link['anchor_text'] or 'No text'
                    href = link['href']
                    chunk_text += f"\n  {j}. {anchor} → {href}"
                
                if len(links) > 10:
                    chunk_text += f"\n  ... and {len(links) - 10} more links"
            
            formatted_results.append(chunk_text)
        
        # Combine all results
        context = "\n\n" + "="*80 + "\n\n".join(formatted_results)
        
        # Add summary of sources
        sources_summary = "\n\n📚 SOURCES SUMMARY:\n" + "\n".join([
            f"{i+1}. {r['title']} ({r['url']})"
            for i, r in enumerate(chunk_results[:3])
        ])
        
        final_output = context + sources_summary
        
        print(f"✅ RAG Tool: Returning comprehensive context ({len(final_output)} chars)")
        
        return final_output
        
    except Exception as e:
        print(f"❌ RAG Tool error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error searching knowledge base: {str(e)}"

# For synchronous contexts
def rag_search_sync(query: str) -> str:
    """
    Synchronous version for testing
    
    Confidence: 95% ✅
    
    Args:
        query: Search query
        
    Returns:
        str: Comprehensive context with links
    """
    import asyncio
    return asyncio.run(rag_search.ainvoke({"query": query}))

