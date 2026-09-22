# Data: catalogue, access levels, fill-in workbooks

`data/` is not in the repository. This folder is: it says **what each table holds, where it
comes from, and who may see it**, and it drives the tools that move data in and out of MOSAICA.

| file | role |
|---|---|
| [`catalogue.yaml`](catalogue.yaml) | one entry per input table: file, layout, fields with type / unit / bounds / codes, source, owner, licence, vintage, resolution, **access level**; plus the level of every file of a run folder |
| `scripts/build_data_templates.py` | writes the fill-in Excel workbook from the catalogue, prefilled from `data/` |
| `scripts/validate_data_workbook.py` | reads a workbook (or `data/` itself) back, checks it, exports the tables with a hashed manifest |

The engine is case-study-agnostic: `core/data/catalogue.py` (schema, validation, GAMS text
formats) and `core/data/workbook.py` (Excel). A new territory writes its own catalogue.

## Access levels (a proposal, to validate)

| level | content | examples |
|---|---|---|
| **0 — public** | aggregates at commune level or above; published sources | POSEI and AECM rates, the crop list, results by island |
| **1 — partner** | per-crop coefficients; aggregates by sub-region, farm type or crop; scenario results | yields, prices, itineraries, `recap.json`, the policy × forcing grid |
| **2 — restricted** | anything at plot or farm level | `plot_data`, `farm_plot_map`, `allocation_output.csv`, `revenue_by_farm.csv`, the Map page |

Two points fix the border and are **to confirm with INRAE's data protection officer and the data
producers**, not to assume:

- **The plot ↔ farm link is what makes a record personal.** The anonymised RPG is public; the
  same plot attached to a (pseudonymised) farm, its size and its revenue identifies a farmer
  (GDPR). Every table sharing plot ids with `farm_plot_map` is therefore level 2, even when it
  alone would be public (`rpg_history`).
- **Statistical confidentiality.** An aggregate of agricultural statistics is usually published
  only if it covers at least 3 units and none weighs more than 85 %. A commune-level figure is
  level 0 by rule but can breach this in a small commune; nothing checks it yet.

**Access control does not live in MOSAICA.** Accounts, roles and views per level belong to
MAELIA's information system. MOSAICA's part is to *label* (this catalogue) and to *export by
level*: today `build_data_templates.py --max-level 1` for the inputs; for run outputs, the
`outputs:` section of the catalogue gives each file's level and the export itself is roadmap
item `level-export`. A run folder as a whole is level 2, and so is the dashboard.

Most licences and owners read **"to confirm"**: nobody wrote them down when the tables were
assembled. Filling them is a prerequisite to any sharing, and the Sources sheet of every
workbook lists them so the gap stays visible. Two known constraints: pesticide properties in
`Data_OTK` come from the PPDB, under its own terms of use; the RPG is under the Licence Ouverte,
but the pseudonymised farm link is not the published RPG.

## Three flows, kept apart

**Add** — a new version of a table (corrected coefficients, a new year, a new territory):

```bash
python scripts/build_data_templates.py --tables crop_yield --max-level 1   # the sheet to send
# ... the partner fills the yellow cells ...
python scripts/validate_data_workbook.py filled.xlsx --compare --export
```

The export lands in `outputs/data_staging/<timestamp>/`, **not** in `data/`: it is reviewed
(`--compare` counts the rows added or removed and the cells changed against `data/`), then copied
in by hand. Its `manifest.json` records each file's SHA-256, row count and level. A version is
never edited in place; a run's recap should cite the fingerprints of the tables it read (not done
yet: roadmap `data-fingerprints`).

**Mobilise** — read for a run: unchanged, `build_dataset` reads `data/`. Check `data/` against
the catalogue after any copy:

```bash
python scripts/validate_data_workbook.py --check-data     # ~5 s, exit 1 on any error
```

**Export** — to a partner, filtered by level: `--max-level 1` for the inputs; the outputs
export is `level-export`.

## The workbook

Carbon-assessment style: a *Read me* sheet (how to fill, the levels, the sheet list), one sheet
per table, a *Sources* sheet (source, owner, licence, vintage and notes of each table) and a
hidden *Lists* sheet feeding the drop-downs.

Every table sheet opens with its title, description, provenance and value rule (rows 1-4) and its
header (row 5). Tables with one row per entity (plots, operations) add a description, unit and
allowed-values row (6-8) and an example row (9, ignored when read back). Yellow cells are to fill;
grey cells are locked (headers, units, rules, computed and derived columns). The protection has
no password: it prevents accidents, not access. Drop-downs come from the referentials (crop
codes, operations, soils, periods) and from the code lists of the catalogue; numeric bounds are
Excel validations.

Computed columns (`CONFORM = PERIMETRE / SURF_HA`, rounded) keep their stored value on prefilled
rows and carry a formula on the spare rows; the validator recomputes both. Derived columns
(`NB_PARC`, counted from `farm_plot_map`) are recomputed by the validator from the mapping.

Sizes: the full level-2 workbook (41 tables, 25 000 plots) takes about a minute to write and a
minute to read back; the level-1 workbook (34 tables, no plot or farm table) about 5 s.

## What the catalogue found in the current data

Written down in the catalogue notes and in `docs/04-vigilance.md` C.7:

- `Data_OTK.GES_SURF` is **empty for `DICOPUR_600`**, an input of every sugarcane and fibre-cane
  itinerary. GAMS and the pandas sum both read it as 0, so the GHG figures are unaffected, but it
  is a gap, not a zero.
- The **unit of `PENTE`** is documented in degrees for plots and in % for the crops' bounds, and
  the two are compared directly. Values up to 100 suggest %; to confirm with the source.
- `CONFORM` is `round(PERIMETRE / SURF_HA)` computed on the unrounded perimeter: recomputing it
  from the file moves 57 plots by one unit (none across the 1 500 threshold). The validator
  accepts ±0.5 and keeps the stored value.
- `Avers.txt` lists 5 336 farms where `EXPL_PARC_2017.set` has 4 638; it is not read.
- `R_Tixier.txt` pads `SEUIL_GUS_CULT` with spaces (`domain/rpest.py` strips it; the validator
  warns).
