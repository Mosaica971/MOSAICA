# Design — Batch de scénarios politiques + port de parité GAMS

_Date : 2026-07-17. Statut : proposé (en attente de revue utilisateur)._

## Contexte et objectif

Trois demandes bundlées par l'utilisateur :

1. **~20 scénarios** dans `case_studies/guadeloupe/scenarios.yaml`, chacun représentant une
   trajectoire politique : fuite en avant / agriculture intensive, adoption de mesures
   agroécologiques, mise en commun, bio, chocs économiques/climatiques, et des **mélanges**.
2. **Nettoyage** léger de la config et des scénarios.
3. **Inventaire GAMS** : ce qui n'est pas encore porté en Python, + **implémentation** des
   ports (choix utilisateur : « tout implémenter »).

Décisions utilisateur (brainstorming du 2026-07-17) :
- Chocs climatiques → représentés par **rendement + éligibilité** (nouveau levier `yield_multipliers`
  + coupures d'éligibilité).
- Agroécologie / bio / mise en commun → **incitation (config) ET contrainte dure (code)**.
- Livraison : **écrire les fichiers, ne PAS lancer de solve** (respecte la règle « pas de `main.py`
  à la volée » — `CLAUDE.md`).
- Périmètre code : **les 3 briques maintenant** + **tout porter** (ITK CS/CF/région,
  `Eq_MO_MAX_Expl`, `cost_multipliers`).

Ce chantier est volumineux et multi-sous-systèmes. Il est **décomposé en 5 lots séquencés** ;
chaque lot est autonome, testé, et peut être commité indépendamment. Les lots 3 et 4 portent des
**risques de disponibilité de données** explicités ci-dessous — s'ils se confirment bloquants, le
lot bascule en « documenté / différé » sans compromettre les lots précédents.

---

## Lot 1 — Leviers économiques et de transition (débloque les scénarios)

### 1.1 `yield_multipliers` (choc de rendement)
Nouvelle clé `economic_overrides.yield_multipliers`, même forme que `price_multipliers` /
`subsidy_multipliers` : liste de `{crops: [...], factor: <float>}`, cumulative sur recouvrement.

**Point d'application** : `data_pipeline.py` ligne 139, envelopper `rdt_cult` dans
`apply_crop_multipliers(..., yield_multipliers)` **immédiatement au chargement**, avant que
`rdt_cult` n'alimente le coût variable, la subvention (POSEI_Q), les ventes, le GES, et le
paramètre `crop_yield_per_ha` des quotas territoriaux. Un choc de rendement se propage ainsi de
façon **physiquement cohérente** : moins de récolte ⇒ moins de coût récolte/transport, moins
d'aide au volume, moins de tonnes vers les quotas, marge ajustée. `var_rdt_cult` (variance) reste
sur sa colonne `init` — le choc ne touche pas le risque (réservé au reporting/Markowitz).

`apply_crop_multipliers` existe déjà et est générique : aucune nouvelle fonction, juste un 3e
appel + le parse de la clé config.

### 1.2 `cost_multipliers` (choc coûts / intrants / carburant)
Nouvelle clé `economic_overrides.cost_multipliers`, même forme. Appliquée sur
`variable_cost_per_ha_cult` après `compute_variable_cost_per_ha_cult`. Débloque les scénarios de
choc économique côté offre (hausse pétrole/engrais) aujourd'hui inexprimables (seuls prix/subvention
étaient scalables). N'affecte que la marge (pas les tonnages).

### 1.3 Règle catégorielle `forbid_crops` (coupure d'éligibilité inconditionnelle)
Nouvelle règle dans `CATEGORICAL_RULE_REGISTRY` : retire une liste de cultures de l'éligibilité,
**sans condition** (masque `False` partout pour ces cultures). Utilisée par les scénarios de choc
climatique/sanitaire : sécheresse ⇒ bannir les cultures irriguées ; maladie ⇒ bannir melon/banane.
Signature alignée sur les règles existantes : retourne `(crops, condition_series_all_true)`.
*(Alternative écartée : `zone_filter` enlève des parcelles entières, pas ciblé par culture.)*

### 1.4 Contrainte `crop_share_bound` (part min/max territoriale)
Nouvelle contrainte enregistrée : généralise `farm_area_ratio_min` à l'échelle **territoire**,
avec `sense` `ge`/`le` :

```
surface(numerator_crops) ⋛ share × surface(denominator_crops)      (sommes sur toutes les parcelles)
```

Couvre les deux leviers politiques dures :
- **Part bio minimale** : `numerator` = variantes BIO du maraîchage (`MA_*BIO*`), `denominator` =
  tout le maraîchage (`SC_MA`), `sense: ge`, `share: 0.30`.
- **Plafond d'intensification** : `numerator` = variantes intensives (`BA_INT`, canne irriguée
  mécanisée `CS_*_IM`, …), `denominator` = leur filière, `sense: le`, `share: 0.X`.

Reprend la **garde « booléen trivial »** (`Constraint.Feasible/Infeasible`) documentée dans
`CLAUDE.md` pour les termes potentiellement vides.

### Tests lot 1
Style data-free existant (`tests/test_guadeloupe_constraints.py`) : configs minimales,
`plot_surface_ha`/`eligible_pairs` à la main. `apply_crop_multipliers` a déjà des tests → étendre
pour yield/cost. `crop_share_bound` : cas ge/le, cas numérateur⊂dénominateur, cas termes vides.
`forbid_crops` : masque bien mis à False pour les cultures listées, pas les autres.

---

## Lot 2 — Port de parité : restrictions ITK géographiques (règles catégorielles)

Le GAMS (`MODELE.txt`) impose des interdictions conditionnelles région/commune/sol/irrigation que le
Python **ne porte pas** — le solveur peut donc placer une variante fine dans une zone interdite.
Ces équations sont toutes de forme `X(P,C) =l= 0` sous condition → **parfaitement modélisables par
le framework des règles catégorielles** (masque d'éligibilité), sans nouvelle contrainte MILP.

Équations à porter (corps GAMS confirmé, `MODELE.txt:254-319`) :

| GAMS | Cultures visées | Condition d'interdiction |
|---|---|---|
| `Eq_CS_IRR` | `SC_CS_IRRIG` | `IRRIG_PARC ∈ {0,1}` (cf. commentaire GAMS : interdite partout — à confirmer) |
| `Eq_CS_SOL_SQUE` | `SC_CS_MECA` | `SOL_COURT = 1` |
| `Eq_CS_CONFORM` | `SC_CS_MECA` | `CONFORM > 1500` |
| `Eq_CS_BT` | `SC_CS_BT` | `ILE ≠ 1 AND REGION ≠ 5` |
| `Eq_CS_SBT` | `SC_CS_SBT` | `REGION ≠ 5` |
| `Eq_CS_NGT` | `SC_CS_NGT` | `COMMUNE ∉ {97102, 97119, 97122}` |
| `Eq_CS_CGT` | `SC_CS_CGT` | `COMMUNE ∉ {97116, 97113, 97101}` |
| `Eq_CS_EGT` | `SC_CS_EGT` | `COMMUNE ∉ {97117, 97128, 97125}` |
| `Eq_CS_MG` | `SC_CS_MG` | `ILE ≠ 3` |
| `Eq_IG_PLA_ILE` | `IG_PLA` | `ILE = 1` |
| `Eq_IG_TUT_ILE` | `IG_TUT` | `ILE ≠ 1` |
| `Eq_BA_IRR` | `BA_IRR` | `IRRIG_PARC = 0` |
| `Eq_BA_IRR_BT` | `BA_IRR` | `ILE = 1` |
| `Eq_BC_BT` | `BC_BT` | `ILE ≠ 1` |
| `Eq_BC_GTMG` | `BC_GTMG` | `ILE = 1` |
| `Eq_BC_IRR_BT` | `BC_BT` | `PLUVIO_PARC < 2300 AND IRRIG_PARC = 0` |
| `Eq_BC_IRR_GTMG` | `BC_GTMG` | `ILE ≠ 1 AND IRRIG_PARC = 0` |
| `Eq_AG_IRR` | `AG` | `IRRIG_PARC = 0 AND ALTITUDE < 400` |
| `Eq_AG_BT` | `AG` | `ILE > 1` |
| `Eq_VE_IRR` | `VE_BTGT` | `PLUVIO_PARC < 2700 AND IRRIG_PARC = 0` |
| `Eq_VE_BTGT` | `VE_BTGT` | `REGION = 4 OR REGION = 5` |
| `Eq_VE_PLUIE` | `VE_PLUIE` | `REGION = 6 OR ILE ≠ 1` |
| `Eq_MA_TO_CHOU_JA_LOC` | `MA_TO_CHOU_JA` | hors Basse-Terre (à lire précisément) |
| `Eq_AN_PA` | `AN_PA` | petites exploitations (à lire précisément) |

### Approche
Plutôt que 24 règles ad hoc, ajouter **2–3 règles catégorielles génériques paramétrables** qui
couvrent les patrons observés, et les instancier depuis `config.yaml` :
- `attribute_forbidden` : interdit `crops` là où `attribute ∈ forbidden_values` (couvre
  ILE, REGION, COMMUNE, SOL_COURT, discrets).
- `attribute_threshold_forbidden` : interdit là où `attribute {<,>,<=,>=} seuil` (couvre
  CONFORM>1500, ALTITUDE<400, PLUVIO<2300/2700).
- Combinaisons ET/OU multi-conditions : soit une règle composite paramétrable, soit décomposer
  chaque équation ET en règles empilées (le masque final est l'intersection, donc un OU
  d'interdictions = plusieurs règles ; un ET d'interdictions = une règle multi-condition). À
  arbitrer au niveau du plan d'implémentation.
- Sous-groupes `SC_CS_MECA/IRRIG/BT/SBT/NGT/CGT/EGT/MG` : transcrits depuis `SETS.txt:122-170`
  vers des ancres YAML `crop_families`.

### ⚠️ Risque bloquant : ambiguïté `REGION` vs `REGION_CODE`
Point ouvert **Mineur** de `VIGILANCE.md`. Le GAMS lit tantôt `Data_Parc_Gwad("REGION")`, tantôt
`Data_RPG_Gwad("REGION")` (numériques 1–6). Le Python a `data_parc["REGION"]` **et** un
`REGION_CODE` recalculé (`R0`…`R27`, jointure `REG_PARC_2017.set`). **Avant** de porter ces règles,
il faut trancher quelle colonne correspond au `REGION` numérique du GAMS et confirmer l'encodage
`ILE` (1=Basse-Terre, 2=Grande-Terre, 3=Marie-Galante, déduit des équations). C'est la **première
tâche** du lot 2, gate pour le reste. Sans cette résolution, le port serait faux silencieusement.

### Tests lot 2
Data-free : masque d'éligibilité sur mini-`data_parc` synthétique (quelques parcelles aux
attributs choisis), vérifier que chaque règle met bien `False` la bonne case (plot,crop) et
laisse le reste. Un test de non-régression : sur données réelles (marqué lent / opt-in), compter
les paires éligibles avant/après le port et vérifier une baisse cohérente (pas 0, pas inchangé).

---

## Lot 3 — Port `Eq_MO_MAX_Expl` (plafond main-d'œuvre par exploitation)

`MODELE.txt:368` :
```
Eq_MO_MAX_Expl(SE).. sum(SP∈E, sum(SC, X(SP,SC) * MO_Ha_Cult_init(SC))) =l= MO_Expl_init(SE);
```
Contrainte par ferme : les heures de MO mobilisées (au barème **init**) ≤ MO disponible initiale de
la ferme. Nouvelle contrainte `farm_labor_max` (patron `farm_area_share_max`, garde booléen trivial).

### ⚠️ Risque : disponibilité des données `init`
Nécessite `MO_Ha_Cult_init` (heures/ha par culture, colonne `init`) et `MO_Expl_init` (MO dispo par
ferme). `MO_Ha_Cult` est déjà calculé (colonne `year`) ; la variante `init` et surtout
`MO_Expl_init` (par exploitation) doivent être **localisées dans `data/`** avant implémentation.
**Première tâche du lot** : confirmer l'existence/format de ces tables. Si `MO_Expl_init` n'existe
pas, le lot bascule en « documenté / différé » (la contrainte est codée + testée data-free, mais
laissée `enable: false` avec commentaire, faute de données).

### Intérêt scénarios
Oppose « mise en commun » (plafond MO désactivé / mutualisé) vs contrainte par ferme réaliste.

---

## Lot 4 — Port du bloc canne-fibre (CF) — le plus lourd, gate données

Bloc `Eq_CF_*` (`MODELE.txt` / `SETS.txt:274-282`, `434`) : restrictions ITK CF (SOL_SQUE, CONFORM,
région BT/SBT/NGT/CGT/EGT/MG), plancher `Eq_CF_MIN` (`Σ X·RDT_Cult_CF ≥ Q_CF_MIN`), interdiction sur
non-cultivé `Eq_CF_NC`, et bans par type d'exploitation `Eq_CF_T0..T8` (CF interdit selon
`MATRICE_TYPE_EXPL`).

### ⚠️ Risque bloquant : données CF non chargées
`VIGILANCE.md` note déjà que `Prix_Cult_CF_{RESTIT,SMART}` et `Rdt_Cult_CF_{RESTIT,SMART}` **ne sont
pas chargés** par le pipeline, et `Q_CF_MIN` / `MATRICE_TYPE_EXPL` restent à câbler. Les cultures CF
apparaissent aujourd'hui dans `friche_lock` et les ratios de rotation, mais **sans économie ni
éligibilité propres**. Porter le bloc CF complet = travail de **data-pipeline** (charger les tables
CF, les brancher dans l'économie) + les règles/contraintes.

**Recommandation** : traiter le lot 4 en **dernier**, précédé d'une tâche de confirmation des
données CF. Les restrictions ITK CF (région/sol) réutilisent les règles génériques du lot 2 — peu
coûteuses une fois le lot 2 fait. Mais `Eq_CF_MIN` et l'économie CF dépendent des tables. Si les
données manquent, porter **seulement** les restrictions ITK CF (règles catégorielles) et **différer**
`Eq_CF_MIN` + économie CF, documenté dans `VIGILANCE.md`.

---

## Lot 5 — Scénarios, nettoyage, inventaire, VIGILANCE

### 5.1 `scenarios.yaml` — ~22 trajectoires
Format existant conservé (`overrides` / `enable` / `disable` / `set_args` / `matrix`). Chaque
scénario documenté (`name` + `description`). Familles :

| Famille | Scénarios |
|---|---|
| **Contrôle** | `baseline` |
| **Fuite en avant / intensif** | `intensif_max`, `marge_pure`, `export_roi`, `plafonds_leves` |
| **Agroécologie** | `agroeco_smart`, `cap_intensif`, `rotations_plus`, `mae_compost_boost` |
| **Bio** | `bio_incitatif`, `bio_contraint`, `bio_fort` |
| **Mise en commun** | `mise_en_commun`, `commun_bio` |
| **Chocs économiques** | `choc_prix_banane`, `choc_subv_canne`, `choc_prix_maraichage`, `choc_petrole` (cost_multipliers) |
| **Chocs climatiques** | `cyclone` (rdt banane/canne −40 %), `secheresse` (rdt −30 % + `forbid_crops` irriguées), `maladie_cercosporiose` (rdt banane −50 %) |
| **Mixes politiques** | `transition_sous_cyclone`, `fuite_en_avant_secheresse`, `bio_commun_choc`, `resilience_agroeco` |

Les scénarios « contraints » (`cap_intensif`, `bio_contraint`, `bio_fort`) reposent sur
`crop_share_bound` (lot 1.4) ; `choc_petrole` sur `cost_multipliers` (lot 1.2) ; les chocs
climatiques sur `yield_multipliers` (1.1) + `forbid_crops` (1.3) ; `mise_en_commun` désactive
`an_agro_max_expl` / `ig_agro_max_expl` / (si lot 3 abouti) `farm_labor_max`.

### 5.2 Nettoyage
- `tub_prod_obj` (désactivé, seuil 0, no-op) : commenter explicitement comme placeholder ou retirer.
- Documenter le doublon volontaire `scenarios.yaml _crop_groups` ⇄ `config.yaml crop_families`
  (ancres YAML non partagées entre fichiers — pas « corrigeable », à annoter).
- Passe de cohérence des commentaires/labels.

### 5.3 Inventaire GAMS (doc écrit)
Fichier `docs/gams_port_inventory.md` : tableau exhaustif équation GAMS → statut (porté /
non-porté / implicite / différé) → localisation Python. Sert de référence de parité vivante.

### 5.4 `VIGILANCE.md`
Mettre à jour : résoudre le point « REGION vs REGION_CODE » (si tranché au lot 2), déplacer les
items traités en « Résolu », consigner les différés (CF économie, MO_Expl_init si absent).

---

## Séquencement et non-goals

**Ordre** : Lot 1 (débloque les scénarios) → Lot 2 (parité ITK, gate REGION) → Lot 5 partiel
(scénarios exprimables) → Lot 3 (MO_MAX, gate données) → Lot 4 (CF, gate données) → Lot 5 final
(inventaire + VIGILANCE). Chaque lot = commit(s) autonome(s).

**Non-goals** :
- **Aucun solve lancé** cette session (ni `main.py`, ni `run_scenarios.py`). Livraison = fichiers +
  tests unitaires data-free + docs. La validation end-to-end reste à la main de l'utilisateur.
- Pas de refonte du reporting/dashboard pour les nouveaux leviers (ils transitent déjà par les
  indicateurs existants ; à vérifier au fil de l'eau, pas un objectif).
- Pas de redimensionnement des quotas territoriaux pour les chocs (choix assumé, cf. VIGILANCE).

**Dépendances externes à confirmer (gates)** : encodage `REGION`/`ILE` (lot 2), tables
`MO_*_init` (lot 3), tables/plancher CF (lot 4). Chaque gate non satisfait ⇒ le lot est codé+testé
data-free mais laissé désactivé + documenté, sans bloquer les autres.
