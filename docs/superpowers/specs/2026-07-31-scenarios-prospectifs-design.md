# Scénarios prospectifs : politiques publiques × forçages climat/marché

**Date** : 2026-07-31
**Statut** : livré (mécaniques + scénarios + contrôle de faisabilité). Aucun solve MILP complet
n'a encore été lancé — voir « Ce qui reste à vérifier ».

## Le problème

Le dépôt savait jusqu'ici faire *une* chose en matière de scénario : modifier un prix, une
subvention, un seuil de quota, ou interdire une culture. C'est suffisant pour un test de
sensibilité, pas pour instruire une politique publique. Trois manques bloquaient :

1. **Aucune contrainte ne pouvait viser un indicateur environnemental.** L'azote, l'IFT, les
   GES, le besoin en eau et le carbone sont calculés par culture depuis 2026-07-20, mais
   uniquement en *reporting* : ils sont lus après le solve, sur une allocation déjà décidée.
   Un « scénario agroécologique » ne pouvait donc être qu'une subvention déguisée — on payait
   des cultures moins polluantes en espérant que le solveur les choisisse. Impossible d'écrire
   la seule chose qu'une politique environnementale fait réellement : *poser un plafond*.
2. **Aucun coût à la reconfiguration.** Le modèle réalloue tout le territoire en un coup, sans
   distinguer une trajectoire de dix ans d'une rupture instantanée. Deux scénarios peuvent
   aboutir au même assolement en étant, politiquement, sans rapport.
3. **Aucun moyen de croiser deux jeux d'hypothèses.** `scenarios.yaml` mélange dans une même
   liste des décisions publiques (« lever le plafond canne ») et des chocs subis (« cyclone »),
   si bien que chaque combinaison devait être réécrite à la main. Le canal `overrides` ne
   compose d'ailleurs pas : deux entrées qui touchent le même chemin pointé s'écrasent, donc
   une politique et un forçage qui modifient tous deux les subventions perdaient l'une des deux.

## Ce qui a été construit

### Trois contraintes génériques (`core/model/constraints.py`)

- **`territory_indicator_bound`** — plafond/plancher territorial sur *n'importe quel* taux par
  hectare exposé par l'étude de cas : `somme(surface × poids[parcelle] × taux[culture]) × échelle {≤|≥} seuil`.
  Une seule fonction couvre le plafond azote, le plafond IFT, le budget GES, la restriction
  d'eau, le plancher de carbone, **l'enveloppe budgétaire de subventions** et le **plancher
  d'emploi** — il suffit de nommer l'indicateur. `crops` restreint à une filière, `scale`
  convertit l'unité au dernier moment (heures → ETP) pour que le seuil s'écrive dans l'unité
  de la politique réelle.
- **`zone_indicator_bound`** — la même borne, tenue séparément dans chaque zone d'un
  découpage (île, région, commune, bassin versant, **exploitation**). `threshold_per_ha`
  multiplie par les hectares propres de la zone, ce qui est la forme exacte d'une directive
  nitrates à 170 kgN/ha. Grouper par exploitation est délibérément autorisé : un plafond
  environnemental par ferme, c'est la même algèbre qu'un plafond par bassin versant.
- **`baseline_inertia_min`** — au moins X % de la surface allouée reste dans son groupe
  observé 2017. Rend la vitesse de transition explicite au lieu de la laisser implicite à 100 %.
  Les deux membres sont variables (part de la surface *allouée*, pas du territoire), ce qui
  garde la contrainte linéaire et l'empêche de forcer la mise en culture pour satisfaire un ratio.

### Deux extensions de `ModelInputs`

- `crop_indicator_rates` : `{indicateur: {culture: taux/ha}}`. `core` ne connaît ni les noms ni
  les unités, il multiplie par des hectares.
- `plot_weights` : `{nom: {parcelle: facteur}}`. Nécessaire et pas cosmétique — les taux sont
  par culture, or **l'eau ne se prélève que sur les parcelles irrigables**. Sans ce poids, un
  plafond d'eau compterait les hectares pluviaux et vaudrait 56 Mm³ là où le run rapporte
  35 Mm³ : un seuil lu sur le recap aurait été faux contre la contrainte.

### Un canal de choc supplémentaire : `variance_multipliers`

`Var_Rdt_Cult` est la variance de rendement que l'objectif de Markowitz met en balance avec la
marge. La multiplier permet de modéliser **l'instabilité climatique distinctement de la perte de
rendement** : une culture peut conserver son rendement moyen et devenir intenable pour une ferme
averse au risque. Aucun des quatre canaux existants ne savait exprimer ça.

### Composition politique × forçage (`core/config.py`)

`merge_run_specs` fusionne deux specs de run en **concaténant** les listes de multiplicateurs
qui partagent un chemin pointé (au lieu de les écraser) et en concaténant les canaux
`enable`/`disable`/`set_args`/`enable_add`. `compose_runs` produit ensuite soit les politiques
seules (défaut étagé), soit leur produit avec les forçages.

Une asymétrie est documentée et assumée : `apply_overrides` applique toujours `enable` avant
`disable`, donc un jeton désactivé par l'un des deux specs le reste quoi qu'en dise l'autre. Un
forçage qui devrait réactiver ce qu'une politique a coupé doit passer par `enable_add`.

### Étiquettes sur les règles d'éligibilité

Les huit règles catégorielles acceptent désormais des arguments supplémentaires, ce qui permet
de leur donner un `label`. Sans cela, un scénario ne pouvait lever **aucune** interdiction
précise : `disable: [forbid_crops]` aurait touché les six entrées portant ce nom, remettant en
jeu les huit codes agrégés qui ne servent qu'à encoder l'observé. Sont étiquetées les seules
règles qu'un scénario prospectif a une raison légitime de rouvrir : `cs_irrig_ban` (canne
irriguée), `pn_tour_supp` (pâturage tournant), `ma_exp_supp` (systèmes maraîchers
agroécologiques), `cf_supp` (canne fibre), `friche`, `nocult_nc_1/2`, `pn_piq_cld`.

### `crops: "*"`

`apply_crop_multipliers` accepte un joker. Un choc territorial (suppression de toutes les
subventions, effondrement général des prix) devait sinon énumérer les 84 codes — et aurait
silencieusement raté toute culture ajoutée ensuite.

## Les scénarios

> **Mise à jour du 2026-08-01.** `scenarios_prospective.yaml` a été scindé sans changer une
> valeur (identité vérifiée sur les 10 politiques et 12 forçages) en trois **catalogues** —
> `scenarios_politiques.yaml`, `scenarios_forcages.yaml`, `scenarios_pareto.yaml` — et un
> **plan**, `plan.yaml`, qui seul décide des croisements effectivement résolus. Les groupes de
> cultures, que les ancres YAML ne pouvaient pas partager entre fichiers, vivent dans
> `crop_groups.yaml` et se citent `{group: canne}`. Ce qui suit décrit le contenu, inchangé.

Dix politiques sur un axe unique, plus une hors axe, chacune portant 5 à 22 modifications :

| # | Politique | Nature |
|---|---|---|
| P1 | `deregulation_totale` | **Borne extrême** : marge pure, zéro subvention, zéro quota, zéro rotation |
| P2 | `accelerationnisme_industriel` | État développeur : on paie, on déplafonne, on irrigue, on mécanise |
| P3 | `intensification_moderee` | Trajectoire productiviste crédible à 10 ans |
| P4 | `statu_quo` | Le statu quo **comme politique** : gel budgétaire, non-dégradation, inertie 70 % |
| P5 | `austerite_budgetaire` | Le statu quo privé d'argent public (−40 %) |
| P6 | `verdissement_incitatif` | Agroécologie par la carotte **seule** |
| P7 | `ecophyto_reglementaire` | Agroécologie par le bâton **seul** — le pendant exact de P6 |
| P8 | `transition_agroecologique` | Le paquet complet et cohérent |
| P9 | `souverainete_alimentaire` | **Hors axe** : nourrir le territoire |
| P10 | `bifurcation_agroecologique` | **Borne extrême** symétrique de P1 |

P6 et P7 sont conçues pour être lues ensemble : même ambition, un instrument chacune. L'écart
entre les deux est la réponse à « faut-il payer ou interdire ? », et c'est la question de
politique publique la plus fréquemment posée.

Onze forçages, dont un neutre (`F0_nominal`, qui fait que le croisement couvre aussi chaque
politique non forcée) : cyclone majeur, sécheresse sévère, dérive climatique (canal *variance*),
choc sanitaire, effondrement des prix d'export, choc d'intrants, inflation alimentaire (favorable
au local), retrait du POSEI, crise systémique, conjoncture favorable (borne haute — sans elle on
ne sait pas si un écart tient au forçage ou à la politique).

**Tous les seuils sont un pourcentage de grandeurs mesurées**, pas des chiffres choisis : les
totaux d'`outputs/output_3` sur le jeu réel (marge 98,6 M€, subventions 71,8 M€, 3 503 ETP,
1 930 903 kg N, IFT 66 946, 34,66 Mm³ d'eau). L'en-tête du YAML les liste, et c'est la seule
raison pour laquelle les seuils ne sont pas arbitraires.

## Le contrôle de faisabilité (`scripts/check_scenario_feasibility.py`)

Un batch croisé, c'est plusieurs nuits de calcul. Découvrir au matin qu'un scénario était
algébriquement infaisable est le mode d'échec coûteux, et il s'est produit **dès la conception**.

Le script relâche les binaires dans [0, 1] et résout la LP. La logique est à sens unique :
LP infaisable ⇒ MILP infaisable, **certain**. LP faisable ⇒ le MILP *peut* encore échouer, mais
toutes les infaisabilités rencontrées dans ce projet ont été algébriques (un plafond de main
d'œuvre contre un plancher de production), jamais entières.

Il a servi immédiatement : **P10 était infaisable tel qu'écrit**, et le contrôle l'a établi en
6 minutes au lieu de le découvrir après une nuit de solve. Après correction des planchers
d'emploi, **les 10 politiques passent** (LP `optimal`), avec ces majorants d'objectif :

| Scénario | Borne LP | Rapport au statu quo |
|---|---|---|
| P1 `deregulation_totale` | 212,9 M€ | *non comparable* — seul scénario à changer d'objectif |
| P2 `accelerationnisme_industriel` | 108,6 M€ | +32 % |
| P3 `intensification_moderee` | 96,4 M€ | +17 % |
| P6 `verdissement_incitatif` | 86,6 M€ | +5 % |
| P9 `souverainete_alimentaire` | 83,9 M€ | +2 % |
| **P4 `statu_quo`** | **82,5 M€** | référence |
| P7 `ecophyto_reglementaire` | 73,4 M€ | −11 % |
| P8 `transition_agroecologique` | 71,1 M€ | −14 % |
| P5 `austerite_budgetaire` | 56,5 M€ | −32 % |
| P10 `bifurcation_agroecologique` | 47,1 M€ | −43 % |

Ce ne sont **pas** des résultats : ce sont des majorants relâchés, sur un objectif qui n'est pas
un indicateur de bien-être. Ils confirment surtout que le spectre est bien ordonné et qu'aucun
scénario n'est vide de sens. Un point mérite déjà d'être noté : P6 (incitation seule) borne plus
haut que P7 (réglementation seule) — l'incitation *ajoute* de la marge là où le plafond en
retire — mais c'est arithmétique, pas un jugement : les deux ne coûtent pas la même chose à
l'argent public, et seule la comparaison des indicateurs physiques après solve tranchera.

**P1 n'est comparable à aucun autre sur cette colonne** : il maximise la marge brute pure quand
les neuf autres maximisent la marge ajustée du risque. Ce sont deux fonctions différentes. La
comparaison entre politiques doit se faire sur les colonnes physiques et économiques du
`batch_summary` (marge brute, ETP, azote, IFT, eau), calculées à l'identique quel que soit
l'objectif.

## Le piège de la main d'œuvre — la leçon principale

`Eq_MO_MAX_Expl` plafonne chaque ferme à la main d'œuvre de son plan 2017 observé : 6 252 740 h,
soit **3 891 ETP** au niveau du territoire, pour 5 629 390 h effectivement utilisées. Il en
découle deux règles qu'aucune relecture de YAML ne rend évidentes :

- un **plancher d'emploi** au-dessus de 3 891 ETP est infaisable si le même scénario ne
  desserre pas le `slack` ;
- les **planchers de production vivrière** demandent 6 222 537 h par leurs cultures les moins
  gourmandes — 0,5 % de marge sur une borne inférieure qui ignore la concurrence foncière — et
  sont de fait infaisables à `slack: 1.0` (`main.py` a échoué exactement là-dessus le 2026-07-21).

Un test le vérifie désormais sans données (`test_prospective_labour_slack_covers_every_employment_floor`) :
il relit chaque politique, calcule le plafond effectif d'après son `slack` et refuse tout
plancher d'emploi au-dessus. C'est le seul garde-fou entre deux blocs YAML distants de trente
lignes.

**Mais desserrer le `slack` ne suffit pas, et c'est le résultat le plus intéressant.** P10 avait
d'abord été écrit avec un plancher à 6 000 ETP sous un `slack: 2.2` autorisant 8 561 ETP de budget
horaire — et il était infaisable. Ce ne sont pas les heures qui manquaient mais **les cultures
capables de les absorber** une fois les plafonds environnementaux posés. En maximisant le travail
sous les autres contraintes de chaque politique (relaxation LP, donc bornes supérieures) :

| Politique | Emploi maximal atteignable | Plancher retenu |
|---|---|---|
| référence `output_3` | 3 503 ETP (réalisé) | — |
| P8 `transition_agroecologique` | 4 875 ETP | 4 200 (86 %) |
| P9 `souverainete_alimentaire` | 5 734 ETP | 4 200 (73 %) |
| P10 `bifurcation_agroecologique` | 4 975 ETP | 4 400 (88 %) |

L'explication rapide — « travail et IFT sont corrélés » — est vraie dans la table des taux
(maraîchage 1 128-1 653 h/ha à IFT 10-15 ; canne 12,7 h/ha à IFT 2,5 ; prairie 126 h/ha à IFT 0)
mais **elle ne suffit pas** : la bissection montre que retirer le plafond d'IFT laisse P10
infaisable, tout comme retirer celui d'azote ou celui de GES. C'est la combinaison des plafonds,
plus la forme *par ferme* du plafond de main d'œuvre, qui borne l'emploi. Le point de fond
reste : dans ce modèle, **une politique environnementale ambitieuse plafonne l'emploi agricole
qu'elle peut soutenir**, et le plafond se mesure au lieu de se postuler.

## Lire la grille : métriques et dashboard (ajouté le 2026-07-31)

Construire la grille ne suffisait pas — la page de comparaison existante demande de cocher les
séries une par une, ce qui est impraticable à 110 runs, et son score composite était faussé.

### Trois corrections de méthode

**Un indicateur que la politique fixe n'est pas son résultat.** Les contraintes livrées plus
haut créent le problème : noter P8 sur « subventions » alors qu'il plafonne son propre budget à
80 M€, c'est mesurer son hypothèse. P1 gagne l'axe « dépense publique » par construction, en la
mettant à zéro. `comparison.bound_indicators(recap)` lit `recap["constraints"]` — donc marche
rétroactivement sur les runs déjà écrits — et la page avertit au lieu de laisser conclure.

**Le score composite pondérait par la finesse du découpage.** Sa moyenne min-max donnait aux
onze ratios d'autonomie, quasi colinéaires, onze fois le poids des GES ; même problème pour
chaque indicateur d'exposition et son ratio (même numérateur) et pour revenu = marge + subvention,
une somme de deux autres colonnes du même sélecteur. `balance_families=True` (défaut) normalise
le poids par famille.

**Les totaux confondent échelle et intensité.** Une politique qui cultive moins d'hectares
affiche moins d'azote sans être plus propre. D'où un bloc `intensity` : marge/ha, emploi/ha,
azote **par tonne**, IFT par tonne — et l'efficience de la dépense publique (subvention par
tonne, par ETP, par € de marge), qui est la métrique d'évaluation de politique proprement dite.
Ajout du Shannon territorial, qui n'existait qu'agrégé par région dans les CSV.

### Robustesse : une notion nouvelle, à ne pas confondre avec l'exposition

`core/reporting/robustness.py` opère sur la grille et fournit pire cas (Wald), rétention,
instabilité (CV), regret maximal (Savage) et domaine de viabilité (Starr). Trois choix assumés,
chacun changeant les conclusions : **l'infaisabilité est le pire résultat**, pas une valeur
manquante (l'écarter reviendrait à calculer les statistiques d'une politique sur les seuls
forçages qu'elle a survécus) ; **les forçages ne sont pas moyennés** par défaut, une moyenne
affirmant une distribution de probabilité que personne n'a choisie ; **le regret se mesure
contre la meilleure politique du même forçage**, ce qui est la raison d'être de la grille.

C'est autre chose que le bloc `resilience` d'un run, qui applique un choc de prix *après* le
solve à une allocation figée. Celui-ci mesure ce qu'on perd si personne ne réagit ; la grille
mesure la capacité d'adaptation dans les limites que la politique laisse. Ne jamais les
additionner dans un même score.

### Vérification de bout en bout

Une grille réelle de 2 politiques × 2 forçages sur Marie-Galante (4 solves, ~2 min) a validé la
chaîne compose → solve → recap → grille → métriques, et donne déjà le type de lecture attendu :

| | Marge brute | Emploi | Rétention emploi | Subvention / ETP | Shannon |
|---|---|---|---|---|---|
| statu quo | 7,21 M€ | 149 ETP | 89 % | 63 152 € | 0,56 |
| agroécologie | 6,83 M€ | 183 ETP | **99 %** | **37 443 €** | **0,86** |

L'agroécologie perd 5 % de marge, soutient 23 % d'emplois en plus, les tient sous le choc, et
achète chaque emploi à 41 % moins d'argent public. C'est exactement l'arbitrage que le
dispositif devait rendre lisible — sur quatre cellules, donc sans valeur de résultat, mais la
mécanique répond.

## Temps de calcul : la symétrie, pas le solveur (2026-07-31, après-midi)

Le batch était annoncé à 10-20 h. La cause n'était pas le solveur mais **une erreur de
modélisation de ma part**, et la mesure l'a montrée en dix minutes.

J'avais écrit que les 24 systèmes maraîchers paillés étaient « les systèmes agroécologiques du
jeu de données », et fait rouvrir `ma_exp_supp` par cinq politiques. Mesure faite : **les 25
variantes sont identiques au bit près à `MA_TO_CO_JA`** sur tous les paramètres lus par le
modèle (marge 20 825,25 €/ha, 75,6 kg N, IFT 10, 1 128 h/ha…), empreintes d'éligibilité
comprises. Les distinctions paillage / fertilisation / irrigation ne portent aucune donnée.

Deux conséquences, les deux avaient mordu :

* **548 000 binaires de pure symétrie** (879 162 contre 331 044). Des copies interchangeables
  sont le pire cas d'un branch-and-bound, qui explore indéfiniment des permutations
  équivalentes de la même solution.
* **La part de bio était un no-op.** Le solveur satisfaisait « 25 % de bio » en choisissant la
  copie nommée `_BIO_` d'une activité identique, à coût exactement nul. Une contrainte qui a
  l'air d'une politique et ne contraint rien.

Correction : plus aucune politique ne rouvre `ma_exp_supp`, et `bio_maraichage` se limite aux
deux systèmes réellement bio du jeu — `MA_PLBIO` et `MA_MOBIO`, **azote 0 et IFT 0**, à
3 882/3 498 €/ha contre 27 929 pour `MA_ROTA`. L'arbitrage est enfin réel.

**Mesuré après correction** (relaxation LP, territoire complet) :

| | avant | après |
|---|---|---|
| binaires (P8) | 879 162 | **331 044** |
| LP P6 / P8 / P9 / P10 | 119 / 173 / 140 / 172 s | **83 / 98 / 70 / 105 s** |
| borne P8 | 71,07 M€ | 71,07 M€ |
| borne P10 | 47,09 M€ | 46,31 M€ |

Les bornes ne bougent quasiment pas : les 25 copies n'apportaient rien, ce qui est la
confirmation directe du diagnostic. Les écarts résiduels viennent de la part de bio qui, elle,
coûte désormais quelque chose.

**Garde-fou.** `check_scenario_feasibility.py` détecte et signale tout groupe de cultures
indistinguables avant chaque batch. Le piège est double — lenteur *et* contrainte fantôme — et
rien dans le YAML ne le rendait visible.

## Warm start : chaîner à l'intérieur d'une politique

`run_scenarios.py` amorce désormais chaque run forcé avec l'allocation **non forcée de sa propre
politique** (actif par défaut ; `--no-warm-start-chain` pour couper, `--warm-start-from <run>`
pour une graine globale). Le raisonnement : un forçage change des **coefficients** (prix,
rendements, coûts, variance), pas l'ensemble faisable — l'allocation nominale reste donc
faisable pour les cellules forcées de la même politique, et c'est précisément l'incumbent que
HiGHS ne sait plus trouver seul au-delà de ~309 000 binaires.

Les exceptions existent (un forçage qui interdit des cultures ou ajoute une borne, une chute de
rendement sous un plancher de tonnage) : l'audit les attrape et le run repart à froid, en le
disant. Vérifié sur une grille réelle 2×2 — les deux cellules forcées ont accepté la graine avec
zéro violation, et le run le plus long est passé de 24,7 à 15,5 s.

Une nuance à connaître : sous un écart de 1 %, le warm start peut changer **quel** incumbent est
retenu parmi ceux qui sont dans la tolérance (écart mesuré : 0,02 % sur la marge). L'optimum
prouvé et la borne, eux, sont inchangés.

## Ce qui reste à vérifier

1. **Aucun solve MILP complet n'a été lancé.** La validation est unitaire (46 tests sans
   données) plus la relaxation LP des 10 politiques. Le premier batch réel reste à faire, et
   c'est lui seul qui dira ce que chaque politique *fait* — la LP ne dit que ce qu'aucune ne
   peut faire. Les forçages, eux, n'ont pas été passés au contrôle LP : ils ne modifient que
   des coefficients (prix, rendements, coûts, variance) sans ajouter de contrainte, sauf
   `F2_secheresse_severe` qui ajoute une interdiction de cultures irriguées et un plafond
   d'eau — c'est le seul à vérifier avant un croisement.
2. **Cinq politiques rouvrent `ma_exp_supp`** et font passer le modèle de ~309 000 à
   ~879 000 binaires. C'est agronomiquement justifié (les 24 systèmes paillés sont précisément
   les systèmes agroécologiques du jeu de données, et sans eux une « part de bio » ne dispose
   que de deux cultures) mais coûteux : à cette taille HiGHS ne trouve plus de bon *incumbent*
   seul, ce qui est exactement le régime où le warm start est devenu nécessaire le 2026-07-29.
   Ces cinq runs portent donc un `solver.args.time_limit` relevé à 3–4 h, et le batch des 10
   politiques est à compter en **10–20 h**, pas en 6–9. Le warm start reste la vraie réponse.
3. **`ges` est dans l'unité du modèle**, dont l'échelle est une question ouverte (TODO.md), d'où
   un seuil calibré en part du niveau de référence plutôt qu'en t CO2.
4. **Le plafond d'eau n'est pas un quota de prélèvement net** : le besoin est brut, la pluie
   n'est jamais déduite (les colonnes mensuelles n'existent pas — docs/04-vigilance.md). Pondéré par
   `irrigable`, il mesure la pression sur la ressource, pas un volume pompé.
