# MAELIA — file-by-file reference

Lookup tables distilled from the MAELIA user guide (2026-08-18), for writing or reading MAELIA
files without reopening the PDFs. What it all means for the coupling is in
[README.md](README.md). Full text: `context/maelia/text/*.txt`. Field names are **as printed in the
guide**; check them against a real `includes/` folder before writing a converter (see
§ Errata).

Conventions for every csv: separator `;`, decimal `.`, no quotes, columns matched by header
(order free unless stated), sub-period values separated by `|`, Julian days 1-366.

---

## Workspace tree

```
MAELIA_<ver>_GAMA_<ver>/
  includes/<study_area>/            input data (csv + shp) -- one folder per study area or scenario
    modeleCommun/                   shared by several modules
      communes/                     departement.shp (CODE_DEPT), communes.shp (CODE_INSEE, NOM)
      typesDeSol/                   typeDeSolParZH.shp
      date/                         joursParMois.csv
      meteo/                        polygonesMeteoFrance.shp, observee/<year>.csv
      simulee/<climate_scenario>/   projected weather (launcher: nomScenarioClimatique)
      altitude/                     altitudeAgregeesParZH.shp
    modeleAgricole/
      ilots/dansZone/               ilots.shp, parcelles.shp        (horsZone/: *_HZ.shp)
      culture(s)/                   especesCultivees.csv, especesHerbSim.csv,
                                    reglesDeDecisions.csv, reglesDeDecisions_fertilisation.csv
      Engrais/                      engrais.csv
      marcheAgricole/               prixVentes<SC>.csv, primes.csv, chargesOp.csv,
                                    chargesDePassage.csv, prixEau.csv, redevanceEau.csv
      agriculteur(s)/               exploitations.csv, materiel.csv, perceptionAgriculteurs.csv,
                                    profilesAgriculteurs.csv, dateDose.csv
    modeleHydrographique/
      zonesHydrographiques/         ZH.shp, donneesMNT_ZH.csv, contourZH.shp, DEM files
      HRU/                          hru_0.25.shp (no agricultural module), hruSansIlots_0.25.shp
      canaux/, retenuesCollinaires/, equipements/, altitude/, clc/, troncons/, nappe/
    modeleNormatif/
      pointsDeReference/, barrage/, zonesAdministratives/
  models/
    main/                           launchers (launcherBase.gaml), log/ (run outputs)
    modeleAgricole/ modeleCommun/ modeleHydrographique/ modeleNormatif/
    output/  (ecritureResultats.gaml)  processus/  testsUnitaires/
```

The guide spells some folders both ways (`culture` / `cultures`, `agriculteur` /
`agriculteurs`); the coherence check uses `./modeleAgricole/cultures/` and
`./modeleAgricole/agriculteurs/`.

---

## Input files

### Common

| file | key fields | notes |
|---|---|---|
| `typeDeSolParZH.shp` | `ID_SOL` (unique; the ZH-STU_DOM-ZONE_PEDO combination), `STU_DOM`, `ZONE_PEDO`, `PIRM` (infiltrability, mm/day, surface), `PRO` (rootable depth, cm), per horizon N=1..10: `P`N (cumulative depth, cm — nested, not thicknesses), `ARG`N (clay %), `CX`N (stones %), `DAH`N (bulk density g/cm³), `RUPRH`N (available water, mm), `KSAT`N (mm/h), `CSTRU` (root access 0-1, default 0.9); NC: `PH`N, `CN`N, `CAL`N, `MO`N, `HCC1`, `HPF1` | soil types are described **per ZH**. DAH by Saxton & Rawls (2006) when missing |
| required soil fields (coherence check) | AqYield: `ARG1, CSTRU, DAH1, ID_SOL, ID_ZH, KSAT1, P1, PIRm, PRO_OC, RUPRH1, STU_DOM, ZONE_PEDO, DAH_OC`; AqYieldNC: `ARG1, CSTRU, DAH1, ID_SOL, ID_ZH, KSAT1, P1, PIRm, PRO_OC, RUPRH1, STU_DOM, ZONE_PEDO, CAL1, CN1, EG1, HCC1, HPFP1, MO1, SAB1` | if `P4` exists, `ARG4` must too (not checked) |
| `polygonesMeteoFrance.shp` | `ID_PDG`, `POSX`, `POSY` (Lambert II extended, hm), `ALTI_MOY` | the weather grid |
| `meteo/observee/<year>.csv` | `ID_PDG;DATE;RRmm;Tmin;Tmax;ETP;RGI` — **this order** | DATE `dd/mm/yyyy`; mm, °C, mm, MJ/m²/day |
| `joursParMois.csv` | month; first day of month (leap); first day (non-leap) | fixed content, counting from 0 |
| `altitudeAgregeesParZH.shp` | `ID_ZH`, `ALTI_MOY`, `ID_ALTI` (`ID_ZH-ALTI_MOY-0`) | snow only; missing file = no snow |

### Agricultural module

| file | key fields | notes |
|---|---|---|
| `ilots.shp` | `ID_ILOT`, `ID_EXPL`, `ID_SOL` (dominant soil), `ID_ZH`, `CARACT_IRR` (O/N), `MATERIEL`, `LISTE_EQUIS` (ids joined by `-`), `PENTE_MOY`, `PENTE_SWAT`, `EQU_0..2` (equipment priority) | without `ID_EXPL` all blocks belong to one farm |
| `parcelles.shp` | `ID_PARCELL` (`<ID_ILOT>_xx`), `ID_ILOT`, `ID_EXPL`, `SEQUENCE` (crops joined by `_`), `POURCENTAG` (share of the block), `INDEX_DEP` (start rank, optional), `CULT_REF` (crop in the reference year), `SURFACE` (ha), `EXPREST` (`exportation`/`exp`/`restitution`/`rest` per crop, same length as `SEQUENCE`) | the plan MAELIA executes under `nomChoixAssolement='Donnees'` |
| `especesCultivees.csv` | one **column per species**, rows = parameters (below) | `RENDEMENT_OPTIMAL` must be adapted to the study area |
| `especesHerbSim.csv` | grassland species for HerbSim / HerbSimNC | table not rendered in the guide |
| `reglesDeDecisions.csv` | one **column per ITK**: `ID_ESPECE`, `ID_PREC`, `ZONE_PEDO`, `TYPE_EXPL`, `MATERIEL`, climate zone, `IS_<OT>` (operation exists), per operation: dates (`80\|105\|130`), trigger values, depths | generated by the ITK web application; `*` = all |
| `reglesDeDecisions_fertilisation.csv` | one column per application: `FERTIALT_ORDRE_ALTERNATIVE`, `FERTIALT_ORDRE_APPORT`, `FERTIALT_NOM_PRODUIT`, `FERTIALT_DOSE` (kg element/ha mineral; t raw/ha organic), `FERTIALT_DOSE_P`, `FERTIALT_DOSE_K`, triggers | only `FERTIALT_HUM_MAX_SOL`, `FERTIALT_N_J_CUMUL_PLUIE`/`FERTIALT_CUMUL_PLUIE`, `FERTIALT_SEUIL_VEGE` are read today |
| `engrais.csv` | one column per fertiliser: C, N, Norg, Nmin, CNorg, hum (% fresh matter), decomposition parameters (K1, C2, kres1, kres2, kbio, CNbio, aCN1, Y, H — Levavasseur 2021), trace metals `ETM_*`, `Fertilizer_type` (mineral/organic), NH₃ factors (`EF_normal_pH`, `EF_high_pH`, `EF`), `Fertilizer_form`, `eqCO2_MinN/P/K`, `eqCO2_PRO`, `CoutT` (€/t), `QuantiteDispoAnnuelleT`, `plan_epandage` | stock 0 = never applied; unlimited = `1000000000` |
| `prixVentes<SC>.csv` | `ID_TYPE` (species), `NOM` (not read), one column per year | unit printed "€/ha" — see Errata; scenarios listed in the launcher |
| `primes.csv` | `ID_TYPE`, `NOM`, `ID_DEPARTEMENT`, one column per year (€/ha) | coupled subsidies |
| `chargesOp.csv` | `NOM_ITK_AFFICHAGE` (ITK id), `ESPECE_x_materielIrrigation` (not read), one column per year (€/ha) | operational costs excl. irrigation → gross margin |
| `chargesDePassage.csv` | same layout (€/ha) | machinery costs → semi-net margin |
| `prixEau.csv`, `redevanceEau.csv` | `source` (NAPP groundwater, SURF surface, RET reservoir, CAN canal), one column per year (€/m³) | |
| `exploitations.csv` | `ID_EXPL` (unique, one row per farm of `ilots.shp`), `TYPE_EXPL` | `TYPE_EXPL` values must match `reglesDeDecisions.csv` |
| `materiel.csv` | first header cell empty (line starts with `;`); first column = equipment ids | must match `reglesDeDecisions.csv` `MATERIEL` and `ilots` `MATERIEL`; `NA` needs no row |
| `perceptionAgriculteurs.csv` | farmer id; perception bias on time windows (days), vegetation, rain and soil water (coefficients) | desynchronises identical agents |
| `profilesAgriculteurs.csv` | weights on income, income variability, free days, transaction costs | only for the belief-function crop choice ("expert mode") |

`especesCultivees.csv` rows (AqYield unless noted, all mandatory unless noted):
yields — `RENDEMENT_MOYEN`, `RENDEMENT_MIN` (optional), `RENDEMENT_OPTIMAL` (potential,
t/ha, mandatory — the one the crop model scales down); display colour `COULEUR_R/V/B`; phenology — `Tbase`, `Tmax`,
`DEGRES_J_LevTbase` (emergence), `DEGRES_J_Flor`, `DEGRES_J_matPhyTbase` (maturity), `FREIN`
(winter fraction); water — `CRACINE` (root growth), `CVIG`, `KMAX` (max Kc), `CSTO` (stomatal
closure), `coeff_Fonction_Prod` (shape of Yield/YieldMax = f(ETR/ETM)); `ZonesClimatiques`
(where the crop can grow); nitrogen and carbon (NC) — `BESOIN_N` (kg N/t), `DEBUT_BESOIN_N`,
`FREIN_BESOIN_N`, `PRE_FLO_BESOIN_N`, `PRE_MAT_BESOIN_N`, `Tms` (dry matter of product),
`C_aer`, `C_rac`, `isLEG`, `ABSCISSION`, `isCouvert`, `HI` (harvest index), `Pse`, `beta`,
`SR_ratio`, `RootC_fixed` (optional), `CN_ratio`, `adil`/`bdil` (critical N dilution curve),
`Type_Nacq`, `a_Ndemand_ci`/`b_Ndemand_ci`, `coef_500Mat`, `N_grain`, `especeRepousse`.
Cover crops: `ciVesce` lasts 5-6 months at most, `ciMoutardeBlanche` 3.

### Hydrological module (skip when `executerModeleHydrographique = FALSE`)

| file | key fields |
|---|---|
| `ZH.shp` | `ID_ZH`, `ID_ND_EXUT` (downstream ZH — the flow tree), optional water-body ids `EU_CD`, `EU_CD_exut`, `PERCENTAGE` |
| `donneesMNT_ZH.csv` | per ZH: `W_bnkful` (CH_W2), `depth_bnkful` (CH_D), `slp_ch` (CH_S2), `L_slp.zh` (SLSUBBSN), `CH_S1`, `CH_W1` — from ArcSWAT |
| `HRU_*.shp` | `ID_HRU`, `FRACTION`, `ID_ZH`, `SURFACE` (m²), `ID_SOL`, `ID_PENTE` (classes 1.5/5/11/22.5/35 %), `ID_CLC` |
| `retenueParZH.shp` | `ID_RESSOUR`, `ID_ZH`, `ORDREDRAIN`, `FRACTIONDR`, `SURFACERET`, `TYPEOFRET` (SURNAPPE / Deconnectees / Connectees), `VOLMAX`, `TYPEDEDRAIN`, `Q_RESERVE` |
| `canaux.csv` | `ID_Canal`, `BVe_origine`, `dataObs` (daily m³/s file), `debitmax`, return points `BVe_retourX`, `fractionEteX`, `fractionHiverX` |
| `pp*.shp`, `rj*.shp` | withdrawal/discharge points (drinking water, industry, irrigation): `ID_EQU`, `ID_RESS_ZH`, `ID_ZH`, `NATURE`, `VOL_AGENCE`, … — used to link irrigable blocks to resources, not by the simulator |
| DEM | `alti25m_ascii.txt`, `MNTTIFN_Alti.tif`, `pente_percent_ascii.txt` |

### Normative module (skip when `executerModeleNormatif = FALSE`)

`pointsDeReference.shp` (`ID_STH`, `ID_ZH`, `IS_NODAL`, `DOE`, `DCR` m³/s), `barrage.csv` (one
**column** per dam, **row order fixed**: volumes hm³, flows m³/s, priority, release days,
efficiencies, transfer time), `zonesAdministratives.shp` (`ID_ZA`, `ID_STH`),
`seuilsDeRestriction.csv`, `secteursAdministratifs.shp`, `joursDeRestriction.csv`,
`RestrictionsDebitCanaux.csv`.

### Supply-chain module

`produits.csv` (price, transport and spreading costs, dry matter, OM, N-P-K and trace
elements), `recettes.csv` (processing recipes), `routes.shp` (OSM roads), `UP.shp`
(production units), `UT.shp` (processing units).

---

## Launcher parameters

| parameter | example | meaning |
|---|---|---|
| `nomTerritoire` / `nomDecoupageZonePourLectureFichiers` | `'AveyronRef'` | study area = `includes/` subfolder |
| `anneeDebutSimulation` | 2008 | first year — **starts in August**; the plan is consistent from year 2 |
| `nbAnneesSimulation` | 8 | years simulated |
| `anneeDeReferenceRPG` | 2014 | year of the last crop of the sequences (with `'Donnees'`) |
| `simulationSurZH` + `idZHASimuler` | `['230','540']` | restrict to some watersheds |
| `executerSurEnsembleExploit` + `listIdExploitationAexecuter` | `['expl_13']` | restrict to some farms |
| `simulationSurParcelle` + `idParcelleASimuler` | `'081-5576417_01'` | one plot |
| `nomScenarioClimatique` | `'rcp2.6'` | read `modeleCommun/simulee/<name>`; absent = observed weather |
| `utiliserMemeMeteoPartout` + `idPointMeteoUnique` | `'3115'` | one weather cell everywhere |
| `modeVerbeux` | TRUE | verbose console |
| `executerModeleHydrographique` | TRUE | FALSE = unlimited water |
| `nomChoixModeleHydrographique` | `'SWAT'` | or `'Simple'` (rainfall-runoff) |
| `isPrelevementEtRejetSimules`, `affecterEqIrrSiInexistant` | TRUE | withdrawals; nearest equipment for orphan irrigated blocks |
| `listNomsZHsDebitForce`, `listNomsZHsDebitComplement`, `listeExutoiresZoneMaelia`, `ID_RESSOURCES_INFINIES` | | forced / complemented flows, outlets, infinite resources |
| `executerModeleAgricole` | TRUE | FALSE = no withdrawals, agricultural land through the hydrological module |
| **`nomChoixAssolement`** | `'Donnees'` | crop choice: **`'Donnees'` = crops from the data (`SEQUENCE`)**; `'FonctionsDeCroyances'`; a multicriteria method; a date/dose file — description clipped in the PDF |
| `fichierDateDose` | `'/modeleAgricole/agriculteurs/dateDose.csv'` | `id_parcelle;culture;an…` (clipped) |
| `activerITKAlternatif` | TRUE | behaviour when sowing misses its window (alternative ITK) |
| `forcerSemisCI` | TRUE | force cover-crop sowing |
| `avecContrainteDeMainOeuvre` | TRUE | labour limits the operations |
| `plusieursTravauxDuSolParITK`, `plusieursTraitementsPhytoParITK`, `plusieursFertilisationsParITK` | TRUE | several campaigns / strategies per ITK |
| `executerModelePaturage` | TRUE | grazing |
| `adaptationFertilisation`, `corpenProfondeurTemporelle` | `'corpen_tronque'`, 3 | adapt doses to past yields (CORPEN) |
| `gestionStocksEngrais` | `'territoire'` | fertiliser stock level (territory or supply chain) |
| `avecIlotsHorsZone` | TRUE | include out-of-area blocks |
| `isIrrigationSimulee`, `nomChoixModeleIrrigation` | TRUE, `'Simple'` | irrigation; plot-independent vs equipment rounds |
| price scenarios, main price scenario | `['SC1','SC2']`, `'SC1'` | `prixVentes<SC>.csv` |
| `option_valeur_finert`, `denit_fTemp_option` (`'Stics'`/SystN), `denit_pot_option`, `profDenit` | | soil C init and denitrification (NC) |
| `avecStressClimatique` | FALSE | climate stress (frost…) |
| `executerModeleNormatif`, `simulerBarrage`, `accelerationTourEauSiRestriction` | | normative module |
| `executerParcelleVirtuelle` | FALSE | **one virtual plot** with forced cropping: |
| `rotationForceeParcelle` | `'colza_CP_orge'` | its rotation |
| `gestionPaillesForceeParcelle` | `'restitution'` | straw management |
| `idSdcForce` | `'cbo'` | its reference cropping system |
| `typeDeSolForceParcelle` | `'rendosols'` | its soil type |
| `surfaceHectareForceParcelle` | 10.0 | its area (ha) |

Output switches: `sorties_eau`, `sorties_azote`, `sorties_carboneGES`, `sorties_retenues`,
`sorties_barrages` (all daily — heavy).

Batch: `experiment <name> type: batch until: simulationTerminee parallel: 4 { … }`, a parameter
with `<- 'first' among: ['first','second',…]`, no `display`; run
`gama-headless.bat -batch <name> "<launcher>.gaml" -memory XG` from GAMA's `headless/` folder.

---

## ITK trigger constraints

Six spatialisation criteria (crop, previous crop, soil zone, farm type, climate zone,
irrigation equipment); one situation = one ITK; each operation has 1-3 sub-periods tried in
order, each with its own trigger values.

| constraint (application name) | paired with | operations |
|---|---|---|
| `hum_max_sol` | — | tillage, sowing, fertilisation, hoeing, harvest, spraying |
| `cumul_pluie` | `n_j_cumul_pluie` | same |
| `cumul_pluie_eva` | `n_j_cumul_pluie_eva` | tillage, sowing, fertilisation, hoeing |
| `temp_min` / `temp_max` | `n_j_cumul_temp_min` / `_max` | tillage, sowing |
| `hum_min_sol` | — | sowing |
| `seuil_vege` | — | fertilisation, hoeing, harvest, spraying |
| `hauteur_pluie_signif` | — | irrigation |
| `cumul_pluie_prevue` | `n_j_cumul_pluie_prevue` | irrigation, fertilisation, harvest |
| `seuil_vege_pre` / `seul_vege_post` | — | irrigation (stop / start stage) |
| `temp_max_inf` | `n_j_cumul_temp_max_inf` | spraying |
| `hygrometrie_min` | `n_j_cumul_hygrometrie_min` | spraying |

In `reglesDeDecisions.csv` the pairs appear as `<OT>_JOURS_PLUIE` / `<OT>_HAUTEURS_PLUIE_MAX`,
`<OT>_TEMPERATURE_MIN` / `<OT>_JOURS_TEMP_MIN`, `IRRIGATION_JOURS_P-ETP_MAX` /
`IRRIGATION_P-ETP_MAX`, `PHYTO_JOURS_HYGROMETERIE` / `PHYTO_HYGROMETERIE`, etc. (full list in
`context/maelia/text/4-itk-application.txt` § 4.17.7). A pair is all-or-nothing. Entries with
`AGRIW`, `OUTIL`, `PASSAGES` (and `OT_SIMULTANEE` for fertilisation) **have no effect** yet.
Operation parameters: depth (cm), done by the farmer or a contractor, tool, work time (h/ha),
simultaneous operation, product, dose (t/ha organic, kg/ha mineral, L/ha phyto, mm
irrigation), minimum return delay (irrigation, days). Organic-fertiliser return times are
hard-coded (`parcelleAqYieldNC.gaml`).

Crop naming: a declared crop maps onto **one** MAELIA species and no two declared crops onto
the same one (else one situation could get two ITKs). A species absent from the list is
created by copying an existing `especesCultivees.csv` column, by hand, with the thematic
referent. Set-aside (`gel`) needs no ITK but must be declared as a previous crop where it
occurs; sequences loop, so the first crop's previous crop is the last one.

---

## Outputs (`models/main/log/<study_area>_<timestamp>/`)

| file | grain | columns |
|---|---|---|
| `suiviOTParParcelle.csv` | one row per operation done | `année`, `date` (Julian), `parcelle`, `exploitation`, `culture`, `ITK`, `OT`, `temps` (h), `profondeur` (cm), `RECOLTE_rendement` (t/ha), `IRRIGATION_dose` (mm), `FERTI_produit`, `FERTI_nature`, `FERTI_doseBrute`, `FERTI_apportNmin`, `FERTI_apportNorg_labile`, `FERTI_apportNorg_recalcitrant` (kg/ha), `BIOMASSE_export`, `BIOMASSE_aer_restit`, `BIOMASSE_rac_restit` (t/ha) |
| `sorties_eau.csv` | plot × period (a period ends on 31 Dec, at sowing or at harvest) | `annee`, `jourDebut`, `jourFin`, `parcelle`, `couvert` (species or `solnu`), `itk`, `evaporation`, `transpiration`, `percolation`, `capilarite`, `pluie`, `irrigation` (mm; 0 when the hydrological module is on), `satisfactionHydrique` (%), `Hr_*`, `Hm_*` (mm), `sommeDegresJourCulture` |
| `sorties_CN.csv` | same periods | `N_lixivie`, `N_volatilise_NH3`, `N_mineralise_net_SOM`, `N_mineralise_net_residus`, `N_acquis_couvert`, `N_mineral_debut/fin`, `emissions_N2O_directes`, `emissions_N2`, `N_fixe_legumineuses` (kg N/ha), `satisfactionAzote_culture`, `satisfactionAzote_ci` (%), `delta_Corg` (kg C/ha), `emissions_N2O_denit/nit/indirectes_volat/indirectes_lixiv` |
| `sorties_carboneGES.csv` | same periods | `delta_Corg`, `emissions_N2O_denit`, `emissions_N2O_nit`, `emissions_eqN2O_NH3volat`, `emissions_eqN2O_lixiv`, `emissions_ferti`, `bilan_net_GES` (kg CO₂eq/ha), `tx_MO_fin`, `ratio_Corg_Arg` (%) |
| `sorties_retenues.csv` | day × reservoir | volumes (m³), fill rate, precipitation, recharge, evaporation, withdrawals, surplus |
| `sorties_barrages.csv` | day × dam | current volume, release flow, reserved flow, remaining annual release quota, and the reservoir columns |

---

## R functions for crop sequences

Loaded with `source("http://www.misslin.com/renaud/maelia/fonctions_pretraitements_sequenc…")`
(temporary hosting; URL clipped in the PDF), on a `parcelles` shapefile read with `rgdal`.
Arguments: data frame, sequence column, area column, separator (`_`).

| function | does |
|---|---|
| `part_surfcult_sdc` | mean annual area share per crop |
| `part_1culture_dans_seq` | % of sequences (by count, not area) that are (semi-)monocultures of a crop |
| `suppr_cult_parc` | delete plots whose sequence is > x % one crop |
| `suppr_cult` | remove a crop from all sequences (may leave empty sequences — forbidden) |
| `insertion_culture` | insert a crop before/after/between given crops, in (semi-)monocultures |
| `changement_integral_seq` | replace whole (semi-)monoculture sequences |
| `changement_subseq_deuxCult` | replace sub-sequences by new ones (replacement: 1-2 crops) |
| `def_exp_rest_selon_cultures` | rebuild `EXPREST` after any change (default `restitution`) |

---

## Errata — what the guide gets wrong or leaves out

- **`prixVentes.csv` unit printed as €/ha** ("Prix par an"); a sale price per tonne is
  expected, since margin = yield × price + subsidies − costs. Check a real file.
- **`Engrais.csv` description** is a copy of `especesHerbSim.csv`'s; the field table is right.
- § 3.3.12 "Other costs" is titled `(prixEau.csv)`; the agricultural-module "subfolders" line
  repeats the common module's.
- The launcher table of the agricultural module is **clipped** (description column cut);
  `nomChoixAssolement` options other than `'Donnees'` are therefore partly unreadable.
- Trigger pairs: `ECOLTE_HAUTEURS_PLUIE_MAX` (for `RECOLTE_…`), and the `REPRISE_TEMPERATURE_*`
  pairs are listed twice with differing names.
- The general rule "column order is free" is contradicted for the weather files (fixed order).
- `especesHerbSim.csv` parameter table did not render (`character(0)`).
- Section 4.14 "Contrôle de cohérence" is empty; the content is in 4.15-4.17.
- The sim-on-a-subset parameter is called `executerModeleSurUneZH` in § 1.8 but
  `simulationSurZH` in the tables.
