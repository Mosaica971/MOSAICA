# Simulation recap

- Scenario: labour_sweep__slack=2
- Timestamp: 2026-10-08T14:59:12.558483+00:00
- Solve duration: 150.59s
- Termination condition: optimal
- Solver: appsi_highs
- Year / scenario: 2017 / RESTIT
- Number of plots (total): 24734
- Number of farms (total): 4638

## Objective
- maximize_risk_adjusted_gross_margin = 93,261,403.82

## Enabled constraints
- at_most_one_crop_per_plot {}
- farm_area_share_max {'label': 'an_agro_max_farm', 'crops': ['AN', 'AN_NU', 'AN_PA'], 'max_share': 0.75}
- farm_area_share_max {'label': 'ig_agro_max_farm', 'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'max_share': 0.66}
- farm_area_ratio_min {'label': 'ba_ja', 'numerator_crops': ['JA'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_area_ratio_min {'label': 'ba_rota', 'numerator_crops': ['JA', 'CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM', 'CF_NBT_NISM', 'CF_NBT_NIM', 'CF_SBT_NISM', 'CF_SBT_NIM', 'CF_NGT_NISM', 'CF_NGT_NIM', 'CF_CGT_NISM', 'CF_CGT_NIM', 'CF_EGT_NISM', 'CF_EGT_NIM'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_labor_hours_max {'label': 'labor_max_farm', 'slack': 2}
- farm_production_bound {'label': 'ba_quota_farm', 'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'reference': 'BA', 'sense': 'le', 'scale': 1.0}
- territory_production_bound {'label': 'ba_quota_max', 'groups': [{'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 77877}
- territory_production_bound {'label': 'cs_quota_max', 'groups': [{'crops': ['CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM'], 'use_yield': True, 'rate_multiplier': 0.072}], 'sense': 'le', 'threshold': 107000}

## Input vs output (area)
- Cultivated area (ha): 23577.99 -> 23543.52 (delta -34.47)
- Active plots: 22197 -> 22124 (delta -73)
- Active farms: 4588 -> 4588 (delta +0)

## Input vs output (economics)
_Input = 2017 baseline priced through the fine ITK GAMS assigns each plot (Matrice_Parc_Cult, see docs/04-vigilance.md C.2)._
- Production (t): 883,147 -> 783,376 (delta -99,771)
- Subsidy (EUR): 70,745,291 -> 60,629,072 (delta -10,116,219)
- Revenue / gross product (EUR): 224,191,676 -> 278,501,406 (delta +54,309,730)
- Variable cost (EUR): 128,386,714 -> 153,858,225 (delta +25,471,511)
- Gross margin (EUR): 95,804,962 -> 124,643,181 (delta +28,838,219)
- Labour cost (EUR): 86,681,050 -> 112,751,862 (delta +26,070,812)
- Net revenue (gross margin - labour cost, EUR): 9,123,912 -> 11,891,319 (delta +2,767,407)
- Employment (FTE): 3,480.0 -> 4,526.6 (delta +1,046.7)

## Calibration (observed 2017 vs simulated)
_Gap measured at the level of the 12 observed RPG groups. Thresholds: Chopin et al. 2015 section 2.6. See docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- Territorial PAD: 27.1% (threshold 15%) -> OUTSIDE THRESHOLD
- Crops under threshold: 0 / 11
- Sub-regional cells under threshold: 21 / 70 (threshold 20%)
- Farms under threshold: 2124 / 4588 (threshold 20%)
- Farm types correctly simulated: 72.3% (threshold 80%) -> OUTSIDE THRESHOLD
- Plots with the right crop: 57.7% (12809 / 22197)
- Area with the right crop: 70.4% (16,600 / 23,578 ha)
