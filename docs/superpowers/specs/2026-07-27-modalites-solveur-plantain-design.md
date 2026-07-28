# Modalités de l'article, poids du solveur, et la contrainte qui manque — investigation

_2026-07-27, seconde investigation de la journée._ Fait suite à
`2026-07-27-calib-parity-rootcause-design.md`, dont elle **corrige la hiérarchie des causes**.

## Les trois questions

1. Sur quelles modalités exactes l'article publie-t-il ses résultats (périmètre, échelle,
   agrégation) — c'est-à-dire : nos chiffres et les siens mesurent-ils la même chose ?
2. Quelle part du résultat tient au solveur plutôt qu'au modèle ?
3. Reste-t-il des contraintes à retirer (absentes du `CALIB`) ou à ajouter (fondées, non
   arbitraires) ?

Aucun résultat ci-dessous ne repose sur la mémoire de session : article relu depuis le PDF,
GAMS relu depuis `old_code_gms_format_now_txt/`, tout le reste mesuré.

## 1. Les modalités — nos chiffres et les leurs ne mesuraient pas la même chose

**L'année de base est 2010.** « The initial geographic database gathered 25 057 fields, owned by
5336 farmers, and the crops grown on them in **2010** » ; contrôle contre le recensement Agreste
2010. Nous sommes sur 2017. Détail qui change l'interprétation du blocage #1 de la spec
précédente (« notre `data/` est un sous-ensemble différent ») : comparés région par région, les
deux jeux ont **quasiment les mêmes parcelles et les mêmes hectares**

| sous-région | parcelles (nous / article) | hectares (nous / article) |
|---|---|---|
| CGT | 1 601 / 1 540 | 1 598 / 1 740 |
| EGT | 3 814 / 3 911 | 4 634 / 5 007 |
| NGT | 5 561 / 5 269 | 7 011 / 7 201 |
| NBT | 4 325 / 4 251 | 5 033 / 5 035 |
| SEBT | 3 026 / 3 056 | 2 856 / 2 999 |
| SOBT | 1 025 / 976 | 1 248 / 1 150 |
| MG | 5 382 / 6 054 | 3 758 / 4 218 |
| **total** | **24 734 / 25 057** | **26 137 / 27 350** |

mais **4 638 exploitations contre 5 336**. Même foncier, 13 % de sièges en moins, taille moyenne
5,13 → 5,64 ha : c'est de la **concentration foncière sur sept ans**, pas un échantillonnage
différent. `Data_RPG_Gwad` ne remonte qu'à 2012 : l'année de base de l'article est hors
d'atteinte, et cette conclusion est définitive.

**Le PAD de l'article est par culture.** Éq. 7 somme sur les parcelles pour **une activité** ;
le seuil <15 % qualifie « a good match for 8 out of 10 agricultural uses ». Il n'existe pas de
« PAD territorial » agrégé dans l'article. Notre ligne TOTAL est une construction maison, plus
sévère ; la métrique comparable est `crops_within_threshold` (0/11 contre 8/10 — et leurs 10
usages fusionnent vergers et agrumes, que nous séparons). Le 48,4 % se relit utilement : les
totaux entrée/sortie s'équilibrant, il signifie que **24,2 % de la surface porte la mauvaise
culture** au niveau agrégé.

**Table 5 compte les parcelles non cultivées.** Leur dénominateur est la base entière
(25 057 parcelles, 27 350 ha) ; le nôtre est l'union des deux côtés cultivés. Or `Eq_NOCULT_NC`
verrouille les NC : ce sont des accords gratuits. À leur convention, `output_1` passe de
56,0 %/64,3 % à **60,5 % / 67,8 %** (2 537 parcelles / 2 559 ha NC des deux côtés). Nous ne
changeons pas notre métrique — la nôtre est plus honnête — mais la comparaison au 66 %/77 %
publié doit se faire à convention égale.

**Ni moyenne ni médiane.** Tables 4 et 5 sont des rapports de sommes (contrôle : la moyenne
non pondérée de leurs sept taux de surface donne 71 %, pas les 77 % publiés). Et **aucune table
de PAD par exploitation n'est publiée** : le seuil « 20 % … and farms » n'est jamais instancié,
l'évaluation à l'échelle ferme *est* la matrice de types. Notre médiane de 18,5 % reste utile
mais n'a pas de contrepartie ; la statistique comparable est la part de fermes sous seuil.

**L'erreur est localisée.** Six de nos sept sous-régions sont à 4–13 points du taux parcellaire
de l'article ; **Sud-Est Basse-Terre est à 36,9 % contre 61,4 %** (surface 38 % contre 66 %).

## 2. Le solveur — clos des deux côtés

**Test décisif, sans solve.** Le plan observé de 2017 valorisé sous notre propre objectif, en
donnant à chaque parcelle la **meilleure variante fine éligible** de sa famille observée (borne
haute : les contraintes de ferme sont ignorées) : **72,2 M€** contre un optimum de **85,0 M€**,
soit **15,0 %**. Le gap MIP vaut 1,0 %. L'écart à combler est quinze fois la tolérance. Le
diagnostic « frontière plate prairie/canne » de la spec précédente reste exact — 1 403 ha à
~300 €/ha ≈ 0,4 M€ — mais il pèse **3 %** du problème, pas l'essentiel.

**Test empirique.** Trois graines HiGHS, même modèle, même gap :

| graine | objectif | PAD | types | parcelles | surface |
|---|---|---|---|---|---|
| défaut | 84 978 687 € | 48,44 % | 64,04 % | 55,99 % | 64,28 % |
| 7 | 84 994 164 € | 48,29 % | 63,97 % | 55,93 % | 64,31 % |
| 42 | 84 973 268 € | 48,31 % | 63,91 % | 55,89 % | 64,28 % |

**0,15 point de PAD d'amplitude, 0,025 % d'objectif.** Il n'existe pas de réglage solveur qui
change le verdict. (Complément : le plan observé demande 5,68 M h contre un plafond de 6,25 M h ;
la main d'œuvre ne l'interdit pas non plus.)

## 3a. Retirer des contraintes absentes du `CALIB` — rien à retirer

Diff équation par équation contre `MODELE.txt:450-565`. Deux règles n'ont pas d'équivalent :

- **`SURF_PARC_MAX`** — GAMS n'a que `Eq_SURF_MIN_Parc` (MODELE.txt:228), aucun maximum de
  taille de parcelle.
- **`PLUVIO_MIN` sans exemption d'irrigation** — `Eq_PLUVIOMIN_PARC` (MODELE.txt:236) porte
  `AND Data_Parc_Gwad(SP,"IRRIG_PARC")=0`, pas notre `compute_eligibility_mask`.

Les deux sont **inertes sur ces données** : `SURF_PARC_MAX` = 1 000 ha pour les 84 cultures,
`PLUVIO_MIN` = 0 et `PLUVIO_MAX` = 10 000 pour les 84. Les retirer donne **+0 paire éligible**
et laisse le plancher de PAD à 348 ha. Corrigé au passage, sans effet : le recouvrement
`Eq_ME_MG` / règle melon `REGION_CODE` (8 647 parcelles avec les deux, 8 683 sans la seconde).

## 3b. Ajouter une contrainte fondée — `Eq_BC_QUOTA_MAX`

**Le plantain est la cause dominante.** Décomposition de l'écart de 12,8 M€ par groupe
(objectif ajusté au risque, simulé − observé) : **BC +20,9 M€**, CS +4,0, AN +3,7, MA +1,9,
contre BA −9,4, PN −5,7, ME −1,5. Le plantain vaut à lui seul plus que l'écart total.

**Le mécanisme est arithmétique.** La substitution dominante après prairie→canne est
**banane export → plantain, 1 298 ha**, concentrée en Sud-Est Basse-Terre (BA 1 427 → 311 ha,
BC 81 → 1 488 ha) — exactement la sous-région qui s'effondre. Par hectare, à AVERS 1,2
(« banana growers ») :

| | marge | `Var_Rdt` | ajusté | obligation |
|---|---|---|---|---|
| `BC_BT` | 11 386 €/ha | 0,20 | 7 971 | aucune |
| `BA_INT` | 10 340 €/ha (dont 18 658 € de subvention) | 0,10 | 9 099 | `Eq_BA_JA` : 20 % de jachère |

`Eq_BA_JA` ramène le mélange banane+jachère (116 €/ha) à **7 602 €/ha** sur 1,2 ha : le plantain
gagne de 4,9 %. Ce n'est **pas** le plafond de main d'œuvre — sur les 138 exploitations qui
basculent, la saturation médiane du plafond est de 48,6 %.

**La contrainte existe dans le GAMS et dans l'article.** `Eq_BC_QUOTA_MAX` (MODELE.txt:385) est
commentée des deux blocs modèles (lignes 551, 668), mais son paramètre est vivant —
`QUOTA_BC_MAX = 40000` t — avec le calcul de l'auteur juste dessous : « 140 tonnes
d'importations + la production locale (350 ha de plantain à 18T) ::: fixé à 6440 ». Et
l'article la décrit, Éq. 6 : « maximum thresholds for limiting the quantity of crops produced
based on … current consumption for non-exported crops, such as plantain, based on the sum of
production for local market and importation (respectively **4500 and 150 tons**) ». Le run
produit **74 757 t**.

**Mesures** (solves complets, dataset réel) :

| variante | PAD | types | parcelles | surface | BC ha | BA ha | objectif |
|---|---|---|---|---|---|---|---|
| base | 48,4 % | 64,0 % | 56,0 % | 64,3 % | 2 875 | 978 | 84,98 M€ |
| plafond 40 000 t | 38,1 % | 65,4 % | 58,7 % | 67,7 % | 1 527 | 1 993 | 84,29 M€ |
| plafond 6 440 t | 31,7 % | 67,0 % | 59,8 % | 69,0 % | 247 | 2 213 | 81,79 M€ |
| _observé_ | | | | | _147_ | _1 921_ | |

**Pourquoi ce n'est pas un forçage** — la distinction qui sépare cette piste de celles écartées
le 2026-07-23. Les « plafonds de marché » testés alors étaient calés *sur l'assolement observé*,
donc le PAD de la culture visée tombait à zéro par construction. Ici : les valeurs candidates
viennent du paramètre GAMS, du commentaire de l'auteur et de l'article, toutes **exogènes à
l'observé** ; et le plantain atterrit à 247 ha contre 147 observés même au plafond serré, soit
un PAD de 68 % — la contrainte borne un débouché, elle ne fixe pas une surface. Le gain n'est
pas non plus local : la banane export revient à 2 213 ha contre 1 921 observés (PAD 15 % contre
49 %) **sans qu'aucune contrainte ne la mentionne**, ce qui est la signature d'un mécanisme
corrigé plutôt que d'un chiffre imposé.

**Le test décisif — balayage du seuil.** La bonne question n'est pas « quelle valeur ? » mais
« le résultat dépend-il de la valeur ? ».

| seuil (t) | 4 650 | 6 440 | 9 240 | 15 000 | 25 000 | 40 000 | désactivé |
|---|---|---|---|---|---|---|---|
| objectif (M€) | 81,54 | 81,79 | 82,27 | 82,91 | 83,74 | 84,29 | 84,98 |
| PAD | 31,73 | 31,69 | **31,24** | 34,37 | 36,41 | 38,13 | 48,44 |
| types | 66,82 | 66,97 | **67,05** | 65,80 | 65,57 | 65,35 | 64,04 |
| parcelles | 59,81 | 59,80 | **60,04** | 59,52 | 59,30 | 58,67 | 55,99 |
| surface | 69,00 | 68,99 | **69,26** | 68,58 | 68,19 | 67,73 | 64,28 |
| plantain (ha) | 179 | 247 | 355 | 577 | 960 | 1 527 | 2 875 |

Deux lectures, toutes deux favorables :

1. **Palier plat de 4 650 à 9 240 t.** Un facteur 2 sur le seuil déplace le PAD de 0,5 point et
   les types de 0,25 — à peine plus que le bruit de solveur mesuré plus haut (0,15 point). Le
   résultat ne dépend pas de la valeur, seulement de l'existence d'un plafond **à l'échelle du
   marché**. Le choix de la valeur exacte n'est donc pas ce qui calibre le modèle.
2. **L'optimum du palier est à 9 240 t, soit ×2,4 le tonnage observé — pas au seuil le plus
   serré.** Un paramètre servant de variable d'ajustement s'améliorerait de façon monotone en se
   rapprochant de l'observé ; celui-ci se dégrade légèrement. C'est la preuve empirique que la
   contrainte corrige un mécanisme au lieu de recopier une réponse.

**Valeur retenue : 6 440 t.** Puisque le palier rend le score indifférent à la valeur, le
critère devient « laquelle peut-on sourcer ? ». 6 440 t est le calcul de l'auteur du GAMS,
corroboré par l'Éq. 6 de l'article (4 650 t) et par notre propre production observée en 2017
(147 ha × 26 t/ha = **3 827 t**, à 18 % du chiffre de marché 2010 de l'article — deux sources
indépendantes, sept ans d'écart). Retenir 9 240 t parce qu'il gagne 0,5 point serait exactement
le sur-ajustement qu'on cherche à éviter. Contrepartie honnête : c'est un chiffre de **2010**,
et il reste une déviation au bloc `CALIB`.

## Ce qui reste ouvert

- **La décision d'activation** (`TODO.md`). L'équation est absente du bloc `CALIB` : l'activer
  est une déviation assumée, la première depuis la clôture du 2026-07-23. Recommandation :
  40 000 t, le paramètre GAMS verbatim, qui donne déjà 10 points de PAD pour 0,8 % d'objectif.
- **Le quota sucrier.** `QUOTA_SUCRE_MAX` = 107 000 t de sucre ne mord pas (64 331 t simulés,
  39 853 t observés) et l'auteur l'a lui-même signalé comme non calé (« cette donnée est
  importante à caler … initialement 5000T fixé à MODIFIER »). La canne reste sur-plantée de
  2 579 ha. Trancher demanderait la capacité réelle de broyage (CTCS / Gardel / Grande-Anse),
  donnée externe absente du dépôt.
- **La prairie** (−5,7 M€, 6 109 → 2 576 ha) n'est pas touchée par le plafond plantain et reste
  ce que le bloc du 2026-07-23 en disait : l'absence d'élevage dans le modèle. L'article le
  reconnaît lui-même en §4.5 (« marginally developed livestock production could have been
  introduced »).
- **Le melon** est éligible sur 7 721 parcelles pour 0 ha planté : son PAD de 100 % est
  économique, pas structurel. L'article échoue aussi à 100 %, pour une raison différente
  (fermage à une société d'export, hors modèle).
