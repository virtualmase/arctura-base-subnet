"""
arctura_base/agentkit.py

AgentKit adapter for the Arctura Base subnet miner.

Enables miners to execute onchain Base actions as mandate types — not just
read state. This is the L3 Cognitive Mesh layer: miners can operate as
autonomous agents on Base, with their actions attested and scored by validators.

Requires the optional [agentkit] install:
    pip install -e ".[agentkit]"

And CDP credentials in .env:
    CDP_API_KEY_NAME=...
    CDP_API_KEY_PRIVATE_KEY=...

Supported action types (Phase 01):
    "transfer"   — Transfer ETH or ERC-20 tokens
    "deploy"     — Deploy a smart contract
    "call"       — Call a non-view contract function (state-changing)
    "mint_nft"   — Mint an NFT on Base

Phase 02 will add:
    "swap"       — Token swap via Uniswap on Base
    "stake"      — Stake ETH or tokens
    "bridge"     — Cross-chain bridge operations

Arctura Council · Coreweaver · base.arctura.network
Apache-2.0
"""

from __future__ import annotations

import os
from typing import Any, Optional


def _get_agentkit():
    """
    Lazily import and initialize AgentKit.
    Returns (AgentKit instance, wallet) or raises ImportError with helpful message.
    """
    try:
        from coinbase_agentkit import AgentKit, AgentKitConfig
        from cdp import Cdp
    except ImportError:
        raise ImportError(
            "AgentKit integration requires optional dependencies.\n"
            "Install with: pip install -e '[agentkit]'\n"
            "Then set CDP_API_KEY_NAME and CDP_API_KEY_PRIVATE_KEY in .env"
        ) from None

    api_key_name = os.environ.get("CDP_API_KEY_NAME")
    api_key_private_key = os.environ.get("CDP_API_KEY_PRIVATE_KEY")

    if not api_key_name or not api_key_private_key:
        raise EnvironmentError(
            "AgentKit requires CDP credentials in .env:\n"
            "  CDP_API_KEY_NAME=your-key-name\n"
            "  CDP_API_KEY_PRIVATE_KEY=your-private-key\n"
            "Get credentials at: https://portal.cdp.coinbase.com"
        )

    Cdp.configure(api_key_name, api_key_private_key)
    config = AgentKitConfig(network_id="base-mainnet")
    kit = AgentKit(config)
    return kit


def execute_agent_action(
    action_type: str,
    action_args: dict,
) -> dict:
    """
    Execute an onchain Base agent action via AgentKit.

    Called by BaseRPCClient.execute_mandate() when query_type == "agent_action".
    Returns a serializable dict describing the action and its outcome —
    this dict is hashed to produce the base_state_hash attestation.

    Args:
        action_type: The type of onchain action to perform.
        action_args: Action-specific arguments (see supported action types above).

    Returns:
        Serializable dict with action result, suitable for SHA-256 hashing.

    Raises:
        ImportError:    If AgentKit is not installed.
        EnvironmentError: If CDP credentials are missing.
        ValueError:     If action_type is unsupported.
        RuntimeError:   If the onchain action fails.
    """
    kit = _get_agentkit()

    if action_type == "transfer":
        result = _do_transfer(kit, action_args)
    elif action_type == "deploy":
        result = _do_deploy(kit, action_args)
    elif action_type == "call":
        result = _do_contract_call(kit, action_args)
    elif action_type == "mint_nft":
        result = _do_mint_nft(kit, action_args)
    else:
        raise ValueError(
            f"Unsupported agent_action type: '{action_type}'. "
            f"Supported: transfer, deploy, call, mint_nft"
        )

    result["action_type"] = action_type
    return result


def _do_transfer(kit: Any, args: dict) -> dict:
    """Transfer ETH or ERC-20 tokens on Base."""
    wallet = kit.wallet
    amount     = args["amount"]
    to_address = args["to_address"]
    token      = args.get("token_address")  # None = native ETH

    if token:
        tx = wallet.transfer(amount, token, to_address)
    else:
        tx = wallet.transfer(amount, "eth", to_address)

    tx.wait()
    return {
        "status":       "success",
        "tx_hash":      tx.transaction_hash,
        "amount":       str(amount),
        "to":           to_address,
        "token":        token,
    }


def _do_deploy(kit: Any, args: dict) -> dict:
    """Deploy a smart contract on Base."""
    wallet    = kit.wallet
    abi       = args["abi"]
    bytecode  = args["bytecode"]
    init_args = args.get("constructor_args", [])

    contract = wallet.deploy_contract(abi=abi, bytecode=bytecode, args=init_args)
    contract.wait()

    return {
        "status":           "success",
        "contract_address": contract.contract_address,
        "tx_hash":          contract.transaction.transaction_hash,
    }


def _do_contract_call(kit: Any, args: dict) -> dict:
    """Call a state-changing contract function on Base."""
    wallet          = kit.wallet
    contract_address = args["contract_address"]
    abi             = args["abi"]
    function_name   = args["function_name"]
    call_args       = args.get("args", [])
    value           = args.get("value", 0)  # ETH value to send

    tx = wallet.invoke_contract(
        contract_address=contract_address,
        method=function_name,
        abi=abi,
        args={str(i): a for i, a in enumerate(call_args)},
    )
    tx.wait()

    return {
        "status":            "success",
        "tx_hash":           tx.transaction.transaction_hash,
        "contract_address":  contract_address,
        "function":          function_name,
    }


def _do_mint_nft(kit: Any, args: dict) -> dict:
    """Mint an NFT on Base."""
    wallet           = kit.wallet
    contract_address = args["contract_address"]
    destination      = args.get("destination", wallet.default_address.address_id)

    nft = wallet.mint_nft(contract_address=contract_address, destination=destination)
    nft.wait()

    return {
        "status":           "success",
        "tx_hash":          nft.transaction.transaction_hash,
        "contract_address": contract_address,
        "destination":      destination,
    }
