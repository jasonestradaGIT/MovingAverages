from __future__ import annotations

import pandas as pd


def add_moving_average(data: pd.DataFrame, points: int) -> pd.DataFrame:
    """Return lab data with a rolling average per analyte and instrument."""
    if points < 1:
        raise ValueError("Moving-average points must be a positive integer.")

    result = data.sort_values(["analyte", "instrument", "date"]).copy()
    result["moving_average"] = (
        result.groupby(["analyte", "instrument"], sort=False)["result"]
        .rolling(window=points, min_periods=1)
        .mean()
        .reset_index(level=[0, 1], drop=True)
    )
    return result


def add_combined_moving_average(data: pd.DataFrame, points: int) -> pd.DataFrame:
    """Return selected lab data with one rolling average across instruments."""
    if points < 1:
        raise ValueError("Moving-average points must be a positive integer.")

    result = data.sort_values(["date", "instrument"]).copy()
    result["combined_moving_average"] = result["result"].rolling(window=points, min_periods=1).mean()
    return result
