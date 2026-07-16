"""Exports a rendered chart to PNG, SVG, or HTML."""

from pathlib import Path

import plotly.graph_objects as go

from app.chart_engine.exceptions import ExportError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ExportManager:
    """Writes a `go.Figure` to a static image or standalone HTML file."""

    def to_png(self, fig: go.Figure, file_path: str | Path, scale: float = 2.0) -> Path:
        """Export `fig` as a PNG. Requires the `kaleido` package."""
        return self._write_image(fig, file_path, "png", scale)

    def to_svg(self, fig: go.Figure, file_path: str | Path, scale: float = 1.0) -> Path:
        """Export `fig` as an SVG. Requires the `kaleido` package."""
        return self._write_image(fig, file_path, "svg", scale)

    def to_html(self, fig: go.Figure, file_path: str | Path, include_plotlyjs: str = "cdn") -> Path:
        """Export `fig` as a standalone (or CDN-linked) interactive HTML page."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fig.write_html(path, include_plotlyjs=include_plotlyjs)
        except Exception as exc:
            raise ExportError(f"Could not export chart to HTML '{path}': {exc}") from exc
        logger.info("Exported chart to HTML: %s", path)
        return path

    def _write_image(self, fig: go.Figure, file_path: str | Path, fmt: str, scale: float) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fig.write_image(path, format=fmt, scale=scale)
        except Exception as exc:
            raise ExportError(
                f"Could not export chart to {fmt.upper()} '{path}': {exc}. "
                "Static image export requires the 'kaleido' package."
            ) from exc
        logger.info("Exported chart to %s: %s", fmt.upper(), path)
        return path
