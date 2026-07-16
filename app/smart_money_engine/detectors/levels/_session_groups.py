"""Shared session-grouping helper for Session High/Low detectors.

Not a detector itself. Reuses `app.context_engine.sessions` (a pure,
dependency-free helper module) to group candles by trading day + active
session -- a direct, sanctioned use of Context Engine outputs per the
Phase 7 spec, rather than a third reimplementation of session windows.
"""

import pandas as pd

from app.context_engine.sessions import get_active_session, to_utc
from app.smart_money_engine.schema import DATETIME_COL


def session_extreme(data: pd.DataFrame, column: str, agg: str) -> list[tuple[int, float, str, int, int]]:
    """Return `(extreme_index, extreme_value, session_name, group_start_index, group_end_index)`
    for each (day, session) group present in `data`, sorted by extreme index.
    """
    groups: dict[tuple[str, str], list[int]] = {}
    for i in range(len(data)):
        moment = to_utc(data[DATETIME_COL].iloc[i])
        info = get_active_session(moment)
        if info.name is None:
            continue
        key = (moment.date().isoformat(), info.name)
        groups.setdefault(key, []).append(i)

    results: list[tuple[int, float, str, int, int]] = []
    for (_, session_name), indices in groups.items():
        series = data[column].iloc[indices]
        extreme_index = int(series.idxmax() if agg == "max" else series.idxmin())
        results.append(
            (extreme_index, float(series.loc[extreme_index]), session_name, indices[0], indices[-1])
        )
    return sorted(results, key=lambda item: item[0])
