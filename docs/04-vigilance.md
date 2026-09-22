# 04 — Vigilance: what to know before quoting a figure

The model produces credible numbers where they mean nothing. This page lists the traps, with
the verdict and the measurement behind it. The **full investigation log** (with the paths
abandoned and why) is in [`archives/journal-vigilance.md`](archives/journal-vigilance.md), in
French.

Severities: **Critical** (falsifies a result) · **Major** (a real functional limit) ·
**Minor** (to know).

Figures below were measured on the runs named with them. The reference runs on disk
(`calib_retenu`, `calib_gams_parite`) predate the correction of the price tables of
2026-09-08 (E.1): their figures stand for those runs, and are due to be regenerated.

---

## A. Reading a result

### A.1 — Critical — An indicator fixed by a constraint is not a result {#a1}

Scoring a policy on subsidies when it caps its own budget at 80 M€ measures **what was imposed
on it**. P1 wins the "public spending" axis by setting it to zero: that is circular.

-> `comparison.bound_indicators(recap)` detects them from `recap["constraints"]` — hence after the
fact on runs already written — and the dashboard marks them ⚠. The score still includes them
**if asked**, on purpose: excluding them outright would hide the effect of a ceiling on the
*other* indicators.

### A.2 — Critical — Comparing totals confuses scale and intensity

A policy farming fewer hectares shows less total nitrogen **without producing more cleanly**. A
nitrogen ceiling can also be met by farming less.

-> Read the `intensity` block: nitrogen **per tonne**, per hectare. Intensity is what describes a
practice.

### A.3 — Critical — "Resilience" means two opposite things in this repository

| | Measure | Did the model react? |
|---|---|---|
| `recap["resilience"]` (`domain/resilience.py`) | **exposure** — shock applied *after* the solve, frozen allocation | no |
| `core/reporting/robustness.py` | **adaptive capacity under policy constraint** — re-optimised under each forcing | yes |

**Never add them up**: the number obtained has no meaning.

Three conventions of the robustness module, to know before interpreting:
- a policy **infeasible** under a forcing has **no** numeric worst case (empty cell) —
  otherwise the worst of its survivors would make it look robust;
- forcings are **not averaged** by default: an average would assert a probability
  distribution nobody chose;
- regret is measured against the best policy **of the same forcing**.

### A.4 — Major — The composite score: weight by family

Without `balance_families=True` (the default), the eleven food self-sufficiency ratios, nearly
collinear, weigh **eleven times** GHG. The score would then measure how finely the list is cut,
not performance.

### A.5 — Major — The PAD is not a score in prospective work

It measures the gap to 2017. A policy scenario is *made* to move away from it. Read it as "size
of the upheaval", never as a mark.

### A.6 — Minor — The config diff says what was *asked*, never what the gap *cost*

A constraint that does not bind changes no result. And two identical configs already diverge by
the solver's branching arbitrariness alone (**0.15 PAD point** measured over three HiGHS
seeds). The **allocation** diff answers the next question.

### A.7 — Critical — An ε-constraint front is parameterised on the bound of its HOST POLICY

The thresholds of `scenarios_pareto.yaml` are fractions of **what `calib_selected` achieved**
(1 930 903 kg N). That is the right setting for a front traced against the reference config.
Under a policy that already sets its own bound, it no longer is.

Measured in LP on 2026-08-09: under **P8**, which caps nitrogen at 1 351 632, **five of the seven
catalogue points are inactive or equal** to that bound. Bare P8 and the 1 930 903 point return
the same value, **71 065 297, to the cent**. Seven solves for three distinct points.

-> Re-parameterise on the level **where the bound binds under the host** (the executed stage
spec `plan_etape_BC.yaml`, in git history: five points, fractions of 1 351 632; measured slope
**5.27 €/kg N**, which matches exactly the dual price read on the nitrogen cap). `plan.yaml`
hangs `pareto_nitrogen` on P8 **without** re-parameterising: the defect is in the plan, not only
in a stage spec.

### A.8 — Major — Under a systemic crisis, the nitrogen ceiling no longer binds at all

The nitrogen front under **F9** was investigated then **abandoned on measurement**. The five
points, from 1 351 632 to 810 979 kg, return the **same LP bound: 32 439 337**. The ceiling is
inactive everywhere in the range.

The reason is economic: F9 degrades yields (x0.80), export prices (x0.75) and subsidies (x0.60)
while raising costs (x1.30), so that intensification stops paying and the optimum spontaneously
uses **less than 42 % of the 2017 nitrogen**.

-> **The crisis already does the ceiling's job.** That is a result, obtained without any MILP
solve — not a failure. A real front under F9 would need thresholds starting below ~810 000 kg,
hence first measuring the spontaneous use of P8 x F9 (the existing run ended at `maxTimeLimit`
and returns an allocation identical to P8 x F0, hence unusable).

---

## B. Solver and tractability {#tractabilite}

### B.1 — Major — The solve is slow and its duration very dispersed

Half an hour to an hour in the **calibration** configuration (308 847 variables), two to three
hours in the **prospective** one (331 044). At **constant size**, the 7 calibration solves
recorded run from **327 s to 3 625 s** — a factor **11**, mean 1 448 s, **CV 91 %**; the 13
prospective solves run from 2 505 s to 10 856 s, mean **7 043 s**, CV 49 %. The dispersion is
not an artefact of mixing warm and cold: on the 6 warm-started calibration solves alone, the CV
is still 96 %. The bottleneck is the branch-and-bound search, not the Pyomo->HiGHS wrapper
(~15 s, negligible).

> **`.mosaica_solve_history.json` is a rolling window over the last 20 solves**
> (`progress.py`, `del entries[:-_MAX_ENTRIES_PER_CASE_STUDY]`), not a cumulative log. The
> figures above were **recounted on 2026-08-30** from its content at the time. The previous
> values — "the 20 solves run from 155 s to 1 007 s, factor 6.5, CV 64 %", read on 2026-08-01 —
> described a campaign since **overwritten**. Anyone reusing this paragraph must **recount** the
> file rather than copy a figure: `clement/memoire/build_chiffres.py` (block `MEASUREMENTS`)
> carries the same values and date.

-> **No point estimate of duration is reliable.** `core/solve/progress.py` therefore prints a
**range** from comparable runs (same size within 20 %, same warm/cold mode), and refuses to
answer outside that band.

### B.2 — Major — A solve that hits the time limit returns a *provably* sub-optimal incumbent

This is not a presumption. Starting from an existing allocation and switching to the best
eligible fruit crop the plots where it costs least, a feasible solution worth 80.91 M€ is built
**in a few seconds**, against the **76.46 M€** HiGHS found **in one hour** — a 5.5 % gap.

**Signature to recognise**: a constraint on pineapple makes cane and banana recede. A constraint
that has no reason to touch an item and touches it = a lost branch-and-bound.

-> The fix is the **warm start**: the same orchard floor, but tighter (335 ha instead of 200),
goes from 3 613 s unconverged to **642 s converged**, an objective 4.7 M€ better.

### B.3 — Major — Symmetric crops are a disaster {#karusmart}

**The 25 "Karusmart" market-gardening variants** `MA_{BAG,BRF,PAI}_{BIO,VEG,FER,NON}_{I,NI}` are
**bit-for-bit identical** to `MA_TO_CO_JA` on every parameter the model reads — margin
20 825 €/ha, yield 36 t/ha, 1 128 h/ha, 75.6 kg N/ha, TFI 10, same eligibility footprint. The
mulching / fertilisation / irrigation distinctions **carry no data**.

Two consequences, both of which bit:
- reopening them adds **548 000 binaries of pure symmetry** (879 162 against 331 044);
- **any organic share built on them is a no-op**: the solver meets "25 % organic" by picking
  the copy named `_BIO_` of an identical activity, at **exactly zero** cost. A constraint that
  looks like an agroecological policy and constrains nothing.

-> **The only genuinely organic crops of the dataset are `MA_PLBIO` and `MA_MOBIO`** (nitrogen 0,
TFI 0, for 3 882 / 3 498 €/ha against 27 929 for `MA_ROTA`). The group
`organic_market_gardening` of `crop_groups.yaml` is built on them alone (the older
`scenarios.yaml` still counts the copies, and says so). **Do not reopen `ma_exp_supp`** until
the 25 have distinct itineraries. `check_scenario_feasibility.py` detects and reports any
symmetric group.

### B.4 — Major — The labour ceiling is the real limiting factor

`Eq_MO_MAX_Expl` grants the territory 6 252 740 h, i.e. **3 891 FTE** at `slack: 1.0`.

- An **employment floor** above 3 891 FTE is infeasible unless the scenario loosens the slack
  (1.5 -> 5 837 FTE, 2.0 -> 7 782).
- The **food-production floors** claim 6 222 537 h and are infeasible at `slack: 1.0`.

**And loosening the slack is not enough.** P10 was infeasible with a floor at 6 000 FTE while its
slack allowed 8 561: what was missing was not hours but **crops able to absorb them** under the
environmental ceilings. Real maximum measured in LP: **P8 -> 4 875 FTE, P10 -> 4 975 FTE**. A
bisection ruled out any single ceiling as the cause (removing TFI, nitrogen or GHG leaves the
infeasibility): it is the combination.

-> **Never raise an employment floor without re-measuring.** A data-free test
(`test_prospective_labour_slack_covers_every_employment_floor`) keeps the two blocks consistent.

The budget itself rests on the representative crops (C.2). The observed fine plan
(`context/SORTIES/ASSOL_PARC_INIT.TXT`) gives 5 592 326 h instead of 6 252 740 and redistributes
it between farms; it is tested in `scenarios_labor.yaml` and not yet the default.

### B.5 — Minor — A zone with no term is silently exempted

`zone_indicator_bound` sets no constraint for a zone where no eligible pair carries a non-zero
rate. Harmless for a **ceiling**; but for a **floor**, that zone is **exempted** instead of
making the run infeasible.

-> Check: compare the number of zones the constraint produced with the number the grouping
declares.

### B.6 — Major — P10 is out of reach, and no seed is repairable {#p10}

`P10_agroecological_bifurcation` stacks a GHG ceiling (−25 %), TFI at 33 473 (−50 %), nitrogen
at 1 158 542 (−40 %), 120 kg N/ha per farm, a water ceiling, five food-crop floors and an
employment floor at 4 400 FTE. On 2026-08-03 it ended at `maxTimeLimit` **without any
incumbent** in 7 200 s.

**It is not infeasibility** — the LP relaxation is feasible, bound **46 311 985 €** in 81 s. Nor
is it mere slowness: `scripts/audit_warm_start_seed.py` rejects the three nearest seeds.

| Seed | Constraints violated | Most telling |
|---|---:|---|
| `pareto_azote_threshold_1061997` | 124 | TFI exceeded by 26 316 on a ceiling at 33 473 |
| `pareto_azote_threshold_1158542` | 156 | + GHG exceeded by 6.4 M |
| `p8_..._f0_nominal` | 407 | GHG exceeded by 63.4 M, nitrogen by 193 081 |

-> **No allocation this model ever produced is within repair distance** of these stacked
ceilings, and `repair_allocation.py` only repairs an area floor. Restarting cold would reproduce
the failure. What can be said lies in the LP bound: **even allowing fractions of plots, P10 costs
at least 43 % of the objective** (46.3 M€ against 80.8 M€ for P8). It is a valid upper bound
and more solid than an unproven incumbent. Consequence for reading: **the P1 <-> P10 axis is
one-sided**, only the accelerationist bound is solved.

### B.7 — Major — The warm-start chain is **internal to the batch**: a run on disk is never a seed {#chaine-batch}

`seed_candidates` (`scripts/run_scenarios.py`) offers three seeds, nearest first: the previous
point of the same front, the policy's nominal allocation, the global seed. The first two are
read from `sweep_seeds` and `policy_seeds` — **two dictionaries filled during the batch**, never
from `outputs/`. There is no discovery of seeds on disk.

-> Consequence: **a cell whose policy has no unforced run in the same batch starts cold**,
whatever sleeps in `outputs/`. That is exactly the case of a resumption batch, which by
construction only replays forced cells. The only way to name an existing run is
`--warm-start-from`, and it is **global to the batch**: a batch mixing several policies cannot
give each its own seed. Splitting it by policy is not fussiness, it is the only way to seed
correctly.

The symptom is discreet — the "warm start from …" line is missing, but the solve starts normally
and the batch says nothing. Check: `run_scenarios.py` prints the seed chosen for each run; **its
absence means cold**.

### B.8 — Major — The root LP bound widely overstates what a solve left {#borne-lp}

Measured on `P8_agroecological_transition` on 2026-08-11: integer optimum **69 088 438**
(proven), root LP bound **71 065 297**. The **integrality gap alone is 2.78 %**. An incumbent at
68 644 754 is therefore 3.41 % from the LP bound but **0.64 % from the optimum** — a factor of
five between the two readings.

-> The LP bound serves to **prove an infeasibility** (B.6) and to compare policies with each
other. It does not quantify how sub-optimal an incumbent is: the gap it shows belongs mostly to
the relaxation, not to the branch-and-bound. Never write "the solver stalls at 3.4 %" on that
basis.

Corollary measured the same day: **proving costs more than finding**. Restarted on the optimum
itself, the solve took **8 981 s** just to close the dual bound. And time only pays off in a
chain, each step restarting from the previous incumbent — 68 445 374 (1 h), 68 644 754 (+3 h),
69 088 438 proven (+2.2 h) — where three hours in one go from a fixed seed had brought only
0.29 %.

### B.9 — Major — A warm start can **degrade** a forced cell {#warm-regression}

A warm start guarantees a result **greater than or equal to its seed's value**. It guarantees
nothing against an earlier run of the same cell, which may have started elsewhere and landed
higher.

Measured on 2026-08-12 on `P8 x F9_systemic_crisis`, resumed with three times more time:

| | objective | duration |
|---|---:|---:|
| initial run, cold | **−1 506 116** | 3 629 s |
| resumption, seeded from P8 x F0 | −1 678 357 | 10 825 s |

The seed was the allocation of `P8 x F0`, **optimal under F0 and poor under F9**: the systemic
crisis reverses the relative profitability of the crops, so that the best nominal cropping plan
is a bad starting point. The solver started from a low incumbent and did not get out of it in
three hours.

-> **Never overwrite the old run.** After any resumption, compare and keep the better of the two
incumbents; the quarantine `outputs/_non_converges/` exists exactly for that. And to resume a
forced cell, the safest seed is **its own earlier run**, not the policy's nominal allocation —
the latter is the best seed only for forcings that move the coefficients little. What
`scenarios_forcings.yaml` says ("a forcing changes coefficients, not the feasible set")
guarantees the seed's **feasibility**, never its **quality**.

---

## C. Data: what the dataset does not contain

### C.1 — Major — The model's yields are 1 to 4x those of the territory

Compared with the 2017 annual agricultural statistics (Agreste, *Mémento de la statistique
agricole — Guadeloupe*, 2019 edition, pp. 16-17), which publish area, **yield** and production per
crop — the yield column is published as is, not a division of ours. Column "model" = simulated
production / simulated area on `calib_retenu`, fine-variant mix included.

| | Agreste | model /cycle | model /yr | ratio |
|---|---:|---:|---:|---:|
| Market gardening | 10.8 t/ha | 43.9 | 43.9 | x4.1 |
| Citrus | 5.2 | 20.0 | 20.0 | x3.8 |
| Plantain | 9.0 | 26.0 | 26.0 | x2.9 |
| Orchards | 6.4 | 14.5 | 14.5 | x2.3 |
| **Pineapple (18-month cycle)** | 12.3 | 34.0 | **22.7** | x1.8 |
| Yam | 10.0 | 17.8 | 17.8 | x1.8 |
| Melon | 19.9 | 20.0 | 20.0 | x1.0 ✓ |

**CORRECTED 2026-08-16 — this entry said "2 to 4x" and compared different units on pineapple.**
`Rdt_Cult` is a yield **per cycle**. GAMS annualises (`/Duree_Cycle_Cult*12`) everything
monetary — sales, subsidies, margin — but **not** the tonnages (`PROD_*`, `TONNE_*`, `NUTRI_*`
read raw `Rdt_Cult`; the Python port does the same, see `compute_production_tonnes_by_crop`).
Out of 84 crops, `Duree_Cycle_Cult.txt` carries only one value ≠ 12: pineapple, at **18 months**.
It is therefore the only crop whose model tonnage is not an annual tonnage, and the former x2.8
on pineapple was overstated by half. Corollary: **any comparison of a model tonnage with an
annual statistic must annualise pineapple** — production quotas included.

**Cross-check.** The 2020 Mémento (2019 data) gives the same orders of magnitude: pineapple
12.91, plantain 9.3, yam 10.0, melon 19.3, citrus 5.1 (64 ha lemons + 79 clementines + 104
oranges + 36 grapefruit), other fruit 5.9. The finding is stable over two editions.

**Two caveats not to hide.** (a) *Market gardening*: the model describes an **annual rotation**
of several vegetables on the same hectare (`MA_ROTA` 54 t/ha, `MA_TO_CO_JA` 36) whereas Agreste
counts one area per vegetable — the x4.1 is therefore partly a difference of unit, not a
productivity gap. (b) *Citrus*: the simulated yield bears on ~10 ha, and the Agreste denominator
includes orchards not yet in production.

**What makes the finding solid despite these caveats: melon.** It is the only crop produced
almost entirely by a single operator under a specified itinerary — hence the only one whose
territorial mean *is* a technical itinerary. And it is exactly the only line where the two
figures coincide. The gap is not a data defect: it is the difference between a **potential
yield** and a **mean yield**, and it vanishes where the two notions merge.

-> **Direct consequence: the margin of these crops is mechanically overstated, so the model
covers the island with them as soon as no outlet bounds them.** That is the common cause behind
plantain, pineapple and yam. Under the parity mandate it is not touched (these are the yields of
the article's Table 1), but it explains *why* market ceilings are needed: **they are not
crutches**, they compensate for a productivity overstated upstream. Simulated yields (the MAELIA
coupling on the [roadmap](status/roadmap.yaml)) attack the cause rather than the symptom.

### C.2 — Major — The fine 2017 allocation on the input side never existed

The baseline only encodes the crop at **RPG aggregate** level (12 codes). **GAMS did the same**:
the 2017 technical variant was never observed; it is not a missing port.

-> To compute production/subsidy/revenue/FTE **on the input side**, a representative fine
variant per family is substituted (`config.yaml baseline_representative_crops`). **The input
indicators therefore rest on an assumption**, documented and configurable.

**And that assumption now shapes the allocation**, not only the reporting: the per-farm labour
ceiling is computed through the representatives. Changing a representative changes the ceiling,
hence the optimum.

**Worse: the representative is often a crop the model would forbid on the plot it stands for.**
Share of the observed area where it is eligible: **cane 31 %**, market gardening 61 %, plantain
63 %, banana 69 %, orchards 46 %, citrus 48 %. Only grassland, melon and fallow are at 100 %.

### C.3 — Major — The RPG under-declares grassland

Our plot dataset covers **87 %** of the 2017 UAA and returns cane at **98 %** — but grassland at
only **64 %** (6 109 ha against 9 595). It is not a labelling problem: if the ~3 500 missing ha
were classified as cane here, our cane would exceed Agreste. **They are plots absent from the
plot universe.**

Independent physical proof: 40 449 cattle ≈ 29 771 LU. On Agreste's 9 595 ha that is **3.10
LU/ha**, which falls exactly on the censuses; on the 2 980 ha the model gave without a floor,
**9.99 LU/ha** — three to four times reality, agronomically impossible.

-> The defect is therefore proven **outside the model**. It is what grounds the grassland floor
at 6 096 ha, **27 % below** the exogenous value (conservative).

### C.4 — Major — No monthly rainfall

The GAMS water-need formula subtracts `PLUVIO_01..12_PARC`, columns **absent** from the data.
GAMS returns 0 on a missing column, so **rain was never subtracted**.

-> The indicator is a **gross crop water need**, not a net irrigation need. **Do not label it
"irrigation".**

**CORRECTED 2026-08-12 — the monthly data EXISTS, and it is in the repository.** This entry said
(as did the water/carbon spec) that unlocking it required "a monthly rainfall series per plot,
which does not exist today". That is wrong. `context/Rapport technique variables
MOSAICA_v2.docx` §5 has a section "Calcul de la répartition mensuelle des précipitations
annuelles" (monthly split of annual rainfall) and publishes the key, averaged over three INRA
stations (Gardel, Duclos, Godet) and nine complete common years:

| J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 7.4 % | 3.8 % | 4.6 % | 9.1 % | 10.3 % | 6.8 % | 8.2 % | 11.4 % | 9.6 % | 11.7 % | 9.9 % | 7.3 % |

`PLUVIO_01..12_PARC` was therefore `PLUVIO_PARC x key`. The columns are missing from the
delivered table, but the method and the coefficients are versioned. The net irrigation need is
computable (roadmap `net-irrigation`) — note however that `PLUVIO_PARC` is a **1981-2010
normal**, not the rain of the simulated year, and the missing `max(0, ·)` bug (entry D.3) will
wake up as soon as rain is actually subtracted.

Corollary: the 12 columns `BESOIN_EAU_01..12` are **identical for the 84 crops** — any monthly
indicator is degenerate (the "peak month" is always the total / 12). That is why it is excluded
from the composite score.

### C.5 — Minor — Data present but never read

`Data_OTK` carries `HOUDART_TOX_SCORE`, `HARMFUL_FACTOR`, `DLRAT`, `BIRD` (ecotoxicity);
`indice_H/RS_Cult.txt`; the sets `EXPL_NBT`, `PARC_NBT`, `CULTIV_2017`… `Avers.txt` is
**deliberately** ignored (uniform stub). (`Cout_Transp_Cult_LAM.txt` was on this list; it is the
transport-cost table read since 2026-09-08.)

### C.6 — Minor — `KNO3` carries `AZOTE = 0`

Potassium nitrate contains ~13 % nitrogen. On the 15 fertilisers named as an NPK triplet, the
nitrogen deduced from the name equals the `AZOTE` column **to the thousandth** — the file's
convention is safe — but chemically named salts escape the check. Not corrected (parity mandate).

### C.7 — Minor — What the data catalogue found in the tables

Checking `data/` against `docs/data/catalogue.yaml` (`validate_data_workbook.py --check-data`)
passes, but only after writing down five facts:

- `Data_OTK.GES_SURF` is **empty for `DICOPUR_600`**, an input of every CS and CF itinerary. The
  pandas sum in `domain/itk.py` skips it, like GAMS reads 0 — no figure changes, but a gap is
  not a zero (and the GHG scale is itself unconfirmed, roadmap `ghg-unit`).
- **`PENTE` has two documented units**: degrees for the plots (`DESCRIPTION_SETS.txt`), % for
  the crops' `PENTE_MIN/MAX`, and the eligibility compares them directly. Plot values reach 100,
  which points to %. To confirm with the source before quoting a slope.
- `CONFORM = round(PERIMETRE / SURF_HA)` was computed on the unrounded perimeter: recomputing it
  from the file moves 57 plots by one unit, none across the 1 500 threshold of `Eq_CS_CONFORM`.
  The validator keeps stored values within ±0.5.
- `Avers.txt` has 5 336 farm ids where `EXPL_PARC_2017.set` has 4 638 (unused, see C.5).
- `R_Tixier.txt` pads `SEUIL_GUS_CULT` with trailing spaces (stripped in `domain/rpest.py`).

---

## D. GAMS bugs ported faithfully

The mandate is parity: the **actual** GAMS behaviour is ported, bug included, with the "presumed
intent" variant as `enable: false` right next to it in `config.yaml`.

### D.1 — Major — `Eq_VE_PLUIE` forbids rain-fed orchards **everywhere**

`MODELE.txt` queries `Data_RPG_Gwad` on columns `REGION`/`ILE` **absent** from that table. GAMS
returns 0 without complaint, so the test `0 ≠ 1` is **always true**.

-> **`VE_PLUIE` will never appear in the output.** First suspect if orchards are ever compared
with observed data.

### D.2 — Major — Trap: two incompatible soil-type orders

`SOL.set` is ordered `NITISOL, ANDOSOL, FERRALSOL, AUTRES, VERTISOL`. GAMS maps the numeric
column `TYPE_SOL` in a **different** order: `1->VERTISOL, 2->FERRALSOL, 3->ANDOSOL, 4->NITISOL,
5->AUTRES`.

-> Indexing `Data_Sol` **by position** produces wrong but plausible coefficients — a **silent
error**. Always map **by name**.

### D.3 — Minor — Two unit errors with no effect on the ranking

- **GHG**: the magnitude reaches ~1.6e5 "t CO₂/ha/yr". The stated unit is probably wrong (kg?),
  but the values come from the source data — GAMS would produce the same (roadmap `ghg-unit`).
- **Water**: GAMS omits the factor 10 of the mm->m³ conversion (the author had himself left
  "pourquoi x 10 ?" (why x 10?) in a comment). The Python port exposes correct m³.

No effect on comparisons: the composite score normalises min-max.

### D.4 — Minor — `crop_variance_per_ha` has a misleading name

The parameter holds `Var_Rdt_Cult`, a **fraction of margin loss** — neither a variance nor a
coefficient of variation. **The loss is linear in area, with no square and no covariance.** A
classic trap for anyone building a variance computation on it.

### D.5 — Minor — Carbon balance: annual flow only

GAMS iterates `C_ORG = C_ORG + (inputs − outputs)` over several years. The Python model is
single-year: only the **annual flow** is portable. A trajectory would need reallocating year
after year — another project.

---

## E. Calibration: what the model is compared with {#calibration}

### E.1 — Current state (`calib_retenu`, to be regenerated as `calib_selected`)

| Metric | GAMS parity | **Selected** | Threshold / article |
|---|---:|---:|---:|
| Farm types reproduced | 64.0 % | **86.9 %** | 80 % (article: 81 %) |
| Plots correctly simulated | 56.0 % | **67.6 %** | article: 66 % |
| Area correctly simulated | 64.3 % | **77.1 %** | article: 77 % |
| Territorial PAD | 48.4 % | 6.6 % | 15 % |

The model **reaches the published calibration quality** on types, plots and area.

**Do NOT quote the 6.6 % territorial PAD.** The grassland floor pins grassland, whose PAD is zero
by construction; the total inherits it. The solid figures are the first three rows — and above
all **cane back at 12 782 ha against 12 813 observed** (PAD 0.2 % against 20 %) **without any
constraint naming it**.

**These two runs predate the 2026-09-08 correction** of the price, yield and transport tables
(`Prix_Cult_CF_<scenario>` instead of `Prix_Cult`, 23 crops out of 84 affected). Replayed with
the corrected tables, the GAMS-parity run (`calib_gams_parity_prices`) reaches a territorial PAD
of 12.07 % against GAMS's own 3.76 % on `Assol_Calib`. The table above therefore describes the
runs on disk, not the current config; regenerating them is roadmap item
`regenerate-reference-runs`.

### E.2 — Critical — Comparing with the article needs four corrections

1. **The article publishes its PAD per crop, never aggregated.** The <15 % threshold qualifies
   "8 uses out of 10". Our "territorial PAD" is a home-made TOTAL row, **stricter**. The
   comparable metric is *Crops under threshold*.
2. **Its Table 5 counts non-cultivated plots** in the denominator, we exclude them. At its
   convention, `calib_gams_parite` would show 60.5 % / 67.8 % instead of 56.0 % / 64.3 % — **four
   points that were a matter of definition.**
3. **Its base year is 2010, not 2017** (25 057 plots, 5 336 farms, against 24 734 / 4 638).
   Region by region the areas match within a few %: it is the same territory, with seven years
   of land concentration. Structurally out of reach.
4. **It publishes no PAD table per farm.** The threshold "20 % … and farms" is never
   instantiated there.

### E.3 — Major — The solver is not to blame

- The **observed 2017 plan is worth 15 % less than the optimum** under our own objective
  (72.2 M€ against 85.0). The MIP gap is 1 %: the gap to close is **fifteen times** the
  tolerance.
- **Three HiGHS seeds**: PAD 48.44 / 48.29 / 48.31. Branching arbitrariness is worth **0.15
  point**. There is no solver knob.

### E.4 — Two deviations accepted in the `CALIB` block, both sourced

| Deviation | Value | Source |
|---|---|---|
| Plantain ceiling `bc_quota_max` | 6 440 t | the GAMS author's figure; corroborated by the article's Eq. 6 (4 650 t) |
| Grassland floor `pn_prod_min` | 6 096 ha | GAMS parameter `QUOTA_PN_PIQ_MIN`, corroborated by Agreste 2017 |

**The test that tells a correction from a fit**: the plantain threshold sweep shows a **flat
plateau from 4 650 to 9 240 t** — a factor of 2 on the threshold, 0.5 PAD point, barely more than
the solver noise. The result does not depend on the value, only on **the existence** of a
ceiling at market scale. And the plateau's optimum is at 9 240 t (x2.4 the observation), not at
the tightest threshold: a parameter used as a fitting variable would improve monotonically as it
approached the observation.

That is the essential difference with the "market ceilings" discarded, which were fitted **on**
the observation (zero PAD by construction). The candidates and the retained values are listed
in `case_studies/guadeloupe/status/parameter_choices.yaml`.

### E.5 — What remains, and why we stop there

Three ways to go below the plateau were investigated to the end then **discarded**: recalibrate
the risk aversion (-> 39.9 % but economically absurd coefficients, a specialist becoming "very
averse" — overfitting), fit ceilings on the observation (circular), add livestock (the economics
is already there; what is missing is a **state variable** forbidding the free liquidation of a
herd, which the article itself acknowledges).

The residual gap — grassland, plantain, small crops — matches the limits **the article itself
acknowledges**. The detail of each dead end is in the journal.

### E.6 — Three reading precautions

- **The PAD floor imposed by eligibility is 1.5 %** (348 ha out of 23 578). The gap is therefore
  **not** explained by the mask: it is an optimisation choice, not an impossibility.
- **The per-farm PAD of the selected calibration has a median of 0.0 % for a mean of 26.3 %**
  (quartiles 0 / 0 / 30.6), and 72.3 % of farms are under the article's 20 % threshold. **Do not
  read the mean as a uniform gap.** (This entry used to give 18.5 % / 51.5 % — the figures of the
  GAMS-parity run, not of the selected one; corrected 2026-09-22 after recounting
  `calibration_pad_by_farm.csv`.)
- Several indicators fall **within the uncertainty range of the observation itself** (subsidy,
  revenue, nitrogen, FTE): the 2017 land use being known only at aggregate level, the gap to the
  "central" value proves nothing there.

---

## F. Mapping {#carte}

### F.1 — Major — The map rests on a rebuilt join

`data/gis/01_RPG 2017/` and `plot_data` describe the **same plot universe** (24 734 records on
each side, 4 638 farms on both, **exactly the same size distribution**, zero orphan signature) —
but **no common identifier**: the model uses `P1..P24734`, invented upstream.

The join is rebuilt by **farm signature** (multiset of commune + area), then plot by plot within
the matched farm.

-> **Coverage: 99.4 % of plots**, 96.7 % of farms. Independent check: each polygon's footprint is
always ≥ the declared area (median ratio 1.74, 0 anomaly out of 2 000).

**What it does not allow**: **~1 557 plots** share commune AND area with a neighbour of the same
farm — they may have been swapped. Territorial and regional readings are reliable; **a single
plot proves nothing.** The page says so. This join is also the first obstacle to handing the
optimised plan to MAELIA, which needs real parcels.

### F.2 — Minor — No coordinate in the tables

`Data_Parc` has neither lat/long nor a geometry identifier. Outside `data/gis/`, spatial
reporting aggregates by `ILE`/`REGION`/`COMMUNE` only.

---

## G. Miscellaneous

### G.1 — Major — `zone_filter` does not rescale the territorial quotas by default

A subset becomes **infeasible** against thresholds meant for the whole territory.
`scale_territorial_bounds: true` fixes it — **opt-in**, because rewriting a threshold changes
what the scenario says.

### G.2 — Major — `Eq_CS_GFA` is disabled

`cs_gfa_minimum_share` (60 % of cane on each GFA farm) is correct and tested, and **disabled**.
It was re-enabled on 2026-07-21 with `skip_when_no_eligible_area: true` — skipping the three
farms whose plots are all fallow-locked — then **disabled again the same day**: 7 GFA farms need
more labour for their 60 % of cane than `farm_labor_hours_max` grants them. Both constraints are
faithful to GAMS; together they are unsatisfiable on this data. The config comment has the
detail; the roadmap item is `cs-gfa`.

### G.3 — Major — Fibre-cane block (`CF`) not wired

The equations `Eq_CF_*` stay out of the model; the `CF_*` crops are suppressed by `cf_supp`, as
GAMS does. Separately, since 2026-09-08 the price and yield tables are read from
`indice_H/Prix_Cult_CF_<scenario>.txt` and `Rdt_Cult_CF_<scenario>.txt`, because those are the
files GAMS includes (DONNEES.txt:283-289) — despite their name, they cover every crop, not only
fibre cane. **Settle the meaning of the CF equations with the source before wiring them**
(roadmap `fibre-cane-block`).

### G.4 — Minor — Rpest: an artificial floor and a "weighted mean" that is not one

- A pesticide-free crop sums `ADI = 0` and `AQUATOX = 0`; yet the thresholds make the **low**
  end of ADI the unfavourable side. "No product" is therefore encoded exactly like "the most
  toxic product" -> grassland, fallow and `MA_PLBIO` at **2.36** against 8.81 for intensive
  banana. **The ranking is solid; the absolute level of the bottom of the scale is not.**
- The dose cancels between numerator and denominator: the announced "weighted mean" is a
  **plain sum**. Many small treatments score higher than one large one.

### G.5 — Minor — Organic by itinerary includes grassland

`PN_PIQ` and `PN_TOUR` use `PROC_BIO_BOVIN`. On `output_3`, **the whole** "organic" area
(6 096 ha) is the grassland floor, and the organic area **excluding grassland is 0 ha**.

-> Read the `organic_area_excl_grassland_*` variant for any statement about cropland. Same logic
for AECMs: agroecology (AECM) and organic are reported **separately**, because green-harvested
cane is not organic.

### G.6 — Minor — `NC` carries `Var_Rdt = 1.0`

"Not cultivated" given a 100 % loss is an artefact of the source table. No effect on the price
shock, but its contribution to the margin at risk is `margin_NC x 1.0`.

### G.7 — Major — Runs written before 2026-09-22 use French names

Recap keys (`total_azote`), labels (`mo_max_expl`), policies (`P4_statu_quo`) and some CSV names
(`etp_by_region_output.csv`) were renamed. The files in `outputs/` are **not** rewritten:
`case_studies/guadeloupe/legacy_names.py` renames on read, for the dashboard and the scripts.
Two consequences. A script reading `recap.json` directly (rather than through
`apps/dashboard/loaders.load_recap`) sees the old keys — the thesis tooling in `clement/memoire/`
does so on purpose. And `run_name` is kept verbatim, so an old run is listed under its French
name while its coordinates (`run_policy`, `run_forcing`) read in English.

### G.8 — Minor — A rule used to read backwards

Until 2026-09-22 the config described `Eq_IG_CLD` as "IG_TUT only where the black-leaf-streak
risk RISQUE_CLD <= 3". The rule actually **forbids** staked yam where the **chlordecone** risk is
medium to very high (RISQUE_CLD <= 3, 1 being the worst), as GAMS does; the backwards-named
`max_risk_threshold` rule said the opposite of what it did. Both chlordecone rules are now
written as `attribute_forbidden`. `docs/gams_port_inventory.md` carried the same inverted
wording and was corrected.

---

## Cheat sheet: the five not to forget

1. **An indicator a constraint fixes is a hypothesis, not a result.**
2. **Comparing totals between scenarios with different areas means nothing** — read the
   intensities.
3. **Do not quote the 6.6 % territorial PAD** — quote types / plots / area, and cane.
4. **A solve that hits the time limit is provably wrong**, not just imprecise.
5. **A single plot on the map proves nothing.**
