# Simulation recap

- Scenario: nolabour_calib_newtypo_off
- Timestamp: 2026-10-08T15:17:19.976962+00:00
- Solve duration: 10.33s
- Termination condition: optimal
- Solver: appsi_highs
- Year / scenario: 2017 / RESTIT
- Number of plots (total): 24734
- Number of farms (total): 4638

## Objective
- maximize_risk_adjusted_gross_margin = 219,440,025.45

## Enabled constraints
- at_most_one_crop_per_plot {}
- farm_area_share_max {'label': 'an_agro_max_farm', 'crops': ['AN', 'AN_NU', 'AN_PA'], 'max_share': 0.75}
- farm_area_share_max {'label': 'ig_agro_max_farm', 'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'max_share': 0.66}
- farm_area_ratio_min {'label': 'ba_ja', 'numerator_crops': ['JA'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_area_ratio_min {'label': 'ba_rota', 'numerator_crops': ['JA', 'CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM', 'CF_NBT_NISM', 'CF_NBT_NIM', 'CF_SBT_NISM', 'CF_SBT_NIM', 'CF_NGT_NISM', 'CF_NGT_NIM', 'CF_CGT_NISM', 'CF_CGT_NIM', 'CF_EGT_NISM', 'CF_EGT_NIM'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_production_bound {'label': 'ba_quota_farm', 'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'reference': 'BA', 'sense': 'le', 'scale': 1.0}
- territory_production_bound {'label': 'ba_quota_max', 'groups': [{'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 77877}
- territory_production_bound {'label': 'cs_quota_max', 'groups': [{'crops': ['CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM'], 'use_yield': True, 'rate_multiplier': 0.072}], 'sense': 'le', 'threshold': 107000}

## Input vs output (area)
- Cultivated area (ha): 23577.99 -> 23549.58 (delta -28.41)
- Active plots: 22197 -> 22170 (delta -27)
- Active farms: 4588 -> 4588 (delta +0)

## Input vs output (economics)
_Input = 2017 baseline priced through the fine ITK GAMS assigns each plot (Matrice_Parc_Cult, see docs/04-vigilance.md C.2)._
- Production (t): 883,147 -> 440,064 (delta -443,083)
- Subsidy (EUR): 70,745,291 -> 30,834,680 (delta -39,910,612)
- Revenue / gross product (EUR): 224,191,676 -> 685,926,619 (delta +461,734,943)
- Variable cost (EUR): 128,386,714 -> 368,629,889 (delta +240,243,175)
- Gross margin (EUR): 95,804,962 -> 317,296,730 (delta +221,491,768)
- Labour cost (EUR): 86,681,050 -> 314,642,021 (delta +227,960,972)
- Net revenue (gross margin - labour cost, EUR): 9,123,912 -> 2,654,708 (delta -6,469,204)
- Employment (FTE): 3,480.0 -> 12,631.9 (delta +9,151.9)

## Calibration (observed 2017 vs simulated)
_Gap measured at the level of the 12 observed RPG groups. Thresholds: Chopin et al. 2015 section 2.6. See docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- Territorial PAD: 118.9% (threshold 15%) -> OUTSIDE THRESHOLD
- Crops under threshold: 1 / 11
- Sub-regional cells under threshold: 10 / 70 (threshold 20%)
- Farms under threshold: 815 / 4588 (threshold 20%)
- Farm types correctly simulated: 31.4% (threshold 80%) -> OUTSIDE THRESHOLD
- Plots with the right crop: 26.4% (5867 / 22197)
- Area with the right crop: 28.8% (6,785 / 23,578 ha)
