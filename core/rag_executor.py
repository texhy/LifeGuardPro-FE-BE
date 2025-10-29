"""
RAG Executor - FULL PIPELINE (MQE + Hybrid + RRF + MMR + CoVe)

This module handles RAG tool execution with the complete advanced retrieval pipeline.

Pipeline:
1. Phase 2: Multi-Query Expansion (MQE) - Generate 3-5 query variations
2. Phase 3.1: BM25 Search - Keyword-based retrieval
3. Phase 3.2: Vector Search - Semantic retrieval
4. Phase 3.3: RRF Fusion - Merge BM25 + Vector rankings
5. Phase 3.4: MMR Diversity - Select diverse chunks
6. Phase 4: CoVe Verification - Verify claims against evidence

Confidence: 85% ✅

Author: Full Pipeline Implementation
"""

from typing import Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# DEBUG CHUNK DISPLAY FUNCTION
# ============================================================================

def display_chunks(chunks: List[Dict[str, Any]], phase_name: str, char_limit: int = 500):
    """
    Display detailed chunk content for debugging
    
    Shows first char_limit characters of each chunk with metadata.
    Only displays if RAG_DEBUG_CHUNKS=true environment variable is set.
    
    Args:
        chunks: List of chunk dictionaries
        phase_name: Name of the RAG phase (e.g., "MMR Diversity Output")
        char_limit: Maximum characters to show per chunk (default: 500)
    """
    debug_enabled = os.getenv("RAG_DEBUG_CHUNKS", "false").lower() == "true"
    
    if not debug_enabled or not chunks:
        return
    
    print(f"\n{'='*80}")
    print(f"🔍 DEBUG: {phase_name} - {len(chunks)} chunks")
    print(f"{'='*80}\n")
    
    for i, chunk in enumerate(chunks, 1):
        content = chunk.get("content", "")
        
        # Truncate content
        content_display = content[:char_limit]
        if len(content) > char_limit:
            content_display += "..."
        
        # Extract metadata
        similarity = chunk.get("similarity_score", chunk.get("rrf_score", chunk.get("vector_score", chunk.get("bm25_score", 0))))
        source_type = chunk.get("source_type", "unknown")
        doc_type = chunk.get("document_type", "unknown")
        doc_title = chunk.get("document_title", "Unknown")
        
        print(f"Chunk {i}/{len(chunks)}:")
        print(f"  Score: {similarity:.4f}")
        print(f"  Source: {source_type}")
        print(f"  Type: {doc_type}")
        print(f"  Title: {doc_title}")
        print(f"  {'─' * 76}")
        print(f"  {content_display}")
        print(f"  {'─' * 76}\n")
    
    print(f"{'='*80}\n")


# ============================================================================
# DATABASE CONNECTION (Uses existing config)
# ============================================================================

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config.database import get_connection


# ============================================================================
# FULL RAG PIPELINE (ALL PHASES)
# ============================================================================

async def execute_rag_search(
    args: Dict[str, Any],
    state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute ADVANCED RAG search with full pipeline
    
    Pipeline:
    1. Multi-Query Expansion (3-5 queries)
    2. BM25 Search (for each query)
    3. Vector Search (for each query)
    4. RRF Fusion (merge BM25 + Vector)
    5. MMR Diversity (select 10 diverse)
    6. CoVe Verification (verify claims)
    
    Args:
        args: {query: str}
        state: Current conversation state
        
    Returns:
        {
            success: bool,
            chunks: List[Dict],
            retrieval_confidence: float,
            retrieval_method: str,
            num_results: int,
            
            # Phase 2 metrics
            expanded_queries: List[Dict],
            expansion_confidence: float,
            
            # Phase 3 metrics
            bm25_candidates: int,
            vector_candidates: int,
            rrf_fused_count: int,
            mmr_final_count: int,
            
            # Phase 4 (CoVe) metrics
            cove_enabled: bool,
            verified_claims: List[Dict],
            coVe_confidence: float,
            
            error: Optional[str]
        }
        
    Confidence: 85% ✅
    """
    
    print(f"\n  🔍 RAG Executor (FULL PIPELINE: MQE + Hybrid + RRF + MMR + CoVe)")
    
    try:
        # ═══════════════════════════════════════════════════════════
        # STEP 0: VALIDATE INPUT
        # ═══════════════════════════════════════════════════════════
        
        query = args.get("query")
        
        if not query:
            return {
                "success": False,
                "chunks": [],
                "retrieval_confidence": 0.0,
                "error": "No query provided in args"
            }
        
        print(f"  Original Query: {query[:100]}...")
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 2: MULTI-QUERY EXPANSION (MQE)
        # ═══════════════════════════════════════════════════════════
        
        from retrieval.mq_expander import expand_query, calculate_coverage_score
        from config.rag_config import get_config
        
        mq_config = get_config("mq_expansion")
        
        if mq_config.get("enabled"):
            print(f"\n  → PHASE 2: Multi-Query Expansion...")
            
            expanded_queries = await expand_query(
                query, 
                num_queries=mq_config.get("num_queries", 3)
            )
            
            # Calculate coverage score
            coverage_score = calculate_coverage_score(query, expanded_queries)
            
            print(f"     ✅ Generated {len(expanded_queries)} query variations:")
            for i, eq in enumerate(expanded_queries, 1):
                print(f"        {i}. {eq['query'][:60]}... (weight: {eq['weight']:.2f})")
            print(f"     📊 Coverage score: {coverage_score:.2%}")
            
            # DEBUG: Show expanded queries detail
            if os.getenv("RAG_DEBUG_CHUNKS") == "true":
                print(f"\n  🔍 DEBUG: MQE Expanded Queries:")
                for i, eq in enumerate(expanded_queries, 1):
                    print(f"     Query {i}: {eq['query']}")
                    print(f"       Weight: {eq['weight']:.2f}")
                    print(f"       Type: {eq.get('variation_type', 'N/A')}")
                    print()
            
        else:
            # Fallback: use original query only
            expanded_queries = [{"query": query, "weight": 1.0, "variation_type": "original"}]
            coverage_score = 1.0
            print(f"  → MQE disabled (set MQE_ENABLED=true to enable)")
            print(f"     Using original query only")
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 3: UNIFIED HYBRID RETRIEVAL (Website + Internal)
        # ═══════════════════════════════════════════════════════════
        
        from retrieval.bm25_search import bm25_search_unified
        from retrieval.vector_search import vector_search_unified
        
        bm25_config = get_config("bm25")
        vector_config = get_config("vector")
        internal_config = get_config("internal_content")
        
        all_bm25_results = []
        all_vector_results = []
        
        print(f"\n  → PHASE 3: Unified Hybrid Retrieval (Website + Internal)...")
        
        # Check if internal content is enabled
        include_internal = internal_config.get("enabled", True)
        website_limit = internal_config.get("website_top_k", 10)
        internal_limit = internal_config.get("internal_top_k", 10)
        
        if include_internal:
            print(f"     🔄 Internal documents enabled (website: {website_limit}, internal: {internal_limit})")
        else:
            print(f"     ℹ️  Internal documents disabled (website only)")
        
        # Run both searches for each expanded query
        for i, exp_query_obj in enumerate(expanded_queries, 1):
            exp_query = exp_query_obj["query"]
            
            print(f"\n     Query {i}/{len(expanded_queries)}: {exp_query[:60]}...")
            
            # BM25 Unified Search (Website + Internal)
            if bm25_config.get("enabled"):
                bm25_unified = bm25_search_unified(
                    exp_query,
                    website_limit=website_limit,
                    internal_limit=internal_limit,
                    include_internal=include_internal
                )
                bm25_results = bm25_unified.get("combined", [])
                all_bm25_results.extend(bm25_results)
                print(f"        • BM25: {len(bm25_results)} chunks (website: {len(bm25_unified.get('website', []))}, internal: {len(bm25_unified.get('internal', []))})")
            else:
                print(f"        • BM25: disabled")
            
            # Vector Unified Search (Website + Internal)
            if vector_config.get("enabled"):
                vector_unified = await vector_search_unified(
                    exp_query,
                    website_limit=website_limit,
                    internal_limit=internal_limit,
                    include_embeddings=True,  # Needed for MMR
                    include_internal=include_internal
                )
                vector_results = vector_unified.get("combined", [])
                all_vector_results.extend(vector_results)
                print(f"        • Vector: {len(vector_results)} chunks (website: {len(vector_unified.get('website', []))}, internal: {len(vector_unified.get('internal', []))})")
            else:
                print(f"        • Vector: disabled")
        
        print(f"\n     📊 Retrieval Summary:")
        print(f"        BM25 candidates: {len(all_bm25_results)}")
        print(f"        Vector candidates: {len(all_vector_results)}")
        
        # DEBUG: Show BM25 and Vector candidates
        display_chunks(all_bm25_results, "BM25 Candidates (All Queries)")
        display_chunks(all_vector_results, "Vector Candidates (All Queries)")
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 3.3: RRF FUSION
        # ═══════════════════════════════════════════════════════════
        
        from retrieval.rrf_fusion import rrf_fusion, analyze_rrf_distribution
        
        rrf_config = get_config("rrf")
        
        if rrf_config.get("enabled") and (all_bm25_results or all_vector_results):
            print(f"\n  → PHASE 3.3: RRF Fusion...")
            
            fused_chunks = rrf_fusion(
                all_bm25_results,
                all_vector_results,
                k=rrf_config.get("k_parameter", 60)
            )
            
            # Analyze distribution
            rrf_analysis = analyze_rrf_distribution(fused_chunks)
            
            print(f"     ✅ Fused {len(fused_chunks)} unique chunks")
            print(f"     📊 In both methods: {rrf_analysis['in_both_methods']}")
            print(f"        BM25 only: {rrf_analysis['bm25_only']}")
            print(f"        Vector only: {rrf_analysis['vector_only']}")
            print(f"     📊 Top 5 RRF scores: {[round(c['rrf_score'], 4) for c in fused_chunks[:5]]}")
            
            # DEBUG: Show RRF fused chunks
            display_chunks(fused_chunks[:20], "RRF Fusion Output (Top 20)")
            
        elif all_vector_results:
            # Fallback: use vector results only
            fused_chunks = all_vector_results
            # Add fake rrf_score = vector_score for compatibility
            for chunk in fused_chunks:
                chunk["rrf_score"] = chunk.get("vector_score", 0.0)
            print(f"  → RRF disabled, using vector results only")
            
        elif all_bm25_results:
            # Fallback: use BM25 results only
            fused_chunks = all_bm25_results
            # Add fake rrf_score = bm25_score for compatibility
            for chunk in fused_chunks:
                chunk["rrf_score"] = chunk.get("bm25_score", 0.0)
            print(f"  → RRF disabled, using BM25 results only")
            
        else:
            # No results from either method
            fused_chunks = []
            print(f"  → No results from BM25 or Vector search")
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 3.4: MMR DIVERSITY
        # ═══════════════════════════════════════════════════════════
        
        from retrieval.mmr_diversity import mmr_select, analyze_mmr_diversity
        
        mmr_config = get_config("mmr")
        
        if mmr_config.get("enabled") and fused_chunks:
            print(f"\n  → PHASE 3.4: MMR Diversity Selection...")
            
            final_chunks = mmr_select(
                fused_chunks,
                n=mmr_config.get("final_chunks", 10),
                lambda_param=mmr_config.get("lambda_param", 0.7)
            )
            
            # Analyze diversity
            diversity_analysis = analyze_mmr_diversity(final_chunks)
            
            print(f"     ✅ Selected {len(final_chunks)} diverse chunks")
            print(f"     📊 Unique documents: {diversity_analysis['unique_documents']}/{len(final_chunks)}")
            print(f"        Diversity ratio: {diversity_analysis['diversity_ratio']:.2%}")
            
            if final_chunks:
                avg_rrf = sum(c.get("rrf_score", 0) for c in final_chunks) / len(final_chunks)
                print(f"        Avg RRF score: {avg_rrf:.4f}")
            
            # DEBUG: Show MMR final chunks (MOST IMPORTANT - what goes to response generator!)
            display_chunks(final_chunks, "MMR Final Diverse Chunks (Sent to Response Generator)")
        else:
            # Fallback: use top 10 from fusion
            final_chunks = fused_chunks[:10] if fused_chunks else []
            print(f"  → MMR disabled, using top {len(final_chunks)} from RRF")
        
        # ═══════════════════════════════════════════════════════════
        # CALCULATE RETRIEVAL CONFIDENCE
        # ═══════════════════════════════════════════════════════════
        
        if final_chunks:
            avg_rrf = sum(c.get("rrf_score", 0) for c in final_chunks) / len(final_chunks)
            retrieval_confidence = avg_rrf
        else:
            retrieval_confidence = 0.0
        
        print(f"\n  📊 Final Retrieval Stats:")
        print(f"     Final chunks: {len(final_chunks)}")
        print(f"     Retrieval confidence: {retrieval_confidence:.2%}")
        print(f"     Retrieval method: hybrid_rrf_mmr")
        
        # ═══════════════════════════════════════════════════════════
        # BUILD RESULT OBJECT (Before CoVe)
        # ═══════════════════════════════════════════════════════════
        
        result = {
            "success": True,
            "chunks": final_chunks,
            "retrieval_confidence": retrieval_confidence,
            "retrieval_method": "hybrid_rrf_mmr",
            "num_results": len(final_chunks),
            "error": None,
            
            # Phase 2 metrics
            "expanded_queries": expanded_queries,
            "expansion_confidence": coverage_score,
            "coverage_score": coverage_score,
            
            # Phase 3 metrics
            "bm25_candidates": len(all_bm25_results),
            "vector_candidates": len(all_vector_results),
            "rrf_fused_count": len(fused_chunks),
            "mmr_final_count": len(final_chunks),
        }
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 4: COVE VERIFICATION (Disabled by default for speed)
        # ═══════════════════════════════════════════════════════════
        # NOTE: CoVe adds 30-60 seconds to response time (too slow for chatbot)
        # Set COVE_ENABLED=true to enable if you need verification
        
        cove_enabled = os.getenv("COVE_ENABLED", "false").lower() == "true"
        
        if cove_enabled and final_chunks:
            print(f"\n  → PHASE 4: CoVe Verification...")
            
            try:
                from verification.cove import verify_rag_response
                
                # Verify the response
                cove_result = await verify_rag_response(query, final_chunks)
                
                # Update result with CoVe data
                result.update({
                    "cove_enabled": True,
                    "draft_response": cove_result.get("draft_response"),
                    "verified_claims": cove_result.get("verified_claims"),
                    "coVe_confidence": cove_result.get("coVe_confidence"),
                    "supported_count": cove_result.get("supported_count"),
                    "partially_supported_count": cove_result.get("partially_supported_count"),
                    "unresolved_count": cove_result.get("unresolved_count"),
                    "verification_summary": cove_result.get("verification_summary"),
                    "claims_extracted": cove_result.get("claims_extracted", 0)
                })
                
                print(f"  ✅ FULL RAG pipeline complete!")
                print(f"     📊 Pipeline Summary:")
                print(f"        • Queries expanded: {len(expanded_queries)}")
                print(f"        • BM25 candidates: {len(all_bm25_results)}")
                print(f"        • Vector candidates: {len(all_vector_results)}")
                print(f"        • RRF fused: {len(fused_chunks)}")
                print(f"        • MMR final: {len(final_chunks)}")
                print(f"        • CoVe: {cove_result.get('verification_summary')}")
                print(f"        • Overall confidence: {cove_result.get('coVe_confidence', 0):.2%}")
                
                return result
                
            except Exception as cove_error:
                print(f"  ⚠️  CoVe verification failed: {cove_error}")
                print(f"     Falling back to non-verified response")
                
                # Fallback: return without CoVe
                result.update({
                    "cove_enabled": False,
                    "cove_error": str(cove_error)
                })
                
                print(f"  ✅ RAG pipeline complete (without CoVe)")
                
                return result
                
        else:
            # CoVe disabled or no chunks
            result["cove_enabled"] = False
            
            if not cove_enabled:
                print(f"\n  → CoVe disabled (set COVE_ENABLED=true to enable)")
            
            print(f"  ✅ RAG pipeline complete!")
            print(f"     📊 Pipeline Summary:")
            print(f"        • Queries expanded: {len(expanded_queries)}")
            print(f"        • BM25 candidates: {len(all_bm25_results)}")
            print(f"        • Vector candidates: {len(all_vector_results)}")
            print(f"        • RRF fused: {len(fused_chunks)}")
            print(f"        • MMR final: {len(final_chunks)}")
            print(f"        • Retrieval confidence: {retrieval_confidence:.2%}")
            
            return result
        
    except Exception as e:
        print(f"  ❌ RAG execution failed: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "success": False,
            "chunks": [],
            "retrieval_confidence": 0.0,
            "retrieval_method": "hybrid_rrf_mmr",
            "num_results": 0,
            "error": str(e)
        }


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'execute_rag_search'
]
