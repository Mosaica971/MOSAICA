# Reference state -- Guadeloupe 2017

Observed initial state, rebuilt from the RPG history in `Data_Parc_Gwad_2017.txt`.
It is the situation every run is scored against (PAD, confusion matrix, plot
agreement rate). No solve: this folder depends on no run.

## 1. Universe covered

- Plots: 24 734
- Farms: 4 638
- Total area: 26 137 ha
- of which cultivated (PAD reference): 23 578 ha on 22 197 plots
- of which not cultivated (NC): 2 559 ha
- Economic year / scenario: 2017 / RESTIT
- Zone filter: none (whole territory)

**This is not Guadeloupe's UAA.** The universe is that of the plot dataset available
locally. Chopin et al. (2015) work on 5 336 farms, this dataset carries
4 638: the two do not describe the same perimeter
(see docs/04-vigilance.md). Any observed/simulated comparison must therefore stay
**internal** to this universe -- which is what the PAD does, comparing both sides on
the same plots.

## 2. Observed land use

Two readings coexist, and one must know which one is quoted:

- **raw**: `cult_2017` translated directly into an RPG group;
- **resolved**: the GAMS fallow-continuity rule (ENTREES.txt:49-57) forces NC when
  `cult_2016` AND `cult_2017` are both fallow. This is the reading the model, the
  typology and the PAD use.

Going from one to the other moves **1 208 ha** from fallow to not cultivated:
it is the only gap between the two readings.

| Group | Label | Raw (ha) | Resolved (ha) | PAD reference (ha) | Share of cultivated |
|---|---|---:|---:|---:|---:|
| AG | Citrus | 101 | 101 | 101 | 0.4 % |
| AN | Pineapple | 133 | 133 | 133 | 0.6 % |
| BA | Export banana | 1 921 | 1 921 | 1 921 | 8.1 % |
| BC | Plantain | 147 | 147 | 147 | 0.6 % |
| CS | Sugarcane | 12 813 | 12 813 | 12 813 | 54.3 % |
| IG | Yam and tubers | 145 | 145 | 145 | 0.6 % |
| JA | Fallow | 1 830 | 621 | 621 | 2.6 % |
| MA | Market gardening | 1 087 | 1 087 | 1 087 | 4.6 % |
| ME | Melon | 189 | 189 | 189 | 0.8 % |
| NC | Not cultivated | 1 351 | 2 559 | 0 | 0.0 % |
| PN | Grassland and savannah | 6 109 | 6 109 | 6 109 | 25.9 % |
| VE | Orchards excluding citrus | 311 | 311 | 311 | 1.3 % |
| **TOTAL** | | 26 137 | 26 137 | 23 578 | 100 % |

Breakdowns: `csv/reference_surface_by_region.csv`, `_by_island.csv`,
`_by_commune.csv`. Plot-by-plot reference: `csv/reference_allocation.csv`.

## 3. Observed farm typology

Row-marginal of every confusion matrix, and source of each farm's risk-aversion
coefficient (AVERS) in the Markowitz objective: part of the reference, not a result.

| Type | Label | Farms | Share | Area (ha) | AVERS |
|---|---|---:|---:|---:|---:|
| 0 | No cultivated area | 50 | 1.1 % | 161 | 0.00 |
| 1 | Fruit growers | 67 | 1.4 % | 263 | 1.30 |
| 2 | Banana growers | 146 | 3.1 % | 2 520 | 1.20 |
| 3 | Specialised cane growers | 1 371 | 29.6 % | 7 954 | 0.30 |
| 4 | Diversified cane growers | 862 | 18.6 % | 4 938 | 0.50-1.60 |
| 5 | Diversified | 282 | 6.1 % | 2 236 | 0.55 |
| 6 | Livestock farmers | 1 047 | 22.6 % | 4 555 | 2.40 |
| 7 | Market gardeners | 216 | 4.7 % | 861 | 0.00 |
| 8 | Cane and livestock farmers | 597 | 12.9 % | 2 649 | 2.30 |

## 4. What the reference cannot say

### 4.1 No fine crop is observed

The 12 RPG groups say "cane", never which technical system. Every economic or
environmental indicator of the reference therefore goes through the **fine ITK GAMS
assigns each plot** (`Matrice_Parc_Cult`, ENTREES.txt:299-457, ported in
`domain/baseline_itk.py`): banana by island, slope and farm size, cane by region, soil
and plot size, market gardening by irrigation... Deterministic and faithful to GAMS
(the farm labour budget `MO_Expl_init` is reproduced to 0.001 h), but an assumption of
the model, not an observation.

**The assignment rules and the eligibility equations are two separate parts of GAMS,
and nothing forces them to agree.** Where the assigned ITK is not eligible, the
reference is valued with a system the model could not choose back:

| Group | Assigned ITK | Observed (ha) | ITK eligible (ha) | Share | Labour (h/ha) | Margin (EUR/ha) |
|---|---|---:|---:|---:|---:|---:|
| AG | `AG` | 101 | 97 | 96 % | 492 | 4 949 |
| AN | `AN_NU` | 69 | 64 | 94 % | 438 | 4 303 |
| AN | `AN_PA` | 64 | 58 | 90 % | 436 | 9 097 |
| BA | `BA_INT` | 1 258 | 1 032 | 82 % | 1 558 | 10 340 |
| BA | `BA_IRR` | 169 | 169 | 100 % | 1 076 | 9 254 |
| BA | `BA_PER` | 289 | 289 | 100 % | 565 | 4 706 |
| BA | `BA_SINT` | 204 | 204 | 100 % | 958 | 5 695 |
| BC | `BC_BT` | 117 | 93 | 80 % | 609 | 4 587 |
| BC | `BC_GTMG` | 30 | 30 | 100 % | 621 | 4 544 |
| CS | `CS_BT_NIM` | 3 349 | 3 292 | 98 % | 13 | 2 762 |
| CS | `CS_BT_NISM` | 12 | 11 | 91 % | 13 | 1 679 |
| CS | `CS_CGT_NIM` | 774 | 770 | 100 % | 13 | 2 567 |
| CS | `CS_CGT_NISM` | 2 | 1 | 49 % | 13 | 1 584 |
| CS | `CS_EGT_NIM` | 1 965 | 1 958 | 100 % | 13 | 2 507 |
| CS | `CS_EGT_NISM` | 186 | 182 | 98 % | 13 | 1 570 |
| CS | `CS_MG_NISM` | 2 186 | 2 174 | 99 % | 13 | 1 617 |
| CS | `CS_NGT_NIM` | 3 366 | 3 350 | 100 % | 13 | 2 425 |
| CS | `CS_NGT_NISM` | 654 | 654 | 100 % | 13 | 1 521 |
| CS | `CS_SBT_NIM` | 319 | 272 | 85 % | 18 | 3 531 |
| IG | `IG_PLA` | 103 | 103 | 100 % | 672 | 11 396 |
| IG | `IG_TUT` | 42 | 34 | 82 % | 991 | 9 061 |
| JA | `JA` | 621 | 621 | 100 % | 6 | 116 |
| MA | `MA_ROTA` | 735 | 735 | 100 % | 1 653 | 27 929 |
| MA | `MA_TO_CO_JA` | 352 | 352 | 100 % | 1 128 | 24 425 |
| ME | `ME` | 189 | 189 | 100 % | 628 | 14 441 |
| PN | `PN_PIQ` | 6 109 | 6 109 | 100 % | 126 | 1 866 |
| VE | `VE_BTGT` | 262 | 193 | 73 % | 362 | 4 718 |
| VE | `VE_PLUIE` | 48 | 0 | 0 % | 362 | 4 718 |

**Consequence not to lose sight of**: this assignment does not stay in the
reporting. `farm_labor_hours_max` (Eq_MO_MAX_Expl) caps each farm at the labour of its
observed plan and `ba_quota_farm` (Eq_BA_QUOTA_Expl) at its banana tonnage, both
computed through these same ITKs: changing a rule changes the caps, hence the optimum.
See docs/04-vigilance.md C.2.

The reference indicators are therefore given with a bracket. The **central** estimate
is that of the GAMS ITKs -- exactly the figures a run reports on its "input" side, so
the two tell the same story. The **low** and **high** bounds replay each plot with the
least, then the most intensive variant **among those actually eligible there**.

Nothing then guarantees that the central estimate falls inside the bracket -- the
assigned ITK does not always belong to the set of eligible variants. Where it leaves
it from above, the reference is valued with a technical system the plot could not
carry: no indicator in this run.

| Indicator | Unit | Low | Central | High | Range |
|---|---|---:|---:|---:|---:|
| production_tonnes | t | 703 242 | 883 147 | 891 333 | 21 % |
| sales | EUR | 104 495 839 | 153 446 385 | 154 881 107 | 33 % |
| subsidy | EUR | 48 207 434 | 70 745 291 | 72 059 978 | 34 % |
| revenue | EUR | 152 703 273 | 224 191 676 | 226 941 084 | 33 % |
| gross_margin | EUR | 51 801 745 | 95 804 962 | 95 881 161 | 46 % |
| labor_hours | h | 3 785 551 | 5 592 326 | 6 195 233 | 43 % |
| nitrogen | kg N | 1 315 421 | 1 897 993 | 1 929 267 | 32 % |
| ghg | t CO2 (magnitude, see docs/04-vigilance.md) | 137 166 567 | 170 620 713 | 173 175 069 | 21 % |
| tfi | TFI.ha | 42 225 | 65 047 | 66 196 | 37 % |
| fte | FTE | - | 3 480 | - | - |
| labor_cost | EUR | - | 86 681 050 | - | - |
| net_revenue | EUR | - | 9 123 912 | - | - |
| chlordecone_risk_area | ha | - | 516 | - | - |
| water_need_m3 | m3 | - | 39 627 450 | - | - |
| soil_carbon_balance | t C | - | -10 774 | - | - |

The bracket falls back on the whole family for 361 plot(s) with no eligible variant at all.

### 4.2 Part of the observation cannot be reproduced by construction

A plot is reproducible only if at least one fine variant of its observed family is
eligible there. What is not is a gap no objective can avoid: a **floor under the
PAD**, a property of the data and of the eligibility mask, not of the run.

| Group | Observed (ha) | Reproducible (ha) | Irreproducible (ha) | Reproducible share |
|---|---:|---:|---:|---:|
| AG | 101 | 97 | 4 | 96 % |
| AN | 133 | 122 | 10 | 92 % |
| BA | 1 921 | 1 921 | 0 | 100 % |
| BC | 147 | 123 | 24 | 84 % |
| CS | 12 813 | 12 729 | 84 | 99 % |
| IG | 145 | 138 | 8 | 95 % |
| JA | 621 | 621 | 0 | 100 % |
| MA | 1 087 | 1 087 | 0 | 100 % |
| ME | 189 | 189 | 0 | 100 % |
| PN | 6 109 | 6 109 | 0 | 100 % |
| VE | 311 | 240 | 71 | 77 % |
| **TOTAL** | 23 578 | 23 377 | 201 | 99 % |

Induced PAD floor: **0.9 %** (201 ha out of 23 578 ha), and up to twice that if the excess these
displaced hectares create elsewhere is counted too. It is small:
**the observed/simulated gap is not explained by eligibility.**

Eligibility also embeds the GAMS suppressions (`Eq_*_SUPP`, and `Eq_VE_PLUIE`
forbidden everywhere by the GAMS bug ported faithfully): orchards and citrus are
therefore irreproducible for a porting reason, not an agronomic one.

## 5. Files

| File | Content |
|---|---|
| `csv/reference_land_use.csv` | Observed land use, raw and resolved readings |
| `csv/reference_allocation.csv` | Plot-by-plot reference (the pivot table) |
| `csv/reference_surface_by_region.csv` | Cultivated area by region x group |
| `csv/reference_surface_by_island.csv` | Same by island |
| `csv/reference_surface_by_commune.csv` | Same by commune |
| `csv/reference_farm_types.csv` | Observed typology and AVERS |
| `csv/reference_indicators.csv` | Indicators, central and bracket |
| `csv/reference_reproducibility.csv` | PAD floor by group |
| `csv/reference_itk_eligibility.csv` | Eligibility of the GAMS-assigned ITKs |
| `reference.json` | All of it, readable by a script |

Regenerate: `python scripts/build_reference_state.py`. Deterministic (no solve).
