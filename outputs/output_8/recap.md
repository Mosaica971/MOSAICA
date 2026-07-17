# Recap de simulation

- Scenario : interdiction_banane_export
- Horodatage : 2026-07-17T09:02:03.758417+00:00
- Duree de resolution : 1496.51s
- Condition de terminaison : optimal
- Solveur : appsi_highs
- Annee / scenario : 2017 / RESTIT
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_gross_margin = 325,391,833.27

## Contraintes activees
- at_most_one_crop_per_plot {}
- farm_area_share_max {'label': 'an_agro_max_expl', 'crops': ['AN', 'AN_NU', 'AN_PA'], 'max_share': 0.75}
- farm_area_share_max {'label': 'ig_agro_max_expl', 'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'max_share': 0.66}
- farm_area_ratio_min {'label': 'ba_ja', 'numerator_crops': ['JA'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- farm_area_ratio_min {'label': 'ba_rota', 'numerator_crops': ['JA', 'CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM', 'CF_NBT_NISM', 'CF_NBT_NIM', 'CF_SBT_NISM', 'CF_SBT_NIM', 'CF_NGT_NISM', 'CF_NGT_NIM', 'CF_CGT_NISM', 'CF_CGT_NIM', 'CF_EGT_NISM', 'CF_EGT_NIM'], 'denominator_crops': ['BA_INT', 'BA_IRR', 'BA_SINT'], 'ratio': 0.2}
- territory_production_bound {'label': 'ba_quota_max', 'groups': [{'crops': ['BA', 'BA_INT', 'BA_IRR', 'BA_PER', 'BA_SINT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'le', 'threshold': 0}
- territory_production_bound {'label': 'cs_quota_max', 'groups': [{'crops': ['CS', 'CS_BT_NISM', 'CS_BT_NIM', 'CS_BT_IM', 'CS_SBT_NISM', 'CS_SBT_NIM', 'CS_SBT_IM', 'CS_NGT_NISM', 'CS_NGT_NIM', 'CS_NGT_IM', 'CS_CGT_NISM', 'CS_CGT_NIM', 'CS_CGT_IM', 'CS_EGT_NISM', 'CS_EGT_NIM', 'CS_EGT_IM', 'CS_MG_NISM', 'CS_MG_NIM', 'CS_MG_IM'], 'use_yield': True, 'rate_multiplier': 0.072}], 'sense': 'le', 'threshold': 107000}
- territory_production_bound {'label': 'bc_prod_min', 'groups': [{'crops': ['BC', 'BC_BT', 'BC_GTMG'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 4056}
- territory_production_bound {'label': 'ig_prod_min', 'groups': [{'crops': ['IG', 'IG_PLA', 'IG_TUT'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 5125}
- territory_production_bound {'label': 'ma_prod_min', 'groups': [{'crops': ['MA', 'MA_PLBIO', 'MA_MOBIO', 'MA_ROTA', 'MA_TO_CHOU_JA', 'MA_TO_CO_JA', 'MA_BAG_BIO_I', 'MA_BAG_BIO_NI', 'MA_BAG_VEG_I', 'MA_BAG_VEG_NI', 'MA_BAG_FER_I', 'MA_BAG_FER_NI', 'MA_BAG_NON_I', 'MA_BAG_NON_NI', 'MA_BRF_BIO_I', 'MA_BRF_BIO_NI', 'MA_BRF_VEG_I', 'MA_BRF_VEG_NI', 'MA_BRF_FER_I', 'MA_BRF_FER_NI', 'MA_BRF_NON_I', 'MA_BRF_NON_NI', 'MA_PAI_BIO_I', 'MA_PAI_BIO_NI', 'MA_PAI_VEG_I', 'MA_PAI_VEG_NI', 'MA_PAI_FER_I', 'MA_PAI_FER_NI', 'MA_PAI_NON_I', 'MA_PAI_NON_NI'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 26404}
- territory_production_bound {'label': 'an_prod_min', 'groups': [{'crops': ['AN', 'AN_NU', 'AN_PA'], 'use_yield': True, 'rate_multiplier': 0.6666666666666666}], 'sense': 'ge', 'threshold': 2322}
- territory_production_bound {'label': 'plu_prod_min', 'groups': [{'crops': ['AG', 'VE', 'VE_BTGT', 'VE_PLUIE'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 5879}
- territory_production_bound {'label': 'me_prod_min', 'groups': [{'crops': ['ME'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 4135}
- territory_production_bound {'label': 'pn_prod_min', 'groups': [{'crops': ['PN_PIQ'], 'use_yield': False, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 6096}
- territory_production_bound {'label': 'leg_prod_obj', 'groups': [{'crops': ['MA', 'MA_PLBIO', 'MA_MOBIO', 'MA_ROTA', 'MA_TO_CHOU_JA', 'MA_TO_CO_JA', 'MA_BAG_BIO_I', 'MA_BAG_BIO_NI', 'MA_BAG_VEG_I', 'MA_BAG_VEG_NI', 'MA_BAG_FER_I', 'MA_BAG_FER_NI', 'MA_BAG_NON_I', 'MA_BAG_NON_NI', 'MA_BRF_BIO_I', 'MA_BRF_BIO_NI', 'MA_BRF_VEG_I', 'MA_BRF_VEG_NI', 'MA_BRF_FER_I', 'MA_BRF_FER_NI', 'MA_BRF_NON_I', 'MA_BRF_NON_NI', 'MA_PAI_BIO_I', 'MA_PAI_BIO_NI', 'MA_PAI_VEG_I', 'MA_PAI_VEG_NI', 'MA_PAI_FER_I', 'MA_PAI_FER_NI', 'MA_PAI_NON_I', 'MA_PAI_NON_NI'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 63059}
- territory_production_bound {'label': 'fru_prod_obj', 'groups': [{'crops': ['BC', 'BC_BT', 'BC_GTMG'], 'use_yield': True, 'rate_multiplier': 1.0}, {'crops': ['AN', 'AN_NU', 'AN_PA'], 'use_yield': True, 'rate_multiplier': 0.6666666666666666}, {'crops': ['AG', 'VE', 'VE_BTGT', 'VE_PLUIE'], 'use_yield': True, 'rate_multiplier': 1.0}, {'crops': ['ME'], 'use_yield': True, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 30789}
- territory_production_bound {'label': 'pat_surf_obj', 'groups': [{'crops': ['PN_PIQ'], 'use_yield': False, 'rate_multiplier': 1.0}], 'sense': 'ge', 'threshold': 12193}

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 24155.09 (delta +577.10)
- Parcelles actives : 22197 -> 22779 (delta +582)
- Exploitations actives : 4588 -> 4599 (delta +11)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir VIGILANCE.md point 4)._
- Production (t) : 722,460 -> 593,997 (delta -128,464)
- Subvention (EUR) : 65,616,972 -> 6,706,150 (delta -58,910,822)
- Revenu / produit brut (EUR) : 228,238,871 -> 668,126,652 (delta +439,887,780)
- Cout variable (EUR) : 141,278,643 -> 342,734,818 (delta +201,456,175)
- Marge brute (EUR) : 86,960,228 -> 325,391,833 (delta +238,431,605)
- Cout main d'oeuvre (EUR) : 89,625,861 -> 301,025,080 (delta +211,399,220)
- Revenu net (marge brute - cout MO, EUR) : -2,665,632 -> 24,366,753 (delta +27,032,385)
- Emploi (ETP) : 3,598.2 -> 12,085.2 (delta +8,487.0)
