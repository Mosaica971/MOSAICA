# Prise en main — MOSAICA

Aide-mémoire express : une commande, une description. Détails complets dans `COMMANDS.md`.
Tout part de la **racine du dépôt**. Exemples en PowerShell (`.venv\Scripts\python`).

## Installer sur un nouveau PC

```powershell
git clone <url-du-repo>                             # récupérer le code (data/ outputs/ solve_history non inclus, copie-les à part)
python -m venv .venv                                # créer le virtualenv (NE PAS copier le .venv d'un autre PC)
.venv\Scripts\python -m pip install --upgrade pip   # mettre pip à jour
.venv\Scripts\python -m pip install -e ".[dev]"     # installer les dépendances + pytest (HiGHS inclus via highspy)
.venv\Scripts\python -m pytest tests/test_readers.py # vérifier que l'install marche
```

## Au quotidien

```powershell
.venv\Scripts\python -m pytest tests\<fichier>.py    # tester un fichier (rapide — à privilégier en itération)
.venv\Scripts\python -m pytest                       # tout tester (LENT ~29 min, vérif finale seulement)
.venv\Scripts\python scripts\display_datasets.py     # inspecter le dataset produit par le config.yaml courant
.venv\Scripts\python scripts\profile_solver.py --island 1  # profiler un solve sur une sous-zone (rapide)
.venv\Scripts\python main.py                         # résolution complète → outputs/output_N/ (LENT, fin de journée uniquement)
streamlit run case_studies\guadeloupe\dashboard\app.py     # dashboard lecture seule sur les runs passés
```

## Où régler quoi

```
case_studies\guadeloupe\config.yaml   # pilote tout : data.year/scenario, contraintes, objectif, zone_filter, solver
VIGILANCE.md                          # journal des points ouverts / dettes / limites de données — à lire avant de commencer
COMMANDS.md                           # référentiel détaillé de chaque commande et de ses arguments
```
