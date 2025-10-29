"""
Retrieval Module - Advanced RAG Retrieval Components

This module contains all retrieval-related components for the advanced RAG system:

- **Multi-Query Expansion (MQE)** - Generate query variations for better coverage
- **BM25 Search** - Keyword-based retrieval using PostgreSQL full-text search
- **Vector Search** - Semantic retrieval using OpenAI embeddings + pgvector
- **RRF Fusion** - Reciprocal Rank Fusion to merge BM25 + Vector results
- **MMR Diversity** - Maximum Marginal Relevance for diverse chunk selection

Confidence: 90% ✅

Usage:
    from retrieval import expand_query, bm25_search, vector_search, rrf_fusion, mmr_select
    
    # Phase 2: Expand query
    expanded = await expand_query("What is CPO?", num_queries=3)
    
    # Phase 3: Hybrid retrieval
    for exp_query in expanded:
        bm25_results = bm25_search(exp_query["query"], limit=20)
        vector_results = await vector_search(exp_query["query"], limit=20)
    
    # Phase 3: Fusion and diversity
    fused = rrf_fusion(bm25_results, vector_results, k=60)
    final = mmr_select(fused, n=10, lambda_param=0.7)
"""

from .mq_expander import expand_query
from .bm25_search import bm25_search
from .vector_search import vector_search
from .rrf_fusion import rrf_fusion
from .mmr_diversity import mmr_select

__all__ = [
    'expand_query',
    'bm25_search',
    'vector_search',
    'rrf_fusion',
    'mmr_select'
]

