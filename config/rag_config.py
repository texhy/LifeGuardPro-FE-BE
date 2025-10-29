"""
RAG Configuration - Tunable Parameters

All retrieval, fusion, and diversity parameters.
Adjust these to tune system performance.

Confidence: 95% ✅
"""

import os

RAG_CONFIG = {
    # Multi-Query Expansion (Phase 2)
    "mq_expansion": {
        "enabled": os.getenv("MQE_ENABLED", "true").lower() == "true",
        "num_queries": int(os.getenv("MQE_NUM_QUERIES", "3")),
        "max_queries": 5,
        "model": "gpt-4o-mini",  # Faster/cheaper for expansion
        "temperature": 0.7,  # Some creativity for variations
    },
    
    # BM25 Keyword Search (Phase 3.1)
    "bm25": {
        "enabled": os.getenv("BM25_ENABLED", "true").lower() == "true",
        "top_k_per_query": int(os.getenv("BM25_TOP_K", "15")),  # Phase 1: Reduced (BM25 less precise)
        "language": "english",  # PostgreSQL ts_config
    },
    
    # Vector Semantic Search (Phase 3.2)
    "vector": {
        "enabled": os.getenv("VECTOR_ENABLED", "true").lower() == "true",
        "top_k_per_query": int(os.getenv("VECTOR_TOP_K", "25")),  # Phase 1: Increased (vector more precise)
        "model": "text-embedding-3-small",
        "include_embeddings": True,  # For MMR
    },
    
    # RRF Fusion (Phase 3.3)
    "rrf": {
        "enabled": os.getenv("RRF_ENABLED", "true").lower() == "true",
        "k_parameter": int(os.getenv("RRF_K", "60")),
        "max_candidates": 200,  # Safety limit
    },
    
    # MMR Diversity (Phase 3.4)
    "mmr": {
        "enabled": os.getenv("MMR_ENABLED", "true").lower() == "true",
        "lambda_param": float(os.getenv("MMR_LAMBDA", "0.75")),  # Phase 1: Slightly favor relevance
        "final_chunks": int(os.getenv("MMR_FINAL", "12")),  # Phase 1: Increased for better coverage
        "max_final": 20,
    },
    
    # Internal Content (Phase 4 - Internal Documents)
    "internal_content": {
        "enabled": os.getenv("INTERNAL_CONTENT_ENABLED", "true").lower() == "true",
        "internal_top_k": int(os.getenv("INTERNAL_TOP_K", "5")),
        "website_top_k": int(os.getenv("WEBSITE_TOP_K", "5")),
        
        # Document type priorities (for boosting/filtering)
        "document_type_priorities": {
            "internal_faq": 1.2,  # Boost FAQ results
            "internal_pricing_rules": 1.0,
            "internal_pricing_emp_inst": 1.0,
            "internal_webpage_links": 0.8,
            "internal_contact": 0.9,
        }
    },
}

def get_config(section: str = None):
    """
    Get config section or full config
    
    Args:
        section: Config section name (e.g., 'mq_expansion', 'bm25')
                If None, returns full config
                
    Returns:
        Dict with config values
    """
    if section:
        return RAG_CONFIG.get(section, {})
    return RAG_CONFIG


__all__ = ['RAG_CONFIG', 'get_config']

