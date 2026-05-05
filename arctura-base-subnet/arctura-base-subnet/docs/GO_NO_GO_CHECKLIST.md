# Mainnet Go / No-Go Checklist

Every item must be checked before running `btcli subnet create` on Finney.

## Capital
- [ ] Burn cost checked within last 30 minutes
- [ ] Owner coldkey balance ≥ burn cost + 20% buffer
- [ ] Validator hotkey funded for recycle_register
- [ ] Miner hotkey funded for recycle_register
- [ ] 30-day server cost budgeted

## Code
- [ ] `arctura_base/protocol.py` — BaseSubnetSynapse tested locally
- [ ] `neurons/miner.py` — returns valid `base_state_hash` on every synapse
- [ ] `neurons/miner.py` — returns valid `merkle_proof` (verify_merkle_proof passes)
- [ ] `neurons/miner.py` — `block_hash_anchor` matches real Base block hash
- [ ] `neurons/validator.py` — sets non-zero weights within every tempo period
- [ ] `pytest tests/ -v` passes with no failures
- [ ] No uncaught exceptions in 48h testnet run

## Network
- [ ] Miner axon port open and reachable externally (default 8091)
- [ ] Validator axon port open and reachable externally (default 8092)
- [ ] At least 1 external validator confirmed for post-launch
- [ ] Bittensor Discord announcement drafted (#subnet-owners)

## Operations
- [ ] Owner coldkey mnemonic stored offline in ≥2 separate locations
- [ ] Validator coldkey mnemonic stored offline
- [ ] Miner coldkey mnemonic stored offline
- [ ] Auto-restart configured (systemd or PM2) for both neurons
- [ ] Monitoring configured for axon uptime

## Final
- [ ] Go/no-go reviewed by at least one other person
- [ ] Command ready to paste (do not type fresh under pressure):
  ```bash
  btcli subnet create --wallet.name owner --subtensor.network finney
  ```
