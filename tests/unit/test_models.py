"""Unit tests for the Pydantic data models.

Verifies model construction, validation, and enum values.
"""

from datetime import datetime, timezone

import pytest


NOW = datetime.now(tz=timezone.utc).isoformat()


# --- Enums ---


def test_risk_level_enum_values():
    """RiskLevel should have the four expected severity values."""
    from verifywise_mcp.models import RiskLevel

    assert RiskLevel.LOW == "low"
    assert RiskLevel.MEDIUM == "medium"
    assert RiskLevel.HIGH == "high"
    assert RiskLevel.CRITICAL == "critical"


def test_project_status_enum_values():
    """ProjectStatus should include draft, active, under_review, and archived."""
    from verifywise_mcp.models import ProjectStatus

    assert ProjectStatus.DRAFT == "draft"
    assert ProjectStatus.ACTIVE == "active"
    assert ProjectStatus.UNDER_REVIEW == "under_review"
    assert ProjectStatus.ARCHIVED == "archived"


# --- Project ---


def test_project_model_valid():
    """Project model should accept a full valid payload."""
    from verifywise_mcp.models import Project, ProjectStatus, RiskLevel

    p = Project(
        id="1",
        name="Loan Approval AI",
        description="Automated loan approval system",
        status=ProjectStatus.ACTIVE,
        risk_level=RiskLevel.HIGH,
        framework="eu-ai-act",
        created_at=NOW,
        updated_at=NOW,
    )

    assert p.id == "1"
    assert p.name == "Loan Approval AI"
    assert p.status == ProjectStatus.ACTIVE
    assert p.risk_level == RiskLevel.HIGH


def test_project_model_optional_fields():
    """Project model should work with only required fields."""
    from verifywise_mcp.models import Project, ProjectStatus

    p = Project(
        id="2",
        name="Minimal Project",
        status=ProjectStatus.DRAFT,
        created_at=NOW,
        updated_at=NOW,
    )

    assert p.description is None
    assert p.risk_level is None
    assert p.framework is None


def test_project_model_rejects_invalid_status():
    """Project model should raise ValidationError for an unknown status."""
    from pydantic import ValidationError

    from verifywise_mcp.models import Project

    with pytest.raises(ValidationError):
        Project(
            id="3",
            name="Bad Project",
            status="invalid_status",
            created_at=NOW,
            updated_at=NOW,
        )


# --- Risk ---


def test_risk_model_valid():
    """Risk model should accept a full valid payload."""
    from verifywise_mcp.models import Risk, RiskLevel

    r = Risk(
        id="r1",
        project_id="p1",
        title="Model bias in loan approval",
        description="Risk of demographic bias affecting approval rates",
        severity=RiskLevel.HIGH,
        status="open",
        owner="risk.manager@example.com",
        created_at=NOW,
    )

    assert r.id == "r1"
    assert r.severity == RiskLevel.HIGH
    assert r.owner == "risk.manager@example.com"
    assert r.due_date is None


def test_risk_model_optional_fields():
    """Risk model should work without optional owner and due_date."""
    from verifywise_mcp.models import Risk, RiskLevel

    r = Risk(
        id="r2",
        project_id="p1",
        title="Data leakage",
        description="Training data might leak PII",
        severity=RiskLevel.MEDIUM,
        status="open",
        created_at=NOW,
    )

    assert r.owner is None
    assert r.due_date is None


# --- Vendor ---


def test_vendor_model_valid():
    """Vendor model should accept a full valid payload."""
    from verifywise_mcp.models import RiskLevel, Vendor

    v = Vendor(
        id="v1",
        name="OpenAI",
        type="ai-provider",
        risk_score=75,
        risk_level=RiskLevel.HIGH,
        created_at=NOW,
        updated_at=NOW,
    )

    assert v.id == "v1"
    assert v.risk_score == 75


def test_vendor_model_optional_fields():
    """Vendor model should work with minimal fields."""
    from verifywise_mcp.models import Vendor

    v = Vendor(
        id="v2",
        name="Small Vendor",
        created_at=NOW,
        updated_at=NOW,
    )

    assert v.type is None
    assert v.risk_score is None
    assert v.risk_level is None


# --- ComplianceControl ---


def test_compliance_control_model_valid():
    """ComplianceControl model should accept a full valid payload."""
    from verifywise_mcp.models import ComplianceControl

    c = ComplianceControl(
        id="c1",
        framework="eu-ai-act",
        subclause="Article 10",
        title="Data governance",
        description="Requirements for data governance practices",
        status="in_progress",
    )

    assert c.framework == "eu-ai-act"
    assert c.evidence_count == 0
    assert c.last_reviewed is None


# --- AIModel ---


def test_ai_model_valid():
    """AIModel model should accept a full valid payload."""
    from verifywise_mcp.models import AIModel

    m = AIModel(
        id="m1",
        name="GPT-4o",
        provider="OpenAI",
        type="llm",
        version="2024-05",
        created_at=NOW,
        updated_at=NOW,
    )

    assert m.name == "GPT-4o"
    assert m.version == "2024-05"


def test_ai_model_optional_fields():
    """AIModel model should work with minimal fields."""
    from verifywise_mcp.models import AIModel

    m = AIModel(
        id="m2",
        name="Custom Model",
        created_at=NOW,
        updated_at=NOW,
    )

    assert m.provider is None
    assert m.type is None
    assert m.version is None
