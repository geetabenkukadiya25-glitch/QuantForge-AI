"""Builds the generated EA's `input` parameter declarations.

Always emits the standard risk/identity inputs from
`EAGeneratorConfiguration`. When an `OptimizationResult` is attached to
the context, also emits one additional, clearly-labeled `input` per
optimized parameter from that result's already-computed best candidate
-- read-only reuse, never re-running the Optimization Engine.
"""

import json
import re

from app.ea_generator.context import EAGeneratorContext
from app.ea_generator.models import GeneratedInput

_SANITIZE_RE = re.compile(r"[^0-9A-Za-z_]+")


def _sanitize(name: str) -> str:
    cleaned = _SANITIZE_RE.sub("_", name).strip("_")
    return cleaned or "param"


def _infer_mql_type(value: object) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "double"
    return "string"


def _literal(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


class ParameterCodeGenerator:
    """Builds the `GeneratedInput` list for one EA generation context."""

    def generate(self, context: EAGeneratorContext) -> tuple[GeneratedInput, ...]:
        cfg = context.configuration
        inputs: list[GeneratedInput] = [
            GeneratedInput(name="InpMagicNumber", mql_type="int", default_value=str(cfg.magic_number), comment="Unique EA identifier"),
            GeneratedInput(name="InpLotSize", mql_type="double", default_value=str(cfg.lot_size), comment="Fixed lot size per trade"),
            GeneratedInput(name="InpStopLossPoints", mql_type="double", default_value=str(cfg.stop_loss_points), comment="Stop loss, in points (0 = disabled)"),
            GeneratedInput(name="InpTakeProfitPoints", mql_type="double", default_value=str(cfg.take_profit_points), comment="Take profit, in points (0 = disabled)"),
            GeneratedInput(name="InpMaxOpenPositions", mql_type="int", default_value=str(cfg.max_open_positions), comment="Maximum concurrent open positions"),
        ]

        best_params = self._best_candidate_parameters(context)
        for key in sorted(best_params):
            inputs.append(
                GeneratedInput(
                    name=f"InpOpt_{_sanitize(key)}",
                    mql_type=_infer_mql_type(best_params[key]),
                    default_value=_literal(best_params[key]),
                    comment=f"Optimized parameter '{key}' (OptimizationResult best candidate)",
                )
            )

        return tuple(inputs)

    @staticmethod
    def _best_candidate_parameters(context: EAGeneratorContext) -> dict:
        optimization_result = context.optimization_result
        if optimization_result is None or not optimization_result.best_candidate_id:
            return {}
        best = next((c for c in optimization_result.candidates if c.candidate_id == optimization_result.best_candidate_id), None)
        if best is None:
            return {}
        return json.loads(best.parameters_json)
