# GAMS -> Python port inventory

Equation-by-equation state of the port of MOSAICA from `context/gams/`.
Reference: `MODELE.txt` (equations), `SETS.txt` (memberships), `ENTREES.txt` (data),
`OPTIMISATION.txt` (indicators).

Statuses: **ported** (active Python equivalent) / **disabled** (ported, `enable: false`, with its
reason in config.yaml) / **deferred** (identified, not done yet) / **discarded** (deliberately
not ported).

The status board (`docs/status/STATUS.md`) lists every config entry with the GAMS equation it
ports, read from its label or its config comment and checked against the sources; this page
keeps the reasoning behind each line.

Last updated: 2026-09-22 (English translation; the chlordecone rows were inverted, the
`Eq_*_SUPP` suppressions were described as implicit although they have been explicit rules
since 2026-07-21, and the CF price tables are now read).

## Eligibility — numeric bounds

| Equation | Role | Status | Python location |
|---|---|---|---|
| Bounds `ALTI_MIN/MAX` | Admissible altitude per crop | ported | `config.yaml eligibility_criteria` -> `core/data/eligibility.compute_eligibility_mask` |
| Bounds `PENTE_MIN/MAX` | Slope | ported | same |
| Bounds `PLUVIO_MIN/MAX` | Rainfall | ported | same |
| Bounds `SURF_MIN/MAX` | Plot size | ported | same |

## Eligibility — categorical rules

| Equation | Role | Status | Python location |
|---|---|---|---|
| `Eq_ME_IRR`, `Eq_MA_ROTA_IRR` | ME / MA_ROTA only on irrigated plots | ported | `irrigation_required` |
| `Eq_AN_SOL_Parc` | Pineapple allowed only on soil type 2 | ported | `attribute_forbidden` (`TYPE_SOL ne 2`). The former `soil_type_forbidden` entry was inverted and was replaced on 2026-07-23. |
| melon / soil / island | ME forbidden on soils 2-3-4 and in Basse-Terre | ported | two `attribute_forbidden` entries (an OR is written as two entries); the former `melon_soil_restriction` rule was removed on 2026-07-21 |
| `Eq_IG_CLD` | IG_TUT **forbidden** where `RISQUE_CLD` <= 3 (medium to very high chlordecone risk; 1 = very high) | ported | `attribute_forbidden`, label `ig_tut_chlordecone` |
| `Eq_PN_PIQ_CLD` | PN_PIQ **forbidden** where `RISQUE_CLD` = 1 | disabled | `attribute_forbidden`, label `pn_piq_cld` — absent from the GAMS CALIB block (commented in SCENARIO); enabled by policy P7 |
| melon / small regions | ME forbidden in a list of `REGION_CODE` | ported | `region_crop_forbidden` — see *open question* below |
| `Eq_FRICHE` | Plots fallow in 2015-2017 locked | ported | `fallow_lock` (label `fallow`) |
| `Eq_NOCULT_NC` | A plot observed as NC in 2017 stays NC | ported | two `attribute_forbidden` entries (`nocult_nc_1`, `nocult_nc_2`) |

## Eligibility — geographic ITK bans (ported 2026-07-20)

All through `attribute_forbidden` / `forbid_crops` (`core/data/eligibility.py`), parameterised in
`config.yaml categorical_rules`, each preceded by a comment naming its equation. They use
`plot_data["REGION"]` (integer 1-7, agronomic macro-region), `COMMUNE` (INSEE) and `ILE`
(1 = Basse-Terre, 2 = Grande-Terre, 3 = Marie-Galante) — **never** `REGION_CODE`.

| Equation | GAMS condition (plots where the ITK is forbidden) | Status |
|---|---|---|
| `Eq_CS_IRR` | `IRRIG_PARC ∈ {0,1}` -> every plot | ported (`forbid_crops` on `cs_irrig`, label `cs_irrig_ban`) |
| `Eq_CS_SOL_SQUE` | `SOL_COURT = 1` | ported |
| `Eq_CS_CONFORM` | `CONFORM > 1500` | ported |
| `Eq_CS_BT` | `ILE ≠ 1 AND REGION ≠ 5` | ported |
| `Eq_CS_SBT` | `REGION ≠ 5` | ported |
| `Eq_CS_NGT` | `COMMUNE ∉ {97102, 97119, 97122}` | ported |
| `Eq_CS_CGT` | `COMMUNE ∉ {97116, 97113, 97101}` | ported |
| `Eq_CS_EGT` | `COMMUNE ∉ {97117, 97128, 97125}` | ported |
| `Eq_CS_MG` | `ILE ≠ 3` | ported |
| `Eq_MA_TO_CHOU_JA_LOC` | `ILE ≠ 1 AND IRRIG_PARC = 0` | ported |
| `Eq_ME_MG` | `REGION = 7` | ported |
| `Eq_IG_PLA_ILE` | `ILE = 1` | ported |
| `Eq_IG_TUT_ILE` | `ILE ≠ 1` | ported |
| `Eq_BA_IRR` | `IRRIG_PARC = 0` | ported |
| `Eq_BA_IRR_BT` | `ILE = 1` | ported |
| `Eq_BC_BT` | `ILE ≠ 1` | ported |
| `Eq_BC_GTMG` | `ILE = 1` | ported |
| `Eq_BC_IRR_BT` | `PLUVIO_PARC < 2300 AND IRRIG_PARC = 0` | ported |
| `Eq_BC_IRR_GTMG` | `ILE ≠ 1 AND IRRIG_PARC = 0` | ported |
| `Eq_AG_IRR` | `IRRIG_PARC = 0 AND ALTITUDE < 400` | ported |
| `Eq_AG_BT` | `ILE > 1` | ported |
| `Eq_VE_IRR` | `PLUVIO_PARC < 2700 AND IRRIG_PARC = 0` | ported |
| `Eq_VE_BTGT` | see *GAMS bug* below | ported (actual behaviour) |
| `Eq_VE_PLUIE` | see *GAMS bug* below | ported (actual behaviour) |

### GAMS bug ported faithfully — `Eq_VE_BTGT` / `Eq_VE_PLUIE`

`MODELE.txt:305-307` queries `Data_RPG_Gwad` on columns `REGION` and `ILE` that **do not exist**
in that table: `Data_RPG_Gwad_2017.txt` only holds `ident` and `cult_2012..cult_2017`, and every
other use in `ENTREES.txt` only indexes it by `cult_20XX`. GAMS returns 0 for such an access,
without warning. Consequences:

- `Eq_VE_BTGT`: `Data_Parc.REGION = 4 OR Data_RPG.REGION = 5` -> the second term is always false
  -> the effective ban is **`REGION = 4` only**, not `{4, 5}`.
- `Eq_VE_PLUIE`: `Data_RPG.REGION = 6 OR Data_RPG.ILE ≠ 1` -> the first term is always false, the
  second is `0 ≠ 1` hence **always true** -> `VE_PLUIE` is in fact **forbidden on every plot**.

Decision of 2026-07-20: port the actual GAMS behaviour (parity mandate). The "presumed intent"
variants are written in `config.yaml` right next to it, as `enable: false` — flipping the pairs
is enough to test the other reading.

### Open question — `Eq_ME_MG` vs the `REGION_CODE` melon rule

`Eq_ME_MG` forbids ME in `REGION = 7` (macro-region). The pre-existing `region_crop_forbidden`
rule forbids ME in 18 `REGION_CODE`s (R0-R27, small regions). The two referentials are distinct
and both rules are restrictive, so their intersection is safe — but it is unknown whether the
second was meant to *replace* the first. To check with the data source (roadmap
`region-code-check`).

## Suppressions `Eq_*_SUPP` (ported 2026-07-21)

`Eq_AN_SUPP`, `Eq_BA_SUPP`, `Eq_BC_SUPP`, `Eq_CS_SUPP`, `Eq_IG_SUPP`, `Eq_MA_SUPP`, `Eq_PN_SUPP`,
`Eq_VE_SUPP` (the eight aggregate codes, which only encode the observed baseline), `Eq_CF_SUPP`,
`Eq_TH_SUPP`, `Eq_PN_TOUR_SUPP`, `Eq_MA_EXP_SUPP`, `Eq_CS_SBT_NISM_supp`, `Eq_CS_MG_NIM_supp`:
**ported** as explicit `forbid_crops` rules. They used to be treated as implicit on the grounds
that these codes carry no economics; that was wrong for `TH`, which the solver did pick on 528
plots. Removing them also drops ~350 000 decision variables.

## Rotations and per-farm quotas

| Equation | Role | Status | Python location |
|---|---|---|---|
| `Eq_AN_AGRO_MAX_Expl`, `Eq_IG_AGRO_MAX_Expl` | Maximum share of a family per farm | ported | `farm_area_share_max` (`an_agro_max_farm`, `ig_agro_max_farm`) |
| `Eq_BA_JA` | Fallow ≥ `PROP_BA_JA` x export banana | ported | `farm_area_ratio_min` (`ba_ja`) |
| `Eq_BA_ROTA` | Fallow + cane (+ CF) ≥ `PROP_BA_JA` x banana | ported | `farm_area_ratio_min` (`ba_rota`) |
| `Eq_CS_GFA` | Minimum cane share on GFA farms | disabled | `cs_gfa_minimum_share` — unsatisfiable together with the labour cap on 7 GFA farms (see `docs/04-vigilance.md` G.2) |
| `Eq_AN_PA` | `AN_PA` forbidden if `Surf_Expl_Parc_init < AN_SURF_EXPL_MIN` | ported | `attribute_forbidden` on `SURF_EXPL_PARC < 10` — the column carries the area of the farm owning the plot, so the rule needs no per-farm indexing (ported 2026-07-27) |
| `Eq_BA_QUOTA_Expl` | Export-banana tonnage of EACH farm ≤ its 2017 production | ported 2026-09-08 | `farm_production_bound` (`ba_quota_farm`); the per-farm reference comes from `compute_farm_baseline_production_t`, which prices each observed group through its representative variant for lack of the fine mix, which **loosens** the cap by about 18 % |

## Territory

| Equation | Role | Status | Python location |
|---|---|---|---|
| `Eq_*_PROD_MIN` | Production floors per chain | ported (disabled, SCENARIO block) | `territory_production_bound` (`sense: ge`) |
| `Eq_*_QUOTA_MAX` | Production ceilings | ported | `territory_production_bound` (`sense: le`) |
| `Eq_LEG/FRU_PROD_OBJ`, `Eq_PAT_SURF_OBJ` | Vegetable / fruit / grassland targets | ported (disabled) | `territory_production_bound` |
| `Eq_TUB_PROD_OBJ` | Tuber target | ported but **no-op** | `tub_prod_obj`, `enable: false`, threshold 0 — traceability placeholder |
| `Eq_MO_MAX_Expl` | Per-farm labour ceiling | **ported and active** | `farm_labor_hours_max` (`labor_max_farm`), `slack: 1.0`. `MO_Expl_init` assumes the fine 2017 allocation, which was never observed; the representative crops stand in for it (`baseline_representative_crops`), and the observed fine plan of the GAMS run is tested as an alternative (`scenarios_labor.yaml`). It is **the dominant constraint**: without it the optimum asks 21 593 FTE where the territory had 3 598 (factor 6). Changing a representative changes the ceiling, hence the optimum — `docs/04-vigilance.md` C.2. |

## Objectives

| Equation | Role | Status | Python location |
|---|---|---|---|
| Gross margin | Sum of margin/ha x area | ported, **disabled** | `maximize_gross_margin`. Without the risk term the model covers the island with market gardening: territorial PAD 193 %. |
| Risk-adjusted margin | Margin x (1 − `AVERS` x `Var_Rdt_Cult`) | ported, **active by default** | `maximize_risk_adjusted_gross_margin` — the objective of GAMS's actual solves (`Eq_REV_MARKOVITZ`). `AVERS` is computed in memory from the `TYPE_EXPL` cascade (8 coefficients, `OPTIMISATION.txt:1745-1754`), not read from the `Avers.txt` stub. `Var_Rdt_Cult` is a **fraction of margin loss**, neither a variance nor a coefficient of variation: the penalty is linear in area — `docs/04-vigilance.md` D.4. |

## Fibre-cane block (CF)

`Eq_CF_SOL_SQUE`, `Eq_CF_CONFORM`, `Eq_CF_BT`, `Eq_CF_SBT`, `Eq_CF_NGT`, `Eq_CF_CGT`,
`Eq_CF_EGT`, `Eq_CF_MG`, `Eq_CF_MIN`, `Eq_CF_T0..T8` -> **deferred as a block** (roadmap
`fibre-cane-block`). The `CF_*` crops are suppressed by `Eq_CF_SUPP` in both GAMS blocks, as
here. The geographic CF bans use `REGION` (BT<->{4,6}, SBT<->5, NGT<->3, CGT<->1, EGT<->2), a
different mapping from the sugarcane one, which goes through `COMMUNE` — to confirm when wiring.

Not to be confused with the files `indice_H/Prix_Cult_CF_<scenario>.txt` and
`Rdt_Cult_CF_<scenario>.txt`: despite their name they hold the prices and yields of **every**
crop, and since 2026-09-08 they are the tables the pipeline reads, because they are what GAMS
includes (`DONNEES.txt:283-289`).
