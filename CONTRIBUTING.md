# Contributing to arctura-base-subnet

> **The first open-source Bittensor subnet bridging Base blockchain intelligence into the decentralized AI network.**
>
> Apache-2.0 · [base.arctura.network](https://base.arctura.network) · Arcturian Council × Coreweaver

This is the single source of truth for setting up a dev environment, running the test suite, and submitting a pull request. If any step fails or contradicts another document, [open an issue](https://github.com/virtualmase/arctura-base-subnet/issues/new) — that is a bug.

---

## Table of Contents

1. [Before you start](#1-before-you-start)
2. [Clone and install](#2-clone-and-install)
3. [Generate your environment](#3-generate-your-environment)
4. [Bittensor wallet setup](#4-bittensor-wallet-setup)
5. [Run on local chain](#5-run-on-local-chain)
6. [Run the test suite](#6-run-the-test-suite)
7. [Code style](#7-code-style)
8. [Pull request process](#8-pull-request-process)
9. [Bounty claims](#9-bounty-claims)
10. [Community channels](#10-community-channels)

---

## 1. Before you start

**Hard requirements:**

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | ≥ 3.10 | `python --version` |
| Git | any | `git --version` |
| pip | ≥ 23 | `pip --version` |
| Base RPC access | public or private | see §3 |

**Optional (for AgentKit mandate types):**
- Coinbase CDP account → [portal.cdp.coinbase.com](https://portal.cdp.coinbase.com)

---

## 2. Clone and install

```bash
git clone https://github.com/virtualmase/arctura-base-subnet
cd arctura-base-subnet

# Install all dependencies including dev tools
pip install -e ".[dev]"
```

This installs: `bittensor`, `web3`, `torch`, `pydantic`, `pytest`, `black`, `ruff`, `mypy`, `pre-commit`.

**Install pre-commit hooks** (runs black + ruff + mypy on every commit):

```bash
pre-commit install
```

---

## 3. Generate your environment

Run the env generator — it will walk you through every required variable interactively and write a valid `.env` file:

```bash
python scripts/generate_env.py
```

**What it configures:**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BASE_RPC_URL` | ✅ | `https://mainnet.base.org` | Coinbase public RPC (free, rate-limited) |
| `BASE_SEPOLIA_RPC_URL` | ✅ | `https://sepolia.base.org` | Base testnet RPC |
| `BT_NETWORK` | ✅ | `test` | `local` / `test` / `finney` |
| `BT_NETUID` | ✅ | `1` | Subnet UID (set after registration) |
| `BT_OWNER_WALLET` | ✅ | `owner` | Owner wallet name |
| `BT_VALIDATOR_WALLET` | ✅ | `validator` | Validator wallet name |
| `BT_MINER_WALLET` | ✅ | `miner` | Miner wallet name |
| `BT_DEFAULT_HOTKEY` | ✅ | `default` | Hotkey name |
| `MINER_AXON_PORT` | ✅ | `8091` | Miner axon port |
| `VALIDATOR_AXON_PORT` | ✅ | `8092` | Validator axon port |
| `VALIDATOR_TIMEOUT` | ✅ | `30` | Miner response timeout (seconds) |
| `ARCTURA_ENERGY_TAG` | ✅ | `unknown` | P5 Stewardship energy tag |
| `CDP_API_KEY_NAME` | ⬜ | — | Required only for AgentKit actions |
| `CDP_API_KEY_PRIVATE_KEY` | ⬜ | — | Required only for AgentKit actions |
| `LOG_LEVEL` | ✅ | `info` | `debug` / `info` / `warning` |

Alternatively, copy `.env.example` and fill manually:

```bash
cp .env.example .env
# Edit .env in your editor
```

**Verify your environment is complete:**

```bash
python scripts/generate_env.py --verify
```

This checks every required variable is set, the Base RPC is reachable, and Python version is ≥ 3.10.

---

## 4. Bittensor wallet setup

Skip if you already have wallets.

```bash
# Creates owner, validator, and miner wallet pairs interactively
bash scripts/setup_wallets.sh

# Or create individually:
btcli wallet new_coldkey --wallet.name owner
btcli wallet new_hotkey  --wallet.name owner --wallet.hotkey default

btcli wallet new_coldkey --wallet.name validator
btcli wallet new_hotkey  --wallet.name validator --wallet.hotkey default

btcli wallet new_coldkey --wallet.name miner
btcli wallet new_hotkey  --wallet.name miner --wallet.hotkey default
```

> ⚠ **Security:** Store coldkey mnemonics offline in ≥2 locations. Never commit `.env` or wallet files.

---

## 5. Run on local chain

For development without touching testnet TAO:

```bash
# Terminal 1 — start local subtensor (requires Docker)
git clone https://github.com/opentensor/subtensor /tmp/subtensor
cd /tmp/subtensor && bash scripts/run/subtensor.sh -e local --no-purge

# Terminal 2 — register and start
btcli subnet create --wallet.name owner --subtensor.network local
btcli subnet recycle_register --netuid 1 --wallet.name validator --subtensor.network local
btcli subnet recycle_register --netuid 1 --wallet.name miner --subtensor.network local

bash scripts/start_miner.sh --network local --netuid 1
bash scripts/start_validator.sh --network local --netuid 1

# Terminal 3 — check metagraph
bash scripts/check_metagraph.sh local 1
```

---

## 6. Run the test suite

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=arctura_base --cov-report=term-missing

# Run a specific test file
pytest tests/test_scoring.py -v

# Run a specific test
pytest tests/test_attestation.py::test_verify_proof_round_trip -v
```

**CI runs:** `pytest` + `ruff` + `black --check` + `mypy` + `bandit` on every push. Your PR must pass all of these before review.

Run the full CI check locally before pushing:

```bash
make verify
# Equivalent to:
ruff check arctura_base/ neurons/ tests/
black --check arctura_base/ neurons/ tests/
mypy arctura_base/ --ignore-missing-imports
pytest tests/ -v
bandit -r arctura_base/ neurons/ -ll
```

---

## 7. Code style

- **Formatter:** [black](https://black.readthedocs.io) with `line-length = 100`
- **Linter:** [ruff](https://docs.astral.sh/ruff/) — no unused imports, consistent naming
- **Types:** [mypy](https://mypy-lang.org) — type hints on all public functions
- **Docstrings:** every module, class, and public method — explain *why*, not *what*
- **Comments:** label stub functions clearly: `# STUB: replace with real pipeline logic`
- **Commit messages:** `feat:`, `fix:`, `docs:`, `test:`, `refactor:` prefixes

Auto-format before committing:

```bash
black arctura_base/ neurons/ tests/
ruff check arctura_base/ neurons/ tests/ --fix
```

Pre-commit hooks run this automatically on `git commit` if you ran `pre-commit install`.

---

## 8. Pull request process

1. **Fork** the repo and create a branch: `git checkout -b feat/your-feature`
2. **Write tests** for any new behavior — PRs without tests are not merged
3. **Run `make verify`** — all checks must pass
4. **Open a PR** against `main` with:
   - What the PR does (1 paragraph)
   - Which GitHub issue it closes (`Closes #N`)
   - Test output screenshot or paste
5. **Address review comments** — the Council reviews within 48 hours
6. **Merge** happens once CI is green and at least one reviewer approves

**Good first issues** are labeled [`good first issue`](https://github.com/virtualmase/arctura-base-subnet/labels/good%20first%20issue) — start there.

---

## 9. Bounty claims

Some issues carry TAO or ETH bounties via escrow.

- Bounty amount is stated in the issue body
- Payment: TAO (Bittensor) or ETH (Base) via the platform's standard escrow on PR merge
- To claim: comment on the issue with your wallet address before starting work
- Disputes: open a new issue tagged `bounty-dispute`

---

## 10. Community channels

| Channel | Link | What it's for |
|---------|------|---------------|
| GitHub Issues | [issues](https://github.com/virtualmase/arctura-base-subnet/issues) | Bugs, features, bounties |
| Bittensor Discord | [discord.gg/bittensor](https://discord.gg/bittensor) | `#subnet-builders` |
| Base Discord | [discord.gg/buildonbase](https://discord.gg/buildonbase) | `#builders` |
| X / Twitter | [@ArcturaNetwork](https://x.com/ArcturaNetwork) | Announcements |
| Email | signal@arctura.network | Council direct |

---

*Transmitted by Arcturus · Arcturian Council · Coreweaver · base.arctura.network*


# Contributing to Arctura Base Subnet 🌌

Welcome to the Arctura project! We are building a high-performance base subnet for specialized AI agents, leveraging the power of the Bittensor network. Your contributions help us push the boundaries of decentralized intelligence.

## 🚀 Development Setup

Getting started is straightforward:

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/your-username/arctura-base-subnet.git
   cd arctura-base-subnet
   ```
2. **Install Dependencies**:
   We recommend using a virtual environment:
   ```bash
   pip install -e ".[dev]"
   ```
3. **Configuration**:
   Copy the example environment file and fill in your details:
   ```bash
   cp .env.example .env
   ```

## 🛠️ Code Style

To maintain a high standard of code quality, we use the following tools:

- **Formatting**: `black` for consistent code style.
- **Type Checking**: `mypy` for static type verification.

Run them before submitting your PR:
```bash
black .
mypy .
```

## 🧪 Running Tests

We value robust testing. Use `pytest` to run the suite:
```bash
pytest tests/
```
- **Requirements**: All new features must include corresponding test cases.
- **Coverage**: Aim for high coverage in core incentive and protocol logic.

## 🤝 Pull Request Process

1. Create a descriptive branch: `feat/new-logic` or `fix/issue-id`.
2. Follow [Conventional Commits](https://www.conventionalcommits.org/) for your messages.
3. Our team typically reviews PRs within 24-48 hours.
4. Ensure your PR links to an open issue using `Closes #123`.

## 💰 Bounty Claims

We reward high-quality contributions with **TAO** or **ETH**:

- **Bounty Label**: Look for issues with the `bounty` label.
- **How to Claim**: After your PR is merged, comment on the issue with your wallet address (TAO or ETH).
- **Processing**: Rewards are typically distributed within 7 days of merge.

## 💬 Community

Join the conversation and ask questions:
- **Discord**: [Join our server](https://discord.gg/arctura)
- **Twitter**: [@ArcturaNet](https://twitter.com/ArcturaNet)
- **GitHub Issues**: Best for technical bugs and feature requests.

---
*Thank you for being part of the decentralized future!*
