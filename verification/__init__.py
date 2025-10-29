"""
Verification Module - Chain-of-Verification (CoVe)

This module implements hallucination prevention through claim verification.

Components:
- claim_extractor: Extract atomic claims from response
- evidence_mapper: Map claims to supporting evidence
- verifier: Apply thresholds and verify claims
- cove: Main orchestration

Confidence: 82% ⚠️

Author: Phase 4 (Sub-Phase 2.3) Implementation
"""

from .claim_extractor import extract_claims, count_claims_by_category
from .evidence_mapper import map_claim_to_evidence, map_all_claims_to_evidence, cosine_similarity
from .verifier import verify_claim, verify_all_claims, THRESHOLDS, ClaimStatus
from .cove import verify_rag_response, verify_response, generate_draft_response

__all__ = [
    # Claim extraction
    'extract_claims',
    'count_claims_by_category',
    
    # Evidence mapping
    'map_claim_to_evidence',
    'map_all_claims_to_evidence',
    'cosine_similarity',
    
    # Verification
    'verify_claim',
    'verify_all_claims',
    'THRESHOLDS',
    'ClaimStatus',
    
    # Main CoVe
    'verify_rag_response',
    'verify_response',
    'generate_draft_response'
]

