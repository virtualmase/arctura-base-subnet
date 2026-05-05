#!/usr/bin/env bash
# scripts/check_metagraph.sh
NETWORK="${1:-test}"
NETUID="${2:-1}"
echo "Arctura Base subnet | network=${NETWORK} netuid=${NETUID}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
btcli subnet burn_cost --subtensor.network "${NETWORK}"
echo ""
btcli subnet metagraph --netuid "${NETUID}" --subtensor.network "${NETWORK}"
