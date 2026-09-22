# Suite du stage — couplage MAELIA, portage vers le SI, passage à l'anglais, tableau d'état

Date : 2026-09-22. Statut : **réflexion, rien n'est implémenté**. Ce document range les cinq
chantiers annoncés après la soutenance, propose un ordre, et isole les décisions qui
reviennent à Clément ou aux encadrants. Il ne tranche rien de ce qui dépend de MAELIA
lui-même : la formation n'a pas eu lieu, et tout ce qui est dit ici sur MAELIA est **à
vérifier** contre sa documentation.

---

## 0. Ordre proposé, et pourquoi

| # | chantier | pourquoi à ce rang |
|---|---|---|
| A | **Tableau d'état** (indicateurs × échelles, contraintes × cultures, paramètres à plusieurs valeurs, statut des implémentations) | Rapide, et c'est déjà le cahier des charges du couplage : la table des paramètres sourcés liste exactement ce que MAELIA remplacera. |
| B | **Passage à l'anglais + revue des commentaires** | Avant d'écrire les interfaces MAELIA. Sinon on renomme deux fois. |
| C | **Catalogue de données, niveaux d'accès, formats d'échange** | Le contrat de données avec MAELIA et avec le SI est le même objet. Le définir une fois. |
| D | **MAELIA → MOSAICA** : rendements et ITK simulés | Demande C (format) et un changement localisé du modèle (§ 4). |
| E | **MOSAICA → MAELIA** : l'assolement testé au pas journalier | Demande D (même référentiel de parcelles et de cultures) et une décision sur la dynamique (§ 5). |

A et B peuvent commencer tout de suite. C, D et E attendent la formation MAELIA pour
leurs détails, pas pour leur cadrage.

---

## 1. Chantier A — le tableau d'état

**Principe : générer ce qui est dérivable du code, écrire à la main seulement ce qui ne l'est
pas.** Le dépôt a déjà prouvé qu'un chiffre saisi à la main dérive (le CV de 64 % écrasé, les
duaux introuvables, les 482 items du corpus au lieu de 491). Un tableau d'état écrit à la main
serait faux dans un mois.

Rendu : une page **État** du dashboard **et** un export Markdown (`docs/status/`), les deux
produits par un même script (`scripts/build_status_board.py`), aucun solve.

### A.1 — Indicateurs × niveaux d'agrégation — *généré*

Constat : aujourd'hui chaque indicateur a été agrégé aux échelles dont on avait besoin à ce
moment-là. `etp` existe par exploitation, île et région ; Shannon par île et région ; azote,
GES, IFT au territoire et par culture ; `facts_output.csv` s'arrête à culture × région × île.
Aucune commune, aucune zone arbitraire.

Proposition, qui transforme le tableau lui-même : **une table longue par parcelle**
(`plot, farm, crop, indicateur…`) calculée une fois, et une seule fonction d'agrégation par
clé de zone. Une zone arbitraire n'est alors qu'un fichier `plot → zone` (ou une couche SIG).
Tout indicateur *additif* (surface, production, marge, heures, azote, eau…) devient disponible
à **toutes** les échelles par construction, et les ratios s'obtiennent en rapport de sommes.

Le tableau ne montre plus alors que les vraies exceptions, qui sont l'information utile :

| classe d'indicateur | exemples | agrégation |
|---|---|---|
| additif | surface, production, marge brute, heures, azote, GES, eau, carbone | somme, toutes échelles |
| ratio d'additifs | marge/ha, azote/t, subvention/ETP, autonomie alimentaire | rapport de sommes, toutes échelles |
| non additif | Shannon, HHI, Gini, PAD, moyenne Rpest | **redéfini par échelle**, à déclarer une à une |
| lié à l'observé | PAD, matrice de confusion, correspondance parcellaire | seulement aux 12 groupes RPG (pas de sous-culture) |

Chaque indicateur se déclare dans un registre (nom, unité, famille, classe ci-dessus, source
du coefficient), sur le modèle de `@register_constraint`. Le tableau se lit dans le registre ;
un test vérifie que tout ce qui est écrit dans le recap y figure.

### A.2 — Contraintes × cultures — *généré*

Résoudre `config.yaml` (entrées `enable: true`) sur le vrai dataset (~7 s) et, pour chaque
entrée, lister les cultures qu'elle touche. Lignes : les contraintes par `label` (avec
l'équation GAMS d'origine et son statut : portée / désactivée / déviation assumée). Colonnes :
les 12 groupes RPG, dépliables en 84 cultures fines. Cellule : `≤`, `≥`, `=`, `interdit`,
`éligibilité (n parcelles retirées)`.

Deuxième vue du même calcul : pour une culture, toutes les règles qui la concernent. C'est la
question qu'on pose réellement (« pourquoi il n'y a pas de melon ? »).

### A.3 — Paramètres à plusieurs valeurs plausibles — *écrit à la main*, dans un YAML

`case_studies/guadeloupe/parameter_choices.yaml` : pour chaque paramètre, les valeurs
candidates avec leur source, la valeur retenue, la raison, la date, l'effet mesuré, et le
renvoi vers l'entrée de `04-vigilance.md`. Le script vérifie que la valeur « retenue » est bien
celle de `config.yaml` — c'est ce qui empêche le YAML de dériver.

Amorce, tirée de ce que le dépôt documente déjà :

| paramètre | candidats (source) | retenu | raison |
|---|---|---|---|
| plafond plantain `bc_quota_max` | 4 650 t (Éq. 6 de l'article) · 6 440 t (auteur du GAMS) · 40 000 t (GAMS, inactif) | 6 440 t | palier plat 4 650-9 240 t ; chiffre de 2010 |
| plancher prairie `pn_prod_min` | 6 096 ha (GAMS) · 8 341 ha (Agreste × couverture 87 %) · 9 595 ha (Agreste 2017) | 6 096 ha | paramètre GAMS, 27 % sous l'exogène |
| aversion au risque `AVERS` | Table 2 publiée · recalibrée § 2.5 | publiée | recalibrée : PAD 40 % mais coefficients absurdes |
| rendements `Rdt_Cult` | Table 1 de l'article · Agreste (1 à 4× plus bas) · **MAELIA** | Table 1 | parité GAMS — c'est le paramètre que D remplace |
| plancher arboricole | 200 ha · 335 ha (Agreste × 87 %) | non adopté | solve intraitable |
| couche chlordécone | `RISQUE_CLD` (agrégé au min) · `CLD_REEL` (au max) | `RISQUE_CLD` | à poser aux encadrants (`PERSP-62`) |
| année économique `data.year` | 2017 … 2022, `init`, `calib` | 2017 | seule année structurelle disponible |
| scénario ITK `data.scenario` | `RESTIT` · `SMART` | `RESTIT` | reproduit le comportement historique |
| écart MIP `mip_rel_gap` | défaut HiGHS · 1 % | 1 % | Markowitz intraitable au défaut (> 37 h → 175 s) |
| heures par ETP | 1 607 h | 1 607 h | durée légale annuelle |

### A.4 — Statut des implémentations — *écrit à la main*, dans un YAML

`docs/status/roadmap.yaml`, un item par ligne : `id`, titre, statut, spec, date, ce qui
bloque. Statuts : **fait · en cours · à faire · à actualiser · proposition · abandonné**
(« abandonné » porte sa raison, pour ne pas le rouvrir).

`docs/TODO.md` fait aujourd'hui 430 lignes dont l'essentiel est *livré* : il mélange le
journal et la liste. Proposition : le YAML devient la liste, le TODO est généré depuis lui
(ou supprimé), et les récits de livraison restent dans les specs, où ils sont déjà.

---

## 2. Chantier B — passage à l'anglais et revue des commentaires

### Ce qui est déjà en anglais

Mesuré aujourd'hui sur `core/`, `case_studies/`, `apps/`, `scripts/` (82 fichiers, 11 800
lignes) : **12 lignes de commentaire en français sur ~1 400**, et **41 noms de fonction sur
451** portent un terme français. Le code est donc déjà anglais à ~90 % ; le français est
concentré dans six endroits, par ordre de coût à changer :

| où | exemples | risque |
|---|---|---|
| termes métier dans les noms | `azote`, `phosphore`, `potasse`, `ges`, `etp`, `cld`, `mae`, suffixe `_cult` | faible — refactor mécanique |
| labels de config | `pn_prod_min`, `azote_max`, `emploi_min`, `friche_lock` | moyen — les scénarios et `plan.yaml` les référencent |
| noms de fichiers | `scenarios_politiques.yaml`, `scenarios_forcages.yaml`, `plan_etape_*.yaml`, `2_Comparaison.py` | moyen |
| **clés du recap et noms de CSV** | `total_azote`, `azote_per_ha`, `etp_by_region_output.csv` | **élevé** — format persisté, lu par le dashboard et `build_chiffres.py` sur les runs déjà écrits |
| chaînes du dashboard | titres, légendes | faible |
| documentation | `docs/`, `TODO.md`, specs | à décider (question 1) |

### Règles proposées

1. **Un glossaire fixe la traduction une fois** (`docs/glossary.md`) : azote → nitrogen,
   GES → GHG, ETP → FTE, IFT → TFI (treatment frequency index), MAE → AECM, CLD → chlordecone,
   ITK → crop management sequence (ou garder `itk`, défini une fois). PAD reste PAD (Chopin
   l'emploie en anglais).
2. **Les identifiants GAMS ne se traduisent pas** quand ils désignent un objet GAMS
   (`Eq_BC_QUOTA_MAX`, `Rdt_Cult`, colonnes `ALTI_MIN`, `PENTE`) : ce sont les ancres de parité.
   Le nom anglais vit dans le Python, le nom GAMS dans la docstring ou le `label`.
3. **Le recap est un format versionné.** Ajouter `recap_version`, et une table d'alias à la
   lecture (`total_azote` → `total_nitrogen`) plutôt que réécrire les `outputs/` existants.
   Le mémoire est clos, mais `build_chiffres.py` doit continuer de tourner.
4. **Un package par commit**, dans l'ordre : glossaire → `core/` → `domain/` → `reporting/` +
   recap → config et scénarios → dashboard → docs. Garde-fous à chaque pas :
   `golden_snapshot.py --check` (les **valeurs** ne doivent pas bouger ; ses clés passent par
   la table d'alias), `check_references.py`, et les tests du package touché.
5. **Revue des commentaires dans le même passage**, puisque chaque ligne est relue de toute
   façon. Grille : un commentaire dit *pourquoi*, pas *quoi* ; il donne l'unité ; il cite la
   ligne GAMS quand il en porte une ; **il ne contient pas de chiffre mesuré** (un chiffre dans
   un commentaire se périme sans bruit — c'est la leçon de `SolveHistory`) mais renvoie à
   l'entrée de vigilance qui le tient.

Coût estimé : une à deux semaines de travail assisté, dominées par le recap et la config, pas
par le code.

---

## 3. Chantier C — données : catalogue, niveaux d'accès, formats

### Le prérequis : classer avant de protéger

On ne peut pas filtrer par niveau d'accréditation des données dont personne n'a écrit le
niveau. Premier livrable : un **catalogue** (`data/catalogue.yaml`, versionné, lui, même si
`data/` ne l'est pas) — une entrée par table et, si besoin, par colonne : source, licence,
propriétaire, date, résolution spatiale, **niveau de sensibilité**.

### Niveaux proposés (à valider avec INRAE et son DPO)

| niveau | contenu | exemples dans le dépôt |
|---|---|---|
| **0 — public** | agrégats ≥ commune, sources déjà publiées | Agreste publié, Tables 1-2 de l'article, résultats territoriaux |
| **1 — partenaire** | agrégats par sous-région, type d'exploitation, culture ; résultats de scénarios | grille politique × forçage, fronts de Pareto |
| **2 — restreint** | tout ce qui est à la parcelle ou à l'exploitation | `allocation_output.csv`, `revenue_by_farm.csv`, la page Carte, la typologie |

Deux points qui fixent la frontière et qu'il faut confirmer, pas supposer :

- **Le lien parcelle ↔ exploitation fait la donnée personnelle.** Une parcelle seule est
  publique (le RPG anonymisé l'est) ; la même parcelle rattachée à une exploitation, avec son
  revenu, identifie un exploitant (RGPD).
- **Le secret statistique** s'applique aux agrégats issus de la statistique agricole : la
  règle usuelle (au moins 3 unités, aucune ne pesant plus de 85 %) est à confirmer auprès du
  producteur de la donnée. Un agrégat communal de niveau 0 peut la violer dans une petite
  commune.

### Où vit le contrôle d'accès

**Pas dans MOSAICA.** L'authentification et les rôles appartiennent au SI de MAELIA (base,
vues par niveau, comptes). Le rôle de MOSAICA est double : (a) **étiqueter** chaque sortie de
run avec son niveau (un dossier `outputs/output_N/` est aujourd'hui de niveau 2 en bloc), et
(b) fournir un **export par niveau** — `export --level 1` qui agrège et supprime ce qui
dépasse. Le dashboard actuel est un outil de niveau 2 ; ce n'est pas un défaut, mais c'est à
écrire.

### Formats : un schéma, deux produits

Une seule description par table (types, unités, bornes, clés étrangères, niveau) — le format
Frictionless Table Schema existe pour ça et évite d'inventer le sien. Elle génère :

1. **le classeur Excel à remplir**, façon bilan carbone : une feuille *Lisez-moi*, une feuille
   par table, une ligne d'unités, des listes déroulantes tirées des référentiels (codes
   cultures, communes), cellules à saisir en jaune, cellules calculées verrouillées en gris,
   une ligne d'exemple, et une feuille *Sources* où chaque coefficient porte sa référence ;
2. **le validateur** qui relit le classeur rempli, vérifie types, bornes, unités et clés, et
   produit soit un rapport d'erreurs lisible, soit les tables prêtes pour le SI.

L'item « classeur Excel type bilan carbone » du `TODO.md` se fond dans ce chantier.

Trois sens de circulation à distinguer : **ajouter** (une nouvelle version de table, une
nouvelle année, un nouveau territoire), **mobiliser** (lire pour un run), **exporter** (vers un
partenaire, filtré par niveau). Chaque version de table est immuable, datée et hachée ; le
recap enregistre les empreintes des tables qu'il a lues, comme il enregistre déjà `year` et
`scenario`.

---

## 4. Chantier D — MAELIA → MOSAICA : rendements et ITK simulés

### Ce qui change dans MOSAICA — peu, mais à un endroit précis

Aujourd'hui **la marge et tous les taux sont indexés par culture seule** :
`crop_margin_per_ha[crop]` dans l'objectif (`core/model/objectives.py`), `Rdt_Cult` par
culture, `crop_indicator_rates` par culture. Un rendement simulé dépend du sol et du climat,
donc il est indexé par **(unité de simulation, culture, ITK)**.

Il faut un canal de coefficients **par couple** dans `ModelInputs` —
`pair_margin_per_ha[(plot, crop)]`, avec repli sur la valeur par culture — et la même chose
pour les taux d'indicateurs. La taille du MILP ne change pas (mêmes variables `Y`), l'objectif
reste linéaire. C'est testable sans données, dans le style des tests actuels.

### Points à tenir

- **Pré-calcul, jamais MAELIA dans la boucle** (`PERSP-D`) : MAELIA tourne hors ligne sur la
  grille (unité × culture × ITK × années climatiques) et produit une table. Ce qui change
  n'est pas le modèle, c'est la provenance de `Rdt_Cult`.
- **L'unité de simulation n'est pas forcément la parcelle.** Une unité pédoclimatique (type de
  sol × classe de pluviométrie × classe d'altitude) borne le coût de MAELIA ; toutes les
  parcelles d'une unité héritent de son rendement.
- **L'ITK est déjà une dimension de MOSAICA** : les 84 cultures fines sont des couples culture ×
  variante d'itinéraire (`CS_MG_NISM`…). Les ITK de MAELIA doivent se projeter sur ces codes ou
  en créer de nouveaux. **Piège B.3** : deux variantes égales sur tous les paramètres lus
  rendent le branch-and-bound inutilisable. `check_scenario_feasibility.py` les détecte déjà.
- **La variance vient avec.** N années climatiques donnent la moyenne *et* la variance du
  rendement par couple — elles remplaceraient `Var_Rdt_Cult` (aujourd'hui figée sur `init`,
  par culture) dans l'objectif de Markowitz. Bénéfice direct pour la résilience.
- **La parité reste reproductible** : un interrupteur `data.yield_source: gams_table | maelia`,
  et `check_references.py` reste branché sur `gams_table`.
- **Conséquence sur la calibration, à anticiper** : les rendements actuels valent 1 à 4× ceux
  du territoire (C.1), et les plafonds de marché (plantain 6 440 t) compensaient en partie ce
  surplus. Des rendements simulés plus réalistes peuvent rendre ces plafonds inutiles ou
  mal placés : **une recalibration est à prévoir**, pas un simple remplacement de colonne.

### Contrat d'interface (brouillon)

Table `simulated_yields` : `unit_id, crop_code, itk_code, climate_series, year,
yield_t_ha, [water_use_mm, n_uptake_kg_ha, labour_h_ha…], maelia_version, maelia_run_id`.
Plus une table `unit_of_plot` (`plot_id → unit_id`).

### À vérifier pendant la formation

Ce que MAELIA simule réellement et avec quel modèle de culture (d'après ce que j'en sais,
MAELIA tourne sur la plateforme GAMA et s'appuie sur un modèle de culture simplifié de type
AqYield — **à confirmer**) ; **si les cultures tropicales** (canne, banane, igname, plantain,
ananas, maraîchage tropical) **y sont paramétrées**, ce qui peut être à lui seul le plus gros
coût du chantier ; les formats d'entrée et de sortie ; la licence et l'accès au SI.

---

## 5. Chantier E — MOSAICA → MAELIA : l'assolement testé au pas journalier

L'idée — l'optimisation fixe des contraintes fortes et grossières, le multi-agents révèle les
contraintes implicites et fines — est la bonne division du travail. Quatre points la rendent
opérationnelle.

### 5.1 — Le référentiel de parcelles est le premier obstacle

Les parcelles de MOSAICA sont des identifiants **synthétiques** `P1..Pn`. La jointure au RPG
se fait par signature d'exploitation à **99,4 %**, et **~1 557 parcelles ont une jumelle
interchangeable** (`04-vigilance.md` F.1). MAELIA a besoin de géométries réelles. Il faut
donc : une règle déterministe et documentée pour les jumelles (elles sont indiscernables pour
MOSAICA, donc l'arbitraire est sans effet sur l'optimum, mais pas forcément sur MAELIA qui
voit la géométrie), et un traitement explicite des 0,6 % non joints. Si le SI de MAELIA
porte le RPG avec ses vrais identifiants, **le mieux est de reconstruire le jeu parcellaire
de MOSAICA depuis le SI** plutôt que de continuer à joindre après coup.

### 5.2 — Statique contre dynamique : une décision à prendre avant de coder

MOSAICA produit un assolement d'**une** année ; MAELIA simule des années avec des successions.
Trois options :

| option | ce que MAELIA reçoit | défaut |
|---|---|---|
| a | le même assolement chaque année | irréaliste pour les rotations (maraîchage, cycles de canne de 5-7 ans) |
| b | l'assolement MOSAICA en année 1, puis ses propres règles | on ne teste plus que la première année |
| c | des parts de surface cibles par exploitation, les rotations restant à MAELIA | le plus réaliste, mais MAELIA décide alors une partie de l'assolement |

Cette décision rejoint le **modèle multi-périodes** du `TODO.md`, cadré et non commencé.

### 5.3 — Forcer l'exécution, ne pas laisser re-décider

Si les agents de MAELIA gardent leurs règles de choix d'assolement, on compare deux modèles de
décision au lieu d'en tester un. Pour le test, l'agent doit **exécuter** le plan : seules les
décisions tactiques (dates de semis, déclenchement de l'irrigation, ordre des chantiers)
restent libres. À vérifier : que MAELIA permet d'imposer un assolement.

### 5.4 — Définir ce qu'on mesure avant de lancer

Une liste d'indicateurs d'écart, écrite avant le premier run, faute de quoi on lira ce qui
arrange :

| contrainte implicite | indicateur MAELIA | ce que MOSAICA en sait déjà |
|---|---|---|
| main-d'œuvre | pics hebdomadaires par exploitation vs disponible | seulement un plafond **annuel** (`farm_labor_hours_max`) |
| matériel | conflits d'usage (tracteur demandé sur deux chantiers dans la même fenêtre) | rien |
| eau | jours de stress hydrique, demande d'irrigation vs ressource | un besoin **mensuel** (`water_need_peak_month_m3`) — comparable directement |
| azote | jours de carence, reliquats | un total annuel par culture |
| rendement | réalisé simulé vs prévu par l'optimisation | le rendement tabulé |
| marge | réalisée vs prévue | la marge du solve |

### 5.5 — Une passe d'abord, une boucle ensuite

Commencer par une **évaluation à sens unique** : l'assolement optimisé, simulé, et le tableau
d'écarts. Seulement si les écarts sont systématiques, traduire ce que MAELIA révèle en
contraintes MOSAICA (plafond de main-d'œuvre mensuel, rendements réalisés) et re-résoudre avec
warm start. Une telle boucle **ne converge pas forcément** (elle peut osciller) : critère
d'arrêt fixé d'avance, trois itérations au plus, et le coût se chiffre — 30-60 min par solve
MOSAICA plus la durée d'un run journalier MAELIA, inconnue à ce jour.

---

## 6. Questions à trancher

**Pour Clément**

1. **Portée de l'anglais** : le code seulement, ou aussi la config, le dashboard et `docs/` ?
   (Le mémoire et le corpus restent en français, ils sont clos.)
2. **`TODO.md`** : le remplacer par `roadmap.yaml`, ou le garder à côté ?
3. **Contrainte « aucun solve neuf »** : elle valait pour la rédaction du mémoire. Est-elle
   levée pour la suite du stage ? (Le couplage D implique une recalibration, donc des solves.)

**Pour la formation MAELIA / les encadrants**

4. Cultures tropicales paramétrées ou non ; modèle de culture utilisé ; formats d'entrée et de
   sortie ; possibilité d'imposer un assolement.
5. Le SI porte-t-il le RPG avec ses vrais identifiants ? (Décide § 5.1.)
6. Qui valide les niveaux d'accès (DPO INRAE, conventions avec les fournisseurs de données) ?
7. Évaluation à sens unique, ou boucle itérée — et le budget de calcul correspondant.
