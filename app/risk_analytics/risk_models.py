"""Data classes for Risk Analytics (Phase 17.7). Every analytic module
returns one of these; `RiskReport` is the single persisted document
(mirrors `app.workflow.workflow_models`' hand-rolled JSON pattern).

Sub-results below are flat dataclasses of JSON-primitive fields (str/int/
float/bool/list/dict) by design, so `dataclasses.asdict`/`Cls(**data)`
round-trip them without custom logic -- only `RiskReport` itself (which
carries a `datetime`/`enum`) needs explicit `to_dict`/`from_dict`.
"""

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class RiskReportKind(str, Enum):
    RISK_SUMMARY = "RISK_SUMMARY"
    PORTFOLIO_SUMMARY = "PORTFOLIO_SUMMARY"
    STRATEGY_SUMMARY = "STRATEGY_SUMMARY"
    EXPOSURE_REPORT = "EXPOSURE_REPORT"
    VAR_REPORT = "VAR_REPORT"
    SCENARIO_REPORT = "SCENARIO_REPORT"
    MONTE_CARLO_REPORT = "MONTE_CARLO_REPORT"
    INSTITUTIONAL_RISK_REPORT = "INSTITUTIONAL_RISK_REPORT"


class RegimeKind(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    CUSTOM = "CUSTOM"


class VarMethod(str, Enum):
    HISTORICAL = "HISTORICAL"
    PARAMETRIC = "PARAMETRIC"
    MONTE_CARLO = "MONTE_CARLO"


def _asdict(obj: Any) -> dict:
    return dataclasses.asdict(obj)


@dataclass(frozen=True)
class ConsecutiveStreaks:
    max_consecutive_wins: int
    max_consecutive_losses: int
    current_streak: int  # positive = winning streak, negative = losing streak, 0 = none

    to_dict = _asdict


@dataclass(frozen=True)
class WinLossDistribution:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    average_risk_reward: float | None

    to_dict = _asdict


@dataclass(frozen=True)
class DrawdownEpisode:
    start_index: int
    trough_index: int
    recovery_index: int | None  # None if never recovered within the run
    drawdown_pct: float
    recovery_time_bars: int | None


@dataclass(frozen=True)
class DrawdownAnalysis:
    max_drawdown: float
    max_drawdown_pct: float
    average_drawdown: float
    episodes: list[dict]  # DrawdownEpisode.to_dict()-shaped rows
    average_recovery_time_bars: float | None

    def to_dict(self) -> dict:
        return {
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "average_drawdown": self.average_drawdown,
            "episodes": self.episodes,
            "average_recovery_time_bars": self.average_recovery_time_bars,
        }


@dataclass(frozen=True)
class RiskMetrics:
    """Genuinely-new-derivation metrics (`risk_metrics.py`) -- never
    duplicates `PerformanceStatistics`' sharpe/sortino/calmar/profit_factor/
    expectancy, which are read directly off the source result instead."""

    kelly_percentage: float | None
    risk_of_ruin_pct: float | None
    exposure_pct: float | None

    to_dict = _asdict


@dataclass(frozen=True)
class VarResult:
    method: str  # VarMethod value
    confidence: float
    value: float  # positive magnitude = potential loss at this confidence

    to_dict = _asdict


@dataclass(frozen=True)
class CvarResult:
    confidence: float
    expected_shortfall: float
    tail_loss: float
    worst_case_average: float

    to_dict = _asdict


@dataclass(frozen=True)
class RegimeSegment:
    kind: str  # RegimeKind value
    start_index: int
    end_index: int

    to_dict = _asdict


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    trade_count: int
    net_profit: float
    win_rate: float
    average_trade_return: float

    to_dict = _asdict


@dataclass(frozen=True)
class MonteCarloRiskResult:
    iterations_run: int
    mean_net_profit: float
    median_net_profit: float
    std_net_profit: float
    worst_net_profit: float
    best_net_profit: float
    confidence_interval_low: float
    confidence_interval_high: float
    probability_of_profit: float
    probability_of_ruin: float
    ruin_threshold: float
    perturbed: bool  # True if random slippage/spread perturbation was applied

    to_dict = _asdict


@dataclass(frozen=True)
class CorrelationPairResult:
    label_a: str
    label_b: str
    correlation: float


@dataclass(frozen=True)
class CorrelationResult:
    axis: str  # "strategy" | "dataset" | "asset" | "timeframe"
    pairs: list[dict]  # CorrelationPairResult-shaped rows
    average_correlation: float

    def to_dict(self) -> dict:
        return {"axis": self.axis, "pairs": self.pairs, "average_correlation": self.average_correlation}


@dataclass(frozen=True)
class HeatmapResult:
    kind: str  # "monthly" | "weekly" | "daily" | "hourly" | "session" | "drawdown" | "risk"
    buckets: dict[str, float]

    to_dict = _asdict


@dataclass(frozen=True)
class ExposureEntryResult:
    symbol: str
    exposure_pct: float


@dataclass(frozen=True)
class RiskExposureResult:
    entries: list[dict]  # ExposureEntryResult-shaped rows
    total_exposure_pct: float

    def to_dict(self) -> dict:
        return {"entries": self.entries, "total_exposure_pct": self.total_exposure_pct}


class RiskAuditEventType(str, Enum):
    ANALYZED = "ANALYZED"
    REPORT_GENERATED = "REPORT_GENERATED"
    EXPORTED = "EXPORTED"
    DELETED = "DELETED"


@dataclass(frozen=True)
class RiskAuditEvent:
    event_type: RiskAuditEventType
    key: str
    timestamp: datetime

    def to_dict(self) -> dict:
        return {"event_type": self.event_type.value, "key": self.key, "timestamp": self.timestamp.isoformat()}

    @staticmethod
    def from_dict(data: dict) -> "RiskAuditEvent":
        return RiskAuditEvent(event_type=RiskAuditEventType(data["event_type"]), key=data["key"], timestamp=datetime.fromisoformat(data["timestamp"]))


@dataclass
class RiskReport:
    """The single persisted artifact: a named collection of analytic
    sections, each already-serialized to a plain dict by the producing
    module's own `to_dict()`. Durable independent of Job Manager's
    in-memory result retention -- see `risk_manager.py`."""

    id: str
    kind: RiskReportKind
    title: str
    source_description: str
    created_at: datetime
    sections: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "title": self.title,
            "source_description": self.source_description,
            "created_at": self.created_at.isoformat(),
            "sections": self.sections,
            "tags": list(self.tags),
        }

    @staticmethod
    def from_dict(data: dict) -> "RiskReport":
        return RiskReport(
            id=data["id"],
            kind=RiskReportKind(data["kind"]),
            title=data["title"],
            source_description=data["source_description"],
            created_at=datetime.fromisoformat(data["created_at"]),
            sections=dict(data.get("sections", {})),
            tags=list(data.get("tags", [])),
        )


@dataclass
class RiskManagerState:
    reports: dict[str, RiskReport] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"reports": {k: r.to_dict() for k, r in self.reports.items()}}

    @staticmethod
    def from_dict(data: dict) -> "RiskManagerState":
        return RiskManagerState(reports={k: RiskReport.from_dict(v) for k, v in data.get("reports", {}).items()})
