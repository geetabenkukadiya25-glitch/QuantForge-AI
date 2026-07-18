"""A queryable, presentation-oriented view over a completed `EAGeneratorResult`.

`EAGeneratorReport` never mutates the result or re-runs anything -- it
only presents it (e.g. as `pandas.DataFrame`s for the EA Generator
Dashboard), mirroring `app.portfolio_engine.report.PortfolioReport`'s role.
"""

import pandas as pd

from app.ea_generator.models import EAGeneratorResult


class EAGeneratorReport:
    """Read-only, queryable wrapper around one `EAGeneratorResult`."""

    def __init__(self, result: EAGeneratorResult) -> None:
        self._result = result

    @property
    def result(self) -> EAGeneratorResult:
        return self._result

    def summary(self) -> dict:
        return {
            "strategy_id": self._result.metadata.strategy_id,
            "output_filename": self._result.metadata.output_filename,
            "checksum": self._result.checksum,
            **self._result.statistics.model_dump(),
        }

    def inputs_table(self) -> pd.DataFrame:
        return pd.DataFrame([i.model_dump() for i in self._result.inputs])

    def indicators_table(self) -> pd.DataFrame:
        return pd.DataFrame([d.model_dump() for d in self._result.indicator_declarations])

    def risk_report(self) -> dict:
        return self._result.risk_parameters.model_dump()

    def filters_table(self) -> pd.DataFrame:
        return pd.DataFrame([b.model_dump() for b in self._result.trade_management.filters])

    def entry_rules_table(self) -> pd.DataFrame:
        return pd.DataFrame([b.model_dump() for b in self._result.trade_management.entry_rules])

    def exit_rules_table(self) -> pd.DataFrame:
        return pd.DataFrame([b.model_dump() for b in self._result.trade_management.exit_rules])

    def source_preview(self, max_lines: int = 50) -> str:
        """The first `max_lines` lines of the generated source, for a quick UI preview."""
        lines = self._result.source_code.splitlines()
        preview = lines[:max_lines]
        if len(lines) > max_lines:
            preview.append(f"// ... ({len(lines) - max_lines} more line(s))")
        return "\n".join(preview)
