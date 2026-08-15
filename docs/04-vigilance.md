# 04 — Vigilance : ce qu'il faut savoir avant de citer un chiffre

Le modèle produit des nombres crédibles là où ils ne veulent rien dire. Cette page liste les
pièges, avec le verdict et la mesure qui le fonde. Le **journal complet des enquêtes** (avec les
chemins abandonnés et pourquoi) est dans [`archives/journal-vigilance.md`](archives/journal-vigilance.md).

Sévérités : **Critique** (fausse un résultat) · **Majeur** (limite fonctionnelle réelle) ·
**Mineur** (à connaître).

---

## A. Lire un résultat

### A.1 — Critique — Un indicateur fixé par une contrainte n'est pas un résultat

Noter une politique sur les subventions alors qu'elle plafonne elle-même son budget à 80 M€
mesure **ce qu'on lui a imposé**. P1 gagne l'axe « dépense publique » en la mettant à zéro : c'est
circulaire.

→ `comparison.bound_indicators(recap)` les détecte depuis `recap["constraints"]` — donc
rétroactivement sur les runs déjà écrits — et le dashboard les marque ⚠. Le score les inclut
quand même **si on le demande**, à dessein : les exclure d'office empêcherait de voir l'effet
d'un plafond sur les *autres* indicateurs.

### A.2 — Critique — Comparer des totaux confond échelle et intensité

Une politique qui cultive moins d'hectares affiche moins d'azote total **sans produire plus
proprement**. Un plafond d'azote se satisfait aussi en cultivant moins.

→ Lire le bloc `intensity` : azote **par tonne**, par hectare. C'est l'intensité qui décrit une
pratique.

### A.3 — Critique — « Résilience » désigne deux choses opposées dans ce dépôt

| | Mesure | Le modèle a-t-il réagi ? |
|---|---|---|
| `recap["resilience"]` (`domain/resilience.py`) | **exposition** — choc appliqué *après* le solve, allocation figée | non |
| `core/reporting/robustness.py` | **capacité d'adaptation sous contrainte politique** — ré-optimisé sous chaque forçage | oui |

**Ne jamais les additionner** : le nombre obtenu n'a pas de sens.

Trois conventions du module de robustesse, à connaître avant d'interpréter :
- une politique **infaisable** sous un forçage n'a **pas** de pire cas chiffré (case vide) —
  sinon le pire de ses survivants la ferait passer pour robuste ;
- les forçages ne sont **pas moyennés** par défaut : une moyenne affirmerait une distribution de
  probabilité que personne n'a choisie ;
- le regret se mesure contre la meilleure politique **du même forçage**.

### A.4 — Majeur — Le score composite : pondérer par famille

Sans `balance_families=True` (le défaut), les onze ratios d'autonomie alimentaire, quasi
colinéaires, pèsent **onze fois** les GES. Le score mesurerait alors la finesse du découpage, pas
la performance.

### A.5 — Majeur — Le PAD n'est pas un score en prospective

Il mesure l'écart à 2017. Un scénario politique est *fait* pour s'en écarter. À lire comme
« ampleur du bouleversement », jamais comme une note.

### A.6 — Mineur — Le diff de config dit ce qui a été *demandé*, jamais ce que l'écart a *coûté*

Une contrainte qui ne mord pas ne change aucun résultat. Et deux configs identiques divergent
déjà par le seul arbitraire de branchement du solveur (**0,15 point de PAD** mesuré sur trois
graines HiGHS). Le diff d'**allocation** répond à la question suivante.

### A.7 — Critique — Un front ε-contrainte se paramètre sur la borne de sa POLITIQUE HÔTE

Les seuils de `scenarios_pareto.yaml` sont des fractions du **réalisé de `calib_retenu`**
(1 930 903 kg N). C'est le bon réglage pour un front tracé contre la config de référence. Sous
une politique qui pose déjà sa propre borne, il ne l'est plus.

Mesuré en LP le 2026-08-09 : sous **P8**, qui plafonne l'azote à 1 351 632, **cinq des sept
points du catalogue sont inactifs ou égaux** à cette borne. P8 nue et le point à 1 930 903
rendent la même valeur, **71 065 297, au centime**. Sept solves pour trois points distincts.

→ Reparamétrer sur le niveau **où la borne mord sous l'hôte** (`plan_etape_BC.yaml` : cinq
points, fractions de 1 351 632 ; pente mesurée **5,27 €/kg N**, qui recoupe exactement le prix
dual relevé sur `plafond_azote`). ⚠ `plan.yaml` accroche `pareto_azote` à P8 **sans**
reparamétrer : le défaut est dans le plan, pas seulement dans un spec d'étape.

### A.8 — Majeur — Sous crise systémique, le plafond d'azote ne mord plus du tout

Le front azote sous **F9** a été instruit puis **abandonné sur mesure**. Les cinq points, de
1 351 632 à 810 979 kg, rendent la **même borne LP : 32 439 337**. Le plafond est inactif
partout dans la plage.

La raison est économique : F9 dégrade les rendements (×0,80), les prix export (×0,75) et les
subventions (×0,60) en renchérissant les coûts (×1,30), si bien que l'intensification cesse
d'être rentable et que l'optimum consomme spontanément **moins de 42 % de l'azote de 2017**.

→ **La crise fait déjà le travail du plafond.** C'est un résultat, obtenu sans aucun solve
MILP — et non un échec. Un vrai front sous F9 demanderait des seuils commençant sous ~810 000
kg, donc de mesurer d'abord la consommation spontanée de P8×F9 (le run existant a fini en
`maxTimeLimit` et rend une allocation identique à P8×F0, donc inexploitable).

---

## B. Solveur et tractabilité {#tractabilite}

### B.1 — Majeur — Le solve est lent et sa durée est très dispersée

30–55 min sur le territoire complet. À **taille constante** (308 847 variables), les 20 solves
enregistrés vont de **155 s à 1 007 s** — facteur 6,5, CV 64 %. Le goulot est la recherche
branch-and-bound, pas l'enveloppe Pyomo→HiGHS (~15 s, négligeable).

→ **Aucune estimation ponctuelle de durée n'est fiable.** `core/solve/progress.py` affiche donc
une **fourchette** issue des runs comparables (même taille à 20 %, même mode warm/cold), et
refuse de répondre hors de cette bande.

### B.2 — Majeur — Un solve qui tape la limite de temps rend un incumbent *prouvablement*
sous-optimal

Ce n'est pas une présomption. En partant d'une allocation existante et en basculant vers le
meilleur fruitier éligible les parcelles où cela coûte le moins, on construit **en quelques
secondes** une solution faisable valant 80,91 M€, contre **76,46 M€** trouvés par HiGHS **en une
heure** — 5,5 % d'écart.

**Signature à reconnaître** : une contrainte sur l'ananas fait reculer la canne et la banane.
Une contrainte qui n'a aucune raison de toucher un poste et le touche = branch-and-bound perdu.

→ Le correctif est le **warm start** : le même plancher arboricole, mais plus serré (335 ha au
lieu de 200), passe de 3 613 s non convergé à **642 s convergé**, objectif 4,7 M€ meilleur.

### B.3 — Majeur — Les cultures symétriques sont un désastre {#karusmart}

**Les 25 variantes maraîchères « Karusmart »** `MA_{BAG,BRF,PAI}_{BIO,VEG,FER,NON}_{I,NI}` sont
**identiques au bit près** à `MA_TO_CO_JA` sur tous les paramètres que le modèle lit — marge
20 825 €/ha, rendement 36 t/ha, 1 128 h/ha, 75,6 kg N/ha, IFT 10, même empreinte d'éligibilité.
Les distinctions paillage / fertilisation / irrigation **ne portent aucune donnée**.

Deux conséquences, les deux ont mordu :
- les rouvrir ajoute **548 000 binaires de pure symétrie** (879 162 contre 331 044) ;
- **toute part de bio bâtie sur elles est un no-op** : le solveur satisfait « 25 % de bio » en
  choisissant la copie nommée `_BIO_` d'une activité identique, à coût **exactement nul**. Une
  contrainte qui a l'air d'une politique agroécologique et ne contraint rien.

→ **Les seules vraies cultures bio du jeu sont `MA_PLBIO` et `MA_MOBIO`** (azote 0, IFT 0, pour
3 882 / 3 498 €/ha contre 27 929 à `MA_ROTA`). C'est sur elles seules qu'est bâti
`bio_maraichage`. **Ne pas rouvrir `ma_exp_supp`** sans que les 25 aient reçu des itinéraires
distincts. `check_scenario_feasibility.py` détecte et signale tout groupe symétrique.

### B.4 — Majeur — Le plafond de main d'œuvre est le vrai facteur limitant

`Eq_MO_MAX_Expl` accorde 6 252 740 h au territoire, soit **3 891 ETP** à `slack: 1.0`.

- Un **plancher d'emploi** au-dessus de 3 891 ETP est infaisable si le scénario ne desserre pas
  le slack (1.5 → 5 837 ETP, 2.0 → 7 782).
- Les **planchers de production vivrière** réclament 6 222 537 h et sont infaisables à
  `slack: 1.0`.

⚠ **Et desserrer le slack ne suffit pas.** P10 était infaisable avec un plancher à 6 000 ETP
alors que son slack en autorisait 8 561 : ce ne sont pas les heures qui manquaient mais les
**cultures capables de les absorber** sous les plafonds environnementaux. Maximum réel mesuré en
LP : **P8 → 4 875 ETP, P10 → 4 975 ETP**. Une bissection a exclu tout plafond isolé comme cause
(retirer l'IFT, l'azote ou les GES laisse l'infaisabilité) : c'est la combinaison.

→ **Ne jamais relever un plancher d'emploi sans re-mesurer.** Un test sans données
(`test_prospective_labour_slack_covers_every_employment_floor`) garde la cohérence des deux blocs.

### B.5 — Mineur — Une zone sans terme est silencieusement exemptée

`zone_indicator_bound` ne pose aucune contrainte pour une zone dont aucune paire éligible ne
porte de taux non nul. Sans conséquence pour un **plafond** ; mais pour un **plancher**, cette
zone est **dispensée** au lieu de rendre le run infaisable.

→ Contrôle : comparer le nombre de zones que la contrainte a produites au nombre que le
groupement déclare.

### B.6 — Majeur — P10 est hors d'atteinte, et aucune graine n'est réparable {#p10}

`P10_bifurcation_agroecologique` empile un plafond GES (−25 %), un IFT à 33 473 (−50 %), un
azote à 1 158 542 (−40 %), 120 kgN/ha par ferme, un plafond d'eau, cinq planchers vivriers et
un plancher d'emploi à 4 400 ETP. Le 2026-08-03 elle est sortie en `maxTimeLimit` **sans aucun
incumbent** en 7 200 s.

**Ce n'est pas de l'infaisabilité** — la relaxation LP est faisable, borne **46 311 985 €** en
81 s. Et ce n'est pas non plus une simple lenteur : `scripts/audit_warm_start_seed.py` rejette
les trois graines les plus proches.

| Graine | Contraintes violées | Le plus parlant |
|---|---:|---|
| `pareto_azote_threshold_1061997` | 124 | IFT dépassé de 26 316 sur un plafond à 33 473 |
| `pareto_azote_threshold_1158542` | 156 | + GES dépassés de 6,4 M |
| `p8_..._f0_nominal` | 407 | GES dépassés de 63,4 M, azote de 193 081 |

→ **Aucune allocation jamais produite par ce modèle n'est à distance de réparation** de ces
plafonds cumulés, et `repair_allocation.py` ne répare qu'un plancher de surface. Relancer à
froid reproduirait l'échec. Ce qu'on sait dire tient dans la borne LP : **même en autorisant
les fractions de parcelle, P10 coûte au moins 43 % de l'objectif** (46,3 M€ contre 80,8 M€
pour P8). C'est une borne supérieure valide et elle est plus solide qu'un incumbent non prouvé.
⚠ Conséquence pour la lecture : **l'axe P1 ↔ P10 est unilatéral**, seule la borne
accélérationniste est résolue.

---

### B.7 — Majeur — La chaîne de warm start est **interne au batch** : un run sur disque n'est jamais une graine {#chaine-batch}

`seed_candidates` (`scripts/run_scenarios.py:74`) propose trois graines, la plus proche
d'abord : le point précédent du même front, l'allocation nominale de la politique, la graine
globale. Les deux premières se lisent dans `sweep_seeds` et `policy_seeds` — **deux
dictionnaires remplis pendant le batch** (`run_scenarios.py:304-312`), jamais depuis
`outputs/`. Il n'existe aucune découverte de graine sur disque.

→ Conséquence : **une cellule dont la politique n'a pas de run non forcé dans le même batch
repart à froid**, quel que soit ce qui dort dans `outputs/`. C'est exactement le cas d'un lot
de reprise, qui ne rejoue par construction que les cellules forcées. Le seul moyen de nommer
un run existant est `--warm-start-from`, et il est **global au batch** : un lot mêlant
plusieurs politiques ne peut donner à chacune sa propre graine. Le découper par politique
n'est pas de la coquetterie, c'est la seule façon d'amorcer correctement.

Le symptôme est discret — la ligne « warm start depuis … » manque, mais le solve démarre
normalement et le batch ne dit rien. Contrôle : `run_scenarios.py` imprime la graine retenue
pour chaque run ; **son absence signifie froid**.

### B.8 — Majeur — La borne LP racine surestime largement ce qu'un solve a laissé {#borne-lp}

Mesuré sur `P8_transition_agroecologique` le 2026-08-11 : optimum entier **69 088 438**
(prouvé), borne LP racine **71 065 297**. Le **saut d'intégralité vaut à lui seul 2,78 %**.
Un incumbent à 68 644 754 est donc à 3,41 % de la borne LP mais à **0,64 % de l'optimum** —
un facteur cinq entre les deux lectures.

→ La borne LP sert à **prouver une infaisabilité** (cf. B.6) et à comparer des politiques
entre elles. Elle ne chiffre pas la sous-optimalité d'un incumbent : l'écart qu'elle affiche
appartient pour l'essentiel à la relaxation, pas au branch-and-bound. Ne jamais écrire « le
solveur cale à 3,4 % » sur cette base.

Corollaire mesuré le même jour : **prouver coûte plus cher que trouver**. Réamorcé sur
l'optimum lui-même, le solve a mis **8 981 s** uniquement à fermer la borne duale. Et le temps
ne rend qu'en chaîne, chaque étape repartant de l'incumbent de la précédente — 68 445 374
(1 h), 68 644 754 (+3 h), 69 088 438 prouvé (+2,2 h) — là où trois heures d'un seul tenant à
graine fixe n'avaient rapporté que 0,29 %.

### B.9 — Majeur — Un warm start peut **dégrader** une cellule forcée {#warm-regression}

Un warm start garantit un résultat **supérieur ou égal à la valeur de sa graine**. Il ne
garantit rien vis-à-vis d'un run antérieur de la même cellule, qui a pu partir d'ailleurs et
atterrir plus haut.

Mesuré le 2026-08-12 sur `P8 × F9_crise_systemique`, repris avec trois fois plus de temps :

| | objectif | durée |
|---|---:|---:|
| run initial, à froid | **−1 506 116** | 3 629 s |
| reprise, amorcée sur P8 × F0 | −1 678 357 | 10 825 s |

La graine était l'allocation de `P8 × F0`, **optimale sous F0 et médiocre sous F9** : la crise
systémique renverse la rentabilité relative des cultures, si bien que le meilleur assolement
nominal est un mauvais point de départ. Le solveur est parti d'un incumbent bas et n'en est
pas sorti en trois heures.

→ **Ne jamais écraser l'ancien run.** Après toute reprise, comparer et garder le meilleur des
deux incumbents ; la quarantaine `outputs/_non_converges/` sert exactement à ça. Et pour
reprendre une cellule forcée, la graine la plus sûre est **son propre run antérieur**, pas
l'allocation nominale de la politique — celle-ci n'est la meilleure graine que pour les
forçages qui déplacent peu les coefficients. Ce que dit `scenarios_forcages.yaml`
(« un forçage change des coefficients, pas l'ensemble faisable ») garantit la **faisabilité**
de la graine, jamais sa **qualité**.

---

## C. Données : ce que le jeu ne contient pas

### C.1 — Majeur — Les rendements du modèle sont 2 à 4× ceux du territoire

Confronté à la Statistique agricole annuelle 2017 (Agreste), qui donne production **et** surface :

| | rdt Agreste | rdt modèle | | | rdt Agreste | rdt modèle |
|---|---|---|---|---|---|---|
| Ananas | 12,3 t/ha | **34,0** | | Agrumes | 5,2 | **20,0** |
| Plantain | 9,0 | **26,0** | | Maraîchage | 10,8 | **43,9** |
| Igname | 10,0 | 17,8 | | Melon | 19,9 | 20,0 ✓ |

Une part de l'écart est légitime (Agreste moyenne tous les producteurs, `Rdt_Cult` décrit des
itinéraires spécifiés), mais un facteur 3–4 ne s'explique pas par cela seul — et le melon, lui,
tombe juste.

→ **Conséquence directe : la marge de ces cultures est mécaniquement surestimée, donc le modèle
en couvre l'île dès qu'aucun débouché ne les borne.** C'est la cause commune du plantain, de
l'ananas et de l'igname. Sous mandat de parité on n'y touche pas, mais cela explique *pourquoi*
des plafonds de marché sont nécessaires : **ce ne sont pas des béquilles**, ils compensent une
productivité surévaluée en amont.

### C.2 — Majeur — L'allocation fine 2017 en entrée n'a jamais existé

La baseline n'encode la culture qu'au niveau **agrégat RPG** (12 codes). **Le GAMS faisait
pareil** : la variante technique de 2017 n'a jamais été observée, ce n'est pas un portage
manquant.

→ Pour calculer production/subvention/revenu/ETP **en entrée**, on substitue une variante fine
représentante par famille (`config.yaml baseline_representative_crops`). **Les indicateurs
d'entrée reposent donc sur une hypothèse**, documentée et configurable.

⚠ **Et cette hypothèse influence désormais l'allocation**, pas seulement le reporting : le
plafond de main d'œuvre par exploitation est calculé via les représentantes. Changer une
représentante change le plafond, donc l'optimum.

⚠ **Pire : la représentante est souvent une culture que le modèle interdirait sur la parcelle
qu'elle représente.** Part de la surface observée où elle est éligible : **canne 31 %**,
maraîchage 61 %, plantain 63 %, banane 69 %, vergers 46 %, agrumes 48 %. Seules prairie, melon et
jachère sont à 100 %.

### C.3 — Majeur — Le RPG sous-déclare la prairie

Notre jeu parcellaire couvre **87 %** de la SAU 2017 et restitue la canne à **98 %** — mais la
prairie à **64 %** seulement (6 109 ha contre 9 595). Ce n'est pas un problème d'étiquetage : si
les ~3 500 ha manquants étaient chez nous classés en canne, notre canne dépasserait Agreste.
**Ce sont des parcelles absentes de l'univers parcellaire.**

Preuve physique indépendante : 40 449 bovins ≈ 29 771 UGB. Sur les 9 595 ha d'Agreste cela fait
**3,10 UGB/ha**, ce qui tombe pile sur les recensements ; sur les 2 980 ha que le modèle donnait
sans plancher, **9,99 UGB/ha** — trois à quatre fois le réel, agronomiquement impossible.

→ Le défaut est donc prouvé **hors modèle**. C'est ce qui fonde le plancher de prairie à
6 096 ha, **27 % sous** la valeur exogène (conservateur).

### C.4 — Majeur — Pas de pluviométrie mensuelle

La formule GAMS du besoin en eau déduit `PLUVIO_01..12_PARC`, colonnes **absentes** des données.
GAMS renvoie 0 sur colonne manquante, donc **la pluie n'a jamais été déduite**.

→ L'indicateur est un besoin en eau **brut des cultures**, pas un besoin net d'irrigation.
**Ne pas l'étiqueter « irrigation ».**

⚠ **CORRIGÉ le 2026-08-12 — la donnée mensuelle EXISTE, et elle est dans le dépôt.** Cette
entrée affirmait (comme la spec eau/carbone) que le déblocage demandait « une série
pluviométrique mensuelle par parcelle, qui n'existe pas aujourd'hui ». C'est faux.
`context/Rapport technique variables MOSAICA_v2.docx` §5 porte une section « Calcul de la
répartition mensuelle des précipitations annuelles » et publie la clé, moyennée sur trois
stations INRA (Gardel, Duclos, Godet) et neuf années complètes communes :

| J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 7,4 % | 3,8 % | 4,6 % | 9,1 % | 10,3 % | 6,8 % | 8,2 % | 11,4 % | 9,6 % | 11,7 % | 9,9 % | 7,3 % |

`PLUVIO_01..12_PARC` valait donc `PLUVIO_PARC × clé`. Les colonnes sont absentes de la table
livrée, mais la méthode et les coefficients sont versionnés. Le besoin net d'irrigation est
calculable — attention toutefois : `PLUVIO_PARC` est une **normale 1981-2010**, pas la pluie
de l'année simulée, et le bug `max(0, ·)` manquant (entrée D.3) se réveillera dès que la pluie
sera effectivement déduite.

Corollaire : les 12 colonnes `BESOIN_EAU_01..12` sont **identiques pour les 84 cultures** — tout
indicateur mensuel est dégénéré (le « mois de pointe » vaut toujours le total / 12). C'est
pourquoi il est exclu du score composite.

### C.5 — Mineur — Données présentes mais jamais lues

`Data_OTK` porte `HOUDART_TOX_SCORE`, `HARMFUL_FACTOR`, `DLRAT`, `BIRD` (écotoxicité) ;
`indice_H/RS_Cult.txt`, `Cout_Transp_Cult_LAM.txt` ; les sets `EXPL_NBT`, `PARC_NBT`,
`CULTIV_2017`… `Avers.txt` est **délibérément** ignoré (stub uniforme).

### C.6 — Mineur — `KNO3` porte `AZOTE = 0`

Le nitrate de potassium titre ~13 % d'azote. Sur les 15 engrais nommés en triplet NPK, l'azote
déduit du nom égale la colonne `AZOTE` **au millième près** — la convention du fichier est sûre —
mais les sels nommés chimiquement échappent au contrôle. Non corrigé (mandat de parité).

---

## D. Bugs GAMS portés fidèlement

Le mandat est la parité : le comportement **réel** du GAMS est porté, bug compris, avec la
variante « intention présumée » en `enable: false` juste à côté dans `config.yaml`.

### D.1 — Majeur — `Eq_VE_PLUIE` interdit les vergers pluviaux **partout**

`MODELE.txt` interroge `Data_RPG_Gwad` sur des colonnes `REGION`/`ILE` **absentes** de cette
table. GAMS renvoie 0 sans broncher, donc le test `0 ≠ 1` est **toujours vrai**.

→ **`VE_PLUIE` n'apparaîtra jamais en sortie.** Premier suspect si l'on compare un jour à des
données observées de vergers.

### D.2 — Majeur — Piège : deux ordres de types de sol incompatibles

`SOL.set` est ordonné `NITISOL, ANDOSOL, FERRALSOL, AUTRES, VERTISOL`. Le GAMS mappe la colonne
numérique `TYPE_SOL` dans un ordre **différent** : `1→VERTISOL, 2→FERRALSOL, 3→ANDOSOL,
4→NITISOL, 5→AUTRES`.

→ Indexer `Data_Sol` **par position** produit des coefficients faux mais plausibles — **erreur
silencieuse**. Toujours mapper **par nom**.

### D.3 — Mineur — Deux erreurs d'unité sans effet sur le classement

- **GES** : la magnitude atteint ~1,6e5 « t CO₂/ha/an ». L'unité annoncée est probablement fausse
  (kg ?), mais les valeurs viennent des données sources — le GAMS produirait les mêmes.
- **Eau** : le GAMS omet le facteur 10 de la conversion mm→m³ (l'auteur avait lui-même laissé
  « pourquoi x 10 ? » en commentaire). Le portage Python expose des m³ corrects.

Sans effet sur les comparaisons : le score composite normalise en min-max.

### D.4 — Mineur — `crop_variance_per_ha` porte un nom trompeur

Le paramètre contient `Var_Rdt_Cult`, une **fraction de perte de marge** — ni une variance ni un
coefficient de variation. **La perte est linéaire en surface, sans carré ni covariance.** Piège
classique pour qui voudrait bâtir un calcul de variance dessus.

### D.5 — Mineur — Bilan carbone : flux annuel seulement

Le GAMS itère `C_ORG = C_ORG + (entrées − sorties)` sur plusieurs années. Le modèle Python est
mono-année : seul le **flux annuel** est portable. Une trajectoire demanderait de réallouer année
après année — autre projet.

---

## E. Calibration : à quoi le modèle est comparé {#calibration}

### E.1 — État actuel (`calib_retenu`)

| Métrique | Parité GAMS | **Retenu** | Seuil / article |
|---|---:|---:|---:|
| Types d'exploitation reproduits | 64,0 % | **86,9 %** | 80 % (article : 81 %) |
| Parcelles bien simulées | 56,0 % | **67,6 %** | article : 66 % |
| Surface bien simulée | 64,3 % | **77,1 %** | article : 77 % |
| PAD territorial | 48,4 % | 6,6 % | 15 % |

Le modèle **atteint la qualité de calibration publiée** sur les types, les parcelles et la
surface.

⚠ **NE PAS citer le PAD territorial de 6,6 %.** Le plancher de prairie épingle la prairie, dont
le PAD est nul par construction ; le total en hérite. Les chiffres solides sont les trois
premières lignes — et surtout la **canne revenue à 12 782 ha contre 12 813 observés** (PAD 0,2 %
contre 20 %) **sans qu'aucune contrainte ne la nomme**.

### E.2 — Critique — Comparer à l'article demande quatre corrections

1. **L'article publie son PAD par culture, jamais agrégé.** Le seuil <15 % qualifie « 8 usages
   sur 10 ». Notre « PAD territorial » est une ligne TOTAL maison, **plus sévère**. La métrique
   comparable est *Cultures sous seuil*.
2. **Sa Table 5 compte les parcelles non cultivées** dans le dénominateur, nous les excluons. À
   sa convention, `calib_gams_parite` afficherait 60,5 % / 67,8 % au lieu de 56,0 % / 64,3 % —
   **quatre points qui relevaient de la définition.**
3. **Son année de base est 2010, pas 2017** (25 057 parcelles, 5 336 exploitations, contre
   24 734 / 4 638). Région par région les surfaces collent à quelques % près : c'est le même
   territoire, avec sept ans de concentration foncière. Structurellement hors d'atteinte.
4. **Il ne publie aucune table de PAD par exploitation.** Le seuil « 20 % … and farms » n'y est
   jamais instancié.

### E.3 — Majeur — Le solveur est hors de cause

- Le **plan observé de 2017 vaut 15 % de moins que l'optimum** sous notre propre objectif
  (72,2 M€ contre 85,0). Le gap MIP est de 1 % : l'écart à combler est **quinze fois** la
  tolérance.
- **Trois graines HiGHS** : PAD 48,44 / 48,29 / 48,31. L'arbitraire de branchement vaut
  **0,15 point**. Il n'y a pas de bouton solveur.

### E.4 — Deux déviations assumées au bloc `CALIB`, toutes deux sourcées

| Déviation | Valeur | Source |
|---|---|---|
| Plafond plantain `bc_quota_max` | 6 440 t | chiffre de l'auteur du GAMS ; corroboré par l'Éq. 6 de l'article (4 650 t) |
| Plancher de prairie `pn_prod_min` | 6 096 ha | paramètre GAMS `QUOTA_PN_PIQ_MIN`, corroboré par Agreste 2017 |

**Le test qui distingue une correction d'un ajustement** : le balayage du seuil plantain montre
un **palier plat de 4 650 à 9 240 t** — facteur 2 sur le seuil, 0,5 point de PAD, à peine plus
que le bruit de solveur. Le résultat ne dépend pas de la valeur, seulement de **l'existence**
d'un plafond à l'échelle du marché. Et l'optimum du palier est à 9 240 t (×2,4 l'observé), pas au
seuil le plus serré : un paramètre servant de variable d'ajustement s'améliorerait de façon
monotone en se rapprochant de l'observé.

C'est la différence de fond avec les « plafonds de marché » écartés, qui étaient calés **sur**
l'observé (PAD nul par construction).

### E.5 — Ce qui reste, et pourquoi on s'arrête là

Trois voies pour descendre sous le plateau ont été instruites jusqu'au bout puis **écartées** :
recalibrer l'aversion au risque (→ 39,9 % mais coefficients économiquement absurdes, un
spécialiste devenant « très averse » — de l'overfitting), caler des plafonds sur l'observé
(circulaire), incorporer l'élevage (l'économie y est déjà ; il manque une **variable d'état**
interdisant de liquider un cheptel gratuitement, ce que l'article reconnaît lui-même).

L'écart résiduel — prairie, plantain, petites cultures — recoupe les limites que **l'article
reconnaît lui-même**. Le détail de chaque impasse est dans le journal.

### E.6 — Trois précautions de lecture

- **Le plancher de PAD imposé par l'éligibilité est de 1,5 %** (348 ha sur 23 578). L'écart
  n'est donc **pas** expliqué par le masque : c'est un choix d'optimisation, pas une impossibilité.
- **Le PAD par exploitation a une médiane de 18,5 % pour une moyenne de 51,5 %** (quartiles
  0 / 18,5 / 88,7) : la moitié des fermes est sous le seuil de l'article. **Ne pas lire la
  moyenne comme un écart uniforme.**
- Plusieurs indicateurs tombent **dans la fourchette d'incertitude de l'observé lui-même**
  (subvention, revenu, azote, ETP) : l'assolement 2017 n'étant connu qu'au niveau agrégé, l'écart
  au « central » n'y démontre rien.

---

## F. Cartographie {#carte}

### F.1 — Majeur — La carte repose sur une jointure reconstruite

`data/gis/01_RPG 2017/` et `data_parc` décrivent le **même univers parcellaire** (24 734
enregistrements de part et d'autre, 4 638 exploitations des deux côtés, **même distribution
exacte des tailles**, zéro signature orpheline) — mais **aucun identifiant commun** : le modèle
utilise `P1..P24734`, inventés en amont.

La jointure est reconstruite par **signature d'exploitation** (multiensemble commune + surface),
puis parcelle à parcelle dans l'exploitation appariée.

→ **Couverture : 99,4 % des parcelles**, 96,7 % des exploitations. Contrôle indépendant :
l'emprise de chaque polygone est toujours ≥ la surface déclarée (ratio médian 1,74, 0 anomalie
sur 2 000).

⚠ **Ce qu'elle ne permet pas** : **~1 557 parcelles** partagent commune ET surface avec une
voisine de la même exploitation — elles peuvent avoir été interverties. Les lectures
territoriales et régionales sont fiables ; **une parcelle isolée ne fait pas preuve.** La page
l'affiche.

### F.2 — Mineur — Aucune coordonnée dans les tables

`Data_Parc` n'a ni lat/long ni identifiant de géométrie. Hors `data/gis/`, le reporting spatial
s'agrège par `ILE`/`REGION`/`COMMUNE` uniquement.

---

## G. Divers

### G.1 — Majeur — `zone_filter` ne redimensionne pas les quotas territoriaux par défaut

Un sous-ensemble devient **infaisable** vis-à-vis de seuils pensés pour tout le territoire.
`scale_territorial_bounds: true` corrige — **opt-in**, parce que réécrire un seuil change ce que
le scénario dit.

### G.2 — Majeur — Déviation assumée sur `Eq_CS_GFA`

`cs_gfa_minimum_share` est réactivée avec `skip_when_no_eligible_area: true`. Trois fermes ont
toutes leurs parcelles verrouillées en friche : la contrainte exige 60 % de canne sur une
exploitation qui ne peut en porter aucune — **algébriquement infaisable, et le GAMS le serait
aussi**. On perd 3 fermes sur 4 588 (0,07 %) plutôt que la contrainte entière. Le drapeau est à
`false` par défaut dans le builder.

### G.3 — Majeur — Bloc canne fibre (`CF`) non câblé

Les équations `Eq_CF_*` restent hors modèle. Les cultures `CF_*` sont bien éligibles et
valorisées ; ce qui manque, ce sont les contraintes et l'exploitation de
`indice_H/Prix_Cult_CF_*`. ⚠ **Ces fichiers ne sont pas des tables « prix des CF »** : ce sont des
variantes *territoire entier* décrivant un monde où la filière existe, qui diffèrent au-delà des
CF et mettent contre-intuitivement les `CF_*` à prix 0. **Trancher le sens avec la source avant
tout câblage.**

### G.4 — Mineur — Rpest : plancher artificiel et « moyenne pondérée » qui n'en est pas une

- Une culture sans pesticide somme `ADI = 0` et `AQUATOX = 0` ; or les seuils font du **bas** de
  l'ADI le côté défavorable. « Aucun produit » s'encode donc exactement comme « le produit le plus
  toxique » → prairie, jachère et `MA_PLBIO` à **2,36** contre 8,81 pour la banane intensive.
  **Le classement est solide ; le niveau absolu du bas d'échelle ne l'est pas.**
- La dose se simplifie entre numérateur et dénominateur : la « moyenne pondérée » annoncée est
  une **somme simple**. Beaucoup de petits traitements scorent plus haut qu'un seul gros.

### G.5 — Mineur — Le « bio » par itinéraire inclut la prairie

`PN_PIQ` et `PN_TOUR` utilisent `PROC_BIO_BOVIN`. Sur `output_3`, **toute** la surface « bio »
(6 096 ha) est du plancher de prairie, et la surface bio **hors prairie vaut 0 ha**.

→ Lire la variante `surface_bio_hors_prairie_*` pour toute affirmation sur les terres cultivées.
Même logique pour les MAE : l'agroécologie (MAE) et le bio sont rapportés **séparément**, parce
que la canne en récolte verte n'est pas bio.

### G.6 — Mineur — `NC` porte `Var_Rdt = 1,0`

« Non cultivé » affecté d'une perte de 100 % est un artefact du tableau source. Sans effet sur le
choc de prix, mais sa contribution à la marge à risque vaut `marge_NC × 1,0`.

---

## Aide-mémoire : les cinq à ne pas oublier

1. **Un indicateur qu'une contrainte fixe est une hypothèse, pas un résultat.**
2. **Comparer des totaux entre scénarios de surfaces différentes ne veut rien dire** — lire les
   intensités.
3. **Ne pas citer le PAD territorial de 6,6 %** — citer types / parcelles / surface, et la canne.
4. **Un solve qui tape la limite de temps est prouvablement faux**, pas juste imprécis.
5. **Une parcelle isolée sur la carte ne fait pas preuve.**
