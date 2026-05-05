"""
neurons/miner.py

Arctura Base subnet miner.

Receives BaseSubnetSynapse mandates from validators, executes the specified
Base chain query deterministically, builds a Merkle-anchored attestation
proof, and returns the completed synapse.

Execution pipeline (L1 → L5 signal stack):
    L1 Orchestration   → mandate received, dispatched via forward()
    L2 Sandbox         → deterministic Base RPC execution via BaseRPCClient
    L3 Cognitive Mesh  → optional AgentKit execution for agent_action types
    L4 Memory Fabric   → local execution trace built and stored
    L5 Action Surface  → completed synapse returned via axon to validator

Usage:
    python neurons/miner.py \\
        --wallet.name miner \\
        --wallet.hotkey default \\
        --subtensor.network test \\
        --netuid 1

Arctura Council · Coreweaver · base.arctura.network
Apache-2.0
"""

from __future__ import annotations

import argparse
import time
import uuid
from typing import Optional

import bittensor as bt

from arctura_base.protocol import BaseSubnetSynapse
from arctura_base.base_rpc import BaseRPCClient
from arctura_base.utils import hash_output, build_merkle_proof, get_energy_tag
from arctura_base.incentive import REQUIRED_STEPS


class ArcturaMiner:
    """
    Arctura Base subnet miner.

    Registers with the Bittensor network, serves an axon endpoint,
    and responds to BaseSubnetSynapse mandates from validators.

    The miner's quality is determined entirely by:
        1. Correctness of Base chain data fetched
        2. Validity of Merkle proof constructed
        3. Accuracy of block_hash_anchor
        4. Completeness of execution_trace
        5. Calibration of confidence score
    """

    def __init__(self, config: Optional[bt.config] = None) -> None:
        self.config = config or self._build_config()

        # Initialize logging
        bt.logging(config=self.config, logging_dir=self.config.full_path)
        bt.logging.info("Initializing Arctura Base miner...")

        # Bittensor components
        self.wallet     = bt.wallet(config=self.config)
        self.subtensor  = bt.subtensor(config=self.config)
        self.metagraph  = self.subtensor.metagraph(self.config.netuid)

        # Base chain client
        self.base_client = BaseRPCClient()

        # Axon — the miner's network-facing endpoint
        self.axon = bt.axon(wallet=self.wallet, config=self.config)
        self.axon.attach(
            forward_fn=self.forward,
            blacklist_fn=self.blacklist,
            priority_fn=self.priority,
        )

        bt.logging.info(
            f"Arctura Base miner initialized\n"
            f"  wallet:   {self.wallet}\n"
            f"  network:  {self.config.subtensor.network}\n"
            f"  netuid:   {self.config.netuid}\n"
            f"  energy:   {get_energy_tag()}"
        )

    # ── Config ────────────────────────────────────────────────────────────

    @staticmethod
    def _build_config() -> bt.config:
        parser = argparse.ArgumentParser(
            description="Arctura Base subnet miner",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        )
        bt.subtensor.add_args(parser)
        bt.logging.add_args(parser)
        bt.wallet.add_args(parser)
        bt.axon.add_args(parser)

        parser.add_argument(
            "--netuid", type=int, default=1,
            help="Bittensor subnet UID to register on."
        )
        parser.add_argument(
            "--max_block_lookback", type=int, default=1000,
            help="Maximum blocks the miner will look back for historical queries."
        )

        config = bt.config(parser)
        config.full_path = (
            f"~/.bittensor/miners/{config.wallet.name}"
            f"/{config.wallet.hotkey}/netuid{config.netuid}/miner"
        )
        return config

    # ── Axon middleware ───────────────────────────────────────────────────

    def blacklist(self, synapse: BaseSubnetSynapse) -> tuple[bool, str]:
        """
        Reject synapse requests from unregistered or unknown hotkeys.

        Only registered validators (present in metagraph) are served.
        This prevents arbitrary external callers from querying the miner.
        """
        caller_hotkey = synapse.dendrite.hotkey

        if caller_hotkey not in self.metagraph.hotkeys:
            return True, f"Unregistered hotkey: {caller_hotkey[:16]}..."

        uid = self.metagraph.hotkeys.index(caller_hotkey)
        if self.metagraph.S[uid] == 0:
            return True, f"Zero-stake validator (uid={uid}) — ignored."

        return False, ""

    def priority(self, synapse: BaseSubnetSynapse) -> float:
        """
        Assign request priority proportional to validator stake.

        Higher-stake validators get their mandates processed first when the
        miner is under load. This aligns miner incentives with the weight
        of the validators scoring them.
        """
        try:
            uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
            return float(self.metagraph.S[uid])
        except ValueError:
            return 0.0

    # ── Core forward function ─────────────────────────────────────────────

    def forward(self, synapse: BaseSubnetSynapse) -> BaseSubnetSynapse:
        """
        Receive a mandate, execute it against Base chain, return attestation.

        This is the critical path. Every synapse that returns must have:
            base_state_hash   — SHA-256 of deterministic output
            merkle_proof      — cryptographic proof chain
            block_hash_anchor — live Base block hash at time of execution
            execution_trace   — metadata proving work was done
            confidence        — calibrated self-assessment (be honest)
            energy_tag        — P5 Stewardship declaration

        A synapse that returns with None for base_state_hash or merkle_proof
        scores 0.0 — no TAO for failed execution.
        """
        bt.logging.info(
            f"Mandate received | id={synapse.mandate_id[:8]}... "
            f"type={synapse.query_type}"
        )

        start_ts = time.time()
        steps_completed: list[str] = []

        try:
            # Step 1: Fetch Base chain data deterministically
            output = self.base_client.execute_mandate(
                query_type=synapse.query_type,
                contract_address=synapse.contract_address,
                block_range=synapse.base_block_range,
                payload=synapse.mandate_payload,
            )
            steps_completed.append("rpc_fetch")

            # Step 2: Hash the output deterministically
            state_hash = hash_output(output)
            synapse.base_state_hash = state_hash
            steps_completed.append("output_hash")

            # Step 3: Build Merkle proof
            synapse.merkle_proof = build_merkle_proof(state_hash)
            steps_completed.append("merkle_build")

            # Step 4: Anchor to live Base block hash
            # The block hash is embedded in the output by BaseRPCClient
            synapse.block_hash_anchor = output.get("_meta", {}).get("block_hash")
            steps_completed.append("block_anchor")

            # Step 5: Build execution trace
            duration_ms = int((time.time() - start_ts) * 1000)
            synapse.execution_trace = {
                "ts":           int(start_ts),
                "duration_ms":  duration_ms,
                "steps":        steps_completed,
                "rpc_calls":    1,
                "block_number": output.get("block_number") or output.get("to_block"),
                "mandate_id":   synapse.mandate_id,
            }

            # Step 6: Set confidence and energy tag
            synapse.confidence = self._estimate_confidence(
                synapse.query_type, steps_completed
            )
            synapse.energy_tag = get_energy_tag()

            bt.logging.success(
                f"Mandate attested | id={synapse.mandate_id[:8]}... "
                f"hash={state_hash[:12]}... "
                f"confidence={synapse.confidence:.2f} "
                f"duration={duration_ms}ms"
            )

        except Exception as exc:
            bt.logging.error(
                f"Mandate execution failed | id={synapse.mandate_id[:8]}... "
                f"error={exc}"
            )
            # Return synapse with nulled attestation fields — scores 0.0
            synapse.base_state_hash  = None
            synapse.merkle_proof     = None
            synapse.block_hash_anchor = None
            synapse.confidence       = 0.0

        return synapse

    def _estimate_confidence(self, query_type: str, steps: list[str]) -> float:
        """
        Estimate confidence in the attestation based on execution completeness.

        Be honest: validators track calibration accuracy over time.
        Overconfident miners are penalized as much as underconfident ones.
        """
        if not steps:
            return 0.0

        required = REQUIRED_STEPS
        completed = set(steps)
        completeness = len(completed & required) / len(required)

        # Simple calibration: confidence tracks completeness
        # In production, refine this based on historical performance data
        return round(completeness * 0.90, 2)  # 0.90 ceiling — leave room for uncertainty

    # ── Run loop ──────────────────────────────────────────────────────────

    def run(self) -> None:
        """Start the miner axon and enter the main loop."""
        self.axon.start()
        self.axon.serve(netuid=self.config.netuid, subtensor=self.subtensor)

        bt.logging.info(
            f"Arctura Base miner live\n"
            f"  axon:   {self.axon}\n"
            f"  netuid: {self.config.netuid}"
        )

        step = 0
        try:
            while True:
                # Sync metagraph every 5 steps (~60 seconds at 12s/block)
                if step % 5 == 0:
                    self.metagraph.sync(subtensor=self.subtensor)
                    bt.logging.debug(
                        f"Metagraph synced | block={self.metagraph.block.item()}"
                    )
                step += 1
                time.sleep(12)

        except KeyboardInterrupt:
            bt.logging.info("Miner shutdown requested — stopping axon.")
            self.axon.stop()


if __name__ == "__main__":
    ArcturaMiner().run()
