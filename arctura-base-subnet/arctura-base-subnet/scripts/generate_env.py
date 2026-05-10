#!/usr/bin/env python3
"""
scripts/generate_env.py

Single source of truth for environment configuration.

Interactive generator that walks contributors through every required variable,
validates inputs, checks Base RPC connectivity, and writes a valid .env file.

Usage:
    python scripts/generate_env.py           # interactive setup
    python scripts/generate_env.py --verify  # verify existing .env
    python scripts/generate_env.py --check   # non-interactive check (CI-safe)

Arctura Council · Coreweaver · base.arctura.network
Apache-2.0
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Schema ────────────────────────────────────────────────────────────────

@dataclass
class EnvVar:
    key: str
    description: str
    default: Optional[str]
    required: bool
    secret: bool = False          # mask in output
    validate_fn: Optional[str] = None  # name of a validator method


ENV_SCHEMA: list[EnvVar] = [
    # Base Chain
    EnvVar("BASE_RPC_URL",         "Base mainnet RPC endpoint",                   "https://mainnet.base.org",  True),
    EnvVar("BASE_SEPOLIA_RPC_URL", "Base Sepolia testnet RPC endpoint",           "https://sepolia.base.org",  True),
    # Bittensor
    EnvVar("BT_NETWORK",           "Bittensor network (local/test/finney)",        "test",                      True,  validate_fn="validate_network"),
    EnvVar("BT_NETUID",            "Subnet UID (set after registration)",           "1",                         True),
    EnvVar("BT_OWNER_WALLET",      "Owner wallet name",                            "owner",                     True),
    EnvVar("BT_VALIDATOR_WALLET",  "Validator wallet name",                        "validator",                  True),
    EnvVar("BT_MINER_WALLET",      "Miner wallet name",                            "miner",                     True),
    EnvVar("BT_DEFAULT_HOTKEY",    "Default hotkey name",                          "default",                   True),
    # Neurons
    EnvVar("MINER_AXON_PORT",      "Miner axon port",                             "8091",                      True),
    EnvVar("VALIDATOR_AXON_PORT",  "Validator axon port",                         "8092",                      True),
    EnvVar("VALIDATOR_TIMEOUT",    "Miner response timeout (seconds)",             "30",                        True),
    # Stewardship
    EnvVar("ARCTURA_ENERGY_TAG",   "P5 energy tag (renewable_verified/renewable_claimed/unknown/high_carbon)", "unknown", True, validate_fn="validate_energy_tag"),
    # Optional AgentKit
    EnvVar("CDP_API_KEY_NAME",     "Coinbase CDP API key name (AgentKit only)",    None,                        False, secret=True),
    EnvVar("CDP_API_KEY_PRIVATE_KEY", "Coinbase CDP private key (AgentKit only)", None,                        False, secret=True),
    # Logging
    EnvVar("LOG_LEVEL",            "Log level (debug/info/warning)",               "info",                      True,  validate_fn="validate_log_level"),
]

VALID_NETWORKS   = {"local", "test", "finney"}
VALID_ENERGY_TAGS = {"renewable_verified", "renewable_claimed", "unknown", "high_carbon"}
VALID_LOG_LEVELS = {"debug", "info", "warning", "error"}


# ── Validators ────────────────────────────────────────────────────────────

def validate_network(value: str) -> Optional[str]:
    if value not in VALID_NETWORKS:
        return f"Must be one of: {', '.join(sorted(VALID_NETWORKS))}"
    return None


def validate_energy_tag(value: str) -> Optional[str]:
    if value not in VALID_ENERGY_TAGS:
        return f"Must be one of: {', '.join(sorted(VALID_ENERGY_TAGS))}"
    return None


def validate_log_level(value: str) -> Optional[str]:
    if value not in VALID_LOG_LEVELS:
        return f"Must be one of: {', '.join(sorted(VALID_LOG_LEVELS))}"
    return None


VALIDATORS = {
    "validate_network":    validate_network,
    "validate_energy_tag": validate_energy_tag,
    "validate_log_level":  validate_log_level,
}


# ── Colors ────────────────────────────────────────────────────────────────

class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BLUE   = "\033[94m"
    CYAN   = "\033[96m"
    DIM    = "\033[2m"


def ok(msg: str)   -> str: return f"{C.GREEN}✓{C.RESET} {msg}"
def err(msg: str)  -> str: return f"{C.RED}✗{C.RESET} {msg}"
def warn(msg: str) -> str: return f"{C.YELLOW}⚠{C.RESET} {msg}"
def info(msg: str) -> str: return f"{C.BLUE}·{C.RESET} {msg}"


# ── RPC connectivity check ────────────────────────────────────────────────

def check_rpc(url: str, timeout: int = 5) -> tuple[bool, str]:
    """Return (reachable, message)."""
    try:
        import urllib.request
        import json
        payload = json.dumps({"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1})
        req = urllib.request.Request(
            url,
            data=payload.encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            if "result" in data:
                block = int(data["result"], 16)
                return True, f"block #{block:,}"
            return False, f"unexpected response: {data}"
    except Exception as e:
        return False, str(e)


# ── Python version check ──────────────────────────────────────────────────

def check_python() -> tuple[bool, str]:
    v = sys.version_info
    if v >= (3, 10):
        return True, f"{v.major}.{v.minor}.{v.micro}"
    return False, f"{v.major}.{v.minor}.{v.micro} — need ≥ 3.10"


# ── .env parsing ──────────────────────────────────────────────────────────

def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            values[k.strip()] = v.strip()
    return values


def write_env(path: Path, values: dict[str, str]) -> None:
    lines = [
        "# arctura-base-subnet environment configuration",
        "# Generated by scripts/generate_env.py — do not commit to version control",
        "",
        "# ── Base Chain ─────────────────────────────────",
    ]
    base_keys = ["BASE_RPC_URL", "BASE_SEPOLIA_RPC_URL"]
    bt_keys   = ["BT_NETWORK", "BT_NETUID", "BT_OWNER_WALLET", "BT_VALIDATOR_WALLET",
                 "BT_MINER_WALLET", "BT_DEFAULT_HOTKEY"]
    neuron_keys = ["MINER_AXON_PORT", "VALIDATOR_AXON_PORT", "VALIDATOR_TIMEOUT"]
    other_keys  = ["ARCTURA_ENERGY_TAG", "CDP_API_KEY_NAME", "CDP_API_KEY_PRIVATE_KEY", "LOG_LEVEL"]

    def emit(keys: list[str], header: Optional[str] = None):
        if header:
            lines.append(f"\n# ── {header} {'─' * max(0, 45 - len(header))}")
        for k in keys:
            if k in values:
                lines.append(f"{k}={values[k]}")

    emit(base_keys)
    emit(bt_keys, "Bittensor")
    emit(neuron_keys, "Neurons")
    emit(other_keys, "Stewardship & Optional")

    path.write_text("\n".join(lines) + "\n")


# ── Verify mode ───────────────────────────────────────────────────────────

def cmd_verify(env_path: Path) -> int:
    print(f"\n{C.BOLD}arctura-base-subnet · Environment Verification{C.RESET}")
    print(f"{C.DIM}{'─' * 52}{C.RESET}\n")

    exit_code = 0

    # Python version
    ok_py, py_msg = check_python()
    print(ok(f"Python {py_msg}") if ok_py else err(f"Python {py_msg}"))
    if not ok_py:
        exit_code = 1

    # .env exists
    if not env_path.exists():
        print(err(f".env not found at {env_path}"))
        print(info("Run: python scripts/generate_env.py"))
        return 1

    values = load_env(env_path)

    # Check each required variable
    missing = []
    invalid = []
    for var in ENV_SCHEMA:
        if not var.required:
            continue
        val = values.get(var.key, "")
        if not val:
            missing.append(var.key)
            continue
        if var.validate_fn:
            fn = VALIDATORS.get(var.validate_fn)
            if fn:
                msg = fn(val)
                if msg:
                    invalid.append((var.key, msg))

    if missing:
        for k in missing:
            print(err(f"{k} — missing"))
        exit_code = 1
    if invalid:
        for k, msg in invalid:
            print(err(f"{k} — {msg}"))
        exit_code = 1

    if not missing and not invalid:
        print(ok("All required variables present and valid"))

    # RPC connectivity
    rpc_url = values.get("BASE_RPC_URL", "")
    if rpc_url:
        reachable, rpc_msg = check_rpc(rpc_url)
        if reachable:
            print(ok(f"Base RPC reachable ({rpc_msg}) — {rpc_url}"))
        else:
            print(warn(f"Base RPC unreachable: {rpc_msg} — {rpc_url}"))
            # Warn but don't fail — could be a CI environment

    print()
    if exit_code == 0:
        print(f"{C.GREEN}{C.BOLD}✓ Environment verified. Ready to contribute.{C.RESET}\n")
    else:
        print(f"{C.RED}{C.BOLD}✗ Fix the issues above, then re-run --verify{C.RESET}\n")

    return exit_code


# ── Interactive setup ─────────────────────────────────────────────────────

def cmd_generate(env_path: Path) -> int:
    print(f"\n{C.BOLD}arctura-base-subnet · Environment Setup{C.RESET}")
    print(f"{C.DIM}Press Enter to accept the default. Ctrl+C to abort.{C.RESET}\n")

    existing = load_env(env_path)
    values: dict[str, str] = {}

    for var in ENV_SCHEMA:
        current = existing.get(var.key, var.default or "")
        prompt_default = f"[{current}]" if current else "[none]"

        if var.secret and current:
            prompt_default = "[set]"

        while True:
            try:
                raw = input(
                    f"{C.CYAN}{var.key}{C.RESET} {C.DIM}({var.description}){C.RESET}\n"
                    f"  {prompt_default}: "
                ).strip()
            except KeyboardInterrupt:
                print("\nAborted.")
                return 1

            value = raw if raw else current

            if var.required and not value:
                print(f"  {C.RED}Required — cannot be empty{C.RESET}")
                continue

            if value and var.validate_fn:
                fn = VALIDATORS.get(var.validate_fn)
                if fn:
                    msg = fn(value)
                    if msg:
                        print(f"  {C.RED}Invalid: {msg}{C.RESET}")
                        continue

            if value:
                values[var.key] = value
            print()
            break

    # Write
    write_env(env_path, values)
    print(ok(f".env written to {env_path}"))

    # Verify immediately
    print()
    return cmd_verify(env_path)


# ── CI check (non-interactive) ────────────────────────────────────────────

def cmd_check(env_path: Path) -> int:
    """Non-interactive verify for CI. Reads from actual environment variables."""
    print("arctura-base-subnet · CI env check")
    exit_code = 0
    for var in ENV_SCHEMA:
        if not var.required:
            continue
        val = os.environ.get(var.key, "")
        if not val:
            print(f"MISSING: {var.key}")
            exit_code = 1
    if exit_code == 0:
        print("All required env vars present.")
    return exit_code


# ── Entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Arctura Base subnet environment generator and verifier",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Verify an existing .env without prompting",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Non-interactive CI check against real environment variables",
    )
    parser.add_argument(
        "--env", type=Path, default=Path(".env"),
        help="Path to the .env file (default: .env)",
    )
    args = parser.parse_args()

    if args.check:
        sys.exit(cmd_check(args.env))
    elif args.verify:
        sys.exit(cmd_verify(args.env))
    else:
        sys.exit(cmd_generate(args.env))


if __name__ == "__main__":
    main()
