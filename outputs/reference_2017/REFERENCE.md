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

The 12 RPG groups say "cane", never which technical system. GAMS had the same limit
(`Matrice_Parc_Cult`). Every economic or environmental indicator of the reference
therefore goes through a **representative crop** per family
(`config.yaml: baseline_representative_crops`) -- an assumption, not an observation.

**The representative is often a crop the model itself would forbid on the plot it
stands for.** `CS_NGT_NISM` is the North Grande-Terre cane system, confined to three
communes, yet it values every cane hectare of the territory; `MA_ROTA` requires
irrigation and values all of market gardening.

| Group | Representative | Observed (ha) | Representative eligible (ha) | Share | Margin (EUR/ha) |
|---|---|---:|---:|---:|---:|
| AG | `AG` | 101 | 48 | 48 % | 4 949 |
| AN | `AN_NU` | 133 | 122 | 92 % | 4 303 |
| BA | `BA_INT` | 1 921 | 1 319 | 69 % | 10 340 |
| BC | `BC_BT` | 147 | 93 | 63 % | 4 587 |
| CS | `CS_NGT_NISM` | 12 813 | 4 020 | 31 % | 1 521 |
| IG | `IG_PLA` | 145 | 103 | 71 % | 11 396 |
| JA | `JA` | 621 | 621 | 100 % | 116 |
| MA | `MA_ROTA` | 1 087 | 663 | 61 % | 27 929 |
| ME | `ME` | 189 | 189 | 100 % | 14 441 |
| PN | `PN_PIQ` | 6 109 | 6 109 | 100 % | 1 866 |
| VE | `VE_BTGT` | 311 | 144 | 46 % | 4 718 |

**Consequence not to lose sight of**: this assumption does not stay in the
reporting. `farm_labor_hours_max` (Eq_MO_MAX_Expl) caps each farm at the labour of its
observed plan, computed through these same representatives: changing a representative
changes the cap, hence the optimum. See docs/04-vigilance.md and the
"region-aware representative crops" item of docs/status/roadmap.yaml, which this
table quantifies.

The reference indicators are therefore given with a bracket. The **central** estimate
is that of the `config.yaml` representatives -- exactly the figures a run reports on
its "input" side, so the two tell the same story. The **low** and **high** bounds
replay each plot with the least, then the most intensive variant **among those
actually eligible there**.

Nothing then guarantees that the central estimate falls inside the bracket -- the
representative does not always belong to the set of eligible variants. Where it leaves
it from above, the reference is valued with a technical system the plot could not
carry: sales (+5 %), revenue (+2 %), labor_hours (+1 %), nitrogen (+8 %), ghg (+3 %), tfi (+3 %).

| Indicator | Unit | Low | Central | High | Range |
|---|---|---:|---:|---:|---:|
| production_tonnes | t | 703 242 | 694 464 | 891 117 | 27 % |
| sales | EUR | 104 495 839 | 162 015 811 | 153 906 677 | 30 % |
| subsidy | EUR | 48 207 434 | 68 977 159 | 72 059 978 | 35 % |
| revenue | EUR | 152 703 273 | 230 992 969 | 225 966 654 | 32 % |
| gross_margin | EUR | 51 801 745 | 88 785 693 | 95 628 374 | 49 % |
| labor_hours | h | 3 785 525 | 6 252 740 | 6 195 233 | 39 % |
| nitrogen | kg N | 1 315 421 | 2 065 682 | 1 914 716 | 29 % |
| ghg | t CO2 (magnitude, see docs/04-vigilance.md) | 137 166 567 | 178 071 030 | 172 946 068 | 20 % |
| tfi | TFI.ha | 42 225 | 68 133 | 65 835 | 35 % |
| fte | FTE | - | 3 891 | - | - |
| labor_cost | EUR | - | 96 917 466 | - | - |
| net_revenue | EUR | - | -8 131 773 | - | - |
| chlordecone_risk_area | ha | - | 691 | - | - |
| water_need_m3 | m3 | - | 35 629 950 | - | - |
| soil_carbon_balance | t C | - | -11 837 | - | - |

The bracket falls back on the whole family for 482 plot(s) with no eligible variant at all.

### 4.2 Part of the observation cannot be reproduced by construction

A plot is reproducible only if at least one fine variant of its observed family is
eligible there. What is not is a gap no objective can avoid: a **floor under the
PAD**, a property of the data and of the eligibility mask, not of the run.

| Group | Observed (ha) | Reproducible (ha) | Irreproducible (ha) | Reproducible share |
|---|---:|---:|---:|---:|
| AG | 101 | 48 | 52 | 48 % |
| AN | 133 | 122 | 10 | 92 % |
| BA | 1 921 | 1 921 | 0 | 100 % |
| BC | 147 | 121 | 26 | 82 % |
| CS | 12 813 | 12 729 | 84 | 99 % |
| IG | 145 | 138 | 8 | 95 % |
| JA | 621 | 621 | 0 | 100 % |
| MA | 1 087 | 1 087 | 0 | 100 % |
| ME | 189 | 189 | 0 | 100 % |
| PN | 6 109 | 6 109 | 0 | 100 % |
| VE | 311 | 144 | 167 | 46 % |
| **TOTAL** | 23 578 | 23 230 | 348 | 99 % |

Induced PAD floor: **1.5 %** (348 ha out of 23 578 ha), and up to twice that if the excess these
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
| `csv/reference_representative_eligibility.csv` | Eligibility of the representatives |
| `reference.json` | All of it, readable by a script |

Regenerate: `python scripts/build_reference_state.py`. Deterministic (no solve).
