"""All built-in Smart Money detector implementations, grouped by category.

`ALL_DETECTORS` is the single list `SMCRegistry.register_builtins` uses
to bootstrap the registry -- adding a new detector means adding it to
its category module's `__all__` and to the list below, nowhere else.
"""

from app.smart_money_engine.detectors.blocks import (
    BreakerBlockDetector,
    MitigationBlockDetector,
    OrderBlockDetector,
)
from app.smart_money_engine.detectors.imbalance import (
    BPRDetector,
    FVGDetector,
    IFVGDetector,
    VolumeImbalanceDetector,
)
from app.smart_money_engine.detectors.levels import (
    PreviousDayHighDetector,
    PreviousDayLowDetector,
    PreviousMonthHighDetector,
    PreviousMonthLowDetector,
    PreviousWeekHighDetector,
    PreviousWeekLowDetector,
    SessionHighDetector,
    SessionLowDetector,
)
from app.smart_money_engine.detectors.liquidity import (
    EqualHighDetector,
    EqualLowDetector,
    LiquidityPoolDetector,
    LiquiditySweepDetector,
)
from app.smart_money_engine.detectors.momentum import (
    DisplacementDetector,
    ImpulseMoveDetector,
    RetracementDetector,
)
from app.smart_money_engine.detectors.structure import (
    BOSDetector,
    CHoCHDetector,
    ExternalStructureDetector,
    InternalStructureDetector,
    MarketStructureDetector,
    SwingHighDetector,
    SwingLowDetector,
)
from app.smart_money_engine.detectors.zones import (
    DiscountZoneDetector,
    EquilibriumDetector,
    PremiumZoneDetector,
)

ALL_DETECTORS = [
    # Structure
    SwingHighDetector,
    SwingLowDetector,
    MarketStructureDetector,
    BOSDetector,
    CHoCHDetector,
    InternalStructureDetector,
    ExternalStructureDetector,
    # Liquidity
    EqualHighDetector,
    EqualLowDetector,
    LiquidityPoolDetector,
    LiquiditySweepDetector,
    # Blocks
    OrderBlockDetector,
    BreakerBlockDetector,
    MitigationBlockDetector,
    # Imbalance
    FVGDetector,
    IFVGDetector,
    BPRDetector,
    VolumeImbalanceDetector,
    # Zones
    PremiumZoneDetector,
    DiscountZoneDetector,
    EquilibriumDetector,
    # Momentum
    DisplacementDetector,
    ImpulseMoveDetector,
    RetracementDetector,
    # Levels
    SessionHighDetector,
    SessionLowDetector,
    PreviousDayHighDetector,
    PreviousDayLowDetector,
    PreviousWeekHighDetector,
    PreviousWeekLowDetector,
    PreviousMonthHighDetector,
    PreviousMonthLowDetector,
]

__all__ = [cls.__name__ for cls in ALL_DETECTORS] + ["ALL_DETECTORS"]
