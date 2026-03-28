"""Application configuration using Pydantic Settings.

Supports two modes:
- local: SQLite databases, local JWT auth, Fernet encryption
- aws: HealthLake, DynamoDB, Cognito, KMS
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(str, Enum):
    LOCAL = "local"
    AWS = "aws"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: AppEnv = AppEnv.LOCAL
    log_level: str = "INFO"
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])

    # Security (BD-5: frozen auth pattern)
    jwt_secret_key: str = "dev-only-change-in-production-min-32-chars!!"
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "healthcare-mcp-a2a"
    jwt_token_lifetime_seconds: int = 3600
    encryption_key: str = "dev-only-change-in-production-32b!"

    # Agent Ports (A2A servers)
    triage_agent_port: int = 9001
    care_coordinator_agent_port: int = 9002

    # MCP Server Ports
    fhir_mcp_port: int = 8001
    scheduling_mcp_port: int = 8003

    # Database (local mode)
    database_dir: str = "./data/db"

    # AWS (aws mode)
    aws_region: str = "us-east-1"
    healthlake_datastore_id: str = ""
    cognito_user_pool_id: str = ""
    cognito_client_id_triage: str = ""
    cognito_client_id_care_coordinator: str = ""
    kms_key_id: str = ""
    dynamodb_table_prefix: str = "healthcare-mcp-a2a"
    lineage_s3_bucket: str = ""
    audit_s3_bucket: str = ""

    @property
    def is_local(self) -> bool:
        return self.app_env == AppEnv.LOCAL

    @property
    def is_aws(self) -> bool:
        return self.app_env == AppEnv.AWS

    @property
    def db_dir(self) -> Path:
        path = Path(self.database_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def fhir_mcp_url(self) -> str:
        return f"http://localhost:{self.fhir_mcp_port}/mcp"

    def scheduling_mcp_url(self) -> str:
        return f"http://localhost:{self.scheduling_mcp_port}/mcp"

    def triage_agent_url(self) -> str:
        return f"http://localhost:{self.triage_agent_port}"

    def care_coordinator_agent_url(self) -> str:
        return f"http://localhost:{self.care_coordinator_agent_port}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
