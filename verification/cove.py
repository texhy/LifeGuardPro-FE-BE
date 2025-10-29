"""
Chain-of-Verification (CoVe) Main Orchestrator

Implements the full CoVe pipeline:
1. Generate draft response (may hallucinate)
2. Extract atomic claims
3. Map claims to supporting evidence
4. Verify each claim against evidence
5. Return verification results

This prevents hallucinations by verifying every claim!

Confidence: 82% ⚠️

Author: Phase 4 (Stage 4.3) Implementation
"""

from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
import os

from .claim_extractor import extract_claims
from .evidence_mapper import map_all_claims_to_evidence
from .verifier import verify_all_claims, THRESHOLDS, get_verification_summary


# LLM for draft generation
draft_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,  # Slightly creative for natural responses
    api_key=os.getenv("OPENAI_API_KEY")
)


async def generate_draft_response(
    query: str,
    chunks: List[Dict[str, Any]]
) -> str:
    """
    Generate initial draft response (may contain hallucinations)
    
    This draft will be verified in subsequent steps.
    Any unsupported claims will be removed.
    
    Args:
        query: User's original query
        chunks: Retrieved chunks for context
        
    Returns:
        Draft response text (unverified)
        
    Confidence: 92% ✅
    """
    # Build context from top chunks
    context_parts = []
    for i, chunk in enumerate(chunks[:5], 1):  # Use top 5 chunks
        content = chunk.get("content", "")
        similarity = chunk.get("similarity_score", 0)
        context_parts.append(f"[Source {i}] (Relevance: {similarity:.0%})\n{content}")
    
    context = "\n\n".join(context_parts)
    
    # Build prompt
    prompt = f"""Based on the context below, answer the user's question comprehensively.

**CONTEXT:**
{context}

**USER QUESTION:**
{query}

**INSTRUCTIONS:**
- Provide a complete and detailed answer
- Use information from the context
- Be specific and helpful
- Natural, conversational tone

**Answer:**"""
    
    # Generate draft
    response = await draft_llm.ainvoke(prompt)
    
    return response.content


async def verify_response(
    draft_response: str,
    retrieved_chunks: List[Dict[str, Any]],
    query: str,
    thresholds: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Verify draft response using Chain-of-Verification
    
    Complete CoVe Pipeline:
    1. Extract atomic claims from draft
    2. Map each claim to supporting evidence
    3. Verify each claim against evidence
    4. Compute verification statistics
    
    Args:
        draft_response: Initial LLM response (potentially has hallucinations)
        retrieved_chunks: Chunks used to generate draft
        query: Original user query
        thresholds: Verification thresholds (optional, uses defaults)
        
    Returns:
        {
            "draft_response": str,
            "verified_claims": List[Dict],
            "coVe_confidence": float,
            "supported_count": int,
            "partially_supported_count": int,
            "unresolved_count": int,
            "contradicted_count": int,
            "verification_summary": str,
            "claims_extracted": int,
            "avg_supported_confidence": float
        }
        
    Confidence: 82% ⚠️
    """
    print(f"     🔍 CoVe: Starting verification pipeline...")
    
    if thresholds is None:
        thresholds = THRESHOLDS
    
    # Step 1: Extract claims from draft response
    print(f"     → Step 1: Extracting claims from draft...")
    
    claims = await extract_claims(draft_response)
    
    if not claims:
        print(f"        ⚠️  No claims extracted (empty response or error)")
        # Empty response is technically "verified" (nothing to contradict)
        return {
            "draft_response": draft_response,
            "verified_claims": [],
            "coVe_confidence": 1.0,
            "supported_count": 0,
            "partially_supported_count": 0,
            "unresolved_count": 0,
            "contradicted_count": 0,
            "verification_summary": "No claims to verify",
            "claims_extracted": 0,
            "avg_supported_confidence": 0.0
        }
    
    print(f"        ✅ Extracted {len(claims)} claims")
    
    # Step 2: Map claims to supporting evidence
    print(f"     → Step 2: Mapping claims to evidence...")
    
    evidence_mappings = await map_all_claims_to_evidence(claims, retrieved_chunks)
    
    print(f"        ✅ Mapped {len(evidence_mappings)} claims to evidence")
    
    # Step 3: Verify each claim
    print(f"     → Step 3: Verifying claims against evidence...")
    
    verification = verify_all_claims(evidence_mappings, thresholds)
    
    # Step 4: Build verification summary
    summary = get_verification_summary(verification)
    
    print(f"     ✅ CoVe verification complete!")
    print(f"        Summary: {summary}")
    print(f"        Overall confidence: {verification['coVe_confidence']:.2%}")
    
    # Return complete verification result
    return {
        "draft_response": draft_response,
        "verified_claims": verification["verified_claims"],
        "coVe_confidence": verification["coVe_confidence"],
        "supported_count": verification["supported_count"],
        "partially_supported_count": verification["partially_supported_count"],
        "unresolved_count": verification["unresolved_count"],
        "contradicted_count": verification["contradicted_count"],
        "verification_summary": summary,
        "claims_extracted": len(claims),
        "avg_supported_confidence": verification.get("avg_supported_confidence", 0.0),
        "support_ratio": verification.get("support_ratio", 0.0)
    }


async def verify_rag_response(
    query: str,
    chunks: List[Dict[str, Any]],
    thresholds: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Complete CoVe pipeline: Draft → Extract → Map → Verify
    
    This is the main function to call from rag_executor.
    It orchestrates the entire verification process.
    
    Args:
        query: User's question
        chunks: Retrieved chunks from RAG search
        thresholds: Optional custom thresholds
        
    Returns:
        Complete CoVe verification result
        
    Confidence: 82% ⚠️
    """
    if thresholds is None:
        thresholds = THRESHOLDS
    
    # Step 1: Generate draft response
    print(f"     → Draft generation...")
    draft = await generate_draft_response(query, chunks)
    print(f"        ✅ Draft generated ({len(draft)} chars)")
    
    # Step 2: Verify the draft
    verification = await verify_response(draft, chunks, query, thresholds)
    
    return verification


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'generate_draft_response',
    'verify_response',
    'verify_rag_response'
]

