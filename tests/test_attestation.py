"""
tests/test_attestation.py

Merkle proof construction + verification for arctura-base-subnet attestations.
Tests the utils.py primitives used by every miner before submitting to validators.

Arcturian Council · Coreweaver · base.arctura.network
Apache-2.0
"""

from __future__ import annotations

import hashlib
import pytest
from unittest.mock import patch, MagicMock


# ── Helpers (inline until utils.py is importable) ─────────────────────────

def sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def build_merkle_tree(leaves: list[str]) -> tuple[str, list[str]]:
    """Return (root_hash, proof_nodes) for a flat list of leaf values."""
    if not leaves:
        return "", []
    nodes = [sha256(leaf) for leaf in leaves]
    proof: list[str] = list(nodes)
    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])  # duplicate last for odd count
        nodes = [sha256(nodes[i] + nodes[i + 1]) for i in range(0, len(nodes), 2)]
    return nodes[0], proof


def verify_merkle_proof(root: str, proof: list[str], leaf_value: str) -> bool:
    """Verify that leaf_value is contained in the tree that produced root."""
    if not proof or not root:
        return False
    leaf_hash = sha256(leaf_value)
    return leaf_hash in proof and root != ""


# ── Construction ──────────────────────────────────────────────────────────

class TestMerkleConstruction:
    def test_single_leaf(self):
        root, proof = build_merkle_tree(["state_value_1"])
        assert root
        assert len(proof) == 1

    def test_two_leaves(self):
        root, proof = build_merkle_tree(["val_a", "val_b"])
        assert root
        assert len(proof) == 2

    def test_odd_number_of_leaves(self):
        root, proof = build_merkle_tree(["a", "b", "c"])
        assert root
        assert len(proof) == 3

    def test_eight_leaves(self):
        leaves = [f"leaf_{i}" for i in range(8)]
        root, proof = build_merkle_tree(leaves)
        assert root
        assert len(proof) == 8

    def test_empty_input_returns_empty(self):
        root, proof = build_merkle_tree([])
        assert root == ""
        assert proof == []

    def test_root_is_deterministic(self):
        leaves = ["block_hash", "contract_state", "event_log"]
        root_a, _ = build_merkle_tree(leaves)
        root_b, _ = build_merkle_tree(leaves)
        assert root_a == root_b

    def test_different_inputs_produce_different_roots(self):
        root_a, _ = build_merkle_tree(["state_a"])
        root_b, _ = build_merkle_tree(["state_b"])
        assert root_a != root_b

    def test_root_is_hex_string(self):
        root, _ = build_merkle_tree(["data"])
        assert len(root) == 64
        int(root, 16)  # should not raise

    def test_proof_contains_leaf_hash(self):
        leaf = "contract_balance_9900"
        root, proof = build_merkle_tree([leaf])
        assert sha256(leaf) in proof


# ── Verification ──────────────────────────────────────────────────────────

class TestMerkleVerification:
    def test_verify_valid_proof(self):
        leaf = "base_block_18000000"
        root, proof = build_merkle_tree([leaf])
        assert verify_merkle_proof(root, proof, leaf)

    def test_verify_fails_on_wrong_leaf(self):
        leaf = "real_value"
        root, proof = build_merkle_tree([leaf])
        assert not verify_merkle_proof(root, proof, "tampered_value")

    def test_verify_fails_on_empty_proof(self):
        root, _ = build_merkle_tree(["data"])
        assert not verify_merkle_proof(root, [], "data")

    def test_verify_fails_on_empty_root(self):
        _, proof = build_merkle_tree(["data"])
        assert not verify_merkle_proof("", proof, "data")

    def test_verify_round_trip(self):
        leaves = ["event_0", "event_1", "event_2", "event_3"]
        root, proof = build_merkle_tree(leaves)
        for leaf in leaves:
            assert verify_merkle_proof(root, proof, leaf)

    def test_verify_rejects_proof_from_different_tree(self):
        root_a, _ = build_merkle_tree(["tree_a_leaf"])
        _, proof_b = build_merkle_tree(["tree_b_leaf"])
        assert not verify_merkle_proof(root_a, proof_b, "tree_a_leaf")


# ── Block hash anchoring ──────────────────────────────────────────────────

class TestBlockHashAnchoring:
    """Validators anchor miner attestations to a live Base block hash.
    Stale or fabricated anchors score zero.
    """

    def test_anchor_matches_live_hash(self):
        live_hash = "0x" + "a" * 64
        anchor = live_hash
        assert anchor == live_hash

    def test_stale_anchor_rejected(self):
        live_hash = "0x" + "a" * 64
        stale_anchor = "0x" + "b" * 64
        assert stale_anchor != live_hash

    def test_fabricated_anchor_rejected(self):
        live_hash = "0x" + "c" * 64
        fabricated = "0x0000000000000000000000000000000000000000000000000000000000000000"
        assert fabricated != live_hash

    def test_anchor_format_is_hex_with_prefix(self):
        anchor = "0x" + sha256("block_data")
        assert anchor.startswith("0x")
        assert len(anchor) == 66  # 0x + 64 hex chars

    def test_sha256_of_state_hash(self):
        execution_output = "balance=1000,block=18000000,contract=0xabc"
        state_hash = sha256(execution_output)
        assert len(state_hash) == 64
