"""
arctura_base/utils.py

Utility functions for the Arctura Base subnet.

    build_merkle_proof   — Construct a Merkle proof chain for an attestation hash
    verify_merkle_proof  — Verify a Merkle proof chain
    hash_output          — Deterministically hash Base chain output for attestation
    get_energy_tag       — Resolve P5 Stewardship energy tag from environment
    format_address       — EVM address normalization helper

Arctura Council · Coreweaver · base.arctura.network
Apache-2.0
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any


# ── Hashing ───────────────────────────────────────────────────────────────

def hash_output(output: dict) -> str:
    """
    Deterministically hash a Base chain execution output.

    The output dict is serialized with sorted keys and no extra whitespace,
    then SHA-256 hashed. This is the base_state_hash stored in the synapse.

    Any two miners querying the same Base state at the same block number
    will produce the same hash — this is the determinism property required
    for Merkle proof verification by validators.

    Args:
        output: Serializable dict returned by BaseRPCClient.execute_mandate()

    Returns:
        SHA-256 hex digest (64 characters).
    """
    serialized = json.dumps(output, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# ── Merkle proof ──────────────────────────────────────────────────────────

def build_merkle_proof(
    attestation_hash: str,
    depth: int = 4,
    salt: str = "arctura-base-v1",
) -> list[dict]:
    """
    Build a Merkle proof chain for an attestation hash.

    Phase 01: simplified linear hash chain. Each proof node is derived from
    the previous hash and a deterministic salt — creating a verifiable chain
    without requiring a full binary Merkle tree.

    Phase 02 will implement a proper binary Merkle tree with real sibling nodes,
    enabling third-party verification without re-running the execution.

    Args:
        attestation_hash: SHA-256 hex digest of the execution output.
        depth:            Number of proof nodes (default: 4).
        salt:             Namespace salt preventing cross-subnet proof reuse.

    Returns:
        List of proof nodes: [{"hash": str, "direction": "left"|"right"}, ...]
    """
    if not attestation_hash or len(attestation_hash) != 64:
        return []

    proof: list[dict] = []
    current = attestation_hash

    for i in range(depth):
        sibling_input = f"{salt}:{i}:{current}"
        sibling = hashlib.sha256(sibling_input.encode()).hexdigest()
        direction = "left" if i % 2 == 0 else "right"

        proof.append({"hash": sibling, "direction": direction})

        if direction == "left":
            combined = sibling + current
        else:
            combined = current + sibling

        current = hashlib.sha256(combined.encode()).hexdigest()

    return proof


def verify_merkle_proof(
    attestation_hash: str,
    proof: list[dict],
    salt: str = "arctura-base-v1",
) -> bool:
    """
    Verify a Merkle proof chain against an attestation hash.

    Replays the proof construction deterministically. Returns True if and only
    if the proof was produced by build_merkle_proof for this attestation_hash
    with the same salt.

    Args:
        attestation_hash: The base_state_hash from the miner's synapse.
        proof:            The merkle_proof list from the miner's synapse.
        salt:             Must match the salt used during build_merkle_proof.

    Returns:
        True if the proof is valid, False otherwise.
    """
    if not attestation_hash or not proof:
        return False

    try:
        current = attestation_hash

        for i, node in enumerate(proof):
            expected_sibling_input = f"{salt}:{i}:{current}"
            expected_sibling = hashlib.sha256(
                expected_sibling_input.encode()
            ).hexdigest()

            # The sibling hash in the proof must match what we'd generate
            if node.get("hash") != expected_sibling:
                return False

            direction = node.get("direction")
            if direction == "left":
                combined = expected_sibling + current
            elif direction == "right":
                combined = current + expected_sibling
            else:
                return False

            current = hashlib.sha256(combined.encode()).hexdigest()

        # If we reached here, all nodes verified correctly
        return True

    except (KeyError, TypeError, AttributeError):
        return False


# ── P5 Stewardship ────────────────────────────────────────────────────────

_VALID_ENERGY_TAGS: frozenset[str] = frozenset({
    "renewable_verified",
    "renewable_claimed",
    "unknown",
    "high_carbon",
})


def get_energy_tag() -> str:
    """
    Resolve the P5 Stewardship energy provenance tag for this miner node.

    Phase 01: reads ARCTURA_ENERGY_TAG environment variable.
    Phase 03: replaced by Stewardship Index API call with verified certificates.

    Returns:
        One of: "renewable_verified" | "renewable_claimed" | "unknown" | "high_carbon"
        Defaults to "unknown" for undeclared or invalid values.
    """
    tag = os.environ.get("ARCTURA_ENERGY_TAG", "unknown").strip().lower()
    return tag if tag in _VALID_ENERGY_TAGS else "unknown"


# ── EVM address helpers ───────────────────────────────────────────────────

def format_address(address: str) -> str:
    """
    Normalize an EVM address to checksummed format.

    Raises ValueError if the address is not a valid EVM address.
    """
    from web3 import Web3

    try:
        return Web3.to_checksum_address(address)
    except Exception as e:
        raise ValueError(f"Invalid EVM address: {address!r}") from e


def is_valid_address(address: str) -> bool:
    """Return True if address is a valid EVM address (any casing)."""
    from web3 import Web3

    try:
        Web3.to_checksum_address(address)
        return True
    except Exception:
        return False
