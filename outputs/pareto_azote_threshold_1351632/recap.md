# Recap de simulation

- Scenario : pareto_azote__threshold=1351632
- Horodatage : 2026-08-04T21:34:49.134678+00:00
- Duree de resolution : 166.81s
- Condition de terminaison : optimal
- Solveur : appsi_highs
- Annee / scenario : 2017 / RESTIT
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_risk_adjusted_gross_margin = 74,117,181.94

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
- territory_indicator_bound {'label': 'azote_max', 'indicator': 'azote', 'sense': 'le', 'threshold': 1351632}

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 23349.15 (delta -228.84)
- Parcelles actives : 22197 -> 21908 (delta -289)
- Exploitations actives : 4588 -> 4588 (delta +0)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir docs/04-vigilance.md point 4)._
- Production (t) : 722,094 -> 759,137 (delta +37,044)
- Subvention (EUR) : 68,977,159 -> 47,143,973 (delta -21,833,186)
- Revenu / produit brut (EUR) : 229,766,229 -> 212,914,586 (delta -16,851,643)
- Cout variable (EUR) : 142,207,276 -> 111,061,811 (delta -31,145,465)
- Marge brute (EUR) : 87,558,952 -> 101,852,774 (delta +14,293,822)
- Cout main d'oeuvre (EUR) : 96,917,466 -> 80,369,640 (delta -16,547,825)
- Revenu net (marge brute - cout MO, EUR) : -9,358,513 -> 21,483,134 (delta +30,841,647)
- Emploi (ETP) : 3,890.9 -> 3,226.6 (delta -664.3)

## Calibration (observe 2017 vs simule)
_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015 section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- PAD territorial : 34.3% (seuil 15%) -> HORS SEUIL
- Cultures sous seuil : 0 / 11
- Cellules sous-regionales sous seuil : 9 / 70 (seuil 20%)
- Exploitations sous seuil : 3024 / 4588 (seuil 20%)
- Types d'exploitation correctement simules : 79.6% (seuil 80%) -> HORS SEUIL
- Parcelles avec la bonne culture : 60.1% (13344 / 22197)
- Surface avec la bonne culture : 68.5% (16,140 / 23,578 ha)
