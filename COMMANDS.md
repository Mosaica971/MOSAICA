# Commandes du dépôt MOSAICA (Python/Pyomo)

Aide-mémoire des commandes disponibles et de leurs arguments. Tout part de la **racine du
dépôt**, avec le venv `.venv/`. Sous Windows PowerShell, remplace `.venv/Scripts/python` par
`.venv\Scripts\python` si besoin.

> Rappel : les données (`data/`), les sorties (`outputs/`) et l'historique de solve ne sont
> pas versionnés. Le comportement est piloté par `case_studies/guadeloupe/config.yaml`.

---

## 1. Résolution complète — `main.py`

Construit les données → le modèle → résout (HiGHS) → écrit un dossier `outputs/output_N/`.

```bash
.venv/Scripts/python main.py
```

- **Aucun argument CLI** : tout se règle dans `config.yaml` (voir §6).
- **Lent** (~30–55 min sur le vrai territoire ; le goulot est la traduction Pyomo→HiGHS, pas
  le solveur). À réserver à une vraie exécution ; pour itérer, utiliser les tests ciblés (§3)
  ou `profile_solver.py` (§5) sur une sous-zone.
- Chaque exécution crée un **nouveau** dossier numéroté `outputs/output_N/` (voir §7 pour le
  contenu).

---

## 2. Dashboard de visualisation — Streamlit

Visualiseur **lecture seule** sur les dossiers `outputs/output_N/` (ne relance jamais de
solve, n'écrit rien).

```bash
streamlit run case_studies/guadeloupe/dashboard/app.py
```

Deux pages (sélecteur dans la barre latérale Streamlit) :

- **Page d'accueil (`app.py`)** — vue **d'un seul run** : recap, indicateurs entrée/sortie,
  figures par culture/région, revenu net & coût main d'œuvre. Sélecteur de run en haut.
- **Page « Comparaison »** (`pages/2_Comparaison.py`) — compare **plusieurs runs côte à côte** :
  - Cocher/décocher des **séries** ; une série = **(run × côté)** — un même run fournit une
    série « entrée » et une série « sortie ».
  - **Barres comparées** : abscisse ∈ {culture, sous-culture, région, île} × mesure ∈
    {surface, production, revenu, marge, subvention, ventes, coût MO, heures, ETP} ; option
    d'**empilement** par une 2ᵉ dimension. La **canne (CS/CF)** est colorée par sa combinaison
    irrigation×récolte (3 modalités réelles), les autres cultures par sous-culture. Axe **y log
    à échelle figée** (mode groupé uniquement ; l'empilé reste linéaire).
  - **Profil de développement** : coordonnées parallèles normalisées (Gini, revenu net, ETP,
    production…), une ligne par série.
  - Les runs antérieurs à la table de faits (`csv/facts_*.csv`) sont ignorés proprement.

---

## 3. Tests — pytest

Config dans `pyproject.toml` (`pythonpath = ["."]`, imports depuis la racine).

```bash
.venv/Scripts/python -m pytest                                   # suite complète — LENTE (~29 min)
.venv/Scripts/python -m pytest tests/test_readers.py             # un fichier
.venv/Scripts/python -m pytest tests/test_main.py                # un fichier
.venv/Scripts/python -m pytest tests/test_guadeloupe_constraints.py::test_cs_gfa_minimum_share_constraint_only_applies_to_farms_with_gfa_surface   # un test
.venv/Scripts/python -m pytest -q                                # sortie condensée
.venv/Scripts/python -m pytest --collect-only -q                 # lister sans exécuter
```

- **Suite complète lente** (~29 min : quelques tests construisent le vrai dataset et résolvent
  en HiGHS). En itération, ne lancer que le(s) fichier(s) concerné(s) ; garder la suite
  complète pour la vérification finale.
- La plupart des tests sont **sans données** (petits configs et dicts à la main), donc rapides.

---

## 4. Inspection du dataset — `scripts/display_datasets.py`

Affiche le registre du dataset (chaque set/paramètre/scalaire avec catégorie, type, taille) —
sanity check de ce que produit `build_dataset` avec le `config.yaml` courant.

```bash
.venv/Scripts/python scripts/display_datasets.py
```

- **Aucun argument.** Lit `config.yaml` (donc respecte `zone_filter`, `data.year/scenario`…).

---

## 5. Profilage du solveur — `scripts/profile_solver.py`

Chronomètre séparément les phases **données / construction du modèle / solve** sur un
**sous-ensemble** (`zone_filter`), pour travailler la perf sans solve plein-territoire. Non
exécuté par la suite de tests.

```bash
.venv/Scripts/python scripts/profile_solver.py --island 1
.venv/Scripts/python scripts/profile_solver.py --farm E1471 --farm E2
.venv/Scripts/python scripts/profile_solver.py --region 3 --plot P12345
```

Arguments (cumulables, répéter l'option pour plusieurs valeurs) :

| Option      | Sens                         | Exemple            |
|-------------|------------------------------|--------------------|
| `--island`  | garder ces îles (entier)     | `--island 1`       |
| `--region`  | garder ces régions           | `--region 3`       |
| `--farm`    | garder ces exploitations     | `--farm E1471`     |
| `--plot`    | garder ces parcelles         | `--plot P12345`    |

- Dès qu'un filtre est fourni, les contraintes `territory_production_bound` (quotas
  plein-territoire, infaisables sur un sous-ensemble) sont **automatiquement désactivées**.
- Sans aucun argument : tourne sur le territoire entier (lent).

---

## 6. Réglages clés de `config.yaml`

`case_studies/guadeloupe/config.yaml` pilote tout. Principaux leviers :

- **`data`** : `year` (colonne des séries économiques : `2017`–`2022`, ou `init`/`calib` ;
  n'agit que sur l'économie, la structure reste 2017) et `scenario` (`RESTIT` | `SMART`).
- **`labor`** : `hours_per_etp` (heures/an par ETP, défaut 1607) et `cost_per_hour` (€/h ;
  0 = MO non valorisée). Servent aux indicateurs emploi/coût MO/revenu net (reporting
  uniquement — n'affectent pas l'optimum).
- **`zone_filter`** (optionnel, désactivé par défaut) : `include`/`exclude` avec
  `islands`/`regions`/`farms`/`plots`, pour restreindre le territoire. ⚠ ne redimensionne pas
  les quotas territoriaux — un sous-ensemble peut devenir infaisable (cf. `VIGILANCE.md`).
- **`constraints`** / **`objectives`** : listes activées via `enable: true`. Exactement **un**
  objectif doit être actif. Certaines entrées sont désactivées volontairement (raisons en
  commentaire — lire avant de basculer un `enable`).
- **`solver`** : `name` (`appsi_highs`) et `args` (options HiGHS).

---

## 7. Contenu d'un dossier `outputs/output_N/`

- `recap.json` / `recap.md` — synthèse (objectif, contraintes, entrée→sortie→delta :
  production, subvention, produit brut, coût variable, marge brute, coût MO, revenu net, ETP).
- `config_used.yaml` — copie du config ayant produit le run.
- `csv/` — **tous les CSV** : `facts_<côté>.csv` (table tidy culture×région, base du dashboard
  comparatif), `allocation_<côté>.csv`, et les indicateurs par culture/région/île/exploitation.
- `plots/` — figures PNG (par culture, par région, marge, coût MO…).

---

## Aide-mémoire express

```bash
.venv/Scripts/python main.py                                   # résoudre (lent)
.venv/Scripts/python -m pytest tests/<fichier>.py              # tester un fichier
.venv/Scripts/python -m pytest                                 # tout tester (lent)
.venv/Scripts/python scripts/display_datasets.py               # inspecter le dataset
.venv/Scripts/python scripts/profile_solver.py --island 1      # profiler sur une sous-zone
streamlit run case_studies/guadeloupe/dashboard/app.py         # dashboard (accueil + comparaison)
```
