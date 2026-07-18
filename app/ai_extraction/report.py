"""A queryable, presentation-oriented view over a completed `ExtractionResult`.

`ExtractionReport` never mutates the result or re-runs anything -- it
only presents it (e.g. as `pandas.DataFrame`s for the Extraction
Dashboard's mentions/confidence/missing-information/statistics views),
mirroring `app.research_engine.report.ResearchReport`'s role.
"""

import pandas as pd

from app.ai_extraction.models import ExtractionResult


class ExtractionReport:
    """Read-only, queryable wrapper around one `ExtractionResult`."""

    def __init__(self, result: ExtractionResult) -> None:
        self._result = result

    @property
    def result(self) -> ExtractionResult:
        return self._result

    def indicators_table(self) -> pd.DataFrame:
        return pd.DataFrame([m.model_dump() for m in self._result.indicators])

    def detectors_table(self) -> pd.DataFrame:
        return pd.DataFrame([m.model_dump() for m in self._result.detectors])

    def entry_rules_table(self) -> pd.DataFrame:
        return pd.DataFrame([m.model_dump() for m in self._result.entry_rules])

    def exit_rules_table(self) -> pd.DataFrame:
        return pd.DataFrame([m.model_dump() for m in self._result.exit_rules])

    def risk_table(self) -> pd.DataFrame:
        return pd.DataFrame([m.model_dump() for m in self._result.risk_mentions])

    def sessions_table(self) -> pd.DataFrame:
        return pd.DataFrame([m.model_dump() for m in self._result.sessions])

    def timeframes_table(self) -> pd.DataFrame:
        return pd.DataFrame([m.model_dump() for m in self._result.timeframes])

    def parameters_table(self) -> pd.DataFrame:
        return pd.DataFrame([m.model_dump() for m in self._result.parameters])

    def confidence_table(self) -> pd.DataFrame:
        return pd.DataFrame([c.model_dump() for c in self._result.confidence.category_confidences])

    def missing_information_table(self) -> pd.DataFrame:
        return pd.DataFrame([w.model_dump() for w in self._result.missing_information.warnings])

    def statistics(self) -> dict:
        """At-a-glance counts across every extracted category."""
        return {
            "strategy_name": self._result.strategy_name,
            "source_type": self._result.metadata.source_type,
            "indicator_count": len(self._result.indicators),
            "detector_count": len(self._result.detectors),
            "entry_rule_count": len(self._result.entry_rules),
            "exit_rule_count": len(self._result.exit_rules),
            "risk_mention_count": len(self._result.risk_mentions),
            "session_count": len(self._result.sessions),
            "timeframe_count": len(self._result.timeframes),
            "parameter_count": len(self._result.parameters),
            "unknown_item_count": len(self._result.unknown_items),
            "missing_item_count": len(self._result.missing_information.missing_items),
            "overall_confidence": self._result.confidence.overall_confidence,
            "sdl_valid": self._result.sdl_validation.is_valid,
            "checksum": self._result.checksum,
        }

    def executive_summary(self) -> str:
        stats = self.statistics()
        return (
            f"'{stats['strategy_name']}' extracted from {stats['source_type']}: "
            f"{stats['indicator_count']} indicator(s), {stats['detector_count']} detector(s), "
            f"{stats['entry_rule_count']} entry rule(s), {stats['exit_rule_count']} exit rule(s), "
            f"{stats['risk_mention_count']} risk statement(s). Overall confidence: {stats['overall_confidence']:.0%}. "
            f"{stats['missing_item_count']} item(s) missing -- human review required."
        )
