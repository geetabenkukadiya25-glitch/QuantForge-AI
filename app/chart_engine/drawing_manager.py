"""Manages a collection of drawing objects and renders them onto a figure.

Independent of `ChartEngine`: it only needs a `go.Figure` to draw onto,
so it can be exercised standalone (including in tests) against a bare
`go.Figure()`.
"""

import plotly.graph_objects as go

from app.chart_engine.drawing_objects import DrawingObject


class DrawingManager:
    """Tracks drawing objects and applies them to a Plotly figure."""

    def __init__(self) -> None:
        self._drawings: list[DrawingObject] = []

    def add(self, drawing: DrawingObject) -> int:
        """Add a drawing and return its index (usable with `remove`)."""
        self._drawings.append(drawing)
        return len(self._drawings) - 1

    def remove(self, index: int) -> None:
        """Remove the drawing at `index`.

        Raises:
            IndexError: if `index` is out of range.
        """
        del self._drawings[index]

    def clear(self) -> None:
        """Remove all drawings."""
        self._drawings.clear()

    def list(self) -> list[DrawingObject]:
        """Return all drawings, in the order they were added."""
        return list(self._drawings)

    def render(self, fig: go.Figure) -> go.Figure:
        """Apply every drawing's shapes/annotations onto `fig` and return it."""
        for drawing in self._drawings:
            for shape in drawing.to_shapes():
                fig.add_shape(**shape)
            for annotation in drawing.to_annotations():
                fig.add_annotation(**annotation)
        return fig
