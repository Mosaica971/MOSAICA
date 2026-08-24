# Situation de reference -- Guadeloupe 2017

Etat initial observe, reconstruit depuis l'historique RPG de `Data_Parc_Gwad_2017.txt`.
C'est la situation contre laquelle chaque run est note (PAD, matrice de confusion,
taux de correspondance parcellaire). Aucun solve : ce dossier ne depend d'aucun run.

## 1. Univers couvert

- Parcelles : 24 734
- Exploitations : 4 638
- Surface totale : 26 137 ha
- dont cultivee (reference PAD) : 23 578 ha sur 22 197 parcelles
- dont non cultivee (NC) : 2 559 ha
- Annee / scenario economique : 2017 / RESTIT
- Filtre de zone : aucun (territoire entier)

**Ce n'est pas la SAU de la Guadeloupe.** L'univers est celui du jeu de donnees
parcellaire disponible localement. Chopin et al. (2015) travaillent sur 5 336
exploitations, ce jeu en porte 4 638 : les deux ne
decrivent pas le meme perimetre
(cf. VIGILANCE.md, entree de reouverture du 2026-07-27). Toute
comparaison observe/simule doit donc rester **interne** a cet univers -- ce que fait
le PAD, qui compare les deux cotes sur les memes parcelles.

## 2. Assolement observe

Deux lectures coexistent et il faut savoir laquelle on cite :

- **brut** : `cult_2017` traduit directement en groupe RPG ;
- **resolu** : la regle GAMS de continuite de friche (ENTREES.txt:49-57) force NC
  quand `cult_2016` ET `cult_2017` sont en jachere. C'est la lecture qu'utilisent le
  modele, la typologie et le PAD.

Le passage de l'une a l'autre deplace **1 208 ha** de la jachere vers le non cultive : c'est le seul ecart entre les deux lectures.

| Groupe | Libelle | Brut (ha) | Resolu (ha) | Reference PAD (ha) | Part du cultive |
|---|---|---:|---:|---:|---:|
| AG | Agrumes | 101 | 101 | 101 | 0.4 % |
| AN | Ananas | 133 | 133 | 133 | 0.6 % |
| BA | Banane export | 1 921 | 1 921 | 1 921 | 8.1 % |
| BC | Banane plantain | 147 | 147 | 147 | 0.6 % |
| CS | Canne a sucre | 12 813 | 12 813 | 12 813 | 54.3 % |
| IG | Igname et tubercules | 145 | 145 | 145 | 0.6 % |
| JA | Jachere | 1 830 | 621 | 621 | 2.6 % |
| MA | Maraichage | 1 087 | 1 087 | 1 087 | 4.6 % |
| ME | Melon | 189 | 189 | 189 | 0.8 % |
| NC | Non cultive | 1 351 | 2 559 | 0 | 0.0 % |
| PN | Prairies et savanes | 6 109 | 6 109 | 6 109 | 25.9 % |
| VE | Vergers hors agrumes | 311 | 311 | 311 | 1.3 % |
| **TOTAL** | | 26 137 | 26 137 | 23 578 | 100 % |

Declinaisons : `csv/reference_surface_by_region.csv`, `_by_island.csv`,
`_by_commune.csv`. Reference parcelle par parcelle : `csv/reference_allocation.csv`.

## 3. Typologie des exploitations observee

Marge-ligne de toute matrice de confusion, et source du coefficient d'aversion au
risque (AVERS) de chaque ferme dans l'objectif de Markowitz : c'est un element de la
reference, pas un resultat.

| Type | Libelle | Exploitations | Part | Surface (ha) | AVERS |
|---|---|---:|---:|---:|---:|
| 0 | Sans surface cultivee | 50 | 1.1 % | 161 | 0.00 |
| 1 | Arboriculteurs | 67 | 1.4 % | 263 | 1.30 |
| 2 | Bananiers | 146 | 3.1 % | 2 520 | 1.20 |
| 3 | Canniers specialises | 1 371 | 29.6 % | 7 954 | 0.30 |
| 4 | Canniers diversifies | 862 | 18.6 % | 4 938 | 0.50-1.60 |
| 5 | Diversifies | 282 | 6.1 % | 2 236 | 0.55 |
| 6 | Eleveurs | 1 047 | 22.6 % | 4 555 | 2.40 |
| 7 | Maraichers | 216 | 4.7 % | 861 | 0.00 |
| 8 | Canniers-eleveurs | 597 | 12.9 % | 2 649 | 2.30 |

## 4. Ce que la reference ne peut pas dire

### 4.1 Aucune culture fine observee

Les 12 groupes RPG disent « canne », jamais quel systeme technique. Le GAMS avait la
meme limite (`Matrice_Parc_Cult`). Tout indicateur economique ou environnemental de
la reference passe donc par une **culture representante** par famille
(`config.yaml: baseline_representative_crops`) -- une hypothese, pas une observation.

**Premier constat, quantifie ici pour la premiere fois : la representante est souvent
une culture que le modele lui-meme interdirait sur la parcelle qu'elle represente.**
`CS_NGT_NISM` est le systeme cannier du Nord Grande-Terre, cantonne a trois communes,
et il vaut pourtant tous les hectares de canne du territoire ; `MA_ROTA` exige
l'irrigation et vaut tout le maraichage.

| Groupe | Representante | Observe (ha) | Representante eligible (ha) | Part | Marge (EUR/ha) |
|---|---|---:|---:|---:|---:|
| AG | `AG` | 101 | 48 | 48 % | 5 999 |
| AN | `AN_NU` | 133 | 122 | 92 % | 6 970 |
| BA | `BA_INT` | 1 921 | 1 319 | 69 % | 10 340 |
| BC | `BC_BT` | 147 | 93 | 63 % | 11 387 |
| CS | `CS_NGT_NISM` | 12 813 | 4 020 | 31 % | 1 521 |
| IG | `IG_PLA` | 145 | 103 | 71 % | 11 396 |
| JA | `JA` | 621 | 621 | 100 % | 116 |
| MA | `MA_ROTA` | 1 087 | 663 | 61 % | 27 929 |
| ME | `ME` | 189 | 189 | 100 % | 9 341 |
| PN | `PN_PIQ` | 6 109 | 6 109 | 100 % | 1 602 |
| VE | `VE_BTGT` | 311 | 144 | 46 % | 4 368 |

**Consequence a ne pas perdre de vue** : cette hypothese ne reste pas dans le
reporting. `farm_labor_hours_max` (Eq_MO_MAX_Expl) plafonne chaque exploitation a la
main d'oeuvre de son assolement observe, calculee via ces memes representantes :
changer une representante change le plafond, donc l'optimum. Cf. VIGILANCE.md et
l'entree « cultures representantes conscientes de la region » de TODO.md, que ce
tableau chiffre.

Les indicateurs de la reference sont donc donnes avec une fourchette. L'estimation
**centrale** est celle des representantes du `config.yaml` -- exactement les chiffres
que reporte le cote « entree » d'un run, pour que les deux racontent la meme histoire.
Les bornes **bas** et **haut** rejouent chaque parcelle avec la variante la moins,
puis la plus intense **parmi celles qui y sont reellement eligibles**.

Rien ne garantit alors que le central tombe dans la fourchette -- la representante
n'appartient pas toujours a l'ensemble des variantes eligibles. La ou il en sort par
le haut, la reference est valorisee par un systeme technique que la parcelle ne
pourrait pas porter : sales (+5 %), revenue (+2 %), labor_hours (+1 %), azote (+8 %), ges (+3 %), ift (+3 %).

| Indicateur | Unite | Bas | Central | Haut | Amplitude |
|---|---|---:|---:|---:|---:|
| production_tonnes | t | 704 784 | 722 094 | 912 864 | 29 % |
| sales | EUR | 103 332 142 | 160 789 070 | 152 958 846 | 31 % |
| subsidy | EUR | 48 207 434 | 68 977 159 | 72 059 978 | 35 % |
| revenue | EUR | 151 671 857 | 229 766 229 | 224 765 879 | 32 % |
| gross_margin | EUR | 50 840 299 | 87 558 952 | 93 187 838 | 48 % |
| labor_hours | h | 3 785 525 | 6 252 740 | 6 195 233 | 39 % |
| azote | kg N | 1 315 421 | 2 065 682 | 1 914 716 | 29 % |
| ges | t CO2 (magnitude, cf. VIGILANCE) | 137 166 567 | 178 071 030 | 172 946 068 | 20 % |
| ift | IFT.ha | 42 225 | 68 133 | 65 835 | 35 % |
| etp | ETP | - | 3 891 | - | - |
| labor_cost | EUR | - | 96 917 466 | - | - |
| net_revenue | EUR | - | -9 358 513 | - | - |
| surface_cld | ha | - | 691 | - | - |
| water_need_m3 | m3 | - | 35 629 950 | - | - |
| soil_carbon_balance | t C | - | -11 837 | - | - |

La fourchette retombe sur la famille entiere pour 482 parcelle(s) sans aucune variante eligible.

### 4.2 Une partie de l'observe est irreproductible par construction

Une parcelle n'est reproductible que si au moins une variante fine de sa famille
observee y est eligible. Ce qui ne l'est pas est un ecart qu'aucun objectif ne peut
eviter : c'est un **plancher sous le PAD**, propriete des donnees et du masque
d'eligibilite, pas du run.

| Groupe | Observe (ha) | Reproductible (ha) | Irreproductible (ha) | Part reproductible |
|---|---:|---:|---:|---:|
| AG | 101 | 48 | 52 | 48 % |
| AN | 133 | 122 | 10 | 92 % |
| BA | 1 921 | 1 921 | 0 | 100 % |
| BC | 147 | 121 | 26 | 82 % |
| CS | 12 813 | 12 729 | 84 | 99 % |
| IG | 145 | 138 | 8 | 95 % |
| JA | 621 | 621 | 0 | 100 % |
| MA | 1 087 | 1 087 | 0 | 100 % |
| ME | 189 | 189 | 0 | 100 % |
| PN | 6 109 | 6 109 | 0 | 100 % |
| VE | 311 | 144 | 167 | 46 % |
| **TOTAL** | 23 578 | 23 230 | 348 | 99 % |

Plancher de PAD induit : **1.5 %** (348 ha sur 23 578 ha), et jusqu'au double si l'on compte aussi
l'exces cree ailleurs par ces hectares deplaces. C'est faible :
**l'ecart observe/simule ne s'explique pas par l'eligibilite.**

L'eligibilite embarque aussi les suppressions GAMS (`Eq_*_SUPP`, et `Eq_VE_PLUIE`
interdite partout par le bug GAMS porte fidelement) : les vergers et les agrumes sont
donc irreproductibles pour une raison de portage, pas d'agronomie.

## 5. Fichiers

| Fichier | Contenu |
|---|---|
| `csv/reference_land_use.csv` | Assolement observe, lectures brute et resolue |
| `csv/reference_allocation.csv` | Reference parcelle par parcelle (la table pivot) |
| `csv/reference_surface_by_region.csv` | Surface cultivee par region x groupe |
| `csv/reference_surface_by_island.csv` | Idem par ile |
| `csv/reference_surface_by_commune.csv` | Idem par commune |
| `csv/reference_farm_types.csv` | Typologie observee et AVERS |
| `csv/reference_indicators.csv` | Indicateurs, central et fourchette |
| `csv/reference_reproducibility.csv` | Plancher de PAD par groupe |
| `csv/reference_representative_eligibility.csv` | Eligibilite des representantes |
| `reference.json` | Le tout, lisible par un script |

Regenerer : `python scripts/build_reference_state.py`. Deterministe (aucun solve).
