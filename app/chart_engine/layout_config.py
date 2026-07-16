"""Rendering configuration for the chart engine.

`ChartConfig` is the single object every chart class reads its display
settings from -- no chart class hardcodes colors, sizes, or interaction
modes directly.
"""

from dataclasses import dataclass

# Fullscreen is a browser/UI-level concept; the chart engine approximates
# it by rendering at a taller height. The actual fullscreen toggle is a
# Streamlit-level concern (see app/ui/pages).
_DEFAULT_HEIGHT = 600
_FULLSCREEN_HEIGHT = 900


@dataclass
class ChartConfig:
    """Visual and interaction settings for a rendered chart."""

    theme: str = "dark"
    show_volume: bool = True
    show_crosshair: bool = True
    dragmode: str = "pan"  # "pan" | "zoom"
    autoscale: bool = True
    height: int = _DEFAULT_HEIGHT
    width: int | None = None
    fullscreen: bool = False
    title: str | None = None

    def __post_init__(self) -> None:
        if self.dragmode not in {"pan", "zoom"}:
            raise ValueError(f"dragmode must be 'pan' or 'zoom', got {self.dragmode!r}")

    @property
    def resolved_height(self) -> int:
        """Effective figure height, accounting for `fullscreen`."""
        return _FULLSCREEN_HEIGHT if self.fullscreen else self.height
