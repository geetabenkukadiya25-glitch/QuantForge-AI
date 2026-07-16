"""Equal Highs detector: clusters of swing highs within a price tolerance."""

from app.smart_money_engine.base import BaseSMCDetector
from app.smart_money_engine.context import SMCContext
from app.smart_money_engine.helpers import find_swing_highs
from app.smart_money_engine.metadata import ParameterSpec, SMCMetadata
from app.smart_money_engine.result import SMCDetection


class EqualHighDetector(BaseSMCDetector):
    """Two or more swing highs whose prices sit within a small tolerance of each other."""

    @classmethod
    def metadata(cls) -> SMCMetadata:
        return SMCMetadata(
            name="Equal High",
            category="Liquidity",
            description="Clusters of swing highs within a small price tolerance of each other.",
            inputs=("High",),
            outputs=("equal_high",),
            parameters=(
                ParameterSpec("left_bars", "int", default=5, minimum=1),
                ParameterSpec("right_bars", "int", default=5, minimum=1),
                ParameterSpec("tolerance_pct", "float", default=0.05, minimum=0.0),
            ),
        )

    def _detect(self, context: SMCContext) -> list[SMCDetection]:
        left, right = self.params["left_bars"], self.params["right_bars"]
        tolerance_pct = self.params["tolerance_pct"]
        data = context.data
        swing_indices = find_swing_highs(data, left, right)
        prices = {i: float(data["High"].iloc[i]) for i in swing_indices}

        detections: list[SMCDetection] = []
        cluster: list[int] = []
        for index in swing_indices:
            if not cluster:
                cluster = [index]
                continue
            reference_price = prices[cluster[0]]
            if abs(prices[index] - reference_price) / reference_price * 100 <= tolerance_pct:
                cluster.append(index)
            else:
                if len(cluster) >= 2:
                    detections.append(self._build(context, prices, cluster))
                cluster = [index]
        if len(cluster) >= 2:
            detections.append(self._build(context, prices, cluster))
        return detections

    def _build(self, context: SMCContext, prices: dict[int, float], cluster: list[int]) -> SMCDetection:
        avg_price = sum(prices[i] for i in cluster) / len(cluster)
        return SMCDetection(
            index=cluster[0],
            datetime=self._iso(context, cluster[0]),
            end_index=cluster[-1],
            end_datetime=self._iso(context, cluster[-1]),
            label="Equal Highs",
            price=avg_price,
            notes=f"{len(cluster)} swing high(s) clustered near {avg_price:.5f}.",
        )
