# calib_retenu vs the 2017 reference state

- Reference: `reference_2017` (23 578 ha cultivated, 22 197 plots, 4 638 farms)
- Run: objective `maximize_risk_adjusted_gross_margin` = 81 222 224, solved in 779 s (optimal)
- Year / scenario: 2017 / RESTIT

## 1. Calibration verdict

| Metric | Value | Threshold (Chopin et al. 2015) | Verdict |
|---|---:|---:|---|
| Territorial PAD | 6.6 % | 15 % | OK |
| Crops under threshold | 4 / 11 | 8 / 10 | OUTSIDE THRESHOLD |
| Farm types reproduced | 86.9 % | 80 % | OK |
| Farms under threshold | 3316 / 4588 | - | - |
| Plots correctly simulated | 67.6 % | 66 % (article) | OK |
| Area correctly simulated | 77.1 % | 77 % (article) | OK |

PAD floor induced by eligibility alone: 1.5 % (348 ha irreproducible). The observed gap
is therefore overwhelmingly a choice of the model, not an impossibility.

## 2. Land use: observed vs simulated

`irreprod.` recalls the part of the observation no fine variant could carry.

| Group | Observed (ha) | Simulated (ha) | Gap (ha) | PAD | Irreprod. (ha) |
|---|---:|---:|---:|---:|---:|
| AG | 101 | 10 | -91 | 90 % | 52 |
| AN | 133 | 461 | +329 | 248 % | 10 |
| BA | 1 921 | 2 047 | +126 | 7 % | 0 |
| BC | 147 | 247 | +99 | 68 % | 26 |
| CS | 12 813 | 12 782 | -30 | 0 % | 84 |
| IG | 145 | 259 | +113 | 78 % | 8 |
| JA | 621 | 418 | -203 | 33 % | 0 |
| MA | 1 087 | 1 149 | +62 | 6 % | 0 |
| ME | 189 | 4 | -185 | 98 % | 0 |
| PN | 6 109 | 6 096 | -13 | 0 % | 0 |
| VE | 311 | 8 | -303 | 97 % | 167 |
| **TOTAL** | 23 578 | 23 481 | -97 | 6.6 % | 348 |

## 3. Indicators: reference vs run

The "inside the bracket" column compares the gap with the reference's own
uncertainty (see REFERENCE.md section 4.1). "yes" = the run falls within the range
of plausible observed cropping plans: the gap to the central value proves nothing.

| Indicator | Reference (central) | Bracket | Run | Gap | Inside the bracket |
|---|---:|---:|---:|---:|:--:|
| production_tonnes | 694 464 | 703 242 - 891 117 | 912 725 | +31 % | no |
| sales | 162 015 811 | 104 495 839 - 153 906 677 | 156 360 244 | -3 % | no |
| subsidy | 68 977 159 | 48 207 434 - 72 059 978 | 71 805 112 | +4 % | yes |
| revenue | 230 992 969 | 152 703 273 - 225 966 654 | 228 165 355 | -1 % | no |
| gross_margin | 88 785 693 | 51 801 745 - 95 628 374 | 98 632 983 | +11 % | no |
| nitrogen | 2 065 682 | 1 315 421 - 1 914 716 | 1 930 903 | -7 % | no |
| ghg | 178 071 030 | 137 166 567 - 172 946 068 | 142 733 204 | -20 % | yes |
| tfi | 68 133 | 42 225 - 65 835 | 66 946 | -2 % | no |
| fte | 3 891 | 2 356 - 3 855 | 3 503 | -10 % | yes |
| labor_cost | 96 917 466 | - | 87 255 538 | -10 % | - |
| net_revenue | -8 131 773 | - | 11 377 445 | -240 % | - |
| chlordecone_risk_area | 691 | - | 625 | -10 % | - |
| water_need_m3 | 35 629 950 | - | 34 663 590 | -3 % | - |
| soil_carbon_balance | -11 837 | - | -10 966 | -7 % | - |

3 bracketed indicator(s) out of 9 fall inside the reference's
bracket.

## 4. Farm types

Reading reminder: the diagonal is the reproduction rate. The row-marginal is the
reference (observed typology), the column-marginal what the run produces.

| Type | Observed | Simulated | Reproduced (recall) |
|---|---:|---:|---:|
| -1 Unclassified | 0 | 0 | - |
| 0 No cultivated area | 50 | 50 | 100 % |
| 1 Fruit growers | 67 | 2 | 3 % |
| 2 Banana growers | 146 | 202 | 77 % |
| 3 Specialised cane growers | 1 371 | 1 447 | 98 % |
| 4 Diversified cane growers | 862 | 745 | 78 % |
| 5 Diversified | 282 | 258 | 70 % |
| 6 Livestock farmers | 1 047 | 1 178 | 96 % |
| 7 Market gardeners | 216 | 240 | 93 % |
| 8 Cane and livestock farmers | 597 | 516 | 74 % |

Least well reproduced types: Fruit growers (3 %), Diversified (70 %), Cane and livestock farmers (74 %).

## 5. Going further

- `python scripts/pad_all_scales.py outputs/calib_retenu`: the PAD at five scales,
  island by island included (rebuilds the dataset, ~7 s).
- `csv/calibration_pad_by_crop_and_region.csv`: the sub-regional detail.
- `outputs/reference_2017/REFERENCE.md`: how the reference is built and what it
  cannot say.

Plot agreement: 15000 plots out of 22197 carry the observed crop (77.1 % of the area).
