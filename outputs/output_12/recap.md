# Recap de simulation

- Scenario : sans_planchers_production
- Horodatage : 2026-07-17T12:21:36.920553+00:00
- Duree de resolution : 48.75s
- Condition de terminaison : optimal
- Solveur : appsi_highs
- Annee / scenario : 2017 / RESTIT
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_gross_margin = 601,027,332.68

## Contraintes activees
- at_most_one_crop_per_plot {}
- farm_area_share_max {'label': 'an_agro_max_expl', 'crops': ['AN', 'AN_NU', 'AN_PA'], 'max_share': 0.75}
- farm_area_share_max {'label': 'ig_agro_max_expl', 'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'max_share': 0.66}
- farm_area_ratio_min {'label': 'ba_ja', 'numerator_crops': ['JA'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_area_ratio_min {'label': 'ba_rota', 'numerator_crops': ['JA', 'CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM', 'CF_NBT_NISM', 'CF_NBT_NIM', 'CF_SBT_NISM', 'CF_SBT_NIM', 'CF_NGT_NISM', 'CF_NGT_NIM', 'CF_CGT_NISM', 'CF_CGT_NIM', 'CF_EGT_NISM', 'CF_EGT_NIM'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- territory_production_bound {'label': 'ba_quota_max', 'groups': [{'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 77877}
- territory_production_bound {'label': 'cs_quota_max', 'groups': [{'crops': ['CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM'], 'use_yield': True, 'rate_multiplier': 0.072}], 'sense': 'le', 'threshold': 107000}

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 24155.09 (delta +577.10)
- Parcelles actives : 22197 -> 22779 (delta +582)
- Exploitations actives : 4588 -> 4599 (delta +11)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir VIGILANCE.md point 4)._
- Production (t) : 722,460 -> 1,105,828 (delta +383,368)
- Subvention (EUR) : 65,616,972 -> 0 (delta -65,616,972)
- Revenu / produit brut (EUR) : 228,238,871 -> 1,198,250,622 (delta +970,011,751)
- Cout variable (EUR) : 141,278,643 -> 597,223,289 (delta +455,944,646)
- Marge brute (EUR) : 86,960,228 -> 601,027,333 (delta +514,067,104)
- Cout main d'oeuvre (EUR) : 89,625,861 -> 537,852,084 (delta +448,226,223)
- Revenu net (marge brute - cout MO, EUR) : -2,665,632 -> 63,175,248 (delta +65,840,881)
- Emploi (ETP) : 3,598.2 -> 21,593.1 (delta +17,994.9)
