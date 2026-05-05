"""
arctura_base/protocol.py

BaseSubnetSynapse — the mandate request and attestation response protocol
for the Arctura Base subnet.

Validators send BaseSubnetSynapse objects to miners containing a Base chain
mandate (what to fetch and prove). Miners return the same object populated
with an attestation: a Merkle-anchored proof of the Base chain state they
observed, tied to a live Base block hash.

Five Primitive alignment:
    P1 Sovereignty  → mandate_id uniquely identifies the mandate owner
    P2 Coherence    → deadline_block enforces forward-only ordering
    P3 Attestation  → base_state_hash + merkle_proof + block_hash_anchor
    P4 Resonance    → confidence drives Resonance BFT weight calibration
    P5 Stewardship  → energy_tag enables carbon-aware scoring modifier

Arctura Council · Coreweaver · base.arctura.network
Apache-2.0
"""

from __future__ import annotations

import bittensor as bt
from typing import Optional


class BaseSubnetSynapse(bt.Synapse):
    """
    Core protocol object for the Arctura Base subnet.

    Lifecycle:
        1. Validator creates a synapse with mandate fields populated.
        2. Validator sends it to miners via bt.dendrite.
        3. Miner executes the mandate against Base chain (deterministically).
        4. Miner populates attestation fields and returns the synapse.
        5. Validator verifies the Merkle proof against a live Base block hash.
        6. Validator assigns a Resonance BFT score and sets Yuma weights.

    Mandate fields are WRITE by validator, READ by miner.
    Attestation fields are WRITE by miner, READ by validator.
    """

    # ── Mandate fields (validator → miner) ───────────────────────────────

    mandate_id: str = ""
    """
    Unique identifier for this mandate. Format: UUID4 string.
    Used by validators to correlate responses and detect duplicate submissions.
    """

    base_block_range: tuple[int, int] = (0, 0)
    """
    Inclusive [start, end] block range on Base to query.
    Set end=0 to query a single block. Set to (0, 0) for latest block.
    """

    contract_address: Optional[str] = None
    """
    EVM contract address on Base to query (checksummed).
    Required for query_type in ("state", "events", "agent_action").
    None for balance queries.
    """

    query_type: str = ""
    """
    Category of Base chain work to perform. One of:
        "balance"      — fetch native ETH or ERC-20 balance
        "events"       — fetch contract event logs in block_range
        "state"        — call a view/pure contract function
        "agent_action" — execute an onchain action via AgentKit
    """

    mandate_payload: dict = {}
    """
    Query-type-specific parameters. Schema varies by query_type:
        balance:       {"address": str, "token_address": Optional[str]}
        events:        {"event_name": str, "filter_args": dict}
        state:         {"function_name": str, "args": list, "abi": list}
        agent_action:  {"action_type": str, "action_args": dict}
    """

    deadline_block: int = 0
    """
    Bittensor block number by which the miner must respond.
    Responses after this block receive a latency penalty in Resonance BFT scoring.
    Validators should set: deadline_block = current_block + tempo_blocks // 4
    """

    # ── Attestation fields (miner → validator) ────────────────────────────

    base_state_hash: Optional[str] = None
    """
    SHA-256 hex digest of the serialized Base chain output.
    This is the primary P3 Attestation signal. Must be deterministically
    reproducible from (base_block_range, contract_address, mandate_payload).

    Construction: hashlib.sha256(json.dumps(output, sort_keys=True).encode()).hexdigest()
    """

    merkle_proof: Optional[list] = None
    """
    Merkle proof chain anchoring base_state_hash.
    Each node: {"hash": str, "direction": "left" | "right"}

    Phase 01: simplified linear hash chain (depth=3).
    Phase 02: full binary Merkle tree with sibling nodes.
    """

    block_hash_anchor: Optional[str] = None
    """
    The live Base block hash at the time of execution.
    Validators fetch this independently and compare — stale or fabricated
    attestations that don't match a real Base block hash score 0.0.

    Critical: this is the primary anti-fabrication check.
    """

    execution_trace: Optional[dict] = None
    """
    Metadata proving the work was performed. Minimum schema:
    {
        "ts":          int,   # Unix timestamp of execution start
        "duration_ms": int,   # Execution time in milliseconds
        "steps":       list,  # Completed execution step identifiers
        "rpc_calls":   int,   # Number of Base RPC calls made
        "block_number":int,   # Actual Base block number queried
    }
    """

    confidence: float = 0.0
    """
    Miner's self-reported confidence in the attestation (0.0–1.0).
    Validators track historical accuracy of confidence scores per hotkey.
    Consistently miscalibrated confidence is penalized in Resonance BFT scoring.
    Be accurate — overconfidence is penalized as much as underconfidence.
    """

    energy_tag: str = "unknown"
    """
    P5 Stewardship energy provenance declaration.
    Used by validators to apply carbon-aware weight modifiers.

    Valid values:
        "renewable_verified"  — backed by verified RECs or grid certificate
        "renewable_claimed"   — self-declared, not yet verified
        "unknown"             — not declared (default, no modifier applied)
        "high_carbon"         — declared or inferred high-carbon source

    Source: ARCTURA_ENERGY_TAG environment variable on the miner node.
    Phase 03 will replace self-declaration with Stewardship Index API verification.
    """

    # ── Computed fields (set by validator post-scoring) ───────────────────

    resonance_score: Optional[float] = None
    """
    Final Resonance BFT score (0.0–1.0) assigned by the validator after
    verifying the attestation. NOT set by miners.
    Populated by validator.py for logging and debugging purposes.
    """
