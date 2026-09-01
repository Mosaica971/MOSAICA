# 01 — Utilisation

Toutes les commandes partent de la **racine du dépôt**, avec le venv local
(PowerShell : `.venv\Scripts\python`, bash : `.venv/bin/python`). Les exemples utilisent
`python` pour rester lisibles.

---


## 1. Résoudre une fois

```bash
python main.py                          # → outputs/output_N/
python main.py --case-study guadeloupe  # explicite (défaut : $MOSAICA_CASE_STUDY, sinon guadeloupe)
```

Aucune autre option, volontairement : **tout est dans `config.yaml`**, pour qu'un run soit
reproductible depuis le `config_used.yaml` qu'il écrit.

> **Lent : 30–55 min sur le territoire complet, avec une variance énorme.** Le goulot est la
> recherche branch-and-bound, pas la construction du modèle (~15 s). Mesuré à taille constante :
> 155 s à 1 007 s, facteur 6,5. N'itérez pas là-dessus — voir §2.

**Sortie** — un dossier `outputs/output_N/` (ou `outputs/<nom>/` si le run est nommé) :

| | |
|---|---|
| `recap.json` / `recap.md` | ~50 scalaires, entrée → sortie → delta |
| `config_used.yaml` | la config exacte du run — c'est lui qui rend le run reproductible |
| `csv/` | allocation, indicateurs, calibration, `facts_<côté>.csv` (source du dashboard) |
| `plots/` | figures PNG |

---

## 2. Itérer vite : réduire le territoire

Les deux façons de ne pas attendre 40 minutes pour tester une idée.

**`zone_filter` dans `config.yaml`** — restreindre à une île, une région, des exploitations :

```yaml
zone_filter:
  include: {islands: [3]}          # Marie-Galante
  scale_territorial_bounds: true   # ⚠ INDISPENSABLE, voir ci-dessous
```

⚠ **Sans `scale_territorial_bounds: true`, un run réduit n'est pas plus petit : il est
infaisable.** Les seuils territoriaux restent énoncés pour tout le territoire — le plancher de
prairie réclame ses 6 096 ha à Marie-Galante seule. Avec le drapeau, chaque seuil absolu est mis
à l'échelle de la part de surface retenue et le run passe **d'infaisable à optimal en 5 s**.
C'est opt-in parce que réécrire un seuil change ce que le scénario dit.

**`profile_solver.py`** — même chose en ligne de commande, avec le temps par phase :

```bash
python scripts/profile_solver.py --island 1
python scripts/profile_solver.py --farm E1471 --farm E2      # options cumulables
```

Dès qu'un filtre est donné, les quotas territoriaux sont désactivés automatiquement.

---

## 3. Lancer un batch de scénarios

Un scénario est un petit jeu d'**overrides** appliqué sur `config.yaml`. Chaque run produit son
propre dossier, plus un `batch_summary_*.csv/.md` comparatif.

```bash
python scripts/run_scenarios.py                            # scenarios.yaml (liste plate)
python scripts/run_scenarios.py --scenarios <fichier> --dry-run   # résoudre sans solver
python scripts/run_scenarios.py --stop-on-error            # défaut : continuer après un échec
```

**`--dry-run` est le réflexe après toute édition de YAML.** Il résout chaque run (labels,
noms de contraintes, groupes de cultures) en quelques secondes et attrape la faute de frappe qui
coûterait une nuit.

### 3.1 Prospective : trois catalogues et un plan

| Fichier | Rôle |
|---|---|
| `scenarios_politiques.yaml` | **ce qui est décidé** — P1…P10, de la dérégulation à la bifurcation agroécologique |
| `scenarios_forcages.yaml` | **ce qui est imposé** — F0…F11, cyclone, sécheresse, chocs de prix, artificialisation |
| `scenarios_pareto.yaml` | les **balayages** ε-contrainte |
| **`plan.yaml`** | **ce qui est réellement lancé** — le seul fichier à éditer |

```yaml
# plan.yaml
scenarios:
  P1_deregulation_totale:                            # la politique seule, non forcée
  P4_statu_quo: [F0_nominal, F9_crise_systemique]     # raccourci pour `forcings:`
  P5_austerite_budgetaire: {forcings: "*"}            # tout le catalogue
  P8_transition_agroecologique:
    forcings: [F0_nominal, F9_crise_systemique]
    sweeps:
      - pareto_azote                                  # front sous P8 non forcée
      - {name: pareto_azote, forcings: [F9_crise_systemique]}   # ... et sous le choc
```

```bash
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/plan.yaml --dry-run
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/plan.yaml --no-sweeps
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/plan.yaml
```

**Compter avant de lancer** : une cellule coûte (ses forçages, ou 1 si aucun) + (les points de
chaque balayage). Le plan livré fait 29 runs. Options d'étagement :

| Option | Effet |
|---|---|
| `--no-sweeps` | laisse tomber les fronts (7 solves chacun) |
| `--policies P8,P9` | une ligne |
| `--forcings F9_crise_systemique` | une colonne |
| `--cross` | **passe outre le plan** et prend tout le produit catalogue |

Un catalogue reste lançable seul, sans plan :

```bash
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/scenarios_politiques.yaml \
       --policies P8_transition_agroecologique
```

### 3.2 Contrôle avant vol — obligatoire avant un batch long

```bash
python scripts/check_scenario_feasibility.py --scenarios case_studies/guadeloupe/plan.yaml
```

Résout la **relaxation linéaire** de chaque scénario (~2–4 min contre 30–55 min pour le MILP).
La logique est à sens unique et c'est tout l'intérêt :

- **infaisable en LP ⇒ infaisable pour de bon.** Corriger le scénario.
- faisable en LP ⇒ le MILP *peut* encore être infaisable (l'intégralité peut tuer), mais toutes
  les infaisabilités réellement rencontrées ici étaient algébriques.

Il signale aussi les **groupes de cultures symétriques** — des cultures que le modèle ne peut pas
distinguer parce qu'elles sont égales sur tous ses paramètres. C'est à la fois un désastre de
branch-and-bound et un piège de modélisation (voir [04 — Vigilance](04-vigilance.md#karusmart)).

### 3.3 Fronts de Pareto : ce que coûte le cran suivant

Un scénario dit « avec ce plafond d'azote, la marge vaut X ». Il ne dit pas ce que coûte le kilo
suivant. Un front le dit : on fixe l'objectif, on serre un indicateur cran par cran, et la courbe
obtenue **est** l'arbitrage.

```yaml
# scenarios_pareto.yaml
sweeps:
  - name: pareto_azote
    enable: [azote_max]
    matrix:
      args:azote_max.threshold: [1930903, 1834358, ..., 1061997]   # 7 points = 7 solves
```

Trois choses à savoir :

1. **`args:<label>.<argument>`** vise l'argument de la contrainte portant ce label — un seuil de
   contrainte ne vit à aucun chemin pointé de la config. C'est pourquoi `azote_max` et
   `emploi_min` existent en `enable: false` dans `config.yaml` : ce sont des coquilles vides qui
   donnent prise au balayage.
2. **Les points ne sortent pas dans l'ordre écrit.** Ils sont réordonnés du seuil le plus *serré*
   vers le plus lâche, parce que la faisabilité n'implique que dans ce sens — une allocation
   faisable à 55 % d'azote l'est encore à 100 %, jamais l'inverse. Chaque point amorce ainsi le
   suivant : 1 solve à froid au lieu de 7.
3. **Un point dominé signale presque toujours un solve non convergé, pas une découverte.** Serrer
   une contrainte ne peut pas améliorer l'objectif.

Le front donne le **coût marginal sur tout l'intervalle**, là où le prix dual
(`core/solve/shadow_prices.py`) n'en donne que la pente locale. Un écart important entre les deux
signifie que le dual est lu hors de son voisinage de validité.

---

## 4. Accélérer : le *warm start*

Au-delà de ~309 000 variables binaires, HiGHS ne trouve plus de bonne solution initiale seul.
Lui en fournir une change **uniquement la vitesse à laquelle l'optimum est prouvé**, jamais
l'optimum. Mesuré : **720 s à froid, 209 s à chaud**, objectif identique.

```yaml
# config.yaml
solver:
  warm_start_from: outputs/calib_retenu
```

Le départ est **audité** contre les contraintes du modèle avant le solve. S'il en viole une, le
run le dit et repart à froid — parce que **HiGHS jette un départ infaisable en silence**, et
qu'un run paraîtrait sinon réamorcé tout en se comportant comme à froid.

Pour amorcer un run qui **ajoute** une contrainte, réparer d'abord l'allocation :

```bash
python scripts/repair_allocation.py outputs/output_3 \
       --crops AG,VE_BTGT,VE_PLUIE --min-surface 335 --out outputs/_warmstart_plu
```

Dans un batch, le chaînage est **automatique** : trois graines essayées du plus proche au plus
lointain (point précédent du même front → allocation nominale de la politique → graine globale
`--warm-start-from`). `--no-warm-start-chain` coupe.

---

## 5. Inspecter les données

```bash
python scripts/display_datasets.py     # tous les sets/paramètres/scalaires produits par build_dataset
```

---

## 6. Calibration : le modèle colle-t-il à la réalité ?

Trois outils, dans cet ordre.

```bash
python scripts/build_reference_state.py            # → outputs/reference_2017/ (~5 s, aucun solve)
python scripts/compare_to_reference.py outputs/calib_retenu
python scripts/evaluate_calibration.py outputs/calib_retenu   # ~7 s, --all pour tous les runs
python scripts/pad_all_scales.py outputs/calib_retenu         # PAD aux cinq échelles
```

1. **`build_reference_state.py`** construit la situation observée 2017, indépendante de tout run.
   **Lire son `REFERENCE.md` avant d'interpréter le moindre écart** : il dit surtout ce que la
   référence *ne peut pas* dire. À relancer si `config.yaml` change `year`, `zone_filter` ou
   `baseline_representative_crops` — et seulement dans ces cas.
2. **`compare_to_reference.py`** met un run en face et écrit `comparaison_reference.md` dedans.
3. **`evaluate_calibration.py`** donne le détail par culture, sous-région et exploitation. Les
   nouveaux runs le font déjà tout seuls dans `generate_report`.

Méthode et seuils : Chopin et al. (2015) §2.6 — **PAD < 15 %** au territoire, **< 20 %** par
sous-région, **80 %** des exploitations dans leur type d'origine.

⚠ **Comparer nos chiffres aux siens demande des précautions** — l'article publie son PAD *par
culture* et jamais agrégé, compte les parcelles non cultivées, et son année de base est 2010.
Détail dans [04 — Vigilance](04-vigilance.md#calibration).

### Runs de référence

Trois séries servent de points fixes, déclarées et **gardées** dans `references.yaml` :

| Rôle | Dossier | Ce qu'il dit |
|---|---|---|
| Observé 2017 (RPG) | `outputs/calib_retenu/` (côté entrée) | l'assolement réellement déclaré |
| Calib parité GAMS | `outputs/calib_gams_parite/` | PAD 48,4 %, types 64,0 % — le CALIB sans déviation |
| Calib retenu | `outputs/calib_retenu/` | types 86,9 %, parcelles 67,6 %, surface 77,1 % |

```bash
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/scenarios_calibration.yaml
python scripts/check_references.py --verbose      # garde-fou, ~0 s, aucun solve
```

`check_references.py` est le **seul garde-fou du dépôt sur le solve** — les tests sont sans
données par choix et `golden_snapshot` s'arrête avant la résolution. Tolérance 5 %, choisie
au-dessus du bruit de branch-and-bound mesuré (0,15 point de PAD sur trois graines HiGHS).

---

## 7. Dashboard (lecture seule)

```bash
streamlit run apps/dashboard/app.py
```

Il ne résout rien et n'écrit rien : il ouvre des dossiers `outputs/`.

| Page | Ce qu'elle répond |
|---|---|
| **Synthèse** (accueil) | en un écran : solve convergé ? les 4 verdicts de calibration ? où est l'écart (classé en **hectares**, pas en PAD) ? et **les pièges de lecture propres à ce run** |
| **Détail du run** | un run en entier : recap, indicateurs entrée/sortie, figures |
| **Comparaison** | plusieurs runs côte à côte + diff de config + diff d'allocation + score composite |
| **Calibration** | un run face à l'observé : PAD par culture, heatmap région × culture, matrice de confusion des types |
| **Prospective** | une grille politique × forçage : carte de chaleur, nuage performance-robustesse, tornado, robustesse |
| **Carte** | le parcellaire observé, simulé, et les changements. Demande `data/gis/` |
| **Pareto** | la courbe d'arbitrage et le coût marginal |

**Les deux diffs se lisent dans cet ordre** : le diff de **configuration** dit ce qui a été
*demandé* (quelles contraintes, quels seuils) ; le diff d'**allocation** dit ce que ça a
*déplacé* (matrice de transition, flux dominants). Le premier ne dit jamais ce que l'écart a
coûté — une contrainte qui ne mord pas ne change aucun résultat.

---

## 8. Tests et garde-fous

```bash
python -m pytest tests/test_readers.py    # un fichier — à privilégier en itération
python -m pytest                          # suite complète — LENTE (~29 min)
python scripts/golden_snapshot.py --write # enregistrer le comportement actuel
python scripts/golden_snapshot.py --check # détecter toute dérive numérique
python scripts/check_references.py        # les runs de référence n'ont pas bougé
```

La plupart des tests sont **sans données** par choix (config minuscule construite à la main),
donc rapides. Quelques-uns construisent le vrai dataset et résolvent : ce sont eux les 29 minutes.

`golden_snapshot` construit le dataset réel et tous les blocs d'indicateurs sur une allocation
réelle (~7 s, **aucun solve**, donc exactement reproductible) et sérialise ~681 sommes de
contrôle. **À lancer après toute retouche de `pipeline/`, `domain/`, `core/data/` ou
`reporting/indicators.py`** : il attrape la dérive numérique que les tests sans données ne
peuvent pas voir.

---

## 9. Aide-mémoire

| Je veux | Commande |
|---|---|
| un run complet | `python main.py` |
| itérer sans attendre | `zone_filter` + `scale_territorial_bounds: true` |
| valider un YAML de scénarios | `run_scenarios.py --scenarios <f> --dry-run` |
| savoir si un batch est faisable | `check_scenario_feasibility.py --scenarios <f>` |
| lancer le plan prospectif | `run_scenarios.py --scenarios case_studies/guadeloupe/plan.yaml` |
| noter un run contre 2017 | `evaluate_calibration.py outputs/<run>` |
| vérifier que rien n'a dérivé | `golden_snapshot.py --check` puis `check_references.py` |
| regarder les résultats | `streamlit run apps/dashboard/app.py` |
