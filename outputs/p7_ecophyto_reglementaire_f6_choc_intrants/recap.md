# Recap de simulation

- Scenario : P7_ecophyto_reglementaire__F6_choc_intrants
- Horodatage : 2026-08-03T13:25:17.665159+00:00
- Duree de resolution : 929.11s
- Condition de terminaison : optimal
- Solveur : appsi_highs
- Annee / scenario : 2017 / RESTIT
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_risk_adjusted_gross_margin = 39,069,519.46

## Contraintes activees
- at_most_one_crop_per_plot {}
- farm_area_share_max {'label': 'an_agro_max_expl', 'crops': ['AN', 'AN_NU', 'AN_PA'], 'max_share': 0.75}
- farm_area_share_max {'label': 'ig_agro_max_expl', 'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'max_share': 0.66}
- farm_area_ratio_min {'label': 'ba_ja', 'numerator_crops': ['JA'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.3}
- farm_area_ratio_min {'label': 'ba_rota', 'numerator_crops': ['JA', 'CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM', 'CF_NBT_NISM', 'CF_NBT_NIM', 'CF_SBT_NISM', 'CF_SBT_NIM', 'CF_NGT_NISM', 'CF_NGT_NIM', 'CF_CGT_NISM', 'CF_CGT_NIM', 'CF_EGT_NISM', 'CF_EGT_NIM'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_labor_hours_max {'label': 'mo_max_expl', 'slack': 1.0}
- territory_production_bound {'label': 'ba_quota_max', 'groups': [{'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 77877}
- territory_production_bound {'label': 'bc_quota_max', 'groups': [{'crops': ['BC', 'BC_BT', 'BC_GTMG'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 6440}
- territory_production_bound {'label': 'cs_quota_max', 'groups': [{'crops': ['CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM'], 'use_yield': True, 'rate_multiplier': 0.072}], 'sense': 'le', 'threshold': 107000}
- territory_production_bound {'label': 'pn_prod_min', 'groups': [{'crops': ['PN_PIQ'], 'use_yield': False, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 6096}
- territory_indicator_bound {'label': 'plafond_ift', 'indicator': 'ift', 'sense': 'le', 'threshold': 46862}
- territory_indicator_bound {'label': 'plafond_azote', 'indicator': 'azote', 'sense': 'le', 'threshold': 1544722}
- zone_indicator_bound {'label': 'nitrates_ferme', 'zone': 'farms', 'indicator': 'azote', 'sense': 'le', 'threshold_per_ha': 170}
- baseline_inertia_min {'label': 'inertie', 'min_share': 0.5}

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 25909.97 (delta +2331.98)
- Parcelles actives : 22197 -> 24450 (delta +2253)
- Exploitations actives : 4588 -> 4638 (delta +50)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir docs/04-vigilance.md point 4)._
- Production (t) : 722,094 -> 816,658 (delta +94,565)
- Subvention (EUR) : 68,977,159 -> 39,228,328 (delta -29,748,831)
- Revenu / produit brut (EUR) : 229,766,229 -> 160,270,162 (delta -69,496,067)
- Cout variable (EUR) : 206,200,551 -> 118,930,912 (delta -87,269,639)
- Marge brute (EUR) : 23,565,678 -> 41,339,250 (delta +17,773,572)
- Cout main d'oeuvre (EUR) : 96,917,466 -> 52,341,710 (delta -44,575,755)
- Revenu net (marge brute - cout MO, EUR) : -73,351,787 -> -11,002,460 (delta +62,349,327)
- Emploi (ETP) : 3,890.9 -> 2,101.4 (delta -1,789.6)

## Calibration (observe 2017 vs simule)
_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015 section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- PAD territorial : 31.2% (seuil 15%) -> HORS SEUIL
- Cultures sous seuil : 2 / 11
- Cellules sous-regionales sous seuil : 10 / 70 (seuil 20%)
- Exploitations sous seuil : 2754 / 4588 (seuil 20%)
- Types d'exploitation correctement simules : 74.3% (seuil 80%) -> HORS SEUIL
- Parcelles avec la bonne culture : 52.5% (11661 / 22197)
- Surface avec la bonne culture : 59.7% (14,072 / 23,578 ha)
