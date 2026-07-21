# Calibration & validation — plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** mesurer l'écart entre l'assolement observé en 2017 et l'assolement simulé, aux quatre échelles de Chopin et al. (2015) §2.6, et exposer le résultat en CSV, dans le recap, en figures et dans le dashboard.

**Architecture:** un module de calcul pur (`reporting/calibration.py`) de signature `(dataset, allocation, config)` comme `indicators.py`, alimenté par une nouvelle correspondance culture fine → groupe RPG observé (`domain/crop_families.py`). Quatre consommateurs : `generate_report`, un script post-hoc, deux figures, une page dashboard. Aucune modification du modèle, aucun solve.

**Tech Stack:** Python 3.12, pandas, matplotlib (backend Agg), streamlit, pytest.

**Spec:** `docs/superpowers/specs/2026-07-21-calibration-validation-design.md`

## Global Constraints

- Le module de calcul ne lit jamais `data/` directement : il reçoit un `Dataset`. Les tests construisent un `Dataset` synthétique, comme `tests/test_guadeloupe_reporting_indicators.py`.
- Le module de calcul n'importe ni `streamlit`, ni `matplotlib`, ni `pathlib` pour écrire : il rend des `DataFrame`.
- `reporting/` ne doit jamais importer `dashboard/`. La dépendance va dans l'autre sens.
- La comparaison observé/simulé se fait **toujours** au niveau des 12 groupes RPG, jamais au niveau des 84 cultures fines.
- Seuils par défaut, valeurs de l'article : régional 15 %, sous-régional 20 %, ferme 20 %, typologie 80 %.
- `recap.md` s'écrit sans accents (convention du fichier existant : « Duree de resolution »). `recap.json`, les CSV et le dashboard peuvent en porter.
- Aucun `main.py`, aucun `run_scenarios.py`, aucun solve réel n'est lancé par ce plan.
- Commandes depuis la racine du dépôt, interpréteur `.venv/Scripts/python`.

---

### Task 1: Correspondance culture fine → groupe observé

**Files:**
- Create: `case_studies/guadeloupe/domain/crop_families.py`
- Test: `tests/test_crop_families.py`

**Interfaces:**
- Consumes: `case_studies.guadeloupe.domain.crop_labels.CROP_LABELS`, `case_studies.guadeloupe.domain.farm_typology._RPG_CODE_TO_BASE_GROUP` (test seulement).
- Produces: `base_group_for(crop: str) -> str`, `base_groups_for(crops: pd.Series) -> pd.Series`, `OBSERVED_BASE_GROUPS: frozenset[str]`, `NON_CULTIVATED: str`.

- [ ] **Step 1: Write the failing test**

Créer `tests/test_crop_families.py` :

```python
import pandas as pd
import pytest

from case_studies.guadeloupe.domain import crop_families
from case_studies.guadeloupe.domain.crop_labels import CROP_LABELS
from case_studies.guadeloupe.domain.farm_typology import _RPG_CODE_TO_BASE_GROUP


def test_fine_variants_fold_onto_their_family():
    assert crop_families.base_group_for("CS_NGT_NISM") == "CS"
    assert crop_families.base_group_for("MA_BAG_BIO_I") == "MA"
    assert crop_families.base_group_for("VE_PLUIE") == "VE"
    assert crop_families.base_group_for("PN_TOUR") == "PN"


def test_fibre_cane_folds_onto_sugarcane():
    # The RPG nomenclature has a single sugarcane code (6): CF and CS are indistinguishable
    # in the observed data, so both must land on CS for the comparison to mean anything.
    assert crop_families.base_group_for("CF_NBT_NIM") == "CS"


def test_tomato_folds_onto_market_gardening():
    assert crop_families.base_group_for("TH") == "MA"


def test_aggregate_codes_map_to_themselves():
    for code in ("AG", "ME", "JA", "NC", "CS", "MA"):
        assert crop_families.base_group_for(code) == code


def test_unknown_code_raises():
    with pytest.raises(KeyError):
        crop_families.base_group_for("ZZ_UNKNOWN")


def test_every_labelled_crop_maps_to_an_observed_group():
    # Guard for the future: adding a crop to CROP_LABELS without declaring its family
    # breaks this test rather than silently skewing the calibration metrics.
    for code in CROP_LABELS:
        assert crop_families.base_group_for(code) in crop_families.OBSERVED_BASE_GROUPS


def test_observed_groups_match_the_rpg_vocabulary():
    assert crop_families.OBSERVED_BASE_GROUPS == frozenset(_RPG_CODE_TO_BASE_GROUP.values())


def test_base_groups_for_maps_a_series():
    crops = pd.Series({"P1": "CS_MG_IM", "P2": "TH", "P3": "AG"})
    result = crop_families.base_groups_for(crops)
    assert result.to_dict() == {"P1": "CS", "P2": "MA", "P3": "AG"}
    assert list(result.index) == ["P1", "P2", "P3"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_crop_families.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'case_studies.guadeloupe.domain.crop_families'`

- [ ] **Step 3: Write minimal implementation**

Créer `case_studies/guadeloupe/domain/crop_families.py` :

```python
"""Fine crop code -> observed RPG base group.

The observed 2017 land use is only known at aggregate/RPG resolution -- 12 groups, see
farm_typology._RPG_CODE_TO_BASE_GROUP -- while the solver allocates one of the fine crops
of CULT_2017.set. Any observed-vs-simulated comparison must therefore fold the fine codes
back onto the 12 observed groups. Chopin et al. (2015) do exactly that in Fig. 4, which
compares "10 agricultural uses" and not the 36 cropping systems of their activity database.

Every fine code starts with its family token (CS_NGT_NISM, MA_BAG_BIO_I, ...), so the token
before the first underscore drives the mapping. Two tokens do not name their own group:
CF (fibre cane) folds onto CS because RPG code 6 covers both cane types, and TH (tomato)
folds onto MA because the RPG nomenclature files tomato under market gardening.
"""

import pandas as pd

NON_CULTIVATED = "NC"

_GROUP_BY_TOKEN: dict[str, str] = {
    "AG": "AG",   # agrumes
    "AN": "AN",   # ananas
    "BA": "BA",   # banane fruit
    "BC": "BC",   # banane plantain
    "CF": "CS",   # canne fibre -> canne (RPG code 6 covers both)
    "CS": "CS",   # canne a sucre
    "IG": "IG",   # igname et tubercules tropicaux
    "JA": "JA",   # jachere
    "MA": "MA",   # maraichage
    "ME": "ME",   # melon
    "NC": "NC",   # non cultive
    "PN": "PN",   # prairies & savanes
    "TH": "MA",   # tomate -> maraichage
    "VE": "VE",   # vergers hors agrumes
}

OBSERVED_BASE_GROUPS: frozenset[str] = frozenset(_GROUP_BY_TOKEN.values())


def base_group_for(crop: str) -> str:
    """Observed RPG group of a fine crop code. Raises KeyError on an undeclared family."""
    token = str(crop).split("_", 1)[0]
    try:
        return _GROUP_BY_TOKEN[token]
    except KeyError:
        raise KeyError(
            f"crop {crop!r}: family token {token!r} has no observed RPG group. "
            f"Declare it in crop_families._GROUP_BY_TOKEN."
        ) from None


def base_groups_for(crops: pd.Series) -> pd.Series:
    """Element-wise base_group_for over a plot-indexed crop Series."""
    return crops.map(base_group_for)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_crop_families.py -v`
Expected: PASS, 8 tests

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/domain/crop_families.py tests/test_crop_families.py
git commit -m "feat(calibration): correspondance culture fine -> groupe RPG observe"
```

---

### Task 2: Vocabulaire géographique dans `domain/`

Le reporting a besoin des noms de régions pour les axes des figures, et `reporting/` ne doit pas importer `dashboard/`. Les quatre symboles quittent `dashboard/comparison.py` pour `domain/zones.py`, et `comparison.py` les ré-exporte pour ne casser aucun appelant.

**Files:**
- Create: `case_studies/guadeloupe/domain/zones.py`
- Modify: `case_studies/guadeloupe/dashboard/comparison.py:63-82`
- Test: `tests/test_zones.py`

**Interfaces:**
- Produces: `zones.REGION_LABELS: dict[str, str]`, `zones.ISLAND_LABELS: dict[str, str]`, `zones.REGION_CODES: tuple[int, ...]`, `zones.ISLAND_CODES: tuple[int, ...]`, `zones.region_label(value) -> str`.
- `comparison.REGION_LABELS`, `comparison.ISLAND_LABELS`, `comparison.REGION_CODES`, `comparison.ISLAND_CODES` restent disponibles sous ces noms (utilisés par `pages/2_Comparaison.py:211-213`).

- [ ] **Step 1: Write the failing test**

Créer `tests/test_zones.py` :

```python
from case_studies.guadeloupe.dashboard import comparison
from case_studies.guadeloupe.domain import zones


def test_the_seven_subregions_of_the_article_are_named():
    assert zones.REGION_CODES == (1, 2, 3, 4, 5, 6, 7)
    assert zones.REGION_LABELS["1"] == "CGT · Centre Grande-Terre"
    assert zones.REGION_LABELS["7"] == "MG · Marie-Galante"
    assert set(zones.REGION_LABELS) == {str(code) for code in zones.REGION_CODES}


def test_islands_are_named():
    assert zones.ISLAND_CODES == (1, 2, 3)
    assert set(zones.ISLAND_LABELS) == {str(code) for code in zones.ISLAND_CODES}


def test_region_label_accepts_int_and_str_and_falls_back():
    assert zones.region_label(3) == zones.REGION_LABELS["3"]
    assert zones.region_label("3") == zones.REGION_LABELS["3"]
    assert zones.region_label("TOTAL") == "TOTAL"


def test_comparison_still_exposes_the_moved_symbols():
    # pages/2_Comparaison.py reads them through `comparison`; the move must be invisible.
    assert comparison.REGION_LABELS is zones.REGION_LABELS
    assert comparison.ISLAND_LABELS is zones.ISLAND_LABELS
    assert comparison.REGION_CODES is zones.REGION_CODES
    assert comparison.ISLAND_CODES is zones.ISLAND_CODES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_zones.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'case_studies.guadeloupe.domain.zones'`

- [ ] **Step 3: Write minimal implementation**

Créer `case_studies/guadeloupe/domain/zones.py` :

```python
"""Region / island codes and their human names (GAMS source: DESCRIPTION_SETS.txt).

The seven REGION codes are the seven "areas with homogeneous soil and climate conditions"
of Chopin et al. (2015), Table 5. Tables and figures store the raw numeric codes; these
turn "1, 2, ..." into readable labels. Lives in domain/ rather than dashboard/ because
reporting/ needs it too, and reporting/ must not import dashboard/.
"""

REGION_LABELS: dict[str, str] = {
    "1": "CGT · Centre Grande-Terre",
    "2": "EGT · Est Grande-Terre",
    "3": "NGT · Nord Grande-Terre",
    "4": "NBT · Nord Basse-Terre",
    "5": "SEBT · Sud-Est Basse-Terre",
    "6": "SOBT · Sud-Ouest Basse-Terre",
    "7": "MG · Marie-Galante",
}
ISLAND_LABELS: dict[str, str] = {
    "1": "Basse-Terre",
    "2": "Grande-Terre",
    "3": "Marie-Galante",
}
# Full universe of region / island codes, so an exhaustive axis can include codes absent
# from a given allocation (as zero-height bars).
REGION_CODES: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)
ISLAND_CODES: tuple[int, ...] = (1, 2, 3)


def _code_key(value: object) -> str:
    """Normalise a region/island code to its label-dict key: 3, 3.0 and "3" all give "3"."""
    text = str(value)
    return text[:-2] if text.endswith(".0") else text


def region_label(value: object) -> str:
    return REGION_LABELS.get(_code_key(value), str(value))


def island_label(value: object) -> str:
    return ISLAND_LABELS.get(_code_key(value), str(value))
```

Dans `case_studies/guadeloupe/dashboard/comparison.py`, remplacer le bloc `REGION_LABELS` / `ISLAND_LABELS` / `REGION_CODES` / `ISLAND_CODES` (lignes 63-82) par une ré-export :

```python
# Region / island codes -> human names. Defined in domain/zones.py because reporting/ needs
# them too; re-exported here under their historical names for this module's callers.
from case_studies.guadeloupe.domain.zones import (  # noqa: F401
    ISLAND_CODES,
    ISLAND_LABELS,
    REGION_CODES,
    REGION_LABELS,
)
```

Placer cet import en tête du fichier, avec les autres imports, et vérifier que les fonctions existantes de `comparison.py` (`_code_key` en ligne 101/105) continuent de résoudre `REGION_LABELS` / `ISLAND_LABELS`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_zones.py tests/test_guadeloupe_dashboard_comparison.py -v`
Expected: PASS — les nouveaux tests et toute la suite comparaison existante

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/domain/zones.py case_studies/guadeloupe/dashboard/comparison.py tests/test_zones.py
git commit -m "refactor(dashboard): deplacer le vocabulaire geographique dans domain/zones"
```

---

### Task 3: Seuils et PAD par culture

**Files:**
- Create: `case_studies/guadeloupe/reporting/calibration.py`
- Test: `tests/test_guadeloupe_reporting_calibration.py`

**Interfaces:**
- Consumes: `crop_families.base_groups_for`, `indicators.decode_baseline_allocation`, `indicators.compute_surface_by_key`.
- Produces: `CalibrationThresholds` (dataclass, champs `regional_pad_max`, `subregional_pad_max`, `farm_pad_max`, `farm_type_match_min`), `thresholds_from_config(config) -> CalibrationThresholds`, `simulated_groups(dataset, output_allocation) -> pd.Series`, `pad_by_crop(dataset, output_allocation, thresholds) -> pd.DataFrame`, `TOTAL_KEY = "TOTAL"`.

- [ ] **Step 1: Write the failing test**

Créer `tests/test_guadeloupe_reporting_calibration.py`. Le `Dataset` synthétique est réutilisé par les tâches 4 à 7 ; il est calibré pour produire des verdicts contrastés.

```python
import numpy as np
import pandas as pd
import pytest

from case_studies.guadeloupe.reporting import calibration
from core.data.dataset import Dataset


def _small_dataset() -> Dataset:
    """Six plots, three farms, two regions.

    Observed 2017 (RPG code -> group): P1/P2 cane, P3 melon, P4 non-cultivated,
    P5 pasture, P6 yam. cult_2016 equals cult_2017 everywhere so the fallow-continuity
    override of compute_base_crop_group is a no-op, except on P4 where both are 14 and it
    stays 14 (NC) anyway.
    """
    data_parc = pd.DataFrame(
        {
            "SURF_HA": [2.0, 3.0, 1.0, 4.0, 3.0, 1.0],
            "REGION": ["R1", "R1", "R2", "R2", "R1", "R2"],
            "ILE": [1, 1, 2, 2, 1, 2],
            "cult_2016": [6, 6, 13, 14, 7, 18],
            "cult_2017": [6, 6, 13, 14, 7, 18],
        },
        index=["P1", "P2", "P3", "P4", "P5", "P6"],
    )
    expl_parc = pd.DataFrame(
        {
            "farm": ["E1", "E1", "E2", "E2", "E3", "E3"],
            "plot": ["P1", "P2", "P3", "P4", "P5", "P6"],
        }
    )
    return Dataset(
        sets={},
        parameters={
            "data_parc": data_parc,
            "expl_parc": expl_parc,
            "farm_plots": {"E1": ["P1", "P2"], "E2": ["P3", "P4"], "E3": ["P5", "P6"]},
        },
        scalars={},
    )


def _simulated() -> pd.Series:
    """P1 stays cane, P2 flips to market gardening, P3/P5 keep their group,
    P4 and P6 are left unallocated by the solver."""
    return pd.Series(
        {"P1": "CS_NGT_NISM", "P2": "MA_ROTA", "P3": "ME", "P5": "PN_TOUR"}, name="crop"
    )


def test_thresholds_default_to_the_article_values():
    thresholds = calibration.thresholds_from_config({})
    assert thresholds.regional_pad_max == 15.0
    assert thresholds.subregional_pad_max == 20.0
    assert thresholds.farm_pad_max == 20.0
    assert thresholds.farm_type_match_min == 80.0


def test_thresholds_read_the_config_section():
    config = {"reporting": {"calibration": {"regional_pad_max": 5, "farm_pad_max": 33.5}}}
    thresholds = calibration.thresholds_from_config(config)
    assert thresholds.regional_pad_max == 5.0
    assert thresholds.farm_pad_max == 33.5
    assert thresholds.subregional_pad_max == 20.0  # untouched keys keep their default


def test_simulated_groups_folds_fine_crops_and_drops_non_cultivated():
    dataset = _small_dataset()
    allocation = pd.Series({"P1": "CS_NGT_NISM", "P2": "NC", "P3": "TH"})
    result = calibration.simulated_groups(dataset, allocation)
    assert result.to_dict() == {"P1": "CS", "P3": "MA"}


def test_pad_by_crop_scores_each_group_and_the_total():
    dataset = _small_dataset()
    thresholds = calibration.thresholds_from_config({})
    frame = calibration.pad_by_crop(dataset, _simulated(), thresholds)

    # Observed: CS 5 ha, ME 1, PN 3, IG 1 (NC excluded). Simulated: CS 2, MA 3, ME 1, PN 3.
    assert frame.loc["CS", "observed_ha"] == pytest.approx(5.0)
    assert frame.loc["CS", "simulated_ha"] == pytest.approx(2.0)
    assert frame.loc["CS", "abs_deviation_ha"] == pytest.approx(3.0)
    assert frame.loc["CS", "pad_pct"] == pytest.approx(60.0)
    assert bool(frame.loc["CS", "within_threshold"]) is False

    assert frame.loc["PN", "pad_pct"] == pytest.approx(0.0)
    assert bool(frame.loc["PN", "within_threshold"]) is True

    # A group that vanished from the output deviates by 100%.
    assert frame.loc["IG", "simulated_ha"] == pytest.approx(0.0)
    assert frame.loc["IG", "pad_pct"] == pytest.approx(100.0)


def test_pad_is_undefined_for_a_crop_absent_from_the_observed_side():
    dataset = _small_dataset()
    frame = calibration.pad_by_crop(dataset, _simulated(), calibration.thresholds_from_config({}))
    assert frame.loc["MA", "observed_ha"] == pytest.approx(0.0)
    assert frame.loc["MA", "simulated_ha"] == pytest.approx(3.0)
    assert np.isnan(frame.loc["MA", "pad_pct"])
    assert pd.isna(frame.loc["MA", "within_threshold"])


def test_pad_by_crop_total_row_is_the_ratio_of_sums():
    dataset = _small_dataset()
    frame = calibration.pad_by_crop(dataset, _simulated(), calibration.thresholds_from_config({}))
    total = frame.loc[calibration.TOTAL_KEY]
    # Deviations: CS 3 + IG 1 + MA 3 = 7 over 10 observed hectares.
    assert total["observed_ha"] == pytest.approx(10.0)
    assert total["abs_deviation_ha"] == pytest.approx(7.0)
    assert total["pad_pct"] == pytest.approx(70.0)
    assert bool(total["within_threshold"]) is False


def test_pad_is_zero_when_the_simulation_reproduces_the_baseline():
    dataset = _small_dataset()
    identical = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME", "P5": "PN", "P6": "IG"})
    frame = calibration.pad_by_crop(dataset, identical, calibration.thresholds_from_config({}))
    assert frame["pad_pct"].fillna(0.0).abs().max() == pytest.approx(0.0)
    assert frame["within_threshold"].dropna().all()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_calibration.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'case_studies.guadeloupe.reporting.calibration'`

- [ ] **Step 3: Write minimal implementation**

Créer `case_studies/guadeloupe/reporting/calibration.py` :

```python
"""Observed-vs-simulated calibration metrics, after Chopin et al. (2015) §2.6.

The article evaluates MOSAICA with the percentage of absolute deviation (PAD, Eq. 7)
between the observed acreage X_init(a) of a crop and the simulated acreage X(a), read at
four nested scales: region, sub-region, farm and field. This module computes those, plus
the per-farm PAD the article states a threshold for without publishing its table.

Everything is compared at the resolution of the 12 observed RPG groups: the observed 2017
land use has no finer resolution (see VIGILANCE.md on the aggregate baseline), so the
simulated fine crops are folded back with domain/crop_families.

Reporting only -- nothing here influences the allocation, and no solve is needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from case_studies.guadeloupe.domain import crop_families
from case_studies.guadeloupe.reporting import indicators
from core.data.dataset import Dataset

TOTAL_KEY = "TOTAL"

# Chopin et al. (2015) §2.6: PAD below 15% regionally and 20% in sub-regions and farms,
# 80% of farms in the right type. The article takes these from Kanellopoulos et al. (2010),
# Hazell and Norton (1986) and Janssen and van Ittersum (2007) -- they are conventions, not
# physical limits, hence configurable.
DEFAULT_REGIONAL_PAD_MAX = 15.0
DEFAULT_SUBREGIONAL_PAD_MAX = 20.0
DEFAULT_FARM_PAD_MAX = 20.0
DEFAULT_FARM_TYPE_MATCH_MIN = 80.0


@dataclass(frozen=True)
class CalibrationThresholds:
    regional_pad_max: float = DEFAULT_REGIONAL_PAD_MAX
    subregional_pad_max: float = DEFAULT_SUBREGIONAL_PAD_MAX
    farm_pad_max: float = DEFAULT_FARM_PAD_MAX
    farm_type_match_min: float = DEFAULT_FARM_TYPE_MATCH_MIN


def thresholds_from_config(config: dict[str, Any]) -> CalibrationThresholds:
    section = (config.get("reporting") or {}).get("calibration") or {}
    return CalibrationThresholds(
        regional_pad_max=float(section.get("regional_pad_max", DEFAULT_REGIONAL_PAD_MAX)),
        subregional_pad_max=float(
            section.get("subregional_pad_max", DEFAULT_SUBREGIONAL_PAD_MAX)
        ),
        farm_pad_max=float(section.get("farm_pad_max", DEFAULT_FARM_PAD_MAX)),
        farm_type_match_min=float(
            section.get("farm_type_match_min", DEFAULT_FARM_TYPE_MATCH_MIN)
        ),
    )


def observed_groups(dataset: Dataset) -> pd.Series:
    """plot -> observed RPG group, NC and unmapped codes already dropped. Identical to the
    baseline the rest of the reporting uses, so both sides tell the same story."""
    return indicators.decode_baseline_allocation(dataset)


def simulated_groups(dataset: Dataset, output_allocation: pd.Series) -> pd.Series:
    """plot -> simulated RPG group. NC is dropped, symmetrically with the observed side:
    a plot the solver leaves non-cultivated is not part of any crop's acreage."""
    groups = crop_families.base_groups_for(output_allocation)
    return groups[groups != crop_families.NON_CULTIVATED]


def _surface_by_group(dataset: Dataset, groups: pd.Series) -> pd.Series:
    return indicators.compute_surface_by_key(dataset, groups)


def _pad_frame(observed: pd.Series, simulated: pd.Series, threshold: float) -> pd.DataFrame:
    """PAD table over the union of the two indexes, plus a TOTAL row.

    Per-entry PAD is 100*|obs-sim|/obs, undefined (NaN) when nothing was observed -- that is
    a crop the model invented, whose deviation cannot be expressed as a share of zero. The
    TOTAL row is the ratio of the sums, Eq. 7 proper; the two verdicts are independent.
    """
    keys = observed.index.union(simulated.index)
    observed = observed.reindex(keys, fill_value=0.0).astype(float)
    simulated = simulated.reindex(keys, fill_value=0.0).astype(float)
    deviation = (simulated - observed).abs()
    pad = 100.0 * deviation / observed.where(observed > 0)

    frame = pd.DataFrame(
        {
            "observed_ha": observed,
            "simulated_ha": simulated,
            "abs_deviation_ha": deviation,
            "pad_pct": pad,
            "within_threshold": pad.le(threshold).where(pad.notna()).astype("boolean"),
        }
    )

    total_observed = float(observed.sum())
    total_deviation = float(deviation.sum())
    total_pad = 100.0 * total_deviation / total_observed if total_observed > 0 else float("nan")
    frame.loc[TOTAL_KEY] = {
        "observed_ha": total_observed,
        "simulated_ha": float(simulated.sum()),
        "abs_deviation_ha": total_deviation,
        "pad_pct": total_pad,
        "within_threshold": pd.NA if pd.isna(total_pad) else bool(total_pad <= threshold),
    }
    frame["within_threshold"] = frame["within_threshold"].astype("boolean")
    return frame


def pad_by_crop(
    dataset: Dataset, output_allocation: pd.Series, thresholds: CalibrationThresholds
) -> pd.DataFrame:
    """Regional scale, Chopin et al. Fig. 4: acreage per crop over the whole territory."""
    observed = _surface_by_group(dataset, observed_groups(dataset))
    simulated = _surface_by_group(dataset, simulated_groups(dataset, output_allocation))
    frame = _pad_frame(observed, simulated, thresholds.regional_pad_max)
    frame.index.name = "crop"
    return frame
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_calibration.py -v`
Expected: PASS, 7 tests

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/calibration.py tests/test_guadeloupe_reporting_calibration.py
git commit -m "feat(calibration): seuils configurables et PAD par culture a l'echelle regionale"
```

---

### Task 4: PAD par sous-région et par exploitation

**Files:**
- Modify: `case_studies/guadeloupe/reporting/calibration.py`
- Test: `tests/test_guadeloupe_reporting_calibration.py`

**Interfaces:**
- Consumes: `_pad_frame`, `observed_groups`, `simulated_groups`, `indicators.plot_to_region`, `indicators.plot_to_farm`.
- Produces: `pad_by_crop_and_region(dataset, output_allocation, thresholds) -> pd.DataFrame` (MultiIndex `(region, crop)`, une ligne `(region, "TOTAL")` par région), `pad_by_farm(dataset, output_allocation, thresholds) -> pd.DataFrame` (index `farm`).

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_guadeloupe_reporting_calibration.py` :

```python
def test_pad_by_crop_and_region_scores_each_subregion():
    dataset = _small_dataset()
    frame = calibration.pad_by_crop_and_region(
        dataset, _simulated(), calibration.thresholds_from_config({})
    )
    # R1 observed: CS 5 (P1+P2), PN 3 (P5). R1 simulated: CS 2 (P1), MA 3 (P2), PN 3 (P5).
    assert frame.loc[("R1", "CS"), "pad_pct"] == pytest.approx(60.0)
    assert frame.loc[("R1", "PN"), "pad_pct"] == pytest.approx(0.0)
    # R2 observed: ME 1 (P3), IG 1 (P6). R2 simulated: ME 1 only.
    assert frame.loc[("R2", "ME"), "pad_pct"] == pytest.approx(0.0)
    assert frame.loc[("R2", "IG"), "pad_pct"] == pytest.approx(100.0)


def test_pad_by_crop_and_region_carries_a_total_per_region():
    dataset = _small_dataset()
    frame = calibration.pad_by_crop_and_region(
        dataset, _simulated(), calibration.thresholds_from_config({})
    )
    # R1: deviations CS 3 + MA 3 = 6 over 8 observed hectares.
    assert frame.loc[("R1", calibration.TOTAL_KEY), "pad_pct"] == pytest.approx(75.0)
    # R2: deviation IG 1 over 2 observed hectares.
    assert frame.loc[("R2", calibration.TOTAL_KEY), "pad_pct"] == pytest.approx(50.0)


def test_pad_by_crop_and_region_uses_the_subregional_threshold():
    dataset = _small_dataset()
    thresholds = calibration.CalibrationThresholds(
        regional_pad_max=0.0, subregional_pad_max=60.0
    )
    frame = calibration.pad_by_crop_and_region(dataset, _simulated(), thresholds)
    assert bool(frame.loc[("R1", "CS"), "within_threshold"]) is True  # 60 <= 60
    assert bool(frame.loc[("R2", "IG"), "within_threshold"]) is False  # 100 > 60


def test_pad_by_farm_scores_each_holding():
    dataset = _small_dataset()
    frame = calibration.pad_by_farm(
        dataset, _simulated(), calibration.thresholds_from_config({})
    )
    # E1 observed 5 ha of cane, simulated 2 cane + 3 market gardening -> 6 ha of deviation.
    assert frame.loc["E1", "observed_ha"] == pytest.approx(5.0)
    assert frame.loc["E1", "pad_pct"] == pytest.approx(120.0)
    # E2 keeps its melon and its non-cultivated plot: nothing moved.
    assert frame.loc["E2", "pad_pct"] == pytest.approx(0.0)
    assert bool(frame.loc["E2", "within_threshold"]) is True
    # E3 loses its yam: 1 ha of deviation over 4 observed.
    assert frame.loc["E3", "pad_pct"] == pytest.approx(25.0)
    assert bool(frame.loc["E3", "within_threshold"]) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_calibration.py -k "region or farm" -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'pad_by_crop_and_region'`

- [ ] **Step 3: Write minimal implementation**

Ajouter à `case_studies/guadeloupe/reporting/calibration.py`, après `pad_by_crop` :

```python
def _surface_by_group_and_key(
    dataset: Dataset, groups: pd.Series, key: pd.Series
) -> pd.Series:
    """Allocated surface totalled by (key, group), for a plot-keyed grouping Series."""
    surface = dataset.parameters["data_parc"]["SURF_HA"].reindex(groups.index)
    keys = key.reindex(groups.index)
    return surface.groupby([keys, groups]).sum()


def pad_by_crop_and_region(
    dataset: Dataset, output_allocation: pd.Series, thresholds: CalibrationThresholds
) -> pd.DataFrame:
    """Sub-regional scale, Chopin et al. Fig. 5: acreage per crop within each of the seven
    areas of homogeneous soil and climate conditions. One TOTAL row per region; the
    territory-wide total lives in pad_by_crop."""
    region = indicators.plot_to_region(dataset)
    observed = _surface_by_group_and_key(dataset, observed_groups(dataset), region)
    simulated = _surface_by_group_and_key(
        dataset, simulated_groups(dataset, output_allocation), region
    )
    regions = observed.index.get_level_values(0).union(simulated.index.get_level_values(0))

    def slice_for(totals: pd.Series, region_key: Any) -> pd.Series:
        """The (crop -> hectares) sub-series of one region, empty when it has none.
        Series.get on a MultiIndex is ambiguous, hence the explicit cross-section."""
        if region_key not in totals.index.get_level_values(0):
            return pd.Series(dtype=float)
        return totals.xs(region_key, level=0)

    blocks = []
    for region_key in sorted(regions, key=str):
        frame = _pad_frame(
            slice_for(observed, region_key),
            slice_for(simulated, region_key),
            thresholds.subregional_pad_max,
        )
        frame.index = pd.MultiIndex.from_product(
            [[region_key], frame.index], names=["region", "crop"]
        )
        blocks.append(frame)
    return pd.concat(blocks)


def pad_by_farm(
    dataset: Dataset, output_allocation: pd.Series, thresholds: CalibrationThresholds
) -> pd.DataFrame:
    """Farm scale: the article states a 20% threshold "in the sub-regions and farms"
    without publishing the table. One row per farm, the deviation summed over its crops."""
    farm = indicators.plot_to_farm(dataset)
    observed = _surface_by_group_and_key(dataset, observed_groups(dataset), farm)
    simulated = _surface_by_group_and_key(
        dataset, simulated_groups(dataset, output_allocation), farm
    )
    keys = observed.index.union(simulated.index)
    observed = observed.reindex(keys, fill_value=0.0)
    simulated = simulated.reindex(keys, fill_value=0.0)

    by_farm = pd.DataFrame(
        {
            "observed_ha": observed.groupby(level=0).sum(),
            "simulated_ha": simulated.groupby(level=0).sum(),
            "abs_deviation_ha": (simulated - observed).abs().groupby(level=0).sum(),
        }
    )
    pad = 100.0 * by_farm["abs_deviation_ha"] / by_farm["observed_ha"].where(
        by_farm["observed_ha"] > 0
    )
    by_farm["pad_pct"] = pad
    by_farm["within_threshold"] = (
        pad.le(thresholds.farm_pad_max).where(pad.notna()).astype("boolean")
    )
    by_farm.index.name = "farm"
    return by_farm
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_calibration.py -v`
Expected: PASS, 11 tests

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/calibration.py tests/test_guadeloupe_reporting_calibration.py
git commit -m "feat(calibration): PAD par sous-region et par exploitation"
```

---

### Task 5: Taux de correspondance à la parcelle

**Files:**
- Modify: `case_studies/guadeloupe/reporting/calibration.py`
- Test: `tests/test_guadeloupe_reporting_calibration.py`

**Interfaces:**
- Produces: `field_match_rate(dataset, output_allocation) -> pd.DataFrame`, index région + ligne `TOTAL`, colonnes `matched_plots`, `total_plots`, `plot_match_pct`, `matched_ha`, `total_ha`, `area_match_pct`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_guadeloupe_reporting_calibration.py` :

```python
def test_field_match_rate_counts_plots_and_hectares_per_region():
    dataset = _small_dataset()
    frame = calibration.field_match_rate(dataset, _simulated())
    # R1 holds P1 (CS=CS, match, 2 ha), P2 (CS vs MA, miss, 3 ha), P5 (PN=PN, match, 3 ha).
    assert frame.loc["R1", "matched_plots"] == 2
    assert frame.loc["R1", "total_plots"] == 3
    assert frame.loc["R1", "matched_ha"] == pytest.approx(5.0)
    assert frame.loc["R1", "total_ha"] == pytest.approx(8.0)
    assert frame.loc["R1", "area_match_pct"] == pytest.approx(62.5)


def test_field_match_rate_ignores_plots_absent_from_both_sides():
    dataset = _small_dataset()
    frame = calibration.field_match_rate(dataset, _simulated())
    # P4 is NC in 2017 and unallocated by the solver: it belongs to no crop's acreage on
    # either side, so it must not inflate the denominator. P6 (yam lost) must.
    assert frame.loc["R2", "total_plots"] == 2
    assert frame.loc["R2", "matched_plots"] == 1


def test_field_match_rate_total_row():
    dataset = _small_dataset()
    total = calibration.field_match_rate(dataset, _simulated()).loc[calibration.TOTAL_KEY]
    assert total["matched_plots"] == 3
    assert total["total_plots"] == 5
    assert total["plot_match_pct"] == pytest.approx(60.0)
    assert total["matched_ha"] == pytest.approx(6.0)
    assert total["total_ha"] == pytest.approx(10.0)
    assert total["area_match_pct"] == pytest.approx(60.0)


def test_field_match_rate_is_total_when_the_simulation_reproduces_the_baseline():
    dataset = _small_dataset()
    identical = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME", "P5": "PN", "P6": "IG"})
    total = calibration.field_match_rate(dataset, identical).loc[calibration.TOTAL_KEY]
    assert total["plot_match_pct"] == pytest.approx(100.0)
    assert total["area_match_pct"] == pytest.approx(100.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_calibration.py -k field_match -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'field_match_rate'`

- [ ] **Step 3: Write minimal implementation**

Ajouter à `case_studies/guadeloupe/reporting/calibration.py` :

```python
def field_match_rate(dataset: Dataset, output_allocation: pd.Series) -> pd.DataFrame:
    """Field scale, Chopin et al. Table 5: share of plots -- and of hectares -- where the
    simulated crop equals the observed one, per sub-region and overall.

    The universe is the union of the two sides: a plot cultivated on one side only counts
    as a miss, but a plot non-cultivated on both is outside the comparison entirely.
    """
    observed = observed_groups(dataset)
    simulated = simulated_groups(dataset, output_allocation)
    plots = observed.index.union(simulated.index)

    data_parc = dataset.parameters["data_parc"]
    surface = data_parc["SURF_HA"].reindex(plots).astype(float)
    region = indicators.plot_to_region(dataset).reindex(plots)
    matched = observed.reindex(plots).eq(simulated.reindex(plots))

    frame = pd.DataFrame(
        {
            "matched_plots": matched.groupby(region).sum().astype(int),
            "total_plots": matched.groupby(region).size().astype(int),
            "matched_ha": surface.where(matched, 0.0).groupby(region).sum(),
            "total_ha": surface.groupby(region).sum(),
        }
    )
    frame.loc[TOTAL_KEY] = {
        "matched_plots": int(matched.sum()),
        "total_plots": int(len(plots)),
        "matched_ha": float(surface.where(matched, 0.0).sum()),
        "total_ha": float(surface.sum()),
    }
    frame["plot_match_pct"] = 100.0 * frame["matched_plots"] / frame["total_plots"]
    frame["area_match_pct"] = 100.0 * frame["matched_ha"] / frame["total_ha"]
    frame.index.name = "region"
    return frame[
        [
            "matched_plots",
            "total_plots",
            "plot_match_pct",
            "matched_ha",
            "total_ha",
            "area_match_pct",
        ]
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_calibration.py -v`
Expected: PASS, 15 tests

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/calibration.py tests/test_guadeloupe_reporting_calibration.py
git commit -m "feat(calibration): taux de correspondance a la parcelle par sous-region"
```

---

### Task 6: Matrice de confusion des types d'exploitation

L'échelle ferme de l'article (Table 4) compare le type de chaque exploitation avant et après simulation. Le calcul repose sur `compute_type_expl`, qui a besoin de l'univers **complet** des parcelles, `NC` comprise : une parcelle non cultivée diminue le dénominateur `surf_cultiv - surf_non` et remonte toutes les parts. Une parcelle que le solveur laisse sans culture vaut donc `NC` côté simulé.

**Files:**
- Modify: `case_studies/guadeloupe/domain/farm_typology.py` (ajout de `TYPE_EXPL_LABELS`)
- Modify: `case_studies/guadeloupe/reporting/calibration.py`
- Test: `tests/test_guadeloupe_reporting_calibration.py`, `tests/test_farm_typology.py`

**Interfaces:**
- Consumes: `farm_typology.compute_type_expl`, `farm_typology.compute_base_crop_group`.
- Produces: `farm_typology.TYPE_EXPL_LABELS: dict[int, str]`, `calibration.farm_type_confusion(dataset, output_allocation) -> pd.DataFrame` (matrice carrée d'effectifs, index `type_observe`, colonnes = mêmes codes), `calibration.farm_type_match_summary(confusion) -> dict[str, Any]`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_farm_typology.py` :

```python
def test_type_expl_labels_cover_the_eight_article_types_plus_the_edge_codes():
    from case_studies.guadeloupe.domain.farm_typology import (
        TYPE_EXPL_LABELS,
        _AVERS_BY_TYPE_EXPL,
    )

    # The eight farm types of Chopin et al. (2015) Table 2, plus 0 (no cultivated surface)
    # and -1 (the np.select default, which no condition should ever leave standing).
    assert set(TYPE_EXPL_LABELS) == {-1, 0, 1, 2, 3, 4, 5, 6, 7, 8}
    # Every type carrying a risk-aversion coefficient must be named.
    assert set(_AVERS_BY_TYPE_EXPL) <= set(TYPE_EXPL_LABELS)
```

Ajouter à `tests/test_guadeloupe_reporting_calibration.py` :

```python
def test_farm_type_confusion_is_a_square_matrix_over_the_full_type_universe():
    from case_studies.guadeloupe.domain.farm_typology import TYPE_EXPL_LABELS

    dataset = _small_dataset()
    confusion = calibration.farm_type_confusion(dataset, _simulated())
    assert list(confusion.index) == sorted(TYPE_EXPL_LABELS)
    assert list(confusion.columns) == sorted(TYPE_EXPL_LABELS)
    assert confusion.to_numpy().sum() == 3  # one cell per farm, three farms


def test_farm_type_confusion_tracks_the_farm_that_changed_type():
    dataset = _small_dataset()
    confusion = calibration.farm_type_confusion(dataset, _simulated())
    # E1 is 100% cane observed -> "specialised cane growers" (3). Simulated it is 40% cane
    # and 60% market gardening, which no dominance threshold catches -> "diversified" (5).
    assert confusion.loc[3, 5] == 1
    # E2 (melon + non-cultivated) and E3 (pasture-dominant) keep their type.
    assert confusion.loc[5, 5] == 1
    assert confusion.loc[6, 6] == 1


def test_farm_type_match_summary_reports_the_diagonal_share():
    dataset = _small_dataset()
    confusion = calibration.farm_type_confusion(dataset, _simulated())
    summary = calibration.farm_type_match_summary(confusion)
    assert summary["total_farms"] == 3
    assert summary["matched_farms"] == 2
    assert summary["match_pct"] == pytest.approx(200.0 / 3)
    # Per-type recall, keyed by the readable label, only for types actually observed.
    assert summary["recall_by_type"]["Canniers specialises"] == pytest.approx(0.0)
    assert summary["recall_by_type"]["Eleveurs"] == pytest.approx(100.0)
    assert "Bananiers" not in summary["recall_by_type"]


def test_farm_type_confusion_is_diagonal_when_the_simulation_reproduces_the_baseline():
    dataset = _small_dataset()
    identical = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME", "P5": "PN", "P6": "IG"})
    confusion = calibration.farm_type_confusion(dataset, identical)
    summary = calibration.farm_type_match_summary(confusion)
    assert summary["match_pct"] == pytest.approx(100.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_calibration.py tests/test_farm_typology.py -k "type" -v`
Expected: FAIL — `ImportError: cannot import name 'TYPE_EXPL_LABELS'`

- [ ] **Step 3: Write minimal implementation**

Dans `case_studies/guadeloupe/domain/farm_typology.py`, ajouter juste après `_AVERS_BY_TYPE_EXPL_BIS` (ligne 54) :

```python
# Readable names for the TYPE_EXPL codes. The eight types are those of Chopin et al. (2015)
# Table 2; 0 is the "no cultivated surface" short-circuit at the end of compute_type_expl,
# and -1 is np.select's default, which the cascade's final catch-all should make
# unreachable. ASCII only: these labels reach recap.md, which carries no accents.
TYPE_EXPL_LABELS: dict[int, str] = {
    -1: "Non classe",
    0: "Sans surface cultivee",
    1: "Arboriculteurs",
    2: "Bananiers",
    3: "Canniers specialises",
    4: "Canniers diversifies",
    5: "Diversifies",
    6: "Eleveurs",
    7: "Maraichers",
    8: "Canniers-eleveurs",
}
```

Dans `case_studies/guadeloupe/reporting/calibration.py`, compléter les imports :

```python
from case_studies.guadeloupe.domain.farm_typology import (
    TYPE_EXPL_LABELS,
    compute_base_crop_group,
    compute_type_expl,
)
```

et ajouter :

```python
def _type_expl(dataset: Dataset, groups: pd.Series) -> pd.Series:
    """farm -> TYPE_EXPL, for a plot -> base-group Series covering the full plot universe."""
    plot_surface = dataset.parameters["data_parc"]["SURF_HA"]
    type_expl, _bis = compute_type_expl(
        dataset.parameters["farm_plots"], groups, plot_surface
    )
    return type_expl


def farm_type_confusion(dataset: Dataset, output_allocation: pd.Series) -> pd.DataFrame:
    """Farm scale, Chopin et al. Table 4: observed farm type x simulated farm type.

    Both sides go through compute_type_expl, which needs the FULL plot universe: NC plots
    feed surf_non, which is subtracted from the denominator of every PART_* share. Dropping
    them -- as the NC-free baseline allocation does -- would shift the shares and could flip
    a farm's type, so the observed side is recomputed here from data_parc and a plot the
    solver left unallocated counts as NC, its agronomic meaning.

    One asymmetry is deliberate: compute_base_crop_group returns NaN for an RPG code it
    does not map, and compute_type_expl drops those rows. That is what the pipeline already
    does for the observed side, so it is reproduced rather than "fixed" here.
    """
    data_parc = dataset.parameters["data_parc"]
    observed = compute_base_crop_group(data_parc["cult_2016"], data_parc["cult_2017"])

    simulated = pd.Series(crop_families.NON_CULTIVATED, index=data_parc.index)
    simulated.update(crop_families.base_groups_for(output_allocation))

    codes = sorted(TYPE_EXPL_LABELS)
    confusion = pd.crosstab(_type_expl(dataset, observed), _type_expl(dataset, simulated))
    confusion = confusion.reindex(index=codes, columns=codes, fill_value=0).astype(int)
    confusion.index.name = "type_observe"
    confusion.columns.name = "type_simule"
    return confusion


def farm_type_match_summary(confusion: pd.DataFrame) -> dict[str, Any]:
    """Diagonal share of a confusion matrix, plus per-type recall for the types actually
    present in the observed data (a type nobody starts in has no recall to report)."""
    total = int(confusion.to_numpy().sum())
    matched = int(sum(confusion.loc[code, code] for code in confusion.index))
    observed_totals = confusion.sum(axis=1)
    return {
        "total_farms": total,
        "matched_farms": matched,
        "match_pct": 100.0 * matched / total if total else float("nan"),
        "recall_by_type": {
            TYPE_EXPL_LABELS[code]: 100.0 * float(confusion.loc[code, code]) / float(count)
            for code, count in observed_totals.items()
            if count > 0
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_calibration.py tests/test_farm_typology.py -v`
Expected: PASS — 19 tests de calibration + la suite typologie existante

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/domain/farm_typology.py case_studies/guadeloupe/reporting/calibration.py tests/test_guadeloupe_reporting_calibration.py tests/test_farm_typology.py
git commit -m "feat(calibration): matrice de confusion des types d'exploitation"
```

---

### Task 7: Assemblage `evaluate` et résumé sérialisable

**Files:**
- Modify: `case_studies/guadeloupe/reporting/calibration.py`
- Test: `tests/test_guadeloupe_reporting_calibration.py`

**Interfaces:**
- Produces: `CalibrationResult` (dataclass gelée : `thresholds`, `pad_by_crop`, `pad_by_crop_and_region`, `pad_by_farm`, `farm_type_confusion`, `field_match`), `CalibrationResult.summary() -> dict[str, Any]`, `evaluate(dataset, output_allocation, config) -> CalibrationResult`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_guadeloupe_reporting_calibration.py` :

```python
def test_evaluate_returns_every_block():
    dataset = _small_dataset()
    result = calibration.evaluate(dataset, _simulated(), {})
    assert result.pad_by_crop.loc["CS", "pad_pct"] == pytest.approx(60.0)
    assert result.pad_by_crop_and_region.loc[("R2", "IG"), "pad_pct"] == pytest.approx(100.0)
    assert result.pad_by_farm.loc["E2", "pad_pct"] == pytest.approx(0.0)
    assert result.farm_type_confusion.loc[3, 5] == 1
    assert result.field_match.loc[calibration.TOTAL_KEY, "plot_match_pct"] == pytest.approx(60.0)
    assert result.thresholds.regional_pad_max == 15.0


def test_summary_is_json_serialisable_and_carries_the_verdicts():
    import json

    dataset = _small_dataset()
    summary = calibration.evaluate(dataset, _simulated(), {}).summary()

    json.dumps(summary)  # must not raise: no numpy scalars, no pandas NA

    assert summary["thresholds"]["regional_pad_max"] == 15.0
    assert summary["regional_pad_pct"] == pytest.approx(70.0)
    assert summary["regional_within_threshold"] is False
    assert summary["crops_evaluated"] == 4      # CS, IG, ME, PN -- MA has no observed base
    assert summary["crops_within_threshold"] == 2  # ME and PN
    assert summary["farms_evaluated"] == 3
    assert summary["farms_within_threshold"] == 1
    assert summary["farm_type_match_pct"] == pytest.approx(200.0 / 3)
    assert summary["farm_type_within_threshold"] is False
    assert summary["plot_match_pct"] == pytest.approx(60.0)
    assert summary["area_match_pct"] == pytest.approx(60.0)


def test_summary_verdicts_are_all_green_on_a_perfect_reproduction():
    dataset = _small_dataset()
    identical = pd.Series({"P1": "CS", "P2": "CS", "P3": "ME", "P5": "PN", "P6": "IG"})
    summary = calibration.evaluate(dataset, identical, {}).summary()
    assert summary["regional_pad_pct"] == pytest.approx(0.0)
    assert summary["regional_within_threshold"] is True
    assert summary["farm_type_within_threshold"] is True
    assert summary["plot_match_pct"] == pytest.approx(100.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_calibration.py -k "evaluate or summary" -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'evaluate'`

- [ ] **Step 3: Write minimal implementation**

Ajouter à `case_studies/guadeloupe/reporting/calibration.py` (`from dataclasses import asdict, dataclass` en tête) :

```python
def _optional_float(value: Any) -> float | None:
    """JSON has no NaN: an undefined metric is None, not a float that json.dumps emits as
    the invalid literal NaN."""
    if value is None or pd.isna(value):
        return None
    return float(value)


@dataclass(frozen=True)
class CalibrationResult:
    """Every block of Chopin et al. §2.6 for one run, plus the thresholds they are read
    against. Frames are for CSV and figures; summary() is what goes into recap.json."""

    thresholds: CalibrationThresholds
    pad_by_crop: pd.DataFrame
    pad_by_crop_and_region: pd.DataFrame
    pad_by_farm: pd.DataFrame
    farm_type_confusion: pd.DataFrame
    field_match: pd.DataFrame

    def summary(self) -> dict[str, Any]:
        crops = self.pad_by_crop.drop(index=TOTAL_KEY)
        total = self.pad_by_crop.loc[TOTAL_KEY]
        subregional = self.pad_by_crop_and_region[
            self.pad_by_crop_and_region.index.get_level_values("crop") != TOTAL_KEY
        ]
        farms = self.pad_by_farm
        field_total = self.field_match.loc[TOTAL_KEY]
        farm_type = farm_type_match_summary(self.farm_type_confusion)

        # Verdicts are recomputed from the numeric PAD rather than read off the
        # within_threshold column: that column is a nullable BooleanDtype whose scalars do
        # not compare cleanly with `is True`, and bool(pd.NA) raises outright.
        regional_pad = _optional_float(total["pad_pct"])
        farm_type_pct = _optional_float(farm_type["match_pct"])

        def _count_true(column: pd.Series) -> int:
            return int(column.fillna(False).astype(bool).sum())

        return {
            "thresholds": asdict(self.thresholds),
            "regional_pad_pct": regional_pad,
            "regional_within_threshold": (
                regional_pad is not None and regional_pad <= self.thresholds.regional_pad_max
            ),
            "crops_evaluated": int(crops["within_threshold"].notna().sum()),
            "crops_within_threshold": _count_true(crops["within_threshold"]),
            "subregional_cells_evaluated": int(subregional["within_threshold"].notna().sum()),
            "subregional_cells_within_threshold": _count_true(subregional["within_threshold"]),
            "farms_evaluated": int(farms["within_threshold"].notna().sum()),
            "farms_within_threshold": _count_true(farms["within_threshold"]),
            "farm_type_match_pct": farm_type_pct,
            "farm_type_within_threshold": (
                farm_type_pct is not None
                and farm_type_pct >= self.thresholds.farm_type_match_min
            ),
            "farm_type_recall_by_type": {
                label: float(value) for label, value in farm_type["recall_by_type"].items()
            },
            "matched_plots": int(field_total["matched_plots"]),
            "total_plots": int(field_total["total_plots"]),
            "plot_match_pct": _optional_float(field_total["plot_match_pct"]),
            "matched_ha": float(field_total["matched_ha"]),
            "total_ha": float(field_total["total_ha"]),
            "area_match_pct": _optional_float(field_total["area_match_pct"]),
        }


def evaluate(
    dataset: Dataset, output_allocation: pd.Series, config: dict[str, Any]
) -> CalibrationResult:
    """Every calibration metric for one solved allocation. No solve, no file written."""
    thresholds = thresholds_from_config(config)
    return CalibrationResult(
        thresholds=thresholds,
        pad_by_crop=pad_by_crop(dataset, output_allocation, thresholds),
        pad_by_crop_and_region=pad_by_crop_and_region(dataset, output_allocation, thresholds),
        pad_by_farm=pad_by_farm(dataset, output_allocation, thresholds),
        farm_type_confusion=farm_type_confusion(dataset, output_allocation),
        field_match=field_match_rate(dataset, output_allocation),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_calibration.py -v`
Expected: PASS, 22 tests

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/calibration.py tests/test_guadeloupe_reporting_calibration.py
git commit -m "feat(calibration): assemblage evaluate() et resume serialisable"
```

---

### Task 8: Figures régionale et heatmap sous-régionale

**Files:**
- Modify: `case_studies/guadeloupe/reporting/plots.py`
- Test: `tests/test_guadeloupe_reporting_plots.py`

**Interfaces:**
- Consumes: `calibration.TOTAL_KEY`, `domain.zones.region_label`, `crop_labels.label_for`.
- Produces: `plots.plot_calibration_regional(pad_by_crop, output_path) -> Path`, `plots.plot_calibration_pad_heatmap(pad_by_crop_and_region, output_path) -> Path`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_guadeloupe_reporting_plots.py` :

```python
def test_plot_calibration_regional_writes_a_png(tmp_path):
    import pandas as pd

    from case_studies.guadeloupe.reporting import plots

    frame = pd.DataFrame(
        {
            "observed_ha": [5.0, 3.0, 10.0],
            "simulated_ha": [2.0, 3.0, 5.0],
            "abs_deviation_ha": [3.0, 0.0, 3.0],
            "pad_pct": [60.0, 0.0, 37.5],
            "within_threshold": pd.array([False, True, False], dtype="boolean"),
        },
        index=["CS", "PN", "TOTAL"],
    )
    path = plots.plot_calibration_regional(frame, tmp_path / "calib.png")
    assert path.exists()
    assert path.stat().st_size > 0


def test_plot_calibration_pad_heatmap_writes_a_png(tmp_path):
    import pandas as pd

    from case_studies.guadeloupe.reporting import plots

    index = pd.MultiIndex.from_tuples(
        [("1", "CS"), ("1", "PN"), ("1", "TOTAL"), ("2", "CS"), ("2", "TOTAL")],
        names=["region", "crop"],
    )
    frame = pd.DataFrame({"pad_pct": [60.0, 0.0, 30.0, 12.0, 12.0]}, index=index)
    path = plots.plot_calibration_pad_heatmap(frame, tmp_path / "heatmap.png")
    assert path.exists()
    assert path.stat().st_size > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_plots.py -k calibration -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'plot_calibration_regional'`

- [ ] **Step 3: Write minimal implementation**

Dans `case_studies/guadeloupe/reporting/plots.py`, ajouter en tête l'import `import numpy as np` et `from case_studies.guadeloupe.domain.zones import region_label`, puis en fin de fichier :

```python
_OBSERVED_COLOR = "#8C8C8C"
_SIMULATED_COLOR = _BAR_COLOR
_TOTAL_KEY = "TOTAL"


def plot_calibration_regional(pad_by_crop: pd.DataFrame, output_path: Path) -> Path:
    """Observed vs simulated acreage per crop, Chopin et al. (2015) Fig. 4. The TOTAL row
    is dropped: it is a different quantity from the per-crop bars and would dwarf them."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = pad_by_crop.drop(index=_TOTAL_KEY, errors="ignore").sort_values(
        "observed_ha", ascending=False
    )
    positions = np.arange(len(frame))
    width = 0.4

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    ax.bar(
        positions - width / 2, frame["observed_ha"].to_numpy(),
        width, label="Observé 2017", color=_OBSERVED_COLOR,
    )
    ax.bar(
        positions + width / 2, frame["simulated_ha"].to_numpy(),
        width, label="Simulé", color=_SIMULATED_COLOR,
    )
    ax.set_xticks(positions)
    ax.set_xticklabels(_relabel_crops(frame.index))
    _style_axes(ax, title="Calibration : surface observée vs simulée", ylabel="Hectares")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)
    return output_path


def plot_calibration_pad_heatmap(
    pad_by_crop_and_region: pd.DataFrame, output_path: Path
) -> Path:
    """PAD per (sub-region, crop), Chopin et al. (2015) Fig. 5 read as a heatmap: the point
    of the figure is which cells breach the threshold, which reads faster than seven
    side-by-side bar panels. Per-region TOTAL rows are dropped."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = pad_by_crop_and_region[
        pad_by_crop_and_region.index.get_level_values("crop") != _TOTAL_KEY
    ]
    grid = frame["pad_pct"].unstack("crop")

    fig, ax = plt.subplots(figsize=_FIGSIZE)
    # Clipped at 100: beyond a full deviation the exact value carries no extra meaning, and
    # letting it run makes every other cell washed out.
    image = ax.imshow(
        grid.to_numpy(dtype=float), cmap="RdYlGn_r", vmin=0.0, vmax=100.0, aspect="auto"
    )
    ax.set_xticks(np.arange(len(grid.columns)))
    ax.set_xticklabels(_relabel_crops(grid.columns))
    ax.set_yticks(np.arange(len(grid.index)))
    ax.set_yticklabels([region_label(key) for key in grid.index])
    ax.set_title("Calibration : PAD (%) par sous-région et culture", fontweight="bold")
    for tick in ax.get_xticklabels():
        tick.set_rotation(45)
        tick.set_horizontalalignment("right")
    fig.colorbar(image, ax=ax, label="PAD (%)")
    fig.tight_layout()
    fig.savefig(output_path, dpi=_DPI)
    plt.close(fig)
    return output_path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_plots.py -v`
Expected: PASS — les deux nouveaux tests et toute la suite existante

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/plots.py tests/test_guadeloupe_reporting_plots.py
git commit -m "feat(calibration): figures observe-vs-simule et heatmap du PAD"
```

---

### Task 9: Branchement dans `generate_report`

**Files:**
- Modify: `case_studies/guadeloupe/reporting/report.py`
- Modify: `case_studies/guadeloupe/config.yaml` (après le bloc `reporting.environment`, ligne 57)
- Test: `tests/test_guadeloupe_reporting_report.py`

**Interfaces:**
- Consumes: `calibration.evaluate`, `plots.plot_calibration_regional`, `plots.plot_calibration_pad_heatmap`.
- Produces: `report.write_calibration(result, output_dir) -> None` (public : la tâche 11 l'appelle aussi) ; fichiers `csv/calibration_pad_by_crop.csv`, `csv/calibration_pad_by_crop_and_region.csv`, `csv/calibration_pad_by_farm.csv`, `csv/calibration_farm_type_confusion.csv`, `csv/calibration_field_match.csv`, `plots/calibration_regional.png`, `plots/calibration_pad_heatmap.png` ; clé `recap["calibration"]` ; section « Calibration » dans `recap.md`.

- [ ] **Step 1: Write the failing test**

`calibration.farm_type_confusion` lit `dataset.parameters["farm_plots"]`, que `_tiny_dataset` ne fournit pas encore. Ajouter la clé au dictionnaire `parameters` de `_tiny_dataset` (`tests/test_guadeloupe_reporting_report.py:70-100`), à côté de `"expl_parc"` :

```python
            # Needed by calibration.farm_type_confusion, which recomputes the farm typology
            # on both sides through farm_typology.compute_type_expl.
            "farm_plots": {"E1": ["P1", "P2"]},
```

Puis ajouter le test, en suivant le motif inline des tests existants du fichier (`test_generate_report_writes_full_output_folder:105-119`) :

```python
def test_generate_report_writes_the_calibration_block(tmp_path):
    dataset = _tiny_dataset()
    model = build_crop_allocation_model(
        ModelInputs(
            plot_surface_ha={"P1": 2.0, "P2": 3.0},
            crop_margin_per_ha={"CS": 100.0, "ME": 200.0},
            eligible_pairs=[("P1", "CS"), ("P1", "ME"), ("P2", "CS"), ("P2", "ME")],
        ),
        _CONFIG,
    )
    results = solve_model(model, _CONFIG)

    output_dir = report.generate_report(
        dataset, _CONFIG, model, results, duration=1.23, outputs_root=tmp_path
    )

    for name in (
        "calibration_pad_by_crop.csv",
        "calibration_pad_by_crop_and_region.csv",
        "calibration_pad_by_farm.csv",
        "calibration_farm_type_confusion.csv",
        "calibration_field_match.csv",
    ):
        assert (output_dir / "csv" / name).exists(), name

    assert (output_dir / "plots" / "calibration_regional.png").exists()
    assert (output_dir / "plots" / "calibration_pad_heatmap.png").exists()

    recap = json.loads((output_dir / "recap.json").read_text())
    assert "calibration" in recap
    assert recap["calibration"]["thresholds"]["regional_pad_max"] == 15.0
    assert "regional_pad_pct" in recap["calibration"]
    assert "plot_match_pct" in recap["calibration"]

    assert "## Calibration" in (output_dir / "recap.md").read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_report.py -k calibration -v`
Expected: FAIL — `AssertionError: calibration_pad_by_crop.csv`

- [ ] **Step 3: Write minimal implementation**

Dans `case_studies/guadeloupe/config.yaml`, sous `reporting:` (après le bloc `environment`, ligne 57) :

```yaml
  # Calibration thresholds, from Chopin et al. (2015) §2.6: percentage of absolute
  # deviation (PAD) between the observed 2017 acreage and the simulated one. The article
  # takes these values from Kanellopoulos et al. (2010), Hazell and Norton (1986) and
  # Janssen and van Ittersum (2007) -- they are review conventions, not model constraints,
  # and changing them changes only the verdicts printed in the recap.
  calibration:
    regional_pad_max: 15       # PAD (%) tolerated per crop over the whole territory
    subregional_pad_max: 20    # PAD (%) tolerated per crop within a sub-region
    farm_pad_max: 20           # PAD (%) tolerated per farm
    farm_type_match_min: 80    # minimum share (%) of farms simulated in their observed type
```

Dans `case_studies/guadeloupe/reporting/report.py`, ajouter `calibration` à l'import ligne 14 :

```python
from case_studies.guadeloupe.reporting import calibration, indicators, plots
```

Dans `generate_report`, après la ligne 61 (`_write_shannon_and_surface_by_key(...)`) :

```python
    calibration_result = calibration.evaluate(dataset, output_allocation, config)
    write_calibration(calibration_result, output_dir)
```

Passer le résumé à `_build_recap` en ajoutant l'argument nommé `calibration_summary=calibration_result.summary()` à l'appel ligne 94, le paramètre correspondant `calibration_summary: dict[str, Any]` à la signature de `_build_recap`, et la clé `"calibration": calibration_summary,` au dictionnaire retourné (juste après `"resilience": resilience,`).

Ajouter la fonction d'écriture, à côté de `_write_shannon_and_surface_by_key` :

```python
def write_calibration(result: calibration.CalibrationResult, output_dir: Path) -> None:
    """Persist the observed-vs-simulated calibration blocks (Chopin et al. 2015 §2.6).

    Public because scripts/evaluate_calibration.py writes the same files into a past run's
    folder. Reporting only: these numbers grade the run, they never feed back into it.
    """
    result.pad_by_crop.to_csv(_csv_path(output_dir, "calibration_pad_by_crop.csv"))
    result.pad_by_crop_and_region.to_csv(
        _csv_path(output_dir, "calibration_pad_by_crop_and_region.csv")
    )
    result.pad_by_farm.to_csv(_csv_path(output_dir, "calibration_pad_by_farm.csv"))
    result.farm_type_confusion.to_csv(
        _csv_path(output_dir, "calibration_farm_type_confusion.csv")
    )
    result.field_match.to_csv(_csv_path(output_dir, "calibration_field_match.csv"))

    plots.plot_calibration_regional(
        result.pad_by_crop, output_dir / "plots" / "calibration_regional.png"
    )
    plots.plot_calibration_pad_heatmap(
        result.pad_by_crop_and_region, output_dir / "plots" / "calibration_pad_heatmap.png"
    )
```

Dans `_render_recap_markdown`, ajouter avant le `return` final :

```python
    calib = recap["calibration"]

    def _verdict(passed: bool) -> str:
        return "OK" if passed else "HORS SEUIL"

    def _pct(value: float | None) -> str:
        return "n/a" if value is None else f"{value:,.1f}%"

    lines += [
        "",
        "## Calibration (observe 2017 vs simule)",
        "_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015"
        " section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._",
        f"- PAD territorial : {_pct(calib['regional_pad_pct'])} "
        f"(seuil {calib['thresholds']['regional_pad_max']:.0f}%) "
        f"-> {_verdict(calib['regional_within_threshold'])}",
        f"- Cultures sous seuil : {calib['crops_within_threshold']} / {calib['crops_evaluated']}",
        f"- Cellules sous-regionales sous seuil : "
        f"{calib['subregional_cells_within_threshold']} / {calib['subregional_cells_evaluated']} "
        f"(seuil {calib['thresholds']['subregional_pad_max']:.0f}%)",
        f"- Exploitations sous seuil : {calib['farms_within_threshold']} / "
        f"{calib['farms_evaluated']} (seuil {calib['thresholds']['farm_pad_max']:.0f}%)",
        f"- Types d'exploitation correctement simules : {_pct(calib['farm_type_match_pct'])} "
        f"(seuil {calib['thresholds']['farm_type_match_min']:.0f}%) "
        f"-> {_verdict(calib['farm_type_within_threshold'])}",
        f"- Parcelles avec la bonne culture : {_pct(calib['plot_match_pct'])} "
        f"({calib['matched_plots']} / {calib['total_plots']})",
        f"- Surface avec la bonne culture : {_pct(calib['area_match_pct'])} "
        f"({calib['matched_ha']:,.0f} / {calib['total_ha']:,.0f} ha)",
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_report.py tests/test_guadeloupe_config.py -v`
Expected: PASS — le nouveau test, la suite rapport existante et la validation de config

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/report.py case_studies/guadeloupe/config.yaml tests/test_guadeloupe_reporting_report.py
git commit -m "feat(calibration): ecrire les metriques dans chaque run et dans le recap"
```

---

### Task 10: Couverture par le golden snapshot

Le golden tourne sur `decode_baseline_representative_allocation`, qui remappe chaque famille observée vers une variante fine. Comme `base_group_for` doit ramener cette variante sur sa famille d'origine, les blocs de calibration y sortent parfaits. C'est l'invariant utile : si quelqu'un fait pointer `baseline_representative_crops` vers une variante qui ne revient pas sur sa famille, le golden le voit. L'arithmétique, elle, est couverte par les tests unitaires.

**Files:**
- Modify: `scripts/golden_snapshot.py:77-105`

**Interfaces:**
- Consumes: `calibration.evaluate`, `_summarise_frame`, `flatten`.

- [ ] **Step 1: Extend the snapshot**

Dans `scripts/golden_snapshot.py`, ajouter l'import :

```python
from case_studies.guadeloupe.reporting import calibration, indicators
```

et, dans `_snapshot_indicators`, avant `return snapshot` :

```python
    # Calibration blocks. The allocation here is the representative baseline, which folds
    # back onto its own observed families, so every PAD is 0 and the confusion matrix is
    # diagonal. That is the point: this checksum guards the round-trip between
    # config's baseline_representative_crops and crop_families.base_group_for. Drift in the
    # arithmetic is caught by tests/test_guadeloupe_reporting_calibration.py instead.
    calib = calibration.evaluate(dataset, allocation, config)
    snapshot.update(flatten("calib", calib.summary()))
    snapshot["calib_pad_by_crop"] = _summarise_frame(calib.pad_by_crop)
    snapshot["calib_pad_by_region"] = _summarise_frame(calib.pad_by_crop_and_region)
    snapshot["calib_pad_by_farm"] = _summarise_frame(calib.pad_by_farm)
    snapshot["calib_confusion"] = _summarise_frame(calib.farm_type_confusion)
    snapshot["calib_field_match"] = _summarise_frame(calib.field_match)
```

`flatten` sérialise `farm_type_recall_by_type` (dictionnaire imbriqué) en `calib.farm_type_recall_by_type.<label>` — comportement attendu, un label qui change fait apparaître un `NEW`/`MISSING` explicite dans le diff.

- [ ] **Step 2: Verify the new checksums appear**

Run: `.venv/Scripts/python scripts/golden_snapshot.py --write`
Expected: `wrote ...\.golden\snapshot.json (N checksums)` avec N supérieur à la valeur précédente (~511)

- [ ] **Step 3: Verify the perfect-reproduction invariant**

Run: `.venv/Scripts/python -c "import json,pathlib; s=json.loads(pathlib.Path('.golden/snapshot.json').read_text()); i=s['indicators']; print(i['calib.regional_pad_pct'], i['calib.plot_match_pct'], i['calib.farm_type_match_pct'])"`
Expected: `0.0 100.0 100.0` — le PAD est nul et la reproduction parfaite sur l'allocation identité. Si ce n'est pas le cas, une famille de `baseline_representative_crops` ne revient pas sur elle-même via `crop_families.base_group_for` : corriger la correspondance avant de continuer.

- [ ] **Step 4: Verify the check mode is stable**

Run: `.venv/Scripts/python scripts/golden_snapshot.py --check`
Expected: `OK (N checksums unchanged)`

- [ ] **Step 5: Commit**

```bash
git add scripts/golden_snapshot.py
git commit -m "test(calibration): couvrir les blocs de calibration dans le golden snapshot"
```

---

### Task 11: Script post-hoc `evaluate_calibration.py`

**Files:**
- Create: `scripts/evaluate_calibration.py`
- Test: `tests/test_evaluate_calibration.py`

**Interfaces:**
- Consumes: `scripts._common.CONFIG_PATH`, `scripts._common.OUTPUTS_ROOT`, `core.config.load_config`, `data_pipeline.build_dataset`, `calibration.evaluate`, `report.write_calibration`, `dashboard.loaders.list_output_runs`.
- Produces: `load_simulated_allocation(run_dir) -> pd.Series`, `evaluate_run(run_dir) -> calibration.CalibrationResult`, `main(argv) -> int`.

- [ ] **Step 1: Write the failing test**

Créer `tests/test_evaluate_calibration.py` :

```python
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import evaluate_calibration


def test_load_simulated_allocation_reads_the_output_csv(tmp_path):
    run_dir = tmp_path / "output_1"
    (run_dir / "csv").mkdir(parents=True)
    (run_dir / "csv" / "allocation_output.csv").write_text(
        "plot,crop,farm,region,island,surface_ha\n"
        "P1,CS_NGT_NISM,E1,1,2,2.0\n"
        "P2,MA_ROTA,E1,1,2,3.0\n"
    )
    allocation = evaluate_calibration.load_simulated_allocation(run_dir)
    assert allocation.to_dict() == {"P1": "CS_NGT_NISM", "P2": "MA_ROTA"}
    assert allocation.name == "crop"


def test_load_simulated_allocation_falls_back_to_the_run_root(tmp_path):
    # Runs written before the csv/ reorg keep their CSVs at the run root.
    run_dir = tmp_path / "output_2"
    run_dir.mkdir(parents=True)
    (run_dir / "allocation_output.csv").write_text(
        "plot,crop,farm,region,island,surface_ha\nP1,PN_TOUR,E1,1,2,2.0\n"
    )
    assert evaluate_calibration.load_simulated_allocation(run_dir).to_dict() == {"P1": "PN_TOUR"}


def test_load_simulated_allocation_reports_a_missing_run(tmp_path):
    run_dir = tmp_path / "output_3"
    run_dir.mkdir()
    with pytest.raises(FileNotFoundError, match="allocation_output.csv"):
        evaluate_calibration.load_simulated_allocation(run_dir)


def test_run_config_prefers_the_run_s_own_config(tmp_path):
    run_dir = tmp_path / "output_4"
    run_dir.mkdir()
    (run_dir / "config_used.yaml").write_text("reporting:\n  calibration:\n    farm_pad_max: 42\n")
    config = evaluate_calibration.load_run_config(run_dir)
    assert config["reporting"]["calibration"]["farm_pad_max"] == 42
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_evaluate_calibration.py -v`
Expected: FAIL — `ImportError: cannot import name 'evaluate_calibration' from 'scripts'`

- [ ] **Step 3: Write minimal implementation**

Créer `scripts/evaluate_calibration.py` :

```python
"""Score a past run against the observed 2017 land use (Chopin et al. 2015, §2.6).

Reads a run's simulated allocation from its allocation_output.csv, rebuilds the dataset
from the run's own config_used.yaml (~7s, no MILP solve), computes every calibration block
and writes them next to the run's other CSVs -- exactly what generate_report now does for
new runs, made available for the runs that predate it.

    python scripts/evaluate_calibration.py outputs/output_12
    python scripts/evaluate_calibration.py --all

The dataset rebuild is not optional: the farm-type confusion matrix needs the full plot
universe, NC plots included, and allocation_input.csv drops them. Scoring from the CSVs
alone would shift the PART_* shares and could flip a farm's type.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import yaml

from case_studies.guadeloupe.dashboard.loaders import list_output_runs
from case_studies.guadeloupe.pipeline.data_pipeline import build_dataset
from case_studies.guadeloupe.reporting import calibration
from case_studies.guadeloupe.reporting.report import write_calibration
from core.config import load_config

from scripts._common import CONFIG_PATH, OUTPUTS_ROOT

_ALLOCATION_CSV = "allocation_output.csv"


def load_simulated_allocation(run_dir: Path) -> pd.Series:
    """plot -> fine crop, from a run's allocation_output.csv (csv/ or, for older runs,
    the run root)."""
    path = run_dir / "csv" / _ALLOCATION_CSV
    if not path.exists():
        path = run_dir / _ALLOCATION_CSV
    if not path.exists():
        raise FileNotFoundError(f"{run_dir}: no {_ALLOCATION_CSV} (csv/ or run root)")
    frame = pd.read_csv(path)
    return pd.Series(frame["crop"].to_numpy(), index=frame["plot"], name="crop")


def load_run_config(run_dir: Path) -> dict:
    """The run's own config_used.yaml, so the zone_filter and thresholds it ran with are
    the ones it is scored with. Falls back to the current config.yaml for runs that predate
    config_used.yaml."""
    path = run_dir / "config_used.yaml"
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    return load_config(CONFIG_PATH)


def evaluate_run(run_dir: Path) -> calibration.CalibrationResult:
    config = load_run_config(run_dir)
    dataset = build_dataset(config)
    result = calibration.evaluate(dataset, load_simulated_allocation(run_dir), config)
    write_calibration(result, run_dir)
    return result


def _print_verdicts(run_dir: Path, result: calibration.CalibrationResult) -> None:
    summary = result.summary()

    def line(label: str, value: float | None, threshold: float, ok: bool) -> str:
        shown = "n/a" if value is None else f"{value:6.1f}%"
        return f"  {label:<34} {shown}  (seuil {threshold:.0f}%)  {'OK' if ok else 'HORS SEUIL'}"

    print(f"\n{run_dir.name}")
    print(
        line(
            "PAD territorial",
            summary["regional_pad_pct"],
            summary["thresholds"]["regional_pad_max"],
            summary["regional_within_threshold"],
        )
    )
    print(
        line(
            "Types d'exploitation reproduits",
            summary["farm_type_match_pct"],
            summary["thresholds"]["farm_type_match_min"],
            summary["farm_type_within_threshold"],
        )
    )
    print(
        f"  {'Cultures sous seuil':<34} "
        f"{summary['crops_within_threshold']} / {summary['crops_evaluated']}"
    )
    print(
        f"  {'Exploitations sous seuil':<34} "
        f"{summary['farms_within_threshold']} / {summary['farms_evaluated']}"
    )
    print(
        f"  {'Parcelles bien simulees':<34} {summary['plot_match_pct']:6.1f}%  "
        f"({summary['matched_plots']} / {summary['total_plots']})"
    )
    print(f"  {'Surface bien simulee':<34} {summary['area_match_pct']:6.1f}%")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", nargs="?", type=Path, help="An outputs/output_N folder.")
    parser.add_argument("--all", action="store_true", help="Score every run in outputs/.")
    args = parser.parse_args(argv)
    if bool(args.run_dir) == args.all:
        parser.error("pass exactly one of a run folder / --all")

    # list_output_runs already filters outputs/ to well-formed output_N folders and sorts
    # them; it is Streamlit-free by design, so a script may use it.
    runs = list_output_runs(OUTPUTS_ROOT) if args.all else [args.run_dir]

    failures = 0
    for run_dir in runs:
        try:
            _print_verdicts(run_dir, evaluate_run(run_dir))
        except (FileNotFoundError, KeyError) as error:
            print(f"\n{run_dir.name}\n  ignore : {error}", file=sys.stderr)
            failures += 1
    return 1 if failures and len(runs) == 1 else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_evaluate_calibration.py -v`
Expected: PASS, 4 tests

- [ ] **Step 5: Score the existing runs**

Run: `.venv/Scripts/python scripts/evaluate_calibration.py outputs/output_12`
Expected: le bloc de verdicts, et cinq nouveaux `calibration_*.csv` dans `outputs/output_12/csv/`. Le PAD territorial doit ressortir très élevé — voir la section « diagnostic attendu » de la spec ; ce n'est pas une défaillance du script.

- [ ] **Step 6: Commit**

```bash
git add scripts/evaluate_calibration.py tests/test_evaluate_calibration.py
git commit -m "feat(calibration): script post-hoc pour scorer un run existant"
```

---

### Task 12: Page dashboard

**Files:**
- Create: `case_studies/guadeloupe/dashboard/pages/3_Calibration.py`
- Modify: `case_studies/guadeloupe/dashboard/loaders.py`
- Test: `tests/test_guadeloupe_dashboard_loaders.py`

**Interfaces:**
- Consumes: `loaders.list_output_runs`, `loaders.load_recap`, `loaders.run_display_name`, `loaders.load_csv`, `zones.region_label`, `farm_typology.TYPE_EXPL_LABELS`, `crop_labels.label_for`.
- Produces: `loaders.load_calibration(run_dir, name) -> pd.DataFrame | None`.

- [ ] **Step 1: Write the failing test**

Ajouter à `tests/test_guadeloupe_dashboard_loaders.py` :

```python
def test_load_calibration_reads_a_block(tmp_path):
    run_dir = tmp_path / "output_1"
    (run_dir / "csv").mkdir(parents=True)
    (run_dir / "csv" / "calibration_pad_by_crop.csv").write_text(
        "crop,observed_ha,simulated_ha,abs_deviation_ha,pad_pct,within_threshold\n"
        "CS,5.0,2.0,3.0,60.0,False\n"
        "TOTAL,5.0,2.0,3.0,60.0,False\n"
    )
    frame = loaders.load_calibration(run_dir, "pad_by_crop")
    assert list(frame["crop"]) == ["CS", "TOTAL"]


def test_load_calibration_returns_none_for_a_run_without_the_block(tmp_path):
    run_dir = tmp_path / "output_2"
    (run_dir / "csv").mkdir(parents=True)
    assert loaders.load_calibration(run_dir, "pad_by_crop") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_dashboard_loaders.py -k calibration -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'load_calibration'`

- [ ] **Step 3: Write minimal implementation**

Dans `case_studies/guadeloupe/dashboard/loaders.py`, après `load_facts` :

```python
def load_calibration(run_dir: Path, name: str) -> pd.DataFrame | None:
    """One calibration block ('pad_by_crop', 'pad_by_crop_and_region', 'pad_by_farm',
    'farm_type_confusion', 'field_match'), or None for a run scored before the calibration
    reporting existed."""
    return load_csv(run_dir, f"calibration_{name}.csv")
```

Créer `case_studies/guadeloupe/dashboard/pages/3_Calibration.py` :

```python
"""Calibration page: how close a run's allocation is to the observed 2017 land use.

Read-only, like every other page. Displays what generate_report (or
scripts/evaluate_calibration.py) already wrote; computes nothing. Run the dashboard from
the repo root with:  streamlit run case_studies/guadeloupe/dashboard/app.py
"""

import sys
from pathlib import Path

# Streamlit runs each page as its own top-level script, so (like app.py) the repo root must
# be on sys.path before importing `case_studies...`.
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
import streamlit as st

from case_studies.guadeloupe.dashboard import loaders
from case_studies.guadeloupe.domain.crop_labels import label_for
from case_studies.guadeloupe.domain.farm_typology import TYPE_EXPL_LABELS
from case_studies.guadeloupe.domain.zones import region_label

OUTPUTS_ROOT = _REPO_ROOT / "outputs"
TOTAL_KEY = "TOTAL"

st.set_page_config(page_title="MOSAICA -- Calibration", layout="wide")
st.title("Calibration : observé 2017 vs simulé")
st.caption(
    "Écart mesuré au niveau des 12 groupes RPG observés, d'après Chopin et al. (2015) "
    "section 2.6. Le PAD est le pourcentage d'écart absolu entre la surface observée et la "
    "surface simulée ; il vaut 0 quand la simulation reproduit exactement l'observé."
)

runs = loaders.list_output_runs(OUTPUTS_ROOT)
if not runs:
    st.info("Aucun run trouvé dans `outputs/`.")
    st.stop()

labels = {loaders.run_display_name(run, loaders.load_recap(run)): run for run in runs}
selected = st.selectbox("Run", list(labels))
run_dir = labels[selected]

pad_by_crop = loaders.load_calibration(run_dir, "pad_by_crop")
if pad_by_crop is None:
    st.warning(
        f"Ce run n'a pas encore été scoré. Lancez :\n\n"
        f"```\npython scripts/evaluate_calibration.py {run_dir.as_posix()}\n```"
    )
    st.stop()

recap = loaders.load_recap(run_dir)
calib = recap.get("calibration", {})
thresholds = calib.get("thresholds", {})


def _verdict(passed: bool) -> str:
    return "✅ OK" if passed else "❌ hors seuil"


st.subheader("Verdicts")
left, middle, right = st.columns(3)
left.metric(
    f"PAD territorial (seuil {thresholds.get('regional_pad_max', 15):.0f} %)",
    f"{calib.get('regional_pad_pct', float('nan')):.1f} %",
    _verdict(calib.get("regional_within_threshold", False)),
    delta_color="off",
)
middle.metric(
    f"Types d'exploitation (seuil {thresholds.get('farm_type_match_min', 80):.0f} %)",
    f"{calib.get('farm_type_match_pct', float('nan')):.1f} %",
    _verdict(calib.get("farm_type_within_threshold", False)),
    delta_color="off",
)
right.metric(
    "Parcelles bien simulées",
    f"{calib.get('plot_match_pct', float('nan')):.1f} %",
    f"{calib.get('area_match_pct', float('nan')):.1f} % de la surface",
    delta_color="off",
)

st.subheader("Échelle régionale — surface par culture")
regional = pad_by_crop.copy()
regional["culture"] = [
    key if key == TOTAL_KEY else label_for(str(key)) for key in regional["crop"]
]
st.dataframe(
    regional[
        ["culture", "observed_ha", "simulated_ha", "abs_deviation_ha", "pad_pct"]
    ].style.background_gradient(subset=["pad_pct"], cmap="RdYlGn_r", vmin=0, vmax=100),
    use_container_width=True,
    hide_index=True,
)

st.subheader("Échelle sous-régionale — PAD (%) par région et culture")
subregional = loaders.load_calibration(run_dir, "pad_by_crop_and_region")
if subregional is not None:
    grid = subregional[subregional["crop"] != TOTAL_KEY].pivot(
        index="region", columns="crop", values="pad_pct"
    )
    grid.index = [region_label(key) for key in grid.index]
    grid.columns = [label_for(str(key)) for key in grid.columns]
    st.dataframe(
        grid.style.background_gradient(cmap="RdYlGn_r", vmin=0, vmax=100),
        use_container_width=True,
    )

st.subheader("Échelle exploitation — types observés vs simulés")
confusion = loaders.load_calibration(run_dir, "farm_type_confusion")
if confusion is not None:
    matrix = confusion.set_index("type_observe")
    matrix.index = [TYPE_EXPL_LABELS.get(int(key), key) for key in matrix.index]
    matrix.columns = [TYPE_EXPL_LABELS.get(int(key), key) for key in matrix.columns]
    matrix = matrix.loc[matrix.sum(axis=1) > 0, matrix.sum(axis=0) > 0]
    st.dataframe(matrix.style.background_gradient(cmap="Blues"), use_container_width=True)
    st.caption(
        "Lignes : type observé en 2017. Colonnes : type après simulation. La diagonale est "
        "la part correctement reproduite (Chopin et al. 2015, Table 4)."
    )

st.subheader("Échelle parcelle — concordance par sous-région")
field = loaders.load_calibration(run_dir, "field_match")
if field is not None:
    shown = field.copy()
    shown["sous-région"] = [
        key if key == TOTAL_KEY else region_label(key) for key in shown["region"]
    ]
    st.dataframe(
        shown[
            ["sous-région", "matched_plots", "total_plots", "plot_match_pct",
             "matched_ha", "total_ha", "area_match_pct"]
        ],
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Échelle exploitation — distribution du PAD")
by_farm = loaders.load_calibration(run_dir, "pad_by_farm")
if by_farm is not None:
    threshold = thresholds.get("farm_pad_max", 20)
    within = int((by_farm["pad_pct"] <= threshold).sum())
    st.write(
        f"{within} exploitations sur {len(by_farm)} sous le seuil de {threshold:.0f} %."
    )
    st.bar_chart(
        by_farm["pad_pct"].clip(upper=200).value_counts(bins=20).sort_index().rename("fermes")
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_dashboard_loaders.py -v`
Expected: PASS

- [ ] **Step 5: Verify the page imports cleanly**

Run: `.venv/Scripts/python -c "import ast,pathlib; ast.parse(pathlib.Path('case_studies/guadeloupe/dashboard/pages/3_Calibration.py').read_text(encoding='utf-8')); print('syntax OK')"`
Expected: `syntax OK`

Puis, manuellement : `streamlit run case_studies/guadeloupe/dashboard/app.py`, ouvrir la page « Calibration », sélectionner `output_12`, vérifier que les cinq blocs s'affichent. Sélectionner un run non scoré et vérifier que le message propose la commande au lieu de planter.

- [ ] **Step 6: Commit**

```bash
git add case_studies/guadeloupe/dashboard/pages/3_Calibration.py case_studies/guadeloupe/dashboard/loaders.py tests/test_guadeloupe_dashboard_loaders.py
git commit -m "feat(calibration): page dashboard de lecture des metriques"
```

---

### Task 13: Documentation

**Files:**
- Modify: `VIGILANCE.md` (section « Points ouverts »)
- Modify: `TODO.md` (section « En cours / prêt à coder »)
- Modify: `PRISE_EN_MAIN.md`
- Modify: `CLAUDE.md` (paragraphe décrivant `reporting/`)

- [ ] **Step 1: Add the two VIGILANCE entries**

Dans `VIGILANCE.md`, sous « ## Points ouverts », ajouter en tête :

```markdown
### Critique — Les métriques de calibration évaluent un modèle non calibré
Le module `reporting/calibration.py` (spec `docs/superpowers/specs/2026-07-21-calibration-validation-design.md`)
mesure l'écart entre l'assolement observé 2017 et l'assolement simulé, aux quatre échelles
de Chopin et al. (2015) §2.6. Sur `outputs/output_12`, l'observé compte 10 955 parcelles en
canne, 5 524 en prairie, 1 947 en banane ; le simulé est **intégralement en maraîchage**. Le
PAD ressort donc proche de 100 % sur toutes les cultures majeures. **Ce n'est pas un défaut
du module d'évaluation**, mais son diagnostic. Deux causes probables, toutes deux cohérentes
avec l'article :
1. l'objectif actif est `maximize_gross_margin`, pas l'utilité de Markowitz où Ø freine
   chaque type d'exploitation (`maximize_risk_adjusted_gross_margin` existe, désactivé) ;
2. `Eq_MO_MAX_Expl` (Eq. 5 de l'article) n'est pas portée — voir l'entrée dédiée ci-dessous.
   Le maraîchage demande 990 à 1 560 h/ha contre 15 h/ha pour la canne mécanisée (Table 1
   de l'article) : sans plafond de main-d'œuvre, rien ne limite la bascule.
Ne pas interpréter un PAD élevé comme une régression du reporting. _2026-07-21._

### Mineur — Reconstruction typologique et parcelles `NC`
`compute_type_expl` calcule `denom = surf_cultiv - surf_non`, où `surf_non` agrège `JA` et
`NC` : une parcelle non cultivée **diminue** le dénominateur et remonte toutes les parts
`PART_*`. `calibration.farm_type_confusion` recalcule donc les groupes de base depuis
`data_parc` sur l'univers complet, et non depuis `allocation_input.csv` qui écarte les `NC`.
Côté simulé, une parcelle que le solveur laisse sans culture compte comme `NC`. Conséquence :
`scripts/evaluate_calibration.py` **doit** reconstruire le `Dataset` (7 s), il ne peut pas
travailler sur les seuls CSV d'un run. _2026-07-21._
```

- [ ] **Step 2: Add the TODO follow-up**

Dans `TODO.md`, sous « ## En cours / prêt à coder », ajouter en tête :

```markdown
**Calibration & validation — livré le 2026-07-21.** Spec :
`docs/superpowers/specs/2026-07-21-calibration-validation-design.md`. PAD régional,
sous-régional et par exploitation, matrice de confusion des 8 types, taux de correspondance
parcellaire, d'après Chopin et al. (2015) §2.6. Écrit dans chaque run et rejouable sur les
runs passés avec `scripts/evaluate_calibration.py`. Reporting seul, aucun solve.
→ Suite naturelle, **non planifiée** : corriger ce que le diagnostic révèle. Deux leviers,
dans cet ordre : (1) porter `Eq_MO_MAX_Expl`, le plafond de main-d'œuvre par exploitation
(Eq. 5 de l'article) — c'est le plus probable des deux, le maraîchage étant 60 fois plus
intensif en travail que la canne ; (2) activer `maximize_risk_adjusted_gross_margin`, dont
les coefficients Ø sont déjà ceux de la Table 2 de l'article. Chaque levier demande un solve
réel (~30-55 min) pour être mesuré, puis un `scripts/evaluate_calibration.py` sur le run
produit. À décider avec l'utilisateur : le point 4 de `VIGILANCE.md` note que `MO_Expl_init`
suppose l'allocation fine 2017, qui n'a jamais existé.
```

- [ ] **Step 3: Document the command**

Dans `PRISE_EN_MAIN.md`, ajouter à la liste des commandes :

```markdown
### Noter un run par rapport à la réalité observée

```bash
.venv/Scripts/python scripts/evaluate_calibration.py outputs/output_12   # un run
.venv/Scripts/python scripts/evaluate_calibration.py --all               # tous les runs
```

Compare l'assolement simulé à l'assolement réellement observé en 2017, aux quatre échelles
de l'article de référence (territoire, sous-région, exploitation, parcelle), et écrit les
tableaux dans le dossier du run. Environ 7 secondes par run, aucun solve. Les résultats se
lisent aussi dans la page « Calibration » du dashboard.
```

- [ ] **Step 4: Update CLAUDE.md**

Dans `CLAUDE.md`, après le paragraphe décrivant les indicateurs environnementaux, ajouter :

```markdown
`reporting/calibration.py` note le run par rapport à la réalité observée, d'après Chopin et al.
(2015) §2.6 : PAD (pourcentage d'écart absolu) territorial, sous-régional et par exploitation,
matrice de confusion des 8 types d'exploitation, taux de correspondance parcellaire. Tout se
compare au niveau des **12 groupes RPG observés** — `domain/crop_families.base_group_for()` y
replie les 84 cultures fines — parce que l'observé 2017 n'a pas de résolution plus fine.
Rejouable sur un run passé avec `scripts/evaluate_calibration.py`. Attention : ces métriques
mesurent aujourd'hui un modèle **non calibré** (objectif marge brute pure, `Eq_MO_MAX_Expl`
non portée) ; un PAD proche de 100 % est le diagnostic attendu, cf. `VIGILANCE.md`.
```

- [ ] **Step 5: Run the full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: PASS. La suite complète prend ~29 min ; c'est le contrôle final du chantier, à lancer une seule fois ici.

- [ ] **Step 6: Verify the golden is still clean**

Run: `.venv/Scripts/python scripts/golden_snapshot.py --check`
Expected: `OK (N checksums unchanged)`

- [ ] **Step 7: Commit**

```bash
git add VIGILANCE.md TODO.md PRISE_EN_MAIN.md CLAUDE.md
git commit -m "docs(calibration): consigner le chantier, le diagnostic et la commande"
```

---

## Vérification finale

Après la tâche 13, l'ensemble doit satisfaire :

- `.venv/Scripts/python -m pytest -q` → vert
- `.venv/Scripts/python scripts/golden_snapshot.py --check` → `OK`
- `.venv/Scripts/python scripts/evaluate_calibration.py --all` → un bloc de verdicts par run, cinq CSV écrits par run
- `streamlit run case_studies/guadeloupe/dashboard/app.py` → page « Calibration » fonctionnelle sur un run scoré, message d'invite sur un run non scoré

Aucun solve réel n'a été lancé. La confirmation de bout en bout (`main.py` → `generate_report` → `outputs/output_N/` avec le bloc calibration) reste à faire au prochain run de fin de journée, comme l'indique déjà `TODO.md` pour le refactor précédent.
