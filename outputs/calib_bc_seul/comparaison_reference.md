# output_2 vs situation de reference 2017

- Reference : `reference_2017` (23 578 ha cultives, 22 197 parcelles, 4 638 exploitations)
- Run : objectif `maximize_risk_adjusted_gross_margin` = 81 794 674, resolu en 155 s (optimal)
- Annee / scenario : 2017 / RESTIT

## 1. Verdict de calibration

| Metrique | Valeur | Seuil (Chopin et al. 2015) | Verdict |
|---|---:|---:|---|
| PAD territorial | 31.7 % | 15 % | HORS SEUIL |
| Cultures sous seuil | 2 / 11 | 8 / 10 | HORS SEUIL |
| Types d'exploitation reproduits | 67.0 % | 80 % | HORS SEUIL |
| Exploitations sous seuil | 2425 / 4588 | - | - |
| Parcelles bien simulees | 59.8 % | 66 % (article) | HORS SEUIL |
| Surface bien simulee | 69.0 % | 77 % (article) | HORS SEUIL |

Plancher de PAD induit par l'eligibilite seule : 1.5 % (348 ha irreproductibles). L'ecart
constate est donc tres majoritairement un choix du modele, pas une impossibilite.

## 2. Assolement : observe vs simule

`irreprod.` rappelle la part de l'observe qu'aucune variante fine ne pouvait porter.

| Groupe | Observe (ha) | Simule (ha) | Ecart (ha) | PAD | Irreprod. (ha) |
|---|---:|---:|---:|---:|---:|
| AG | 101 | 91 | -9 | 9 % | 52 |
| AN | 133 | 507 | +375 | 282 % | 10 |
| BA | 1 921 | 2 213 | +292 | 15 % | 0 |
| BC | 147 | 247 | +100 | 68 % | 26 |
| CS | 12 813 | 15 425 | +2 612 | 20 % | 84 |
| IG | 145 | 289 | +144 | 99 % | 8 |
| JA | 621 | 427 | -194 | 31 % | 0 |
| MA | 1 087 | 1 240 | +153 | 14 % | 0 |
| ME | 189 | 4 | -185 | 98 % | 0 |
| PN | 6 109 | 2 980 | -3 130 | 51 % | 0 |
| VE | 311 | 33 | -278 | 89 % | 167 |
| **TOTAL** | 23 578 | 23 459 | -119 | 31.7 % | 348 |

## 3. Indicateurs : reference vs run

La colonne « dans la fourchette » compare l'ecart a l'incertitude de la reference
elle-meme (cf. REFERENCE.md section 4.1). « oui » = le run tombe dans le domaine des
assolements observes plausibles : l'ecart au central ne demontre rien.

| Indicateur | Reference (central) | Fourchette | Run | Ecart | Dans la fourchette |
|---|---:|---:|---:|---:|:--:|
| production_tonnes | 722 094 | 704 784 - 912 864 | 1 066 501 | +48 % | non |
| sales | 160 789 070 | 103 332 142 - 152 958 846 | 158 045 591 | -2 % | non |
| subsidy | 68 977 159 | 48 207 434 - 72 059 978 | 77 843 617 | +13 % | non |
| revenue | 229 766 229 | 151 671 857 - 224 765 879 | 235 889 208 | +3 % | non |
| gross_margin | 87 558 952 | 50 840 299 - 93 187 838 | 103 873 643 | +19 % | non |
| azote | 2 065 682 | 1 315 421 - 1 914 716 | 2 178 991 | +5 % | non |
| ges | 178 071 030 | 137 166 567 - 172 946 068 | 117 262 727 | -34 % | non |
| ift | 68 133 | 42 225 - 65 835 | 75 847 | +11 % | non |
| etp | 3 891 | 2 356 - 3 855 | 3 443 | -12 % | oui |
| labor_cost | 96 917 466 | - | 85 765 452 | -12 % | - |
| net_revenue | -9 358 513 | - | 18 108 191 | -293 % | - |
| surface_cld | 691 | - | 574 | -17 % | - |
| water_need_m3 | 35 629 950 | - | 37 557 343 | +5 % | - |
| soil_carbon_balance | -11 837 | - | -7 142 | -40 % | - |

1 indicateur(s) sur 9 encadres tombent dans la fourchette de
la reference.

## 4. Types d'exploitation

Rappel de lecture : la diagonale est le taux de reproduction. La marge-ligne est la
reference (typologie observee), la marge-colonne ce que le run produit.

| Type | Observees | Simulees | Reproduites (rappel) |
|---|---:|---:|---:|
| -1 Non classe | 0 | 0 | - |
| 0 Sans surface cultivee | 50 | 50 | 100 % |
| 1 Arboriculteurs | 67 | 10 | 7 % |
| 2 Bananiers | 146 | 215 | 66 % |
| 3 Canniers specialises | 1 371 | 2 062 | 99 % |
| 4 Canniers diversifies | 862 | 837 | 43 % |
| 5 Diversifies | 282 | 278 | 68 % |
| 6 Eleveurs | 1 047 | 675 | 61 % |
| 7 Maraichers | 216 | 250 | 93 % |
| 8 Canniers-eleveurs | 597 | 261 | 33 % |

Types les moins bien reproduits : Arboriculteurs (7 %), Canniers-eleveurs (33 %), Canniers diversifies (43 %).

## 5. Pour aller plus loin

- `python scripts/pad_all_scales.py outputs/output_2` : le PAD aux cinq
  echelles, ile par ile comprise (reconstruit le dataset, ~7 s).
- `csv/calibration_pad_by_crop_and_region.csv` : le detail sous-regional.
- `outputs/reference_2017/REFERENCE.md` : comment la reference est construite
  et ce qu'elle ne peut pas dire.

Correspondance parcellaire : 13274 parcelles sur 22197 portent la culture observee (69.0 % de la surface).
