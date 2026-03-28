# Healthcare MCP + A2A Platform

Multi-Agent Patient Care Coordination Platform using MCP (Model Context Protocol) and A2A (Agent-to-Agent Protocol).

See [PLAN.md](PLAN.md) for the full architecture and implementation plan.

## Quick Start

```bash
# Install dependencies
uv sync --all-extras

# Run linting and type checks
make lint && make typecheck

# Run tests
make test

# Seed synthetic data and run locally
make seed && make run
```
