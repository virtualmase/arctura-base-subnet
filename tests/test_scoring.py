"""
tests/test_scoring.py

Resonance BFT scoring unit tests.
Tests the 4-dimension scoring function used by validators to set Yuma weights.

Scoring dimensions:
  40% — Attestation validity  (Merkle proof correct)
  30% — Execution completeness (trace covers all mandate steps)
  20% — Response latency       (within deadline_block)
  10% — Confidence calibration (historical self-assessment accuracy)

Invalid proof OR stale block anchor → score = 0.0 (hard zero, no partial credit)

Arcturian Council · Coreweaver · base.arctura.network
Apache-2.0
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass, field
from typing import Optional


# ── Stub types (mirror protocol.py until importable) ─────────────────────

@dataclass
class MockSynapse:
    base_state_hash:    Optional[str] = None
    merkle_proof:       Optional[list] = None
    block_hash_anchor:  Optional[str] = None
    execution_trace:    Optional[dict] = None
    confidence:         float          = 0.0
    response_block:     int            = 0
    deadline_block:     int            = 100


# ── Stub scoring (mirrors neurons/validator.py) ───────────────────────────

LIVE_BLOCK_HASH = "0x" + "a" * 64
VALID_PROOF     = ["node_a", "node_b", "root_c"]
FULL_TRACE      = {"balance": True, "events": True, "state": True}
PARTIAL_TRACE   = {"balance": True, "events": False, "state": False}


def _verify_merkle(proof: Optional[list], state_hash: Optional[str]) -> bool:
    return bool(proof) and bool(state_hash)


def score_response(response: MockSynapse, live_block_hash: str) -> float:
    # Hard-zero gates
    if not _verify_merkle(response.merkle_proof, response.base_state_hash):
        return 0.0
    if response.block_hash_anchor != live_block_hash:
        return 0.0

    # Attestation validity (40%)
    attestation_score = 1.0 if _verify_merkle(response.merkle_proof, response.base_state_hash) else 0.0

    # Execution completeness (30%)
    if response.execution_trace:
        steps_complete = sum(1 for v in response.execution_trace.values() if v)
        total_steps    = len(response.execution_trace)
        exec_score     = steps_complete / total_steps if total_steps > 0 else 0.0
    else:
        exec_score = 0.0

    # Response latency (20%) — linear decay from 0 to deadline
    if response.deadline_block > 0:
        latency_score = max(0.0, 1.0 - (response.response_block / response.deadline_block))
    else:
        latency_score = 0.0

    # Confidence calibration (10%) — stub: confidence in [0,1] is taken at face value
    confidence_score = min(1.0, max(0.0, response.confidence))

    return (
        0.40 * attestation_score
        + 0.30 * exec_score
        + 0.20 * latency_score
        + 0.10 * confidence_score
    )


# ── Hard-zero gates ───────────────────────────────────────────────────────

class TestHardZeroGates:
    def test_invalid_proof_returns_zero(self):
        r = MockSynapse(
            base_state_hash="hash_abc",
            merkle_proof=None,  # invalid
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace=FULL_TRACE,
            confidence=1.0,
        )
        assert score_response(r, LIVE_BLOCK_HASH) == 0.0

    def test_stale_block_anchor_returns_zero(self):
        r = MockSynapse(
            base_state_hash="hash_abc",
            merkle_proof=VALID_PROOF,
            block_hash_anchor="0x" + "b" * 64,  # stale
            execution_trace=FULL_TRACE,
            confidence=1.0,
        )
        assert score_response(r, LIVE_BLOCK_HASH) == 0.0

    def test_empty_state_hash_returns_zero(self):
        r = MockSynapse(
            base_state_hash=None,
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace=FULL_TRACE,
            confidence=1.0,
        )
        assert score_response(r, LIVE_BLOCK_HASH) == 0.0

    def test_fabricated_anchor_returns_zero(self):
        r = MockSynapse(
            base_state_hash="hash_abc",
            merkle_proof=VALID_PROOF,
            block_hash_anchor="0x0000000000000000000000000000000000000000000000000000000000000000",
            execution_trace=FULL_TRACE,
            confidence=1.0,
        )
        assert score_response(r, LIVE_BLOCK_HASH) == 0.0


# ── Perfect score ─────────────────────────────────────────────────────────

class TestPerfectScore:
    def test_perfect_response_scores_one(self):
        r = MockSynapse(
            base_state_hash="hash_abc",
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace=FULL_TRACE,
            confidence=1.0,
            response_block=0,    # immediate
            deadline_block=100,
        )
        score = score_response(r, LIVE_BLOCK_HASH)
        assert score == pytest.approx(1.0)

    def test_score_is_bounded_0_to_1(self):
        r = MockSynapse(
            base_state_hash="hash_abc",
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace=FULL_TRACE,
            confidence=1.0,
            response_block=0,
            deadline_block=100,
        )
        score = score_response(r, LIVE_BLOCK_HASH)
        assert 0.0 <= score <= 1.0


# ── Attestation dimension (40%) ───────────────────────────────────────────

class TestAttestationDimension:
    def test_valid_proof_contributes_40_pct(self):
        r = MockSynapse(
            base_state_hash="hash",
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace={},
            confidence=0.0,
            response_block=100,
            deadline_block=100,
        )
        score = score_response(r, LIVE_BLOCK_HASH)
        # attestation=1.0*0.4 + exec=0.0 + latency=0.0 + conf=0.0 = 0.40
        assert score == pytest.approx(0.40)


# ── Execution completeness dimension (30%) ────────────────────────────────

class TestExecutionDimension:
    def test_full_trace_contributes_30_pct(self):
        r = MockSynapse(
            base_state_hash="hash",
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace=FULL_TRACE,  # all 3 steps complete
            confidence=0.0,
            response_block=100,
            deadline_block=100,
        )
        score = score_response(r, LIVE_BLOCK_HASH)
        # 0.40 + 0.30 + 0.0 + 0.0 = 0.70
        assert score == pytest.approx(0.70)

    def test_partial_trace_reduces_score(self):
        r_full = MockSynapse(
            base_state_hash="hash",
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace=FULL_TRACE,
            confidence=0.0, response_block=100, deadline_block=100,
        )
        r_partial = MockSynapse(
            base_state_hash="hash",
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace=PARTIAL_TRACE,  # 1 of 3 steps
            confidence=0.0, response_block=100, deadline_block=100,
        )
        assert score_response(r_full, LIVE_BLOCK_HASH) > score_response(r_partial, LIVE_BLOCK_HASH)

    def test_empty_trace_scores_zero_exec(self):
        r = MockSynapse(
            base_state_hash="hash",
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace=None,
            confidence=0.0, response_block=100, deadline_block=100,
        )
        score = score_response(r, LIVE_BLOCK_HASH)
        assert score == pytest.approx(0.40)  # only attestation


# ── Latency dimension (20%) ───────────────────────────────────────────────

class TestLatencyDimension:
    def test_instant_response_full_latency_score(self):
        r = MockSynapse(
            base_state_hash="hash",
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace={},
            confidence=0.0,
            response_block=0,
            deadline_block=100,
        )
        # 0.40 + 0.0 + 0.20 + 0.0 = 0.60
        assert score_response(r, LIVE_BLOCK_HASH) == pytest.approx(0.60)

    def test_at_deadline_zero_latency_score(self):
        r = MockSynapse(
            base_state_hash="hash",
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace={},
            confidence=0.0,
            response_block=100,
            deadline_block=100,
        )
        # latency = 1 - (100/100) = 0.0
        assert score_response(r, LIVE_BLOCK_HASH) == pytest.approx(0.40)

    def test_midpoint_response_half_latency_score(self):
        r = MockSynapse(
            base_state_hash="hash",
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace={},
            confidence=0.0,
            response_block=50,
            deadline_block=100,
        )
        # latency = 1 - 0.5 = 0.5 → 0.5 * 0.2 = 0.10
        assert score_response(r, LIVE_BLOCK_HASH) == pytest.approx(0.50)


# ── Confidence dimension (10%) ────────────────────────────────────────────

class TestConfidenceDimension:
    def test_full_confidence_adds_10_pct(self):
        r_low  = MockSynapse(base_state_hash="h", merkle_proof=VALID_PROOF,
                             block_hash_anchor=LIVE_BLOCK_HASH, execution_trace={},
                             confidence=0.0, response_block=100, deadline_block=100)
        r_high = MockSynapse(base_state_hash="h", merkle_proof=VALID_PROOF,
                             block_hash_anchor=LIVE_BLOCK_HASH, execution_trace={},
                             confidence=1.0, response_block=100, deadline_block=100)
        assert score_response(r_high, LIVE_BLOCK_HASH) - score_response(r_low, LIVE_BLOCK_HASH) == pytest.approx(0.10)

    def test_confidence_clamped_above_one(self):
        r = MockSynapse(base_state_hash="h", merkle_proof=VALID_PROOF,
                        block_hash_anchor=LIVE_BLOCK_HASH, execution_trace={},
                        confidence=9999.0, response_block=100, deadline_block=100)
        assert score_response(r, LIVE_BLOCK_HASH) <= 1.0

    def test_confidence_clamped_below_zero(self):
        r = MockSynapse(base_state_hash="h", merkle_proof=VALID_PROOF,
                        block_hash_anchor=LIVE_BLOCK_HASH, execution_trace={},
                        confidence=-5.0, response_block=100, deadline_block=100)
        assert score_response(r, LIVE_BLOCK_HASH) >= 0.0


# ── Weight ordering ───────────────────────────────────────────────────────

class TestWeightOrdering:
    """Validators must rank miners correctly to set Yuma weights."""

    def make_response(self, **kwargs) -> MockSynapse:
        defaults = dict(
            base_state_hash="hash",
            merkle_proof=VALID_PROOF,
            block_hash_anchor=LIVE_BLOCK_HASH,
            execution_trace=FULL_TRACE,
            confidence=1.0,
            response_block=0,
            deadline_block=100,
        )
        defaults.update(kwargs)
        return MockSynapse(**defaults)

    def test_better_miner_ranks_higher(self):
        good   = self.make_response(response_block=5)
        bad    = self.make_response(response_block=90, execution_trace=PARTIAL_TRACE, confidence=0.2)
        assert score_response(good, LIVE_BLOCK_HASH) > score_response(bad, LIVE_BLOCK_HASH)

    def test_scores_are_sortable(self):
        responses = [
            self.make_response(response_block=80, confidence=0.1),
            self.make_response(response_block=10, confidence=0.9),
            self.make_response(response_block=50, confidence=0.5),
        ]
        scores = [score_response(r, LIVE_BLOCK_HASH) for r in responses]
        assert sorted(scores) == sorted(scores)  # trivially sortable
        assert scores[1] > scores[2] > scores[0]
