#!/usr/bin/env bash
# scripts/start_miner.sh
set -euo pipefail
NETWORK="${NETWORK:-test}"
NETUID="${NETUID:-1}"
WALLET="${WALLET:-miner}"
HOTKEY="${HOTKEY:-default}"
PORT="${MINER_AXON_PORT:-8091}"
while [[ $# -gt 0 ]]; do
  case $1 in
    --network) NETWORK="$2"; shift 2;;
    --netuid)  NETUID="$2";  shift 2;;
    --wallet)  WALLET="$2";  shift 2;;
    *) echo "Unknown: $1"; exit 1;;
  esac
done
echo "Starting Arctura Base miner | network=${NETWORK} netuid=${NETUID}"
python neurons/miner.py \
  --wallet.name "${WALLET}" \
  --wallet.hotkey "${HOTKEY}" \
  --subtensor.network "${NETWORK}" \
  --netuid "${NETUID}" \
  --axon.port "${PORT}" \
  --logging.info
