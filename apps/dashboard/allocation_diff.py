"""What two runs actually did differently on the ground.

The companion of `config_diff`. That module says two lines of YAML separate two runs; this
one says what those two lines *moved* -- which hectares changed crop, from what to what,
and where. Between `calib_gams_parite` and `calib_retenu` the config diff is two constraints;
the allocation diff is the ~1 300 ha of export banana that came back and the ~3 100 ha of
pasture that stopped leaking into cane.

TWO RESOLUTIONS, AND THE CHOICE MATTERS.

* `base` folds the 84 fine crops onto the 12 observed RPG groups. This is the resolution the
  calibration works at, and the only one that means anything against the observed side --
  the fine variant of 2017 was never observed.
* `fine` keeps the crop codes. Comparing two SIMULATED runs is exactly the case where this is
  legitimate: both sides come from the same 84-code universe, so a plot moving from
  `CS_MG_NISM` to `PN_PIQ` is a real, readable change rather than an artefact of resolution.
  Prefer it here; `base` is for reading the diff next to a calibration figure.

ONE TRAP THIS MODULE DOES NOT HIDE. A plot allocated in one run and absent from the other is
not "unchanged" -- the model left it out of production. Those hectares are reported under
`UNALLOCATED` on the missing side rather than dropped, because a run that idles land is
saying something and a silent inner join would erase it.
"""

from __future__ import annotations

from typing import Callable

import pandas as pd

from case_studies.guadeloupe.domain.crop_families import base_group_for

# Stand-in for "this run put nothing here", so idled land survives the join.
UNALLOCATED = "—"

RESOLUTIONS = ("fine", "base")


def _labeller(resolution: str) -> Callable[[str], str]:
    if resolution == "fine":
        return str
    if resolution == "base":
        return lambda crop: crop if crop == UNALLOCATED else base_group_for(crop)
    raise ValueError(f"unknown resolution {resolution!r}, expected one of {RESOLUTIONS}")


def align(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    resolution: str = "fine",
    region: object | None = None,
) -> pd.DataFrame:
    """One row per plot appearing in either run: {plot, surface_ha, region, left, right}.

    Surfaces come from whichever side has the plot (they describe the same physical
    parcels, so the two agree); `region` filters to a single region code before anything
    else, which is how a reader localises a change.
    """
    label = _labeller(resolution)

    def prepared(frame: pd.DataFrame, side: str) -> pd.DataFrame:
        keep = frame[["plot", "crop", "surface_ha", "region"]].copy()
        keep["plot"] = keep["plot"].astype(str)
        keep[side] = keep["crop"].astype(str).map(label)
        return keep.drop(columns=["crop"]).set_index("plot")

    merged = prepared(left, "left").join(
        prepared(right, "right"), how="outer", lsuffix="_left", rsuffix="_right"
    )
    # Surface and region describe the same physical parcel, so either side answers; take the
    # left one and fall back on the right for plots the left run did not allocate at all.
    merged["surface_ha"] = merged["surface_ha_left"].fillna(merged["surface_ha_right"])
    merged["region"] = merged["region_left"].fillna(merged["region_right"])
    merged = merged.drop(
        columns=["surface_ha_left", "surface_ha_right", "region_left", "region_right"]
    )
    merged[["left", "right"]] = merged[["left", "right"]].fillna(UNALLOCATED)
    merged["surface_ha"] = merged["surface_ha"].fillna(0.0)

    if region is not None:
        merged = merged[merged["region"].astype(str) == str(region)]
    return merged.reset_index()[["plot", "surface_ha", "region", "left", "right"]]


def transition_matrix(aligned: pd.DataFrame) -> pd.DataFrame:
    """Hectares moving from each left crop (rows) to each right crop (columns).

    The diagonal is what did not move. Reading a row tells you where a crop went; reading a
    column tells you what a crop was made of.
    """
    if aligned.empty:
        return pd.DataFrame()
    return aligned.pivot_table(
        index="left", columns="right", values="surface_ha", aggfunc="sum", fill_value=0.0
    )


def net_change(aligned: pd.DataFrame) -> pd.DataFrame:
    """Per crop: hectares in the left run, in the right run, and the signed difference,
    biggest mover first. `UNALLOCATED` appears as a crop of its own so that land entering
    or leaving production is visible rather than implied."""
    if aligned.empty:
        return pd.DataFrame(columns=["crop", "left_ha", "right_ha", "delta_ha"])
    left = aligned.groupby("left")["surface_ha"].sum()
    right = aligned.groupby("right")["surface_ha"].sum()
    frame = pd.DataFrame({"left_ha": left, "right_ha": right}).fillna(0.0)
    frame["delta_ha"] = frame["right_ha"] - frame["left_ha"]
    frame.index.name = "crop"
    return frame.reset_index().sort_values(
        "delta_ha", key=lambda col: col.abs(), ascending=False
    )


def top_moves(aligned: pd.DataFrame, *, top: int = 12) -> pd.DataFrame:
    """The `top` largest from -> to flows, excluding plots that did not change.

    This is the table that answers "what did the constraint actually do": a single line
    like `BA_INT -> BC_BT, 1 298 ha` carried the whole Sud-Est Basse-Terre collapse.
    """
    if aligned.empty:
        return pd.DataFrame(columns=["left", "right", "surface_ha", "plots"])
    moved = aligned[aligned["left"] != aligned["right"]]
    if moved.empty:
        return pd.DataFrame(columns=["left", "right", "surface_ha", "plots"])
    grouped = (
        moved.groupby(["left", "right"])
        .agg(surface_ha=("surface_ha", "sum"), plots=("plot", "count"))
        .reset_index()
    )
    return grouped.nlargest(top, "surface_ha")


def stability(aligned: pd.DataFrame) -> dict[str, float]:
    """How much of the territory the two runs agree on.

    `share_ha` is the headline: the fraction of hectares carrying the same crop in both.
    Read it against the config diff -- two runs differing by one non-binding constraint sit
    near 100 %, and a low figure under a small config diff means the model's optimum is
    poorly determined, not that the constraint did a lot.
    """
    if aligned.empty:
        return {"same_ha": 0.0, "total_ha": 0.0, "share_ha": 0.0,
                "same_plots": 0, "total_plots": 0, "share_plots": 0.0}
    same = aligned["left"] == aligned["right"]
    total_ha = float(aligned["surface_ha"].sum())
    same_ha = float(aligned.loc[same, "surface_ha"].sum())
    return {
        "same_ha": same_ha,
        "total_ha": total_ha,
        "share_ha": (same_ha / total_ha) if total_ha else 0.0,
        "same_plots": int(same.sum()),
        "total_plots": int(len(aligned)),
        "share_plots": float(same.mean()),
    }
