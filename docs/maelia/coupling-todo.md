# MAELIA ↔ MOSAICA coupling: to-do

The two work items of the [2026-09-22 spec](../superpowers/specs/2026-09-22-post-thesis-maelia-data-english-design.md)
share one trunk — **Guadeloupe must exist in MAELIA** — and then split:

```
                        ┌── D. MAELIA -> MOSAICA: simulated yields and ITKs replace Rdt_Cult
I. Guadeloupe in MAELIA ┤
                        └── E. MOSAICA -> MAELIA: is the optimised plan robust to finer,
                               implicit constraints (labour peaks, water, nitrogen, timing)?
```

Roadmap items: `maelia-guadeloupe-instance` (I), `maelia-yields` (D), `maelia-daily-test` (E),
`pair-coefficients` (D.5). The *why* of each point is in [README.md](README.md) § M (M.1…M.9);
the per-crop work list is [crop-parameters.md](crop-parameters.md).

**Who**: **C** Clément · **MT** MAELIA team (Renaud Misslin for the ITK application, "Jean"
for runs, Olivier and Renaud for new species) · **S** supervisors. **Now** marks what does
not need MAELIA and can start before the training.

---

## I. Common trunk — a Guadeloupe instance in MAELIA

Agricultural module only at first (`executerModeleHydrographique = FALSE`,
`executerModeleNormatif = FALSE`): water is then unlimited, as in MOSAICA (M.5).

### I.0 — Training and access

- [ ] Get the `MAELIA_xxx_GAMA_yyy.zip` archive and install the matching GAMA "with JDK" (MT, C)
- [ ] Account on the ITK web application (Renaud Misslin) (MT)
- [ ] Run the shipped example (Aveyron) end to end; **time one run** — the budget of D and E
      depends on it (spec §5.5) (C)
- [ ] Ask the [questions left for the training](README.md#questions-left-for-the-training),
      first of all: tropical and perennial crops (M.2) (C)
- [ ] Update `docs/maelia/README.md` with the answers (every *to confirm*) (C)

### I.1 — Decisions to take before coding

| # | decision | options | who | blocks |
|---|---|---|---|---|
| I.1a | source of `RENDEMENT_OPTIMAL` (M.1) | Agreste yields, Chopin et al. Table 1, experts, MAELIA calibration on observed yields | S, C | D, E |
| I.1b | how perennials are simulated (M.2) | a MAELIA mechanism if it exists; else cane as a looping sequence `plantation_ratoon_ratoon…`, banana/orchards as a repeated annual species | MT | I.3 |
| I.1c | AqYield or AqYieldNC | NC gives nitrogen but **drops grassland** (M.2) | C, MT | I.3, E.2 |
| I.1d | plot referential (M.6, spec §5.1) | rebuild MOSAICA's plot set keyed on RPG ids **(recommended)**, or keep the farm-signature join | C, S | I.6, E.3 |
| I.1e | static or dynamic plan (spec §5.2) | a: one-token `SEQUENCE` repeated; b: MOSAICA's crop then a rotation; c: MAELIA decides | S | E |
| I.1f | pilot crops | one annual crop with the most ✓ in crop-parameters.md (yam `IG_PLA`, melon `ME`), then cane (largest area, perennial) | C | I.3 |

### I.2 — Weather

- [ ] Find a daily series for Guadeloupe (Météo-France stations, *to confirm* with MT; SAFRAN and
      E-OBS do not cover it): rain, Tmin, Tmax, ETP, radiation, over ≥ 10 years (C, MT)
- [ ] Build the grid `polygonesMeteoFrance.shp` (`ID_PDG`, `POSX`, `POSY`, `ALTI_MOY`) — e.g.
      station polygons crossed with the rainfall classes of `data/gis/05_Pluviométrie` (C)
- [ ] Write `meteo/observee/<year>.csv` in the fixed column order
      `ID_PDG;DATE;RRmm;Tmin;Tmax;ETP;RGI`, by code, never through Excel (M.9) (C)

### I.3 — Species (work list: [crop-parameters.md](crop-parameters.md))

- [ ] Pilot crop (I.1f): fill its `especesCultivees.csv` column — the ✓/~ from MOSAICA's
      tables, the ✗ (phenology, water response, N demand) from FAO-56/33 and CIRAD references,
      reviewed with MT (C, MT)
- [ ] One species per MOSAICA variant that E will impose (M.4) — or group variants that only
      differ by region into one species with a regional criterion (C, MT)
- [ ] Grassland: HerbSim parameters (`especesHerbSim.csv`) (MT)
- [ ] Remaining crops, by area: cane, banana, grassland, market gardening, plantain, yam, the rest (C)

### I.4 — ITKs

- [ ] **Now** — script drafting each ITK from `Matrice_OTK_Cult`: operations typed onto MAELIA's
      7 types, doses, work time (h/ha), products; list the untyped operations per crop (C)
- [ ] Dates (1-3 sub-periods per operation) and trigger thresholds from experts and technical
      sheets — the largest ✗ of crop-parameters.md (C, experts)
- [ ] Enter them in the ITK application; export `reglesDeDecisions*.csv` (C)
- [ ] `engrais.csv`: mineral fertilisers from `Data_OTK`; organic ones (manure, compost,
      `FERTI_MA_*BIO`) need decomposition parameters (C, MT)

### I.5 — Soils

- [ ] Map `TYPE_SOL` / Colmet-Daage units (`data/gis/04_Pédologie`) onto `ZONE_PEDO` (C)
- [ ] Horizon properties per soil unit (clay, stones, bulk density, available water, Ksat,
      depth; + pH, C/N, OM for NC) from the literature on the five Guadeloupe soils (C, MT)
- [ ] `typeDeSolParZH.shp` with the fields the coherence check requires (reference.md) (C)

### I.6 — Farms, blocks, plots

- [ ] **Now** — `ilots.shp` and `parcelles.shp` from the RPG layer: `ID_EXPL` ← `pacage`,
      `ID_ILOT` ← `pac_ilot`, `ID_PARCELL` ← `pac_ilot_parcelle` (M.6; *to confirm* with MT) (C)
- [ ] `exploitations.csv` (`TYPE_EXPL`: MOSAICA's 8 types or `*`), `materiel.csv`, irrigation
      equipment of the irrigable blocks (C)
- [ ] These tables are **access level 2** (`pacage`): declare them in `docs/data/catalogue.yaml` (C)

### I.7 — Economics

- [ ] **Now** — export `prixVentes.csv`, `primes.csv` (per-tonne aids turned into €/ha),
      `chargesOp.csv` from MOSAICA's tables; `chargesDePassage.csv` is missing (C)

### I.8 — First runs

- [ ] Coherence check of the zipped `includes/` in the ITK application: no ERREUR (C)
- [ ] One farm (`executerSurEnsembleExploit`), then one region, then the island (C)
- [ ] Read the console warnings; record the duration of a full-island year (C)

### I.9 — The exporter, in the repository

- [ ] **Now** — one module writing every MAELIA file from the `Dataset` (`;`, `.`, no quotes,
      `|` for sub-periods), tested data-free like the rest; each exchanged table in the data
      catalogue (C)

---

## D. MAELIA → MOSAICA — simulated yields and ITKs

**Goal**: replace `Rdt_Cult` (one yield per crop) and `Var_Rdt_Cult` (one variance per crop) by
values simulated per (simulation unit, crop), so that soil and climate enter the margin.
**Done when** a calibrated run with `data.yield_source: maelia` exists, its PAD is reported
against the parity run, and the differences are explained.

- [ ] **D.1 Simulation units.** Define the unit (soil type × rainfall class × altitude class ×
      weather cell), the table `unit_of_plot`, and count units × crops × climate years = the
      number of simulations; choose the grain from the run time measured in I.0 (C)
- [ ] **D.2 Virtual-plot batch** (M.7): launcher with `executerParcelleVirtuelle`,
      `rotationForceeParcelle` = the crop, `typeDeSolForceParcelle`, `idPointMeteoUnique`;
      sweep with `among:` in batch headless. *To confirm*: how the virtual plot picks its ITK
      (`idSdcForce`?) (C, MT)
- [ ] **D.3 Read the outputs**: `RECOLTE_rendement` per year from `suiviOTParParcelle.csv`,
      **year 1 dropped** (it starts in August); water use and N uptake from `sorties_eau` /
      `sorties_CN` → table `simulated_yields` (spec §4 schema), in the data catalogue (C)
- [ ] **D.4 Check the level**: MAELIA's mean yield per crop against Agreste and Chopin et al.
      Table 1, and against `Rdt_Cult` — this is where vigilance C.1 is settled or moved (C, S)
- [ ] **D.5 Per-pair coefficients in MOSAICA** — **Now**, it needs no MAELIA:
      `ModelInputs.pair_margin_per_ha[(plot, crop)]` falling back on the per-crop value, same
      for the indicator rates and the variance; the margin recomputed per pair (sales, POSEI
      per tonne and harvest/transport costs all scale with yield); switch
      `data.yield_source: gams_table | maelia`, `check_references.py` kept on `gams_table`;
      data-free tests (C)
- [ ] **D.6 ITKs**: map MAELIA's ITKs onto MOSAICA's fine codes, create codes for ITKs MOSAICA
      lacks; run `check_scenario_feasibility.py` for new symmetric groups (vigilance B.3) (C)
- [ ] **D.7 Recalibrate**, don't just swap the column: market ceilings (plantain 6 440 t) partly
      compensated the yield surplus and may become useless or misplaced (spec §4) (C, S)
- [ ] **D.8 Document**: vigilance entry, `parameter_choices.yaml` (yield source), roadmap (C)

---

## E. MOSAICA → MAELIA — robustness of an optimised plan to finer constraints

**Goal**: have MAELIA's agents *execute* an optimised cropping plan at a daily time step, and
measure what MOSAICA's annual, coarse constraints could not see. **Done when** the gap table
(E.2) exists for the selected calibration run against its control (E.5), with its reading
written up.

- [ ] **E.1 Decide the dynamics** (I.1e) and what a perennial becomes in `SEQUENCE` (I.1b);
      pick the plans to test: `calib_selected` first, then prospective scenarios (S, C)
- [ ] **E.2 Write the gap indicators before any run** (spec §5.4), each with its threshold (C, S):

  | implicit constraint | MAELIA output (M.8) | MOSAICA counterpart |
  |---|---|---|
  | labour peaks | `suiviOTParParcelle.csv` `temps` → hours per farm per week | annual cap `farm_labor_hours_max` |
  | timing | operations delayed or missed (sowing out of window → alternative ITK) | none |
  | water | `sorties_eau` satisfaction index, days of stress, irrigation | gross annual need (vigilance C.4) |
  | nitrogen | `sorties_CN` satisfaction, leaching (NC only) | fertiliser N per crop |
  | yield | `RECOLTE_rendement` achieved | `Rdt_Cult` |
  | margin | rebuilt from yields × `prixVentes` + `primes` − `chargesOp` | the solve's margin |
  | machinery | **not measurable** — tool entries have no effect in MAELIA (M.8) | none |

- [ ] **E.3 Export the plan** — **Now** for the code: `allocation_output.csv` → per plot
      `SEQUENCE`, `EXPREST`, `CULT_REF`, under `nomChoixAssolement = 'Donnees'` (M.3); a
      deterministic rule for the ~1 557 interchangeable twins and the 0.6 % unjoined plots
      (vigilance F.1) unless I.1d rebuilt the plot set; `zone_filter` runs would need the
      out-of-area blocks (C)
- [ ] **E.4 Labour on both sides**: `avecContrainteDeMainOeuvre = TRUE`; the same labour
      availability per farm as MOSAICA's budget; add back the hours of the operations MAELIA
      has no slot for (column *Untyped h* of crop-parameters.md) or the comparison is biased
      downwards (C)
- [ ] **E.5 Run a control first**: the **observed 2017 plan** in MAELIA, then the optimised
      plan, over the same climate years. The gaps that matter are *optimised minus observed*:
      MAELIA's own gap to reality must not be read as a flaw of the plan (C)
- [ ] **E.6 Analysis script**: MAELIA outputs → the E.2 table per farm, region, crop, and the
      comparison with the run's `recap.json`; outputs at plot/farm level are access level 2 (C)
- [ ] **E.7 Only if the gaps are systematic**: turn them into MOSAICA constraints (monthly or
      weekly labour cap, achieved yields) and re-solve with a warm start; stopping criterion
      fixed in advance, three iterations at most (spec §5.5) (C, S)
- [ ] **E.8 Scenario plans**: same test on the prospective policies (e.g. P4 status quo vs P8
      agroecological transition) — robustness becomes a criterion between policies (C)
