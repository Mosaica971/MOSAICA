# Recap de simulation

- Scenario : P4_statu_quo__pareto_subventions__threshold=57400000
- Horodatage : 2026-08-05T23:53:38.977969+00:00
- Duree de resolution : 1609.53s
- Condition de terminaison : optimal
- Solveur : appsi_highs
- Annee / scenario : 2017 / RESTIT
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_risk_adjusted_gross_margin = 79,182,205.97

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
- territory_indicator_bound {'label': 'budget_subventions', 'indicator': 'subvention', 'sense': 'le', 'threshold': 57400000}
- territory_indicator_bound {'label': 'plafond_ift', 'indicator': 'ift', 'sense': 'le', 'threshold': 67000}
- territory_indicator_bound {'label': 'plafond_azote', 'indicator': 'azote', 'sense': 'le', 'threshold': 1950000}
- territory_indicator_bound {'label': 'plancher_emploi', 'indicator': 'travail', 'sense': 'ge', 'threshold': 3400, 'scale': 0.00062228}

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 25943.65 (delta +2365.66)
- Parcelles actives : 22197 -> 24433 (delta +2236)
- Exploitations actives : 4588 -> 4637 (delta +49)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir docs/04-vigilance.md point 4)._
- Production (t) : 722,094 -> 856,468 (delta +134,374)
- Subvention (EUR) : 68,977,159 -> 57,111,266 (delta -11,865,893)
- Revenu / produit brut (EUR) : 229,766,229 -> 227,712,710 (delta -2,053,519)
- Cout variable (EUR) : 142,207,276 -> 123,477,950 (delta -18,729,326)
- Marge brute (EUR) : 87,558,952 -> 104,234,760 (delta +16,675,807)
- Cout main d'oeuvre (EUR) : 96,917,466 -> 86,023,541 (delta -10,893,924)
- Revenu net (marge brute - cout MO, EUR) : -9,358,513 -> 18,211,218 (delta +27,569,731)
- Emploi (ETP) : 3,890.9 -> 3,453.6 (delta -437.4)

## Calibration (observe 2017 vs simule)
_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015 section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- PAD territorial : 19.6% (seuil 15%) -> HORS SEUIL
- Cultures sous seuil : 2 / 11
- Cellules sous-regionales sous seuil : 16 / 70 (seuil 20%)
- Exploitations sous seuil : 3361 / 4588 (seuil 20%)
- Types d'exploitation correctement simules : 84.3% (seuil 80%) -> OK
- Parcelles avec la bonne culture : 64.7% (14354 / 22197)
- Surface avec la bonne culture : 73.0% (17,220 / 23,578 ha)
