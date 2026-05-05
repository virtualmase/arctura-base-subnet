"""tests/test_protocol.py — BaseSubnetSynapse schema validation."""
import pytest
from arctura_base.protocol import BaseSubnetSynapse


def test_default_instantiation():
    s = BaseSubnetSynapse()
    assert s.mandate_id == ""
    assert s.query_type == ""
    assert s.confidence == 0.0
    assert s.energy_tag == "unknown"
    assert s.base_state_hash is None
    assert s.merkle_proof is None
    assert s.block_hash_anchor is None

def test_mandate_fields_set():
    s = BaseSubnetSynapse(
        mandate_id="test-uuid",
        base_block_range=(21_000_000, 21_000_100),
        contract_address="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        query_type="state",
        mandate_payload={"function_name": "totalSupply", "args": [], "abi": []},
        deadline_block=500,
    )
    assert s.mandate_id == "test-uuid"
    assert s.base_block_range == (21_000_000, 21_000_100)
    assert s.query_type == "state"
    assert s.deadline_block == 500

def test_attestation_fields_set():
    s = BaseSubnetSynapse()
    s.base_state_hash   = "a" * 64
    s.merkle_proof      = [{"hash": "b" * 64, "direction": "left"}]
    s.block_hash_anchor = "c" * 64
    s.confidence        = 0.87
    s.energy_tag        = "renewable_verified"
    assert s.confidence == 0.87
    assert s.energy_tag == "renewable_verified"
    assert len(s.merkle_proof) == 1

def test_energy_tag_values():
    valid = ["renewable_verified", "renewable_claimed", "unknown", "high_carbon"]
    for tag in valid:
        s = BaseSubnetSynapse(energy_tag=tag)
        assert s.energy_tag == tag
