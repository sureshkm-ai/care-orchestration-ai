"""Agent Governance Card schema -- extends A2A AgentCard with governance metadata."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PerformanceTargets(BaseModel):
    accuracy_target: str = ">95%"
    false_negative_max: str = "<2%"
    latency_p95_ms: int = 500
    availability: str = "99.99%"


class BiasTestingConfig(BaseModel):
    methodology: str = "demographic parity analysis"
    monitored_groups: list[str] = Field(default_factory=lambda: ["race", "gender", "age_group"])
    frequency: str = "weekly automated, monthly human review"


class HumanOversight(BaseModel):
    escalation_triggers: list[str] = Field(default_factory=list)
    review_cadence: str = ""


class ExplainabilityConfig(BaseModel):
    method: str = ""
    output_format: str = ""
    human_readable: bool = True


class AgentGovernanceCard(BaseModel):
    """Full governance metadata for an agent."""

    # Identification
    name: str
    version: str
    developer: str = "Healthcare MCP+A2A Platform"
    release_date: date | None = None

    # Intended use
    purpose: str = ""
    clinical_context: str = ""
    target_population: str = ""
    out_of_scope: list[str] = Field(default_factory=list)

    # Performance
    performance: PerformanceTargets = Field(default_factory=PerformanceTargets)

    # Bias and fairness
    bias_testing: BiasTestingConfig = Field(default_factory=BiasTestingConfig)

    # Explainability
    explainability: ExplainabilityConfig = Field(default_factory=ExplainabilityConfig)

    # Human oversight
    human_oversight: HumanOversight = Field(default_factory=HumanOversight)

    # Governance
    risk_classification: str = "high"  # NIST AI RMF
    approval_status: str = "draft"
    next_review_date: date | None = None
