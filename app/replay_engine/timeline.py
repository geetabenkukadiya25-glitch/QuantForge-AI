"""Builds the deterministic `ReplayTimeline` for a `ReplayContext`.

A pure transformation over already-validated inputs: given the configured
`start_index`/`end_index` scope, slice the historical data once and record
its frame-by-frame datetimes. This is the only place frame ordering is
decided -- `ReplayCursor` and `ReplayController` only ever navigate an
already-built timeline, never recompute it.
"""

from app.data_engine.columns import DATETIME_COL
from app.replay_engine.context import ReplayContext
from app.replay_engine.models import ReplayTimeline


def build_timeline(context: ReplayContext) -> ReplayTimeline:
    """Build the `ReplayTimeline` for `context`'s configured scope."""
    data = context.data
    config = context.configuration

    start_index = config.start_index
    end_index = config.end_index if config.end_index is not None else len(data) - 1
    sliced = data.iloc[start_index : end_index + 1]

    frame_datetimes = tuple(str(v) for v in sliced[DATETIME_COL])
    return ReplayTimeline(
        symbol=config.symbol,
        timeframe=config.timeframe,
        total_frames=len(sliced),
        start_index=start_index,
        end_index=end_index,
        start_datetime=frame_datetimes[0] if frame_datetimes else "",
        end_datetime=frame_datetimes[-1] if frame_datetimes else "",
        frame_datetimes=frame_datetimes,
    )
