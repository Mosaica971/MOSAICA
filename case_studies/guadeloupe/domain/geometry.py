"""Join the RPG 2017 parcel geometry to the model's synthetic plot ids.

THE PROBLEM. `data/gis/01_RPG 2017/` holds the real 2017 parcel layer; `data_parc` holds the
same parcels under invented identifiers (P1..P24734) with no key in common. The two files
were derived from one another upstream, but the link was not kept, so it has to be rebuilt
from the attributes both sides carry.

WHAT ESTABLISHES THE LINK. Three facts, measured on 2026-08-01:
  * `RPG_2017_GC_MG_ss_doublon` holds exactly 24 734 records -- the count of data_parc, to
    the unit (the full layer has 24 931, and a companion "Doublons" layer holds the 198
    duplicates removed);
  * both sides describe 4 638 farms with the SAME distribution of sizes (769 farms of one
    plot, 759 of two, 664 of three, ...);
  * every farm signature on the model side has a counterpart on the SIG side -- zero orphans.
Taken together these are not a coincidence: it is one parcel universe written twice.

HOW THE JOIN IS BUILT. Each farm is reduced to the sorted multiset of its plots'
(commune, surface) pairs. Farms whose signature is unique on both sides are matched, then
their plots are paired within the farm by the same key. Measured coverage: 96.7 % of farms,
**99.4 % of plots** (24 582 of 24 734).

WHAT IT CANNOT DO, and it must be said before anyone reads a single parcel off a map:
  * 152 farms sit in 70 groups sharing an identical signature (all tiny, mostly one plot of
    the same size in the same commune). They are left unmatched rather than guessed.
  * within a matched farm, ~1 557 plots share their (commune, surface) with a sibling and so
    are interchangeable: one may be drawn on the other's outline. Both carry the same area
    and the same commune, so territorial and regional readings are unaffected -- but a
    single parcel is not evidence.
A map from this join is a picture of the territory, never a cadastral statement.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from core.data.shapefile import Polygon, read_layer

# The de-duplicated layer is the one whose record count matches the model's plot table.
RPG_LAYER = Path("data/gis") / "01_RPG 2017" / "RPG_2017_GC_MG_ss_doublon.shp"

_SURFACE_DECIMALS = 2


@dataclass(frozen=True)
class GeometryJoin:
    """Plot id -> polygon, plus what the join could not place."""

    polygons: dict[str, Polygon] = field(default_factory=dict)
    matched_farms: int = 0
    total_farms: int = 0
    ambiguous_plots: int = 0

    def summary(self, total_plots: int) -> str:
        share = 100.0 * len(self.polygons) / total_plots if total_plots else 0.0
        return (
            f"{len(self.polygons):,}/{total_plots:,} parcelles localisées ({share:.1f} %), "
            f"{self.matched_farms:,}/{self.total_farms:,} exploitations appariées, "
            f"{self.ambiguous_plots:,} parcelles interchangeables avec une jumelle"
        )


def _signature(pairs: list[tuple[Any, float]]) -> tuple:
    return tuple(sorted(pairs))


def build_geometry_join(
    data_parc: pd.DataFrame,
    plot_farm: pd.Series,
    layer_path: str | Path = RPG_LAYER,
) -> GeometryJoin:
    """Match model plots to RPG polygons through farm signatures. See the module docstring
    for what the result is and is not."""
    shapes, rows = read_layer(layer_path)

    sig_plots: dict[str, list[tuple[Any, float, Polygon]]] = defaultdict(list)
    for polygon, row in zip(shapes, rows):
        if polygon is None:
            continue
        try:
            commune = int(float(row["code_insee"]))
            surface = round(float(row["surf_parc"]), _SURFACE_DECIMALS)
        except (KeyError, TypeError, ValueError):
            continue
        sig_plots[row["pacage"]].append((commune, surface, polygon))

    model_plots: dict[Any, list[tuple[Any, float, str]]] = defaultdict(list)
    farms = plot_farm.reindex(data_parc.index)
    for plot, farm, commune, surface in zip(
        data_parc.index, farms, data_parc["COMMUNE"], data_parc["SURF_HA"]
    ):
        if pd.isna(farm):
            continue
        model_plots[farm].append(
            (int(commune), round(float(surface), _SURFACE_DECIMALS), plot)
        )

    model_by_sig: dict[tuple, list[Any]] = defaultdict(list)
    for farm, entries in model_plots.items():
        model_by_sig[_signature([(c, s) for c, s, _ in entries])].append(farm)
    sig_by_sig: dict[tuple, list[str]] = defaultdict(list)
    for pacage, entries in sig_plots.items():
        sig_by_sig[_signature([(c, s) for c, s, _ in entries])].append(pacage)

    polygons: dict[str, Polygon] = {}
    matched_farms = 0
    ambiguous_plots = 0
    for signature, model_farms in model_by_sig.items():
        sig_farms = sig_by_sig.get(signature)
        # Only unambiguous pairs are used: guessing between two identical farms would put a
        # parcel on someone else's land for no gain in coverage.
        if not sig_farms or len(model_farms) != 1 or len(sig_farms) != 1:
            continue
        matched_farms += 1
        available: dict[tuple[Any, float], list[Polygon]] = defaultdict(list)
        for commune, surface, polygon in sig_plots[sig_farms[0]]:
            available[(commune, surface)].append(polygon)
        counts = Counter(key for key in available for _ in available[key])
        for commune, surface, plot in model_plots[model_farms[0]]:
            candidates = available.get((commune, surface))
            if not candidates:
                continue
            if counts[(commune, surface)] > 1:
                ambiguous_plots += 1
            polygons[plot] = candidates.pop()

    return GeometryJoin(
        polygons=polygons,
        matched_farms=matched_farms,
        total_farms=len(model_plots),
        ambiguous_plots=ambiguous_plots,
    )
