"""Rolling Standard Deviation.

Not provided as a named class by the `ta` library -- computed directly
via pandas' rolling standard deviation, a universal statistical formula.
"""

import pandas as pd

from app.indicator_engine.base import BaseIndicator
from app.indicator_engine.context import IndicatorContext
from app.indicator_engine.metadata import IndicatorMetadata, ParameterSpec


class StandardDeviationIndicator(BaseIndicator):
    """Rolling standard deviation of the close price."""

    @classmethod
    def metadata(cls) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="Standard Deviation",
            category="Volatility",
            description="Rolling standard deviation of the close price.",
            inputs=("Close",),
            outputs=("StdDev",),
            parameters=(
                ParameterSpec("window", "int", default=20, minimum=1),
            ),
        )

    def _calculate(self, context: IndicatorContext) -> dict[str, pd.Series]:
        std = context.data["Close"].rolling(self.params["window"]).std()
        return {"StdDev": std}
