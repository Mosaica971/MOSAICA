# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Human-facing documentation is `docs/`** — five numbered files: how to run it (01), the file
> tree (02), how to extend it (03), **the traps to know before quoting any number (04)**, and how
> to port the model to another territory (05). `docs/archives/journal-vigilance.md` holds the full
> investigation log. Keep `docs/04-vigilance.md` in sync when a new limitation is found: it is the
> file a newcomer reads, and this one is not.

## What this is

Python/Pyomo rewrite of **MOSAICA**, a crop-allocation optimization model originally
written in GAMS. It solves a large binary MILP: assign each agricultural plot in
Guadeloupe to at most one crop so as to maximize gross margin, subject to agronomic
eligibility, per-farm area rules, and territory-wide production quotas. The original
GAMS source lives (as `.txt`) in `context/gams/` and is the **reference
for parity** — when a constraint or coefficient is in question, that directory is the
source of truth (`MODELE.txt`, `OPTIMISATION.txt`, `ENTREES.txt`, `SETS.txt`, etc.).

The active workstream is "GAMS parity" — porting legacy behavior faithfully. Deviations
from GAMS are deliberate and documented in config comments and `docs/04-vigilance.md`.

## Commands

The venv is at `.venv/`. Run tests with pytest (config in `pyproject.toml`,
`pythonpath = ["."]` so imports resolve from the repo root):

```bash
.venv/Scripts/python -m pytest tests/test_readers.py # one file
.venv/Scripts/python -m pytest tests/test_guadeloupe_constraints.py::test_cs_gfa_minimum_share_constraint_only_applies_to_farms_with_gfa_surface  # one test
.venv/Scripts/python -m pytest                       # full suite — SLOW (~29 min)
```

The **full suite is slow** (~29 min: a few tests build the real dataset and run real
HiGHS solves). During iteration, run only the file(s) you're touching; save the full run
for a final check.

Full end-to-end solve (builds data → model → solves with HiGHS → writes `outputs/output_N/`):

```bash
.venv/Scripts/python main.py
.venv/Scripts/python main.py --case-study guadeloupe   # or $MOSAICA_CASE_STUDY
```

**Which case study runs is resolved by name** (`core/case_study.py`), not wired into imports:
`main.py`, `run_scenarios.py`, `profile_solver.py` and `display_datasets.py` all take
`--case-study`. A case study is a package under `case_studies/` exposing exactly three functions
— `build_dataset(config)`, `build_model(dataset, config)`, `generate_report(...)` — plus its
`config.yaml`. `core/` speaks no Guadeloupe and that is checked; the calibration scripts
(`build_reference_state`, `evaluate_calibration`, `compare_to_reference`, `pad_all_scales`) are
case-study-specific by nature. See `docs/05-nouveau-cas-etude.md`.

**Do NOT run `main.py` casually.** The full solve is slow (~30–55 min on the real dataset,
with large run-to-run variance; the bottleneck is the branch-and-bound search itself — see
`docs/04-vigilance.md`). Per standing user preference, only run the full solve at end-of-day and
only when asked; iterate with targeted pytest instead. For scaled-down experiments use
`zone_filter` in `config.yaml` (restrict to one island/region/farm) or
`scripts/profile_solver.py` (phase-timed run on a zone subset).

Scenario batch (same pipeline as `main.py`, one `output_N/` per scenario + a batch summary;
spec in `case_studies/guadeloupe/scenarios.yaml`): `.venv/Scripts/python scripts/run_scenarios.py`.
Same caveat as `main.py` — real solves, don't run casually.

**Prospective scenarios are four files: three catalogues and one plan.** The catalogues declare
what exists — `scenarios_politiques.yaml` (`policies:`, what a public authority decides),
`scenarios_forcages.yaml` (`forcings:`, what climate and markets impose),
`scenarios_pareto.yaml` (`sweeps:`, the ε-constraint fronts). **`plan.yaml` is what actually
runs**, and the only file to edit to change a batch: it `include:`s the three and then names,
per policy, which forcings it goes through and which fronts are traced under it.

```yaml
scenarios:
  P1_deregulation_totale:                          # la politique seule, non forcée
  P4_statu_quo: [F0_nominal, F9_crise_systemique]   # raccourci pour `forcings:`
  P8_transition_agroecologique:
    forcings: [F0_nominal, F9_crise_systemique]
    sweeps: [pareto_azote, {name: pareto_azote, forcings: [F9_crise_systemique]}]
```

A cell costs (its forcings, or 1 if none) + (the points of each sweep). **A sweep is not crossed
with the cell's forcings** — a front is one solve per point, and multiplying it by a forcing list
is how an afternoon becomes a week; a forced front is named explicitly. `--no-sweeps` drops every
front (staging), `--policies` / `--forcings` restrict to a row or a column, and `--cross`
**overrides** the plan to take the whole catalogue product (what the completeness test uses).
Every run carries `policy` / `forcing` / `sweep` into its recap, so the dashboard groups on
coordinates rather than parsing `__` out of a name. Always validate before committing hours:

```bash
python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/plan.yaml --dry-run
python scripts/check_scenario_feasibility.py --scenarios case_studies/guadeloupe/plan.yaml
```

**Crop groups are a catalogue, not a copy.** YAML anchors do not cross files, so a spec writes
`crops: {group: canne}` and `core/config.load_batch_spec` substitutes the list. The catalogue is
`crop_families` from `config.yaml` **plus** `crop_groups.yaml` (the latter winning), so a group
the model already knows is never restated in a scenario file; `@name` members compose groups out
of groups. Two traps: the match is the *exact* one-key dict `{group: x}`, because
`territory_production_bound`'s args already carry a key literally named `groups`; and a catalogue
declares its own `crop_groups` include so it stays runnable alone (`--scenarios
scenarios_politiques.yaml --policies P8`). `scenarios.yaml` deliberately still uses in-file
anchors — one file, no cross-file copy, nothing to gain.

`check_scenario_feasibility.py` solves each scenario's **LP relaxation** (~2 min vs 30-55 min for
the MILP). Infeasible there ⇒ infeasible for certain; feasible there is necessary, not sufficient.
It already caught one design error before any batch ran. It also reports **symmetric crop groups**
— crops the model cannot tell apart because they are equal on every parameter it reads. Those are
both a branch-and-bound disaster (the search permutes equivalent solutions) and a modelling trap
(a share constraint distinguishing crops the data does not distinguish is met by relabelling, at
zero cost). The 25 experimental market-gardening variants are exactly that; see docs/04-vigilance.md.

`run_scenarios.py` **chains warm starts** (on by default), from three sources tried nearest-first
(`seed_candidates`): the **previous point of the same Pareto front**, then the policy's own
unforced allocation (a forcing changes coefficients, not the feasible set), then an optional
global `--warm-start-from <run>`. Every seed is audited — HiGHS discards an infeasible MIP start
silently, so an unaudited seed yields a run that looks warm and behaves cold.

The front chain only works because `core/config.order_sweep_points` **reorders each sweep
tightest-first before the batch runs**, which is the reverse of how the YAML reads. Feasibility
implies one way only: under `sense: le` a solution feasible at a low ceiling stays feasible at a
high one, so ascending order makes every seed valid and descending order makes every seed
infeasible; under `sense: ge` it inverts. One cold solve (the tightest, also the slowest) then six
warm, instead of seven cold. The reordering abstains whenever it cannot be sure — a 2-D matrix, a
constraint with no `sense`, or an argument that is not the bound's level (`scale` multiplies the
indicator and therefore *inverts* the direction, which is why the allowlist exists). Abstaining
costs speed only: correctness rests on the audit, never on the order.
Design spec: `docs/superpowers/specs/2026-07-31-scenarios-prospectifs-design.md`.

Read-only Streamlit dashboard over past runs: `streamlit run apps/dashboard/app.py`.
Its **Prospective** page reads a policy × forcing grid rather than a flat run list (heatmap with
absolute / %-of-nominal / regret readings, performance-robustness scatter, per-policy tornado,
robustness table). A run joins the grid via `run_policy` / `run_forcing` in its recap.

**Score a run against the observed 2017 land use** (~7s, no solve; new runs do it themselves
inside `generate_report`):

```bash
.venv/Scripts/python scripts/evaluate_calibration.py outputs/output_12   # one run
.venv/Scripts/python scripts/evaluate_calibration.py --all               # every run
```

**The 2017 reference state** (~5s, no solve, deterministic) is the observed situation every
run is scored against, built as a standalone artifact rather than only as a run's "input"
side:

```bash
.venv/Scripts/python scripts/build_reference_state.py        # -> outputs/reference_2017/
.venv/Scripts/python scripts/compare_to_reference.py outputs/output_1
.venv/Scripts/python scripts/pad_all_scales.py outputs/output_1   # PAD at five scales
```

`outputs/reference_2017/REFERENCE.md` documents how it is built and — more usefully — what it
cannot say: the observed side has no fine crops (hence the low/high bracket on every
indicator), and part of the observed acreage is unreproducible by construction (a floor under
the PAD). Rebuild it whenever `config.yaml` changes year, `zone_filter` or
`baseline_representative_crops`.

**Invariance check before/after a refactor** — `scripts/golden_snapshot.py` builds the full
real dataset and every indicator block on a real allocation (~7s, **no MILP solve**, so it is
exactly reproducible) and serialises ~570 numeric checksums:

```bash
.venv/Scripts/python scripts/golden_snapshot.py --write   # record current behavior
.venv/Scripts/python scripts/golden_snapshot.py --check   # non-zero exit + diff on any drift
```

Use it whenever touching `pipeline/`, `domain/`, `core/data/` or `reporting/indicators.py`:
it catches numeric drift that the (deliberately synthetic, data-free) unit tests cannot. The
reference lands in `.golden/`, gitignored because it derives from the local `data/`.

## Data is not in the repo

`/data/` is **gitignored** — `data/sets/` (`.set`), `data/tables/` (`.txt`) and `data/gis/`
(the shapefile layers) live locally only, as do `/outputs/`, `.worktrees/`, `.golden/` and
`.mosaica_solve_history.json`. Code that touches them fails on a fresh clone until the files
are present. There are no geographic coordinates in `data/tables/`; outside `data/gis/`,
spatial reporting is aggregated by `ILE`/`REGION`/`COMMUNE` only.

**`context/` holds the external sources**, and is versioned (except the .docx): `context/gams/`
is the original GAMS — the source of truth for any parity question — and
`context/Chopin et al 2015 pour Hal.pdf` is the reference article (§2.6 = the calibration method,
Tables 1-2 = yields/margins and risk-aversion coefficients).

## Architecture

Three layers: a **case-study-agnostic `core/`**, a **`case_studies/guadeloupe/`** supplying the
concrete data pipeline, GAMS-specific rules and reporting, and an **`apps/`** holding what only
*reads* finished runs.

`core/` splits building a model from solving one: `core/model/` (`registry`, `builder`,
`constraints`, `objectives`, `model_inputs`) constructs the Pyomo problem and knows nothing
about how it will be solved; `core/solve/` (`solver`, `progress`, `timing`, `warm_start`,
`shadow_prices`) drives HiGHS and everything that happens around a solve. `core/data/` reads
tables; `core/reporting/` writes run folders and computes robustness over a grid.

`case_studies/guadeloupe/` is organized by role — `pipeline/` (`data_pipeline.py`),
`domain/` (per-crop science: `economics`, `environment`, `water`, `soil_carbon`,
`resilience`, `farm_typology`, `crop_labels`, `crop_families`, `zones`, `agroecology`,
`rpest`, `geometry`), `model/` (`model.py`, `constraints.py`), `reporting/`. Note
`model/model.py`: the module is `case_studies.guadeloupe.model.model`, and importing only the
*package* does not register the case-study constraints (see below). `config.yaml`,
`scenarios.yaml`, `plan.yaml` with its three catalogues (`scenarios_politiques.yaml`,
`scenarios_forcages.yaml`, `scenarios_pareto.yaml`), `crop_groups.yaml` and `references.yaml`
stay at the case-study
root.

`apps/dashboard/` is the read-only Streamlit viewer. It lives **outside** `case_studies/`
because it is not part of the solve path at all: it opens `outputs/output_N/` folders and
never builds a dataset, a model or a solver. Nothing under `core/` or `case_studies/` may
import it; it imports `case_studies.guadeloupe.domain` freely for labels and geometry.

**Config-driven registry pattern (the central idea).** Constraints, objectives,
eligibility criteria, and categorical rules are all Python functions registered by name
via decorators, then selected and parameterized entirely from
`case_studies/guadeloupe/config.yaml`. To add or change model behavior you usually edit
the YAML, not the builder.

- `core/model/registry.py` — `@register_constraint(name)` / `@register_objective(name)`
  populate `CONSTRAINT_REGISTRY` / `OBJECTIVE_REGISTRY`.
- `core/config.py` `resolve_enabled(entries, registry)` — reads a config list, keeps
  entries with `enable: true`, and returns `(builder_fn, args)` pairs. The same pattern
  drives constraints, objectives (exactly one must be enabled), eligibility, and
  categorical rules.
- Builders are **imported for their side effect** of registering (e.g.
  `from core.model import constraints as _constraints  # noqa: F401`). If a builder isn't
  imported somewhere on the path to `build_crop_allocation_model`, its name won't be in
  the registry and config referencing it raises `KeyError`. `core/model/builder.py`
  imports the core builders; `case_studies/guadeloupe/model/model.py` additionally imports
  `case_studies.guadeloupe.model.constraints` to register case-specific ones. Import the
  *module* (`case_studies.guadeloupe.model.model`), never just the package — the package
  `__init__.py` is empty, so `import case_studies.guadeloupe.model` registers nothing.

**Data flow** (`main.py` orchestrates):
1. `load_config(config.yaml)` → dict.
2. `build_dataset(config)` (`case_studies/guadeloupe/pipeline/data_pipeline.py`) reads the `.set`/
   `.txt` tables, applies the `zone_filter`, computes economics
   (`domain/economics.py`: margin/sales/subsidy per ha per crop), farm typology
   (`domain/farm_typology.py`: base crop group → `TYPE_EXPL` → risk aversion `AVERS`), and the
   plot×crop **eligibility mask** (`core/data/eligibility.py` numeric bounds +
   `categorical_rules`). Returns a `Dataset(sets, parameters, scalars)`.
3. `build_model(dataset, config)` → `build_crop_allocation_model(...)` creates the Pyomo
   `ConcreteModel`: binary var `model.Y[plot, crop]` over eligible `PAIRS`, then runs every
   enabled constraint/objective builder against a `ModelInputs` bundle
   (`core/model/model_inputs.py`).
3b. **Optional warm start.** `core/solve/warm_start.py` writes a past run's allocation into
   `model.Y` (`apply_allocation`) and — the part that matters — **audits it against the
   model's own constraints before solving** (`constraint_violations`). HiGHS discards an
   infeasible MIP start silently, so without the audit a run looks warm-started and behaves
   exactly like a cold one. Driven by `solver.warm_start_from` in `config.yaml` (a run
   folder); `main.py` loads, applies, audits, and only then passes `warm_start=True` down to
   `solve_model`, which maps it onto Pyomo's `warmstart` kwarg → `Highs.setSolution`.
   A warm start changes only how fast the optimum is **proven**, never what it is. It became
   necessary past ~309 000 binaries, where HiGHS stops finding good incumbents unaided
   (2026-07-29: two constraints each hit the 1 h limit 5.5% below a hand-built solution).
   Measured: 720 s cold → 209 s warm, identical objective. To seed a run that adds a new
   constraint the old allocation must be repaired first — `scripts/repair_allocation.py`.
4. `solve_with_progress(model, config, case_study=...)` (`core/solve/progress.py`) runs
   `solve_model` (`core/solve/solver.py`, `SolverFactory('appsi_highs')` → HiGHS)
   **synchronously on the main thread**, printing an expected-duration **range** before and
   the real duration after. It is a range, not a point, because measurement says a point is
   meaningless: at a fixed 308 847 variables the 20 recorded solves span 155 s to 1 007 s
   (CV 64 %, factor 6.5), and the previous point estimator was wrong by a median 75 %.
   `SolveHistory.estimate_range` therefore reads the **most recent** comparable runs (same
   size ±20 %, same warm/cold mode — 720 s against 209 s, so those are never pooled) and
   **returns None rather than answer outside the size band** (the old one gave the same 456 s
   for 200 000 and 331 044 variables). Note: the solve must NOT be backgrounded behind a
   live progress bar — `appsi_highs` (via either `SolverFactory` or the persistent
   interface) loads the model inside `capture_output(capture_fd=True)`, and concurrent
   progress I/O from another thread corrupts Pyomo's process-global stdout/stderr fd state,
   crashing every real run (see
   `docs/superpowers/specs/2026-07-10-solver-progress-capture-fd-conflict.md`).
5. `generate_report(...)` (`case_studies/guadeloupe/reporting/report.py`) decodes the
   solution, computes indicators (`reporting/indicators.py`), renders PNGs
   (`reporting/plots.py`), and writes a timestamped `outputs/output_N/` folder
   (`core/reporting/run_folder.py`) with a recap, CSVs, YAML, and charts. The dashboard
   (`apps/dashboard/`) is a read-only viewer over those folders.

**`data/gis/` (racine, non versionné comme `data/`) porte le RPG 2017 parcellaire.**
`core/data/shapefile.py` le lit en Python pur — pas de GDAL, pas de geopandas — et
`domain/geometry.py` le raccorde aux identifiants synthétiques `P1..Pn` par **signature
d'exploitation**, faute d'identifiant commun : 99,4 % des parcelles. La page **Carte** montre
l'observé, le simulé et les changements. Lire l'entrée VIGILANCE avant de conclure sur une
parcelle isolée — ~1 557 d'entre elles ont une jumelle interchangeable.

**Trois indicateurs environnementaux de plus, chacun avec son piège** (tous documentés dans
`docs/04-vigilance.md`, entrée « Quatre pièges ») : le **phosphore et la potasse** lus sur les noms
d'engrais NPK (validés contre la colonne `AZOTE`, qui les confirme au millième) ;
**`domain/agroecology.py`**, où les MAE donnent une définition *sourcée* de l'agroécologie et
les opérations `FERTI_MA_*BIO` une définition du bio — les deux rapportées séparément, car la
canne en récolte verte n'est pas bio, et la prairie domine le bio par itinéraire ; et
**`domain/rpest.py`**, l'arbre flou de Tixier, seul indicateur qui dépende du **couple**
(parcelle, culture) puisqu'il croise les produits de la culture avec le ruissellement et le
drainage de la parcelle.

**`core/solve/shadow_prices.py`** donne le coût marginal de chaque contrainte nommée. Attention :
figer les entiers ne marche PAS ici (le modèle est purement binaire, donc l'LP obtenue n'a plus
aucune variable libre et tous les duaux valent 0) — ce sont les duaux de la **relaxation
linéaire** qui sont lus, avec les réserves que le module détaille.

**`zone_filter.scale_territorial_bounds: true`** met les seuils territoriaux à l'échelle de la
part de surface retenue. Sans lui un run réduit n'est pas plus petit, il est **infaisable** (le
plancher de prairie réclame ses 6 096 ha à l'île entière). Opt-in : réécrire un seuil change ce
que le scénario dit.

Les indicateurs environnementaux vivent dans trois modules par culture de `domain/` —
`environment.py` (azote/GES/IFT), `water.py` (besoin en eau) et `soil_carbon.py` (carbone organique) —
tous calculés dans `data_pipeline` puis appliqués à l'allocation par `reporting/indicators.py`.
Le carbone est le seul à dépendre de la **parcelle** (via `TYPE_SOL` → `Data_Sol.txt`) et non
seulement de la culture : il ne passe donc pas par l'helper `rate()` de `compute_facts_table`.

**Deux notions de résilience, à ne jamais additionner.** `recap["resilience"]` mesure
l'**exposition** d'une allocation *figée* : le choc de prix est appliqué après le solve, donc il
répond à « que perd-on si personne ne réagit ». `core/reporting/robustness.py` mesure la
**capacité d'adaptation sous contrainte politique** sur une grille politique × forçage : le
modèle a ré-optimisé sous chaque forçage, dans les limites que la politique lui laisse. Le
module fournit pire cas (Wald), rétention, CV, regret maximal (Savage) et domaine de viabilité
(Starr), avec trois choix assumés : l'infaisabilité est le **pire résultat** et non une valeur
manquante ; les forçages ne sont **pas moyennés** par défaut (une moyenne affirmerait une
distribution de probabilité que personne n'a choisie) ; le regret se calcule contre la
meilleure politique **du même forçage**.

**Piège du score composite.** Un indicateur qu'une contrainte *fixe* est une hypothèse du
scénario, pas son résultat : noter une politique sur le plafond de subventions qu'elle s'est
elle-même donné est circulaire. `comparison.bound_indicators(recap)` les détecte depuis
`recap["constraints"]` (donc rétroactivement sur les runs déjà écrits) et la page les signale.
Par ailleurs `compute_composite_scores(..., balance_families=True)` — le défaut — normalise le
poids **par famille** : sans cela les onze ratios d'autonomie, quasi colinéaires, pèsent onze
fois les GES, et le score mesure la finesse du découpage plutôt que la performance.

`domain/resilience.py` ajoute trois indicateurs d'**exposition** (marge à risque climatique via
`Var_Rdt_Cult`, concentration du revenu, perte sous choc de prix), agrégés par
`compute_resilience_totals` et stockés dans `recap["resilience"]`. Attention : exposer un
indicateur au score composite demande **deux** ajouts — `INDICATOR_DIRECTION`
(`apps/dashboard/comparison.py`) pour le sens, et un groupe de `_INDICATOR_LABELS`
(`apps/dashboard/pages/2_Comparaison.py`) pour l'appartenance au sélecteur. Le premier seul ne
branche rien.

**Le dashboard s'ouvre sur une page Synthèse** (`apps/dashboard/app.py`) qui répond en un écran :
solve convergé ou non, les quatre verdicts de calibration contre leurs seuils, les groupes de
cultures qui portent l'écart (classés en **hectares**, pas en PAD), et les pièges de lecture qui
s'appliquent à *ce* run — dérivés du recap par `apps/dashboard/synthesis.run_alerts`. Chaque
alerte encode un piège documenté ici ou dans VIGILANCE (solve non prouvé optimal, PAD épinglé par
`pn_prod_min`/`bc_quota_max`, indicateur fixé par une contrainte, objectif de marge brute pure),
pour que la mise en garde voyage avec le chiffre.

**Trois runs de référence sont déclarés dans `case_studies/guadeloupe/references.yaml`** —
observé 2017, calibration à parité GAMS, calibration retenue — chacun avec la justification de son
choix et les métriques qu'il doit reproduire. Les deux runs de calibration se régénèrent en une
commande depuis `scenarios_calibration.yaml`, et leur dossier **porte leur nom**
(`outputs/calib_retenu/`, pas `output_7`) : `run_folder.create_output_folder` accepte un nom, et
la découverte se fait sur la présence d'un `recap.json` — ce qui met sur le même plan dossiers
nommés et numérotés, et exclut naturellement `reference_2017/` (il écrit `reference.json`).

```bash
.venv/Scripts/python scripts/run_scenarios.py --scenarios case_studies/guadeloupe/scenarios_calibration.yaml
.venv/Scripts/python scripts/check_references.py     # garde-fou, ~0 s, aucun solve
```

`check_references.py` est **le seul garde-fou du dépôt sur le solve** : les tests sont sans données
par choix et `golden_snapshot` couvre le pipeline et les indicateurs, pas la résolution. Sa
tolérance est à 5 % parce que le bruit de branch-and-bound mesuré vaut 0,15 point de PAD — une
garde à l'égalité exacte échouerait sur un simple re-run.

**Deux diffs, à lire dans cet ordre.** `apps/dashboard/config_diff.py` met en regard les
`config_used.yaml` de deux runs : quelles contraintes l'un active que l'autre n'a pas, quels seuils
ont bougé. `apps/dashboard/allocation_diff.py` dit ce que ces lignes ont **déplacé** : matrice de
transition, flux dominants, bilan net par culture. Entre les deux calibrations, le premier sort
deux contraintes et le second `CS → PN` 2 972 ha et `BC → BA` 1 189 ha. Le diff de config dit ce
qui a été **demandé**, jamais ce que l'écart a **coûté** — une contrainte qui ne mord pas ne change
aucun résultat. Attention à la résolution du diff d'allocation : `fine` (84 codes) n'a de sens
qu'entre deux runs **simulés** ; contre l'observé, seuls les 12 groupes RPG existent.

**Fronts de Pareto par ε-contrainte** (`scenarios_pareto.yaml`, `apps/dashboard/pareto.py`, page
**Pareto**). Un balayage est un run portant un `matrix:`, déplié par `expand_runs` en un solve
par point. Deux leviers `enable: false` vivent dans `config.yaml` (`azote_max`, `emploi_min`)
uniquement pour que `matrix: {args:<label>.<argument>: [...]}` puisse en faire varier le seuil —
`set_args` ne sait toucher qu'une entrée déjà déclarée. Un front se trace soit contre la config
de référence (le catalogue lancé seul), soit **sous une politique** déclarée dans `plan.yaml` —
et c'est là l'objet intéressant, le coût marginal de l'azote n'étant pas le même à 70 % et à
30 % d'inertie. Conséquence pour la lecture : le run s'appelle alors
`<politique>__<forçage>__<balayage>__<point>`, donc le préfixe avant `__` nomme la **politique**
et non le balayage — `pareto.sweep_of` groupe sur `run_sweep`/`run_policy`/`run_forcing` du recap,
le préfixe ne servant que de repli pour les runs antérieurs. Le contrôle du premier point (seuil
inactif ⇒ marge égale au run non balayé) se fait alors contre la politique, pas contre
`calib_retenu`. Le front donne le **coût marginal** sur
tout l'intervalle, là où le prix dual de `shadow_prices.py` n'en donne que la pente locale ; un
écart important entre les deux signifie que le dual est lu hors de son voisinage de validité. Un
point **dominé** sur un front signale presque toujours un solve non convergé, pas une découverte :
serrer une contrainte ne peut pas améliorer l'objectif.

`reporting/calibration.py` note le run contre la réalité observée, d'après Chopin et al. (2015)
§2.6 (`context/Chopin et al 2015 pour Hal.pdf`) : PAD (pourcentage d'écart absolu) territorial,
sous-régional et par exploitation, matrice de confusion des 8 types d'exploitation, taux de
correspondance parcellaire. Tout se compare au niveau des **12 groupes RPG observés** —
`domain/crop_families.base_group_for()` y replie les 84 cultures fines, parce que l'observé 2017
n'a pas de résolution plus fine. Écrit dans chaque run (`recap["calibration"]` +
`csv/calibration_*.csv`), rejouable sur un run passé avec `scripts/evaluate_calibration.py`
(reconstruit le `Dataset`, ~7 s, sans solve). **Attention : ces métriques mesurent aujourd'hui
un modèle non calibré** — PAD territorial ~193 %, objectif marge brute pure et `Eq_MO_MAX_Expl`
non portée ; un mauvais score est le diagnostic attendu, pas une régression du reporting
(cf. `docs/04-vigilance.md`).

**Bounding an indicator, not just production.** `territory_production_bound` can only bound
physical output. `territory_indicator_bound` bounds *any* per-hectare rate the case study
exposes in `ModelInputs.crop_indicator_rates` — nitrogen, IFT, GHG, water, soil carbon, labour
hours, subsidy euros — so one builder writes a nitrates ceiling, a public-spending envelope and
an employment floor. `zone_indicator_bound` holds the same bound per island/region/watershed/**farm**
(`threshold_per_ha` × the zone's own hectares is the directive-nitrates form), and
`baseline_inertia_min` requires a share of allocated area to stay in its observed 2017 group.
Two traps: `ModelInputs.plot_weights` exists because rates are per-crop while water is only drawn
on irrigable plots (a bound without `plot_weight: irrigable` counts 56 Mm³ where the report says
35); and an **employment floor above the labour cap is infeasible** — `farm_labor_hours_max` grants
3 891 ETP at `slack: 1.0`, so any floor above that must raise the slack in the same scenario.

**Eligibility** is a boolean plot×crop matrix: numeric attribute bounds (altitude, slope,
rainfall, plot size) intersected with `categorical_rules` (irrigation, soil type, region
bans, `friche_lock` fallow history, etc.). Only eligible `(plot, crop)` pairs become
decision variables, which keeps the MILP tractable.

A categorical rule receives the plot table as `plot_attributes` and returns
`(crops, condition)`; `forbid_where` then clears those crops on the matching plots. Since
each rule forbids its own subset and the mask keeps the **union** forbidden, a single
`attribute_forbidden` entry ANDs its conditions and an **OR is expressed as several
entries** (that is how the ME soil/island ban is written in `config.yaml`).

**`core/` speaks no Guadeloupe.** It reasons about plots, crops and farms only: no
`data_parc`, no `ILE`, no GFA. `ModelInputs.farm_restricted_surface_ha` is the generic name
for "surface of the farm's plots flagged as subject to a land-tenure scheme" — the case
study maps its `farm_gfa_surface_ha` parameter onto it in `model/model.py`. Keep it that
way: case-study vocabulary belongs in `case_studies/`, where it anchors GAMS parity.

## Conventions & gotchas

- **`territory_production_bound` and the "trivial Boolean" trap.** When a constraint's
  `sum()` matches zero `(plot, crop)` pairs it returns a plain Python `0`, not a Pyomo
  expression; comparing it yields a bare `bool` that Pyomo rejects. Both
  `territory_production_bound` (`core/model/constraints.py`) and `cs_gfa_minimum_share`
  guard for this with `Constraint.Feasible`/`Constraint.Infeasible`. Replicate this guard
  in any new constraint whose term set can be empty.
- **Disabled config entries are intentional, with reasons in the YAML comments.** E.g.
  `cs_gfa_minimum_share` and `maximize_risk_adjusted_gross_margin` are correct and tested
  but disabled because enabling them causes a genuine (GAMS-matching) infeasibility on the
  real 2017 data, or diverges from the chosen default. Read the comment before flipping an
  `enable:` flag.
- **Where each kind of knowledge goes.** `docs/04-vigilance.md` (French) holds the **traps and
  known data gaps** — the *why*, and the file a newcomer must read before quoting a number; a
  newly discovered limitation belongs there. `TODO.md` is what remains **to implement** (the
  *what next*). A whole investigation — with the dead ends and the measurement that closed
  them — belongs in a new spec under `docs/superpowers/specs/`. The historical log is
  `docs/archives/journal-vigilance.md`, no longer maintained as such. Read `04` and `TODO.md`
  at the start of substantive work.
- `docs/superpowers/specs/` (design docs) and `docs/superpowers/plans/` (implementation
  plans) hold the reasoning behind each feature. Only **unexecuted** plans are kept —
  executed ones are deleted, their rationale surviving in the matching spec. (`plans/` is
  currently empty for exactly that reason: all four were executed and removed 2026-08-01.)
- Tests exercise builders in isolation with tiny hand-built configs and `plot_surface_ha`/
  `eligible_pairs` dicts (see `tests/test_guadeloupe_constraints.py`) — they do not read
  `data/`. Follow that style for new model logic so tests stay fast and data-free.
- **`data.year` / `data.scenario` come from `config.yaml`** (defaults `2017` / `RESTIT`,
  which reproduce the historical hard-coded behavior). `year` selects the economic
  time-series column in the `indice_H` tables (`2017`–`2022`, or `init`/`calib`) and drives
  **economics only** — the plot/farm structure stays pinned to 2017, the only year whose
  structural data exists. `scenario` (`RESTIT`|`SMART`) selects `Matrice_OTK_Cult_<scenario>`
  and `MAE_Compost_Cult_<scenario>`. `data_pipeline.build_dataset` validates both (fail-fast
  `ValueError`) and `var_rdt_cult` deliberately stays on its `init` column regardless of
  `year`. The chosen year/scenario is recorded in each run's recap.
