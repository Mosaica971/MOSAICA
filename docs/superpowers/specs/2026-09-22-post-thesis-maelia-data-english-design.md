# After the thesis — MAELIA coupling, data porting to the information system, English renaming, status board

Date: 2026-09-22. Status: **A, B and C done, D and E postponed** (decision of
2026-09-22: the MAELIA couplings come later). This document orders the five work items announced
after the defence, and isolates the decisions that belong to Clément or to the supervisors.
Everything said here about MAELIA itself is **to be checked** against its documentation: the
training has not taken place yet.

**2026-09-23 — the MAELIA user guide has been read** (`context/maelia/`, digest in
[`docs/maelia/README.md`](../../maelia/README.md)). What it settles is noted inline below
("Guide:"); its § M holds the consequences, some of which change §4 and §5.

Decisions taken on 2026-09-22:

- **Everything in English** — code, config, scenario files, dashboard, docs. The thesis and its
  corpus (`clement/`) stay in French: they are closed. The dated specs and the investigation
  journal stay in French as historical records.
- **The "no new solve" rule** of the thesis phase is **lifted** for the rest of the internship.
- **`docs/TODO.md` is replaced by `docs/status/roadmap.yaml`.**

---

## 0. Proposed order, and why

| # | work item | why at this rank | state |
|---|---|---|---|
| A | **Status board** (indicators x levels, constraints x crops, multi-valued parameters, implementation status) | Quick, and already the specification of the coupling: the table of sourced parameters lists exactly what MAELIA will replace. | done |
| B | **English renaming + comment review** | Before writing the MAELIA interfaces; otherwise everything is renamed twice. | done (code, config, dashboard, numbered docs) |
| C | **Data catalogue, access levels, exchange formats** | The data contract with MAELIA and the one with the information system are the same object. Define it once. | done (`docs/data/`) |
| D | **MAELIA -> MOSAICA**: simulated yields and ITKs | Needs C (format) and a localised change of the model (§ 4). | postponed |
| E | **MOSAICA -> MAELIA**: the cropping plan tested at a daily time step | Needs D (same plot and crop referential) and a decision on dynamics (§ 5). | postponed |

---

## 1. Work item A — the status board (done)

**Principle: generate what can be derived from the code, write by hand only what cannot.** The
repository has already shown that a hand-typed figure drifts (the 64 % CV overwritten, the dual
prices nowhere to be found, 482 corpus items instead of 491). A hand-written status table would
be wrong within a month.

Delivered: `case_studies/guadeloupe/reporting/status.py`, `scripts/build_status_board.py` ->
`docs/status/STATUS.md`, the dashboard page **Status**, and `tests/test_status_board.py`.

### A.1 — Indicators x aggregation levels — *declared, derived, tested*

Finding: each indicator had been aggregated at the scales needed at the time. `fte` exists per
farm, island and region; Shannon per island and region; nitrogen, GHG, TFI over the territory and
per crop; `facts_output.csv` stops at crop x region x island. No commune, no arbitrary zone.

`status/indicator_catalog.yaml` declares each indicator's aggregation **class**, and the board
derives what is computable from it:

| class | examples | aggregation |
|---|---|---|
| additive | area, production, gross margin, hours, nitrogen, GHG, water, carbon | sum, every level |
| ratio | margin/ha, nitrogen/t, subsidy/FTE, shares | ratio of sums, every level |
| non_additive | Shannon, HHI, Gini, maximum | **redefined per level**, one by one |
| territorial | food self-sufficiency | needs a population per zone: territory only |
| observed | PAD, confusion matrix, plot agreement | only at the 12 RPG groups (no fine crop) |

The next step, which changes the table itself, is on the roadmap (`per-plot-facts`): **one
per-plot table** (`plot, farm, crop, indicator…`) computed once, and a single aggregation function
per zone key. An arbitrary zone is then only a `plot -> zone` file (or a GIS layer), and every
additive indicator becomes available at every level by construction.

### A.2 — Constraints x crops — *generated*

Derived from `config.yaml` (enabled entries and disabled ones): for each entry, its role
(ceiling, floor, ban, eligibility bound), the crops it touches, and the GAMS equation it ports —
read from its label or from the config comment above it, and shown only if found in
`context/gams/`. With `--with-data`, the number of (plot, crop) pairs each ban removes. A second
view gives, for one crop, every rule that applies to it ("why is there no melon?").

### A.3 — Parameters with several plausible values — *hand-written, checked*

`status/parameter_choices.yaml`: for each parameter, the candidates with their source, the
retained value, the reason, the status (retained / open / not adopted) and the vigilance entry.
The board reads the value config.yaml actually holds and flags a `DRIFT` when the two differ.

### A.4 — Implementation status — *hand-written, tested*

`docs/status/roadmap.yaml`, one item per line: `id`, title, status, area, spec, what is left, what
blocks it. Statuses: **done · in_progress · todo · to_update · proposal · blocked · abandoned**.
`docs/TODO.md` mixed the log and the list (most of its 430 lines were *delivered*); it was
retired, each entry re-checked against the code — several "deferred" items were in fact done
(`Eq_AN_PA`, the labour cap, the map, P and K).

---

## 2. Work item B — English renaming and comment review (done)

### What it found

Measured on `core/`, `case_studies/`, `apps/`, `scripts/` (82 files, 11 800 lines): 12 French
comment lines out of ~1 400, and 41 function names out of 451 with a French term. The French was
concentrated in: domain terms in identifiers (`azote`, `ges`, `etp`, `cld`, `mae`, suffix
`_cult`), config labels, file names, **recap keys and CSV names** (a persisted format), dashboard
strings, and the docs.

### Rules applied

1. **A glossary fixes each translation once** (`docs/glossary.md`).
2. **GAMS identifiers are not translated** when they name a GAMS object (`Eq_BC_QUOTA_MAX`,
   `Rdt_Cult`, the column names `ALTI_MIN`, `PENTE`): they anchor parity. The English name lives
   in Python, the GAMS name in the docstring or the `label`.
3. **Old runs are read, not rewritten.** `case_studies/guadeloupe/legacy_names.py` renames legacy
   keys, labels, coordinates and CSV names on the way in; `apps/dashboard/loaders.py` and the
   scripts go through it. `references.yaml` accepts `[new_name, legacy_folder]`.
4. **Checked at each step**: `golden_snapshot.py` identical through the rename map (682/682
   checksums, no value changed), `check_references.py` 10/10, the fast test suite, and every
   dashboard page run headless on the real runs.
5. **Comment review in the same pass.** Found and fixed, among others: a config comment
   describing `Eq_IG_CLD` backwards ("IG_TUT only where the black-leaf-streak risk ≤ 3" — the rule
   forbids it where the chlordecone risk is ≤ 3), a "fail after 1 h" safety net set at 3 h, a
   claim that the CF price tables were never read (they are, since 2026-09-08), per-farm PAD
   figures in `04-vigilance.md` that belonged to the parity run, and the undocumented core entry
   points.

---

## 3. Work item C — data: catalogue, access levels, formats (done)

Delivered 2026-09-22 as described below: `docs/data/catalogue.yaml` (41 tables, the levels of
every run-output file), `core/data/catalogue.py` + `core/data/workbook.py`,
`scripts/build_data_templates.py` and `scripts/validate_data_workbook.py`. The export by level
exists for inputs (`--max-level`); for run outputs it remains roadmap `level-export`. The levels
themselves stay a proposal (`data-levels-validation`). Usage: `docs/data/README.md`.

### The prerequisite: classify before protecting

One cannot filter by access level data whose level nobody has written down. First deliverable:
a **catalogue** (`docs/data/catalogue.yaml`, versioned even though `data/` is not) — one entry per
table and, where needed, per column: source, licence, owner, date, spatial resolution,
**sensitivity level**.

### Proposed levels (to validate with INRAE and its data protection officer)

| level | content | examples in the repository |
|---|---|---|
| **0 — public** | aggregates at commune level or above, sources already published | published Agreste, Tables 1-2 of the article, territorial results |
| **1 — partner** | aggregates by sub-region, farm type, crop; scenario results | policy x forcing grid, Pareto fronts |
| **2 — restricted** | anything at plot or farm level | `allocation_output.csv`, `revenue_by_farm.csv`, the Map page, the typology |

Two points that fix the border, to confirm rather than assume:

- **The plot <-> farm link is what makes the data personal.** A plot alone is public (the
  anonymised RPG is); the same plot attached to a farm, with its revenue, identifies a farmer
  (GDPR).
- **Statistical confidentiality** applies to aggregates derived from agricultural statistics:
  the usual rule (at least 3 units, none weighing more than 85 %) is to confirm with the data
  producer. A commune-level aggregate of level 0 can breach it in a small commune.

### Where access control lives

**Not in MOSAICA.** Authentication and roles belong to MAELIA's information system (database,
views per level, accounts). MOSAICA's role is twofold: (a) **label** each run output with its
level (an `outputs/output_N/` folder is today level 2 as a whole), and (b) provide an **export by
level** — `export --level 1` that aggregates and suppresses what exceeds it (roadmap
`level-export`). The current dashboard is a level-2 tool; that is not a defect, but it must be
written down.

### Formats: one schema, two products

One description per table (types, units, bounds, foreign keys, level). It generates:

1. **the fill-in Excel workbook**, in the style of a carbon assessment: a *Read me* sheet, one
   sheet per table, a units row, drop-down lists taken from the referentials (crop codes,
   communes), cells to fill in yellow, computed cells locked in grey, an example row, and a
   *Sources* sheet where each coefficient carries its reference;
2. **the validator**, which reads the filled workbook back, checks types, bounds, units and keys,
   and produces either a readable error report or the tables ready for the information system.

Three directions of flow to keep apart: **add** (a new table version, a new year, a new
territory), **mobilise** (read for a run), **export** (to a partner, filtered by level). Each
table version is immutable, dated and hashed; the recap records the fingerprints of the tables it
read, as it already records `year` and `scenario`.

---

## 4. Work item D — MAELIA -> MOSAICA: simulated yields and ITKs (postponed)

### What changes in MOSAICA — little, but in one precise place

Today **the margin and every rate are indexed by crop alone**: `crop_margin_per_ha[crop]` in the
objective (`core/model/objectives.py`), `Rdt_Cult` per crop, `crop_indicator_rates` per crop. A
simulated yield depends on soil and climate, so it is indexed by **(simulation unit, crop, ITK)**.

`ModelInputs` needs a **per-pair** coefficient channel — `pair_margin_per_ha[(plot, crop)]`, falling
back on the per-crop value — and the same for indicator rates. The size of the MILP does not
change (same `Y` variables), the objective stays linear. It is testable without data, in the
style of the current tests.

### Points to hold

- **Pre-computation, never MAELIA inside the loop** (thesis item `PERSP-D`): MAELIA runs offline
  over the grid (unit x crop x ITK x climate years) and produces a table. What changes is not the
  model but the provenance of `Rdt_Cult`.
- **The simulation unit is not necessarily the plot.** A soil-climate unit (soil type x rainfall
  class x altitude class) bounds the cost of MAELIA; every plot of a unit inherits its yield.
- **ITK is already a dimension of MOSAICA**: the 84 fine crops are crop x itinerary variant pairs
  (`CS_MG_NISM`…). MAELIA's ITKs must map onto these codes or create new ones. **Trap B.3**: two
  variants equal on every parameter read make the branch-and-bound unusable;
  `check_scenario_feasibility.py` already detects them.
- **Variance comes with it.** N climate years give the mean *and* the variance of the yield per
  pair — which would replace `Var_Rdt_Cult` (frozen on `init`, per crop) in the Markowitz
  objective.
- **Parity stays reproducible**: a switch `data.yield_source: gams_table | maelia`, with
  `check_references.py` kept on `gams_table`.
- **Consequence for calibration, to anticipate**: the current yields are 1 to 4x those of the
  territory (vigilance C.1), and the market ceilings (plantain 6 440 t) partly compensated for that
  surplus. More realistic simulated yields may make those ceilings useless or misplaced: **plan a
  recalibration**, not a mere column replacement.

### Interface contract (draft)

Table `simulated_yields`: `unit_id, crop_code, itk_code, climate_series, year, yield_t_ha,
[water_use_mm, n_uptake_kg_ha, labour_h_ha…], maelia_version, maelia_run_id`. Plus a table
`unit_of_plot` (`plot_id -> unit_id`). The data catalogue of work item C is where both get their
schema.

### To check during the training

What MAELIA actually simulates and with which crop model (as far as I know MAELIA runs on the
GAMA platform and relies on a simplified crop model of the AqYield type — **to confirm**);
**whether the tropical crops** (cane, banana, yam, plantain, pineapple, tropical market gardening)
**are parameterised in it**, which may alone be the largest cost of the work item; the input and
output formats; the licence and the access to the information system.

Guide: GAMA and AqYield / AqYieldNC confirmed (HerbSim for grassland); licence GPLv3; formats
in `docs/maelia/reference.md`. **No tropical crop is mentioned** and no mechanism for
multi-year crops is described (M.2). Two corrections to the plan above: the simulated yield is
`RENDEMENT_OPTIMAL` scaled down by water and nitrogen stress, and `RENDEMENT_OPTIMAL` is an
**input to adapt to the territory** — so the coupling moves the yield-level question of
vigilance C.1, it does not answer it (M.1); and the "simulation unit" exists as MAELIA's
**virtual-plot** mode (forced rotation, soil, weather cell), sweepable in batch (M.7).

---

## 5. Work item E — MOSAICA -> MAELIA: the cropping plan tested at a daily time step (postponed)

The idea — optimisation sets strong, coarse constraints, the agent-based model reveals implicit,
finer ones — is the right division of labour. Four points make it operational.

### 5.1 — The plot referential is the first obstacle

MOSAICA's plots are **synthetic** ids `P1..Pn`. The join to the RPG goes through a farm signature
at **99.4 %**, and **~1 557 plots have an interchangeable twin** (vigilance F.1). MAELIA needs
real geometries. Hence: a deterministic, documented rule for the twins (indistinguishable for
MOSAICA, so the arbitrariness does not affect the optimum, but not necessarily for MAELIA, which
sees the geometry), and an explicit treatment of the 0.6 % unjoined. If MAELIA's information
system holds the RPG with its real ids, **the best is to rebuild MOSAICA's plot set from the
information system** rather than keep joining after the fact.

### 5.2 — Static vs dynamic: a decision to take before coding

MOSAICA produces a cropping plan for **one** year; MAELIA simulates years with successions. Three
options:

| option | what MAELIA receives | drawback |
|---|---|---|
| a | the same plan every year | unrealistic for rotations (market gardening, 5-7-year cane cycles) |
| b | MOSAICA's plan in year 1, then its own rules | only the first year is tested |
| c | target area shares per farm, rotations left to MAELIA | the most realistic, but MAELIA then decides part of the plan |

This decision joins the **multi-period model** of the roadmap (`multi-period`).

### 5.3 — Force execution, do not let it re-decide

If MAELIA's agents keep their own cropping-plan rules, two decision models are compared instead
of one being tested. For the test, the agent must **execute** the plan: only tactical decisions
(sowing dates, irrigation triggers, order of field operations) stay free. To check: that MAELIA
allows a cropping plan to be imposed.

Guide: **it does** — `nomChoixAssolement = 'Donnees'` reads each plot's crop sequence from
`parcelles.shp` (`SEQUENCE`) and leaves the agents only tactical decisions (M.3). But the ITK
is not chosen in MAELIA, it follows from (crop, previous crop, soil, farm type, climate,
irrigation): a MOSAICA variant must become its own MAELIA species to be imposed (M.4). And
the machinery row of §5.4 cannot be measured: tool entries have no effect in MAELIA yet (M.8).

### 5.4 — Define what is measured before launching

A list of gap indicators, written before the first run, otherwise one reads what suits:

| implicit constraint | MAELIA indicator | what MOSAICA already knows |
|---|---|---|
| labour | weekly peaks per farm vs available | only an **annual** cap (`farm_labor_hours_max`) |
| machinery | use conflicts (a tractor needed on two jobs in the same window) | nothing |
| water | days of water stress, irrigation demand vs resource | a **monthly** need (`water_need_peak_month_m3`) — directly comparable |
| nitrogen | days of deficiency, residues | an annual total per crop |
| yield | simulated achieved vs planned by the optimisation | the tabulated yield |
| margin | achieved vs planned | the solve's margin |

### 5.5 — One pass first, a loop later

Start with a **one-way evaluation**: the optimised plan, simulated, and the gap table. Only if
the gaps are systematic, translate what MAELIA reveals into MOSAICA constraints (monthly labour
cap, achieved yields) and re-solve with a warm start. Such a loop **does not necessarily
converge** (it can oscillate): stopping criterion fixed in advance, three iterations at most, and
the cost counted — 30-60 min per MOSAICA solve plus the duration of a daily MAELIA run, unknown
to date.

---

## 6. Questions still open

**For the MAELIA training / the supervisors**

1. Tropical crops parameterised or not; crop model used; input and output formats; possibility
   of imposing a cropping plan. *(Guide, 2026-09-23: crop model, formats and imposing a plan
   answered; tropical and perennial crops still open — the updated list is in
   `docs/maelia/README.md` § Questions left for the training.)*
2. Does the information system hold the RPG with its real ids? (Decides § 5.1.)
3. Who validates the access levels (INRAE's data protection officer, agreements with the data
   providers)?
4. One-way evaluation, or an iterated loop — and the matching computation budget.
