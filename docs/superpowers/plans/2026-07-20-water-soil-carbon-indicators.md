# Indicateurs eau + carbone organique du sol — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter deux indicateurs de reporting — besoin en eau des cultures et bilan de carbone organique du sol — calculés après le solve, alimentant la table de faits et le score composite du dashboard.

**Architecture:** Deux modules purs (`water.py`, `soil_carbon.py`) produisant des taux par hectare, sur le modèle de `environment.py`. Le pipeline les calcule et les enregistre dans `Dataset.parameters` ; la couche `reporting/indicators.py` les applique à l'allocation. Le carbone est partiellement **parcellaire** (il dépend du type de sol), contrairement à tous les indicateurs existants qui sont purement par culture — c'est la principale nouveauté structurelle.

**Tech Stack:** Python 3, pandas, pytest. Venv à `.venv/`. Pas de Pyomo ni de solveur dans ce lot.

**Spec :** `docs/superpowers/specs/2026-07-20-water-soil-carbon-indicators-design.md`

## Global Constraints

- **Reporting seul.** Aucune contrainte, aucun objectif, aucune modification du modèle Pyomo. L'allocation ne change pas.
- **Tests sans `data/`.** Convention du repo : configs minuscules montées à la main (cf. `tests/test_guadeloupe_constraints.py`). Aucun test de ce lot ne lit `data/` ni ne résout de MILP.
- **Ne jamais lancer `main.py` ni `scripts/run_scenarios.py`.** Solves réels, ~30–55 min, réservés à une demande explicite de l'utilisateur en fin de journée.
- **Mapping des types de sol par nom, jamais par position.** `1→VERTISOL, 2→FERRALSOL, 3→ANDOSOL, 4→NITISOL, 5→AUTRES`. L'ordre de `SOL.set` et des colonnes de `Data_Sol.txt` est différent (`NITISOL, ANDOSOL, FERRALSOL, AUTRES, VERTISOL`) : indexer par position produit des coefficients faux mais plausibles.
- **Conversion eau :** 1 mm sur 1 ha = 10 m³. Constante nommée `M3_PER_MM_PER_HA = 10.0`.
- **Parité GAMS assumée** sur quatre points, tous documentés dans `VIGILANCE.md` : flux carbone annuel (pas de trajectoire), pluie jamais déduite, bug `max(0, ·)` porté tel quel, amendements non annualisés.
- Commandes pytest : `.venv/Scripts/python -m pytest <chemin> -v`.

---

### Task 1: Module `water.py` — taux de besoin en eau par culture

**Files:**
- Create: `case_studies/guadeloupe/water.py`
- Test: `tests/test_guadeloupe_water.py`

**Interfaces:**
- Consumes: rien (premier task).
- Produces:
  - `M3_PER_MM_PER_HA: float` (= 10.0)
  - `MONTHLY_WATER_ROWS: list[str]` — `["BESOIN_EAU_01", ..., "BESOIN_EAU_12"]`
  - `compute_monthly_water_need_per_ha_cult(data_cult: pd.DataFrame) -> pd.DataFrame` — index = les 12 libellés de `MONTHLY_WATER_ROWS`, colonnes = cultures, valeurs en mm/mois.
  - `compute_water_need_per_ha_cult(data_cult: pd.DataFrame) -> pd.Series` — index = cultures, total annuel en mm/an.

- [ ] **Step 1: Write the failing test**

Créer `tests/test_guadeloupe_water.py` :

```python
import pandas as pd

from case_studies.guadeloupe import water


def _data_cult() -> pd.DataFrame:
    """Data_Cult miniature: lignes = attributs, colonnes = cultures (comme la vraie table)."""
    rows = {f"BESOIN_EAU_{m:02d}": [10.0 * m, 0.0] for m in range(1, 13)}
    rows["KCROP"] = [0.9, 0.5]  # ligne non liée à l'eau, doit être ignorée
    return pd.DataFrame(rows, index=["CROP_A", "CROP_B"]).T


def test_monthly_water_need_returns_twelve_rows_in_calendar_order():
    monthly = water.compute_monthly_water_need_per_ha_cult(_data_cult())
    assert list(monthly.index) == water.MONTHLY_WATER_ROWS
    assert len(monthly.index) == 12
    assert monthly.loc["BESOIN_EAU_01", "CROP_A"] == 10.0
    assert monthly.loc["BESOIN_EAU_12", "CROP_A"] == 120.0


def test_monthly_water_need_ignores_unrelated_rows():
    monthly = water.compute_monthly_water_need_per_ha_cult(_data_cult())
    assert "KCROP" not in monthly.index


def test_annual_water_need_sums_the_twelve_months():
    annual = water.compute_water_need_per_ha_cult(_data_cult())
    # 10 + 20 + ... + 120 = 780
    assert annual["CROP_A"] == 780.0
    assert annual["CROP_B"] == 0.0


def test_m3_conversion_constant_is_ten():
    """1 mm sur 1 ha = 10 m3. Le GAMS omet ce facteur (OPTIMISATION.txt:2559)."""
    assert water.M3_PER_MM_PER_HA == 10.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_water.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'case_studies.guadeloupe.water'`

- [ ] **Step 3: Write minimal implementation**

Créer `case_studies/guadeloupe/water.py` :

```python
"""Per-ha water need by crop, from the monthly BESOIN_EAU rows of Data_Cult.

Faithful to OPTIMISATION.txt:2489-2560, with two documented departures (see VIGILANCE.md):
rainfall is never deducted (the monthly PLUVIO_*_PARC columns do not exist in the data), so
this is a *gross crop water need*, not a net irrigation need; and the mm -> m3 conversion
factor the GAMS omits is applied explicitly here.
"""

import pandas as pd

# 1 mm of water over 1 ha = 10 m3. GAMS omits this factor and divides by 1e6
# (OPTIMISATION.txt:2559); its author had flagged "pourquoi x 10?" in DECLAR_OPT.txt:2114.
M3_PER_MM_PER_HA = 10.0

MONTHLY_WATER_ROWS = [f"BESOIN_EAU_{month:02d}" for month in range(1, 13)]


def compute_monthly_water_need_per_ha_cult(data_cult: pd.DataFrame) -> pd.DataFrame:
    """Monthly crop water need (mm/month): rows = the 12 months in calendar order,
    columns = crops."""
    return data_cult.loc[MONTHLY_WATER_ROWS]


def compute_water_need_per_ha_cult(data_cult: pd.DataFrame) -> pd.Series:
    """Annual crop water need per ha (mm/year): sum of the 12 monthly rows."""
    return compute_monthly_water_need_per_ha_cult(data_cult).sum(axis=0)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_water.py -v`
Expected: PASS — 4 passed

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/water.py tests/test_guadeloupe_water.py
git commit -m "feat(indicateurs): taux de besoin en eau par culture"
```

---

### Task 2: Module `soil_carbon.py` — bilan de carbone organique

**Files:**
- Create: `case_studies/guadeloupe/soil_carbon.py`
- Test: `tests/test_guadeloupe_soil_carbon.py`

**Interfaces:**
- Consumes: rien de Task 1.
- Produces:
  - `TYPE_SOL_TO_SOIL_NAME: dict[int, str]` — `{1: "VERTISOL", 2: "FERRALSOL", 3: "ANDOSOL", 4: "NITISOL", 5: "AUTRES"}`
  - `compute_residue_carbon_per_ha_cult(data_cult: pd.DataFrame) -> pd.Series`
  - `compute_amendment_carbon_per_ha_cult(data_otk: pd.DataFrame, matrice_otk_cult: pd.DataFrame) -> pd.Series`
  - `compute_carbon_input_per_ha_cult(data_cult, data_otk, matrice_otk_cult) -> pd.Series` — somme des deux précédentes
  - `compute_initial_soil_carbon_per_ha_plot(data_parc: pd.DataFrame, data_sol: pd.DataFrame) -> pd.Series` — index = parcelles
  - `compute_mineralization_per_ha_plot(allocation: pd.Series, data_parc, data_sol, data_cult, initial_carbon: pd.Series) -> pd.Series` — index = parcelles allouées
  - `compute_carbon_balance_per_ha_plot(allocation, data_parc, data_sol, data_cult, data_otk, matrice_otk_cult) -> pd.Series`

Toutes les séries de carbone sont en **t C/ha/an** (les stocks en t C/ha).

- [ ] **Step 1: Write the failing test**

Créer `tests/test_guadeloupe_soil_carbon.py` :

```python
import pandas as pd
import pytest

from case_studies.guadeloupe import soil_carbon


def _data_cult() -> pd.DataFrame:
    """CROP_HIGH: gros producteur de résidus. CROP_LOW: quasi rien."""
    return pd.DataFrame(
        {
            "BIOM_AER": [10.0, 1.0],
            "RAC": [0.5, 0.0],
            "CARB": [0.4, 0.4],
            "HRES": [0.5, 0.5],
            "KCROP": [1.0, 1.0],
        },
        index=["CROP_HIGH", "CROP_LOW"],
    ).T


def _data_sol() -> pd.DataFrame:
    """Colonnes dans l'ordre de la vraie table, DIFFERENT de l'ordre TYPE_SOL 1..5."""
    return pd.DataFrame(
        {
            "NITISOL": [0.10, 1.0, 0.25, 3.0],
            "ANDOSOL": [0.20, 1.0, 0.25, 17.5],
            "FERRALSOL": [0.30, 1.0, 0.25, 10.0],
            "AUTRES": [0.40, 1.0, 0.25, 0.0],
            "VERTISOL": [0.50, 1.0, 0.25, 0.0],
        },
        index=["KAER", "DENS", "PROF", "KOC"],
    )


def _data_parc() -> pd.DataFrame:
    return pd.DataFrame(
        {"PART_C_INIT": [4.0, 4.0], "TYPE_SOL": [1, 4], "SURF_HA": [2.0, 3.0]},
        index=["P1", "P2"],
    )


def _data_otk() -> pd.DataFrame:
    return pd.DataFrame(
        {"DOSE": [2.0, 1.0], "HUM": [0.5, 0.0], "CARB": [0.3, 0.0], "FHUM": [1.0, 0.0]},
        index=["COMPOST", "UREE"],
    )


def _matrice() -> pd.DataFrame:
    """Lignes = opérations ITK, colonnes = cultures."""
    return pd.DataFrame(
        {"CROP_HIGH": [1.0, 1.0], "CROP_LOW": [0.0, 1.0]}, index=["COMPOST", "UREE"]
    )


def test_type_sol_mapping_matches_gams_order_not_table_order():
    """OPTIMISATION.txt:2880-2896. L'ordre des colonnes de Data_Sol est DIFFERENT --
    indexer par position donnerait des coefficients faux mais plausibles."""
    assert soil_carbon.TYPE_SOL_TO_SOIL_NAME == {
        1: "VERTISOL", 2: "FERRALSOL", 3: "ANDOSOL", 4: "NITISOL", 5: "AUTRES",
    }
    # Garde-fou explicite: la position 1 de Data_Sol est NITISOL, pas VERTISOL.
    assert list(_data_sol().columns)[0] == "NITISOL"
    assert soil_carbon.TYPE_SOL_TO_SOIL_NAME[1] == "VERTISOL"


def test_residue_carbon_uses_aerial_plus_root_biomass():
    # BIOM_AER * (1 + RAC) * CARB * HRES = 10 * 1.5 * 0.4 * 0.5 = 3.0
    residue = soil_carbon.compute_residue_carbon_per_ha_cult(_data_cult())
    assert residue["CROP_HIGH"] == pytest.approx(3.0)
    # 1 * 1.0 * 0.4 * 0.5 = 0.2
    assert residue["CROP_LOW"] == pytest.approx(0.2)


def test_amendment_carbon_sums_over_itk_operations():
    # COMPOST: DOSE 2 * HUM 0.5 * CARB 0.3 * FHUM 1 * matrice 1 = 0.3 ; UREE contribue 0.
    amendment = soil_carbon.compute_amendment_carbon_per_ha_cult(_data_otk(), _matrice())
    assert amendment["CROP_HIGH"] == pytest.approx(0.3)
    assert amendment["CROP_LOW"] == pytest.approx(0.0)


def test_initial_soil_carbon_maps_soil_type_by_name():
    # P1: TYPE_SOL 1 -> VERTISOL. 4/100 * DENS 1.0 * PROF 0.25 * 10000 = 100.
    # P2: TYPE_SOL 4 -> NITISOL,  meme DENS/PROF ici -> 100 aussi.
    initial = soil_carbon.compute_initial_soil_carbon_per_ha_plot(_data_parc(), _data_sol())
    assert initial["P1"] == pytest.approx(100.0)
    assert initial["P2"] == pytest.approx(100.0)


def test_mineralization_uses_the_plot_soil_kaer_not_a_fixed_one():
    """Le test qui attrape un mapping par position: P1 (VERTISOL, KAER .50) et
    P2 (NITISOL, KAER .10) doivent differer d'un facteur 5."""
    allocation = pd.Series(["CROP_HIGH", "CROP_HIGH"], index=["P1", "P2"])
    initial = pd.Series([100.0, 100.0], index=["P1", "P2"])
    mineralization = soil_carbon.compute_mineralization_per_ha_plot(
        allocation, _data_parc(), _data_sol(), _data_cult(), initial
    )
    # C_ORG 100 * KAER * KCROP 1.0
    assert mineralization["P1"] == pytest.approx(50.0)
    assert mineralization["P2"] == pytest.approx(10.0)


def test_carbon_balance_drops_when_switching_to_a_low_residue_crop():
    """Entrees - sorties. Meme parcelle, meme sol: seule la culture change."""
    data_parc, data_sol, data_cult = _data_parc(), _data_sol(), _data_cult()
    data_otk, matrice = _data_otk(), _matrice()

    high = soil_carbon.compute_carbon_balance_per_ha_plot(
        pd.Series(["CROP_HIGH"], index=["P2"]),
        data_parc, data_sol, data_cult, data_otk, matrice,
    )
    low = soil_carbon.compute_carbon_balance_per_ha_plot(
        pd.Series(["CROP_LOW"], index=["P2"]),
        data_parc, data_sol, data_cult, data_otk, matrice,
    )
    # HIGH: entrees 3.0 + 0.3 = 3.3, sorties 100 * 0.10 * 1.0 = 10 -> -6.7
    assert high["P2"] == pytest.approx(-6.7)
    # LOW: entrees 0.2 + 0.0 = 0.2, sorties 10 -> -9.8
    assert low["P2"] == pytest.approx(-9.8)
    assert low["P2"] < high["P2"]


def test_carbon_balance_on_empty_allocation_is_empty():
    balance = soil_carbon.compute_carbon_balance_per_ha_plot(
        pd.Series(dtype=object), _data_parc(), _data_sol(), _data_cult(),
        _data_otk(), _matrice(),
    )
    assert balance.empty
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_soil_carbon.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'case_studies.guadeloupe.soil_carbon'`

- [ ] **Step 3: Write minimal implementation**

Créer `case_studies/guadeloupe/soil_carbon.py` :

```python
"""Annual soil organic carbon balance: crop residues + organic amendments - mineralization.

Faithful to OPTIMISATION.txt:2880-2947, with two documented departures (see VIGILANCE.md):
the GAMS iterates the stock over years (C_ORG = C_ORG + flux, NB_BOUCLE loop) while this
model is single-year, so only the *annual flux* is ported; and the amendment term is not
annualized by Duree_Cycle/Duree_Plant, unlike azote/GES/costs -- that is what the GAMS does
(OPTIMISATION.txt:2919), and it looks like a source-side oversight.

All carbon quantities are in t C/ha (stocks) or t C/ha/year (flows).
"""

import pandas as pd

# Data_Parc's numeric TYPE_SOL -> Data_Sol column name, per OPTIMISATION.txt:2880-2896.
# CAREFUL: Data_Sol's own column order (and SOL.set) is NITISOL, ANDOSOL, FERRALSOL,
# AUTRES, VERTISOL -- a DIFFERENT order. Indexing Data_Sol positionally yields wrong but
# plausible coefficients, so always map by name through this dict.
TYPE_SOL_TO_SOIL_NAME = {
    1: "VERTISOL",
    2: "FERRALSOL",
    3: "ANDOSOL",
    4: "NITISOL",
    5: "AUTRES",
}

# PART_C_INIT is a percentage; DENS is t/m3, PROF is m, and 10000 m2 = 1 ha.
_PERCENT = 100.0
_M2_PER_HA = 10000.0


def _soil_attribute_by_plot(
    data_parc: pd.DataFrame, data_sol: pd.DataFrame, attribute: str
) -> pd.Series:
    """One Data_Sol row (KAER, DENS, PROF...) resolved per plot through TYPE_SOL."""
    soil_names = data_parc["TYPE_SOL"].map(TYPE_SOL_TO_SOIL_NAME)
    return soil_names.map(data_sol.loc[attribute])


def compute_residue_carbon_per_ha_cult(data_cult: pd.DataFrame) -> pd.Series:
    """Carbon returned by crop residues (t C/ha/year): aerial biomass plus root biomass,
    times carbon content, times the humification coefficient."""
    aerial = data_cult.loc["BIOM_AER"]
    total_residue = aerial * (1.0 + data_cult.loc["RAC"])
    return total_residue * data_cult.loc["CARB"] * data_cult.loc["HRES"]


def compute_amendment_carbon_per_ha_cult(
    data_otk: pd.DataFrame, matrice_otk_cult: pd.DataFrame
) -> pd.Series:
    """Carbon brought by organic amendments (t C/ha/year): sum over the crop's ITK
    operations of DOSE * HUM * CARB * FHUM. Deliberately NOT annualized -- see module
    docstring."""
    per_operation = (
        data_otk["DOSE"] * data_otk["HUM"] * data_otk["CARB"] * data_otk["FHUM"]
    )
    return matrice_otk_cult.multiply(per_operation, axis=0).sum(axis=0)


def compute_carbon_input_per_ha_cult(
    data_cult: pd.DataFrame, data_otk: pd.DataFrame, matrice_otk_cult: pd.DataFrame
) -> pd.Series:
    """Total carbon input per ha per year: residues + amendments."""
    residues = compute_residue_carbon_per_ha_cult(data_cult)
    amendments = compute_amendment_carbon_per_ha_cult(data_otk, matrice_otk_cult)
    return residues.add(amendments.reindex(residues.index).fillna(0.0), fill_value=0.0)


def compute_initial_soil_carbon_per_ha_plot(
    data_parc: pd.DataFrame, data_sol: pd.DataFrame
) -> pd.Series:
    """Initial soil organic carbon stock (t C/ha) per plot, from its measured carbon
    fraction and its soil type's bulk density and depth."""
    density = _soil_attribute_by_plot(data_parc, data_sol, "DENS")
    depth = _soil_attribute_by_plot(data_parc, data_sol, "PROF")
    return data_parc["PART_C_INIT"] / _PERCENT * density * depth * _M2_PER_HA


def compute_mineralization_per_ha_plot(
    allocation: pd.Series,
    data_parc: pd.DataFrame,
    data_sol: pd.DataFrame,
    data_cult: pd.DataFrame,
    initial_carbon: pd.Series,
) -> pd.Series:
    """Carbon lost to mineralization (t C/ha/year) on each allocated plot: the plot's
    carbon stock times its soil's aerobic mineralization rate times the crop's KCROP."""
    if allocation.empty:
        return pd.Series(dtype=float)
    kaer = _soil_attribute_by_plot(data_parc, data_sol, "KAER").reindex(allocation.index)
    kcrop = pd.Series(
        data_cult.loc["KCROP"].reindex(allocation.to_numpy()).to_numpy(),
        index=allocation.index,
    )
    return initial_carbon.reindex(allocation.index) * kaer * kcrop


def compute_carbon_balance_per_ha_plot(
    allocation: pd.Series,
    data_parc: pd.DataFrame,
    data_sol: pd.DataFrame,
    data_cult: pd.DataFrame,
    data_otk: pd.DataFrame,
    matrice_otk_cult: pd.DataFrame,
) -> pd.Series:
    """Net annual carbon balance (t C/ha/year) per allocated plot. Negative means the
    system depletes soil carbon."""
    if allocation.empty:
        return pd.Series(dtype=float)
    inputs_by_crop = compute_carbon_input_per_ha_cult(data_cult, data_otk, matrice_otk_cult)
    inputs = pd.Series(
        inputs_by_crop.reindex(allocation.to_numpy()).to_numpy(), index=allocation.index
    )
    initial_carbon = compute_initial_soil_carbon_per_ha_plot(data_parc, data_sol)
    outputs = compute_mineralization_per_ha_plot(
        allocation, data_parc, data_sol, data_cult, initial_carbon
    )
    return inputs - outputs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_soil_carbon.py -v`
Expected: PASS — 7 passed

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/soil_carbon.py tests/test_guadeloupe_soil_carbon.py
git commit -m "feat(indicateurs): bilan de carbone organique du sol"
```

---

### Task 3: Câblage dans le pipeline de données

**Files:**
- Modify: `case_studies/guadeloupe/data_pipeline.py` (lecture de `Data_Sol.txt`, calcul des taux, enregistrement dans `parameters`)
- Test: `tests/test_guadeloupe_pipeline_rates.py` (créer)

**Interfaces:**
- Consumes: Task 1 (`water.compute_water_need_per_ha_cult`, `water.compute_monthly_water_need_per_ha_cult`), Task 2 (`soil_carbon.compute_carbon_input_per_ha_cult`).
- Produces, dans `Dataset.parameters` :
  - `"data_sol"` — `pd.DataFrame`, lignes `KAER`/`DENS`/`PROF`/`KOC`, colonnes = noms de sols
  - `"water_need_per_ha_cult"` — `pd.Series` indexée par culture, mm/an
  - `"monthly_water_need_per_ha_cult"` — `pd.DataFrame` 12 × cultures, mm/mois
  - `"carbon_input_per_ha_cult"` — `pd.Series` indexée par culture, t C/ha/an

Note : `read_wide_table` (`core/data/readers.py`) lit déjà n'importe quelle table large ; aucun nouveau lecteur n'est nécessaire, seulement un appel supplémentaire.

- [ ] **Step 1: Write the failing test**

Créer `tests/test_guadeloupe_pipeline_rates.py` :

```python
"""Vérifie que les nouveaux paramètres sont enregistrés, sans lire data/."""

import pandas as pd

from case_studies.guadeloupe import soil_carbon, water


def test_water_and_carbon_rates_compose_into_crop_indexed_series():
    """Contrat attendu par data_pipeline: des Series indexées par culture, prêtes à être
    reindexées sur une allocation."""
    data_cult = pd.DataFrame(
        {
            **{f"BESOIN_EAU_{m:02d}": [5.0, 1.0] for m in range(1, 13)},
            "BIOM_AER": [10.0, 1.0],
            "RAC": [0.5, 0.0],
            "CARB": [0.4, 0.4],
            "HRES": [0.5, 0.5],
            "KCROP": [1.0, 1.0],
        },
        index=["CROP_A", "CROP_B"],
    ).T
    data_otk = pd.DataFrame(
        {"DOSE": [2.0], "HUM": [0.5], "CARB": [0.3], "FHUM": [1.0]}, index=["COMPOST"]
    )
    matrice = pd.DataFrame({"CROP_A": [1.0], "CROP_B": [0.0]}, index=["COMPOST"])

    annual_water = water.compute_water_need_per_ha_cult(data_cult)
    carbon_input = soil_carbon.compute_carbon_input_per_ha_cult(data_cult, data_otk, matrice)

    assert list(annual_water.index) == ["CROP_A", "CROP_B"]
    assert annual_water["CROP_A"] == 60.0  # 12 mois x 5 mm
    assert list(carbon_input.index) == ["CROP_A", "CROP_B"]
    assert carbon_input["CROP_A"] == 3.3  # residus 3.0 + amendement 0.3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_pipeline_rates.py -v`
Expected: PASS immédiatement (le test ne fait que verrouiller le contrat des Tasks 1–2). Si FAIL, une signature de Task 1 ou 2 a dérivé — corriger avant de continuer.

- [ ] **Step 3: Wire the pipeline**

Dans `case_studies/guadeloupe/data_pipeline.py`, ajouter l'import en tête, à côté des imports existants du même paquet :

```python
from case_studies.guadeloupe import soil_carbon, water
```

Juste après la ligne `data_otk = read_wide_table(TABLES_DIR / "Data_OTK.txt")` (~ligne 132), ajouter :

```python
    data_sol = read_wide_table(TABLES_DIR / "Data_Sol.txt")
```

Puis, à côté des calculs `azote_per_ha_cult` / `ges_per_ha_cult` / `ift_per_ha_cult` existants, ajouter :

```python
    water_need_per_ha_cult = water.compute_water_need_per_ha_cult(data_cult)
    monthly_water_need_per_ha_cult = water.compute_monthly_water_need_per_ha_cult(data_cult)
    carbon_input_per_ha_cult = soil_carbon.compute_carbon_input_per_ha_cult(
        data_cult, data_otk, matrice_otk_cult
    )
```

Enfin, dans le dict `parameters`, après `"ift_per_ha_cult": ift_per_ha_cult,` :

```python
        "data_sol": data_sol,
        "water_need_per_ha_cult": water_need_per_ha_cult,
        "monthly_water_need_per_ha_cult": monthly_water_need_per_ha_cult,
        "carbon_input_per_ha_cult": carbon_input_per_ha_cult,
```

- [ ] **Step 4: Verify the pipeline still imports and the suite is green**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_pipeline_rates.py tests/test_guadeloupe_water.py tests/test_guadeloupe_soil_carbon.py -v`
Expected: PASS — 12 passed

Puis vérifier que le module s'importe sans erreur de syntaxe :
Run: `.venv/Scripts/python -c "import case_studies.guadeloupe.data_pipeline"`
Expected: aucune sortie, code de retour 0

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/data_pipeline.py tests/test_guadeloupe_pipeline_rates.py
git commit -m "feat(indicateurs): lecture de Data_Sol et enregistrement des taux eau/carbone"
```

---

### Task 4: Agrégation par allocation dans `reporting/indicators.py`

**Files:**
- Modify: `case_studies/guadeloupe/reporting/indicators.py`
- Test: `tests/test_guadeloupe_reporting_water_carbon.py` (créer)

**Interfaces:**
- Consumes: Task 3 (`parameters["water_need_per_ha_cult"]`, `["monthly_water_need_per_ha_cult"]`, `["data_sol"]`, `["carbon_input_per_ha_cult"]`).
- Produces :
  - `compute_water_need_m3_by_plot(dataset, allocation) -> pd.Series`
  - `compute_monthly_water_need_m3(dataset, allocation) -> pd.Series` — index = les 12 mois, valeurs en m³
  - `compute_soil_carbon_balance_by_plot(dataset, allocation) -> pd.Series` — t C (bilan × surface)
  - `compute_soil_carbon_mineralization_by_plot(dataset, allocation) -> pd.Series` — t C
  - `compute_environmental_totals` gagne 4 clés : `total_water_need_m3`, `water_need_peak_month_m3`, `soil_carbon_balance`, `soil_carbon_mineralization`

Règle métier : une parcelle dont `IRRIG_PARC == 0` contribue **0** au besoin en eau (pas d'irrigation possible, donc pas de prélèvement). Le carbone n'a pas de filtre.

- [ ] **Step 1: Write the failing test**

Créer `tests/test_guadeloupe_reporting_water_carbon.py` :

```python
import pandas as pd
import pytest

from core.data.dataset import Dataset
from case_studies.guadeloupe.reporting import indicators


def _dataset() -> Dataset:
    data_parc = pd.DataFrame(
        {
            "PART_C_INIT": [4.0, 4.0],
            "TYPE_SOL": [1, 4],
            "SURF_HA": [2.0, 3.0],
            "IRRIG_PARC": [1, 0],  # P2 non irrigable -> 0 en eau
        },
        index=["P1", "P2"],
    )
    data_sol = pd.DataFrame(
        {
            "NITISOL": [0.10, 1.0, 0.25, 3.0],
            "ANDOSOL": [0.20, 1.0, 0.25, 17.5],
            "FERRALSOL": [0.30, 1.0, 0.25, 10.0],
            "AUTRES": [0.40, 1.0, 0.25, 0.0],
            "VERTISOL": [0.50, 1.0, 0.25, 0.0],
        },
        index=["KAER", "DENS", "PROF", "KOC"],
    )
    data_cult = pd.DataFrame(
        {
            **{f"BESOIN_EAU_{m:02d}": [5.0, 5.0] for m in range(1, 13)},
            "BIOM_AER": [10.0, 10.0],
            "RAC": [0.5, 0.5],
            "CARB": [0.4, 0.4],
            "HRES": [0.5, 0.5],
            "KCROP": [1.0, 1.0],
        },
        index=["CROP_A", "CROP_B"],
    ).T
    # Un mois de pointe marqué: juillet à 50 mm pour CROP_A.
    data_cult.loc["BESOIN_EAU_07", "CROP_A"] = 50.0

    monthly = data_cult.loc[[f"BESOIN_EAU_{m:02d}" for m in range(1, 13)]]
    parameters = {
        "data_parc": data_parc,
        "data_sol": data_sol,
        "data_cult": data_cult,
        "data_otk": pd.DataFrame(
            {"DOSE": [0.0], "HUM": [0.0], "CARB": [0.0], "FHUM": [0.0]}, index=["NONE"]
        ),
        "matrice_otk_cult": pd.DataFrame(
            {"CROP_A": [0.0], "CROP_B": [0.0]}, index=["NONE"]
        ),
        "water_need_per_ha_cult": monthly.sum(axis=0),
        "monthly_water_need_per_ha_cult": monthly,
        "carbon_input_per_ha_cult": pd.Series({"CROP_A": 3.0, "CROP_B": 3.0}),
    }
    return Dataset(sets={}, parameters=parameters, scalars={})


def _allocation() -> pd.Series:
    return pd.Series(["CROP_A", "CROP_A"], index=["P1", "P2"])


def test_non_irrigable_plot_contributes_no_water():
    by_plot = indicators.compute_water_need_m3_by_plot(_dataset(), _allocation())
    # P1: (11 mois x 5 + 50) x 2 ha x 10 m3 = 105 x 20 = 2100
    assert by_plot["P1"] == pytest.approx(2100.0)
    assert by_plot["P2"] == pytest.approx(0.0)


def test_peak_month_is_higher_than_the_average_month():
    totals = indicators.compute_environmental_totals(_dataset(), _allocation())
    assert totals["total_water_need_m3"] == pytest.approx(2100.0)
    # Juillet: 50 mm x 2 ha x 10 = 1000
    assert totals["water_need_peak_month_m3"] == pytest.approx(1000.0)
    assert totals["water_need_peak_month_m3"] > totals["total_water_need_m3"] / 12


def test_carbon_balance_and_mineralization_scale_with_surface():
    totals = indicators.compute_environmental_totals(_dataset(), _allocation())
    # Mineralisation/ha: P1 (VERTISOL, KAER .50) 100 x .50 = 50 ; P2 (NITISOL) 100 x .10 = 10.
    # Pondere par surface: 50 x 2 + 10 x 3 = 130.
    assert totals["soil_carbon_mineralization"] == pytest.approx(130.0)
    # Bilan/ha: P1 3 - 50 = -47 ; P2 3 - 10 = -7. Pondere: -47 x 2 + -7 x 3 = -115.
    assert totals["soil_carbon_balance"] == pytest.approx(-115.0)


def test_existing_environmental_keys_are_preserved():
    """Le lot ne doit rien retirer des indicateurs existants."""
    totals = indicators.compute_environmental_totals(_dataset(), _allocation())
    for key in ("total_water_need_m3", "water_need_peak_month_m3",
                "soil_carbon_balance", "soil_carbon_mineralization"):
        assert key in totals
```

Note : ce test fournit un `dataset` réduit qui ne contient pas les paramètres azote/GES/IFT. Si `compute_environmental_totals` échoue faute de ceux-ci, ajouter au dict `parameters` du test :

```python
        "azote_per_ha_cult": pd.Series({"CROP_A": 0.0, "CROP_B": 0.0}),
        "ges_per_ha_cult": pd.Series({"CROP_A": 0.0, "CROP_B": 0.0}),
        "ift_per_ha_cult": pd.Series({"CROP_A": 0.0, "CROP_B": 0.0}),
        "cld_uptake_cult": pd.Series({"CROP_A": 4.0, "CROP_B": 4.0}),
```
et les colonnes `RISQUE_CLD` (valeur `5`) à `data_parc`.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_water_carbon.py -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'compute_water_need_m3_by_plot'`

- [ ] **Step 3: Write the implementation**

Dans `case_studies/guadeloupe/reporting/indicators.py`, ajouter l'import en tête :

```python
from case_studies.guadeloupe import soil_carbon, water
```

Ajouter ces fonctions juste avant `compute_environmental_totals` :

```python
def _irrigable_surface(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Plot surface (ha), zeroed on plots that cannot be irrigated (IRRIG_PARC = 0) and
    therefore draw nothing from the resource. Faithful to OPTIMISATION.txt:2540-2542."""
    data_parc = dataset.parameters["data_parc"]
    surface = data_parc["SURF_HA"].reindex(allocation.index)
    irrigable = data_parc["IRRIG_PARC"].reindex(allocation.index) == 1
    return surface.where(irrigable, 0.0)


def compute_water_need_m3_by_plot(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Annual gross crop water need (m3) per allocated plot. Gross, not net of rainfall --
    the monthly PLUVIO_*_PARC columns do not exist in the data (see VIGILANCE.md)."""
    if allocation.empty:
        return pd.Series(dtype=float)
    rate = dataset.parameters["water_need_per_ha_cult"]
    per_ha = pd.Series(
        rate.reindex(allocation.to_numpy()).to_numpy(), index=allocation.index
    )
    return per_ha * _irrigable_surface(dataset, allocation) * water.M3_PER_MM_PER_HA


def compute_monthly_water_need_m3(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Territory-wide water need (m3) for each of the 12 months, in calendar order."""
    monthly_rate = dataset.parameters["monthly_water_need_per_ha_cult"]
    surface = _irrigable_surface(dataset, allocation)
    if allocation.empty:
        return pd.Series(0.0, index=monthly_rate.index)
    per_month = {}
    for month in monthly_rate.index:
        per_ha = pd.Series(
            monthly_rate.loc[month].reindex(allocation.to_numpy()).to_numpy(),
            index=allocation.index,
        )
        per_month[month] = float((per_ha * surface * water.M3_PER_MM_PER_HA).sum())
    return pd.Series(per_month)


def compute_soil_carbon_mineralization_by_plot(
    dataset: Dataset, allocation: pd.Series
) -> pd.Series:
    """Carbon mineralized (t C) per allocated plot: per-ha rate times plot surface."""
    if allocation.empty:
        return pd.Series(dtype=float)
    data_parc = dataset.parameters["data_parc"]
    initial = soil_carbon.compute_initial_soil_carbon_per_ha_plot(
        data_parc, dataset.parameters["data_sol"]
    )
    per_ha = soil_carbon.compute_mineralization_per_ha_plot(
        allocation, data_parc, dataset.parameters["data_sol"],
        dataset.parameters["data_cult"], initial,
    )
    return per_ha * data_parc["SURF_HA"].reindex(allocation.index)


def compute_soil_carbon_balance_by_plot(dataset: Dataset, allocation: pd.Series) -> pd.Series:
    """Net annual carbon balance (t C) per allocated plot. Negative = soil depletion."""
    if allocation.empty:
        return pd.Series(dtype=float)
    data_parc = dataset.parameters["data_parc"]
    inputs_by_crop = dataset.parameters["carbon_input_per_ha_cult"]
    inputs_per_ha = pd.Series(
        inputs_by_crop.reindex(allocation.to_numpy()).to_numpy(), index=allocation.index
    )
    inputs = inputs_per_ha * data_parc["SURF_HA"].reindex(allocation.index)
    return inputs - compute_soil_carbon_mineralization_by_plot(dataset, allocation)
```

Puis, dans `compute_environmental_totals`, ajouter avant le `return` :

```python
    monthly_water = compute_monthly_water_need_m3(dataset, allocation)
    total_water = float(compute_water_need_m3_by_plot(dataset, allocation).sum())
```

et ces quatre entrées au dict retourné :

```python
        "total_water_need_m3": total_water,
        "water_need_peak_month_m3": float(monthly_water.max()) if len(monthly_water) else 0.0,
        "soil_carbon_balance": float(
            compute_soil_carbon_balance_by_plot(dataset, allocation).sum()
        ),
        "soil_carbon_mineralization": float(
            compute_soil_carbon_mineralization_by_plot(dataset, allocation).sum()
        ),
```

Mettre à jour la docstring de `compute_environmental_totals` pour mentionner l'eau (m³, brute) et le carbone (t C, flux annuel).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_water_carbon.py -v`
Expected: PASS — 4 passed

Puis vérifier que les indicateurs existants ne régressent pas :
Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_indicators.py -v`
Expected: PASS (aucun échec nouveau)

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/indicators.py tests/test_guadeloupe_reporting_water_carbon.py
git commit -m "feat(indicateurs): agregation eau et carbone par allocation"
```

---

### Task 5: Table de faits, CSV mensuel et score composite

**Files:**
- Modify: `case_studies/guadeloupe/reporting/indicators.py` (`_FACT_MEASURES`, `compute_facts_table`)
- Modify: `case_studies/guadeloupe/reporting/report.py` (CSV mensuel)
- Modify: `case_studies/guadeloupe/dashboard/comparison.py` (`INDICATOR_DIRECTION`)
- Test: `tests/test_guadeloupe_reporting_water_carbon.py` (étendre)

**Interfaces:**
- Consumes: Task 4 (toutes les fonctions d'agrégation).
- Produces : colonnes `water_need_m3`, `soil_carbon_balance` dans la table de faits ; fichier `output_N/csv/water_need_monthly_<side>.csv` ; 4 entrées dans `INDICATOR_DIRECTION`.

**Attention :** `compute_facts_table` utilise l'helper `rate(name)`, qui indexe un paramètre **par culture**. L'eau fonctionne ainsi, mais le **carbone est parcellaire** (il dépend du type de sol de la parcelle) et ne peut pas passer par `rate()`. Il faut l'ajouter via les fonctions par parcelle de Task 4.

- [ ] **Step 1: Write the failing test**

Ajouter à la fin de `tests/test_guadeloupe_reporting_water_carbon.py` :

```python
def test_facts_table_carries_water_and_carbon_measures():
    dataset = _dataset()
    dataset.parameters["data_parc"]["REGION"] = [1, 1]
    dataset.parameters["data_parc"]["ILE"] = [1, 1]
    for name in ("rdt_cult", "sales_per_ha_cult", "subsidy_per_ha_cult_annualized",
                 "margin_per_ha_cult", "labor_hours_per_ha_cult"):
        dataset.parameters[name] = pd.Series({"CROP_A": 0.0, "CROP_B": 0.0})

    facts = indicators.compute_facts_table(
        dataset, _allocation(), hours_per_etp=1607.0, cost_per_hour=0.0
    )
    assert "water_need_m3" in facts.columns
    assert "soil_carbon_balance" in facts.columns
    # Les deux parcelles sont dans la meme (culture, region) -> une ligne agregee.
    assert facts["water_need_m3"].sum() == pytest.approx(2100.0)
    assert facts["soil_carbon_balance"].sum() == pytest.approx(-115.0)


def test_monthly_water_csv_series_has_twelve_calendar_rows():
    monthly = indicators.compute_monthly_water_need_m3(_dataset(), _allocation())
    assert len(monthly) == 12
    assert list(monthly.index)[0] == "BESOIN_EAU_01"
    assert list(monthly.index)[-1] == "BESOIN_EAU_12"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_water_carbon.py::test_facts_table_carries_water_and_carbon_measures -v`
Expected: FAIL — `AssertionError: assert 'water_need_m3' in ...`

- [ ] **Step 3: Write the implementation**

Dans `indicators.py`, étendre `_FACT_MEASURES` :

```python
_FACT_MEASURES = [
    "surface", "production", "sales", "subsidy", "revenue",
    "gross_margin", "labor_hours", "labor_cost", "etp",
    "ges", "ift", "azote", "surface_cld",
    "water_need_m3", "soil_carbon_balance",
]
```

Dans `compute_facts_table`, après la ligne `per_plot["surface_cld"] = ...`, ajouter :

```python
    # L'eau est un taux par culture, mais le carbone dépend du type de sol de la parcelle :
    # il ne peut pas passer par rate() et vient des fonctions par parcelle.
    per_plot["water_need_m3"] = compute_water_need_m3_by_plot(dataset, allocation).to_numpy()
    per_plot["soil_carbon_balance"] = compute_soil_carbon_balance_by_plot(
        dataset, allocation
    ).to_numpy()
```

Dans `report.py`, à côté de l'écriture de `facts_{side}.csv` (~ligne 53), ajouter dans la même boucle sur `side` / `allocation` :

```python
        indicators.compute_monthly_water_need_m3(dataset, allocation).to_csv(
            _csv_path(output_dir, f"water_need_monthly_{side}.csv"),
            header=["water_need_m3"],
            index_label="month",
        )
```

Dans `dashboard/comparison.py`, ajouter à `INDICATOR_DIRECTION` :

```python
    "total_water_need_m3": "cost",
    "water_need_peak_month_m3": "cost",
    "soil_carbon_balance": "benefit",
    "soil_carbon_mineralization": "cost",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_water_carbon.py -v`
Expected: PASS — 6 passed

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_water.py tests/test_guadeloupe_soil_carbon.py tests/test_guadeloupe_reporting_indicators.py tests/test_guadeloupe_dashboard_comparison.py -v`
Expected: PASS (aucun échec nouveau)

- [ ] **Step 5: Commit**

```bash
git add case_studies/guadeloupe/reporting/indicators.py case_studies/guadeloupe/reporting/report.py case_studies/guadeloupe/dashboard/comparison.py tests/test_guadeloupe_reporting_water_carbon.py
git commit -m "feat(indicateurs): eau et carbone dans la table de faits et le score composite"
```

---

### Task 6: Documentation des écarts assumés

**Files:**
- Modify: `VIGILANCE.md`
- Modify: `TODO.md`
- Modify: `CLAUDE.md`

Les quatre écarts au GAMS sont **déjà** consignés dans `VIGILANCE.md` (entrées du 2026-07-20 : pluviométrie mensuelle absente, bug `max(0, ·)`, facteur 10, flux carbone annuel) ainsi que le piège des deux ordres de types de sol. Cette tâche ne fait que refermer la boucle une fois le code livré.

- [ ] **Step 1: Marquer le lot comme livré dans `TODO.md`**

Dans la section « Chantier "indicateurs d'impact" », remplacer la ligne 1 par :

```markdown
1. **Eau + carbone organique du sol** — **livré le 2026-07-20**. Spec :
   `docs/superpowers/specs/2026-07-20-water-soil-carbon-indicators-design.md`.
   Validation unitaire seulement (aucun solve réel lancé).
```

- [ ] **Step 2: Ajouter une ligne à `CLAUDE.md`**

Dans la section « Architecture », après la description de l'étape 5 (`generate_report`), ajouter :

```markdown
Les indicateurs environnementaux vivent dans trois modules par culture — `environment.py`
(azote/GES/IFT), `water.py` (besoin en eau) et `soil_carbon.py` (bilan de carbone organique) —
tous calculés dans `data_pipeline` puis appliqués à l'allocation par `reporting/indicators.py`.
Le carbone est le seul à dépendre de la **parcelle** (via `TYPE_SOL` → `Data_Sol.txt`) et non
seulement de la culture : il ne passe donc pas par l'helper `rate()` de `compute_facts_table`.
```

- [ ] **Step 3: Vérifier que rien n'a été oublié dans VIGILANCE.md**

Relire les entrées du 2026-07-20 dans `VIGILANCE.md` et confirmer que les cinq points sont présents : deux ordres de types de sol, pluviométrie mensuelle absente, bug `max(0, ·)`, facteur 10 mm→m³, flux carbone annuel + amendements non annualisés. Ajouter ce qui manque.

- [ ] **Step 4: Lancer les tests du lot une dernière fois**

Run: `.venv/Scripts/python -m pytest tests/test_guadeloupe_water.py tests/test_guadeloupe_soil_carbon.py tests/test_guadeloupe_reporting_water_carbon.py tests/test_guadeloupe_pipeline_rates.py -v`
Expected: PASS — 13 passed

- [ ] **Step 5: Commit**

```bash
git add VIGILANCE.md TODO.md CLAUDE.md
git commit -m "docs(indicateurs): consigner le lot eau/carbone et ses ecarts GAMS"
```

---

## Vérification finale

Le lot est terminé quand :

1. `.venv/Scripts/python -m pytest tests/test_guadeloupe_water.py tests/test_guadeloupe_soil_carbon.py tests/test_guadeloupe_reporting_water_carbon.py tests/test_guadeloupe_pipeline_rates.py -v` passe intégralement.
2. `.venv/Scripts/python -m pytest tests/test_guadeloupe_reporting_indicators.py tests/test_readers.py -v` ne montre aucune régression.
3. `.venv/Scripts/python -c "import case_studies.guadeloupe.data_pipeline"` retourne 0.

**Ne pas lancer `main.py`.** La validation de ce lot est unitaire par construction : les indicateurs sont du post-traitement et ne peuvent pas rendre le modèle infaisable. Un run complet reste utile pour vérifier les ordres de grandeur sur données réelles, mais il relève de la fin de journée et d'une demande explicite de l'utilisateur.

**Ordre de grandeur attendu** au premier run réel, pour repérer une erreur d'unité : avec `PART_C_INIT` ≈ 3 %, le stock initial est ≈ 75 t C/ha, la minéralisation ≈ 2,4 t C/ha/an et les entrées par résidus ≈ 0,8 t C/ha/an — donc un **bilan négatif de l'ordre de −1,5 t C/ha/an**. Un bilan positif, ou un ordre de grandeur en milliers, signale une erreur de facteur. Côté eau, ≈ 1200 mm/an et par ha, soit ≈ 12 000 m³/ha/an.
