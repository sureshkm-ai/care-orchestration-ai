# Healthcare MCP + A2A: Multi-Agent Patient Care Coordination Platform

## Context

The project idea (captured in `idea.png`) shows an **MCP + A2A** architecture where multiple AI agents (MCP Hosts) communicate via A2A Protocol while each accessing their own data sources through MCP Servers. This is a greenfield project.

**Use Case: Patient Care Coordination** -- triage, scheduling, pharmacy, clinical data agents coordinating patient care with FHIR-compliant data, safety guardrails, and human oversight.

**Execution Strategy: 3 releases.** Full architecture designed upfront, but implementation is narrow vertical slices -- depth over breadth.

---

## Release Strategy

### Release 1: Vertical Slice (MVP)
- **2 agents**: Triage + Care Coordinator
- **2 MCP servers**: FHIR (includes patient intake tools) + Scheduling
- **1 workflow**: Triage & Route Patient (intake → triage → schedule appointment; no notification step)
- **1 human escalation path**: ESI Level 1-2 → clinician review queue
- **1 lineage trace**: end-to-end OpenLineage for the workflow
- **1 compliance dashboard slice**: audit trail + governance card validation
- **5 golden tests**: deterministic end-to-end scenarios
- **AWS infra**: full CDK stacks (network, security, data, compute, API, observability, governance, lineage)
- **All cross-cutting concerns**: PHI redaction, consent, audit, idempotency, saga, terminology validation

### Release 2: Medication Safety
- Pharmacy Agent + Clinical Data Agent
- Pharmacy MCP + Notification MCP + Patient Intake MCP (extracted from FHIR MCP)
- Prescribe with Safety Check workflow
- Drug interaction safety guardrails
- Richer metadata catalog + operational dashboards
- Evaluation harness expansion

### Release 3: Hardening & Interoperability
- Comprehensive Patient Review workflow
- External integration connectors (async inbound, webhooks)
- Advanced evaluation + prompt lifecycle governance
- Cost optimization, resilience hardening, DR drills
- Multi-region DR posture

---

## Full Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    AWS Cloud (multi-account)                               │
│                                                                            │
│  ┌─── dev account ───┐  ┌─── test account ──┐  ┌─── prod account ───┐   │
│  │ (own KMS, audit,  │  │ (own KMS, audit,  │  │ (own KMS, audit,   │   │
│  │  data plane)      │  │  data plane)      │  │  data plane)       │   │
│  └───────────────────┘  └───────────────────┘  └────────────────────┘   │
│                                                                            │
│  Per account:                                                              │
│  ┌──── Governance ──── Control Tower ─ SCPs ─ Config ─ Security Hub ──┐  │
│  │  GuardDuty ─ Macie ─ CloudTrail ─ AWS Backup                       │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌── API Layer ──────┐   ┌── Agent Layer (ECS Fargate) ──────────────┐  │
│  │ API Gateway + WAF  │──▶│ Triage Agent    Care Coordinator Agent    │  │
│  │ + Cognito Auth     │   │ (+ human queue) (+ saga coordinator)     │  │
│  │ + rate limiting    │   │                                           │  │
│  └────────────────────┘   │ [R2] Pharmacy Agent   Clinical Data Agent│  │
│                            │ Orchestrator (module, not a service)     │  │
│  ┌── Human Review ───┐   └──────────┬────────────────────────────────┘  │
│  │ Clinician Worklist │              │ MCP Protocol                      │
│  │ Approval Queue     │   ┌──────────┴────────────────────────────────┐  │
│  │ Override Capture   │   │ MCP Layer (Lambda)                         │  │
│  │ Resume-After-      │   │ FHIR MCP    Scheduling MCP                 │  │
│  │   Approval         │   │ [R2] Pharmacy MCP  [R2] Notification MCP   │  │
│  └────────────────────┘   └──────────┬────────────────────────────────┘  │
│                                       │                                    │
│  ┌── Data Layer ─────────────────────┴────────────────────────────────┐  │
│  │ HealthLake (FHIR R4)  DynamoDB (ops data)  DynamoDB (lineage idx) │  │
│  │ DynamoDB (human queue) DynamoDB (saga state)  S3 (lineage detail) │  │
│  │ DynamoDB (metadata catalog)   S3 (audit archive)                   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌── Terminology Service ────────────────────────────────────────────┐   │
│  │ Code normalization ─ Value set validation ─ Version management     │   │
│  │ ICD-10, SNOMED CT, RxNorm, LOINC ─ Inactive code handling         │   │
│  └───────────────────────────────────────────────────────────────────┘   │
│                                                                            │
│  ┌── Security Layer ────────────────────────────────────────────────┐    │
│  │ Cognito (per-agent identity) ─ KMS (per-env CMK) ─ Secrets Mgr  │    │
│  │ VPC (private subnets) ─ VPC Endpoints ─ Egress restrictions      │    │
│  │ PHI Redaction middleware ─ Log scrubbing ─ Trace sanitization     │    │
│  │ SBOM ─ Signed images ─ Dependency allowlist ─ Admission policy   │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│                                                                            │
│  ┌── Observability (PHI-safe) ──────────────────────────────────────┐   │
│  │ CloudWatch (redacted logs) ─ X-Ray (sanitized traces)            │   │
│  │ CloudTrail ─ Athena (lineage queries) ─ ADOT (OpenTelemetry)     │   │
│  │ Exception sanitization ─ No raw PHI in metrics/alarms            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Cross-Cutting Concerns (Release 1)

### 1. Human Workflow Layer

Not just escalation policy -- an **operational capability**.

```
src/core/human_review/
├── queue.py              # DynamoDB-backed clinician worklist
├── models.py             # ReviewTask, ReviewDecision, OverrideReason
├── approval.py           # Submit/approve/reject/override with reason capture
├── resume.py             # Resume paused workflow after human decision
└── sla_monitor.py        # Alert on unresolved escalations (configurable timeout)
```

**Review Task Model**:
```python
class ReviewTask(BaseModel):
    task_id: str                     # Unique review task ID
    workflow_id: str                 # Correlation ID of the triggering workflow
    a2a_task_id: str                 # A2A task that was paused
    agent_id: str                    # Which agent escalated
    escalation_trigger: str          # "ESI_LEVEL_1", "low_confidence", "contraindication"
    patient_id: str
    agent_recommendation: dict       # What the agent suggested
    clinical_context: dict           # Relevant patient data (PHI - encrypted)
    status: ReviewStatus             # PENDING | APPROVED | REJECTED | OVERRIDDEN | EXPIRED
    assigned_to: str | None          # Clinician ID
    decision: ReviewDecision | None  # Human decision with reasoning
    override_reason: str | None      # Required if overriding agent recommendation
    created_at: datetime
    resolved_at: datetime | None
    sla_deadline: datetime           # Auto-escalate if unresolved
```

**Workflow behavior**:
- Agent hits escalation trigger → creates ReviewTask → A2A task enters `input-required` state
- Clinician reviews via API (FastAPI endpoint, or future UI)
- On approval/rejection: workflow resumes with human decision injected
- Override: agent recommendation rejected, human provides alternative, both recorded immutably
- SLA: unresolved tasks after timeout → auto-escalate to supervisor

### 2. Identity, Consent, and Break-Glass Access

```
src/core/consent/
├── manager.py            # Consent verification, revocation handling
├── models.py             # ConsentRecord, ConsentScope, ConsentStatus
├── break_glass.py        # Emergency access with enhanced audit
└── patient_identity.py   # Patient matching, duplicate resolution
```

**Consent Model** (not binary -- scoped by data type and use case):
```python
class ConsentScope(BaseModel):
    data_types: list[str]            # ["demographics", "labs", "medications", "conditions"]
    permitted_uses: list[str]        # ["treatment", "care_coordination", "research"]
    permitted_agents: list[str]      # ["triage_agent", "care_coordinator"]
    valid_from: datetime
    valid_until: datetime | None

class ConsentRecord(BaseModel):
    consent_id: str                  # FHIR Consent resource ID
    patient_id: str
    status: ConsentStatus            # ACTIVE | REVOKED | EXPIRED | DRAFT
    scopes: list[ConsentScope]       # Multiple scopes per consent
    revocation_date: datetime | None
    revocation_reason: str | None
```

**Break-Glass Access**:
- Emergency override when consent doesn't cover the required access
- Requires: reason code, enhanced audit event, supervisor notification
- All break-glass access: logged separately, reviewed within 24 hours
- FHIR AuditEvent with `purposeOfUse = "ETREAT"` (emergency treatment)

**Patient Identity**:
- Master Patient Index (MPI) pattern for duplicate resolution
- Deterministic + probabilistic matching (name, DOB, MRN, SSN-last-4)
- Merge/link records, maintain audit trail of identity changes

**Per-Agent Service Identity**:
- Each agent and MCP server has its own Cognito client ID + secret
- Service-to-service JWT with `sub` = agent ID, `scope` = permitted operations
- No shared app credentials -- every call attributable to a specific agent

### 3. Prompt/Model Lifecycle Governance

```
governance/lifecycle/
├── version_registry.py     # Track all version dimensions
├── prompt_registry.py      # Store and version prompts
├── eval_runner.py          # Run evaluation datasets against agents
├── shadow_eval.py          # Shadow mode comparison (old vs new)
└── rollback.py             # Independent rollback per dimension
```

**Five version dimensions tracked per workflow result**:
```python
class WorkflowVersionContext(BaseModel):
    model_version: str          # e.g., "claude-sonnet-4-6-20250514"
    prompt_version: str         # e.g., "triage-v2.3"
    retrieval_corpus_version: str  # e.g., "esi-guidelines-2026Q1"
    policy_version: str         # e.g., "escalation-policy-v1.2"
    tool_contract_version: str  # e.g., "fhir-mcp-tools-v1.0"
```

- Every agent output includes the full `WorkflowVersionContext`
- When behavior changes → diff versions to identify cause
- **Prompt registry**: prompts stored as versioned assets, not inline strings
- **Eval datasets**: per-agent golden datasets with expected outputs
- **Shadow eval**: new version runs in shadow mode, output compared to production
- **Rollback**: each dimension independently rollbackable

### 4. LLM Safety and Evaluation Harnesses

```
eval/
├── datasets/                # Golden evaluation datasets per agent
│   ├── triage/
│   │   ├── golden_inputs.json
│   │   └── expected_outputs.json
│   └── care_coordinator/
│       ├── golden_inputs.json
│       └── expected_outputs.json
├── harness.py              # Evaluation runner
├── metrics.py              # Evaluation metrics
└── reports/                # Generated evaluation reports
```

**Evaluation metrics per agent**:
| Metric | Description | Target |
|--------|-------------|--------|
| Clinical routing correctness | Agent routes to correct specialty | >95% |
| Unsafe recommendation rate | Dangerous clinical advice given | <0.1% |
| Hallucinated code rate | Invalid ICD-10/SNOMED/RxNorm codes | 0% |
| Citation completeness | Decision references valid clinical criteria | >90% |
| Tool-call success rate | MCP calls succeed without error | >99% |
| Escalation precision | Escalations that needed human review | >80% |
| Escalation recall | Cases needing review that were escalated | >98% |
| **Abstention accuracy** | Correctly abstains when uncertain | >95% |

**Golden test coverage roadmap** (`golden_tests/`):
- Deterministic end-to-end scenarios with fixed inputs and expected outputs
- Run in CI on every PR
- **R1** (implemented): normal triage, emergency escalation, consent denial, break-glass, saga compensation
- **R2** (added later): drug interaction block, unsafe prescription rejection, notification failure

### 5. Idempotency, Sagas, and Compensating Actions

```
src/core/workflow/
├── saga.py               # Saga state machine per workflow
├── idempotency.py        # Idempotency key management
├── compensating.py       # Compensating action registry
└── models.py             # SagaState, SagaStep, CompensatingAction
```

**Saga Pattern for Triage & Route Workflow (Release 1)**:
```
Step 1: Record intake (FHIR MCP intake tools) → compensate: mark intake as voided
Step 2: Assess triage (Triage Agent logic) → compensate: void triage assessment
Step 3: Book appointment (Scheduling MCP) → compensate: cancel appointment
```
Note: Notification step is added in R2 when Notification MCP is introduced.

**Idempotency**:
- Every write operation accepts an idempotency key (UUID generated by caller)
- DynamoDB conditional writes: `attribute_not_exists(idempotency_key)`
- Client retries safe: duplicate delivery produces same result
- TTL on idempotency records (24 hours)

**Timeout ownership**:
- Each agent/MCP boundary has an explicit timeout
- Caller owns the timeout (not callee)
- On timeout: saga step marked as UNKNOWN, compensating action queued for investigation

### 6. PHI Redaction in Observability

```
src/core/security/
├── ...existing...
├── redaction.py          # PHI redaction engine
├── log_sanitizer.py      # Middleware for structlog
├── trace_sanitizer.py    # OpenTelemetry span processor for PHI scrubbing
└── exception_sanitizer.py # Strip PHI from exception messages/tracebacks
```

**Rules**:
- **Logs**: All structlog processors run through `PHIRedactor` before emission
- **Traces**: Custom `SpanProcessor` strips PHI from span attributes (patient names, MRNs, SSNs)
- **Exceptions**: `ExceptionSanitizer` wraps exception handlers to remove PHI from messages
- **Metrics**: No patient identifiers in CloudWatch metric dimensions or alarm messages
- **Prompts/Responses**: LLM I/O stored only in encrypted audit log, never in general logs
- **Safe sampling**: trace sampling policy excludes PHI-heavy spans from sampled exports

**PHI detection patterns** (regex + Macie integration):
- Patient name patterns, MRN formats, SSN patterns, DOB patterns
- FHIR resource IDs that resolve to patient data
- Free-text clinical notes

### 7. Terminology Service

```
src/core/terminology/
├── service.py            # TerminologyService: normalize, validate, translate
├── models.py             # CodingSystem, CodedConcept, ValueSet
├── normalization.py      # Canonical coding strategy
├── validation.py         # Value set validation against FHIR ValueSets
├── versioning.py         # Track terminology version, handle deprecated codes
└── data/                 # Terminology data files (loaded at startup)
    ├── icd10_2026.json
    ├── snomed_core_subset.json
    ├── rxnorm_active.json
    └── loinc_common.json
```

**Not just lookup files** -- a service boundary:
- `normalize(system, code) -> CanonicalCode` -- maps synonyms/variants to canonical
- `validate(system, code) -> ValidationResult` -- checks against value set, flags deprecated/inactive
- `translate(source_system, code, target_system) -> Code | None` -- cross-system mapping
- `get_display(system, code) -> str` -- human-readable display name
- Version-aware: tracks which terminology version is active, handles updates
- Deprecated code handling: flag, suggest replacement, don't silently accept

### 8. Workflow Resilience (Saga State Machine)

Each workflow step is a saga step with clear state:
```python
class SagaStep(BaseModel):
    step_id: str
    name: str                     # "book_appointment"
    status: StepStatus            # PENDING | RUNNING | COMPLETED | FAILED | COMPENSATED | UNKNOWN
    idempotency_key: str
    started_at: datetime | None
    completed_at: datetime | None
    timeout_ms: int               # Caller-owned timeout
    result: dict | None
    compensating_action: str      # "cancel_appointment"
    compensation_status: StepStatus | None
```

Saga state persisted in DynamoDB. On partial failure:
1. Mark failed step
2. Execute compensating actions for completed steps (in reverse order)
3. Log saga outcome with full lineage context
4. If compensation fails → alert on-call + create incident

---

## Data Lineage Framework

### OpenLineage Events

Every MCP tool call and A2A message emits a `HealthcareLineageEvent`:

```
src/core/lineage/
├── events.py              # HealthcareLineageEvent model (OpenLineage-based)
├── context.py             # ContextVar: run_id, parent_run_id, correlation_id, consent_ref
├── emitter.py             # Emit to DynamoDB (index) + S3 (detail)
├── mcp_middleware.py       # Auto-capture on every MCP tool call
├── a2a_propagation.py     # Lineage context in A2A headers + DataPart metadata
├── fhir_audit.py           # FHIR AuditEvent dual-write for PHI access
├── decorators.py           # @track_lineage decorator
└── graph.py                # NetworkX DAG builder + Mermaid export + cycle detection
```

**Key fields per event**: run_id, parent_run_id, correlation_id, agent_id, job_name, patient_id, consent_reference, data_classification, PHI handling facets, mcp_tool_name, a2a_task_id, workflow_version_context

**Storage**: DynamoDB (index, GSI on correlation_id + patient_id) + S3 (partitioned JSON) + Athena (queries)

**Lineage trace example** (Triage & Route, Release 1):
```
FHIR MCP (record_symptoms) ──▶ Triage Agent (assess_urgency)
  run_id: R1                      run_id: R2, parent: R1
  input: symptoms JSON            input: Patient/P001 (via FHIR MCP get_patient)
  output: Observation/OBS001      output: TriageAssessment/T001
  classification: PHI             classification: PHI
  consent: Consent/C001           consent: Consent/C001
       │
       ▼
  Triage Agent ──A2A──▶ Care Coordinator ──▶ Scheduling MCP (book_appointment)
  run_id: R2              run_id: R3, parent: R2    run_id: R4, parent: R3
                          input: TriageAssessment    output: Appointment/A001
                          output: CarePlan/CP001     classification: OPERATIONAL
                          saga_state: COMPLETED

                          (if ESI 1-2:)
                          → saga_state: PAUSED
                          → ReviewTask created
                          → human approves/overrides
                          → saga_state: RESUMED
                          → Appointment booked
```

---

## Metadata Management

```
governance/metadata/
├── catalog.py                    # Central registry + FastAPI endpoints (/metadata/*)
├── agent_cards/                  # Agent Governance Cards (Pydantic + YAML)
│   ├── schema.py                 # AgentGovernanceCard model
│   └── *.yaml                    # Per-agent cards (risk, bias, explainability, oversight)
├── tool_cards/                   # MCP Tool Cards (per tool: PHI classification, RBAC, SLA)
│   ├── schema.py
│   └── tools/*.yaml
├── data_cards/                   # Dataset Cards (sensitivity, quality, lineage, access control)
│   ├── schema.py
│   └── datasets/*.yaml
└── quality/
    ├── metrics.py                # 5-dimension scoring: completeness, accuracy, consistency, timeliness, conformance
    └── monitors.py               # Continuous quality checks (daily/weekly/hourly)
```

Cards are version-controlled YAML. Runtime metadata (usage stats, quality scores) stored in DynamoDB.

---

## Governance Framework (4 Pillars)

### 1. AI Governance (NIST AI RMF)
- Risk classification per agent (high for clinical, moderate for scheduling)
- Agent governance cards with: intended use, out-of-scope, performance targets, bias testing, explainability, oversight
- Version registry tracking 5 dimensions (model, prompt, corpus, policy, tool contracts)
- Evaluation harness with golden tests in CI

### 2. Clinical Governance
- Safety guardrails engine (escalation triggers, contraindication blocks)
- Human review queue with SLA monitoring
- Override reason capture (immutable record: agent recommendation vs human decision)
- Clinical outcome tracking

### 3. Data Governance
- Scoped consent (per data type, use case, agent)
- Consent revocation handling (stop processing, retain audit trail)
- Break-glass access with enhanced audit + 24hr review requirement
- PHI redaction across all observability surfaces
- Data classification tags on every data access
- Retention policies (HIPAA 7-year minimum)

### 4. Operational Governance
- SLA definitions per agent (availability, latency, accuracy, escalation rate)
- Incident response protocol (detect → alert → contain → investigate → remediate → postmortem)
- Change management (shadow mode → canary → full rollout, governance board approval for high-risk)
- Compliance dashboard (audit trail, governance card status, quality scores, escalation rates)

---

## Locked Boundary Decisions (ADR-Level)

### BD-1: Notification is R2 (not in R1 saga)

The R1 workflow is: intake → triage → schedule appointment. There is no notification step in R1. The saga has 3 steps (intake, triage, schedule). Notification MCP and notification-related compensation are introduced in R2. Golden tests do not include notification failure scenarios.

### BD-2: Patient Intake is folded into FHIR MCP for R1

In R1, the FHIR MCP Server includes patient intake tools (`record_symptoms`, `record_vital_signs`) alongside standard FHIR CRUD. This avoids creating an extra service boundary prematurely. In R2, intake tools are extracted into a separate Patient Intake MCP Server. The Triage Agent's MCP client connects to one server (FHIR MCP) in R1, not two.

### BD-3: Saga/workflow state is source of truth for task durability

The `a2a-sdk` task store (in-memory for dev, SQLite for local) is treated as an **implementation detail** of the A2A protocol layer. The **source of truth** for workflow state, paused tasks, and human review status is our own **saga state in DynamoDB** (AWS) or SQLite (local). When a task enters `input-required` for human review, the saga state captures the pause, and workflow resumption is driven from our saga coordinator -- not from the A2A SDK's task store. This means the A2A SDK dependency on `sqlite` is only for local dev convenience, not for durable production state.

### BD-4: FHIR R4 is the canonical wire format

- **Canonical wire format**: FHIR R4 (what HealthLake speaks, what leaves MCP tools)
- **Internal Python models**: `fhir.resources` R4B classes (R4B is a backward-compatible maintenance release of R4; no breaking changes vs R4)
- **Validation rule**: all FHIR resources must pass R4 validation before persistence or emission
- **Serialization**: `to_fhir()` and `from_fhir()` converters on domain models produce R4-valid JSON
- **Test fixtures**: validated against R4 profiles, not R4B-specific extensions
- **HealthLake adapter**: no translation needed (R4B is R4-compatible)

### BD-5: Service-to-service auth pattern (frozen for MVP)

```yaml
auth:
  issuer: Cognito User Pool (AWS) / local JWT issuer (dev)
  token_type: OAuth2 Client Credentials Grant (machine-to-machine)
  audience: "healthcare-mcp-a2a"          # Single audience for all services
  scope_naming: "{resource}:{action}"     # e.g., "patient:read", "appointment:write"
  token_lifetime: 3600s (1 hour)          # Short-lived, no refresh token needed
  secret_rotation: Secrets Manager auto-rotation (90 days)

  agents:                                 # Each agent = Cognito app client
    triage_agent:
      client_id: "triage-agent-{env}"
      scopes: ["patient:read", "observation:read", "condition:read", "intake:write", "triage:write"]
    care_coordinator:
      client_id: "care-coordinator-{env}"
      scopes: ["patient:read", "appointment:read", "appointment:write", "triage:read"]

  mcp_servers:                            # Each MCP server validates caller scopes
    fhir_mcp:
      required_scopes_per_tool:
        get_patient: ["patient:read"]
        record_symptoms: ["intake:write"]
        create_observation: ["observation:write"]
    scheduling_mcp:
      required_scopes_per_tool:
        book_appointment: ["appointment:write"]
        get_available_slots: ["appointment:read"]

  local_dev:
    mode: "jwt-only"                      # No Cognito; local JWT issuer with same scope model
    secret: "from .env (JWT_SECRET_KEY)"
    validation: "same scope checks, same audit logging"
```

This is ADR-005. All auth code implements this pattern from day one. No redesign later.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.11+ with strict type hints |
| **MCP SDK** | `mcp[cli]` (FastMCP, Streamable HTTP transport) |
| **A2A SDK** | `a2a-sdk[http-server]` (task store is impl detail; saga state is source of truth) |
| **Web Framework** | FastAPI + Uvicorn |
| **Data Validation** | Pydantic v2, pydantic-settings |
| **FHIR** | `fhir.resources` R4B classes (R4-compatible wire format; see BD-4) |
| **Local DB** | SQLAlchemy async + aiosqlite (per-service SQLite) |
| **AWS DB** | HealthLake (FHIR), DynamoDB (ops + lineage + saga + human queue) |
| **AWS Compute** | ECS Fargate (agents), Lambda (MCP servers) |
| **AWS API** | API Gateway + WAF + Cognito |
| **AWS Security** | KMS (per-env CMK), Secrets Manager, Macie, GuardDuty |
| **AWS Observability** | CloudWatch, X-Ray, CloudTrail, ADOT |
| **AWS Governance** | Config, Security Hub, Control Tower, Organizations |
| **IaC** | AWS CDK (Python) |
| **Auth** | Cognito OAuth2 (per-agent client IDs), JWT |
| **Encryption** | KMS CMK (AWS), AES-256 Fernet (local) |
| **Data Lineage** | OpenLineage Python client, FHIR AuditEvent |
| **Lineage Storage** | DynamoDB (index) + S3 (detail) + Athena (query) |
| **Lineage Viz** | NetworkX (DAG) + Mermaid export |
| **Terminology** | Custom service (ICD-10, SNOMED CT, RxNorm, LOINC) |
| **PHI Redaction** | Custom middleware (logs, traces, exceptions, metrics) |
| **HTTP Client** | httpx (async) |
| **Logging** | structlog (JSON, PHI-redacted) -> CloudWatch Logs |
| **Tracing** | OpenTelemetry (ADOT, PHI-sanitized) -> X-Ray |
| **Testing** | pytest, pytest-asyncio, pytest-cov (>80%) |
| **Evaluation** | Custom harness with golden datasets |
| **Code Quality** | ruff, black, mypy (strict), pre-commit |
| **Supply Chain** | SBOM (syft), signed container images, dependency allowlist |
| **Containers** | Docker multi-stage, docker-compose (local), ECS (AWS) |
| **CI/CD** | GitHub Actions -> CDK Deploy |
| **Package Mgmt** | uv |

---

## Project Structure

```
healthcare-mcp-a2a/
├── pyproject.toml
├── .env.example
├── .pre-commit-config.yaml
├── .gitignore
├── Makefile
├── CLAUDE.md
│
├── infra/                              # AWS CDK (Python)
│   ├── app.py
│   ├── cdk.json
│   ├── requirements.txt
│   ├── stacks/
│   │   ├── network_stack.py            # VPC, private subnets, VPC endpoints, egress rules
│   │   ├── security_stack.py           # KMS (per-env), Cognito (per-agent clients), WAF, Secrets Mgr
│   │   ├── data_stack.py              # HealthLake, DynamoDB tables, S3 buckets
│   │   ├── compute_stack.py           # ECS Fargate cluster + tasks, Lambda MCP functions
│   │   ├── api_stack.py               # API Gateway, A2A routes, Cognito authorizer
│   │   ├── observability_stack.py     # CloudWatch, X-Ray, ADOT, dashboards, alarms
│   │   ├── governance_stack.py        # Config HIPAA rules, Security Hub, GuardDuty, Macie
│   │   ├── audit_stack.py             # CloudTrail, S3 audit bucket, Athena
│   │   └── lineage_stack.py           # DynamoDB lineage table, S3 lineage bucket, Glue Catalog
│   └── constructs/                    # Reusable HIPAA-compliant L3 constructs
│       ├── hipaa_bucket.py
│       ├── hipaa_dynamodb.py
│       └── fargate_agent.py
│
├── governance/
│   ├── ai_governance/
│   │   ├── risk_assessment.py
│   │   └── agent_registry.py
│   ├── clinical/
│   │   ├── safety_guardrails.py
│   │   ├── escalation_policies.py
│   │   ├── validation_rules.py
│   │   └── outcome_tracker.py
│   ├── data/
│   │   ├── classification.py
│   │   ├── consent_manager.py         # → delegates to src/core/consent/
│   │   ├── retention_policies.py
│   │   └── sharing_policies.py
│   ├── metadata/
│   │   ├── catalog.py
│   │   ├── agent_cards/               # Schema + per-agent YAML
│   │   ├── tool_cards/                # Schema + per-tool YAML
│   │   ├── data_cards/                # Schema + per-dataset YAML
│   │   └── quality/
│   │       ├── metrics.py
│   │       └── monitors.py
│   ├── lifecycle/
│   │   ├── version_registry.py        # 5-dimension version tracking
│   │   ├── prompt_registry.py         # Versioned prompt storage
│   │   ├── eval_runner.py
│   │   ├── shadow_eval.py
│   │   └── rollback.py
│   └── operational/
│       ├── sla_definitions.py
│       ├── incident_response.py
│       ├── change_management.py
│       ├── compliance_dashboard.py
│       └── performance_monitor.py
│
├── src/
│   ├── core/
│   │   ├── config.py                  # Pydantic Settings (local/AWS mode)
│   │   ├── security/
│   │   │   ├── auth.py                # Per-agent JWT/Cognito
│   │   │   ├── rbac.py
│   │   │   ├── encryption.py          # KMS/Fernet
│   │   │   ├── redaction.py           # PHI redaction engine
│   │   │   ├── log_sanitizer.py       # structlog PHI scrubber
│   │   │   ├── trace_sanitizer.py     # OTEL span PHI scrubber
│   │   │   └── exception_sanitizer.py # Exception message PHI stripper
│   │   ├── consent/
│   │   │   ├── manager.py             # Scoped consent verification
│   │   │   ├── models.py              # ConsentRecord, ConsentScope, ConsentStatus
│   │   │   ├── break_glass.py         # Emergency access + enhanced audit
│   │   │   └── patient_identity.py    # MPI, duplicate resolution
│   │   ├── audit/
│   │   │   ├── logger.py              # HIPAA audit (hash-chained)
│   │   │   ├── models.py
│   │   │   └── middleware.py
│   │   ├── observability/
│   │   │   ├── logging.py             # structlog + PHI redaction
│   │   │   ├── correlation.py
│   │   │   └── tracing.py             # OTEL + PHI sanitization
│   │   ├── lineage/
│   │   │   ├── events.py              # HealthcareLineageEvent
│   │   │   ├── context.py             # ContextVar propagation
│   │   │   ├── emitter.py             # DynamoDB + S3
│   │   │   ├── mcp_middleware.py      # Auto-capture on MCP calls
│   │   │   ├── a2a_propagation.py     # Lineage in A2A headers
│   │   │   ├── fhir_audit.py          # FHIR AuditEvent dual-write
│   │   │   ├── decorators.py          # @track_lineage
│   │   │   └── graph.py               # NetworkX DAG + Mermaid
│   │   ├── terminology/
│   │   │   ├── service.py             # normalize, validate, translate
│   │   │   ├── models.py
│   │   │   ├── normalization.py
│   │   │   ├── validation.py
│   │   │   └── versioning.py
│   │   ├── workflow/
│   │   │   ├── saga.py                # Saga state machine
│   │   │   ├── idempotency.py         # Idempotency key management
│   │   │   ├── compensating.py        # Compensating action registry
│   │   │   └── models.py
│   │   ├── human_review/
│   │   │   ├── queue.py               # DynamoDB-backed worklist
│   │   │   ├── models.py              # ReviewTask, ReviewDecision
│   │   │   ├── approval.py            # Submit/approve/reject/override
│   │   │   ├── resume.py              # Resume paused workflow
│   │   │   └── sla_monitor.py         # Alert on unresolved reviews
│   │   ├── database/
│   │   │   ├── engine.py
│   │   │   ├── healthlake_client.py
│   │   │   └── migrations.py
│   │   ├── errors.py
│   │   └── resilience.py
│   │
│   ├── models/                        # Pydantic domain models
│   │   ├── fhir/                      # Patient, Observation, Condition, MedReq, Encounter
│   │   ├── clinical/                  # TriageAssessment, UrgencyLevel, SymptomReport, CarePlan
│   │   ├── scheduling/               # Appointment, TimeSlot, ProviderAvailability
│   │   ├── pharmacy/                  # [R2] Medication, DrugInteraction, Prescription
│   │   └── notification.py           # [R2] NotificationRequest
│   │
│   ├── mcp_servers/
│   │   ├── fhir/                      # [R1] FHIR R4 CRUD + patient intake tools (symptoms, vitals)
│   │   ├── scheduling/               # [R1] Appointment booking, availability
│   │   ├── patient_intake/            # [R2] Extracted from FHIR MCP as separate server
│   │   ├── pharmacy/                  # [R2]
│   │   └── notification/             # [R2]
│   │
│   ├── agents/
│   │   ├── triage/                    # [R1] ESI-based triage
│   │   ├── care_coordinator/          # [R1] Scheduling + human escalation + saga
│   │   ├── clinical_data/             # [R2]
│   │   └── pharmacy/                  # [R2]
│   │
│   └── orchestrator/
│       ├── coordinator.py             # [R1] A2A client
│       ├── workflows.py              # [R1] triage_and_route workflow
│       └── discovery.py              # Agent Card registry
│
├── eval/                              # Agent evaluation harness
│   ├── datasets/
│   │   ├── triage/                    # Golden inputs + expected outputs
│   │   └── care_coordinator/
│   ├── harness.py
│   ├── metrics.py
│   └── reports/
│
├── golden_tests/                      # Deterministic end-to-end scenarios (R1 only; R2 tests added in Release 2)
│   ├── test_normal_triage.py          # Happy path: intake → triage → appointment booked
│   ├── test_emergency_escalation.py   # ESI 1 → human review → approve → schedule
│   ├── test_consent_denial.py         # PHI access blocked, workflow halted
│   ├── test_break_glass.py            # Emergency override, enhanced audit, 24hr review
│   └── test_saga_compensation.py      # Scheduling fails → intake voided, triage voided
│
├── schemas/                           # Event contracts
│   ├── events/
│   │   ├── lineage_event.json         # OpenLineage event JSON schema
│   │   ├── audit_event.json           # FHIR AuditEvent schema
│   │   └── review_task.json           # Human review task schema
│   └── contracts/
│       ├── a2a_messages.json          # A2A message contracts per agent
│       └── mcp_tools.json             # MCP tool input/output contracts
│
├── policies/                          # Declarative policy files
│   ├── redaction.yaml                 # PHI redaction patterns and rules
│   ├── retention.yaml                 # Data retention by classification
│   ├── consent_scopes.yaml            # Default consent scope templates
│   ├── break_glass.yaml               # Break-glass conditions and audit requirements
│   └── escalation.yaml               # Escalation trigger definitions
│
├── data/
│   ├── seed/                          # FHIR JSON bundles
│   ├── terminology/                   # Code system data
│   └── drug_interactions/             # [R2]
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── contract/
│
├── scripts/
│   ├── seed_data.py
│   ├── run_all.py
│   ├── verify_setup.py
│   └── deploy.sh
│
├── docs/
│   ├── architecture/
│   │   ├── overview.md
│   │   ├── aws-deployment.md
│   │   └── adr/                       # 9 ADRs
│   ├── governance-framework.md
│   ├── data-lineage.md
│   ├── metadata-management.md
│   ├── threat-model.md
│   ├── clinical-safety-case.md
│   ├── rto-rpo.md
│   ├── data-contracts/
│   └── runbooks/
│       ├── incident-response.md
│       ├── agent-deployment.md
│       ├── compliance-audit.md
│       └── lineage-investigation.md
│
└── .github/workflows/
    ├── ci.yml                         # Lint + typecheck + test + golden tests + eval
    ├── security.yml                   # SBOM, dependency scan, SAST
    └── deploy.yml                     # CDK diff (PR) + CDK deploy (main)
```

---

## Implementation Phases (Release 1 Only)

### Phase 1: Foundation + Cross-Cutting Concerns
**Goal**: Project setup, all core infrastructure that every agent and server depends on

1. `pyproject.toml` (deps incl. `openlineage-python`, `networkx`), `.gitignore`, `.env.example`, `.pre-commit-config.yaml`, `Makefile`, `CLAUDE.md`
2. `src/core/config.py` -- Pydantic Settings (local/AWS mode, per-agent ports, per-env keys)
3. `src/core/security/auth.py` -- Per-agent JWT/Cognito (each agent has own client ID)
4. `src/core/security/rbac.py` -- 4 roles, scoped permissions
5. `src/core/security/encryption.py` -- KMS (AWS) / Fernet (local) for PHI at rest
6. `src/core/security/redaction.py` + `log_sanitizer.py` + `trace_sanitizer.py` + `exception_sanitizer.py` -- PHI redaction everywhere
7. `src/core/consent/` -- ConsentRecord, ConsentScope, scoped verification, revocation, break-glass with enhanced audit, patient identity (MPI basics)
8. `src/core/audit/` -- HIPAA audit logger (hash-chained, PHI-redacted), FHIR AuditEvent model
9. `src/core/observability/` -- structlog (with redaction), correlation IDs, OpenTelemetry tracing (with sanitization)
10. `src/core/lineage/` -- HealthcareLineageEvent, ContextVar propagation, emitter (DynamoDB+S3 or SQLite), MCP middleware, A2A propagation, FHIR AuditEvent dual-write, @track_lineage decorator, NetworkX DAG
11. `src/core/terminology/` -- TerminologyService (normalize, validate, translate), ICD-10/SNOMED/RxNorm/LOINC data, deprecated code handling
12. `src/core/workflow/` -- Saga state machine, idempotency keys, compensating action registry
13. `src/core/human_review/` -- ReviewTask model, DynamoDB-backed queue, approval/reject/override, resume-after-approval, SLA monitor
14. `src/core/database/` -- SQLite engine + HealthLake client + DynamoDB helpers
15. `src/core/errors.py` + `src/core/resilience.py`
16. `src/models/fhir/` + `src/models/clinical/` + `src/models/scheduling/` -- Pydantic models
17. `policies/*.yaml` -- redaction, retention, consent_scopes, break_glass, escalation
18. `schemas/events/` + `schemas/contracts/` -- JSON schemas for event/API contracts
19. Governance foundations: `governance/data/classification.py`, `consent_manager.py`, `sharing_policies.py`, `retention_policies.py`
20. Governance: `governance/clinical/safety_guardrails.py`, `escalation_policies.py`
21. Governance: `governance/lifecycle/version_registry.py`, `prompt_registry.py`
22. Metadata: `governance/metadata/catalog.py`, agent/tool/data card schemas, quality metrics
23. Unit tests for ALL of the above

**Verify**: `uv sync` + `ruff check` + `mypy` + `pytest tests/unit/` pass

### Phase 2: MCP Servers (FHIR + Scheduling)
**Goal**: Two MCP servers with lineage, audit, consent, terminology validation

24. `src/mcp_servers/fhir/` -- FHIR R4 CRUD (Patient, Observation, Condition, Encounter) **+ patient intake tools** (`record_symptoms`, `record_vital_signs`, `assess_vital_signs_urgency`) with:
    - Repository pattern (SQLite local, HealthLake AWS)
    - Lineage middleware on every tool (auto-emit OpenLineage events)
    - FHIR AuditEvent on every PHI access
    - Consent verification before PHI read/write
    - Terminology validation (ICD-10, SNOMED, LOINC codes validated via TerminologyService)
    - Data classification tags on every response
    - Idempotency keys on write operations
    - FHIR R4 wire format validation on all persisted resources (BD-4)
    - Auth: caller scope validation per tool (BD-5)
25. `src/mcp_servers/scheduling/` -- Appointment booking, availability with:
    - Same cross-cutting concerns (minus PHI-specific ones for operational data)
    - Idempotency on `book_appointment`
    - Auth: `appointment:read` / `appointment:write` scopes
26. Tool cards (YAML) for all MCP tools (~15 tools across 2 servers)
27. Data cards (YAML) for all datasets
28. Contract tests for MCP tool schemas
29. Unit tests for all tools + repository layers + lineage emission + consent checks

**Verify**: 2 MCP servers start, tools listed via Inspector, lineage events emitted, consent enforced, terminology validated, FHIR R4 validation passes

### Phase 3: A2A Agents (Triage + Care Coordinator)
**Goal**: Two agents with A2A communication, human escalation, saga coordination

31. `src/agents/triage/` -- AgentCard, MCP client (single FHIR MCP server which includes intake tools per BD-2), ESI triage logic, A2A executor
    - Safety guardrails: ESI 1-2 → create ReviewTask → A2A task enters `input-required`
    - Explainability: structured reasoning with ESI criteria references
    - Lineage: A2A context propagation (parent_run_id, correlation_id)
    - Version context: model/prompt/policy versions attached to every output
32. `src/agents/care_coordinator/` -- AgentCard, scheduling MCP client, A2A client to Triage
    - Saga coordinator for Triage & Route workflow
    - Human review integration: pause workflow on escalation, resume after approval
    - Compensating actions: cancel appointment if downstream fails
    - Override handling: if clinician overrides triage, route differently
33. Agent governance cards (YAML) for both agents
34. Evaluation datasets: `eval/datasets/triage/` + `eval/datasets/care_coordinator/`
35. Golden tests: `golden_tests/test_normal_triage.py`, `test_emergency_escalation.py`, `test_consent_denial.py`, `test_break_glass.py`, `test_saga_compensation.py`
36. Integration tests: A2A communication, lineage chain, human review flow, saga compensation

**Verify**: Agent Cards discoverable, ESI 1 triggers human review, lineage traces across agents, saga compensates on failure

### Phase 4: Orchestration + End-to-End
**Goal**: Complete Triage & Route workflow, compliance dashboard

37. `src/orchestrator/discovery.py` + `coordinator.py` -- A2A client driving workflow
38. `src/orchestrator/workflows.py` -- `triage_and_route_workflow` with:
    - Full saga coordination
    - Lineage: complete trace from intake to appointment
    - Human escalation path: pause → review → resume
    - Version context: all 5 dimensions tracked
39. `governance/operational/sla_definitions.py` + `performance_monitor.py`
40. `governance/operational/compliance_dashboard.py` -- first slice (audit count, escalation rate, lineage completeness)
41. `scripts/seed_data.py` -- 50 synthetic FHIR patients with consent records
42. `scripts/run_all.py` -- start 2 MCP servers + 2 agents (orchestrator is a library module invoked by workflows, not a separate running service)
43. Full integration tests for Triage & Route workflow
44. Eval harness run in CI: `eval/harness.py` against golden datasets

**Verify**: Workflow completes end-to-end, lineage DAG valid, human review works, golden tests pass, eval metrics meet targets

### Phase 5: AWS Infrastructure (CDK)
**Goal**: Full AWS deployment for Release 1

45. `infra/stacks/network_stack.py` -- VPC, private subnets, VPC endpoints, egress restrictions
46. `infra/stacks/security_stack.py` -- KMS CMK (per env), Cognito (per-agent clients), WAF, Secrets Mgr
47. `infra/stacks/data_stack.py` -- HealthLake, DynamoDB (saga, human queue, lineage index, metadata), S3 (audit, lineage)
48. `infra/stacks/compute_stack.py` -- ECS Fargate (2 agents, least-privilege IAM per task), Lambda (2 MCP servers, egress restricted)
49. `infra/stacks/api_stack.py` -- API Gateway + Cognito authorizer + A2A routes
50. `infra/stacks/observability_stack.py` -- CloudWatch dashboards, X-Ray, ADOT, alarms (no PHI in alarm messages)
51. `infra/stacks/governance_stack.py` -- Config HIPAA conformance pack, Security Hub, GuardDuty, Macie
52. `infra/stacks/audit_stack.py` -- CloudTrail, S3 lifecycle (7yr retention, Glacier after 1yr), Athena
53. `infra/stacks/lineage_stack.py` -- DynamoDB lineage table, S3 lineage bucket, Glue Catalog, Athena
54. `infra/constructs/` -- HIPAA bucket (encrypted, versioned, logged), HIPAA DynamoDB (encrypted, PITR, tagged), Fargate agent (least-privilege)
55. CDK unit tests (assertions on CloudFormation)
56. Contract tests against real AWS test env (ephemeral integration env in CI)

**Verify**: `cdk synth` valid, `cdk deploy` succeeds, agents healthy on Fargate, workflow works via API Gateway

### Phase 6: Quality, Docs & CI/CD
**Goal**: Production-ready, documented, automated

57. Docker multi-stage build + docker-compose (local dev with signed images)
58. GitHub Actions CI: lint, typecheck, test, golden tests, eval harness, SBOM generation
59. GitHub Actions security: dependency scanning, SAST, container image scanning
60. GitHub Actions deploy: CDK diff on PRs, CDK deploy on main (to test account first)
61. Documentation: README, architecture overview, aws-deployment, governance-framework, data-lineage, metadata-management
62. Documentation: threat-model, clinical-safety-case, rto-rpo, data-contracts
63. Operational runbooks: incident-response, agent-deployment, compliance-audit, lineage-investigation
64. 9 ADRs: MCP transport, A2A task store, FHIR store, agent compute, IaC, governance, lineage, terminology, human review
65. Ensure >80% test coverage
66. `scripts/deploy.sh` -- CDK deploy wrapper with env selection + pre-deploy validation

**Verify**: Full CI/CD passes, `make deploy-aws` deploys, all docs written, coverage >80%

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Execution | 3-release vertical slices | Reduce scope/coupling risk; depth over breadth |
| R1 MCP Servers | FHIR (incl. intake tools) + Scheduling only | Avoid premature boundaries; intake extracted in R2 |
| MCP Transport | Streamable HTTP | Production-recommended, multi-client |
| FHIR Version | R4 wire format, R4B Python classes (BD-4) | HealthLake speaks R4; R4B is backward-compatible |
| FHIR Store | HealthLake (AWS), SQLite (local) | Native FHIR R4, ONC compliant |
| Agent Compute | ECS Fargate | Serverless containers, HIPAA, auto-scale |
| MCP Compute | Lambda | Per-invocation, cost-efficient (evaluate cold-start for latency-sensitive tools) |
| Agent Identity | Per-agent Cognito client (BD-5) | Attributable auth, no shared credentials, frozen scope model |
| Task State | Saga/DynamoDB is source of truth (BD-3) | A2A SDK task store is impl detail; saga owns durability |
| PHI Redaction | Custom middleware (logs, traces, exceptions, metrics) | Prevent leakage across all observability |
| Consent | Scoped (per data type, use, agent) + break-glass | Healthcare consent is never binary |
| Human Review | DynamoDB-backed queue with SLA + resume | Operational capability, not just policy |
| Workflow | Saga with idempotency + compensating actions | Partial failure handling across agents |
| Terminology | Service boundary (not just files) | Normalize, validate, translate, version, deprecate |
| Version Tracking | 5 dimensions (model, prompt, corpus, policy, tools) | Isolate behavioral changes |
| Lineage | OpenLineage + FHIR AuditEvent dual-write | Graph lineage + HIPAA compliance |
| Lineage Storage | DynamoDB index + S3 detail + Athena query | Cost-effective, queryable, long-term |
| Metadata | Pydantic cards (YAML) + Glue Catalog | Type-safe, version-controlled, AWS-native |
| Data Quality | 5-dimension scoring | FHIR-aligned quality model |
| Environment | Separate AWS accounts (dev/test/prod) | Isolated data plane, KMS, audit |
| Supply Chain | SBOM, signed images, dependency allowlist | MCP servers are tool-execution surfaces |
| Orchestrator | Workflow sequencing only | Agent owns domain decisions, MCP owns data |
| Local Parity | Contract tests against real AWS | Prevent SQLite/DynamoDB drift |

---

## Verification Plan (Release 1)

| Category | Check | Expected |
|----------|-------|----------|
| **Build** | `uv sync --all-extras` | All deps installed |
| **Quality** | `make lint && make typecheck` | Zero errors |
| **Unit Tests** | `pytest tests/unit/ -v` | All pass, >80% coverage |
| **Golden Tests** | `pytest golden_tests/ -v` | All 5 scenarios pass |
| **Eval Harness** | `python eval/harness.py` | All metrics meet targets |
| **Local Run** | `make run` | 4 services healthy (2 MCP servers + 2 agents; orchestrator is a module, not a service) |
| **Workflow** | Run triage_and_route for patient P001 | Appointment booked OR escalated |
| **Escalation** | Triage ESI Level 1 patient | ReviewTask created, workflow paused |
| **Human Review** | Approve review task | Workflow resumes, appointment booked |
| **Override** | Override triage recommendation | Agent + human decisions both recorded |
| **Consent Denial** | Access patient without consent | Blocked, audit logged, 403 returned |
| **Break-Glass** | Emergency access without consent | Allowed with enhanced audit + alert |
| **Saga Failure** | Fail scheduling after intake + triage | Intake voided, triage voided (compensating actions) |
| **Idempotency** | Retry book_appointment with same key | Single appointment created |
| **Lineage Trace** | Query by correlation_id | Events from all agents in correct order |
| **Lineage DAG** | Build graph from workflow | Valid DAG, correct topology |
| **FHIR AuditEvent** | Query audit events for patient | All PHI accesses with consent refs |
| **PHI Redaction** | Inspect logs/traces after workflow | No raw PHI in any observability output |
| **Terminology** | Submit invalid ICD-10 code | Rejected with suggestion |
| **Metadata API** | GET /metadata/agents | All governance cards returned |
| **Data Quality** | Run quality monitors | Completeness >90%, conformance >95% |
| **Docker** | `make run-docker` | All services healthy |
| **AWS Deploy** | `cdk deploy --all` | All stacks deployed |
| **AWS Workflow** | Run via API Gateway | End-to-end success |
| **Config Rules** | Security Hub dashboard | HIPAA rules passing |
| **CloudTrail** | Athena query on audit bucket | All API calls logged |

---

## Backup, DR & Restore (Release 1 Baseline)

| Resource | RTO | RPO | Mechanism |
|----------|-----|-----|-----------|
| HealthLake | 4h | 0 (continuous) | AWS-managed, cross-AZ |
| DynamoDB | 1h | 35 days PITR | Point-in-time recovery enabled |
| S3 (audit/lineage) | 1h | 0 (versioned) | Versioning + object lock + cross-region replication |
| ECS Tasks | 5min | N/A (stateless) | Auto-restart, multi-AZ |
| Lambda | 1min | N/A (stateless) | Multi-AZ by default |
| Cognito | AWS-managed | AWS-managed | Multi-AZ by default |

- Restore drill cadence: quarterly (documented in runbooks)
- Degraded mode: agents return `503 + Retry-After` when backing service unavailable
- Region failure: manual failover to secondary region (R3 automation target)
