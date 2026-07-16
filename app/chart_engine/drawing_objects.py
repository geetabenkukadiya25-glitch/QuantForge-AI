"""Drawing tool object model.

Each drawing tool is a plain, independent dataclass that knows how to
turn itself into Plotly shape/annotation dicts. None of them depend on
`ChartEngine` or any other chart class -- `DrawingManager` (or any other
caller) can render them onto any `go.Figure`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import pandas as pd

Timestamp = pd.Timestamp | str


def _ts(value: Timestamp) -> str:
    """Normalize a timestamp-like value to an ISO string.

    Plotly's own trace serialization accepts `pd.Timestamp` directly, but
    manually-built shape/annotation dicts are also passed through
    `kaleido`'s stricter JSON encoder during static export, which cannot
    serialize `pd.Timestamp` objects -- so every x-coordinate here is
    normalized to a plain string up front.
    """
    return pd.Timestamp(value).isoformat()


class DrawingObject(ABC):
    """Common contract every drawing tool implements."""

    @abstractmethod
    def to_shapes(self) -> list[dict[str, Any]]:
        """Return Plotly `layout.shapes`-compatible dicts (may be empty)."""

    def to_annotations(self) -> list[dict[str, Any]]:
        """Return Plotly `layout.annotations`-compatible dicts (default: none)."""
        return []


@dataclass
class HorizontalLine(DrawingObject):
    """A horizontal price level line spanning the full chart width."""

    price: float
    color: str = "#2962FF"
    width: float = 1.5
    dash: str = "solid"
    label: str | None = None

    def to_shapes(self) -> list[dict[str, Any]]:
        return [
            dict(
                type="line",
                xref="paper",
                x0=0,
                x1=1,
                yref="y",
                y0=self.price,
                y1=self.price,
                line=dict(color=self.color, width=self.width, dash=self.dash),
            )
        ]

    def to_annotations(self) -> list[dict[str, Any]]:
        if not self.label:
            return []
        return [
            dict(
                xref="paper",
                x=1.0,
                y=self.price,
                text=self.label,
                showarrow=False,
                xanchor="left",
                font=dict(color=self.color),
            )
        ]


@dataclass
class VerticalLine(DrawingObject):
    """A vertical time marker line spanning the full chart height."""

    timestamp: Timestamp
    color: str = "#2962FF"
    width: float = 1.5
    dash: str = "dash"
    label: str | None = None

    def to_shapes(self) -> list[dict[str, Any]]:
        return [
            dict(
                type="line",
                xref="x",
                x0=_ts(self.timestamp),
                x1=_ts(self.timestamp),
                yref="paper",
                y0=0,
                y1=1,
                line=dict(color=self.color, width=self.width, dash=self.dash),
            )
        ]

    def to_annotations(self) -> list[dict[str, Any]]:
        if not self.label:
            return []
        return [
            dict(
                xref="x",
                x=_ts(self.timestamp),
                yref="paper",
                y=1.0,
                text=self.label,
                showarrow=False,
                yanchor="bottom",
                font=dict(color=self.color),
            )
        ]


@dataclass
class TrendLine(DrawingObject):
    """A freeform line between two (time, price) points."""

    x0: Timestamp
    y0: float
    x1: Timestamp
    y1: float
    color: str = "#2962FF"
    width: float = 1.5
    dash: str = "solid"

    def to_shapes(self) -> list[dict[str, Any]]:
        return [
            dict(
                type="line",
                xref="x",
                yref="y",
                x0=_ts(self.x0),
                y0=self.y0,
                x1=_ts(self.x1),
                y1=self.y1,
                line=dict(color=self.color, width=self.width, dash=self.dash),
            )
        ]


@dataclass
class Rectangle(DrawingObject):
    """A filled/outlined rectangle between two (time, price) corners."""

    x0: Timestamp
    y0: float
    x1: Timestamp
    y1: float
    color: str = "#2962FF"
    fill_opacity: float = 0.15
    border_width: float = 1.0

    def to_shapes(self) -> list[dict[str, Any]]:
        return [
            dict(
                type="rect",
                xref="x",
                yref="y",
                x0=_ts(self.x0),
                y0=self.y0,
                x1=_ts(self.x1),
                y1=self.y1,
                fillcolor=self.color,
                opacity=self.fill_opacity,
                line=dict(color=self.color, width=self.border_width),
            )
        ]


@dataclass
class TextLabel(DrawingObject):
    """A free text label anchored at a (time, price) point."""

    x: Timestamp
    y: float
    text: str
    color: str = "#D1D4DC"
    size: int = 12

    def to_shapes(self) -> list[dict[str, Any]]:
        return []

    def to_annotations(self) -> list[dict[str, Any]]:
        return [
            dict(
                xref="x",
                yref="y",
                x=_ts(self.x),
                y=self.y,
                text=self.text,
                showarrow=False,
                font=dict(color=self.color, size=self.size),
            )
        ]


@dataclass
class Arrow(DrawingObject):
    """An arrow pointing from (x0, y0) to (x1, y1)."""

    x0: Timestamp
    y0: float
    x1: Timestamp
    y1: float
    color: str = "#2962FF"

    def to_shapes(self) -> list[dict[str, Any]]:
        return []

    def to_annotations(self) -> list[dict[str, Any]]:
        return [
            dict(
                xref="x",
                yref="y",
                x=_ts(self.x1),
                y=self.y1,
                axref="x",
                ayref="y",
                ax=_ts(self.x0),
                ay=self.y0,
                showarrow=True,
                arrowhead=3,
                arrowwidth=2,
                arrowcolor=self.color,
                text="",
            )
        ]


@dataclass
class RiskRewardBox(DrawingObject):
    """A risk/reward visualization: a loss zone and a profit zone with a ratio label."""

    entry: float
    stop: float
    target: float
    x0: Timestamp
    x1: Timestamp
    risk_color: str = "#EF5350"
    reward_color: str = "#26A69A"

    @property
    def risk_reward_ratio(self) -> float:
        """Reward-to-risk ratio; 0.0 if entry == stop (undefined risk)."""
        risk = abs(self.entry - self.stop)
        if risk == 0:
            return 0.0
        return abs(self.target - self.entry) / risk

    def to_shapes(self) -> list[dict[str, Any]]:
        common = dict(
            type="rect", xref="x", yref="y", x0=_ts(self.x0), x1=_ts(self.x1), line=dict(width=0)
        )
        return [
            dict(common, y0=self.entry, y1=self.stop, fillcolor=self.risk_color, opacity=0.2),
            dict(common, y0=self.entry, y1=self.target, fillcolor=self.reward_color, opacity=0.2),
        ]

    def to_annotations(self) -> list[dict[str, Any]]:
        return [
            dict(
                xref="x",
                yref="y",
                x=_ts(self.x1),
                y=self.target,
                text=f"R:R {self.risk_reward_ratio:.2f}",
                showarrow=False,
                font=dict(color=self.reward_color),
                xanchor="left",
            )
        ]


@dataclass
class MeasurementTool(DrawingObject):
    """Measures price and time distance between two points."""

    x0: Timestamp
    y0: float
    x1: Timestamp
    y1: float
    color: str = "#B2B5BE"

    @property
    def price_delta(self) -> float:
        return self.y1 - self.y0

    @property
    def price_delta_pct(self) -> float:
        return (self.price_delta / self.y0 * 100) if self.y0 else 0.0

    @property
    def time_delta(self) -> pd.Timedelta:
        return pd.Timestamp(self.x1) - pd.Timestamp(self.x0)

    def to_shapes(self) -> list[dict[str, Any]]:
        return [
            dict(
                type="line",
                xref="x",
                yref="y",
                x0=_ts(self.x0),
                y0=self.y0,
                x1=_ts(self.x1),
                y1=self.y1,
                line=dict(color=self.color, width=1.5, dash="dot"),
            )
        ]

    def to_annotations(self) -> list[dict[str, Any]]:
        bars = self.time_delta
        return [
            dict(
                xref="x",
                yref="y",
                x=_ts(self.x1),
                y=self.y1,
                text=f"Δ {self.price_delta:+.5f} ({self.price_delta_pct:+.2f}%) / {bars}",
                showarrow=False,
                font=dict(color=self.color),
                xanchor="left",
            )
        ]
