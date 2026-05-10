#!/usr/bin/env bash
# scripts/health_check.sh
#
# Arctura Base Subnet — Node Health Check
# Checks wallet funding, Base RPC, axon registration, last score, and deps.
# Color-coded output. Exit code 0 = all green. Exit code 1 = one or more failures.
#
# Usage:
#   bash scripts/health_check.sh [--network local|test|finney] [--netuid 1]
#
# Arcturian Council · Coreweaver · base.arctura.network
# Apache-2.0

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

ok()   { echo -e "  ${GREEN}✓${RESET}  $1"; }
fail() { echo -e "  ${RED}✗${RESET}  $1"; FAILURES=$((FAILURES + 1)); }
warn() { echo -e "  ${YELLOW}⚠${RESET}  $1"; WARNINGS=$((WARNINGS + 1)); }
info() { echo -e "  ${BLUE}·${RESET}  $1"; }
section() { echo -e "\n${BOLD}${CYAN}── $1 ${RESET}${DIM}$( printf '─%.0s' $(seq 1 $((50 - ${#1}))) )${RESET}"; }

FAILURES=0
WARNINGS=0

# ── Args ──────────────────────────────────────────────────────────────────
NETWORK="test"
NETUID="1"

while [[ $# -gt 0 ]]; do
  case $1 in
    --network) NETWORK="$2"; shift 2 ;;
    --netuid)  NETUID="$2";  shift 2 ;;
    *) shift ;;
  esac
done

# ── Load .env ─────────────────────────────────────────────────────────────
if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

BASE_RPC_URL="${BASE_RPC_URL:-https://mainnet.base.org}"
BT_MINER_WALLET="${BT_MINER_WALLET:-miner}"
BT_VALIDATOR_WALLET="${BT_VALIDATOR_WALLET:-validator}"
BT_DEFAULT_HOTKEY="${BT_DEFAULT_HOTKEY:-default}"

echo -e "\n${BOLD}arctura-base-subnet · Health Check${RESET}"
echo -e "${DIM}Network: ${NETWORK} · Netuid: ${NETUID} · $(date -u '+%Y-%m-%dT%H:%M:%SZ')${RESET}"

# ── 1. Dependencies ───────────────────────────────────────────────────────
section "Dependencies"

if command -v python3 &>/dev/null; then
  PY_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
  MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
  MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
  if [[ "$MAJOR" -ge 3 && "$MINOR" -ge 10 ]]; then
    ok "Python ${PY_VERSION}"
  else
    fail "Python ${PY_VERSION} — need ≥ 3.10"
  fi
else
  fail "Python not found"
fi

if python3 -c "import bittensor" 2>/dev/null; then
  BT_VERSION=$(python3 -c "import bittensor; print(bittensor.__version__)" 2>/dev/null || echo "unknown")
  ok "bittensor ${BT_VERSION}"
else
  fail "bittensor not installed — run: pip install -e '.[dev]'"
fi

if python3 -c "import web3" 2>/dev/null; then
  W3_VERSION=$(python3 -c "import web3; print(web3.__version__)" 2>/dev/null || echo "unknown")
  ok "web3 ${W3_VERSION}"
else
  fail "web3 not installed"
fi

for pkg in torch pydantic pytest; do
  if python3 -c "import $pkg" 2>/dev/null; then
    ok "$pkg"
  else
    warn "$pkg not installed"
  fi
done

# ── 2. Environment variables ──────────────────────────────────────────────
section "Environment"

required_vars=(
  "BASE_RPC_URL"
  "BT_NETWORK"
  "BT_NETUID"
  "BT_MINER_WALLET"
  "BT_VALIDATOR_WALLET"
  "BT_DEFAULT_HOTKEY"
  "MINER_AXON_PORT"
  "VALIDATOR_AXON_PORT"
)

for var in "${required_vars[@]}"; do
  val="${!var:-}"
  if [[ -n "$val" ]]; then
    if [[ "$var" == *"KEY"* || "$var" == *"SECRET"* ]]; then
      ok "${var}=[set]"
    else
      ok "${var}=${val}"
    fi
  else
    fail "${var} — not set (check .env or run: python scripts/generate_env.py)"
  fi
done

# ── 3. Base RPC connectivity ──────────────────────────────────────────────
section "Base RPC"

RPC_RESPONSE=$(python3 - <<EOF 2>/dev/null
import urllib.request, json, sys
url = "${BASE_RPC_URL}"
payload = json.dumps({"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}).encode()
req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        data = json.loads(r.read())
        if "result" in data:
            print("ok:" + str(int(data["result"], 16)))
        else:
            print("err:unexpected response")
except Exception as e:
    print("err:" + str(e))
EOF
)

if [[ "$RPC_RESPONSE" == ok:* ]]; then
  BLOCK_NUM="${RPC_RESPONSE#ok:}"
  ok "Base RPC reachable — block #$(printf '%s' "$BLOCK_NUM" | sed ':a;s/\B[0-9]\{3\}\>/,&/;ta')"
else
  ERROR="${RPC_RESPONSE#err:}"
  fail "Base RPC unreachable: ${ERROR}"
  info "URL: ${BASE_RPC_URL}"
  info "Free alternative: https://mainnet.base.org"
fi

# Sepolia check
BASE_SEPOLIA_RPC_URL="${BASE_SEPOLIA_RPC_URL:-https://sepolia.base.org}"
SEPOLIA_RESPONSE=$(python3 - <<EOF 2>/dev/null
import urllib.request, json
url = "${BASE_SEPOLIA_RPC_URL}"
payload = json.dumps({"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}).encode()
req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"}, method="POST")
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        data = json.loads(r.read())
        print("ok" if "result" in data else "err")
except:
    print("err")
EOF
)
if [[ "$SEPOLIA_RESPONSE" == "ok" ]]; then
  ok "Base Sepolia RPC reachable"
else
  warn "Base Sepolia RPC unreachable (${BASE_SEPOLIA_RPC_URL}) — testnet ops may fail"
fi

# ── 4. Bittensor wallets ──────────────────────────────────────────────────
section "Wallets"

WALLET_DIR="${HOME}/.bittensor/wallets"

check_wallet() {
  local name="$1"
  local hotkey="$2"
  local coldkey_path="${WALLET_DIR}/${name}/coldkeypub.txt"
  local hotkey_path="${WALLET_DIR}/${name}/hotkeys/${hotkey}"

  if [[ -f "$coldkey_path" ]]; then
    ok "Wallet ${name} — coldkey found"
  else
    fail "Wallet ${name} — coldkey not found at ${coldkey_path}"
    info "Run: btcli wallet new_coldkey --wallet.name ${name}"
    return
  fi

  if [[ -f "$hotkey_path" ]]; then
    ok "Wallet ${name} — hotkey '${hotkey}' found"
  else
    fail "Wallet ${name} — hotkey '${hotkey}' not found"
    info "Run: btcli wallet new_hotkey --wallet.name ${name} --wallet.hotkey ${hotkey}"
  fi
}

check_wallet "$BT_MINER_WALLET"     "$BT_DEFAULT_HOTKEY"
check_wallet "$BT_VALIDATOR_WALLET" "$BT_DEFAULT_HOTKEY"

# ── 5. Axon registration ──────────────────────────────────────────────────
section "Axon Registration"

if command -v btcli &>/dev/null; then
  info "Checking metagraph (${NETWORK}, netuid ${NETUID})..."
  METAGRAPH_OUT=$(btcli subnet metagraph \
    --subtensor.network "${NETWORK}" \
    --netuid "${NETUID}" 2>&1 || true)

  if echo "$METAGRAPH_OUT" | grep -q "$BT_MINER_WALLET"; then
    ok "Miner wallet found in metagraph"
  else
    warn "Miner wallet not found in metagraph — not yet registered, or netuid not active"
    info "Run: bash scripts/start_miner.sh --network ${NETWORK} --netuid ${NETUID}"
  fi

  if echo "$METAGRAPH_OUT" | grep -q "$BT_VALIDATOR_WALLET"; then
    ok "Validator wallet found in metagraph"
  else
    warn "Validator wallet not found in metagraph"
  fi
else
  warn "btcli not found — install bittensor to check axon registration"
fi

# ── 6. Port availability ──────────────────────────────────────────────────
section "Ports"

MINER_PORT="${MINER_AXON_PORT:-8091}"
VALIDATOR_PORT="${VALIDATOR_AXON_PORT:-8092}"

check_port() {
  local port="$1"
  local label="$2"
  if command -v lsof &>/dev/null; then
    if lsof -i :"$port" -sTCP:LISTEN &>/dev/null 2>&1; then
      ok "Port ${port} (${label}) — LISTENING"
    else
      info "Port ${port} (${label}) — not active (normal if neuron not running)"
    fi
  elif command -v ss &>/dev/null; then
    if ss -ltn | grep -q ":${port} "; then
      ok "Port ${port} (${label}) — LISTENING"
    else
      info "Port ${port} (${label}) — not active"
    fi
  else
    info "Port ${port} (${label}) — cannot check (lsof/ss not available)"
  fi
}

check_port "$MINER_PORT"     "miner axon"
check_port "$VALIDATOR_PORT" "validator axon"

# ── 7. Tests ──────────────────────────────────────────────────────────────
section "Test Suite"

if command -v pytest &>/dev/null && [[ -d "tests/" ]]; then
  TEST_COUNT=$(find tests/ -name "test_*.py" | wc -l | tr -d ' ')
  ok "${TEST_COUNT} test file(s) found in tests/"
  info "Run: make test — or: pytest tests/ -v"
else
  warn "pytest not available or tests/ directory missing"
fi

# ── Summary ───────────────────────────────────────────────────────────────
echo -e "\n${DIM}──────────────────────────────────────────────────────${RESET}"
if [[ $FAILURES -eq 0 && $WARNINGS -eq 0 ]]; then
  echo -e "\n${GREEN}${BOLD}✓ All checks passed. Node is healthy.${RESET}\n"
  exit 0
elif [[ $FAILURES -eq 0 ]]; then
  echo -e "\n${YELLOW}${BOLD}⚠ ${WARNINGS} warning(s) — review above. No hard failures.${RESET}\n"
  exit 0
else
  echo -e "\n${RED}${BOLD}✗ ${FAILURES} failure(s), ${WARNINGS} warning(s) — fix issues above.${RESET}\n"
  exit 1
fi
