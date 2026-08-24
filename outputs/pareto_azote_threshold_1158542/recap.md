# Recap de simulation

- Scenario : pareto_azote__threshold=1158542
- Horodatage : 2026-08-04T21:31:04.631502+00:00
- Duree de resolution : 175.47s
- Condition de terminaison : optimal
- Solveur : appsi_highs
- Annee / scenario : 2017 / RESTIT
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_risk_adjusted_gross_margin = 70,725,583.64

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
- territory_indicator_bound {'label': 'azote_max', 'indicator': 'azote', 'sense': 'le', 'threshold': 1158542}

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 23314.15 (delta -263.84)
- Parcelles actives : 22197 -> 21905 (delta -292)
- Exploitations actives : 4588 -> 4588 (delta +0)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir docs/04-vigilance.md point 4)._
- Production (t) : 722,094 -> 752,332 (delta +30,239)
- Subvention (EUR) : 68,977,159 -> 35,652,804 (delta -33,324,354)
- Revenu / produit brut (EUR) : 229,766,229 -> 215,327,942 (delta -14,438,287)
- Cout variable (EUR) : 142,207,276 -> 104,883,011 (delta -37,324,266)
- Marge brute (EUR) : 87,558,952 -> 110,444,931 (delta +22,885,978)
- Cout main d'oeuvre (EUR) : 96,917,466 -> 78,600,358 (delta -18,317,107)
- Revenu net (marge brute - cout MO, EUR) : -9,358,513 -> 31,844,573 (delta +41,203,086)
- Emploi (ETP) : 3,890.9 -> 3,155.6 (delta -735.4)

## Calibration (observe 2017 vs simule)
_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015 section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- PAD territorial : 40.5% (seuil 15%) -> HORS SEUIL
- Cultures sous seuil : 0 / 11
- Cellules sous-regionales sous seuil : 11 / 70 (seuil 20%)
- Exploitations sous seuil : 3020 / 4588 (seuil 20%)
- Types d'exploitation correctement simules : 78.5% (seuil 80%) -> HORS SEUIL
- Parcelles avec la bonne culture : 58.1% (12899 / 22197)
- Surface avec la bonne culture : 65.6% (15,462 / 23,578 ha)
