#!/usr/bin/env bash
# scripts/start_validator.sh
set -euo pipefail
NETWORK="${NETWORK:-test}"
NETUID="${NETUID:-1}"
WALLET="${WALLET:-validator}"
HOTKEY="${HOTKEY:-default}"
TIMEOUT="${VALIDATOR_TIMEOUT:-30}"
while [[ $# -gt 0 ]]; do
  case $1 in
    --network) NETWORK="$2"; shift 2;;
    --netuid)  NETUID="$2";  shift 2;;
    --wallet)  WALLET="$2";  shift 2;;
    *) echo "Unknown: $1"; exit 1;;
  esac
done
echo "Starting Arctura Base validator | network=${NETWORK} netuid=${NETUID}"
python neurons/validator.py \
  --wallet.name "${WALLET}" \
  --wallet.hotkey "${HOTKEY}" \
  --subtensor.network "${NETWORK}" \
  --netuid "${NETUID}" \
  --timeout "${TIMEOUT}" \
  --logging.info
