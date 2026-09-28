# MAELIA — what its user guide says, and what it changes for the coupling

MAELIA is the INRAE agent-based platform MOSAICA is to be coupled with, in both directions
(roadmap `maelia-yields`, `maelia-daily-test`; design in
[the 2026-09-22 spec](../superpowers/specs/2026-09-22-post-thesis-maelia-data-english-design.md)
§4-5). This page digests the **MAELIA user guide** (*Guide de l'utilisateur de MAELIA*, team
UMR LAE + MAELAB, published 2026-08-18) so that nobody has to reread 170 pages of French PDF
to answer a coupling question. It has three parts:

1. **MAELIA in brief** — what it is, how a run is set up, how a scenario is built;
2. **What it means for MOSAICA** (§ M) — answers to the spec's open questions, and the traps
   the guide reveals. **Read this part before any coupling work;**
3. **Questions left for the training** — what the guide does not settle.

The file-by-file detail (input tables and their fields, launcher parameters, output columns,
trigger rules) is in **[reference.md](reference.md)**. What to do, step by step, is in
**[coupling-todo.md](coupling-todo.md)**; what MOSAICA's tables already give for creating each
crop in MAELIA, in **[crop-parameters.md](crop-parameters.md)**.

**Sources.** The PDFs are in `context/maelia/`, with plain-text extracts in
`context/maelia/text/` (made with `pdftotext -layout -enc UTF-8`; grep those rather than the PDFs).
The guide is a web book printed to PDF: some wide tables are **clipped in the source** (the
agricultural-module launcher table has lost its description column), and it carries a few
copy-paste errors (listed in reference.md § Errata). **Field names quoted from the guide are
indicative until checked against a real `includes/` folder.** The online documentation it
points to is `http://maelia-platform.inra.fr`.

Status of this page: written **before the MAELIA training**, from the guide alone. Anything
marked *to confirm* is an inference, not a statement of the guide.

---

## 1. MAELIA in brief

### What it is

A **multi-agent platform for integrated modelling and assessment of agricultural territories**:
it simulates, at a **daily time step** and over several years, farmer agents conducting their
crops plot by plot, the water cycle, nitrogen and carbon, and water management. Indicators:
water, nitrogen and carbon cycles, soil quality, **semi-net margin**, labour (nature and
quantity), from plot to territory — as a multi-year mean **and** as a dynamic, hence
resilience to climate, price and policy variability. Licence **GPLv3**.

It is written in **GAML** on the **GAMA** platform (UMI UMMISCO). It is made of:

| module (launcher switch) | what it simulates | underlying model |
|---|---|---|
| agricultural (`executerModeleAgricole`) | farmer agents, crop sequences, technical operations triggered by decision rules, crop growth, irrigation, fertilisation | crop model **AqYield** (water) / **AqYieldNC** (+ nitrogen and carbon); a "simple" crop model; **HerbSim** / HerbSimNC for grassland |
| hydrological (`executerModeleHydrographique`) | runoff, rivers, reservoirs, aquifers, withdrawals | **SWAT** formalisms (or a simplified rainfall-runoff model) on elementary watersheds |
| normative (`executerModeleNormatif`) | dam releases for low-water support, withdrawal restrictions | rules per administrative zone |
| supply chains (filières) | organic residual products (sludge, digestate, compost), processing units | recipes, stocks, transport |
| other uses | drinking-water demand from INSEE population data | in stabilisation |

Switching the hydrological module **off** makes water resources unlimited; switching the
normative module off removes dams and restrictions. **The agricultural module alone is a
valid configuration** — the one work item D needs.

### Vocabulary

| MAELIA (French) | English | MOSAICA counterpart |
|---|---|---|
| terrain / territoire | study area | the case study (`case_studies/guadeloupe/`) |
| dossier *includes* | the study area's input folder (csv + shp) | `data/` |
| *models* | the GAML code | `core/` + `case_studies/` |
| lanceur / launcher (`.gaml`) | run configuration + entry point | `config.yaml` + `main.py` |
| solution de modélisation | a chosen set of modules, data and parameters | one run's `config_used.yaml` |
| îlot (PAC) | CAP block (a group of parcels of one farm) | — (no block level) |
| parcelle | plot, the simulation unit | plot `P1..Pn` |
| exploitation (`ID_EXPL`) | farm | farm (`EXPL`) |
| `TYPE_EXPL` | farm type (an ITK criterion) | farm type (`TYPE_EXPL`, 8 types) — same name, **not** the same typology |
| séquence (`SEQUENCE`) | crop sequence of a plot, read in a loop | — (one crop per plot, one year) |
| espèce (`ID_ESPECE`) | crop species with its growth parameters | fine crop code (`CS_MG_NISM`) |
| ITK, règles de décision | crop management sequence, as decision rules | the ITK part of the fine crop code |
| OT (opération technique) | technical operation (PREPA, REPRISE, SEMIS, BINAGE, RECOLTE, IRRIGATION, FERTI, PHYTO) | operation (`crop_operation_matrix`) |
| zone pédologique (`ZONE_PEDO`) | agronomic soil group | `TYPE_SOL` |
| BVe / ZH | elementary watershed ("ZH" in the code means BVe) | watershed (`code_bv`, `data/gis/10_*`) |
| HRU | hydrologic response unit (soil × land use × slope) | — |
| CI (couvert intermédiaire) | cover crop (species codes start with `ci`) | — |
| gel | set-aside; needs no ITK | fallow (JA) |
| marge semi-nette | margin after operational **and** machinery (passage) costs | gross margin (operational costs only) |

### How a run is set up

1. **Install GAMA** (a "with JDK" build), then import the archive `MAELIA_xxx_GAMA_yyy.zip`
   **without unzipping it** (*User models > Import > GAMA Project*). xxx is the MAELIA
   version, yyy the GAMA version it was built for — install that GAMA or newer. The archive
   is obtained from the MAELIA team.
2. The workspace holds `includes/<study_area>/` (data: `modeleCommun`, `modeleAgricole`,
   `modeleHydrographique`, `modeleNormatif`) and `models/` (`main/` holds the launchers,
   plus one folder per module, `output/`, `processus/`, `testsUnitaires/`).
3. **Copy** `models/main/launcherBase.gaml` to your own launcher, rename its `model` line,
   and set its `parameter` lines — study area (`nomDecoupageZonePourLectureFichiers`), start
   year, number of years, modules on/off, outputs. All parameters: reference.md § Launcher.
4. Press the green button: **initialisation** (tens of seconds) — read the console, it lists
   errors (blocking) and warnings (e.g. a missing file means snow is not simulated). Then
   *play*. The console prints each simulated day.
5. Outputs land in `models/main/log/<study_area>_<timestamp>/`.

**Two timing rules that matter for reading outputs.** The first simulated year **starts in
August**, so that the cropping plan is consistent from the **second** year on: drop year 1.
And the **reference year** (`anneeDeReferenceRPG`) aligns the looping crop sequences on the
observed years — set it to the year of the last crop of each `SEQUENCE`.

**Speed.** Outputs are daily and big; each extra output slows the run. Test on a subset first:
`simulationSurZH` (some watersheds), `executerSurEnsembleExploit` (some farms),
`simulationSurParcelle` (one plot), or `executerParcelleVirtuelle` (one virtual plot with a
forced rotation, soil and area — see M.7). For many runs, switch the launcher's `experiment`
to `type: batch until: simulationTerminee parallel: N`, let a parameter take its values from
an `among: [...]` list, remove every `display`, and run it **headless**:
`gama-headless.bat -batch <experiment> "<path to launcher>.gaml"` (add `-memory XG`). GAMA 1.9
only maintains the batch headless mode.

### How a scenario is built

**A scenario is a modified copy of the `includes/` folder** (`Aveyron_Ref` → `Aveyron_SC1`)
plus a copy of the launcher pointing to it. What one edits: weather files (climate), dam and
restriction files (water supply), `parcelles.shp` `SEQUENCE` (the spatial distribution of
cropping systems), `reglesDeDecisions.csv` (ITKs: irrigation, sowing, tillage), and the
`marcheAgricole/` files (prices, subsidies, costs). Price scenarios can also live side by side
(`prixVentesSC1.csv`, `prixVentesSC2.csv`) and be picked from the launcher.

The guide ships R functions (by Renaud Misslin, MAELAB) to rewrite sequences in bulk: shares
of area per crop, share of monocultures, deleting or inserting a crop, replacing whole
sequences or two-crop sub-sequences, and re-deriving the export/return (`EXPREST`) sequence
after any change — list in reference.md § R functions.

### How crop management is described (ITKs)

An ITK is attached to **exactly one crop** and to a set of **spatialisation criteria**:
**crop, preceding crop, soil zone (`ZONE_PEDO`), farm type (`TYPE_EXPL`), climate zone,
irrigation equipment**. The rule that governs everything: **every agronomic situation the
simulation meets must be covered by one and only one ITK.** `*` means "all values".

Each operation has 1 to 3 **sub-periods** (Julian days, which may wrap over New Year), each
with trigger constraints (soil moisture, cumulative rain over N days, temperature over N days,
vegetation stage, forecast rain…); the agent tries sub-period 1, then relaxes to 2, then 3.
Irrigation has one window, split by vegetation stage. Fertilisation is organised as ordered
**strategies** of up to 4 applications each; the agent picks the first whose fertilisers are
in stock, 15 days before the earliest application — a last, 100 %-mineral strategy with an
unlimited stock guarantees one applies.

ITKs are entered in a **web application** (login from Renaud Misslin, MAELAB), which exports
`reglesDeDecisions.csv` and `reglesDeDecisions_fertilisation.csv`, and runs a **coherence
check** on a zipped `includes/` folder (≤ 30 MB; verdicts OK / ATTENTION / ERREUR). ITK names
must be unique **across all study areas** of the application, without accents.

---

## M. What it means for MOSAICA

Each point says what the guide establishes, and what follows for the coupling. The spec's
questions (§4 "to check during the training", §5.3, §6) are answered in M.1-M.4.

### M.1 — The crop model is AqYield, and its yield is a potential scaled down by stress

**Confirmed**: GAMA, and AqYield / AqYieldNC for crops (HerbSim for grassland). Growth is
driven by degree-days (`Tbase`, `Tmax`, sums at emergence, flowering and maturity, a winter
brake `FREIN`), water stress through `Yield/YieldMax = f(ETR/ETM)`, and nitrogen stress in the
NC version. The yield an agent harvests (`RECOLTE_rendement`, t/ha) is **`RENDEMENT_OPTIMAL`
reduced by those stresses** — and the guide says `RENDEMENT_OPTIMAL` **must be adapted to the
study area (mandatory)**.

-> **The yield level is still an input.** Vigilance [C.1](../04-vigilance.md) (model yields
1-4x the territory's) is not cured by the coupling unless `RENDEMENT_OPTIMAL` comes from a
territorial source. Filling it from `Rdt_Cult` would reproduce the overstatement with a
daily-time-step alibi. What MAELIA adds for sure is the **variation**: per plot (soil,
weather), per year (climate), and the resulting variance — the part that would replace
`Var_Rdt_Cult`. Plan the recalibration the spec already calls for, and decide the source of
`RENDEMENT_OPTIMAL` explicitly (candidates: Agreste yields, Chopin et al. Table 1, experts).

### M.2 — Tropical crops: nothing in the guide; perennials: no documented mechanism

The guide's examples are all temperate field crops (wheat, maize, sunflower, rapeseed, pea,
barley, soybean, cover crops), on Aveyron and the Adour-Garonne basin. No sugarcane, banana,
yam, pineapple, plantain or market-gardening species is mentioned. A crop missing from the
MAELIA species list can be **created by hand** in `especesCultivees.csv` by copying the growth
parameters of an existing species — "in full knowledge of the consequences and in
coordination with the thematic MAELIA referent"; the application cannot do it.

And the structure is **annual**: a sequence is a list of one crop per year (cover crops aside),
operations sit in Julian days within a year, and the first year starts in August. Nothing
describes a crop occupying the ground for 18 months (pineapple), a 5-7-year cane plantation
with ratoons, a banana plantation or an orchard.

Grassland goes through HerbSim, and **AqYieldNC cannot simulate grassland** yet (`prairiep`,
`prairiet` are forbidden in sequences under it) — while grassland is a floor of 6 096 ha in
MOSAICA (vigilance C.3). Choosing the NC version for nitrogen therefore leaves grassland out.

-> **Parameterising the tropical crops is the largest unknown of both work items**, as the
spec feared: species parameters (degree-days, Kc, stress coefficients, N demand), ITKs for
each (crop, previous crop, soil, farm type, irrigation) situation, and a way to represent
multi-year crops. First question for the training.

### M.3 — A cropping plan **can** be imposed: `nomChoixAssolement = 'Donnees'`

The launcher chooses how crops are assigned (`nomChoixAssolement`): **`'Donnees'` = the crops
are supplied by the data**, i.e. read from each plot's `SEQUENCE` in `parcelles.shp`; the
alternatives are a belief-function choice model (`'FonctionsDeCroyances'`, with farmer
profiles weighting income, income variability, free days and transaction costs — "expert
mode"), a multicriteria method, and a date/dose file (`dateDose.csv`: `id_parcelle;culture;
an…`). The description column of that table is clipped in the PDF: the exact option strings
other than `'Donnees'` are *to confirm*.

With `'Donnees'`, the agent does not choose the crop; it only takes **tactical** decisions —
when to sow, till, fertilise, irrigate, harvest, within the ITK windows and triggers. That is
precisely what spec §5.3 asked for ("force execution, do not let it re-decide").

-> MOSAICA → MAELIA is **writing `SEQUENCE`** (and `EXPREST`, same length) per plot. The
spec's §5.2 options map directly: (a) a one-token sequence `"crop"` repeats every year; (b)
MOSAICA's crop for year 1, then a rotation; (c) needs `'FonctionsDeCroyances'`, i.e. letting
MAELIA decide. Sequences loop, so the preceding crop of the first token is the **last** one —
it selects the ITK (M.4). `INDEX_DEP` (start rank) and `CULT_REF` (crop in the reference
year) align the loop.

### M.4 — In MAELIA the ITK is **determined** by the situation; in MOSAICA it is **chosen**

MOSAICA's 84 fine crops are crop × ITK variants, and the optimiser picks the variant
(`CS_MG_NISM` vs another cane variant) plot by plot. In MAELIA the ITK is not a decision: it
follows from (crop, previous crop, soil zone, farm type, climate zone, irrigation equipment),
one situation = one ITK. And **two declared crops may not map onto the same MAELIA species**
(to keep that uniqueness).

-> To hand MAELIA a plan that says *which variant*, each variant must become **its own MAELIA
species** (a copied `especesCultivees.csv` column, a distinct `ID_ESPECE` usable in
`SEQUENCE`), or the variant must be expressed through a criterion (`TYPE_EXPL` — but that is
per farm, so all the farm's plots would share it). Mind vigilance
[B.3](../04-vigilance.md#karusmart): variants equal on every parameter MOSAICA reads may be
*different* in MAELIA (operations, dates), which is fine there but means the MOSAICA-side
symmetry is not evidence that MAELIA will treat them alike.

### M.5 — What Guadeloupe lacks to instantiate MAELIA

| input | what MAELIA expects | what the repository has |
|---|---|---|
| weather | daily `ID_PDG;DATE;RRmm;Tmin;Tmax;ETP;RGI` per grid cell and year, grid as polygons; sources named: **SAFRAN (metropolitan France) and E-OBS (Europe)** — neither covers Guadeloupe | a rainfall class per plot (`data/gis/05_Pluviométrie`), no daily series (vigilance C.4: not even monthly rain) |
| soils | per soil unit, up to 10 horizons: clay, stones, bulk density, available water, Ksat, depth, structure; for NC also pH, C/N, limestone, OM, water content at field capacity and wilting point; required fields depend on the AqYield version (reference.md) | a soil **type** per plot (`TYPE_SOL`, `Data_Sol.txt`) and the Colmet-Daage map (`data/gis/04_Pédologie`, `Code_pedo`) — **no horizon hydraulics** |
| blocks, plots, farms | `ilots.shp` (`ID_ILOT`, `ID_EXPL`, `ID_SOL`, `ID_ZH`, irrigability, equipment, slope) and `parcelles.shp` (`ID_PARCELL` = `<ID_ILOT>_xx`, `SEQUENCE`, `SURFACE`…) | the RPG 2017 layer carries `pacage` (farm), `pac_ilot` / `num_ilot` (block), `parcelle`, `c_culture`, `surf_parc` — **the MAELIA hierarchy is already there** (M.6) |
| watersheds | `ZH.shp` with the downstream link `ID_ND_EXUT`, SWAT geomorphology from ArcSWAT, HRUs | 230 watersheds of ≥ 50 ha with `code_bv` and outlets (`data/gis/10_Bassins versants`); no topology table, no SWAT parameters |
| species, ITKs | `especesCultivees.csv`, `reglesDeDecisions*.csv` | per-crop tables and operation matrices from GAMS (`Matrice_OTK_Cult_*`), with no dates or triggers |
| economics | sale prices, coupled subsidies per département, operational and machinery costs **per ITK and year** | `Prix_Cult`, subsidies, operation costs per crop (`indice_H` years 2017-2022) |

-> **Start with the agricultural module alone** (`executerModeleHydrographique = FALSE`,
`executerModeleNormatif = FALSE`): water is then unlimited, which is also MOSAICA's
assumption (its water indicator is a need, not a constrained supply). SWAT on Guadeloupe is a
project of its own. A daily weather source for Guadeloupe (Météo-France stations, *to
confirm*) is a prerequisite of anything.

### M.6 — The plot referential: the RPG layer already has MAELIA's keys

`data/gis/01_RPG 2017/RPG_2017_GC_MG*.dbf` holds `pacage`, `pac_ilot`, `num_ilot`, `parcelle`
next to the geometry. `ID_EXPL` ← `pacage`, `ID_ILOT` ← `pac_ilot`, `ID_PARCELL` ←
`pac_ilot` + `_` + `parcelle` is the natural mapping (*to confirm* with the team: the guide
only requires that `ID_PARCELL` start with its block id). MOSAICA's synthetic `P1..Pn` join
that layer at 99.4 % with ~1 557 interchangeable twins (vigilance [F.1](../04-vigilance.md#carte))
— so spec §5.1's recommendation holds, and gets easier: **rebuild MOSAICA's plot set keyed on
the RPG ids** rather than join after the fact.

Two cautions. `pacage` is a farm's CAP number: a table keyed on it is **access level 2**
(`docs/data/README.md`). And MAELIA simulates **out-of-area blocks** of in-area farms
(`ilots_HZ.shp`, `avecIlotsHorsZone`); for an island that is moot, but a `zone_filter` run
handed to MAELIA would need them.

### M.7 — Work item D can run on **virtual plots**

The advanced launcher parameters simulate **one virtual plot** with a forced rotation
(`rotationForceeParcelle = 'c1_c2_c3'`), soil type (`typeDeSolForceParcelle`), reference
cropping system (`idSdcForce`), straw management and area; with `utiliserMemeMeteoPartout` +
`idPointMeteoUnique`, a single weather cell. That is the spec's "simulation unit" (soil ×
climate), and batch mode with `among:` sweeps it in parallel:

```
unit (soil type × weather cell) × crop/ITK × climate years  ->  RECOLTE_rendement per year
```

The per-year yields give the mean **and** variance per (unit, crop, ITK) — the
`simulated_yields` table of spec §4. *To confirm*: how the virtual plot selects its ITK (via
`idSdcForce`?), and whether the farm-level constraints (labour) apply to it.

### M.8 — The gap indicators of spec §5.4, against what MAELIA outputs

| implicit constraint | MAELIA output | usable? |
|---|---|---|
| labour | `suiviOTParParcelle.csv`: one row per operation, with day, plot, farm, `temps` (h) → **weekly hours per farm** are a group-by away; `avecContrainteDeMainOeuvre` makes labour limit the agents | **yes** — compare with `farm_labor_hours_max`, annual in MOSAICA |
| machinery | ITK entries with `OUTIL`, `PASSAGES`, `AGRIW` **have no effect in MAELIA yet** (guide) | **no**, as documented: no machinery conflict is simulated |
| water | `sorties_eau.csv` per plot × period: rain, evaporation, transpiration, percolation, irrigation, water-satisfaction index; `IRRIGATION_dose` in `suiviOT` (use it when the hydrological module is on — `sorties_eau` then reports 0) | **yes** — directly comparable with `water_need_peak_month_m3` |
| nitrogen | `sorties_CN.csv`: leached, volatilised, mineralised, uptake, N₂O, N-satisfaction; `FERTI_*` doses in `suiviOT` | **yes** (AqYieldNC only; **AqYieldNC cannot simulate grassland** yet) |
| GHG, soil carbon | `sorties_carboneGES.csv`: ΔC_org, N₂O by pathway, fertiliser emissions, net GHG balance (kg CO₂eq/ha) | yes — a process-based counterpart of MOSAICA's per-crop factors |
| yield | `RECOLTE_rendement` (t/ha) per harvest | **yes** |
| margin | built from inputs (`prixVentes`, `primes`, `chargesOp`, `chargesDePassage` → semi-net margin), but **no margin output file is documented** | *to confirm* where it is written |

Output periods split each calendar year at sowing and harvest dates (a row per plot × cover
period); the team has R scripts to aggregate by crop or by year.

### M.9 — File hygiene the coherence check enforces

Separator `;`, decimal `.`, no quotes in headers, and **no Excel** (it changes separators) —
the opposite of MOSAICA's fill-in workbooks, so a MAELIA export must be written by code.
Column order is free (matched by header) except where stated: weather columns in the order
`ID_PDG;DATE;RRmm;Tmin;Tmax;ETP;RGI`, and the **row** order of `barrage.csv`. Sub-period
values are separated by `|`. Irrigation equipment `NA` = not irrigated. A fertiliser with an
annual stock of 0 is never applied; "unlimited" is `1000000000`. Every crop in a `SEQUENCE`
must exist in `especesCultivees.csv` **and** in `reglesDeDecisions.csv`; empty sequences are
forbidden.

---

## Questions left for the training

Ordered by how much they block.

1. **Tropical and perennial crops**: which species already exist in some MAELIA study area
   (La Réunion? another DOM?), how multi-year crops (cane cycles and ratoons, banana,
   pineapple's 18 months, orchards) are represented, and who parameterises the missing ones.
2. **Weather and soils for Guadeloupe**: an accepted daily weather source outside SAFRAN/E-OBS,
   and how soil horizons are derived where BDGSF does not reach.
3. **The exact `nomChoixAssolement` options** (the table is clipped) and whether `'Donnees'`
   keeps the agents from changing the crop under any condition.
4. **ITK variants as species** (M.4): acceptable to the team? naming convention?
5. **Virtual plots** (M.7): ITK selection, labour, and the cost of one run — the budget of work
   item D depends on it (spec §5.5 still has "duration of a daily MAELIA run, unknown").
6. **Where the semi-net margin is written**, and the unit of `prixVentes.csv` (the guide says
   €/ha; a price per tonne is expected — reference.md § Errata).
7. **Plot ids**: `ID_PARCELL` from `pac_ilot` + `parcelle`? And does MAELIA's information
   system hold the RPG with those ids (spec §6.2)?
8. Information system and access levels (spec §6.3) — the guide says nothing about them.

## Contacts named in the guide

- **ITK application** (accounts, bugs, adding a territory or criteria): Renaud Misslin (MAELAB).
- **Launching MAELIA** and any problem during or after a run: "Jean" (MAELIA team).
- **Adding a species or a cover crop to the MAELIA list**: Olivier and Renaud.
- The guide itself: the MAELIA team (UMR LAE and MAELAB).
