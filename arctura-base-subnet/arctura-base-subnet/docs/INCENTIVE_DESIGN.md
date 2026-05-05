# Incentive Design — Resonance BFT Scoring

## Overview

Validators score miners on four dimensions. Scores determine Yuma Consensus
weights, which determine TAO emission distribution.

## Scoring Dimensions

| Dimension | Weight | Description |
|-----------|--------|-------------|
| Attestation validity | 40% | Merkle proof valid + block_hash_anchor matches |
| Execution completeness | 30% | execution_trace covers all required steps |
| Response latency | 20% | Response within deadline_block |
| Confidence calibration | 10% | Historical accuracy of self-reported confidence |

## Anti-Gaming Properties

| Attack | Mitigation |
|--------|-----------|
| Fabricated state hash | Merkle proof verification fails → 0.0 |
| Stale attestation | block_hash_anchor mismatch → 0.0 |
| Pre-computed proof | block_hash_anchor tied to a block that must exist at query time |
| Incomplete execution | Completeness scoring penalizes missing trace steps |
| Sybil (identical hashes) | Hash collision detection → 75% score penalty |
| Overconfident miner | Calibration tracking penalizes consistent miscalibration |

## P5 Stewardship Modifier

| Energy Tag | Modifier |
|-----------|---------|
| `renewable_verified` | ×1.15 (+15%) |
| `renewable_claimed` | ×1.05 (+5%) |
| `unknown` | ×1.00 (no change) |
| `high_carbon` | ×0.90 (-10%) |

Set via `ARCTURA_ENERGY_TAG` in `.env`. Phase 03 replaces self-declaration
with Stewardship Index API verification.

## Validator Economics

Validators earn TAO proportional to stake weight × Yuma Consensus alignment.
Validators who consistently set weights aligned with network consensus earn
more than outliers. Missing a tempo period = zero earnings for that period.
