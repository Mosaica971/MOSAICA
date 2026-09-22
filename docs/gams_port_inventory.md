# Inventaire de portage GAMS → Python

État équation par équation du portage de MOSAICA depuis `context/gams/`.
Référence : `MODELE.txt` (équations), `SETS.txt` (appartenances), `ENTREES.txt` (données),
`OPTIMISATION.txt` (indicateurs).

Statuts : **porté** (équivalent Python actif) / **implicite** (obtenu sans équation
dédiée) / **différé** (identifié, pas encore fait) / **écarté** (délibérément non porté).

Dernière mise à jour : 2026-08-09 (les lignes `Eq_MO_MAX_Expl` et « objectifs » étaient
périmées depuis le 2026-07-21 : les deux sont désormais actives).

## Éligibilité — bornes numériques

| Équation | Rôle | Statut | Localisation Python |
|---|---|---|---|
| Bornes `ALTI_MIN/MAX` | Altitude admissible par culture | porté | `config.yaml eligibility_criteria` → `core/data/eligibility.compute_eligibility_mask` |
| Bornes `PENTE_MIN/MAX` | Pente | porté | idem |
| Bornes `PLUVIO_MIN/MAX` | Pluviométrie | porté | idem |
| Bornes `SURF_MIN/MAX` | Taille de parcelle | porté | idem |

## Éligibilité — règles catégorielles

| Équation | Rôle | Statut | Localisation Python |
|---|---|---|---|
| `Eq_ME_IRR`, `Eq_MA_ROTA_IRR` | ME / MA_ROTA seulement en irrigué | porté | `irrigation_required` |
| `Eq_AN_SOL` | Ananas interdit sur type de sol 2 | porté | `soil_type_forbidden` |
| melon / sol / île | ME interdit sur sols 2-3-4 et en Basse-Terre | porté | `melon_soil_restriction` |
| `Eq_IG_CLD` | IG_TUT seulement si `RISQUE_CLD` ≤ 3 | porté | `max_risk_threshold` |
| `Eq_PN_PIQ_CLD` | PN_PIQ seulement si `RISQUE_CLD` = 1 | porté | `exact_risk_value` |
| melon / petites régions | ME interdit dans une liste de `REGION_CODE` | porté | `region_crop_forbidden` — voir *question ouverte* ci-dessous |
| `Eq_FRICHE` | Parcelles en friche 2015-2017 verrouillées | porté | `friche_lock` |

## Éligibilité — bans ITK géographiques (portés le 2026-07-20)

Tous via `attribute_forbidden` / `forbid_crops` (`core/data/eligibility.py`), paramétrés
dans `config.yaml categorical_rules`. Ils utilisent `data_parc["REGION"]` (entier 1-7,
macro-région agronomique), `COMMUNE` (INSEE) et `ILE` (1=Basse-Terre, 2=Grande-Terre,
3=Marie-Galante) — **jamais** `REGION_CODE`.

| Équation | Condition GAMS | Statut |
|---|---|---|
| `Eq_CS_IRR` | `IRRIG_PARC ∈ {0,1}` → toutes parcelles | porté (`forbid_crops` sur `SC_CS_IRRIG`) |
| `Eq_CS_SOL_SQUE` | `SOL_COURT = 1` | porté |
| `Eq_CS_CONFORM` | `CONFORM > 1500` | porté |
| `Eq_CS_BT` | `ILE ≠ 1 AND REGION ≠ 5` | porté |
| `Eq_CS_SBT` | `REGION ≠ 5` | porté |
| `Eq_CS_NGT` | `COMMUNE ∉ {97102, 97119, 97122}` | porté |
| `Eq_CS_CGT` | `COMMUNE ∉ {97116, 97113, 97101}` | porté |
| `Eq_CS_EGT` | `COMMUNE ∉ {97117, 97128, 97125}` | porté |
| `Eq_CS_MG` | `ILE ≠ 3` | porté |
| `Eq_MA_TO_CHOU_JA_LOC` | `ILE ≠ 1 AND IRRIG_PARC = 0` | porté |
| `Eq_ME_MG` | `REGION = 7` | porté |
| `Eq_IG_PLA_ILE` | `ILE = 1` | porté |
| `Eq_IG_TUT_ILE` | `ILE ≠ 1` | porté |
| `Eq_BA_IRR` | `IRRIG_PARC = 0` | porté |
| `Eq_BA_IRR_BT` | `ILE = 1` | porté |
| `Eq_BC_BT` | `ILE ≠ 1` | porté |
| `Eq_BC_GTMG` | `ILE = 1` | porté |
| `Eq_BC_IRR_BT` | `PLUVIO_PARC < 2300 AND IRRIG_PARC = 0` | porté |
| `Eq_BC_IRR_GTMG` | `ILE ≠ 1 AND IRRIG_PARC = 0` | porté |
| `Eq_AG_IRR` | `IRRIG_PARC = 0 AND ALTITUDE < 400` | porté |
| `Eq_AG_BT` | `ILE > 1` | porté |
| `Eq_VE_IRR` | `PLUVIO_PARC < 2700 AND IRRIG_PARC = 0` | porté |
| `Eq_VE_BTGT` | voir *bug GAMS* ci-dessous | porté (comportement réel) |
| `Eq_VE_PLUIE` | voir *bug GAMS* ci-dessous | porté (comportement réel) |

### Bug GAMS porté fidèlement — `Eq_VE_BTGT` / `Eq_VE_PLUIE`

`MODELE.txt:305-307` interroge `Data_RPG_Gwad` sur des colonnes `REGION` et `ILE` qui
**n'existent pas** dans cette table : `Data_RPG_Gwad_2017.txt` ne contient que `ident` et
`cult_2012..cult_2017`, et tous les autres usages dans `ENTREES.txt` ne l'indexent que par
`cult_20XX`. GAMS renvoie 0 pour un tel accès, sans avertissement. Conséquences :

- `Eq_VE_BTGT` : `Data_Parc.REGION = 4 OR Data_RPG.REGION = 5` → le second terme est
  toujours faux → le ban effectif est **`REGION = 4` seulement**, pas `{4, 5}`.
- `Eq_VE_PLUIE` : `Data_RPG.REGION = 6 OR Data_RPG.ILE ≠ 1` → le premier terme est toujours
  faux, le second vaut `0 ≠ 1` donc **toujours vrai** → `VE_PLUIE` est en réalité **interdite
  sur toute parcelle**.

Décision du 2026-07-20 : porter le comportement réel du GAMS (mandat de parité). Les
variantes « intention présumée » sont écrites dans `config.yaml` juste à côté, en
`enable: false` — basculer les paires suffit à tester l'autre lecture.

### Question ouverte — `Eq_ME_MG` vs la règle melon `REGION_CODE`

`Eq_ME_MG` interdit ME en `REGION = 7` (macro-région). La règle `region_crop_forbidden`
préexistante interdit ME dans 18 `REGION_CODE` (R0-R27, petites régions). Les deux
référentiels sont distincts et les deux règles sont restrictives, donc leur intersection est
sûre — mais on ignore si la seconde était censée *remplacer* la première. À vérifier avec la
source des données.

## Rotations et quotas par exploitation

| Équation | Rôle | Statut | Localisation Python |
|---|---|---|---|
| `Eq_AN_AGRO_MAX`, `Eq_IG_AGRO_MAX` | Part max d'une famille par exploitation | porté | `farm_area_share_max` |
| `Eq_BA_JA` | Jachère ≥ `PROP_BA_JA` × banane export | porté | `farm_area_ratio_min` (`ba_ja`) |
| `Eq_BA_ROTA` | Jachère + canne (+ CF) ≥ `PROP_BA_JA` × banane | porté | `farm_area_ratio_min` (`ba_rota`) — terme CF absent tant que le bloc CF n'est pas câblé |
| `Eq_CS_GFA` | Part min de canne sur les exploitations GFA | porté, **désactivé par choix** | `cs_gfa_minimum_share` — infaisable sur les données 2017 réelles, comme en GAMS |
| `Eq_AN_PA` | `AN_PA` interdit si `Surf_Expl_Parc_init < AN_SURF_EXPL_MIN` | porté | `attribute_forbidden` sur `SURF_EXPL_PARC < 10` — la colonne porte la surface de l'exploitation propriétaire de la parcelle, donc la règle s'exprime sans indexation par exploitation. Cette ligne annonçait « différé » jusqu'au 2026-09-08 : c'était périmé, le portage date du 2026-07-27. |
| `Eq_BA_QUOTA_Expl` | Tonnage de banane export de CHAQUE exploitation ≤ sa production 2017 | porté 2026-09-08 | `farm_production_bound` (`ba_quota_expl`) — nouveau builder ; la référence par exploitation vient de `compute_farm_baseline_production_t`, qui valorise chaque groupe observé par sa variante représentante faute de mix fin, ce qui **desserre** le plafond d'environ 18 %. |

## Territoire

| Équation | Rôle | Statut | Localisation Python |
|---|---|---|---|
| `Eq_*_PROD_MIN` | Planchers de production par filière | porté | `territory_production_bound` (`sense: ge`) |
| `Eq_*_QUOTA_MAX` | Plafonds de production | porté | `territory_production_bound` (`sense: le`) |
| `Eq_LEG/FRU_PROD_OBJ`, `Eq_PAT_SURF_OBJ` | Objectifs légumes / fruits / patrimoine | porté | `territory_production_bound` |
| `Eq_TUB_PROD_OBJ` | Objectif tubercules | porté mais **no-op** | `tub_prod_obj`, `enable: false`, seuil 0 — placeholder de traçabilité |
| `Eq_MO_MAX_Expl` | Plafond de main d'œuvre par exploitation | **porté et actif** | `farm_labor_hours_max`, `slack: 1.0`. L'obstacle était que `MO_Expl_init` suppose l'allocation fine 2017, qui n'a jamais existé ; il est levé par l'approximation « cultures représentantes » (`baseline_representative_crops`). C'est aujourd'hui **la contrainte dominante** : sans elle l'optimum réclame 21 593 ETP là où le territoire en comptait 3 598 (facteur 6). Corollaire à connaître : changer une représentante change le plafond, donc l'optimum — cf. `docs/04-vigilance.md` C.2. |

## Objectifs

| Équation | Rôle | Statut | Localisation Python |
|---|---|---|---|
| Marge brute | Somme marge/ha × surface | porté, **désactivé** | `maximize_gross_margin`. Sans le terme de risque le modèle couvre l'île de maraîchage : PAD territorial 193 %. |
| Marge ajustée au risque | Marge × (1 − `AVERS` × `Var_Rdt_Cult`) | porté, **actif par défaut** | `maximize_risk_adjusted_gross_margin` — l'objectif réel des solves GAMS (`Eq_REV_MARKOVITZ`). `AVERS` est calculé en mémoire depuis la cascade `TYPE_EXPL` (8 coefficients, `OPTIMISATION.txt:1745-1754`) et non lu dans le stub `Avers.txt`. ⚠ `Var_Rdt_Cult` est une **fraction de perte de marge**, ni une variance ni un coefficient de variation : la pénalité est linéaire en surface, sans carré ni covariance — cf. `docs/04-vigilance.md` D.4. |

## Bloc canne fourragère (CF)

`Eq_CF_SOL_SQUE`, `Eq_CF_CONFORM`, `Eq_CF_BT`, `Eq_CF_SBT`, `Eq_CF_NGT`, `Eq_CF_CGT`,
`Eq_CF_EGT`, `Eq_CF_MG`, `Eq_CF_MIN`, `Eq_CF_T0..T8` → **différé en bloc (lot séparé)**.
Les données existent (`Prix_Cult_CF_{RESTIT,SMART}.txt`, `Rdt_Cult_CF_{RESTIT,SMART}.txt`)
mais ne sont jamais lues par `data_pipeline.py`. Les bans géographiques CF utilisent
`REGION` (BT↔{4,6}, SBT↔5, NGT↔3, CGT↔1, EGT↔2), un mapping différent de celui de la canne
à sucre qui passe par `COMMUNE` — à confirmer au moment du câblage.

## Équations rendues implicites

| Équation | Pourquoi aucune contrainte n'est nécessaire |
|---|---|
| `Eq_AN_SUPP`, `Eq_BA_SUPP`, `Eq_BC_SUPP`, `Eq_CS_SUPP`, `Eq_IG_SUPP`, `Eq_MA_SUPP`, `Eq_PN_SUPP`, `Eq_VE_SUPP`, `Eq_CF_SUPP`, `Eq_TH_SUPP`, `Eq_PN_TOUR_SUPP`, `Eq_MA_EXP_SUPP`, `Eq_CS_SBT_NISM_supp`, `Eq_CS_MG_NIM_supp` | Ces équations annulent des **codes agrégats** (ou des variantes d'essai). Côté Python ces codes portent une économie nulle : le solveur ne les choisit jamais, l'interdiction est donc sans objet. À porter explicitement seulement si l'économie de ces codes devenait non nulle. |
