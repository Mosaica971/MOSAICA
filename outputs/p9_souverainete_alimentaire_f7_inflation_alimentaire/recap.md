# Recap de simulation

- Scenario : P9_souverainete_alimentaire__F7_inflation_alimentaire
- Horodatage : 2026-08-04T00:38:28.476849+00:00
- Duree de resolution : 1495.08s
- Condition de terminaison : optimal
- Solveur : appsi_highs
- Annee / scenario : 2017 / RESTIT
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_risk_adjusted_gross_margin = 122,447,677.01

## Contraintes activees
- at_most_one_crop_per_plot {}
- farm_area_share_max {'label': 'an_agro_max_expl', 'crops': ['AN', 'AN_NU', 'AN_PA'], 'max_share': 0.75}
- farm_area_share_max {'label': 'ig_agro_max_expl', 'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'max_share': 0.66}
- farm_area_ratio_min {'label': 'ba_ja', 'numerator_crops': ['JA'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_area_ratio_min {'label': 'ba_rota', 'numerator_crops': ['JA', 'CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM', 'CF_NBT_NISM', 'CF_NBT_NIM', 'CF_SBT_NISM', 'CF_SBT_NIM', 'CF_NGT_NISM', 'CF_NGT_NIM', 'CF_CGT_NISM', 'CF_CGT_NIM', 'CF_EGT_NISM', 'CF_EGT_NIM'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_labor_hours_max {'label': 'mo_max_expl', 'slack': 1.6}
- territory_production_bound {'label': 'ba_quota_max', 'groups': [{'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 77877}
- territory_production_bound {'label': 'bc_quota_max', 'groups': [{'crops': ['BC', 'BC_BT', 'BC_GTMG'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 20000}
- territory_production_bound {'label': 'cs_quota_max', 'groups': [{'crops': ['CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM'], 'use_yield': True, 'rate_multiplier': 0.072}], 'sense': 'le', 'threshold': 80000}
- territory_production_bound {'label': 'bc_prod_min', 'groups': [{'crops': ['BC', 'BC_BT', 'BC_GTMG'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 4056}
- territory_production_bound {'label': 'ig_prod_min', 'groups': [{'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 5125}
- territory_production_bound {'label': 'ma_prod_min', 'groups': [{'crops': ['MA', 'MA_PLBIO', 'MA_MOBIO', 'MA_ROTA', 'MA_TO_CHOU_JA', 'MA_TO_CO_JA', 'MA_BAG_BIO_I', 'MA_BAG_BIO_NI', 'MA_BAG_VEG_I', 'MA_BAG_VEG_NI', 'MA_BAG_FER_I', 'MA_BAG_FER_NI', 'MA_BAG_NON_I', 'MA_BAG_NON_NI', 'MA_BRF_BIO_I', 'MA_BRF_BIO_NI', 'MA_BRF_VEG_I', 'MA_BRF_VEG_NI', 'MA_BRF_FER_I', 'MA_BRF_FER_NI', 'MA_BRF_NON_I', 'MA_BRF_NON_NI', 'MA_PAI_BIO_I', 'MA_PAI_BIO_NI', 'MA_PAI_VEG_I', 'MA_PAI_VEG_NI', 'MA_PAI_FER_I', 'MA_PAI_FER_NI', 'MA_PAI_NON_I', 'MA_PAI_NON_NI'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 26404}
- territory_production_bound {'label': 'an_prod_min', 'groups': [{'crops': ['AN', 'AN_NU', 'AN_PA'], 'use_yield': True, 'rate_multiplier': 0.6666666666666666}], 'sense': 'ge', 'threshold': 2322}
- territory_production_bound {'label': 'me_prod_min', 'groups': [{'crops': ['ME'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 4135}
- territory_production_bound {'label': 'pn_prod_min', 'groups': [{'crops': ['PN_PIQ'], 'use_yield': False, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 6096}
- territory_production_bound {'label': 'arbo_surf_min', 'groups': [{'crops': ['AG', 'VE', 'VE_BTGT', 'VE_PLUIE'], 'use_yield': False, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 200}
- territory_indicator_bound {'label': 'plancher_emploi', 'indicator': 'travail', 'sense': 'ge', 'threshold': 4200, 'scale': 0.00062228}
- territory_indicator_bound {'label': 'budget_subventions', 'indicator': 'subvention', 'sense': 'le', 'threshold': 80000000}
- baseline_inertia_min {'label': 'inertie', 'min_share': 0.3}

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 26011.29 (delta +2433.30)
- Parcelles actives : 22197 -> 24544 (delta +2347)
- Exploitations actives : 4588 -> 4638 (delta +50)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir docs/04-vigilance.md point 4)._
- Production (t) : 722,094 -> 846,190 (delta +124,096)
- Subvention (EUR) : 52,294,794 -> 29,917,566 (delta -22,377,229)
- Revenu / produit brut (EUR) : 244,954,771 -> 354,562,701 (delta +109,607,930)
- Cout variable (EUR) : 142,207,276 -> 141,421,392 (delta -785,885)
- Marge brute (EUR) : 102,747,495 -> 213,141,309 (delta +110,393,814)
- Cout main d'oeuvre (EUR) : 96,917,466 -> 108,515,438 (delta +11,597,972)
- Revenu net (marge brute - cout MO, EUR) : 5,830,030 -> 104,625,872 (delta +98,795,842)
- Emploi (ETP) : 3,890.9 -> 4,356.6 (delta +465.6)

## Calibration (observe 2017 vs simule)
_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015 section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- PAD territorial : 37.5% (seuil 15%) -> HORS SEUIL
- Cultures sous seuil : 2 / 11
- Cellules sous-regionales sous seuil : 14 / 70 (seuil 20%)
- Exploitations sous seuil : 2106 / 4588 (seuil 20%)
- Types d'exploitation correctement simules : 71.5% (seuil 80%) -> HORS SEUIL
- Parcelles avec la bonne culture : 50.0% (11090 / 22197)
- Surface avec la bonne culture : 62.5% (14,734 / 23,578 ha)
