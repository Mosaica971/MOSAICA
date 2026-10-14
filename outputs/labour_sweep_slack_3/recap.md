# Simulation recap

- Scenario: labour_sweep__slack=3
- Timestamp: 2026-10-08T15:02:54.767191+00:00
- Solve duration: 146.78s
- Termination condition: optimal
- Solver: appsi_highs
- Year / scenario: 2017 / RESTIT
- Number of plots (total): 24734
- Number of farms (total): 4638

## Objective
- maximize_risk_adjusted_gross_margin = 99,499,079.88

## Enabled constraints
- at_most_one_crop_per_plot {}
- farm_area_share_max {'label': 'an_agro_max_farm', 'crops': ['AN', 'AN_NU', 'AN_PA'], 'max_share': 0.75}
- farm_area_share_max {'label': 'ig_agro_max_farm', 'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'max_share': 0.66}
- farm_area_ratio_min {'label': 'ba_ja', 'numerator_crops': ['JA'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_area_ratio_min {'label': 'ba_rota', 'numerator_crops': ['JA', 'CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM', 'CF_NBT_NISM', 'CF_NBT_NIM', 'CF_SBT_NISM', 'CF_SBT_NIM', 'CF_NGT_NISM', 'CF_NGT_NIM', 'CF_CGT_NISM', 'CF_CGT_NIM', 'CF_EGT_NISM', 'CF_EGT_NIM'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_labor_hours_max {'label': 'labor_max_farm', 'slack': 3}
- farm_production_bound {'label': 'ba_quota_farm', 'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'reference': 'BA', 'sense': 'le', 'scale': 1.0}
- territory_production_bound {'label': 'ba_quota_max', 'groups': [{'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 77877}
- territory_production_bound {'label': 'cs_quota_max', 'groups': [{'crops': ['CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM'], 'use_yield': True, 'rate_multiplier': 0.072}], 'sense': 'le', 'threshold': 107000}

## Input vs output (area)
- Cultivated area (ha): 23577.99 -> 23531.46 (delta -46.53)
- Active plots: 22197 -> 22118 (delta -79)
- Active farms: 4588 -> 4588 (delta +0)

## Input vs output (economics)
_Input = 2017 baseline priced through the fine ITK GAMS assigns each plot (Matrice_Parc_Cult, see docs/04-vigilance.md C.2)._
- Production (t): 883,147 -> 756,141 (delta -127,006)
- Subsidy (EUR): 70,745,291 -> 57,815,637 (delta -12,929,654)
- Revenue / gross product (EUR): 224,191,676 -> 308,342,128 (delta +84,150,452)
- Variable cost (EUR): 128,386,714 -> 170,813,311 (delta +42,426,597)
- Gross margin (EUR): 95,804,962 -> 137,528,817 (delta +41,723,855)
- Labour cost (EUR): 86,681,050 -> 128,143,628 (delta +41,462,579)
- Net revenue (gross margin - labour cost, EUR): 9,123,912 -> 9,385,188 (delta +261,276)
- Employment (FTE): 3,480.0 -> 5,144.6 (delta +1,664.6)

## Calibration (observed 2017 vs simulated)
_Gap measured at the level of the 12 observed RPG groups. Thresholds: Chopin et al. 2015 section 2.6. See docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- Territorial PAD: 33.7% (threshold 15%) -> OUTSIDE THRESHOLD
- Crops under threshold: 2 / 11
- Sub-regional cells under threshold: 15 / 70 (threshold 20%)
- Farms under threshold: 1895 / 4588 (threshold 20%)
- Farm types correctly simulated: 67.8% (threshold 80%) -> OUTSIDE THRESHOLD
- Plots with the right crop: 54.4% (12076 / 22197)
- Area with the right crop: 67.3% (15,874 / 23,578 ha)
