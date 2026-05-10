"""
tests/test_protocol.py

BaseSubnetSynapse schema validation tests.
Verifies mandate (validator→miner) and attestation (miner→validator) field contracts.

Arcturian Council · Coreweaver · base.arctura.network
Apache-2.0
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass, field
from typing import Optional


# ── Stub synapse (mirrors protocol.py) ───────────────────────────────────

@dataclass
class BaseSubnetSynapse:
    # Mandate (validator → miner)
    base_block_range:   tuple          = (0, 0)
    contract_address:   Optional[str]  = None
    query_type:         str            = ""
    mandate_payload:    dict           = field(default_factory=dict)

    # Attestation (miner → validator)
    base_state_hash:    Optional[str]  = None
    merkle_proof:       Optional[list] = None
    block_hash_anchor:  Optional[str]  = None
    execution_trace:    Optional[dict] = None
    confidence:         float          = 0.0

    VALID_QUERY_TYPES = {"balance", "events", "state", "agent_action"}

    def is_mandate_valid(self) -> bool:
        start, end = self.base_block_range
        if end <= start:
            return False
        if self.query_type not in self.VALID_QUERY_TYPES:
            return False
        return True

    def is_attestation_complete(self) -> bool:
        return all([
            self.base_state_hash is not None,
            self.merkle_proof is not None,
            self.block_hash_anchor is not None,
            0.0 <= self.confidence <= 1.0,
        ])


# ── Mandate validation ────────────────────────────────────────────────────

class TestMandateValidation:
    def test_valid_balance_mandate(self):
        s = BaseSubnetSynapse(
            base_block_range=(18_000_000, 18_001_000),
            contract_address="0xabc123",
            query_type="balance",
            mandate_payload={"address": "0xuser"},
        )
        assert s.is_mandate_valid()

    def test_valid_events_mandate(self):
        s = BaseSubnetSynapse(
            base_block_range=(17_000_000, 17_050_000),
            query_type="events",
            mandate_payload={"event": "Transfer"},
        )
        assert s.is_mandate_valid()

    def test_valid_state_mandate(self):
        s = BaseSubnetSynapse(
            base_block_range=(18_000_000, 18_000_100),
            query_type="state",
        )
        assert s.is_mandate_valid()

    def test_valid_agent_action_mandate(self):
        s = BaseSubnetSynapse(
            base_block_range=(18_000_000, 18_000_500),
            query_type="agent_action",
            mandate_payload={"action": "swap", "amount": "1.0"},
        )
        assert s.is_mandate_valid()

    def test_invalid_query_type_fails(self):
        s = BaseSubnetSynapse(
            base_block_range=(18_000_000, 18_001_000),
            query_type="invalid_type",
        )
        assert not s.is_mandate_valid()

    def test_empty_query_type_fails(self):
        s = BaseSubnetSynapse(
            base_block_range=(18_000_000, 18_001_000),
            query_type="",
        )
        assert not s.is_mandate_valid()

    def test_reversed_block_range_fails(self):
        s = BaseSubnetSynapse(
            base_block_range=(18_001_000, 18_000_000),  # end < start
            query_type="balance",
        )
        assert not s.is_mandate_valid()

    def test_zero_block_range_fails(self):
        s = BaseSubnetSynapse(
            base_block_range=(0, 0),
            query_type="balance",
        )
        assert not s.is_mandate_valid()

    def test_equal_block_range_fails(self):
        s = BaseSubnetSynapse(
            base_block_range=(18_000_000, 18_000_000),
            query_type="balance",
        )
        assert not s.is_mandate_valid()


# ── Attestation completeness ──────────────────────────────────────────────

class TestAttestationCompleteness:
    def test_complete_attestation_passes(self):
        s = BaseSubnetSynapse(
            base_state_hash="abc123hash",
            merkle_proof=["node1", "node2"],
            block_hash_anchor="0x" + "a" * 64,
            execution_trace={"balance": True},
            confidence=0.95,
        )
        assert s.is_attestation_complete()

    def test_missing_state_hash_fails(self):
        s = BaseSubnetSynapse(
            base_state_hash=None,
            merkle_proof=["node1"],
            block_hash_anchor="0x" + "a" * 64,
            confidence=0.9,
        )
        assert not s.is_attestation_complete()

    def test_missing_proof_fails(self):
        s = BaseSubnetSynapse(
            base_state_hash="hash",
            merkle_proof=None,
            block_hash_anchor="0x" + "a" * 64,
            confidence=0.9,
        )
        assert not s.is_attestation_complete()

    def test_missing_anchor_fails(self):
        s = BaseSubnetSynapse(
            base_state_hash="hash",
            merkle_proof=["node1"],
            block_hash_anchor=None,
            confidence=0.9,
        )
        assert not s.is_attestation_complete()

    def test_confidence_above_one_fails(self):
        s = BaseSubnetSynapse(
            base_state_hash="hash",
            merkle_proof=["node1"],
            block_hash_anchor="0x" + "a" * 64,
            confidence=1.1,  # invalid
        )
        assert not s.is_attestation_complete()

    def test_negative_confidence_fails(self):
        s = BaseSubnetSynapse(
            base_state_hash="hash",
            merkle_proof=["node1"],
            block_hash_anchor="0x" + "a" * 64,
            confidence=-0.1,  # invalid
        )
        assert not s.is_attestation_complete()

    def test_zero_confidence_is_valid(self):
        s = BaseSubnetSynapse(
            base_state_hash="hash",
            merkle_proof=["node1"],
            block_hash_anchor="0x" + "a" * 64,
            confidence=0.0,  # valid — miner uncertain but honest
        )
        assert s.is_attestation_complete()


# ── Payload contracts ─────────────────────────────────────────────────────

class TestPayloadContracts:
    def test_empty_payload_is_allowed(self):
        s = BaseSubnetSynapse(
            base_block_range=(18_000_000, 18_001_000),
            query_type="state",
            mandate_payload={},
        )
        assert s.is_mandate_valid()

    def test_payload_preserves_arbitrary_keys(self):
        payload = {"contract": "0xabc", "method": "balanceOf", "args": ["0xuser"]}
        s = BaseSubnetSynapse(
            base_block_range=(18_000_000, 18_001_000),
            query_type="state",
            mandate_payload=payload,
        )
        assert s.mandate_payload == payload

    def test_default_synapse_is_not_valid_mandate(self):
        s = BaseSubnetSynapse()
        assert not s.is_mandate_valid()

    def test_default_synapse_attestation_incomplete(self):
        s = BaseSubnetSynapse()
        assert not s.is_attestation_complete()
