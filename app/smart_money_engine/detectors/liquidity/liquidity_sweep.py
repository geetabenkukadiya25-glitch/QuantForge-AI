"""Liquidity Sweep detector: a wick beyond a liquidity pool that closes back through it."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.detectors.liquidity.liquidity_pool import LiquidityPoolDetector
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class LiquiditySweepDetector(BaseSMCDetector):
    """Price wicks beyond a liquidity pool level, then closes back on the other side."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Liquidity Sweep",
            category="Liquidity",
            description="Price wicks through a liquidity pool level and closes back through it (a stop-hunt).",
            inputs=("High", "Low", "Close"),
            outputs=("liquidity_sweep",),
            parameters=(
                ParameterSpec("left_bars", "int", default=10, minimum=1),
                ParameterSpec("right_bars", "int", default=10, minimum=1),
                ParameterSpec("tolerance_pct", "float", default=0.05, minimum=0.0),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        left, right = self.params["left_bars"], self.params["right_bars"]
        tolerance_pct = self.params["tolerance_pct"]
        data = context.data
        pools = LiquidityPoolDetector(
            left_bars=left, right_bars=right, tolerance_pct=tolerance_pct
        ).detect(context)

        detections: list[SMCDetection] = []
        for pool in pools.detections:
            sweep_index = self._find_sweep(context, pool)
            if sweep_index is not None:
                is_buy_side = pool.label.startswith("Buy-side")
                detections.append(
                    SMCDetection(
                        index=sweep_index,
                        datetime=self._iso(context, sweep_index),
                        label="Liquidity Sweep (Buy-side)" if is_buy_side else "Liquidity Sweep (Sell-side)",
                        direction="bearish" if is_buy_side else "bullish",
                        price=pool.price,
                        notes=f"Swept liquidity pool originating at index {pool.index}.",
                    )
                )
        return sorted(detections, key=lambda d: d.index)

    @staticmethod
    def _find_sweep(context: SMCContext, pool: SMCDetection) -> int | None:
        data = context.data
        start = (pool.end_index if pool.end_index is not None else pool.index) + 1
        is_buy_side = pool.label.startswith("Buy-side")
        for i in range(start, len(data)):
            high, low, close = float(data["High"].iloc[i]), float(data["Low"].iloc[i]), float(data["Close"].iloc[i])
            if is_buy_side and high > pool.price and close < pool.price:
                return i
            if not is_buy_side and low < pool.price and close > pool.price:
                return i
        return None
