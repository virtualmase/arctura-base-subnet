"""tests/test_attestation.py — Merkle proof construction and verification."""
import pytest
from arctura_base.utils import (
    hash_output, build_merkle_proof, verify_merkle_proof, get_energy_tag,
    is_valid_address, format_address,
)


def test_hash_output_deterministic():
    output = {"balance": 1000, "block_number": 21_000_000, "address": "0xAbc"}
    h1 = hash_output(output)
    h2 = hash_output(output)
    assert h1 == h2
    assert len(h1) == 64

def test_hash_output_order_invariant():
    a = hash_output({"z": 1, "a": 2})
    b = hash_output({"a": 2, "z": 1})
    assert a == b  # sort_keys=True ensures this

def test_hash_output_sensitivity():
    h1 = hash_output({"balance": 1000})
    h2 = hash_output({"balance": 1001})
    assert h1 != h2

def test_build_proof_returns_list():
    h = "a" * 64
    proof = build_merkle_proof(h)
    assert isinstance(proof, list)
    assert len(proof) == 4  # default depth
    for node in proof:
        assert "hash" in node
        assert "direction" in node
        assert node["direction"] in ("left", "right")

def test_verify_proof_round_trip():
    output = {"result": "100000", "block_number": 21_000_000}
    h = hash_output(output)
    proof = build_merkle_proof(h)
    assert verify_merkle_proof(h, proof) is True

def test_verify_proof_rejects_tampered_hash():
    output = {"result": "100000"}
    h = hash_output(output)
    proof = build_merkle_proof(h)
    tampered = "b" * 64
    assert verify_merkle_proof(tampered, proof) is False

def test_verify_proof_rejects_tampered_proof():
    output = {"result": "100000"}
    h = hash_output(output)
    proof = build_merkle_proof(h)
    proof[0]["hash"] = "0" * 64  # tamper first node
    assert verify_merkle_proof(h, proof) is False

def test_verify_proof_rejects_empty():
    assert verify_merkle_proof("", []) is False
    assert verify_merkle_proof("a" * 64, []) is False

def test_get_energy_tag_default(monkeypatch):
    monkeypatch.delenv("ARCTURA_ENERGY_TAG", raising=False)
    assert get_energy_tag() == "unknown"

def test_get_energy_tag_valid(monkeypatch):
    monkeypatch.setenv("ARCTURA_ENERGY_TAG", "renewable_verified")
    assert get_energy_tag() == "renewable_verified"

def test_get_energy_tag_invalid(monkeypatch):
    monkeypatch.setenv("ARCTURA_ENERGY_TAG", "garbage")
    assert get_energy_tag() == "unknown"

def test_is_valid_address():
    assert is_valid_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913") is True
    assert is_valid_address("not-an-address") is False
    assert is_valid_address("0x" + "0" * 40) is True
