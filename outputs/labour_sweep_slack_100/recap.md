# Simulation recap

- Scenario: labour_sweep__slack=100
- Timestamp: 2026-10-08T15:15:30.856274+00:00
- Solve duration: 30.95s
- Termination condition: optimal
- Solver: appsi_highs
- Year / scenario: 2017 / RESTIT
- Number of plots (total): 24734
- Number of farms (total): 4638

## Objective
- maximize_risk_adjusted_gross_margin = 232,574,430.27

## Enabled constraints
- at_most_one_crop_per_plot {}
- farm_area_share_max {'label': 'an_agro_max_farm', 'crops': ['AN', 'AN_NU', 'AN_PA'], 'max_share': 0.75}
- farm_area_share_max {'label': 'ig_agro_max_farm', 'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'max_share': 0.66}
- farm_area_ratio_min {'label': 'ba_ja', 'numerator_crops': ['JA'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_area_ratio_min {'label': 'ba_rota', 'numerator_crops': ['JA', 'CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM', 'CF_NBT_NISM', 'CF_NBT_NIM', 'CF_SBT_NISM', 'CF_SBT_NIM', 'CF_NGT_NISM', 'CF_NGT_NIM', 'CF_CGT_NISM', 'CF_CGT_NIM', 'CF_EGT_NISM', 'CF_EGT_NIM'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_labor_hours_max {'label': 'labor_max_farm', 'slack': 100}
- farm_production_bound {'label': 'ba_quota_farm', 'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'reference': 'BA', 'sense': 'le', 'scale': 1.0}
- territory_production_bound {'label': 'ba_quota_max', 'groups': [{'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 77877}
- territory_production_bound {'label': 'cs_quota_max', 'groups': [{'crops': ['CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM'], 'use_yield': True, 'rate_multiplier': 0.072}], 'sense': 'le', 'threshold': 107000}

## Input vs output (area)
- Cultivated area (ha): 23577.99 -> 23568.79 (delta -9.20)
- Active plots: 22197 -> 22186 (delta -11)
- Active farms: 4588 -> 4588 (delta +0)

## Input vs output (economics)
_Input = 2017 baseline priced through the fine ITK GAMS assigns each plot (Matrice_Parc_Cult, see docs/04-vigilance.md C.2)._
- Production (t): 883,147 -> 422,344 (delta -460,803)
- Subsidy (EUR): 70,745,291 -> 29,671,059 (delta -41,074,232)
- Revenue / gross product (EUR): 224,191,676 -> 686,424,187 (delta +462,232,511)
- Variable cost (EUR): 128,386,714 -> 358,366,509 (delta +229,979,795)
- Gross margin (EUR): 95,804,962 -> 328,057,678 (delta +232,252,716)
- Labour cost (EUR): 86,681,050 -> 308,465,639 (delta +221,784,589)
- Net revenue (gross margin - labour cost, EUR): 9,123,912 -> 19,592,039 (delta +10,468,127)
- Employment (FTE): 3,480.0 -> 12,384.0 (delta +8,904.0)

## Calibration (observed 2017 vs simulated)
_Gap measured at the level of the 12 observed RPG groups. Thresholds: Chopin et al. 2015 section 2.6. See docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- Territorial PAD: 119.6% (threshold 15%) -> OUTSIDE THRESHOLD
- Crops under threshold: 1 / 11
- Sub-regional cells under threshold: 7 / 70 (threshold 20%)
- Farms under threshold: 793 / 4588 (threshold 20%)
- Farm types correctly simulated: 34.3% (threshold 80%) -> OUTSIDE THRESHOLD
- Plots with the right crop: 26.0% (5768 / 22197)
- Area with the right crop: 28.3% (6,673 / 23,578 ha)
