"""
Reciprocal Rank Fusion (RRF) Module

Merges results from multiple retrieval methods (BM25 + Vector) into a single ranked list.

Formula: RRF_score = Σ(1 / (k + rank_i))
- k = 60 (standard constant)
- rank_i = position in retrieval method i (1, 2, 3, ...)

Why RRF:
- Chunks appearing in BOTH methods get highest scores
- Robust across different query types
- Research-backed algorithm

Confidence: 90% ✅

Example:
    Chunk appears in:
    - BM25 rank 3 → RRF += 1/(60+3) = 0.0159
    - Vector rank 5 → RRF += 1/(60+5) = 0.0154
    - Total RRF = 0.0313 ← High score (in both methods!)
"""

from typing import List, Dict, Any


def rrf_fusion(
    bm25_results: List[Dict[str, Any]],
    vector_results: List[Dict[str, Any]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Merge BM25 and Vector results using Reciprocal Rank Fusion
    
    Algorithm:
    1. For each chunk, calculate RRF score from its rank in each method
    2. Chunks in both methods get higher scores
    3. Sort by RRF score DESC
    
    Args:
        bm25_results: Results from BM25 search
        vector_results: Results from vector search
        k: RRF constant (default 60)
        
    Returns:
        Fused results sorted by RRF score (DESC)
        
    Example:
        bm25 = [chunk_1, chunk_2, chunk_3, ...]
        vector = [chunk_1, chunk_4, chunk_2, ...]
        
        Chunk 1: rank_bm25=1, rank_vector=1
        → RRF = 1/(60+1) + 1/(60+1) = 0.0328 ← Highest!
        
        Chunk 2: rank_bm25=2, rank_vector=3
        → RRF = 1/(60+2) + 1/(60+3) = 0.0277
        
        Chunk 3: rank_bm25=3, not in vector
        → RRF = 1/(60+3) = 0.0159
        
    Confidence: 90% ✅
    """
    
    # Step 1: Calculate RRF scores for each chunk
    rrf_scores = {}
    chunk_data = {}
    
    # Process BM25 results
    for rank, result in enumerate(bm25_results, start=1):
        chunk_id = result.get("chunk_id")
        
        if chunk_id is None:
            continue
        
        # Add to RRF score
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
        
        # Store chunk data (if not already stored)
        if chunk_id not in chunk_data:
            chunk_data[chunk_id] = result.copy()
        else:
            # Merge: add BM25 score
            chunk_data[chunk_id]["bm25_score"] = result.get("bm25_score")
    
    # Process Vector results
    for rank, result in enumerate(vector_results, start=1):
        chunk_id = result.get("chunk_id")
        
        if chunk_id is None:
            continue
        
        # Add to RRF score
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
        
        # Store chunk data (if not already stored)
        if chunk_id not in chunk_data:
            chunk_data[chunk_id] = result.copy()
        else:
            # Merge: add Vector score and embedding
            chunk_data[chunk_id]["vector_score"] = result.get("vector_score")
            
            # Keep embedding (needed for MMR)
            if "embedding" in result:
                chunk_data[chunk_id]["embedding"] = result["embedding"]
    
    # Step 2: Create fused results with RRF scores
    fused_results = []
    
    for chunk_id, chunk in chunk_data.items():
        # Add RRF score
        chunk["rrf_score"] = rrf_scores[chunk_id]
        
        # Mark which methods found this chunk
        methods = []
        if "bm25_score" in chunk:
            methods.append("bm25")
        if "vector_score" in chunk:
            methods.append("vector")
        
        chunk["found_in_methods"] = methods
        chunk["in_both_methods"] = len(methods) == 2
        
        fused_results.append(chunk)
    
    # Step 3: Sort by RRF score (descending)
    fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
    
    return fused_results


def analyze_rrf_distribution(fused_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze RRF score distribution (for debugging/tuning)
    
    Returns:
        {
            "total_chunks": int,
            "in_both_methods": int,
            "bm25_only": int,
            "vector_only": int,
            "avg_rrf_score": float,
            "top_10_avg_rrf": float
        }
    """
    
    if not fused_results:
        return {
            "total_chunks": 0,
            "in_both_methods": 0,
            "bm25_only": 0,
            "vector_only": 0,
            "avg_rrf_score": 0.0,
            "top_10_avg_rrf": 0.0
        }
    
    in_both = sum(1 for c in fused_results if c.get("in_both_methods"))
    bm25_only = sum(1 for c in fused_results if "bm25" in c.get("found_in_methods", []) and "vector" not in c.get("found_in_methods", []))
    vector_only = sum(1 for c in fused_results if "vector" in c.get("found_in_methods", []) and "bm25" not in c.get("found_in_methods", []))
    
    avg_rrf = sum(c["rrf_score"] for c in fused_results) / len(fused_results)
    
    top_10 = fused_results[:10]
    top_10_avg = sum(c["rrf_score"] for c in top_10) / len(top_10) if top_10 else 0.0
    
    return {
        "total_chunks": len(fused_results),
        "in_both_methods": in_both,
        "bm25_only": bm25_only,
        "vector_only": vector_only,
        "avg_rrf_score": avg_rrf,
        "top_10_avg_rrf": top_10_avg
    }


def rrf_fusion_unified(
    bm25_results: Dict[str, List[Dict[str, Any]]],
    vector_results: Dict[str, List[Dict[str, Any]]],
    k: int = 60
) -> List[Dict[str, Any]]:
    """
    Merge BM25 and Vector results from unified search (website + internal)
    
    Handles results that have source_type metadata (website vs internal).
    Preserves document_type and source attribution.
    
    Args:
        bm25_results: Dict with 'combined' list from bm25_search_unified
        vector_results: Dict with 'combined' list from vector_search_unified
        k: RRF constant (default 60)
        
    Returns:
        Fused results sorted by RRF score with source attribution
        
    Example:
        bm25 = bm25_search_unified("CPR training")
        vector = await vector_search_unified("CPR training")
        fused = rrf_fusion_unified(bm25, vector)
        
    Confidence: 90% ✅
    """
    
    # Extract combined results
    bm25_combined = bm25_results.get('combined', [])
    vector_combined = vector_results.get('combined', [])
    
    # Use regular RRF fusion
    fused = rrf_fusion(bm25_combined, vector_combined, k=k)
    
    # Ensure source_type is preserved (it should already be in the results)
    # Add source statistics
    source_counts = {}
    for chunk in fused:
        source = chunk.get('source_type', 'unknown')
        source_counts[source] = source_counts.get(source, 0) + 1
    
    # Add metadata about source distribution
    if fused:
        fused[0]['_source_distribution'] = source_counts
    
    return fused


def analyze_source_distribution(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze distribution of sources in unified search results
    
    Returns:
        {
            "total_chunks": int,
            "website_chunks": int,
            "internal_chunks": int,
            "internal_by_type": {
                "internal_faq": int,
                "internal_pricing_rules": int,
                ...
            }
        }
    """
    
    if not results:
        return {
            "total_chunks": 0,
            "website_chunks": 0,
            "internal_chunks": 0,
            "internal_by_type": {}
        }
    
    website_count = 0
    internal_count = 0
    internal_by_type = {}
    
    for chunk in results:
        source_type = chunk.get('source_type', 'unknown')
        
        if source_type == 'website':
            website_count += 1
        elif source_type == 'internal':
            internal_count += 1
            doc_type = chunk.get('document_type', 'unknown')
            internal_by_type[doc_type] = internal_by_type.get(doc_type, 0) + 1
    
    return {
        "total_chunks": len(results),
        "website_chunks": website_count,
        "internal_chunks": internal_count,
        "internal_by_type": internal_by_type
    }


__all__ = ['rrf_fusion', 'analyze_rrf_distribution', 'rrf_fusion_unified', 'analyze_source_distribution']

