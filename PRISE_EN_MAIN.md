# Prise en main — MOSAICA

Toutes les commandes du dépôt. Tout part de la **racine**, avec le venv `.venv/`
(PowerShell : `.venv\Scripts\python`). Données (`data/`), sorties (`outputs/`) et
historique de solve ne sont pas versionnés.

## Installer sur un nouveau PC

```powershell
git clone <url-du-repo>                             # data/ outputs/ non inclus, copie-les à part
python -m venv .venv                                # NE PAS copier le .venv d'un autre PC
.venv\Scripts\python -m pip install -e ".[dev]"     # dépendances + pytest (HiGHS via highspy)
.venv\Scripts\python -m pytest tests\test_readers.py  # vérifier l'install
```

## Commandes

| Commande | Quoi |
|---|---|
| `python main.py` | Résolution complète → `outputs/output_N/`. Aucun argument (tout est dans `config.yaml`). **Lent** (~30–55 min plein territoire, goulot = recherche B&B). |
| `python scripts/run_scenarios.py` | Batch de scénarios (`case_studies/guadeloupe/scenarios.yaml`) : overrides sur le config de référence, un `output_N/` par run + `batch_summary_*.csv/.md`. `--scenarios <fichier>`, `--stop-on-error`. Lance de vrais solves. |
| `python -m pytest tests\<fichier>.py` | Tester un fichier — à privilégier en itération (la plupart des tests sont sans données, donc rapides). |
| `python -m pytest` | Suite complète — **LENTE (~29 min)**, quelques tests construisent le vrai dataset et résolvent. Vérification finale seulement. |
| `python scripts/display_datasets.py` | Inspecter le dataset produit par le `config.yaml` courant (sets/paramètres/scalaires). Aucun argument. |
| `python scripts/profile_solver.py --island 1` | Chronométrer données / construction / solve sur une sous-zone. Options cumulables : `--island`, `--region`, `--farm`, `--plot`. Dès qu'un filtre est donné, les quotas territoriaux sont désactivés automatiquement. |
| `streamlit run case_studies\guadeloupe\dashboard\app.py` | Dashboard **lecture seule** sur les runs passés (ne résout ni n'écrit rien). |

## Dashboard — deux pages

- **Accueil (`app.py`)** — un seul run : recap, indicateurs entrée/sortie, figures par
  culture/région, revenu net & coût MO.
- **Comparaison (`pages/2_Comparaison.py`)** — plusieurs runs côte à côte. Une **série** =
  (run × côté entrée/sortie), cochable. Barres : x ∈ {culture, sous-culture, région, île} ×
  mesure ∈ {surface, production, revenu, marge, subvention, ventes, coût MO, heures, ETP},
  empilement optionnel par une 2ᵉ dimension. Canne (CS/CF) colorée par irrigation×récolte,
  les autres par sous-culture. Axe y log à échelle figée (mode groupé seulement).
  2ᵉ vue : coordonnées parallèles normalisées. Les runs sans `csv/facts_*.csv` sont ignorés.

## Réglages clés de `config.yaml`

`case_studies/guadeloupe/config.yaml` pilote tout :

- **`data`** : `year` (colonne économique `2017`–`2022`/`init`/`calib` — n'agit que sur
  l'économie, la structure reste 2017) et `scenario` (`RESTIT` | `SMART`).
- **`labor`** : `hours_per_etp` (défaut 1607) et `cost_per_hour` (0 = MO non valorisée).
  Reporting uniquement — n'affectent pas l'optimum.
- **`zone_filter`** (désactivé par défaut) : `include`/`exclude` sur
  `islands`/`regions`/`farms`/`plots`. ⚠ ne redimensionne pas les quotas territoriaux.
- **`constraints`** / **`objectives`** : listes activées par `enable: true` (exactement
  **un** objectif actif). Certaines entrées sont désactivées volontairement — lire le
  commentaire avant de basculer un flag.
- **`solver`** : `name` (`appsi_highs`) et `args` (options HiGHS).

## Contenu d'un `outputs/output_N/`

`recap.json`/`recap.md` (synthèse entrée→sortie→delta), `config_used.yaml`,
`csv/` (tous les CSV, dont `facts_<côté>.csv` qui alimente le dashboard comparatif),
`plots/` (PNG).

## Où régler quoi

```
case_studies\guadeloupe\config.yaml   # pilote tout
case_studies\guadeloupe\scenarios.yaml # batch de scénarios
VIGILANCE.md                          # points ouverts / limites de données — à lire avant de commencer
TODO.md                               # idées à implémenter
```
