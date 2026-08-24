# Recap de simulation

- Scenario : P1_deregulation_totale
- Horodatage : 2026-08-02T02:09:03.646190+00:00
- Duree de resolution : 60.95s
- Condition de terminaison : optimal
- Solveur : appsi_highs
- Annee / scenario : 2017 / RESTIT
- Nombre de parcelles (total) : 24734
- Nombre d'exploitations (total) : 4638

## Objectif
- maximize_gross_margin = 204,517,602.34

## Contraintes activees
- at_most_one_crop_per_plot {}
- farm_labor_hours_max {'label': 'mo_max_expl', 'slack': 3.0}

## Entree vs sortie (surface)
- Surface cultivee (ha) : 23577.99 -> 11221.93 (delta -12356.06)
- Parcelles actives : 22197 -> 13103 (delta -9094)
- Exploitations actives : 4588 -> 3957 (delta -631)

## Entree vs sortie (economie)
_Entree = baseline 2017 a economie representative par famille (voir docs/04-vigilance.md point 4)._
- Production (t) : 722,094 -> 382,339 (delta -339,755)
- Subvention (EUR) : 0 -> 0 (delta +0)
- Revenu / produit brut (EUR) : 160,789,070 -> 397,802,179 (delta +237,013,109)
- Cout variable (EUR) : 142,207,276 -> 193,284,576 (delta +51,077,300)
- Marge brute (EUR) : 18,581,794 -> 204,517,602 (delta +185,935,808)
- Cout main d'oeuvre (EUR) : 96,917,466 -> 174,162,024 (delta +77,244,558)
- Revenu net (marge brute - cout MO, EUR) : -78,335,672 -> 30,355,579 (delta +108,691,250)
- Emploi (ETP) : 3,890.9 -> 6,992.1 (delta +3,101.1)

## Calibration (observe 2017 vs simule)
_Ecart mesure au niveau des 12 groupes RPG observes. Seuils : Chopin et al. 2015 section 2.6. Voir docs/superpowers/specs/2026-07-21-calibration-validation-design.md._
- PAD territorial : 121.7% (seuil 15%) -> HORS SEUIL
- Cultures sous seuil : 0 / 11
- Cellules sous-regionales sous seuil : 1 / 70 (seuil 20%)
- Exploitations sous seuil : 270 / 4588 (seuil 20%)
- Types d'exploitation correctement simules : 12.8% (seuil 80%) -> HORS SEUIL
- Parcelles avec la bonne culture : 7.6% (1806 / 23683)
- Surface avec la bonne culture : 6.8% (1,676 / 24,749 ha)
