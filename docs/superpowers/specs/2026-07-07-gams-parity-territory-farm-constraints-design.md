# GAMS parity: territory/farm constraints (Phase 1) + Markovitz risk objective (Phase 2)

## Goal

Port the remaining GAMS equations from `context/gams/MODELE.txt` that are
not yet in the Python model, so the Guadeloupe crop-allocation model matches what the
reference GAMS `SCENARIO` solve actually optimizes: farm-level area/labor/production
caps, territory-wide quota ceilings and production floors, the banana fallow/rotation
rule, the 3-year fallow lock, and (Phase 2) the Markovitz risk-adjusted objective that
GAMS actually solves in `CALIB`/`SCENARIO` instead of plain gross margin.

All formulas below are copied verbatim from `MODELE.txt`/`DONNEES.txt`/`OPTIMISATION.txt`
(line numbers given), re-verified directly against source during this design pass — not
taken secondhand from the originating audit report, which had two factual errors
(corrected below).

## Corrections to the originating audit report

- **Item 11 (`Eq_ME_Reg`, melon regional ban) is already correctly implemented**, via the
  `region_crop_forbidden` categorical rule in today's `config.yaml` — byte-for-byte match
  of GAMS's `SRM` region list, regression-tested in `test_guadeloupe_pipeline.py`. Not a
  gap; no work needed.
- **Item 13 (`BV_PARC`/`CPT_PARC`, watershed/catchment)**: confirmed used only in GAMS
  post-solve reporting aggregation, never in a hard constraint. No constraint work needed;
  out of scope here.
- **Item 12 (fiber-cane block, `Eq_CF_MIN`/`Eq_CF_T0..T8`/`Eq_CF_CS_*_NISM`)**: declared in
  GAMS with algebraic bodies but **never included in the `INIT`/`CALIB`/`SCENARIO` model
  statements actually solved** (`MODELE.txt` lines 443-697, grepped exhaustively — zero
  matches). Fiber cane is fully suppressed in the reference model via separate always-on
  prohibition equations. Dropped from scope entirely — building it would be unused
  machinery.
- **`Eq_BA_JA`/`Eq_BA_ROTA` (item 9) produce one constraint per (farm, banana-subtype)
  pair, not one per farm.** The equations are declared `Eq_BA_JA(SE,SC_BA_JA)..` and the
  RHS (`sum(SP$Expl_Parc(SE,SP), X(SP,SC_BA_JA))`) does *not* sum over the `SC_BA_JA` set —
  in GAMS, a bare set-name reference inside an equation body that is also one of the
  equation's own domain indices is bound to that single element per equation instance, it
  is not implicitly summed. Confirmed unambiguously against `Eq_FRICHE(SP,SC_CULT_NON_NC)..
  X(SP,SC_CULT_NON_NC) =l= 0` (`MODELE.txt` line 307), where `X(SP,SC_CULT_NON_NC)` can only
  mean "the single bound crop for this instance" (a variable reference can't sum a free
  index on its own). So `Eq_BA_JA`/`Eq_BA_ROTA` generate 3 constraints per farm (one each
  for `BA_INT`, `BA_IRR`, `BA_SINT`), each comparing fallow area against that *one*
  banana-subtype's area — not fallow vs. the combined 3-subtype area.

## Non-goals

- Fiber-cane scenario block — see correction above.
- `BV_PARC`/`CPT_PARC` watershed/catchment constraints — see correction above.
- No new "solve mode" (`INIT`/`CALIB`/`SCENARIO`) abstraction. `config.yaml` stays one
  file; the default enabled set mirrors GAMS `SCENARIO` (confirmed the superset — every
  equation active in `CALIB` is also active in `SCENARIO`, per `MODELE.txt` lines 450-693).
- `Eq_ME_QUOTA_MAX`, `Eq_AN_QUOTA_MAX`, `Eq_IG_QUOTA_MAX`, `Eq_BC_QUOTA_MAX`,
  `Eq_TUB_PROD_OBJ` are implemented (registered, available) but shipped `enable: false`,
  since GAMS itself keeps them commented out / unused in the model it actually solves
  (`MODELE.txt` lines 548-551, 665-668; `Eq_TUB_PROD_OBJ` never appears in either model
  list at all).
- No change to existing eligibility criteria/categorical rules beyond adding the new
  `friche_lock` rule.

## Scope / phasing

**Phase 1** (primary target, fully data-available, no blockers): farm pineapple/yam area
caps, GFA sugarcane-share rule, 6 territory quota ceilings, 7 territory production floors,
4 nutrition-category floors, banana fallow/rotation rule, 3-year fallow lock.

**Phase 2** (after Phase 1 is implemented and tested): the Markovitz risk-adjusted
objective, farm labor cap, farm-level banana quota. These three share one real blocker:
they need to know which *specific* ITK crop-variant (e.g. `BA_INT` vs `BA_IRR`) was
initially (2017) on each plot — GAMS derives this via classification logic, it is not
stored as data anywhere. `Avers.txt`, which looks like ready per-farm risk data, is a
placeholder (every farm = 1); the real coefficient requires deriving an 8-category farm
typology first.

---

## Phase 1

### Equation → mechanism map

| GAMS equation | Index | Mechanism | Default `enable` |
|---|---|---|---|
| `Eq_AN_AGRO_MAX_Expl` | farm | `farm_area_share_max` | true |
| `Eq_IG_AGRO_MAX_Expl` | farm | `farm_area_share_max` | true |
| `Eq_CS_GFA` | farm (gated) | `cs_gfa_minimum_share` (case-study specific) | true |
| `Eq_BA_QUOTA_MAX` | territory | `territory_production_bound` | true |
| `Eq_CS_QUOTA_MAX` | territory | `territory_production_bound` | true |
| `Eq_ME_QUOTA_MAX` / `Eq_AN_QUOTA_MAX` / `Eq_IG_QUOTA_MAX` / `Eq_BC_QUOTA_MAX` | territory | `territory_production_bound` | **false** (inactive in GAMS reference too) |
| `Eq_BC/IG/MA/AN/PLU/ME/PN_PROD_MIN` (7) | territory | `territory_production_bound` | true |
| `Eq_LEG_PROD_OBJ` / `Eq_FRU_PROD_OBJ` / `Eq_PAT_SURF_OBJ` | territory | `territory_production_bound` | true |
| `Eq_TUB_PROD_OBJ` | territory | `territory_production_bound` | **false** (never active in GAMS) |
| `Eq_BA_JA` | farm × banana-subtype | `farm_area_ratio_min` | true |
| `Eq_BA_ROTA` | farm × banana-subtype | `farm_area_ratio_min` | true |
| `Eq_FRICHE` | plot × crop | new `categorical_rule` (`friche_lock`), not a Pyomo constraint | true |

### Architecture

**`core/model/model_inputs.py`** — extend `ModelInputs` (all new fields default to
empty mapping so existing callers/tests are unaffected):

```python
@dataclass
class ModelInputs:
    plot_surface_ha: Mapping[str, float]
    crop_margin_per_ha: Mapping[str, float]
    eligible_pairs: Sequence[tuple[str, str]]
    farm_plots: Mapping[str, Sequence[str]] = field(default_factory=dict)
    farm_surface_ha: Mapping[str, float] = field(default_factory=dict)
    crop_yield_per_ha: Mapping[str, float] = field(default_factory=dict)
```

**`core/model/builder.py`** — `build_crop_allocation_model` gains optional
`farm_plots`, `farm_surface_ha`, `crop_yield_per_ha` parameters (default `{}`), threaded
into `ModelInputs`. Adds `model.FARMS = pyo.Set(initialize=list(farm_plots.keys()))`.

**`core/model/constraints.py`** — three new generic, reusable builders (case-study
agnostic, live in `core/` like `at_most_one_crop_per_plot` today):

- `territory_production_bound(model, inputs, *, label, groups, sense, threshold)` —
  `groups` is a list of `{crops: [...], use_yield: bool, rate_multiplier: float}`. Builds
  `sum(Y[p,c]*surface[p]*(yield[c] if use_yield else 1.0)*rate_multiplier for group in
  groups for (p,c) in eligible_pairs if c in group.crops) <=/>= threshold`. Covers all 6
  quota ceilings, all 7 production floors, and all 4 nutrition floors (`Eq_FRU_PROD_OBJ`
  is the only multi-group case: BC + AN×(12/18) + PLU + ME, one `territory_production_bound`
  entry with 4 groups). Because this builder is invoked many times with different config
  entries, `label` is required and used as the Pyomo attribute name
  (`setattr(model, label, pyo.Constraint(...))`) — this is a new convention this design
  introduces; `at_most_one_crop_per_plot` (single-instance) is unaffected and keeps its
  fixed attribute name.
- `farm_area_share_max(model, inputs, *, label, crops, max_share)` — per farm e:
  `sum(Y[p,c]*surface[p] for p in farm_plots[e], c in crops if eligible) <= max_share *
  farm_surface_ha[e]`. Covers pineapple/yam caps.
- `farm_area_ratio_min(model, inputs, *, label, numerator_crops, denominator_crops,
  ratio)` — for each farm e, for each crop d in `denominator_crops`: `sum(Y[p,c]*surface[p]
  for p in farm_plots[e], c in numerator_crops if eligible) >= ratio *
  sum(Y[p,d]*surface[p] for p in farm_plots[e] if (p,d) eligible)`. Two config entries
  cover `Eq_BA_JA` (`numerator_crops: [JA]`) and `Eq_BA_ROTA` (`numerator_crops: [JA] +
  SC_CS (19 codes) + SC_CF (10 codes)`), both with `denominator_crops: SC_BA_JA
  ([BA_INT, BA_IRR, BA_SINT])`, `ratio: 0.2`.

**New file `case_studies/guadeloupe/constraints.py`** — one case-study-specific builder,
since it is the only constraint needing a farm's *tenure-flagged* surface, not worth a
generic indirection mechanism for a single caller:

- `cs_gfa_minimum_share(model, inputs, *, label, crops, min_share)` — only builds the
  constraint for farms where `inputs.farm_gfa_surface_ha[e] > 0` (mirrors GAMS's `$`
  conditional equation activation — the equation is simply absent for other farms, not a
  trivially-true constraint). `sum(Y[p,c]*surface[p] for p in farm_plots[e], c in crops if
  eligible) >= min_share * farm_gfa_surface_ha[e]`.
- Imported in `case_studies/guadeloupe/model.py` (`from case_studies.guadeloupe import
  constraints as _guadeloupe_constraints  # noqa: F401`) so the decorator registers before
  `build_crop_allocation_model` resolves `config["constraints"]`.
- `ModelInputs` also needs `farm_gfa_surface_ha: Mapping[str, float]` (add alongside the
  other Phase 1 fields above — used only by this one builder, kept generic-named since
  `ModelInputs` is meant to stay case-study-agnostic in spirit even though this dataset
  happens to be Guadeloupe's).

**`core/data/eligibility.py`** — new categorical rule:

```python
@register_categorical_rule("friche_lock")
def rule_friche_lock(data_parc, *, crops, history_columns, fallow_codes):
    condition = pd.Series(True, index=data_parc.index)
    for col in history_columns:
        condition &= data_parc[col].isin(fallow_codes)
    return crops, condition
```

Config: `history_columns: [cult_2015, cult_2016, cult_2017]`, `fallow_codes: [0, 10, 14]`.
`crops` is the 83-code `CULT_NON_NC` list, copied verbatim (programmatically, not
hand-typed, to avoid transcription errors) from `data/sets/CULT_NON_NC_2017.set` into
`config.yaml` — kept as an explicit literal list like every other categorical rule's
`crops` arg, rather than inventing a "load crops from a named set" indirection for one
rule.

**`case_studies/guadeloupe/data_pipeline.py`** additions:

- `farm_plots`: `expl_parc.groupby("farm")["plot"].apply(list).to_dict()`.
- `crop_yield_per_ha`: expose the already-loaded `rdt_cult` series (already in
  `parameters["rdt_cult"]` — just thread it into `build_model`).
- `farm_gfa_surface_ha`: per farm, `sum(surface_ha * GFA_PARC)` over its plots — same
  merge/groupby shape as the existing `compute_farm_surface_ha`.
- Merge `cult_2015`, `cult_2016`, `cult_2017` from `Data_RPG_Gwad_2017.txt` into
  `data_parc` (same pattern as the existing `REGION_CODE` merge from `reg_parc`), for the
  `friche_lock` rule.
- **Footnote on a GAMS source inconsistency**: `Eq_CS_GFA`'s gating condition references
  `Data_RPG_Gwad(SP,"GFA_PARC")` while its RHS sum references `Data_Parc_Gwad(SP,"GFA_PARC")`
  (`MODELE.txt` lines 348-349) — inconsistent table names in the original GAMS. In this
  repo, `Data_RPG_Gwad_2017.txt` only carries `cult_2012..cult_2017` (no `GFA_PARC`), while
  `Data_Parc_Gwad_2017.txt` has it. Decision: use `Data_Parc_Gwad`'s `GFA_PARC` for both the
  gate and the sum (both are the same value in the original GAMS tables anyway, per the
  `MIN_CS_GFA` comment block).

**`case_studies/guadeloupe/model.py`** — pass the new dataset parameters through to
`build_crop_allocation_model`.

### Exact formulas (for implementation reference)

```
Eq_AN_AGRO_MAX_Expl(SE).. sum((SP,SC_AN)$Expl_Parc(SE,SP),X(SP,SC_AN)) =l= MAX_AGRO_AN * SURF_Expl_init(SE);
Eq_IG_AGRO_MAX_Expl(SE).. sum((SP,SC_IG)$Expl_Parc(SE,SP),X(SP,SC_IG)) =l= MAX_AGRO_IG * SURF_Expl_init(SE);
  MAX_AGRO_AN=0.75, MAX_AGRO_IG=0.66  (DONNEES.txt:17,20)

Eq_CS_GFA(SE)$(sum(SP$Expl_Parc(SE,SP), Data_RPG_Gwad(SP,"GFA_PARC")) >0)..
    sum((SP,SC_CS)$Expl_Parc(SE,SP), X(SP,SC_CS)) =g=
    sum(SP$Expl_Parc(SE,SP), SURF_Parc_init(SP)*Data_Parc_Gwad(SP,"GFA_PARC"))*MIN_CS_GFA;
  MIN_CS_GFA=0.6  (DONNEES.txt:14)

Eq_BA_QUOTA_MAX.. sum((SP,SC_BAN_EX), X(SP,SC_BAN_EX)*RDT_Cult_BA(SC_BAN_EX))=l=QUOTA_BA_MAX;        QUOTA_BA_MAX=77877
Eq_ME_QUOTA_MAX.. sum(SP, X(SP,"ME")*RDT_Cult_ME("ME"))=l=QUOTA_ME_MAX;                                QUOTA_ME_MAX=80000 (disabled)
Eq_AN_QUOTA_MAX.. sum((SP,SC_AN), X(SP,SC_AN)*RDT_Cult_AN(SC_AN)/18*12)=l=QUOTA_AN_MAX;                QUOTA_AN_MAX=70000 (disabled)
Eq_IG_QUOTA_MAX.. sum((SP,SC_IG), X(SP,SC_IG)*RDT_Cult_IG(SC_IG))=l=QUOTA_IG_MAX;                       QUOTA_IG_MAX=50000 (disabled)
Eq_BC_QUOTA_MAX.. sum((SP,SC_BC), X(SP,SC_BC)*RDT_Cult_BC(SC_BC))=l=QUOTA_BC_MAX;                       QUOTA_BC_MAX=40000 (disabled)
Eq_CS_QUOTA_MAX.. sum((SP,SC_CS), X(SP,SC_CS)*RDT_Cult_CS(SC_CS)*(8/100)*0.9)=l=QUOTA_SUCRE_MAX;       QUOTA_SUCRE_MAX=107000

Eq_BC_PROD_MIN..  sum((SP,SC_BC),  X*RDT_Cult_BC)       =g=QUOTA_BC_MIN=4056;
Eq_IG_PROD_MIN..  sum((SP,SC_IG),  X*RDT_Cult_IG)       =g=QUOTA_IG_MIN=5125;
Eq_MA_PROD_MIN..  sum((SP,SC_MA),  X*RDT_Cult_MA)       =g=QUOTA_MA_MIN=26404;
Eq_AN_PROD_MIN..  sum((SP,SC_AN),  X*RDT_Cult_AN/18*12) =g=QUOTA_AN_MIN=2322;
Eq_PLU_PROD_MIN.. sum((SP,SC_PLU), X*RDT_Cult_PLU)      =g=QUOTA_PLU_MIN=5879;
Eq_ME_PROD_MIN..  sum(SP, X(SP,"ME")*RDT_Cult_ME)       =g=QUOTA_ME_MIN=4135;
Eq_PN_PROD_MIN..  sum(SP, X(SP,"PN_PIQ"))               =g=QUOTA_PN_PIQ_MIN=6096;   (area, not production)

Eq_LEG_PROD_OBJ.. sum((SP,SC_MA), X*RDT_Cult_MA) =g= QUOTA_LEG=63059;    (NOT +SC_IG -- explicitly commented out in MODELE.txt:407)
Eq_FRU_PROD_OBJ.. sum(SC_BC,X*RDT_Cult_BC) + sum(SC_AN,X*RDT_Cult_AN/18*12) + sum(SC_PLU,X*RDT_Cult_PLU) + X(SP,"ME")*RDT_Cult_ME =g= QUOTA_FRU=30789;
Eq_PAT_SURF_OBJ.. sum(SP, X(SP,"PN_PIQ")) =g= QUOTA_PAT=12193;           (area; same expression as Eq_PN_PROD_MIN, different threshold)
Eq_TUB_PROD_OBJ.. sum((SP,SC_IG), X*RDT_Cult_IG) =g= QUOTA_TUB=0;        (disabled -- dead in GAMS reference)

Eq_BA_JA(SE,c in SC_BA_JA)..   sum(farm plots, X[.,"JA"]) =g= PROP_BA_JA * sum(farm plots, X[.,c]);
Eq_BA_ROTA(SE,c in SC_BA_JA).. sum(farm plots, X[.,"JA"] + sum(SC_CS,X) + sum(SC_CF,X)) =g= PROP_BA_JA * sum(farm plots, X[.,c]);
  PROP_BA_JA=0.2  (DONNEES.txt:11)
  SC_BA_JA = {BA_INT, BA_IRR, BA_SINT}

Eq_FRICHE(SP, c in SC_CULT_NON_NC)$(cult_2015 in {0,10,14} AND cult_2016 in {0,10,14} AND cult_2017 in {0,10,14})..
    X(SP,c) =l= 0;
```

Crop-family lists (verbatim from `SETS.txt`, verified directly):
- `SC_AN` = `{AN, AN_NU, AN_PA}`
- `SC_IG` = `{IG, IG_PLA, IG_TUT}`
- `SC_CS` = `{CS, CS_BT_NISM, CS_BT_NIM, CS_BT_IM, CS_SBT_NISM, CS_SBT_NIM, CS_SBT_IM, CS_NGT_NISM, CS_NGT_NIM, CS_NGT_IM, CS_CGT_NISM, CS_CGT_NIM, CS_CGT_IM, CS_EGT_NISM, CS_EGT_NIM, CS_EGT_IM, CS_MG_NISM, CS_MG_NIM, CS_MG_IM}` (19)
- `SC_BAN_EX` = `{BA, BA_INT, BA_IRR, BA_PER, BA_SINT}`
- `SC_BC` = `{BC, BC_BT, BC_GTMG}`
- `SC_MA` = `{MA, MA_PLBIO, MA_MOBIO, MA_ROTA, MA_TO_CHOU_JA, MA_TO_CO_JA, MA_BAG_BIO_I, MA_BAG_BIO_NI, MA_BAG_VEG_I, MA_BAG_VEG_NI, MA_BAG_FER_I, MA_BAG_FER_NI, MA_BAG_NON_I, MA_BAG_NON_NI, MA_BRF_BIO_I, MA_BRF_BIO_NI, MA_BRF_VEG_I, MA_BRF_VEG_NI, MA_BRF_FER_I, MA_BRF_FER_NI, MA_BRF_NON_I, MA_BRF_NON_NI, MA_PAI_BIO_I, MA_PAI_BIO_NI, MA_PAI_VEG_I, MA_PAI_VEG_NI, MA_PAI_FER_I, MA_PAI_FER_NI, MA_PAI_NON_I, MA_PAI_NON_NI}` (30)
- `SC_PLU` = `{AG, VE, VE_BTGT, VE_PLUIE}`
- `SC_CF` = `{CF_NBT_NISM, CF_NBT_NIM, CF_SBT_NISM, CF_SBT_NIM, CF_NGT_NISM, CF_NGT_NIM, CF_CGT_NISM, CF_CGT_NIM, CF_EGT_NISM, CF_EGT_NIM}` (10)
- `SC_BA_JA` = `{BA_INT, BA_IRR, BA_SINT}`

Note: `Y[p,c]` is binary and represents the *whole plot* (GAMS `X` is semicontinuous,
either 0 or the full `SURF_HA`), so every "area" term above is `Y[p,c] * plot_surface_ha[p]`
in Pyomo, matching the existing `maximize_gross_margin` objective's pattern.

### Testing

Same convention as existing code (`test_eligibility.py`, `test_model_builder.py`,
`test_guadeloupe_pipeline.py`): synthetic tiny-DataFrame/tiny-model unit tests per new
function, plus real-data regression assertions citing the GAMS equation name in a comment.

---

## Phase 2 — Markovitz risk objective, farm labor cap, farm banana quota

### The shared blocker

`Eq_REV_MARKOVITZ`, `Eq_MO_MAX_Expl`, and `Eq_BA_QUOTA_Expl` all need
`Matrice_Parc_Cult(P,C)` — which specific ITK crop-variant was on each plot in 2017. This
is derived in GAMS from the raw `cult_2017` code (1-20) plus plot attributes
(slope/island/farm-surface/irrigation/region/soil/commune) via ~150 lines of classification
logic (`ENTREES.txt` lines 62-103, 304-458) — not stored as data. The implementing agent
must read that logic directly from `ENTREES.txt` (not rely on paraphrase) since it's the
foundation every Phase 2 formula sits on.

`Eq_REV_MARKOVITZ` additionally needs `AVERS(E)`, a per-farm risk-aversion coefficient.
**`data/tables/Avers.txt` must not be used** — every one of its 5336 rows is `1`, a
placeholder, not the real GAMS-computed value. The real derivation (verified directly
against `OPTIMISATION.txt`):

1. Per-farm crop-family area shares from `Matrice_Parc_Cult` (`OPTIMISATION.txt`
   1467-1526): `PART_CAN`, `PART_BAN`, `PART_PAT`, `PART_MAR`, `PART_PLU` = that family's
   farm area ÷ `(SURF_CUL - SURF_NON)` (cultivated minus fallow/non-cultivated). The
   family definitions (`SURF_CAN` = `SC_CAN`, `SURF_BAN` = `SC_BAN_EX`, `SURF_PAT` =
   `SC_PAT`, `SURF_MAR` = `SC_MAR`, `SURF_PLU` = `SC_PLU`, `SURF_NON` = `SC_NON`,
   `SURF_CUL` = `SC_CULTIV`) must be read directly from `SETS.txt` during implementation —
   `SC_CAN`, `SC_PAT`, `SC_NON`, `SC_MAR`, `SC_CULTIV` were not fully transcribed during
   this design pass (unlike every Phase 1 set, which was verified) and must not be guessed.
2. An 8-category typology cascade (`OPTIMISATION.txt` 1530-1552). **GAMS defines two
   competing cascades; the second (lines 1542-1551) runs after the first and
   unconditionally overwrites every farm's `TYPE_EXPL` — it is the only one that matters,
   confirmed by direct read, not inference:**
   ```
   IF(PART_CAN>=0.939, TYPE_EXPL=3)
   ELIF(PART_CAN>=0.625, TYPE_EXPL=4)
   ELIF(PART_PAT>=0.606, TYPE_EXPL=6)
   ELIF(PART_PAT>=0.327, TYPE_EXPL=8)
   ELIF(PART_BAN>=0.364, TYPE_EXPL=2)
   ELIF(PART_MAR>=0.801, TYPE_EXPL=7)
   ELIF(PART_PLU>=0.522, TYPE_EXPL=1)
   ELSE TYPE_EXPL=5
   -- then unconditionally: IF(SURF_CUL=0, TYPE_EXPL=0)   [empty/fallow farms]
   ```
   (Written above as an if/elif chain for clarity; in GAMS these are independent
   sequential `IF`s over mutually-exclusive conditions — replicate the exact conditions,
   not the if/elif framing, to avoid subtly changing boundary behavior.)
3. `AVERS` lookup by `TYPE_EXPL` (`OPTIMISATION.txt` 1744-1754), all values verified
   directly:
   `1→1.30, 2→1.20, 3→0.30, 4→1.40, 5→0.55, 6→2.40, 7→0.00, 8→2.30`. `TYPE_EXPL=0`
   (empty farms) has no explicit assignment → `AVERS=0` (GAMS parameter default).
   Additionally, farms with `TYPE_EXPL=4` get refined into `41`/`42` by presence of
   diversification crops (maraîchage/arboriculture/plantain/tubers) and use `41→0.50,
   42→1.60` instead of the plain `4→1.40` (`OPTIMISATION.txt` 1557-1559, 1753-1754) — the
   `41`/`42` lookup takes priority since it runs after the base 1-8 lookup in the same
   `LOOP`.

### Formulas

```
Eq_REV_MARKOVITZ(SE).. sum(farm plots, sum(SC, X*MB_Ha_Cult(SC)))
                      - sum(farm plots, sum(SC, X*MB_Ha_Cult(SC)*Var_Rdt_Cult(SC,"init"))) * AVERS(SE)
                      =e= REV_MARKOVITZ(SE);
Eq_REV_MARKOVITZ_GWAD.. sum(SE,REV_MARKOVITZ(SE)) =e= REV_MARKOVITZ_GWAD;
```
Becomes the new `maximize_markovitz_revenue` objective (registered alongside, not
replacing, `maximize_gross_margin`); `config.yaml` flips the enabled objective to this one.
`MB_Ha_Cult` = existing `margin_per_ha_cult`. `Var_Rdt_Cult(.,"init")` =
`data/tables/indice_H/Var_Rdt_Cult.txt`'s `init` column (already available, just needs
wiring into `ModelInputs`).

```
Eq_MO_MAX_Expl(SE).. sum(farm plots, sum(SC,X*MO_Ha_Cult_init(SC))) =l= MO_Expl_init(SE);
```
`MO_Ha_Cult_init` from `Data_OTK.txt`'s `MO_EXPL` column + `matrice_otk_cult` +
`duree_plant_cult`/`duree_cycle_cult` (already loaded, not yet exposed in
`data_pipeline.py`'s returned parameters — trivial addition). `MO_Expl_init(SE)` needs
`Matrice_Parc_Cult` (the shared blocker) to know each plot's initial crop.

```
Eq_BA_QUOTA_Expl(SE).. sum(farm plots, X(.,"BA_INT")*Rdt_Cult_Init("BA_INT") + X(.,"BA_SINT")*Rdt_Cult_Init("BA_SINT")
                                       + X(.,"BA_PER")*Rdt_Cult_Init("BA_PER") + X(.,"BA_IRR")*Rdt_Cult_Init("BA_IRR"))
                       =l= REF_BAN_EXPL_init(SE);
```
`Rdt_Cult_Init` = `data/tables/indice_H/Rdt_Cult.txt`'s `init` column (available).
`REF_BAN_EXPL_init(SE)` needs `Matrice_Parc_Cult` (shared blocker) to know each plot's
2017 banana sub-variant.

### Testing

Same convention. Given the classification pipeline is the highest-risk piece in this whole
effort, it needs the most thorough real-data regression coverage: assert `TYPE_EXPL`/
`AVERS` for a handful of hand-picked real farms whose category is unambiguous from their
raw `Data_RPG_Gwad_2017.txt` history (e.g. an all-sugarcane farm should land `TYPE_EXPL=3`),
plus the full solve should still produce a feasible, bounded result on the real dataset.

---

## Error handling / edge cases (applies to both phases)

- Unknown `label` collisions (two config entries for the same generic constraint given
  the same `label`) → Pyomo itself raises on `setattr` of a duplicate component name; no
  extra validation needed, the failure is already clear.
- `farm_area_ratio_min`/`cs_gfa_minimum_share`: farms with zero plots or zero relevant
  crops are not skipped for `farm_area_ratio_min` (GAMS builds this constraint
  unconditionally per farm — a farm with no eligible pairs just yields a trivial `0 >= 0`),
  but *are* skipped for `cs_gfa_minimum_share` per its explicit GAMS `$` gate.
- `territory_production_bound` with `use_yield: true` for a crop absent from
  `crop_yield_per_ha` is a data error (should not happen for the crop families used here)
  and should raise (`KeyError`), not silently default to 0 or 1.

## Testing (repo-wide)

New test files follow existing naming: extend `tests/test_model_builder.py` for the three
generic `core/model/constraints.py` builders, add `tests/test_guadeloupe_constraints.py`
for `cs_gfa_minimum_share`, extend `tests/test_eligibility.py` for `friche_lock`, extend
`tests/test_guadeloupe_pipeline.py` for the new data-pipeline wiring (`farm_plots`,
`farm_gfa_surface_ha`, history columns). Phase 2 gets its own `tests/test_itk_classification.py`.
