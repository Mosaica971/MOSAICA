# GAMS Parity Phase 2: Markovitz Risk-Adjusted Objective — Design

**Status:** Drafted overnight in automode, during the same session that implemented and
merged Phase 1. **Not yet reviewed by a human.** Phase 1 changed only mechanical
constraints (each one either binds or it doesn't); Phase 2 changes the objective
function itself, which silently reshapes every solve's result. Two of the open
questions below (the `Avers.txt` stub, and a dead-code branch in the GAMS
classification cascade) have no unambiguous answer inside the GAMS source, so this
design makes an explicit, documented judgment call on each rather than leaving a
placeholder — but they are exactly the kind of calls a domain-knowledgeable human should
sanity-check before this plan is executed. Recommend reading this spec before running
the accompanying implementation plan.

## Goal

Port the Markovitz risk-adjusted objective (`Eq_REV_MARKOVITZ` /
`Eq_REV_MARKOVITZ_GWAD`) as a second, mutually-exclusive Pyomo objective alongside the
existing `maximize_gross_margin`, plus the preprocessing pipeline that computes its two
new inputs: a per-farm risk-aversion coefficient (`AVERS`) and a per-crop yield-variance
coefficient (`Var_Rdt_Cult`).

## What Eq_REV_MARKOVITZ actually computes

Verbatim from `context/gams/MODELE.txt:424-430`:

```
Eq_REV_MARKOVITZ(SE)..   sum(SP$Expl_Parc(SE,SP), sum(SC, X(SP,SC)*MB_Ha_Cult(SC)                         ))
                       - sum(SP$Expl_Parc(SE,SP), sum(SC, X(SP,SC)*MB_Ha_Cult(SC)*Var_Rdt_Cult(SC,"init") )) * AVERS(SE)
                       =e= REV_MARKOVITZ(SE);
Eq_REV_MARKOVITZ_GWAD.. sum(SE,REV_MARKOVITZ(SE)) =e= REV_MARKOVITZ_GWAD;
```

Per farm: `gross_margin − AVERS(farm) × Σ(margin × variance_coefficient)`, summed
territory-wide. This is a **diagonal/variance-only** risk penalty — there is no
cross-crop covariance term anywhere in the GAMS source (confirmed by exhaustive search
of `DONNEES.txt`, `DECLAR_OPT.txt`, `OPTIMISATION.txt`). `Var_Rdt_Cult(crop,"init")` is a
per-crop scalar in `[0,1]` (already on disk:
`data/tables/indice_H/Var_Rdt_Cult.txt`, `init` column) — despite its GAMS table
description reading "yield in tonnes/ha" (a copy-paste error from the neighboring
`Rdt_Cult` table's real description), its actual values and usage make it a relative
yield-variability/risk-loss fraction: `MB × (1 − Var_Rdt_Cult)` is used elsewhere
(`OPTIMISATION.txt:70`) as "margin under a bad-yield scenario," confirming this reading.

**This is the real production objective, not an optional add-on.** GAMS's driver
(`OPTIMISATION.txt:174-185`) maximizes plain `REV` only for the trivial `NB_BOUCLE=0`
initialization pass (which just pins `X` to observed 2017 land use via an equality
constraint — no actual optimization). Every real solve (`CALIB`, `SCENARIO`) maximizes
`REV_MARKOVITZ_GWAD`. `Eq_REV`/`REV` is still computed in those models, but only as a
reported quantity. This port adds Markovitz as a selectable alternative in the Python
registry (matching this codebase's existing "exactly one enabled objective" pattern,
`core/model/builder.py:52-58`), but a maintainer picking a default for a real
policy-relevant run should know GAMS's own real answer was Markovitz, not plain margin.

### Dead code found, not to be ported

`OPTIMISATION.txt:74-82` computes nine farm-type-specific alternate margin measures
(`MB_Ha_Cult_Marko_ARBORICULTEUR`, `_BANANIER`, etc.). Grepped every file in
`context/gams/` — none of these parameters are referenced anywhere else
in the model or its outputs. This is a superseded, abandoned approach to the same idea,
left in the source. Do not port it.

## The two new inputs

### `Var_Rdt_Cult(crop, "init")` — already available, no new pipeline needed

On disk at `data/tables/indice_H/Var_Rdt_Cult.txt`, same wide-table shape as the
already-ported `Rdt_Cult`/`Prix_Cult` tables `case_studies/guadeloupe/data_pipeline.py`
already reads with `read_wide_table(...)[YEAR]`. This needs only
`read_wide_table(INDICE_H_DIR / "Var_Rdt_Cult.txt")["init"]` — one line, same pattern as
six neighboring tables already in that file.

### `AVERS(farm)` — needs a new preprocessing pipeline; the on-disk file is not usable as-is

`data/tables/Avers.txt` exists (5,336 rows) but is a **uniform stub**: every farm has
`AVERS=1`. The real GAMS cascade produces ten possible discrete values
(`0, 0.30, 0.50, 0.55, 1.20, 1.30, 1.40, 1.60, 2.30, 2.40`) keyed off a farm-typology
classification (`TYPE_EXPL`), not a flat constant. **Decision: treat `Avers.txt` as an
unvalidated placeholder and compute `AVERS` from the ported cascade rather than reading
the file.** (`data/` is gitignored, so there's no commit history indicating whether this
file was ever meant to hold real values — a human with access to the original GAMS
run's output could confirm this file is stale, but absent that, using a uniform
`AVERS=1` for every farm would silently make risk-aversion meaningless — every farm
penalized identically regardless of their real risk profile is equivalent to not
implementing Markovitz's actual purpose. Computing it from source is the more
GAMS-faithful choice and doesn't cost much: all its raw inputs are already on disk.)

**Cascade** (`OPTIMISATION.txt:1467-1561` for `TYPE_EXPL`/`TYPE_EXPL_Bis`, `:1744-1758`
for the `AVERS` lookup — all values below re-verified directly against the source during
plan-writing, superseding an earlier, incomplete pass over this section):

1. Per farm, compute land-use shares by crop group from the farm's **initial (2017)**
   observed allocation, each as a share of cultivated area excluding fallow/non-cultivated
   (`SURF_CUL − SURF_NON`, see step 4 for exact set membership):
   `PART_CAN` (cane, `SC_CAN`), `PART_PAT` (pasture, `SC_PAT`), `PART_BAN` (export
   banana, `SC_BAN_EX` — **not** the wider `SC_BAN = SC_BAN_EX ∪ SC_BC`, a
   similarly-named but different set that TYPE_EXPL does not use), `PART_MAR` (market
   garden + tubers, `SC_MAR`), `PART_PLU` (perennial/tree crops, `SC_PLU`), plus two more
   needed only for step 3's sub-split: `PART_BC` (plantain banana, `SC_BC`) and `PART_TT`
   (tubers, confusingly computed as `sum(SC_IG, ...)` in GAMS despite the "TT" name —
   `SC_IG` is the correct set, there is no separate `SC_TT`).
2. Classify into `TYPE_EXPL ∈ {0..8}` via the threshold cascade at
   `OPTIMISATION.txt:1542-1552` (values transcribed in the implementation plan). **Decision:
   use this cascade, not the different-threshold cascade at `OPTIMISATION.txt:1530-1540`
   immediately above it.** Both blocks assign the same `TYPE_EXPL(SE)` parameter in
   sequence; only the second one's result survives to
   `STOCK_TYPE_EXPL(SH,SE) = TYPE_EXPL(SE)` (`OPTIMISATION.txt:1553`), which is the only
   place `TYPE_EXPL` is read after being set. The first block is unreachable dead code —
   its output is unconditionally overwritten before anything reads it. (This is the same
   category of "which of two GAMS blocks is authoritative" question Phase 1 hit with
   `Eq_BA_JA`/`Eq_BA_ROTA`; here the tie-break is unambiguous — GAMS execution order plus
   single-read-site makes the second block's precedence a hard fact, not a judgment
   call — but it's flagged here because getting it backwards would silently produce a
   different, wrong classification for every farm.) **User confirmed 2026-07-08: proceed
   with this reading.**
3. **Newly found during plan-writing, not in the original design pass:** farms classified
   `TYPE_EXPL=4` ("Canniers diversifiés") get a second-level split into
   `TYPE_EXPL_Bis ∈ {41, 42}` (`OPTIMISATION.txt:1557-1561`) based on `PART_MAR`,
   `PART_PLU`, `PART_BC`, `PART_TT`, and **this sub-split — not the bare `TYPE_EXPL=4`
   value — determines `AVERS` for every type-4 farm** (see step 4). Both `41`'s and `42`'s
   conditions are OR-chains evaluated in GAMS's `IF`/`IF` (not `IF`/`ELSEIF`) sequence, so
   whichever condition is true *last* wins if both are true — same "last assignment in
   iteration order wins" semantics as step 2. In practice `42`'s condition
   (`PART_MAR=0 OR PART_PLU=0 OR PART_BC=0 OR PART_TT=0`) is true for the large majority
   of real farms (any one of the four shares being exactly zero triggers it, and having
   all four simultaneously positive is rare), so most type-4 farms end up `42`; only
   farms diversified across all four of market-garden/perennial/plantain/tuber
   simultaneously stay at `41`.
4. Look up `AVERS(farm)` from `TYPE_EXPL(farm)` (and `TYPE_EXPL_Bis(farm)` for type-4
   farms) via the table at `OPTIMISATION.txt:1744-1758`, applied in GAMS's exact order —
   the `TYPE_EXPL=4 → 1.40` assignment always fires first for a type-4 farm and is then
   unconditionally overwritten by its `TYPE_EXPL_Bis` value, so `1.40` never survives as a
   final value for any real farm (this corrects the original design pass, which listed
   `1.40` as one of "ten possible discrete values" — it is transient, not final):

   | `TYPE_EXPL` | Label (from GAMS comment) | `AVERS` |
   |---|---|---|
   | 1 | Arboriculteurs | 1.30 |
   | 2 | Bananiers | 1.20 |
   | 3 | Canniers | 0.30 |
   | 4, then Bis=41 | Canniers diversifiés (fully diversified) | 0.50 |
   | 4, then Bis=42 | Canniers diversifiés (partially diversified) | 1.60 |
   | 5 | Diversifiés | 0.55 |
   | 6 | Eleveurs | 2.40 |
   | 7 | Maraîchers | 0.00 |
   | 8 | Mixtes canniers-éleveurs | 2.30 |
   | 0 | Frichiers (`SURF_CUL=0`) | 0.00 (default, never overwritten — `ENTREES.txt:487` initializes `AVERS(SE)=0`, confirmed, and no lookup row targets `TYPE_EXPL=0`) |

   Nine distinct final values: `{0, 0.30, 0.50, 0.55, 1.20, 1.30, 1.60, 2.30, 2.40}` (not
   ten — `1.40` is excluded per the correction above).

**Exact crop-group set membership** (re-verified directly against
`context/gams/SETS.txt` during plan-writing; only `SC_BC`, `SC_IG`,
`SC_BAN_EX` already existed as `config.yaml` anchors from Phase 1 and need no changes —
`SC_CAN`, `SC_PAT`, `SC_NON`, `SC_MAR`, `SC_CULTIV` are new and must be added):

- `SC_CAN` (29 codes) = `SC_CF` (10 cane-fiber ITK codes: `CF_NBT_NISM, CF_NBT_NIM,
  CF_SBT_NISM, CF_SBT_NIM, CF_NGT_NISM, CF_NGT_NIM, CF_CGT_NISM, CF_CGT_NIM, CF_EGT_NISM,
  CF_EGT_NIM`) ∪ `SC_CS` (the existing 19-code `cs` anchor, which includes the bare `CS`
  in addition to its 18 ITK-technique variants).
- `SC_PAT` (3 codes) = `[PN, PN_PIQ, PN_TOUR]`.
- `SC_NON` (2 codes) = `[JA, NC]`.
- `SC_MAR` (35 codes) = the existing 30-code `ma` anchor ∪ the existing 3-code `ig`
  anchor ∪ `{ME, TH}` (two additional bare codes not covered by either existing anchor —
  `ME` = melon, `TH` appears in the crop universe but is never produced by the base
  RPG→crop mapping below, so it is a harmless always-zero member for this port's purposes).
- `SC_CULTIV` = the full 84-code crop universe minus `NC` (83 codes) — i.e. every crop
  code except "non cultivé", notably including `JA` (fallow still counts as
  "cultivated" for this set, which is exactly why the `PART_*` shares divide by
  `SURF_CUL − SURF_NON` rather than by `SURF_CUL` alone: `SURF_NON = JA + NC` area still
  needs subtracting out even though `JA` is inside `SC_CULTIV`).

Because this port already scopes `TYPE_EXPL`'s inputs to the **base crop-group** mapping
(next section) rather than the full ITK-technique code space, and every one of these
family sets contains its own "bare" base-group code as a member (`CS ∈ SC_CS ⊂ SC_CAN`,
`BA ∈ SC_BAN_EX`, `BC ∈ SC_BC`, `IG ∈ SC_IG ⊂ SC_MAR`, `MA ∈ SC_MAR`, `ME ∈ SC_MAR`,
`PN ∈ SC_PAT`, `AG, VE ∈ SC_PLU`, `JA, NC ∈ SC_NON`), each of a plot's 12 possible base
crop groups maps to exactly one family aggregate — no ITK-level detail is needed to
compute any `SURF_*`/`PART_*` share correctly.

Both `TYPE_EXPL` and `AVERS` are computed once from the **initial** observed allocation
and never recomputed for later years, even in GAMS's own multi-year loop
(`STOCK_TYPE_EXPL("init",SE)` is what feeds `AVERS`, not the current-year value) — so
this reduces to a **pure preprocessing step**, no iterative solve loop needed. This
matches the current Python model's shape (`case_studies/guadeloupe/model.py` is
single-period); no multi-year `LOOP` construct needs to be introduced.

### `Matrice_Parc_Cult` — only the base crop-group mapping is needed, not the full ITK cascade

`TYPE_EXPL`'s land-use shares (`SURF_CAN`, `SURF_PAT`, etc.) are defined over coarse
crop-group sets (`SC_CAN`, `SC_PAT`, `SC_BAN_EX`, `SC_MAR`, `SC_PLU`) — granularity
coarser than the ITK-technique split (e.g. all of `CS_BT_NISM`/`CS_BT_NIM`/... roll up
into `SC_CAN` regardless of which ITK variant). **Decision: port only the base
crop-code mapping** (`ENTREES.txt:62-103` — maps each plot's observed `cult_2017` RPG
code to one of the model's base crop groups) **and skip the ITK-technique refinement**
(`ENTREES.txt:304-458` — the region/soil/farm-size cascade that further splits `BA` into
`BA_INT`/`BA_SINT`/`BA_PER`/`BA_IRR`, etc.). Nothing in the Markovitz objective or the
`TYPE_EXPL`/`AVERS` pipeline consumes the ITK-level split; it exists in GAMS to drive
`Eq_SURF_INIT_Parc`'s initial-allocation pinning and a few Canne-Énergie-scenario
equations, none of which are in scope here. If a future phase needs per-ITK initial
allocations, the full cascade can be added then — deferring it now keeps this phase
tightly scoped to what Markovitz actually requires.

**Complete RPG→base-crop-group mapping** (`ENTREES.txt:62-103`, all 20 codes,
re-verified verbatim during plan-writing):

| RPG `cult_2017` code | Meaning | Base group |
|---|---|---|
| 1 | Agrumes | `AG` |
| 2 | Ananas | `AN` |
| 3 | Banane créole | `BC` |
| 4 | Banane export | `BA` |
| 5 | Café/Cacao | `VE` |
| 6 | Canne à sucre | `CS` |
| 7 | Cultures fourragères | `PN` |
| 8 | Horticulture ornementale de plein champ | `MA` |
| 9 | Horticulture ornementale sous abri | `MA` |
| 10 | Jachère | `JA` |
| 11 | Maraîchage de plein champ | `MA` |
| 12 | Maraîchage sous abri | `MA` |
| 13 | Melon | `ME` |
| 14 | Non cultivé | `NC` |
| 15 | Pastèque | `MA` |
| 16 | Prairie permanente | `PN` |
| 17 | Prairie temporaire | `PN` |
| 18 | Tubercules tropicaux | `IG` |
| 19 | Vanille et PPAM | `VE` |
| 20 | Vergers | `VE` |

A continuity override precedes this mapping (`ENTREES.txt:49-57`). **Correction found
during Task 2's review (2026-07-09):** the human-readable comment on line 49 states the
rule as a 3-year check ("si Non cultivé ou Jachère en 2015, 2016 et 2017"), but the
`cult_2015` clause of the actual `IF` condition is commented out in the executable GAMS
(`*` in column 1, `ENTREES.txt:51`) — the *real*, executable rule only checks
`cult_2016` and `cult_2017`. Confirmed by reading the raw file bytes directly (the `*`
is unambiguous; this file uses the same leading-`*`-disables-a-line convention
throughout, including its own section-header banners). **The correct rule: if a plot's
`cult_2016` and `cult_2017` are both in `{14, 10, 0}`, `cult_2017` is force-set to `14`
(Non cultivé) before the table above is applied — `cult_2015` plays no role.** This is a
narrower, RPG-code-space version of the same "fallow-for-N-years" idea Phase 1's
`friche_lock` rule already implements at the crop-eligibility level
(`core/data/eligibility.py`) — the two are independent mechanisms (this one only affects
which base group a farm's *own* initial allocation is classified into for `TYPE_EXPL`;
it does not touch plot eligibility) and both must exist.

## Architecture

New `ModelInputs` fields (2), following the exact pattern Phase 1 used for
`farm_gfa_surface_ha` etc.:
```python
crop_variance_per_ha: Mapping[str, float] = field(default_factory=dict)
farm_risk_aversion: Mapping[str, float] = field(default_factory=dict)
```

New objective builder in `core/model/objectives.py`, registered
`"maximize_risk_adjusted_gross_margin"`:
```python
@register_objective("maximize_risk_adjusted_gross_margin")
def build_maximize_risk_adjusted_gross_margin_objective(
    model: pyo.ConcreteModel, inputs: ModelInputs, **_args
) -> None:
    model.objective = pyo.Objective(
        expr=sum(
            model.Y[plot, crop] * inputs.plot_surface_ha[plot] * inputs.crop_margin_per_ha[crop]
            * (1 - inputs.farm_risk_aversion.get(farm, 0.0) * inputs.crop_variance_per_ha.get(crop, 0.0))
            for farm, plots in inputs.farm_plots.items()
            for plot in plots
            for crop in [c for p, c in inputs.eligible_pairs if p == plot]
        ),
        sense=pyo.maximize,
    )
```
(Exact comprehension shape to be finalized in the implementation plan — the point above
is the algebraic content: `Σ Y·surface·margin·(1 − AVERS(farm)·Var(crop))`, algebraically
identical to `Σ Y·surface·margin − AVERS(farm)·Σ Y·surface·margin·Var(crop)` from the
GAMS equation. A plot-keyed-to-farm lookup is needed since `eligible_pairs` is
plot/crop-indexed but `AVERS` is farm-indexed — likely cleanest via a precomputed
`plot_to_farm` dict built once from `farm_plots`, rather than the quadratic filter shown
above; the plan will specify this precisely.)

New preprocessing module, `case_studies/guadeloupe/farm_typology.py`:
- `compute_base_crop_group(data_rpg_cult2017_column) -> pd.Series` — the RPG-code-to-
  base-crop-group mapping (`ENTREES.txt:62-103`), 14-way lookup.
- `compute_type_expl(farm_plots, base_crop_group, plot_surface_ha) -> pd.Series` — the
  land-use-share cascade (`OPTIMISATION.txt:1542-1552`).
- `compute_avers(type_expl) -> pd.Series` — the ten-value lookup
  (`OPTIMISATION.txt:1744-1761`).

Wiring: `case_studies/guadeloupe/data_pipeline.py` calls these three functions and adds
`crop_variance_per_ha` (from `Var_Rdt_Cult`) and `farm_risk_aversion` (from
`compute_avers`) to the returned `parameters` dict, then `case_studies/guadeloupe/
model.py` passes them through to `build_crop_allocation_model` alongside the existing
farm-level kwargs.

Config: add a second, disabled-by-default `objectives:` entry
(`maximize_risk_adjusted_gross_margin`) to `case_studies/guadeloupe/config.yaml`,
leaving `maximize_gross_margin` as the enabled default — switching which one is enabled
is a one-line config change, matching how Phase 1 left `cs_gfa_minimum_share` available
but disabled. **Recommendation, not yet actioned:** given GAMS's own real solves always
maximized Markovitz, a maintainer with domain authority to decide "what does this
codebase's default answer mean" should choose whether to flip which objective is
enabled by default — that's a modeling-policy decision, not a porting one, so this spec
doesn't make that call.

## Testing strategy

Same TDD/registry pattern as Phase 1: unit tests for each `farm_typology.py` function
against small synthetic fixtures (verify each `TYPE_EXPL` threshold boundary, verify the
AVERS lookup table exactly), a unit test for the objective builder against a small
model (2-3 plots, hand-computed expected objective value), and a real-dataset
integration test that builds `TYPE_EXPL`/`AVERS` from the actual 2017 Guadeloupe data
and checks the resulting distribution is plausible (e.g. assert the ten expected AVERS
values all appear at least once across 5,336 farms, catching a wiring bug that would
otherwise silently produce a uniform-again result).

## Explicitly out of scope for Phase 2

- The full ITK-technique cascade (`ENTREES.txt:304-458`) — ported only if a future phase
  needs per-ITK initial allocations.
- Any multi-year `LOOP` structure — GAMS's own `AVERS`/`Var_Rdt_Cult("init")` pinning
  means this isn't needed for Markovitz specifically.
- Re-validating or replacing `data/tables/Avers.txt` on disk — this design computes
  `AVERS` in-memory during dataset building rather than reading that file at all, so the
  stale file becomes simply unused, not fixed. Deleting or regenerating it on disk is a
  separate, optional cleanup.

## Open items — resolved 2026-07-08

1. `TYPE_EXPL` dead-code tie-break (second cascade block wins): confirmed unambiguous
   from GAMS execution order + single-read-site; user approved proceeding on this
   reading.
2. `Avers.txt` stub vs. in-memory computation: user does not have institutional
   knowledge to confirm either way. **Decision: compute `AVERS` in-memory from the
   ported cascade** (this design's original recommendation), and leave an explicit code
   comment plus a note in the implementation plan flagging this for later verification
   against a real GAMS run's output, if one becomes available.
3. Default-enabled objective: **decision: keep `maximize_gross_margin` enabled by
   default**; ship `maximize_risk_adjusted_gross_margin` disabled, a one-line
   `config.yaml` flip to enable — same pattern Phase 1 used for `cs_gfa_minimum_share`.

## Correction made during plan-writing (2026-07-08)

The original design pass (drafted overnight) summarized the `TYPE_EXPL`/`AVERS` cascade
from a research agent's conversational report rather than re-reading the GAMS source
directly, and missed the `TYPE_EXPL_Bis` sub-split entirely — it claimed `AVERS` had "ten
possible discrete values" including `1.40` for bare `TYPE_EXPL=4`. Re-reading
`OPTIMISATION.txt:1467-1561` and `:1744-1758` directly while writing the implementation
plan found that every `TYPE_EXPL=4` farm is always subsequently reclassified into
`TYPE_EXPL_Bis ∈ {41,42}`, and `1.40` is never a farm's final `AVERS` value — see the
corrected "Cascade" section above for the exact nine-value table. The plan below
implements the corrected version.
