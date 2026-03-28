# Healthcare MCP + A2A Platform

## Project Overview
Multi-Agent Patient Care Coordination Platform using MCP (Model Context Protocol) + A2A (Agent-to-Agent Protocol). See PLAN.md for full architecture.

## Quick Reference
- **Language**: Python 3.11+ with strict type hints
- **Package manager**: uv
- **Lint/format**: `make lint` / `make format` (ruff)
- **Type check**: `make typecheck` (mypy --strict)
- **Test**: `make test` (pytest, >80% coverage required)
- **Run locally**: `make run` (starts 4 services: 2 MCP servers + 2 agents)

## Architecture
- **2 MCP Servers** (Release 1): FHIR MCP (includes patient intake), Scheduling MCP
- **2 A2A Agents** (Release 1): Triage Agent, Care Coordinator Agent
- **1 Workflow**: Triage & Route Patient (intake -> triage -> schedule)
- **Orchestrator**: Library module (not a service), drives workflow sequencing

## Key Boundary Decisions (do not change without ADR update)
- BD-1: No notification in R1 (R2 feature)
- BD-2: Patient intake tools folded into FHIR MCP for R1
- BD-3: Saga/DynamoDB state is source of truth for task durability (not A2A SDK)
- BD-4: FHIR R4 wire format, fhir.resources R4B classes (backward-compatible)
- BD-5: OAuth2 Client Credentials Grant, per-agent Cognito client IDs, scope = {resource}:{action}

## Conventions
- All PHI access must go through consent verification + FHIR AuditEvent + OpenLineage event
- Every MCP tool has lineage middleware (auto-emits events)
- PHI never appears in logs, traces, exceptions, or metric labels
- Terminology codes (ICD-10, SNOMED, RxNorm, LOINC) validated via TerminologyService
- Write operations require idempotency keys
- ESI Level 1-2 triage always triggers human review queue

## Directory Layout
- `src/core/` - Shared infrastructure (security, consent, audit, lineage, terminology, workflow, human review)
- `src/models/` - Pydantic domain models (FHIR, clinical, scheduling)
- `src/mcp_servers/` - MCP server implementations
- `src/agents/` - A2A agent implementations
- `src/orchestrator/` - Workflow coordination (library module)
- `governance/` - Governance framework (AI, clinical, data, metadata, lifecycle, operational)
- `policies/` - Declarative YAML policy files
- `schemas/` - Event and contract JSON schemas
- `infra/` - AWS CDK stacks
- `eval/` - Agent evaluation harness
- `golden_tests/` - Deterministic end-to-end test scenarios
