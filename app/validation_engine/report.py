"""A queryable, presentation-oriented view over a completed `ValidationResult`.

`ValidationReport` never mutates the result or re-runs anything -- it
only presents it (e.g. as `pandas.DataFrame`s for the Streamlit Walk
Forward / Monte Carlo / Robustness / Confidence viewers), mirroring
`app.optimization_engine.report.OptimizationReport`'s role.
"""

import pandas as pd

from app.validation_engine.models import ValidationResult


class ValidationReport:
    """Read-only, queryable wrapper around one `ValidationResult`."""

    def __init__(self, result: ValidationResult) -> None:
        self._result = result

    @property
    def result(self) -> ValidationResult:
        return self._result

    def walk_forward_report(self) -> pd.DataFrame:
        """One row per window: boundaries, in/out-of-sample scores, pass/fail status."""
        wf = self._result.walk_forward_result
        if wf is None:
            return pd.DataFrame()
        rows = [
            {
                "window_index": o.window.window_index,
                "in_sample_start": o.window.in_sample_start_datetime,
                "in_sample_end": o.window.in_sample_end_datetime,
                "out_of_sample_start": o.window.out_of_sample_start_datetime,
                "out_of_sample_end": o.window.out_of_sample_end_datetime,
                "in_sample_score": o.in_sample_score,
                "out_of_sample_score": o.out_of_sample_score,
                "status": o.status.value,
                "succeeded": o.succeeded,
                "error_message": o.error_message,
            }
            for o in wf.windows
        ]
        return pd.DataFrame(rows)

    def monte_carlo_report(self) -> pd.DataFrame:
        """One row per Monte Carlo iteration."""
        mc = self._result.monte_carlo_result
        if mc is None:
            return pd.DataFrame()
        return pd.DataFrame(
            [{"iteration": p.iteration_index, "final_equity": p.final_equity, "net_profit": p.net_profit, "max_drawdown": p.max_drawdown} for p in mc.distribution]
        )

    def robustness_report(self) -> dict:
        score = self._result.robustness_score
        return score.model_dump(mode="json") if score else {}

    def confidence_report(self) -> dict:
        score = self._result.confidence_score
        return score.model_dump(mode="json") if score else {}

    def stability_report(self) -> dict:
        score = self._result.stability_score
        return score.model_dump(mode="json") if score else {}

    def validation_summary(self) -> dict:
        """A single flat dict combining every top-level score -- the "at a glance" summary."""
        wf = self._result.walk_forward_result
        mc = self._result.monte_carlo_result
        return {
            "strategy_id": self._result.metadata.strategy_id,
            "candidate_id": self._result.metadata.candidate_id,
            "walk_forward_pass_rate": wf.pass_rate if wf else None,
            "walk_forward_total_windows": wf.total_windows if wf else None,
            "monte_carlo_probability_of_profit": mc.probability_of_profit if mc else None,
            "monte_carlo_confidence_interval": (mc.confidence_interval_low, mc.confidence_interval_high) if mc else None,
            "robustness_score": self._result.robustness_score.robustness_score if self._result.robustness_score else None,
            "confidence_score": self._result.confidence_score.confidence_score if self._result.confidence_score else None,
            "stability_score": self._result.stability_score.stability_score if self._result.stability_score else None,
            "checksum": self._result.checksum,
        }
