# Subnet Launch Guide

Complete walkthrough: wallet setup → local chain → testnet → Finney mainnet.

## Phase 0 — Wallets & Capital

```bash
# Check live burn cost FIRST — it changes daily
btcli subnet burn_cost --subtensor.network finney

# Create wallets
bash scripts/setup_wallets.sh finney
```

Minimum TAO: **burn cost + 20% buffer + validator/miner recycle fees**.  
Keep ≥100 TAO liquid. Check [taostats.io/subnets](https://taostats.io/subnets) for live cost.

## Phase 1 — Local Chain

```bash
# Start local subtensor (requires Docker)
git clone https://github.com/opentensor/subtensor && cd subtensor
bash scripts/run/subtensor.sh -e local --no-purge

# Register locally
btcli subnet create --wallet.name owner --subtensor.network local
btcli subnet recycle_register --netuid 1 --wallet.name validator --subtensor.network local
btcli subnet recycle_register --netuid 1 --wallet.name miner    --subtensor.network local

# Run both neurons (separate terminals)
bash scripts/start_miner.sh    --network local --netuid 1
bash scripts/start_validator.sh --network local --netuid 1
```

## Phase 2 — Testnet

```bash
# Free testnet TAO from Bittensor Discord #testnet-faucet
btcli subnet create --wallet.name owner --subtensor.network test
# Note your netuid from output

bash scripts/start_miner.sh    --network test --netuid N
bash scripts/start_validator.sh --network test --netuid N
bash scripts/check_metagraph.sh test N
```

Run for **48+ hours** before proceeding. Confirm non-zero weights in metagraph.

## Phase 3 — Mainnet Registration

See [GO_NO_GO_CHECKLIST.md](GO_NO_GO_CHECKLIST.md) before running any of these.

```bash
# Final burn cost check (run this within 30 minutes of registering)
btcli subnet burn_cost --subtensor.network finney

# Register — this burns TAO
btcli subnet create --wallet.name owner --subtensor.network finney
# RECORD YOUR NETUID

# Register neurons
btcli subnet recycle_register --netuid N --wallet.name validator --subtensor.network finney
btcli subnet recycle_register --netuid N --wallet.name miner    --subtensor.network finney

# Verify
btcli subnet metagraph --netuid N --subtensor.network finney

# Start immediately
bash scripts/start_miner.sh    --network finney --netuid N
bash scripts/start_validator.sh --network finney --netuid N
```

Emissions activate 7 days post-registration. Immunity period: 4 months.
