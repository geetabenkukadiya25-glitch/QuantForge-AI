"""All built-in indicator implementations, grouped by category.

`ALL_INDICATORS` is the single list `IndicatorRegistry.register_builtins`
uses to bootstrap the registry -- adding a new indicator means adding it
to its category module's `__all__` and to the list below, nowhere else.
"""

from app.indicator_engine.indicators.momentum import (
    CCIIndicator,
    ROCIndicator,
    RSIIndicator,
    StochasticRSIIndicator,
    WilliamsRIndicator,
)
from app.indicator_engine.indicators.moving_average import (
    EMAIndicator,
    SMAIndicator,
    VWMAIndicator,
    WMAIndicator,
)
from app.indicator_engine.indicators.price import (
    MedianPriceIndicator,
    TypicalPriceIndicator,
    WeightedCloseIndicator,
)
from app.indicator_engine.indicators.range_ import TrueRangeIndicator
from app.indicator_engine.indicators.trend import ADXIndicator, MACDIndicator, ParabolicSARIndicator
from app.indicator_engine.indicators.volatility import (
    ATRIndicator,
    BollingerBandsIndicator,
    KeltnerChannelsIndicator,
    StandardDeviationIndicator,
)
from app.indicator_engine.indicators.volume import (
    ChaikinMoneyFlowIndicator,
    MFIIndicator,
    OBVIndicator,
    VWAPIndicator,
)

ALL_INDICATORS = [
    # Moving Average
    SMAIndicator,
    EMAIndicator,
    WMAIndicator,
    VWMAIndicator,
    # Trend
    MACDIndicator,
    ADXIndicator,
    ParabolicSARIndicator,
    # Momentum
    RSIIndicator,
    StochasticRSIIndicator,
    CCIIndicator,
    WilliamsRIndicator,
    ROCIndicator,
    # Volatility
    ATRIndicator,
    StandardDeviationIndicator,
    BollingerBandsIndicator,
    KeltnerChannelsIndicator,
    # Volume
    OBVIndicator,
    VWAPIndicator,
    MFIIndicator,
    ChaikinMoneyFlowIndicator,
    # Price
    TypicalPriceIndicator,
    MedianPriceIndicator,
    WeightedCloseIndicator,
    # Range
    TrueRangeIndicator,
]

__all__ = [cls.__name__ for cls in ALL_INDICATORS] + ["ALL_INDICATORS"]
