"""
arctura_base/base_rpc.py

Base chain client for the Arctura subnet miner.

Wraps Coinbase's public Base RPC and optionally the CDP SDK. All execution
is deterministic: given the same block range, contract address, and query
parameters, the output is identical across any miner. This property is
required for Merkle proof verification by validators.

RPC endpoints:
    Mainnet:  https://mainnet.base.org    (public, rate-limited)
    Sepolia:  https://sepolia.base.org    (testnet, free)
    Premium:  Alchemy / QuickNode / Coinbase Node (higher rate limits)

Arctura Council · Coreweaver · base.arctura.network
Apache-2.0
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Optional

import bittensor as bt
from web3 import Web3
from web3.types import BlockIdentifier


class BaseRPCClient:
    """
    Deterministic Base chain client.

    All public methods are designed to return the same output for the same
    inputs when queried at the same block — a prerequisite for Merkle proof
    reproducibility by validators.

    Usage:
        client = BaseRPCClient()
        balance = client.get_balance("0xAbc...", block_number=21_000_000)
        events  = client.get_events("0xAbc...", abi, "Transfer", 21_000_000, 21_000_100)
        state   = client.call_view("0xAbc...", abi, "totalSupply", [], 21_000_000)
    """

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        timeout: int = 10,
    ) -> None:
        """
        Initialize the Base RPC client.

        Args:
            rpc_url:  Base RPC endpoint. Defaults to BASE_RPC_URL env var,
                      then Coinbase's public endpoint.
            timeout:  HTTP request timeout in seconds.
        """
        url = rpc_url or os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
        self.w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": timeout}))
        self._verify_connection()

    def _verify_connection(self) -> None:
        """Verify the RPC connection is live. Raises on failure."""
        if not self.w3.is_connected():
            raise ConnectionError(
                f"Cannot connect to Base RPC. Check BASE_RPC_URL in .env\n"
                f"Current: {self.w3.provider.endpoint_uri}"
            )
        chain_id = self.w3.eth.chain_id
        # Base mainnet = 8453, Base Sepolia = 84532
        if chain_id not in (8453, 84532):
            bt.logging.warning(
                f"Connected to chain_id={chain_id}. "
                f"Expected Base mainnet (8453) or Sepolia (84532)."
            )

    # ── Core query methods ────────────────────────────────────────────────

    def get_latest_block_number(self) -> int:
        """Return the current latest block number on Base."""
        return self.w3.eth.block_number

    def get_block_hash(self, block_number: int) -> str:
        """
        Return the block hash for a given block number.

        This is the anchor used by validators to verify attestation freshness.
        A miner's block_hash_anchor must match what the validator independently
        fetches — fabricated attestations referencing non-existent blocks fail.
        """
        block = self.w3.eth.get_block(block_number)
        return block["hash"].hex()

    def get_balance(
        self,
        address: str,
        token_address: Optional[str] = None,
        block_number: Optional[int] = None,
    ) -> dict:
        """
        Fetch native ETH or ERC-20 token balance at a specific block.

        Args:
            address:       The address to query.
            token_address: If provided, fetch ERC-20 balance instead of ETH.
            block_number:  Block to query at. None = latest.

        Returns:
            {"address": str, "balance": int, "block_number": int, "token": str | None}
        """
        block_id: BlockIdentifier = block_number or "latest"
        checksum_addr = Web3.to_checksum_address(address)

        if token_address is None:
            # Native ETH balance
            balance = self.w3.eth.get_balance(checksum_addr, block_id)
            token = None
        else:
            # ERC-20 balance via balanceOf(address) view call
            erc20_abi = [
                {"name": "balanceOf", "type": "function",
                 "inputs": [{"name": "account", "type": "address"}],
                 "outputs": [{"name": "", "type": "uint256"}],
                 "stateMutability": "view"}
            ]
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address), abi=erc20_abi
            )
            balance = contract.functions.balanceOf(checksum_addr).call(
                block_identifier=block_id
            )
            token = token_address

        actual_block = (
            block_number if block_number else self.w3.eth.block_number
        )

        return {
            "address": checksum_addr,
            "balance": balance,
            "block_number": actual_block,
            "token": token,
        }

    def get_events(
        self,
        contract_address: str,
        abi: list,
        event_name: str,
        from_block: int,
        to_block: int,
        filter_args: Optional[dict] = None,
    ) -> dict:
        """
        Fetch contract event logs in a block range.

        Args:
            contract_address: Contract to query.
            abi:              Contract ABI (list of dicts).
            event_name:       Name of the event to fetch.
            from_block:       Start of block range (inclusive).
            to_block:         End of block range (inclusive).
            filter_args:      Optional indexed event argument filters.

        Returns:
            {"event": str, "from_block": int, "to_block": int, "logs": list, "count": int}
        """
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )
        event = getattr(contract.events, event_name)

        # Fetch and serialize (web3 objects aren't JSON-serializable directly)
        raw_logs = event.get_logs(fromBlock=from_block, toBlock=to_block)
        serialized = [
            {
                "blockNumber":      log["blockNumber"],
                "transactionHash":  log["transactionHash"].hex(),
                "logIndex":         log["logIndex"],
                "args":             {k: str(v) for k, v in log["args"].items()},
            }
            for log in raw_logs
        ]

        return {
            "event":      event_name,
            "from_block": from_block,
            "to_block":   to_block,
            "logs":       serialized,
            "count":      len(serialized),
        }

    def call_view(
        self,
        contract_address: str,
        abi: list,
        function_name: str,
        args: list,
        block_number: Optional[int] = None,
    ) -> dict:
        """
        Call a view/pure contract function at a specific block.

        Args:
            contract_address: Contract to query.
            abi:              Contract ABI.
            function_name:    The view function to call.
            args:             Positional arguments to the function.
            block_number:     Block to query at. None = latest.

        Returns:
            {"function": str, "args": list, "result": Any, "block_number": int}
        """
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )
        func = getattr(contract.functions, function_name)
        block_id: BlockIdentifier = block_number or "latest"
        result = func(*args).call(block_identifier=block_id)

        actual_block = block_number if block_number else self.w3.eth.block_number

        return {
            "function":    function_name,
            "args":        [str(a) for a in args],
            "result":      str(result),
            "block_number": actual_block,
        }

    # ── Mandate dispatch ──────────────────────────────────────────────────

    def execute_mandate(
        self,
        query_type: str,
        contract_address: Optional[str],
        block_range: tuple[int, int],
        payload: dict,
    ) -> dict:
        """
        Dispatch a mandate to the appropriate Base RPC method.

        This is the single entry point called by neurons/miner.py.
        Returns a serializable dict suitable for SHA-256 hashing.

        Args:
            query_type:       "balance" | "events" | "state" | "agent_action"
            contract_address: EVM contract address (or None for balance queries).
            block_range:      (from_block, to_block) — to_block=0 means single block.
            payload:          Query-type-specific parameters from mandate_payload.

        Raises:
            ValueError:     On unknown query_type or missing required payload fields.
            RuntimeError:   On Base RPC failure.
        """
        from_block, to_block = block_range
        effective_to = to_block or from_block or self.get_latest_block_number()

        start_ts = time.time()

        if query_type == "balance":
            result = self.get_balance(
                address=payload["address"],
                token_address=payload.get("token_address"),
                block_number=effective_to,
            )

        elif query_type == "events":
            if not contract_address:
                raise ValueError("contract_address required for events query")
            result = self.get_events(
                contract_address=contract_address,
                abi=payload["abi"],
                event_name=payload["event_name"],
                from_block=from_block,
                to_block=effective_to,
                filter_args=payload.get("filter_args"),
            )

        elif query_type == "state":
            if not contract_address:
                raise ValueError("contract_address required for state query")
            result = self.call_view(
                contract_address=contract_address,
                abi=payload["abi"],
                function_name=payload["function_name"],
                args=payload.get("args", []),
                block_number=effective_to,
            )

        elif query_type == "agent_action":
            # Delegate to AgentKit adapter — requires CDP credentials
            from arctura_base.agentkit import execute_agent_action
            result = execute_agent_action(
                action_type=payload["action_type"],
                action_args=payload.get("action_args", {}),
            )

        else:
            raise ValueError(
                f"Unknown query_type: '{query_type}'. "
                f"Expected one of: balance, events, state, agent_action"
            )

        duration_ms = int((time.time() - start_ts) * 1000)
        result["_meta"] = {
            "query_type":  query_type,
            "duration_ms": duration_ms,
            "block_hash":  self.get_block_hash(effective_to),
        }

        return result
