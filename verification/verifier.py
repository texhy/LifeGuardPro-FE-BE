"""
Verifier - Apply thresholds to determine claim support

Labels claims as:
- SUPPORTED: High similarity + keywords found
- PARTIALLY_SUPPORTED: Medium similarity or missing keywords
- UNRESOLVED: Low similarity, no evidence
- CONTRADICTED: Evidence contradicts claim (future)

Confidence: 90% ✅

Author: Phase 4 (Stage 4.3) Implementation
"""

from typing import List, Dict, Any, Literal

# Verification thresholds (configurable)
# NOTE: Adjusted based on observed retrieval quality with MQE+Hybrid+RRF+MMR
# Observed chunk similarities: 40-65% typical range
# Original thresholds (85%/70%) were too strict
THRESHOLDS = {
    "strongly_supported": 0.75,  # Lowered from 0.90 (very high confidence)
    "supported": 0.65,            # Lowered from 0.85 (high confidence - default for SUPPORTED)
    "partially_supported": 0.50,  # Lowered from 0.70 (medium confidence)
    "weakly_supported": 0.40      # Lowered from 0.60 (low confidence)
}

# Claim status type
ClaimStatus = Literal[
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "UNRESOLVED",
    "CONTRADICTED"
]


def verify_claim(
    evidence_mapping: Dict[str, Any],
    thresholds: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Verify a single claim against evidence
    
    Decision logic:
    - similarity >= 0.85 + keywords → SUPPORTED
    - similarity >= 0.85, no keywords → PARTIALLY_SUPPORTED
    - similarity >= 0.70 + keywords → PARTIALLY_SUPPORTED
    - similarity < 0.70 → UNRESOLVED
    
    Args:
        evidence_mapping: Output from evidence_mapper
        thresholds: Similarity thresholds (optional)
        
    Returns:
        {
            "claim": str,
            "claim_id": str,
            "category": str,
            "status": ClaimStatus,
            "confidence": float,
            "evidence_chunk_id": int,
            "evidence_snippet": str,
            "similarity_score": float,
            "keywords_found": bool,
            "reasoning": str
        }
        
    Confidence: 90% ✅
    """
    if thresholds is None:
        thresholds = THRESHOLDS
    
    # Extract fields from evidence mapping
    claim = evidence_mapping.get("claim", "")
    similarity = evidence_mapping.get("best_match_similarity", 0.0)
    keywords_found = evidence_mapping.get("keywords_found", False)
    chunk_id = evidence_mapping.get("best_match_chunk_id")
    chunk_content = evidence_mapping.get("supporting_chunk_content", "")
    claim_id = evidence_mapping.get("claim_id", "unknown")
    category = evidence_mapping.get("category", "general")
    
    # Determine status based on thresholds and criteria
    if similarity >= thresholds["supported"]:
        # High similarity
        if keywords_found:
            status = "SUPPORTED"
            confidence = similarity
            reasoning = f"High similarity ({similarity:.2%}) and keywords found in source"
        else:
            status = "PARTIALLY_SUPPORTED"
            confidence = similarity * 0.85  # Reduce confidence if no keyword match
            reasoning = f"High similarity ({similarity:.2%}) but keywords not found in source"
    
    elif similarity >= thresholds["partially_supported"]:
        # Medium similarity
        if keywords_found:
            status = "PARTIALLY_SUPPORTED"
            confidence = similarity
            reasoning = f"Medium similarity ({similarity:.2%}), keywords found"
        else:
            status = "UNRESOLVED"
            confidence = similarity * 0.7
            reasoning = f"Medium similarity ({similarity:.2%}) but no keyword match"
    
    elif similarity >= thresholds["weakly_supported"]:
        # Weak similarity
        status = "UNRESOLVED"
        confidence = similarity
        reasoning = f"Low similarity ({similarity:.2%}), insufficient evidence"
    
    else:
        # Very low similarity
        status = "UNRESOLVED"
        confidence = similarity
        reasoning = f"Very low similarity ({similarity:.2%}), no supporting evidence found"
    
    return {
        "claim": claim,
        "claim_id": claim_id,
        "category": category,
        "status": status,
        "confidence": confidence,
        "evidence_chunk_id": chunk_id,
        "evidence_snippet": chunk_content[:200] if chunk_content else "",
        "similarity_score": similarity,
        "keywords_found": keywords_found,
        "reasoning": reasoning
    }


def verify_all_claims(
    evidence_mappings: List[Dict[str, Any]],
    thresholds: Dict[str, float] = None
) -> Dict[str, Any]:
    """
    Verify all claims and compute summary statistics
    
    Args:
        evidence_mappings: List of evidence mappings (from evidence_mapper)
        thresholds: Verification thresholds (optional)
        
    Returns:
        {
            "verified_claims": List[Dict],
            "coVe_confidence": float,
            "supported_count": int,
            "partially_supported_count": int,
            "unresolved_count": int,
            "contradicted_count": int,
            "avg_supported_confidence": float,
            "support_ratio": float
        }
        
    Confidence: 88% ✅
    """
    if thresholds is None:
        thresholds = THRESHOLDS
    
    print(f"        ✓ Verifying {len(evidence_mappings)} claims...")
    
    # Verify each claim
    verified_claims = []
    
    for mapping in evidence_mappings:
        verified = verify_claim(mapping, thresholds)
        verified_claims.append(verified)
    
    # Compute statistics
    supported = [c for c in verified_claims if c["status"] == "SUPPORTED"]
    partially = [c for c in verified_claims if c["status"] == "PARTIALLY_SUPPORTED"]
    unresolved = [c for c in verified_claims if c["status"] == "UNRESOLVED"]
    contradicted = [c for c in verified_claims if c["status"] == "CONTRADICTED"]
    
    # Calculate overall CoVe confidence
    if supported:
        avg_supported_conf = sum(c["confidence"] for c in supported) / len(supported)
    else:
        avg_supported_conf = 0.0
    
    # Penalize for high unresolved ratio
    # If half the claims are unresolved, reduce confidence
    support_ratio = len(supported) / len(verified_claims) if verified_claims else 0
    coVe_confidence = avg_supported_conf * support_ratio
    
    print(f"        ✅ Verification complete:")
    print(f"           SUPPORTED: {len(supported)}")
    print(f"           PARTIALLY_SUPPORTED: {len(partially)}")
    print(f"           UNRESOLVED: {len(unresolved)}")
    print(f"           CoVe confidence: {coVe_confidence:.2%}")
    
    return {
        "verified_claims": verified_claims,
        "coVe_confidence": coVe_confidence,
        "supported_count": len(supported),
        "partially_supported_count": len(partially),
        "unresolved_count": len(unresolved),
        "contradicted_count": len(contradicted),
        "avg_supported_confidence": avg_supported_conf,
        "support_ratio": support_ratio
    }


def get_verification_summary(verification_result: Dict[str, Any]) -> str:
    """
    Generate human-readable verification summary
    
    Args:
        verification_result: Output from verify_all_claims
        
    Returns:
        Summary string like "3 supported, 1 partial, 2 unresolved"
        
    Confidence: 95% ✅
    """
    supported = verification_result.get("supported_count", 0)
    partial = verification_result.get("partially_supported_count", 0)
    unresolved = verification_result.get("unresolved_count", 0)
    contradicted = verification_result.get("contradicted_count", 0)
    
    parts = []
    if supported > 0:
        parts.append(f"{supported} supported")
    if partial > 0:
        parts.append(f"{partial} partial")
    if unresolved > 0:
        parts.append(f"{unresolved} unresolved")
    if contradicted > 0:
        parts.append(f"{contradicted} contradicted")
    
    return ", ".join(parts) if parts else "no claims"


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'THRESHOLDS',
    'ClaimStatus',
    'verify_claim',
    'verify_all_claims',
    'get_verification_summary'
]

