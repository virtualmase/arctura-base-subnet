"""tests/test_scoring.py — Resonance BFT scoring unit tests."""
import pytest
from arctura_base.protocol import BaseSubnetSynapse
from arctura_base.utils import hash_output, build_merkle_proof
from arctura_base.incentive import (
    score_attestation, score_completeness, score_latency,
    apply_stewardship_modifier, normalize_weights,
    detect_hash_collision, compute_calibration_accuracy,
    REQUIRED_STEPS,
)


FAKE_BLOCK_HASH = "d" * 64


def make_valid_synapse(block_hash: str = FAKE_BLOCK_HASH) -> BaseSubnetSynapse:
    output = {"result": "999", "block_number": 21_000_000}
    h = hash_output(output)
    s = BaseSubnetSynapse(
        base_state_hash=h,
        merkle_proof=build_merkle_proof(h),
        block_hash_anchor=block_hash,
        execution_trace={"steps": list(REQUIRED_STEPS), "ts": 0, "duration_ms": 100},
        confidence=0.85,
        deadline_block=100,
        energy_tag="unknown",
    )
    return s


class TestAttestationScoring:
    def test_valid_attestation_scores_one(self):
        s = make_valid_synapse()
        assert score_attestation(s, FAKE_BLOCK_HASH) == 1.0

    def test_missing_hash_scores_zero(self):
        s = BaseSubnetSynapse()
        assert score_attestation(s, FAKE_BLOCK_HASH) == 0.0

    def test_wrong_block_anchor_scores_zero(self):
        s = make_valid_synapse()
        assert score_attestation(s, "e" * 64) == 0.0

    def test_tampered_proof_scores_zero(self):
        s = make_valid_synapse()
        s.merkle_proof[0]["hash"] = "0" * 64
        assert score_attestation(s, FAKE_BLOCK_HASH) == 0.0


class TestCompletenessScoring:
    def test_full_trace_scores_one(self):
        s = BaseSubnetSynapse(execution_trace={"steps": list(REQUIRED_STEPS)})
        assert score_completeness(s) == 1.0

    def test_partial_trace_scores_partial(self):
        partial = list(REQUIRED_STEPS)[:2]
        s = BaseSubnetSynapse(execution_trace={"steps": partial})
        expected = len(partial) / len(REQUIRED_STEPS)
        assert abs(score_completeness(s) - expected) < 0.01

    def test_empty_trace_scores_zero(self):
        assert score_completeness(BaseSubnetSynapse()) == 0.0


class TestLatencyScoring:
    def test_on_time_scores_one(self):
        assert score_latency(response_block=90, deadline_block=100) == 1.0
        assert score_latency(response_block=100, deadline_block=100) == 1.0

    def test_late_scores_less(self):
        s = score_latency(response_block=106, deadline_block=100)
        assert 0.0 < s < 1.0

    def test_very_late_scores_zero(self):
        assert score_latency(response_block=200, deadline_block=100) == 0.0

    def test_no_deadline_scores_one(self):
        assert score_latency(response_block=999, deadline_block=0) == 1.0


class TestStewardshipModifier:
    def test_renewable_verified_boost(self):
        assert apply_stewardship_modifier(0.8, "renewable_verified") > 0.8

    def test_high_carbon_penalty(self):
        assert apply_stewardship_modifier(0.8, "high_carbon") < 0.8

    def test_unknown_no_change(self):
        assert apply_stewardship_modifier(0.8, "unknown") == 0.8

    def test_capped_at_one(self):
        assert apply_stewardship_modifier(1.0, "renewable_verified") == 1.0


class TestNormalization:
    def test_sums_to_one(self):
        weights = [0.3, 0.5, 0.2]
        normed = normalize_weights(weights)
        assert abs(sum(normed) - 1.0) < 1e-9

    def test_all_zeros_uniform(self):
        normed = normalize_weights([0.0, 0.0, 0.0])
        assert all(abs(w - 1/3) < 1e-9 for w in normed)

    def test_empty_returns_empty(self):
        assert normalize_weights([]) == []


class TestSybilDetection:
    def test_no_collision(self):
        hashes = {0: "aaa", 1: "bbb", 2: "ccc"}
        assert detect_hash_collision(hashes) == set()

    def test_collision_flagged(self):
        same = "a" * 64
        hashes = {i: same for i in range(4)}
        flagged = detect_hash_collision(hashes)
        assert flagged == {0, 1, 2, 3}

    def test_none_hashes_ignored(self):
        hashes = {0: None, 1: None, 2: "abc"}
        assert detect_hash_collision(hashes) == set()


class TestCalibration:
    def test_perfect_calibration(self):
        assert compute_calibration_accuracy(0.8, 0.8) == 1.0

    def test_zero_calibration(self):
        assert compute_calibration_accuracy(0.0, 1.0) == 0.0

    def test_partial_calibration(self):
        acc = compute_calibration_accuracy(0.6, 0.8)
        assert abs(acc - 0.8) < 0.01
