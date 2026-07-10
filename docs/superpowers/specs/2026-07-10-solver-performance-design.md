# Performance du solveur (brique D) — Design

## Contexte

`core/model/progress.py::solve_with_progress` mesure deja la duree de la
phase de resolution (`solve_model`), avec un historique glissant
(`.mosaica_solve_history.json`) pour estimer un ETA. Mais rien ne mesure
separement `build_dataset` (pipeline de donnees, lecture de ~30 tables) ni
`build_model` (construction du modele Pyomo) : on ne sait pas aujourd'hui si
le temps "perdu" est dans le chargement/la preparation des donnees, la
construction du modele, ou la resolution elle-meme. `config.yaml.solver.args`
est actuellement vide (`{}`) : aucune option HiGHS n'est encore reglee.

Decisions actees avec l'utilisateur (2026-07-10) :
- Profiler sur un sous-ensemble reduit via `zone_filter` (brique C), pas sur
  le run complet — le run complet reste reserve a la demande explicite de
  fin de journee (voir `feedback_no_main_py_each_session`).
- Perimetre des changements : reglages solveur/config uniquement (options
  HiGHS, tolerances, presolve...). Pas de restructuration de la formulation
  Pyomo (contraintes/variables). Les optimisations de code autour du modele
  (ex. pipeline de donnees) restent dans le perimetre tant qu'elles ne
  changent pas ce que le modele represente ou ses resultats.

## Non-goals

- Pas de changement de formulation du modele (contraintes/variables/
  objectifs) — risque sur la justesse des resultats, explicitement exclu.
- Pas de run complet pour mesurer le "avant/apres" dans cette session — les
  chiffres avant/apres sont mesures sur le meme sous-ensemble reduit
  (comparaison relative valide meme sans chiffre absolu sur le run complet).
- Pas de parallelisation multi-run ni d'infrastructure de calcul distribue.

## Architecture

**D1 — instrumentation par phase.** Nouveau
`core/model/timing.py::time_phases(build_dataset_fn, build_model_fn, solve_fn)`
qui chronometre chaque etape et retourne un dict
`{"data_pipeline": s, "model_build": s, "solve": s}`. `main.py` l'utilise a
la place d'appeler les trois fonctions a la suite sans instrumentation, et
affiche le detail avec le total (en plus du `duration` deja affiche pour la
seule phase de resolution, inchangee pour ne pas casser `report.py`/
`recap.json` qui consomment deja ce champ).

**D2 — script de profilage.** `scripts/profile_solver.py` (nouveau,
executable directement, pas un test) : charge `config.yaml`, applique un
`zone_filter` passe en argument CLI (ex. `--island 1` ou `--farm E1471`),
appelle `time_phases`, affiche le detail. Sert a la fois pour cette session
(mesurer avant/apres un reglage) et pour les sessions futures (ressource
reutilisable, pas un one-shot jete apres usage).

**D3 — mesure + reglage.** Executer `scripts/profile_solver.py` sur un
sous-ensemble reduit pour identifier la phase dominante, puis ajuster
`config.yaml.solver.args` (candidats HiGHS : `presolve`, `parallel`,
`threads`, `mip_rel_gap`/`time_limit` si le probleme est MIP et que
l'optimalite exacte n'est pas indispensable a chaque run). Chaque
changement de `config.yaml` est mesure avant/apres avec le meme script sur
le meme sous-ensemble, et documente (quoi, pourquoi, gain mesure) dans
`VIGILANCE.md`.

## Data flow

```
scripts/profile_solver.py --island 1
    -> config = load_config(...) puis config["zone_filter"] = {...}
    -> core.model.timing.time_phases(
           lambda: build_dataset(config),
           lambda dataset: build_model(dataset, config),
           lambda model: solve_model(model, config),
       )
    -> print du detail par phase + total
```

## Error handling

- `time_phases` ne doit pas avaler les exceptions des phases qu'il
  chronometre (une erreur de `build_dataset` doit remonter normalement,
  avec le temps ecoule jusque-la perdu — acceptable pour un outil de
  profilage, pas un chemin de production).
- `scripts/profile_solver.py` valide que le `zone_filter` demande en CLI
  correspond a un critere connu (`resolve_kept_plots` leve deja `KeyError`
  sinon) — pas de validation supplementaire a dupliquer.

## Testing

- `core/model/timing.py::time_phases` : test unitaire avec des callables
  factices (`time.sleep` court ou compteur d'appels) verifiant que les 3
  cles sont presentes, que le total est coherent, et que l'exception d'une
  phase remonte bien.
- `scripts/profile_solver.py` n'est pas couvert par un test automatise
  (c'est un outil d'investigation manuelle, comme `main.py`) mais son
  parsing d'arguments CLI (`--island`/`--region`/`--farm` -> dict
  `zone_filter`) est extrait dans une fonction pure testable.
- Le reglage effectif de `config.yaml.solver.args` (D3) n'a pas de test en
  lui-meme (c'est une valeur de configuration) ; sa validite est verifiee
  par les tests existants qui invoquent deja le solveur sur un jeu de
  donnees factice (`tests/test_guadeloupe_model.py`,
  `tests/test_model_solver.py`) — s'ils restent verts, le reglage n'a pas
  casse la resolution.
