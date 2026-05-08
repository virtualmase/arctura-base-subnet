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
