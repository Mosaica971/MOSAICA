# Recap de simulation

- Scenario : P4_statu_quo__pareto_subventions__threshold=64600000
- Horodatage : 2026-08-06T00:55:01.464109+00:00
- Duree de resolution : 3191.48s
- Condition de terminaison : optimal
- Solveur : appsi_highs
- Annee / scenario : 2017 / RESTIT
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_risk_adjusted_gross_margin = 80,624,428.14

## Contraintes activees
- at_most_one_crop_per_plot {}
- farm_area_share_max {'label': 'an_agro_max_expl', 'crops': ['AN', 'AN_NU', 'AN_PA'], 'max_share': 0.75}
- farm_area_share_max {'label': 'ig_agro_max_expl', 'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'max_share': 0.66}
- farm_area_ratio_min {'label': 'ba_ja', 'numerator_crops': ['JA'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_area_ratio_min {'label': 'ba_rota', 'numerator_crops': ['JA', 'CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM', 'CF_NBT_NISM', 'CF_NBT_NIM', 'CF_SBT_NISM', 'CF_SBT_NIM', 'CF_NGT_NISM', 'CF_NGT_NIM', 'CF_CGT_NISM', 'CF_CGT_NIM', 'CF_EGT_NISM', 'CF_EGT_NIM'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_labor_hours_max {'label': 'mo_max_expl', 'slack': 1.0}
- territory_production_bound {'label': 'ba_quota_max', 'groups': [{'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 77877}
- territory_production_bound {'label': 'bc_quota_max', 'groups': [{'crops': ['BC', 'BC_BT', 'BC_GTMG'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 6440}
- territory_production_bound {'label': 'cs_quota_max', 'groups': [{'crops': ['CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM'], 'use_yield': True, 'rate_multiplier': 0.072}], 'sense': 'le', 'threshold': 107000}
- territory_production_bound {'label': 'pn_prod_min', 'groups': [{'crops': ['PN_PIQ'], 'use_yield': False, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 6096}
- baseline_inertia_min {'label': 'inertie', 'min_share': 0.7}
- territory_indicator_bound {'label': 'budget_subventions', 'indicator': 'subvention', 'sense': 'le', 'threshold': 64600000}
- territory_indicator_bound {'label': 'plafond_ift', 'indicator': 'ift', 'sense': 'le', 'threshold': 67000}
- territory_indicator_bound {'label': 'plafond_azote', 'indicator': 'azote', 'sense': 'le', 'threshold': 1950000}
- territory_indicator_bound {'label': 'plancher_emploi', 'indicator': 'travail', 'sense': 'ge', 'threshold': 3400, 'scale': 0.00062228}

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 26022.99 (delta +2445.00)
- Parcelles actives : 22197 -> 24565 (delta +2368)
- Exploitations actives : 4588 -> 4638 (delta +50)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir docs/04-vigilance.md point 4)._
- Production (t) : 722,094 -> 884,733 (delta +162,640)
- Subvention (EUR) : 68,977,159 -> 64,590,701 (delta -4,386,458)
- Revenu / produit brut (EUR) : 229,766,229 -> 227,501,417 (delta -2,264,812)
- Cout variable (EUR) : 142,207,276 -> 126,354,517 (delta -15,852,759)
- Marge brute (EUR) : 87,558,952 -> 101,146,899 (delta +13,587,947)
- Cout main d'oeuvre (EUR) : 96,917,466 -> 86,518,205 (delta -10,399,261)
- Revenu net (marge brute - cout MO, EUR) : -9,358,513 -> 14,628,695 (delta +23,987,208)
- Emploi (ETP) : 3,890.9 -> 3,473.4 (delta -417.5)

## Calibration (observe 2017 vs simule)
_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015 section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- PAD territorial : 12.2% (seuil 15%) -> OK
- Cultures sous seuil : 3 / 11
- Cellules sous-regionales sous seuil : 19 / 70 (seuil 20%)
- Exploitations sous seuil : 3349 / 4588 (seuil 20%)
- Types d'exploitation correctement simules : 85.9% (seuil 80%) -> OK
- Parcelles avec la bonne culture : 66.6% (14778 / 22197)
- Surface avec la bonne culture : 75.3% (17,747 / 23,578 ha)
