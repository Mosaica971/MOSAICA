import warnings

import pandas as pd


def resolve_kept_plots(
    plot_index: pd.Index,
    criteria: dict[str, pd.Series],
    config: dict,
) -> pd.Index:
    zone_filter = config.get("zone_filter")
    if not zone_filter:
        return plot_index

    include = zone_filter.get("include") or {}
    exclude = zone_filter.get("exclude") or {}
    _check_unknown_keys(include, criteria, "include")
    _check_unknown_keys(exclude, criteria, "exclude")

    include_mask = pd.Series(True, index=plot_index)
    for name, series in criteria.items():
        values = include.get(name) or []
        if not values:
            continue
        include_mask &= series.isin(values)
        _warn_unmatched(name, values, series, "include")

    exclude_mask = pd.Series(False, index=plot_index)
    for name, series in criteria.items():
        values = exclude.get(name) or []
        if not values:
            continue
        exclude_mask |= series.isin(values)
        _warn_unmatched(name, values, series, "exclude")

    kept = plot_index[include_mask & ~exclude_mask]
    if kept.empty:
        raise ValueError(
            "zone_filter excludes every plot -- check config.yaml's zone_filter section"
        )
    return kept


def _check_unknown_keys(spec: dict, criteria: dict, section: str) -> None:
    unknown = set(spec) - set(criteria)
    if unknown:
        available = ", ".join(sorted(criteria))
        raise KeyError(
            f"Unknown zone_filter.{section} key(s) {sorted(unknown)}. Available: {available}"
        )


def _warn_unmatched(name: str, values: list, series: pd.Series, section: str) -> None:
    unmatched = set(values) - set(series.unique())
    if unmatched:
        warnings.warn(
            f"zone_filter.{section}.{name}: value(s) {sorted(unmatched)} match no plot",
            stacklevel=2,
        )
