"""
arctura_base — Base × Bittensor subnet protocol package.

The first open-source Bittensor subnet bridging Base blockchain intelligence
into the decentralized AI network.

    Base Mainnet ──▶ arctura-base-subnet ──▶ TAO Emissions

Exports:
    BaseSubnetSynapse   — mandate + attestation protocol object
    score_response      — Resonance BFT scoring function
    normalize_weights   — Yuma Consensus weight normalizer
    apply_stewardship   — P5 carbon-aware weight modifier
    build_merkle_proof  — Merkle proof construction
    verify_merkle_proof — Merkle proof verification
    get_energy_tag      — P5 Stewardship energy tag resolver

Arctura Council · Coreweaver · base.arctura.network
Apache-2.0
"""

from arctura_base.protocol import BaseSubnetSynapse
from arctura_base.incentive import (
    score_response,
    normalize_weights,
    apply_stewardship_modifier as apply_stewardship,
)
from arctura_base.utils import build_merkle_proof, verify_merkle_proof, get_energy_tag

__version__ = "0.1.0"
__author__ = "Arctura Collective"
__license__ = "Apache-2.0"

__all__ = [
    "BaseSubnetSynapse",
    "score_response",
    "normalize_weights",
    "apply_stewardship",
    "build_merkle_proof",
    "verify_merkle_proof",
    "get_energy_tag",
]
