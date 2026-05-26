"""testboat strategy — create and validate test strategy YAML."""

from __future__ import annotations
from testboat.commands.active import active_dir

from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError, field_validator

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

STRATEGY_FILE = "strategy.yaml"
STRATEGY_DIR = ""


class Likelihood(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class StrategyStatus(str, Enum):
    draft = "draft"
    in_review = "in-review"
    approved = "approved"


class Scope(BaseModel):
    in_scope: list[str]
    out_scope: list[str]


class RiskItem(BaseModel):
    area: str
    likelihood: Likelihood
    impact: Likelihood
    approach: str


class SeverityItem(BaseModel):
    level: str
    description: str
    acceptable: int


class Metrics(BaseModel):
    severity: list[SeverityItem]

    @field_validator("severity")
    @classmethod
    def at_least_one_severity(cls, v: list[SeverityItem]) -> list[SeverityItem]:
        if not v:
            raise ValueError("metrics.severity must have at least one entry")
        return v


class Environment(BaseModel):
    name: str
    purpose: str


class Strategy(BaseModel):
    release: str
    status: StrategyStatus
    scope: Scope
    risk_matrix: list[RiskItem]
    test_pyramid: dict[str, Any]
    environments: list[Environment]
    entry_criteria: list[str]
    exit_criteria: list[str]
    metrics: Metrics

    @field_validator("risk_matrix")
    @classmethod
    def risk_matrix_not_empty(cls, v: list[RiskItem]) -> list[RiskItem]:
        if not v:
            raise ValueError("risk_matrix must have at least one entry")
        return v


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

TEMPLATE: dict[str, Any] = {
    "release": "<version>",
    "status": "draft",
    "scope": {
        "in_scope": ["<feature or requirement>"],
        "out_scope": ["<excluded area>"],
    },
    "risk_matrix": [
        {
            "area": "<high-risk area, e.g. payment>",
            "likelihood": "high",
            "impact": "high",
            "approach": "unit + API automation + E2E critical path + exploratory",
        },
        {
            "area": "<low-risk area, e.g. about page>",
            "likelihood": "low",
            "impact": "low",
            "approach": "smoke test only",
        },
    ],
    "test_pyramid": {
        "unit": {"owner": "dev", "coverage_target": "80%"},
        "api": {"tool": "playwright"},
        "e2e": {"tool": "playwright", "focus": "critical user journeys"},
        "performance": {"tool": "jmeter", "phase": "staging"},
        "security": {"tool": "zap", "phase": "pre-release"},
        "mobile": {"tool": "maestro"},
    },
    "environments": [
        {"name": "staging", "purpose": "functional testing"},
    ],
    "entry_criteria": [
        "requirements doc reviewed and signed off",
        "dev self-test passed, unit coverage >= 80%",
        "smoke test 100% pass",
    ],
    "exit_criteria": [
        "all P0/P1 bugs fixed and verified closed",
        "remaining low-severity bugs have PO risk acceptance in writing",
    ],
    "metrics": {
        "severity": [
            {"level": "P0", "description": "system crash / data loss", "acceptable": 0},
            {"level": "P1", "description": "core feature unavailable", "acceptable": 0},
            {"level": "P2", "description": "major feature degraded", "acceptable": 3},
            {"level": "P3", "description": "minor issue / cosmetic", "acceptable": 10},
        ]
    },
}


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

def _strategy_path(testboat_root: Path) -> Path:
    return active_dir(testboat_root) /  STRATEGY_FILE


def create_strategy(testboat_root: Path) -> Path:
    """Write strategy.yaml template under .testboat/draft/strategy/.

    Idempotent: overwrites if already exists.
    Returns the written file path.
    """
    path = _strategy_path(testboat_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(TEMPLATE, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path


def validate_strategy(testboat_root: Path) -> list[str]:
    """Validate strategy.yaml against the Strategy schema.

    Returns a list of error strings (empty = valid).
    Raises FileNotFoundError if strategy.yaml does not exist.
    """
    path = _strategy_path(testboat_root)
    if not path.exists():
        raise FileNotFoundError(
            f"strategy.yaml not found at {path}. Run `testboat strategy create` first."
        )

    raw = yaml.safe_load(path.read_text(encoding="utf-8"))

    try:
        Strategy.model_validate(raw)
        return []
    except ValidationError as exc:
        return [f"{e['loc']}: {e['msg']}" for e in exc.errors()]
