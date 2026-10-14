# Baseline ITK by the GAMS rules (`Matrice_Parc_Cult`) — 2026-09-28

## Question

The FTE of the observed 2017 plan, as Python reported them (`fte_by_farm_input.csv`, the input
side of every run), were 11 % above the `MO_Expl_init` GAMS displays for the same farms. Where
does the gap come from?

## Why an ITK must be chosen at all

The observation is the RPG: `Data_RPG_Gwad_2017.txt` carries `cult_2012..cult_2017`, 20 codes
folded onto 12 groups. It never says which technical system a plot ran. Labour, yield, cost and
nitrogen belong to the fine ITK; the aggregate codes (AN, BA, BC, CS, IG, MA, PN, VE) have
empty columns in `Matrice_OTK_Cult` and therefore a 0 rate. Pricing the observed side requires
assigning an ITK to each plot — there is nothing to "read directly".

`context/SORTIES/ASSOL_PARC_INIT.TXT` looked like an observed fine plan. It is not: it is
`STOCK_ASSOL_Parc("init",SP,SC)` (RESULTATS.txt:160), the `X.l` of the `init` iteration, where
`Eq_SURF_INIT_Parc` (MODELE.txt:214) fixes `X = Matrice_Parc_Cult × SURF_HA`. It is the output
of the rules below, and the file is no longer on disk.

## The two methods

- **Python until 2026-09-28**: one representative ITK per group (`baseline_representative_crops`:
  BA→BA_INT, MA→MA_ROTA, CS→CS_NGT_NISM, IG→IG_PLA…), identical on every plot.
- **GAMS**: rules on the plot's attributes (ENTREES.txt:299-457) — banana by island, slope
  (> 25 %) and farm size (≥ 10 ha); cane by region, `SOL_COURT` and plot size (< 0.2 ha);
  market gardening by irrigation on Basse-Terre; plantain, yam by island; pineapple by farm size
  (`AN_SURF_EXPL_MIN`); orchards by region; grassland always PN_PIQ.

## Measurement

Porting the rules and applying `MO_Ha_Cult_init` reproduces the pasted GAMS `DISPLAY
MO_Expl_init` **to 0.001 h on all 4 588 farms** (5 592 326 h). The representative method gave
6 252 740 h. Gap −660 414 h = −411 FTE (−10.6 %), by group:

| Group | Representative | GAMS mix | Δ h | Δ FTE |
|---|---|---|---:|---:|
| BA | BA_INT 1 558 h/ha on 1 921 ha | BA_INT 1 258 ha, BA_PER 289 (565 h/ha), BA_SINT 204 (958), BA_IRR 169 (1 076) | −491 050 | −306 |
| MA | MA_ROTA 1 653 on 1 087 ha | MA_ROTA 735 ha, MA_TO_CO_JA 352 (1 128) | −184 627 | −115 |
| IG | IG_PLA 672 | IG_TUT 42 ha on Basse-Terre (991) | +13 449 | +8 |
| CS, BC, AN | | CS_SBT_NIM, BC_GTMG, AN_PA | +1 813 | +1 |
| AG, JA, ME, NC, PN, VE | no variant or equal rate | | 0 | 0 |

Cane looks arbitrary (CS_NGT_NISM) but costs nothing here: every cane ITK is at ~12.7 h/ha.
405 farms lose budget, 119 gain, 50 all-NC farms are at zero on both sides; the top 100 farms
carry 71 % of the gap. The banana reference `REF_BAN_EXPL_init` moves from 86 436 t to 73 097 t.

## Decision

The GAMS rules become the only method (`domain/baseline_itk.py`, parameter
`baseline_fine_crop`). They feed `compute_farm_labor_capacity_hours` (Eq_MO_MAX_Expl),
`compute_farm_baseline_production_t` (Eq_BA_QUOTA_Expl), the run's input side
(`indicators.decode_baseline_fine_allocation`), the reference state and the golden snapshot.
Removed: `baseline_representative_crops`, `data.fine_baseline_allocation`, the
`ASSOL_PARC_INIT.TXT` reader, `scenarios_labor.yaml`, `scenarios_calibration_fine_labor.yaml`.

It remains an assumption of the GAMS model, not an observation; its merit is to depend on the
plot and to give parity. The rules and the eligibility equations do not always agree
(VE_PLUIE is assigned but forbidden everywhere; see `reference_itk_eligibility.csv`).

## Consequences

- The labour cap tightens by 10.6 % and the banana cap by 15 %. The selected calibration used
  5 629 390 h, above the new 5 592 326 h: every reference run and every scenario threshold
  measured against the old cap must be re-measured (roadmap `regenerate-reference-runs`;
  `check_references.py` still guards the old runs, which do not move).
- A warm start from a run solved before 2026-09-28 will generally violate the new per-farm
  caps; the audit reports it, and `scripts/repair_allocation.py` is the way to seed from one.
- Input-side indicators of new runs differ from old runs at constant allocation (e.g. input
  FTE 3 891 → 3 480, gross margin 88.8 → 95.8 M€); the dashboard captions say which basis a
  run used by its date.
</content>
</invoke>
