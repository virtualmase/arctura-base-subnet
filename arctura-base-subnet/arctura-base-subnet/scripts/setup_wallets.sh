#!/usr/bin/env bash
# scripts/setup_wallets.sh
# Create the three Bittensor wallet pairs for Arctura Base subnet.
# Run once before registering. Store coldkey mnemonics OFFLINE.
set -euo pipefail

NETWORK="${1:-finney}"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Arctura Base Subnet — Wallet Setup              ║"
echo "║  Network: ${NETWORK}                             ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

echo "⚠  SECURITY: Store every mnemonic phrase offline."
echo "   Never store mnemonics in cloud, email, or password managers."
echo "   Coldkeys never touch an internet-connected machine after creation."
echo ""

read -rp "Press Enter to create the OWNER wallet..." 
btcli wallet new_coldkey --wallet.name owner
btcli wallet new_hotkey  --wallet.name owner --wallet.hotkey default

echo ""
read -rp "Press Enter to create the VALIDATOR wallet..."
btcli wallet new_coldkey --wallet.name validator
btcli wallet new_hotkey  --wallet.name validator --wallet.hotkey default

echo ""
read -rp "Press Enter to create the MINER wallet..."
btcli wallet new_coldkey --wallet.name miner
btcli wallet new_hotkey  --wallet.name miner --wallet.hotkey default

echo ""
echo "✓ All wallets created."
echo ""
echo "Next: Fund the owner coldkey with TAO, then run:"
echo "  btcli subnet burn_cost --subtensor.network ${NETWORK}"
echo "  btcli subnet create --wallet.name owner --subtensor.network ${NETWORK}"
