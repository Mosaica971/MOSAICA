# Glossary: French source terms and their English names in the code

The project is written in English. Its sources are not. The original GAMS model, the data
tables and the reference article use French, and the code keeps a few French words on purpose.
This file fixes each translation **once**, so that the same concept never gets two English
names.

## What stays in French, and why

| kept verbatim | why |
|---|---|
| GAMS identifiers: `Eq_BC_QUOTA_MAX`, `Rdt_Cult`, `MO_Expl_init`, `ENTREES.txt:466` | They name objects in `context/gams/`, which is the reference for parity. A translated name could not be searched for in the source. |
| Data file names and column names: `Data_Parc_Gwad_2017.txt`, `PENTE`, `ALTITUDE`, `RISQUE_CLD`, `IRRIG_PARC` | They are the schema of external files that the project reads but does not own. Python holds them in string literals and binds them to English variable names. |
| Crop codes: `CS_MG_NISM`, `BA_INT`, `PN_PIQ`, … | Data codes shared with the GAMS model and the RPG. `crop_labels.CROP_LABELS` gives the English name of each. |
| Place names: Basse-Terre, Grande-Terre, Marie-Galante | Proper nouns. |
| Scheme names: POSEI, GFA, RPG, Agreste, Ecophyto, EGalim | Proper nouns of French or EU programmes. The glossary explains each below. |
| `clement/` (thesis, defence, corpus) | A French academic document, submitted and closed. |

Everything else is in English: identifiers, config labels, scenario names, recap keys, CSV
names, dashboard text, comments and docs.

## Domain terms

| French (source) | English (code) | notes |
|---|---|---|
| parcelle | plot | `plot_data` holds `Data_Parc_Gwad_2017.txt` |
| exploitation (`EXPL`) | farm | `farm_plot_map` holds `EXPL_PARC_2017.set` |
| culture (`CULT`) | crop | the `_cult` suffix becomes a `crop_` prefix: `crop_margin_per_ha` |
| itinéraire technique (ITK) | crop management sequence; `itk` in identifiers | one fine crop code = one crop × one ITK |
| opération technique (OTK) | technical operation; `operation` | `crop_operation_matrix` holds `Matrice_OTK_Cult_<scenario>.txt` |
| assolement | cropping plan / allocation | |
| rendement (`Rdt`) | yield | `crop_yield`, t/ha |
| variance de rendement (`Var_Rdt`) | yield variance | `crop_variance_per_ha` |
| prix (`Prix`) | price | `crop_price`, EUR/t |
| marge brute (`MB`) | gross margin | `crop_margin_per_ha`, EUR/ha/year |
| produit brut (`PB`) | gross product | |
| charges variables (`CV`) | variable cost | |
| main-d'œuvre (`MO`) | labour | hours |
| ETP (équivalent temps plein) | FTE (full-time equivalent) | 1 607 h per FTE |
| aversion au risque (`AVERS`) | risk aversion | `farm_risk_aversion` |
| type d'exploitation (`TYPE_EXPL`) | farm type | `farm_type`; `TYPE_EXPL_Bis` → `farm_type_secondary` |
| durée de cycle / de plantation | cycle duration / plantation duration | months / years, as in the GAMS tables |
| bassin versant (`BV`) | watershed | `watershed_plot_map` |
| captage (`CPT`) | catchment | `catchment_plot_map` |
| île, région, commune | island, region, commune | |
| jachère | fallow | |
| friche | abandoned land (fallow lock) | the `fallow_lock` rule, GAMS `Eq_FRICHE` |
| prairie | grassland / pasture | `PN` crops |
| sole, SAU | area, utilised agricultural area (UAA) | |

## Indicators

| French (source) | English (code) | notes |
|---|---|---|
| azote | nitrogen | `total_nitrogen`, kg N |
| phosphore | phosphorus | P₂O₅, read off fertiliser names |
| potasse | potassium | K₂O |
| GES (gaz à effet de serre) | GHG (greenhouse gas) | `total_ghg` |
| IFT (indice de fréquence de traitement) | TFI (treatment frequency index) | `total_tfi` |
| chlordécone (`CLD`) | chlordecone | `chlordecone_risk_area` |
| MAE (mesure agro-environnementale) | AECM (agri-environment-climate measure) | `crop_aecm_per_ha` |
| bio | organic | `crop_is_organic` |
| besoin en eau | water need | m³ |
| carbone organique du sol | soil organic carbon | |
| autonomie alimentaire | food self-sufficiency | |
| PAD (pourcentage d'écart absolu) | PAD (percentage absolute deviation) | Chopin et al. (2015) already use the acronym in English |
| Rpest (Tixier) | Rpest | proper name of the indicator |

## Scenario vocabulary

| French (source) | English (code) |
|---|---|
| politique | policy |
| forçage | forcing |
| balayage | sweep |
| plan d'étape | stage plan (`plan_stage_*.yaml`) |
| plancher / plafond | floor / ceiling (`_min` / `_max` in labels) |
| seuil | threshold |
| calibration retenue | selected calibration (`calib_selected`) |
| calibration à parité GAMS | GAMS-parity calibration (`calib_gams_parity`) |

## Programmes and data sources (proper nouns)

| name | what it is |
|---|---|
| **POSEI** | EU support scheme for agriculture in the outermost regions; the main subsidy stream |
| **GFA** (groupement foncier agricole) | land-tenure scheme whose leases require a sugarcane share |
| **RPG** (registre parcellaire graphique) | the French CAP land-parcel register, source of the 2017 observed land use |
| **Agreste** | the French Ministry of Agriculture's statistics service |
| **Ecophyto** | French national plan to reduce pesticide use (the P7 policy) |
| **EGalim** | French law on sourcing requirements for public catering |
| **Karusmart** | the 25 experimental market-gardening variants `MA_{BAG,BRF,PAI}_*` |
