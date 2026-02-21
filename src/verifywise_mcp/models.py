"""Pydantic data models for VerifyWise API entities.

These models are used throughout the MCP server to validate and serialise
data received from the VerifyWise REST API. They also drive the JSON schema
that FastMCP exposes to LLM clients.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    """Risk / severity level for projects, risks, and vendors."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProjectStatus(StrEnum):
    """Lifecycle status of an AI governance project (Use Case)."""

    DRAFT = "draft"
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    ARCHIVED = "archived"


class Project(BaseModel):
    """An AI governance project (Use Case) in VerifyWise.

    Projects represent AI applications that are being governed under one or
    more compliance frameworks.
    """

    id: str = Field(description="Unique project identifier")
    name: str = Field(description="Human-readable project name")
    description: str | None = Field(default=None, description="Project description")
    status: ProjectStatus = Field(description="Current lifecycle status")
    risk_level: RiskLevel | None = Field(default=None, description="Overall risk level")
    framework: str | None = Field(default=None, description="Primary compliance framework")
    created_at: datetime = Field(description="Creation timestamp (ISO 8601)")
    updated_at: datetime = Field(description="Last update timestamp (ISO 8601)")


class Risk(BaseModel):
    """A risk associated with an AI governance project."""

    id: str = Field(description="Unique risk identifier")
    project_id: str = Field(description="ID of the owning project")
    title: str = Field(description="Short risk title")
    description: str = Field(description="Detailed risk description")
    severity: RiskLevel = Field(description="Risk severity level")
    status: str = Field(description="Risk status (e.g. open, mitigated, closed)")
    owner: str | None = Field(default=None, description="Email of the risk owner")
    due_date: datetime | None = Field(default=None, description="Risk mitigation due date")
    created_at: datetime = Field(description="Creation timestamp (ISO 8601)")


class Vendor(BaseModel):
    """A third-party vendor tracked in the VerifyWise vendor risk register."""

    id: str = Field(description="Unique vendor identifier")
    name: str = Field(description="Vendor / company name")
    type: str | None = Field(default=None, description="Vendor category (e.g. ai-provider)")
    risk_score: int | None = Field(default=None, description="Vendor risk score (0–100)")
    risk_level: RiskLevel | None = Field(default=None, description="Derived risk level")
    created_at: datetime = Field(description="Creation timestamp (ISO 8601)")
    updated_at: datetime = Field(description="Last update timestamp (ISO 8601)")


class ComplianceControl(BaseModel):
    """A single compliance control within a governance framework.

    Controls represent specific requirements from frameworks such as the
    EU AI Act, ISO 42001, ISO 27001, or NIST AI RMF.
    """

    id: str = Field(description="Unique control identifier")
    framework: str = Field(description="Parent framework (e.g. eu-ai-act)")
    subclause: str = Field(description="Framework subclause reference (e.g. Article 10)")
    title: str = Field(description="Short control title")
    description: str = Field(description="Detailed control description")
    status: str = Field(
        description="Completion status: not_started, in_progress, complete, not_applicable"
    )
    evidence_count: int = Field(default=0, description="Number of attached evidence items")
    last_reviewed: datetime | None = Field(default=None, description="Timestamp of the last review")


class AIModel(BaseModel):
    """An AI/ML model entry in the VerifyWise model inventory."""

    id: str = Field(description="Unique model record identifier")
    name: str = Field(description="Model name (e.g. GPT-4o, Llama-3)")
    provider: str | None = Field(default=None, description="Model provider (e.g. OpenAI)")
    type: str | None = Field(default=None, description="Model type (e.g. llm, cv, nlp)")
    version: str | None = Field(default=None, description="Model version or release tag")
    created_at: datetime = Field(description="Creation timestamp (ISO 8601)")
    updated_at: datetime = Field(description="Last update timestamp (ISO 8601)")
