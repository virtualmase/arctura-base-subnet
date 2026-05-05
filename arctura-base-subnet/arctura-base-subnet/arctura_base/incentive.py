"""
arctura_base/incentive.py

Resonance BFT scoring for the Arctura Base subnet validator.

Scoring dimensions (Phase 01):
    40%  Attestation validity    — Merkle proof cryptographic check + block_hash_anchor match
    30%  Execution completeness  — execution_trace covers required mandate steps
    20%  Response latency        — response within deadline_block
    10%  Confidence calibration  — historical accuracy of miner self-scoring

P5 Stewardship modifier applied after base score computation:
    renewable_verified  → ×1.15 (+15%)
    renewable_claimed   → ×1.05 (+5%)
    unknown             → ×1.00 (no change)
    high_carbon         → ×0.90 (-10%)

Anti-gaming properties:
    • Fabricated hash:     Merkle proof verification fails → 0.0
    • Stale attestation:   block_hash_anchor mismatch → 0.0
    • Incomplete trace:    completeness penalty → reduced score
    • Late response:       linear latency decay after deadline_block
    • Sybil detection:     identical hashes across UIDs flagged (see validator.py)

Arctura Council · Coreweaver · base.arctura.network
Apache-2.0
"""

from __future__ import annotations

import hashlib
from arctura_base.protocol import BaseSubnetSynapse
from arctura_base.utils import verify_merkle_proof


# ── Constants ─────────────────────────────────────────────────────────────

# Required execution steps that a complete miner trace must contain
REQUIRED_STEPS: frozenset[str] = frozenset({
    "rpc_fetch",
    "output_hash",
    "merkle_build",
    "block_anchor",
})

# Dimension weights — must sum to 1.0
WEIGHT_ATTESTATION   = 0.40
WEIGHT_COMPLETENESS  = 0.30
WEIGHT_LATENCY       = 0.20
WEIGHT_CALIBRATION   = 0.10

assert abs(WEIGHT_ATTESTATION + WEIGHT_COMPLETENESS + WEIGHT_LATENCY + WEIGHT_CALIBRATION - 1.0) < 1e-9

# Latency grace window (blocks after deadline_block before score hits 0.0)
LATENCY_GRACE_BLOCKS = 12  # ~2.4 minutes at 12s/block

# P5 Stewardship modifiers
STEWARDSHIP_MODIFIER: dict[str, float] = {
    "renewable_verified": 1.15,
    "renewable_claimed":  1.05,
    "unknown":            1.00,
    "high_carbon":        0.90,
}


# ── Dimension 1: Attestation validity ─────────────────────────────────────

def score_attestation(
    synapse: BaseSubnetSynapse,
    live_block_hash: str,
) -> float:
    """
    Score the cryptographic validity of a miner's attestation (0.0 or 1.0).

    Two checks — both must pass for a non-zero score:
        1. Merkle proof is cryptographically valid for base_state_hash.
        2. block_hash_anchor matches the validator's independently-fetched
           live Base block hash for the queried block.

    The block_hash_anchor check is the primary anti-fabrication mechanism:
    a miner cannot pre-compute attestations for blocks that don't exist yet.

    Args:
        synapse:         Miner's completed synapse response.
        live_block_hash: Block hash the validator fetched independently.

    Returns:
        1.0 if both checks pass, 0.0 otherwise.
    """
    if not synapse.base_state_hash or not synapse.merkle_proof:
        return 0.0

    # Check 1: Merkle proof validity
    if not verify_merkle_proof(synapse.base_state_hash, synapse.merkle_proof):
        return 0.0

    # Check 2: Block hash anchor — reject stale or fabricated attestations
    if synapse.block_hash_anchor != live_block_hash:
        return 0.0

    return 1.0


# ── Dimension 2: Execution completeness ───────────────────────────────────

def score_completeness(synapse: BaseSubnetSynapse) -> float:
    """
    Score how completely the miner's execution trace covers required steps.

    Returns:
        Float [0.0, 1.0] representing fraction of required steps present.
    """
    if not synapse.execution_trace:
        return 0.0

    steps_present = set(synapse.execution_trace.get("steps", []))
    if not steps_present:
        return 0.0

    covered = len(steps_present & REQUIRED_STEPS)
    return covered / len(REQUIRED_STEPS)


# ── Dimension 3: Response latency ─────────────────────────────────────────

def score_latency(response_block: int, deadline_block: int) -> float:
    """
    Score response latency relative to the mandate deadline_block.

    Scoring curve:
        response_block <= deadline_block:                    1.0  (on time)
        deadline_block < response_block <= deadline_block+grace: linear decay
        response_block > deadline_block + grace:             0.0  (too late)

    Args:
        response_block: Bittensor block when the validator received the response.
        deadline_block: Deadline set in the mandate synapse.

    Returns:
        Float [0.0, 1.0].
    """
    if deadline_block <= 0:
        return 1.0  # No deadline set — no penalty

    blocks_late = response_block - deadline_block

    if blocks_late <= 0:
        return 1.0
    if blocks_late >= LATENCY_GRACE_BLOCKS:
        return 0.0

    return 1.0 - (blocks_late / LATENCY_GRACE_BLOCKS)


# ── Dimension 4: Confidence calibration ───────────────────────────────────

def compute_calibration_accuracy(
    reported_confidence: float,
    actual_score: float,
) -> float:
    """
    Compute how accurately a miner's self-reported confidence tracks actual performance.

    Accuracy = 1.0 - |confidence - actual_score|
    Perfect calibration: confidence == actual_score → 1.0
    Maximum miscalibration: |confidence - actual_score| == 1.0 → 0.0

    Args:
        reported_confidence: Miner's self-reported confidence (0.0–1.0).
        actual_score:        Computed base score (before calibration dimension).

    Returns:
        Float [0.0, 1.0].
    """
    return max(0.0, 1.0 - abs(reported_confidence - actual_score))


# ── Main scoring function ──────────────────────────────────────────────────

def score_response(
    synapse: BaseSubnetSynapse,
    live_block_hash: str,
    response_block: int,
    historical_calibration: float = 0.5,
) -> float:
    """
    Compute the Resonance BFT score for a miner's synapse response.

    This is the primary function called by neurons/validator.py.

    Scoring formula:
        score = 0.40 × attestation
              + 0.30 × completeness
              + 0.20 × latency
              + 0.10 × calibration

    Args:
        synapse:                Completed miner synapse with attestation fields.
        live_block_hash:        Block hash the validator fetched independently.
        response_block:         Bittensor block at which the response arrived.
        historical_calibration: Miner's historical confidence accuracy (0.0–1.0).
                                Default 0.5 (neutral) for new miners.

    Returns:
        Float [0.0, 1.0] — the Resonance BFT score.
    """
    if synapse is None or synapse.base_state_hash is None:
        return 0.0

    # Compute each dimension
    attestation  = score_attestation(synapse, live_block_hash)
    completeness = score_completeness(synapse)
    latency      = score_latency(response_block, synapse.deadline_block)

    # Base score (without calibration dimension, for calibration computation)
    base_score = (
        WEIGHT_ATTESTATION  * attestation
        + WEIGHT_COMPLETENESS * completeness
        + WEIGHT_LATENCY      * latency
    )

    # Calibration dimension uses historical accuracy
    calibration = historical_calibration

    final_score = base_score + WEIGHT_CALIBRATION * calibration

    return round(min(max(final_score, 0.0), 1.0), 6)


# ── P5 Stewardship modifier ───────────────────────────────────────────────

def apply_stewardship_modifier(base_score: float, energy_tag: str) -> float:
    """
    Apply P5 Stewardship carbon-aware weight modifier.

    Miners who declare verified renewable energy sources receive higher weight.
    This incentivizes low-carbon operation at the infrastructure level.

    Args:
        base_score:  Resonance BFT score before stewardship adjustment.
        energy_tag:  Miner's declared energy provenance tag.

    Returns:
        Adjusted score, capped at 1.0.
    """
    modifier = STEWARDSHIP_MODIFIER.get(energy_tag, 1.00)
    return round(min(base_score * modifier, 1.0), 6)


# ── Sybil detection ───────────────────────────────────────────────────────

def detect_hash_collision(
    uid_hashes: dict[int, str | None],
) -> set[int]:
    """
    Detect potential Sybil attack: multiple miners returning identical attestation hashes.

    If N miners return the exact same base_state_hash in the same tempo period,
    this is suspicious — legitimate independent execution should produce the same
    hash (determinism), but near-identical timing combined with the same hash
    across many UIDs can indicate Sybil coordination.

    Phase 01: flag UIDs sharing a hash with >2 other miners (threshold configurable).
    Phase 02: cross-reference with historical patterns.

    Args:
        uid_hashes: {uid: base_state_hash | None} for all miners this tempo.

    Returns:
        Set of UIDs flagged for potential Sybil behavior.
    """
    COLLISION_THRESHOLD = 3  # Flag if >3 miners share the same hash

    from collections import defaultdict
    hash_to_uids: dict[str, list[int]] = defaultdict(list)

    for uid, h in uid_hashes.items():
        if h is not None:
            hash_to_uids[h].append(uid)

    flagged: set[int] = set()
    for h, uids in hash_to_uids.items():
        if len(uids) > COLLISION_THRESHOLD:
            flagged.update(uids)

    return flagged


# ── Weight normalization ───────────────────────────────────────────────────

def normalize_weights(weights: list[float]) -> list[float]:
    """
    Normalize a list of scores to sum to 1.0 for Yuma Consensus submission.

    Yuma Consensus requires weights to sum to exactly 1.0.
    If all scores are 0.0 (e.g., all miners failed), returns uniform weights
    to avoid dividing by zero — validators still submit to signal they're alive.

    Args:
        weights: Raw Resonance BFT scores for each miner UID.

    Returns:
        Normalized list summing to 1.0.
    """
    total = sum(weights)
    if total == 0.0:
        n = len(weights)
        return [1.0 / n] * n if n > 0 else []
    return [round(w / total, 8) for w in weights]
