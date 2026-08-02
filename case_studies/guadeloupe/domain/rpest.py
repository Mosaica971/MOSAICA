"""Rpest (Tixier): risk that pesticides applied to a plot reach the water.

Ported from R_PEST_NEW.txt. Unlike the nitrogen or IFT rates, this one is not a per-crop
number: it combines what the CROP applies (dose, persistence, toxicity, leaching potential)
with what the PLOT does with it (runoff, drainage), so the score exists per (plot, crop).

The method is a fuzzy decision tree, in three stages:

1. **Fuzzification.** Each variable is turned into a degree of unfavourability in [0, 1] by
   linear interpolation between a favourable and an unfavourable threshold, both read from
   `R_Tixier.txt`. Note the thresholds are not always increasing -- for ADI (acceptable daily
   intake) and the ADI/AQUATOX minimum, *high* is favourable -- which the interpolation
   handles naturally because it divides by (unfavourable - favourable).

2. **Combination.** Two or three degrees are merged by a min-based fuzzy rule: each corner of
   the truth table carries a severity (0 to 10) and the result is the severity-weighted
   average of the corner memberships. Four sub-scores:
       E_SURF = dose x runoff              T_SURF = persistence x min(ADI, aquatic toxicity)
       E_PROF = dose x leaching x drainage T_PROF = persistence x ADI
   Surface risk is (E_SURF + T_SURF)/2, depth risk (E_PROF + T_PROF)/2, and Rpest is the
   worse of the two -- a plot polluting by either route is polluting.

3. **Aggregation.** Per plot, weighted by the allocated area; territory-wide, GAMS reports
   the SURFACE whose score exceeds 6, which is the headline figure.

TWO FAITHFUL-PORT NOTES, both visible in the GAMS and neither corrected here:

* the per-crop averages are described in the source as "pondérée par les quantités de
  produits phytosanitaires utilisés", but the algebra cancels the weights: numerator and
  denominator carry the same annualised dose, so each term reduces to the property itself and
  the sum over operations is a **plain sum of the property over the operations the crop
  uses**, not a dose-weighted mean. A crop performing many small treatments therefore scores
  higher than one doing a single large one. Ported as written (parity mandate), flagged in
  docs/04-vigilance.md.
* the `ASSOL_Parc` factors multiplying every corner cancel between numerator and denominator,
  so the sub-scores do not depend on the allocation at all -- only the final per-plot
  aggregation does.

AND ONE CONSEQUENCE THAT MUST BE READ BEFORE QUOTING A LOW SCORE. A crop that applies no
pesticide at all sums to ADI = 0 and AQUATOX = 0 -- but the thresholds make a LOW acceptable
daily intake the unfavourable end (favourable 1, unfavourable 0), so "no product" is encoded
exactly like "the most toxic product there is". Pasture, fallow and the organic systems
therefore land on a floor around 2.4 instead of 0. Measured 2026-08-01: PN_PIQ, JA and
MA_PLBIO all score 2.36, against 8.81 for intensive banana.
The ranking is sound and is what the indicator is for -- banana above market gardening above
cane above grass. The absolute level of the bottom of the scale is not: it is an artefact of
summing a property over "no operations". Ported as written; flagged in docs/04-vigilance.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from case_studies.guadeloupe.domain.itk import annual_rate_per_ha_cult

# Severity attached to each corner of the truth table, favourable-first. Straight from
# R_PEST_NEW.txt: the two-variable rules run 0/4/6/10, the three-variable one 0/3/4/7/3/6/7/10.
_WEIGHTS_2 = (0.0, 4.0, 6.0, 10.0)
_WEIGHTS_3 = (0.0, 3.0, 4.0, 7.0, 3.0, 6.0, 7.0, 10.0)

# Properties averaged per crop over the operations it uses, and the Data_OTK column each
# reads. QMA (active-ingredient load) is handled separately: it IS a genuine annual rate.
_CROP_PROPERTIES = ("DT50", "ADI", "AQUATOX", "GUS")


def unfavourability(
    values: pd.Series, favourable: float, unfavourable: float
) -> pd.Series:
    """Degree of unfavourability in [0, 1], linear between the two thresholds.

    Works in both directions: when `favourable` exceeds `unfavourable` (ADI, where a high
    acceptable dose is good news) the slope is negative and the clip still yields 0 at the
    favourable end and 1 at the other.
    """
    span = unfavourable - favourable
    if span == 0:
        return pd.Series(0.0, index=values.index)
    return ((values.astype(float) - favourable) / span).clip(0.0, 1.0)


def _fuzzy_combine(degrees: list[np.ndarray], weights: tuple[float, ...]) -> np.ndarray:
    """Severity-weighted average over the corners of the truth table.

    `degrees` holds one unfavourability array per variable, broadcast to a common shape.
    Corner k takes each variable favourable (1-d) or unfavourable (d) according to the bits
    of k, most significant first -- the order the GAMS lists them in.
    """
    n = len(degrees)
    numerator = np.zeros_like(degrees[0], dtype=float)
    denominator = np.zeros_like(degrees[0], dtype=float)
    for corner, weight in enumerate(weights):
        membership = None
        for position, degree in enumerate(degrees):
            unfavourable_here = bool(corner >> (n - 1 - position) & 1)
            side = degree if unfavourable_here else (1.0 - degree)
            membership = side if membership is None else np.minimum(membership, side)
        numerator += weight * membership
        denominator += membership
    return np.divide(
        numerator, denominator, out=np.zeros_like(numerator), where=denominator > 0
    )


def compute_crop_properties(
    data_otk: pd.DataFrame,
    matrice_otk_cult: pd.DataFrame,
    duree_plant_cult: pd.Series,
    duree_cycle_cult: pd.Series,
) -> pd.DataFrame:
    """Per-crop DT50 / ADI / AQUATOX / GUS / QMA, as the GAMS computes them.

    The first four are sums over the operations the crop performs (see the module note on
    why the documented dose weighting cancels); QMA is a genuine annualised load per hectare.
    """
    used = matrice_otk_cult.fillna(0.0) > 0
    table = pd.DataFrame(index=matrice_otk_cult.columns, dtype=float)
    for column in _CROP_PROPERTIES:
        if column not in data_otk.columns:
            table[column] = 0.0
            continue
        values = data_otk[column].reindex(matrice_otk_cult.index).fillna(0.0)
        table[column] = used.mul(values, axis=0).sum(axis=0)

    if "QMA" in data_otk.columns:
        amortized = data_otk["AMORTI"] == 1
        per_application = data_otk["DOSE"] * data_otk["QMA"]
        table["QMA"] = annual_rate_per_ha_cult(
            matrice_otk_cult, per_application, duree_plant_cult, duree_cycle_cult, amortized
        ).reindex(table.index).fillna(0.0)
    else:
        table["QMA"] = 0.0
    return table


def compute_rpest_by_pair(
    crop_properties: pd.DataFrame,
    plot_attributes: pd.DataFrame,
    thresholds: pd.DataFrame,
    crops: list[str],
) -> pd.DataFrame:
    """Rpest for every (plot, crop): a plots x crops frame of scores on the 0-10 scale."""

    # R_Tixier.txt pads at least one identifier with trailing spaces ("SEUIL_GUS_CULT   "),
    # which would make an exact lookup fail on that row alone -- and silently drop the
    # leaching term if it were caught with a default.
    thresholds = thresholds.rename(index=lambda name: str(name).strip())

    def limits(name: str) -> tuple[float, float]:
        row = thresholds.loc[name]
        return float(row["Favorable"]), float(row["Defavorable"])

    crops = [c for c in crops if c in crop_properties.index]
    props = crop_properties.loc[crops]

    dose = unfavourability(props["QMA"], *limits("SEUIL_DOSE_CULT")).to_numpy()[None, :]
    dt50 = unfavourability(props["DT50"], *limits("SEUIL_DT50_CULT")).to_numpy()[None, :]
    gus = unfavourability(props["GUS"], *limits("SEUIL_GUS_CULT")).to_numpy()[None, :]
    adi = unfavourability(props["ADI"], *limits("SEUIL_ADI_CULT")).to_numpy()[None, :]
    min_adi_aqua = unfavourability(
        props[["ADI", "AQUATOX"]].min(axis=1), *limits("SEUIL_MIN_ADIAQUATOX")
    ).to_numpy()[None, :]

    runoff = unfavourability(
        plot_attributes["RUI_PARC"], *limits("SEUIL_RUI_PARC")
    ).to_numpy()[:, None]
    drainage = unfavourability(
        plot_attributes["DRAI_PARC"], *limits("SEUIL_DRAI_PARC")
    ).to_numpy()[:, None]

    shape = (len(plot_attributes), len(crops))

    def spread(array: np.ndarray) -> np.ndarray:
        return np.broadcast_to(array, shape)

    e_surf = _fuzzy_combine([spread(dose), spread(runoff)], _WEIGHTS_2)
    t_surf = _fuzzy_combine([spread(dt50), spread(min_adi_aqua)], _WEIGHTS_2)
    e_prof = _fuzzy_combine([spread(dose), spread(gus), spread(drainage)], _WEIGHTS_3)
    t_prof = _fuzzy_combine([spread(dt50), spread(adi)], _WEIGHTS_2)

    return pd.DataFrame(
        np.maximum((e_surf + t_surf) / 2.0, (e_prof + t_prof) / 2.0),
        index=plot_attributes.index,
        columns=crops,
    )
