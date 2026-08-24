# Recap de simulation

- Scenario : P8_transition_agroecologique__pareto_azote__threshold=1351632
- Horodatage : 2026-08-10T17:52:05.389871+00:00
- Duree de resolution : 3646.86s
- Condition de terminaison : maxTimeLimit
- Solveur : appsi_highs
- Annee / scenario : 2017 / SMART
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_risk_adjusted_gross_margin = 66,552,098.33

## Contraintes activees
- at_most_one_crop_per_plot {}
- farm_area_share_max {'label': 'an_agro_max_expl', 'crops': ['AN', 'AN_NU', 'AN_PA'], 'max_share': 0.75}
- farm_area_share_max {'label': 'ig_agro_max_expl', 'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'max_share': 0.66}
- farm_area_ratio_min {'label': 'ba_ja', 'numerator_crops': ['JA'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.35}
- farm_area_ratio_min {'label': 'ba_rota', 'numerator_crops': ['JA', 'CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM', 'CF_NBT_NISM', 'CF_NBT_NIM', 'CF_SBT_NISM', 'CF_SBT_NIM', 'CF_NGT_NISM', 'CF_NGT_NIM', 'CF_CGT_NISM', 'CF_CGT_NIM', 'CF_EGT_NISM', 'CF_EGT_NIM'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_labor_hours_max {'label': 'mo_max_expl', 'slack': 1.5}
- territory_production_bound {'label': 'ba_quota_max', 'groups': [{'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 77877}
- territory_production_bound {'label': 'bc_quota_max', 'groups': [{'crops': ['BC', 'BC_BT', 'BC_GTMG'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 6440}
- territory_production_bound {'label': 'cs_quota_max', 'groups': [{'crops': ['CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM'], 'use_yield': True, 'rate_multiplier': 0.072}], 'sense': 'le', 'threshold': 107000}
- territory_production_bound {'label': 'pn_prod_min', 'groups': [{'crops': ['PN_PIQ'], 'use_yield': False, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 6096}
- territory_indicator_bound {'label': 'azote_max', 'indicator': 'azote', 'sense': 'le', 'threshold': 1351632}
- territory_indicator_bound {'label': 'plafond_ift', 'indicator': 'ift', 'sense': 'le', 'threshold': 40168}
- territory_indicator_bound {'label': 'plafond_azote', 'indicator': 'azote', 'sense': 'le', 'threshold': 1351632}
- zone_indicator_bound {'label': 'nitrates_ferme', 'zone': 'farms', 'indicator': 'azote', 'sense': 'le', 'threshold_per_ha': 150}
- territory_indicator_bound {'label': 'plafond_eau', 'indicator': 'eau', 'sense': 'le', 'threshold': 27700000, 'scale': 10.0, 'plot_weight': 'irrigable'}
- territory_indicator_bound {'label': 'plancher_emploi', 'indicator': 'travail', 'sense': 'ge', 'threshold': 4200, 'scale': 0.00062228}
- crop_share_bound {'label': 'bio_min', 'numerator_crops': ['MA_PLBIO', 'MA_MOBIO'], 'denominator_crops': ['MA', 'MA_PLBIO', 'MA_MOBIO', 'MA_ROTA', 'MA_TO_CHOU_JA', 'MA_TO_CO_JA', 'MA_BAG_BIO_I', 'MA_BAG_BIO_NI', 'MA_BAG_VEG_I', 'MA_BAG_VEG_NI', 'MA_BAG_FER_I', 'MA_BAG_FER_NI', 'MA_BAG_NON_I', 'MA_BAG_NON_NI', 'MA_BRF_BIO_I', 'MA_BRF_BIO_NI', 'MA_BRF_VEG_I', 'MA_BRF_VEG_NI', 'MA_BRF_FER_I', 'MA_BRF_FER_NI', 'MA_BRF_NON_I', 'MA_BRF_NON_NI', 'MA_PAI_BIO_I', 'MA_PAI_BIO_NI', 'MA_PAI_VEG_I', 'MA_PAI_VEG_NI', 'MA_PAI_FER_I', 'MA_PAI_FER_NI', 'MA_PAI_NON_I', 'MA_PAI_NON_NI'], 'sense': 'ge', 'share': 0.25}
- territory_indicator_bound {'label': 'budget_subventions', 'indicator': 'subvention', 'sense': 'le', 'threshold': 80000000}
- baseline_inertia_min {'label': 'inertie', 'min_share': 0.4}

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 25894.99 (delta +2317.00)
- Parcelles actives : 22197 -> 24357 (delta +2160)
- Exploitations actives : 4588 -> 4637 (delta +49)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir docs/04-vigilance.md point 4)._
- Production (t) : 722,094 -> 473,743 (delta -248,351)
- Subvention (EUR) : 63,046,280 -> 36,947,299 (delta -26,098,981)
- Revenu / produit brut (EUR) : 223,835,350 -> 217,010,451 (delta -6,824,899)
- Cout variable (EUR) : 142,155,073 -> 137,561,288 (delta -4,593,784)
- Marge brute (EUR) : 81,680,278 -> 79,449,163 (delta -2,231,115)
- Cout main d'oeuvre (EUR) : 96,859,669 -> 104,615,812 (delta +7,756,143)
- Revenu net (marge brute - cout MO, EUR) : -15,179,391 -> -25,166,649 (delta -9,987,258)
- Emploi (ETP) : 3,888.6 -> 4,200.0 (delta +311.4)

## Calibration (observe 2017 vs simule)
_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015 section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- PAD territorial : 76.2% (seuil 15%) -> HORS SEUIL
- Cultures sous seuil : 1 / 11
- Cellules sous-regionales sous seuil : 7 / 70 (seuil 20%)
- Exploitations sous seuil : 1431 / 4588 (seuil 20%)
- Types d'exploitation correctement simules : 49.0% (seuil 80%) -> HORS SEUIL
- Parcelles avec la bonne culture : 37.3% (8270 / 22197)
- Surface avec la bonne culture : 49.1% (11,566 / 23,578 ha)
