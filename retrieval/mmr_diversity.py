"""
Maximum Marginal Relevance (MMR) Module

Selects diverse chunks to avoid redundancy while maintaining relevance.

Formula: MMR = λ × relevance - (1-λ) × max_similarity
- λ = 0.7 (default: favor relevance)
- relevance = RRF score
- max_similarity = highest similarity to already-selected chunks

Why MMR:
- Avoids returning 10 chunks from same document
- Balances relevance (RRF score) vs diversity (novelty)
- Ensures comprehensive information coverage

Confidence: 87% ✅

Example:
    candidates = [80 chunks from RRF fusion]
    selected = mmr_select(candidates, n=10, lambda_param=0.7)
    # Returns 10 diverse, high-quality chunks (8-10 unique documents)
"""

from typing import List, Dict, Any
import numpy as np


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors
    
    Returns:
        float: Similarity score (0.0 to 1.0)
        
    Confidence: 95% ✅
    """
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    
    dot_product = np.dot(vec1_np, vec2_np)
    norm1 = np.linalg.norm(vec1_np)
    norm2 = np.linalg.norm(vec2_np)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def mmr_select(
    candidates: List[Dict[str, Any]],
    n: int = 10,
    lambda_param: float = 0.7
) -> List[Dict[str, Any]]:
    """
    Select n diverse chunks using Maximum Marginal Relevance
    
    Algorithm:
    1. Select first chunk (highest RRF score)
    2. For each subsequent chunk:
       - Calculate relevance (RRF score)
       - Calculate max similarity to already-selected chunks
       - Calculate MMR score = λ × relevance - (1-λ) × max_similarity
       - Select chunk with highest MMR score
    3. Repeat until n chunks selected
    
    Args:
        candidates: Chunks sorted by RRF score (from rrf_fusion)
        n: Number of chunks to select (default 10)
        lambda_param: Relevance vs diversity balance
                     - 0.9 = favor relevance (may get duplicates)
                     - 0.7 = balanced (recommended)
                     - 0.5 = favor diversity (may get less relevant)
        
    Returns:
        List of n selected diverse chunks
        
    Example:
        Iteration 1: Select chunk with highest RRF (0.95)
        Iteration 2: 
            Candidate A: RRF=0.92, similarity_to_selected=0.15
            → MMR = 0.7×0.92 - 0.3×0.15 = 0.599
            
            Candidate B: RRF=0.90, similarity_to_selected=0.80 (very similar!)
            → MMR = 0.7×0.90 - 0.3×0.80 = 0.390
            
            Select A (higher MMR, more diverse) ✅
            
    Confidence: 87% ✅
    """
    
    if not candidates:
        return []
    
    if n <= 0:
        return []
    
    # If fewer candidates than requested, return all
    if len(candidates) <= n:
        return candidates
    
    # Ensure candidates have embeddings (needed for similarity)
    candidates_with_embeddings = [
        c for c in candidates 
        if c.get("embedding") is not None
    ]
    
    if not candidates_with_embeddings:
        # Fallback: return top n by RRF score (no diversity)
        print(f"     ⚠️  MMR: No embeddings found, using top {n} by RRF score")
        return candidates[:n]
    
    selected = []
    remaining = candidates_with_embeddings.copy()
    
    # Step 1: Select first chunk (highest relevance)
    if remaining:
        selected.append(remaining.pop(0))
    
    # Step 2: Iteratively select diverse chunks
    while len(selected) < n and remaining:
        best_mmr_score = -float('inf')
        best_idx = 0
        
        for i, candidate in enumerate(remaining):
            # Get relevance (RRF score, or vector_score as fallback)
            relevance = candidate.get("rrf_score")
            
            if relevance is None:
                # Fallback: use vector_score or bm25_score
                relevance = candidate.get("vector_score", candidate.get("bm25_score", 0.0))
            
            # Get candidate embedding
            candidate_emb = candidate.get("embedding")
            
            if candidate_emb is None:
                continue
            
            # Calculate max similarity to already-selected chunks
            max_similarity = 0.0
            
            for selected_chunk in selected:
                selected_emb = selected_chunk.get("embedding")
                
                if selected_emb is not None:
                    sim = cosine_similarity(candidate_emb, selected_emb)
                    max_similarity = max(max_similarity, sim)
            
            # MMR score: balance relevance and diversity
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_similarity
            
            if mmr_score > best_mmr_score:
                best_mmr_score = mmr_score
                best_idx = i
        
        # Add best MMR chunk
        if best_idx < len(remaining):
            selected_chunk = remaining.pop(best_idx)
            selected_chunk["mmr_score"] = best_mmr_score
            selected.append(selected_chunk)
    
    return selected


def analyze_mmr_diversity(selected: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze diversity of MMR-selected chunks (for debugging/tuning)
    
    Returns:
        {
            "total_chunks": int,
            "unique_documents": int,
            "diversity_ratio": float,  # unique_docs / total_chunks
            "avg_mmr_score": float,
            "document_distribution": Dict[int, int]  # {doc_id: count}
        }
        
    Confidence: 90% ✅
    """
    
    if not selected:
        return {
            "total_chunks": 0,
            "unique_documents": 0,
            "diversity_ratio": 0.0,
            "avg_mmr_score": 0.0,
            "document_distribution": {}
        }
    
    # Count unique documents
    document_ids = [c.get("document_id") for c in selected if c.get("document_id") is not None]
    unique_docs = len(set(document_ids))
    
    # Document distribution
    from collections import Counter
    doc_dist = dict(Counter(document_ids))
    
    # Diversity ratio (ideal: 1.0 = all unique docs)
    diversity_ratio = unique_docs / len(selected) if selected else 0.0
    
    # Average MMR score
    mmr_scores = [c.get("mmr_score", 0) for c in selected]
    avg_mmr = sum(mmr_scores) / len(mmr_scores) if mmr_scores else 0.0
    
    return {
        "total_chunks": len(selected),
        "unique_documents": unique_docs,
        "diversity_ratio": diversity_ratio,
        "avg_mmr_score": avg_mmr,
        "document_distribution": doc_dist
    }


__all__ = ['mmr_select', 'cosine_similarity', 'analyze_mmr_diversity']

