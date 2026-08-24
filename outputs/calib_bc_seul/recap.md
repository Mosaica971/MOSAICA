# Recap de simulation

- Horodatage : 2026-07-28T02:49:41.049119+00:00
- Duree de resolution : 154.66s
- Condition de terminaison : optimal
- Solveur : appsi_highs
- Annee / scenario : 2017 / RESTIT
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_risk_adjusted_gross_margin = 81,794,674.15

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

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 23458.85 (delta -119.14)
- Parcelles actives : 22197 -> 22034 (delta -163)
- Exploitations actives : 4588 -> 4588 (delta +0)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir VIGILANCE.md point 4)._
- Production (t) : 722,094 -> 1,066,501 (delta +344,408)
- Subvention (EUR) : 68,977,159 -> 77,843,617 (delta +8,866,458)
- Revenu / produit brut (EUR) : 229,766,229 -> 235,889,208 (delta +6,122,979)
- Cout variable (EUR) : 142,207,276 -> 132,015,564 (delta -10,191,712)
- Marge brute (EUR) : 87,558,952 -> 103,873,643 (delta +16,314,691)
- Cout main d'oeuvre (EUR) : 96,917,466 -> 85,765,452 (delta -11,152,013)
- Revenu net (marge brute - cout MO, EUR) : -9,358,513 -> 18,108,191 (delta +27,466,704)
- Emploi (ETP) : 3,890.9 -> 3,443.2 (delta -447.7)

## Calibration (observe 2017 vs simule)
_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015 section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- PAD territorial : 31.7% (seuil 15%) -> HORS SEUIL
- Cultures sous seuil : 2 / 11
- Cellules sous-regionales sous seuil : 12 / 70 (seuil 20%)
- Exploitations sous seuil : 2425 / 4588 (seuil 20%)
- Types d'exploitation correctement simules : 67.0% (seuil 80%) -> HORS SEUIL
- Parcelles avec la bonne culture : 59.8% (13274 / 22197)
- Surface avec la bonne culture : 69.0% (16,266 / 23,578 ha)
