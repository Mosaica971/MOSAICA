# Creating the MOSAICA crops in MAELIA: what is known, what is missing

None of MOSAICA's crops appears in the MAELIA user guide ([README](README.md) M.2), so each
one has to be **created** in MAELIA: a species column in `especesCultivees.csv`, one ITK per
situation in `reglesDeDecisions*.csv`, and its economics. This page says, parameter by
parameter (§ 1, written by hand) and crop by crop (§ 2, generated from the data), what the
GAMS tables MOSAICA holds already give. It is the work list of step I.3 of the
[coupling to-do](coupling-todo.md).

Legend: **✓** known in MOSAICA's tables, to convert · **~** a proxy exists (a value shared by
the whole family, or a neighbouring quantity) · **✗** missing: needs the literature, experts
or a MAELIA referent · **—** not applicable (the ITK has no such operation).

---

## 1. Parameter by parameter

### Species — `especesCultivees.csv` (one column per species; AqYield / AqYieldNC)

| MAELIA parameter | what it is | MOSAICA source | status |
|---|---|---|---|
| `RENDEMENT_MOYEN` | mean yield, t/ha | `Rdt_Cult_CF_<scenario>` | ✓ — but 1-4x the territory's ([vigilance C.1](../04-vigilance.md)) |
| `RENDEMENT_OPTIMAL` | **potential** yield, which the crop model scales down by water and N stress | none: `Rdt_Cult` is an achieved mean | ~ — the decision of M.1 |
| `RENDEMENT_MIN` | optional | `Var_Rdt_Cult` is a variance, not a minimum | ~ |
| `Tbase`, `Tmax`, `DEGRES_J_LevTbase`, `DEGRES_J_Flor`, `DEGRES_J_matPhyTbase`, `FREIN` | phenology in degree-days | only `Duree_Cycle_Cult` (months: 12 for every crop but pineapple, 18) | ✗ |
| `KMAX` | maximum crop coefficient | `Data_Cult` `KCROP` | ~ one value per family |
| `CRACINE` | root growth rate | `Data_Cult` `LONG_RAC` is a rooting depth (cm), not a rate | ~ |
| `CVIG`, `CSTO`, `coeff_Fonction_Prod` | vigour, stomatal closure, shape of Yield/YieldMax = f(ETR/ETM) | none | ✗ (FAO-33/56 yield-response factors are a candidate for the last) |
| `ZonesClimatiques` | where the species can grow | eligibility bounds `ALTI_*`, `PLUVIO_*` of `Data_Cult` | ~ — Guadeloupe's climate zones must be defined first |
| `BESOIN_N`, `DEBUT_BESOIN_N`, `FREIN_BESOIN_N`, `PRE_FLO_BESOIN_N`, `PRE_MAT_BESOIN_N`, `adil`, `bdil`, `Type_Nacq`, `N_grain` | nitrogen demand and dilution curve (NC only) | none — the fertiliser N per crop is a supply, not a demand | ✗ |
| `C_aer`, `C_rac`, `HI`, `SR_ratio`, `CN_ratio`, `Tms`, `Pse`, `beta` | carbon allocation, harvest index, dry matter (NC only) | `Data_Cult` `BIOM_AER`, `RAC`, `CARB`, `HRES` (the soil-carbon inputs) | ~ mostly one value per family |
| `isLEG`, `isCouvert`, `ABSCISSION`, `especeRepousse` | flags | agronomy: none of the crop codes is a legume | ✓ by hand; *to confirm* whether `especeRepousse` (regrowth) is a hook for cane ratoons |
| grassland: `especesHerbSim.csv` | HerbSim species | none; the guide's table did not render | ✗ — and AqYieldNC cannot simulate grassland |

### ITK — `reglesDeDecisions.csv` and `reglesDeDecisions_fertilisation.csv` (one column per situation)

| MAELIA parameter | what it is | MOSAICA source | status |
|---|---|---|---|
| `ID_ESPECE` | the species | the fine crop code; **one species per variant** (M.4) | ✓ |
| `ID_PREC` | preceding crop | none: MOSAICA is one year; the RPG gives `cult_2015`, `cult_2016` | ~ — `*` to start |
| `ZONE_PEDO`, `TYPE_EXPL`, climate zone | situation criteria | MOSAICA's ITKs do not vary with them; the region is in the code (`CS_NGT_…`) | `*`, or one criterion value per regional variant |
| `MATERIEL` | irrigation equipment | the irrigated variants (`_I`, `_IM`, `BA_IRR`) and the plot flag `IRRIG_PARC` | ~ — the equipment type is unknown |
| `IS_<OT>` | which operations exist | `Matrice_OTK_Cult_<scenario>`, 189 operations, mapped onto MAELIA's 7 types | ✓ for the typed ones — column *Ops typed* |
| sub-periods (1-3 Julian-day windows per operation) | when | none | ✗ |
| trigger thresholds | soil moisture, rain, temperature, vegetation stage | none | ✗ |
| depth (cm) | tillage, sowing… | `Data_Cult` `PROF_SILLONS` (furrow depth) only | ~ |
| work time (h/ha) | per operation | `Data_OTK` `MO_EXPL` × `DOSE` | ✓ |
| fertilisation: product, dose, strategies | kg element/ha (mineral), t/ha (organic) | fertiliser rows of the matrix; N from `AZOTE`, P and K from the grade in the name | ✓ doses — ✗ timing and alternative strategies |
| `engrais.csv` | fertiliser composition, organic decomposition (K1, C2, kres…), NH₃ factors, cost | N content and unit price of each product | ~ mineral — ✗ organic (`FUMIER`, `ORGANOR`, `FERTI_MA_*BIO`, compost) |
| crop protection: product, dose (L/ha) | | pesticide rows (TFI and PPDB columns of `Data_OTK`) | ✓ |
| irrigation: window, dose (mm), return delay | | `BESOIN_EAU_01..12`, a gross need flat over the year ([vigilance C.4](../04-vigilance.md)), and the irrigation operations of the matrix | ~ |

### Economics — `marcheAgricole/`

| MAELIA file | what it is | MOSAICA source | status |
|---|---|---|---|
| `prixVentes.csv` | sale price per species and year | `Prix_Cult_CF_<scenario>` (€/t; years 2017-2022 are copies of 2017) | ✓ — mind the unit ([errata](reference.md#errata--what-the-guide-gets-wrong-or-leaves-out)) |
| `primes.csv` | coupled subsidies, €/ha per département | POSEI area and volume aids, industry, replanting, transport, AECM (`crop_subsidy_per_ha`) | ✓ once the per-tonne aids are turned into €/ha |
| `chargesOp.csv` | operational costs per ITK, €/ha | variable cost: matrix × `PRIX_UNIT`, plus harvest and transport costs | ✓ |
| `chargesDePassage.csv` | machinery costs per ITK, €/ha | `AMORTI` only flags amortised operations; no machinery cost | ✗ |

### What the crop table shows that the parameter list does not

- **Operations with no MAELIA slot.** MAELIA knows 7 operation types (tillage, sowing, hoeing,
  fertilisation, crop protection, irrigation, harvest). Staking, de-suckering, de-leafing,
  bagging, pruning, plastic mulching, packing and livestock care have none. Column *Untyped h*
  is the share of each crop's labour hours they carry, and it is large exactly where labour is
  the question: banana (de-leafing and packing), tomato and market gardening (staking,
  pruning), grassland (livestock care). **Those hours vanish in MAELIA**, which biases the
  labour comparison of the robustness test (to-do E.4) downwards unless they are folded into
  a typed operation or added back outside MAELIA.
- **Irrigated cane has irrigation operations but no water need** (`BESOIN_EAU_*` = 0 for the
  whole cane family, and for tomato, pineapple, grassland): MOSAICA's water indicator ignores
  them (vigilance C.4), and a cane irrigation ITK has nothing to start from.
- **Crop-level values.** `KCROP`, `LONG_RAC`, `CARB`, `RAC` are the same for every variant of
  a crop — all sugarcane variants, all banana variants, the 24 Karusmart variants (only
  `BIOM_AER` varies, within cane and banana): the variants are one plant under
  different management, so a MAELIA species per variant (M.4) copies one set of growth
  parameters and differs in its ITK and its yield.
- **Lifespan.** A plantation of more than one year (cane, banana, citrus, orchards) or a
  cycle of more than 12 months (pineapple) has no documented mechanism in MAELIA (M.2).

Candidate sources for what is missing, to discuss at the training: FAO-56 (crop coefficients,
rooting depth, stage lengths), FAO-33 (yield response to water), CIRAD and INRAE Antilles-Guyane
technical references, and the Chambre d'agriculture's technical sheets for dates and practices.

---

## 2. Crop by crop

Regenerate with `.venv/Scripts/python scripts/build_maelia_crop_table.py` (~7 s, needs
`data/`) after a change of the tables; how each cell is decided is in
`case_studies/guadeloupe/reporting/maelia_crops.py`. *Ops typed* is "operations mapped onto a
MAELIA type / operations in the ITK".

<!-- BEGIN GENERATED: scripts/build_maelia_crop_table.py -->

*Generated on 2026-09-23 from the tables of year 2017, scenario RESTIT; 75 crops. Left out, no operation at all: `AN`, `BA`, `BC`, `CS`, `IG`, `MA`, `NC`, `PN`, `VE`.*

### How many crops each block is covered for

| block | ✓ | ~ | ✗ | other |
|---|---|---|---|---|
| Yield | 74 | 0 | 0 | 1 |
| Phenology | 0 | 0 | 74 | 1 |
| Kc, roots | 0 | 74 | 0 | 1 |
| Biomass, C | 0 | 74 | 0 | 1 |
| N need | 0 | 0 | 74 | 1 |
| Ops typed | 2 | 72 | 1 | 0 |
| Dates, triggers | 0 | 0 | 74 | 1 |
| Fertilisation | 73 | 0 | 0 | 2 |
| Protection | 71 | 0 | 0 | 4 |
| Irrigation | 8 | 39 | 0 | 28 |
| Price | 64 | 0 | 0 | 11 |
| Subsidies | 24 | 0 | 0 | 51 |
| Op. costs | 75 | 0 | 0 | 0 |
| Lifespan | 0 | 0 | 39 | 36 |

### Citrus (1)

| code | crop | Yield | Phenology | Kc, roots | Biomass, C | N need | Ops typed | Untyped h | Dates, triggers | Fertilisation | Protection | Irrigation | Price | Subsidies | Op. costs | Lifespan | MAELIA model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `AG` | Citrus | ✓ | ✗ | ~ | ~ | ✗ | ~ 17/19 | 5% | ✗ | ✓ | ✓ | ✓ ops + need | ✓ | none | ✓ | ✗ 15-yr plantation | AqYield(NC) |

### Pineapple (2)

| code | crop | Yield | Phenology | Kc, roots | Biomass, C | N need | Ops typed | Untyped h | Dates, triggers | Fertilisation | Protection | Irrigation | Price | Subsidies | Op. costs | Lifespan | MAELIA model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `AN_NU` | Pineapple: system without plastic mulch | ✓ | ✗ | ~ | ~ | ✗ | ✓ 12/12 | 0% | ✗ | ✓ | ✓ | — | ✓ | none | ✓ | ✗ 18-month cycle | AqYield(NC) |
| `AN_PA` | Pineapple: system with plastic mulch | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/18 | 0% | ✗ | ✓ | ✓ | — | ✓ | none | ✓ | ✗ 18-month cycle | AqYield(NC) |

### Dessert banana (4)

| code | crop | Yield | Phenology | Kc, roots | Biomass, C | N need | Ops typed | Untyped h | Dates, triggers | Fertilisation | Protection | Irrigation | Price | Subsidies | Op. costs | Lifespan | MAELIA model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `BA_INT` | Banana: intensive lowland system | ✓ | ✗ | ~ | ~ | ✗ | ~ 13/21 | 82% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | ✓ | ✓ | ✗ 8-yr plantation | AqYield(NC) |
| `BA_IRR` | Banana: irrigated system | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/23 | 85% | ✗ | ✓ | ✓ | ✓ ops + need | ✓ | ✓ | ✓ | ✗ 11-yr plantation | AqYield(NC) |
| `BA_PER` | Banana: extensive upland system | ✓ | ✗ | ~ | ~ | ✗ | ~ 11/18 | 84% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | ✓ | ✓ | ✗ 15-yr plantation | AqYield(NC) |
| `BA_SINT` | Banana: intensive upland system | ✓ | ✗ | ~ | ~ | ✗ | ~ 13/21 | 83% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | ✓ | ✓ | ✗ 11-yr plantation | AqYield(NC) |

### Plantain (2)

| code | crop | Yield | Phenology | Kc, roots | Biomass, C | N need | Ops typed | Untyped h | Dates, triggers | Fertilisation | Protection | Irrigation | Price | Subsidies | Op. costs | Lifespan | MAELIA model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `BC_BT` | Plantain, Basse-Terre | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/20 | 34% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | ✗ 2-yr plantation | AqYield(NC) |
| `BC_GTMG` | Plantain, Grande-Terre & Marie-Galante | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/21 | 33% | ✗ | ✓ | ✓ | ✓ ops + need | ✓ | none | ✓ | ✗ 2-yr plantation | AqYield(NC) |

### Sugarcane and fibre cane (28)

| code | crop | Yield | Phenology | Kc, roots | Biomass, C | N need | Ops typed | Untyped h | Dates, triggers | Fertilisation | Protection | Irrigation | Price | Subsidies | Op. costs | Lifespan | MAELIA model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `CF_NBT_NISM` | Fibre cane: North Basse-Terre, rain-fed, semi-mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 14% | ✗ | ✓ | ✓ | — | 0 | none | ✓ | ✗ 6-yr plantation | AqYield(NC) |
| `CF_NBT_NIM` | Fibre cane: North Basse-Terre, rain-fed, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 14% | ✗ | ✓ | ✓ | — | 0 | none | ✓ | ✗ 6-yr plantation | AqYield(NC) |
| `CF_SBT_NISM` | Fibre cane: South Basse-Terre, rain-fed, semi-mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 14% | ✗ | ✓ | ✓ | — | 0 | none | ✓ | ✗ 6-yr plantation | AqYield(NC) |
| `CF_SBT_NIM` | Fibre cane: South Basse-Terre, rain-fed, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 14% | ✗ | ✓ | ✓ | — | 0 | none | ✓ | ✗ 6-yr plantation | AqYield(NC) |
| `CF_NGT_NISM` | Fibre cane: North Grande-Terre, rain-fed, semi-mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/16 | 14% | ✗ | ✓ | ✓ | — | 0 | none | ✓ | ✗ 6-yr plantation | AqYield(NC) |
| `CF_NGT_NIM` | Fibre cane: North Grande-Terre, rain-fed, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/16 | 14% | ✗ | ✓ | ✓ | — | 0 | none | ✓ | ✗ 6-yr plantation | AqYield(NC) |
| `CF_CGT_NISM` | Fibre cane: Central Grande-Terre, rain-fed, semi-mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 14% | ✗ | ✓ | ✓ | — | 0 | none | ✓ | ✗ 6-yr plantation | AqYield(NC) |
| `CF_CGT_NIM` | Fibre cane: Central Grande-Terre, rain-fed, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 14% | ✗ | ✓ | ✓ | — | 0 | none | ✓ | ✗ 6-yr plantation | AqYield(NC) |
| `CF_EGT_NISM` | Fibre cane: East Grande-Terre, rain-fed, semi-mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/16 | 14% | ✗ | ✓ | ✓ | — | 0 | none | ✓ | ✗ 6-yr plantation | AqYield(NC) |
| `CF_EGT_NIM` | Fibre cane: East Grande-Terre, rain-fed, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/16 | 14% | ✗ | ✓ | ✓ | — | 0 | none | ✓ | ✗ 6-yr plantation | AqYield(NC) |
| `CS_BT_NISM` | Sugarcane: Basse-Terre, rain-fed, semi-mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 12% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_BT_NIM` | Sugarcane: Basse-Terre, rain-fed, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 12% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_BT_IM` | Sugarcane: Basse-Terre, irrigated, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/16 | 22% | ✗ | ✓ | ✓ | ~ ops, no need | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_SBT_NISM` | Sugarcane: South-East Basse-Terre, rain-fed, semi-mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 21% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 3-yr plantation | AqYield(NC) |
| `CS_SBT_NIM` | Sugarcane: South-East Basse-Terre, rain-fed, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 21% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 3-yr plantation | AqYield(NC) |
| `CS_SBT_IM` | Sugarcane: South-East Basse-Terre, irrigated, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 16/17 | 14% | ✗ | ✓ | ✓ | ~ ops, no need | ✓ | ✓ | ✓ | ✗ 3-yr plantation | AqYield(NC) |
| `CS_NGT_NISM` | Sugarcane: North Grande-Terre, rain-fed, semi-mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 12% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_NGT_NIM` | Sugarcane: North Grande-Terre, rain-fed, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 12% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_NGT_IM` | Sugarcane: North Grande-Terre, irrigated, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 16/17 | 10% | ✗ | ✓ | ✓ | ~ ops, no need | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_CGT_NISM` | Sugarcane: Central Grande-Terre, rain-fed, semi-mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 12% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_CGT_NIM` | Sugarcane: Central Grande-Terre, rain-fed, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 12% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_CGT_IM` | Sugarcane: Central Grande-Terre, irrigated, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 16/17 | 10% | ✗ | ✓ | ✓ | ~ ops, no need | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_EGT_NISM` | Sugarcane: East Grande-Terre, rain-fed, semi-mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 12% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_EGT_NIM` | Sugarcane: East Grande-Terre, rain-fed, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 12% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_EGT_IM` | Sugarcane: East Grande-Terre, irrigated, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 16/17 | 10% | ✗ | ✓ | ✓ | ~ ops, no need | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_MG_NISM` | Sugarcane: Marie-Galante, rain-fed, semi-mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 12% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_MG_NIM` | Sugarcane: Marie-Galante, rain-fed, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/15 | 12% | ✗ | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |
| `CS_MG_IM` | Sugarcane: Marie-Galante, irrigated, mechanised harvest | ✓ | ✗ | ~ | ~ | ✗ | ~ 16/17 | 10% | ✗ | ✓ | ✓ | ~ ops, no need | ✓ | ✓ | ✓ | ✗ 7-yr plantation | AqYield(NC) |

### Yam (2)

| code | crop | Yield | Phenology | Kc, roots | Biomass, C | N need | Ops typed | Untyped h | Dates, triggers | Fertilisation | Protection | Irrigation | Price | Subsidies | Op. costs | Lifespan | MAELIA model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `IG_PLA` | Yam, flat-grown | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/17 | 7% | ✗ | ✓ | ✓ | ✓ ops + need | ✓ | none | ✓ | annual | AqYield(NC) |
| `IG_TUT` | Yam, staked | ✓ | ✗ | ~ | ~ | ✗ | ~ 14/18 | 27% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |

### Fallow (1)

| code | crop | Yield | Phenology | Kc, roots | Biomass, C | N need | Ops typed | Untyped h | Dates, triggers | Fertilisation | Protection | Irrigation | Price | Subsidies | Op. costs | Lifespan | MAELIA model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `JA` | Fallow | — | — | — | — | — | ✓ 1/1 | 0% | — | — | — | — | 0 | ✓ | ✓ | annual | gel (no ITK) |

### Market gardening (incl. tomato) (30)

| code | crop | Yield | Phenology | Kc, roots | Biomass, C | N need | Ops typed | Untyped h | Dates, triggers | Fertilisation | Protection | Irrigation | Price | Subsidies | Op. costs | Lifespan | MAELIA model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `MA_TO_CHOU_JA` | Open-field market gardening (tomato/cabbage/fallow rotation) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_PLBIO` | Organic multi-species market gardening | ✓ | ✗ | ~ | ~ | ✗ | ~ 16/26 | 40% | ✗ | ✓ | — | ✓ ops + need | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_MOBIO` | Organic single-species market gardening | ✓ | ✗ | ~ | ~ | ✗ | ~ 11/18 | 47% | ✗ | ✓ | — | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_ROTA` | Market gardening in rotation | ✓ | ✗ | ~ | ~ | ✗ | ~ 32/39 | 29% | ✗ | ✓ | ✓ | ✓ ops + need | ✓ | none | ✓ | annual | AqYield(NC) |
| `TH` | Tomato | ✓ | ✗ | ~ | ~ | ✗ | ~ 20/27 | 52% | ✗ | ✓ | ✓ | — | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_TO_CO_JA` | Open-field market gardening (TO/CO/JA rotation) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BAG_BIO_I` | Open-field market gardening (bagasse, BIO, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BAG_BIO_NI` | Open-field market gardening (bagasse, BIO, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BAG_VEG_I` | Open-field market gardening (bagasse, VEG, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BAG_VEG_NI` | Open-field market gardening (bagasse, VEG, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BAG_FER_I` | Open-field market gardening (bagasse, FER, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BAG_FER_NI` | Open-field market gardening (bagasse, FER, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BAG_NON_I` | Open-field market gardening (bagasse, NON, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BAG_NON_NI` | Open-field market gardening (bagasse, NON, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BRF_BIO_I` | Open-field market gardening (ramial wood chips, BIO, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BRF_BIO_NI` | Open-field market gardening (ramial wood chips, BIO, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BRF_VEG_I` | Open-field market gardening (ramial wood chips, VEG, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BRF_VEG_NI` | Open-field market gardening (ramial wood chips, VEG, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BRF_FER_I` | Open-field market gardening (ramial wood chips, FER, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BRF_FER_NI` | Open-field market gardening (ramial wood chips, FER, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BRF_NON_I` | Open-field market gardening (ramial wood chips, NON, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_BRF_NON_NI` | Open-field market gardening (ramial wood chips, NON, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_PAI_BIO_I` | Open-field market gardening (straw, BIO, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_PAI_BIO_NI` | Open-field market gardening (straw, BIO, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_PAI_VEG_I` | Open-field market gardening (straw, VEG, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_PAI_VEG_NI` | Open-field market gardening (straw, VEG, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_PAI_FER_I` | Open-field market gardening (straw, FER, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_PAI_FER_NI` | Open-field market gardening (straw, FER, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_PAI_NON_I` | Open-field market gardening (straw, NON, irrigated) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |
| `MA_PAI_NON_NI` | Open-field market gardening (straw, NON, rain-fed) | ✓ | ✗ | ~ | ~ | ✗ | ~ 15/22 | 49% | ✗ | ✓ | ✓ | ~ need, no op | ✓ | none | ✓ | annual | AqYield(NC) |

### Melon (1)

| code | crop | Yield | Phenology | Kc, roots | Biomass, C | N need | Ops typed | Untyped h | Dates, triggers | Fertilisation | Protection | Irrigation | Price | Subsidies | Op. costs | Lifespan | MAELIA model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `ME` | Melon | ✓ | ✗ | ~ | ~ | ✗ | ~ 20/24 | 21% | ✗ | ✓ | ✓ | ✓ ops + need | ✓ | none | ✓ | annual | AqYield(NC) |

### Grassland (2)

| code | crop | Yield | Phenology | Kc, roots | Biomass, C | N need | Ops typed | Untyped h | Dates, triggers | Fertilisation | Protection | Irrigation | Price | Subsidies | Op. costs | Lifespan | MAELIA model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `PN_PIQ` | Natural grassland with tethered livestock | ✓ | ✗ | ~ | ~ | ✗ | ✗ 0/7 | 100% | ✗ | — | — | — | ✓ | ✓ | ✓ | annual | HerbSim (not NC) |
| `PN_TOUR` | Natural grassland with rotational grazing | ✓ | ✗ | ~ | ~ | ✗ | ~ 2/8 | 88% | ✗ | ✓ | ✓ | — | ✓ | none | ✓ | annual | HerbSim (not NC) |

### Orchards (2)

| code | crop | Yield | Phenology | Kc, roots | Biomass, C | N need | Ops typed | Untyped h | Dates, triggers | Fertilisation | Protection | Irrigation | Price | Subsidies | Op. costs | Lifespan | MAELIA model |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `VE_BTGT` | Orchards: Basse-Terre & Grande-Terre | ✓ | ✗ | ~ | ~ | ✗ | ~ 17/19 | 7% | ✗ | ✓ | ✓ | ✓ ops + need | ✓ | none | ✓ | ✗ 15-yr plantation | AqYield(NC) |
| `VE_PLUIE` | Orchards: very rainy areas | ✓ | ✗ | ~ | ~ | ✗ | ~ 17/19 | 7% | ✗ | ✓ | ✓ | ~ ops, no need | ✓ | none | ✓ | ✗ 15-yr plantation | AqYield(NC) |


<!-- END GENERATED -->
