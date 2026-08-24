# Recap de simulation

- Scenario : P5_austerite_budgetaire
- Horodatage : 2026-08-10T02:41:29.065842+00:00
- Duree de resolution : 3624.80s
- Condition de terminaison : maxTimeLimit
- Solveur : appsi_highs
- Annee / scenario : 2017 / RESTIT
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_risk_adjusted_gross_margin = 50,622,686.38

## Contraintes activees
- at_most_one_crop_per_plot {}
- farm_area_share_max {'label': 'an_agro_max_expl', 'crops': ['AN', 'AN_NU', 'AN_PA'], 'max_share': 0.75}
- farm_area_share_max {'label': 'ig_agro_max_expl', 'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'max_share': 0.66}
- farm_area_ratio_min {'label': 'ba_ja', 'numerator_crops': ['JA'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_area_ratio_min {'label': 'ba_rota', 'numerator_crops': ['JA', 'CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM', 'CF_NBT_NISM', 'CF_NBT_NIM', 'CF_SBT_NISM', 'CF_SBT_NIM', 'CF_NGT_NISM', 'CF_NGT_NIM', 'CF_CGT_NISM', 'CF_CGT_NIM', 'CF_EGT_NISM', 'CF_EGT_NIM'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_labor_hours_max {'label': 'mo_max_expl', 'slack': 0.9}
- territory_production_bound {'label': 'ba_quota_max', 'groups': [{'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 77877}
- territory_production_bound {'label': 'bc_quota_max', 'groups': [{'crops': ['BC', 'BC_BT', 'BC_GTMG'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 6440}
- territory_production_bound {'label': 'cs_quota_max', 'groups': [{'crops': ['CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM'], 'use_yield': True, 'rate_multiplier': 0.072}], 'sense': 'le', 'threshold': 107000}
- territory_production_bound {'label': 'pn_prod_min', 'groups': [{'crops': ['PN_PIQ'], 'use_yield': False, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 6096}
- territory_indicator_bound {'label': 'budget_subventions', 'indicator': 'subvention', 'sense': 'le', 'threshold': 43000000}
- baseline_inertia_min {'label': 'inertie', 'min_share': 0.6}

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 24586.23 (delta +1008.24)
- Parcelles actives : 22197 -> 22658 (delta +461)
- Exploitations actives : 4588 -> 4611 (delta +23)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir docs/04-vigilance.md point 4)._
- Production (t) : 722,094 -> 771,810 (delta +49,717)
- Subvention (EUR) : 37,827,768 -> 17,430,130 (delta -20,397,638)
- Revenu / produit brut (EUR) : 198,616,838 -> 181,363,180 (delta -17,253,659)
- Cout variable (EUR) : 142,207,276 -> 98,492,680 (delta -43,714,596)
- Marge brute (EUR) : 56,409,562 -> 82,870,500 (delta +26,460,938)
- Cout main d'oeuvre (EUR) : 96,917,466 -> 71,068,523 (delta -25,848,943)
- Revenu net (marge brute - cout MO, EUR) : -40,507,903 -> 11,801,977 (delta +52,309,881)
- Emploi (ETP) : 3,890.9 -> 2,853.2 (delta -1,037.8)

## Calibration (observe 2017 vs simule)
_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015 section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- PAD territorial : 30.4% (seuil 15%) -> HORS SEUIL
- Cultures sous seuil : 1 / 11
- Cellules sous-regionales sous seuil : 12 / 70 (seuil 20%)
- Exploitations sous seuil : 1179 / 4588 (seuil 20%)
- Types d'exploitation correctement simules : 51.3% (seuil 80%) -> HORS SEUIL
- Parcelles avec la bonne culture : 41.7% (9266 / 22197)
- Surface avec la bonne culture : 52.2% (12,318 / 23,578 ha)
