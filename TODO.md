# TODO — idées à implémenter

Ce qui reste à faire. Les limites connues et non planifiées sont dans `VIGILANCE.md`.

## En cours / prêt à coder

**Calibration & validation — livré le 2026-07-21.** Spec :
`docs/superpowers/specs/2026-07-21-calibration-validation-design.md`, plan :
`docs/superpowers/plans/2026-07-21-calibration-validation.md`. PAD territorial,
sous-régional et par exploitation, matrice de confusion des 8 types, taux de correspondance
parcellaire, d'après Chopin et al. (2015) §2.6. Écrit dans chaque run et rejouable sur les
runs passés avec `scripts/evaluate_calibration.py`. Reporting seul, aucun solve.
**Leviers de calibration — livrés et mesurés le 2026-07-23.** Spec :
`docs/superpowers/specs/2026-07-21-calibration-levers-design.md`. L'enquête GAMS a établi que
le modèle résolu n'était pas celui que l'article évalue (`CALIB`, `MODELE.txt:450-565`). Portés :
objectif de **Markowitz**, 14 suppressions `Eq_*_SUPP` (−29 % de variables), prairie `PN_PIQ`,
plafond de main d'œuvre `Eq_MO_MAX_Expl`. `Eq_CS_GFA` et les planchers de production
**désactivés** (infaisables avec le plafond ; les planchers sont d'ailleurs `SCENARIO`, pas
`CALIB`). Bug de sol de l'ananas corrigé (règle inversée). Écart d'optimalité solveur porté à
1 % (`mip_rel_gap`) : l'objectif Markowitz était intraitable au gap par défaut (> 37 h → 175 s).

→ **Résultat : PAD 193 % → 51 %**, types 63 %, avec les coefficients d'aversion **publiés**
(Table 2). Canne (17-22 %) et maraîchage (18 %) bien reproduits. **Chantier clos** : voir le
bloc FINALISATION de `VIGILANCE.md` pour la décision et les trois voies instruites puis
écartées pour descendre plus bas (recalibration §2.5 → 40 % mais coefficients absurdes ;
plafonds de marché → 33 % mais forçants ; contrainte de cheptel → intraitable). L'écart
résiduel (prairie, plantain, petites cultures) recoupe les limites reconnues par l'article
lui-même.
→ **Piste ouverte, non planifiée** : si un jour on obtient le jeu de coefficients ou les
résultats du vrai run GAMS, ils trancheraient le doute sur l'aversion et permettraient une
comparaison directe. Sans eux, 51 % est la limite fidèle reproductible.

**Refactor transverse — livré le 2026-07-21.** Spec :
`docs/superpowers/specs/2026-07-21-refactor-structure-et-deduplication-design.md`.
Arborescence `guadeloupe/` par rôle (`pipeline/`, `domain/`, `model/`), fusion des helpers
dupliqués (indicateurs, bloc ITK ×3, signature du builder, chemins des scripts), et
abstraction du vocabulaire case-study hors de `core/`. Aucun changement de comportement :
validé par `scripts/golden_snapshot.py` (511 sommes de contrôle sur les vraies données,
sans solve MILP) et la suite pytest.
→ Reste à faire : **aucun solve réel complet n'a été relancé de bout en bout** (`main.py`,
`run_scenarios.py`). Le golden couvre le pipeline, les indicateurs et la construction du
modèle, pas la chaîne solve → `generate_report` → écriture d'`outputs/output_N/`. À faire
lors du prochain run de fin de journée, qui vaudra confirmation.
→ Piste non retenue, à rouvrir si utile : 5 règles catégorielles de `core/`
(`soil_type_forbidden`, `region_crop_forbidden`, `max_risk_threshold`, `exact_risk_value`,
`irrigation_required`) sont des cas particuliers d'`attribute_forbidden`. Elles ont été
conservées car leurs noms sont génériques et lisibles dans le YAML — seule
`melon_soil_restriction`, au nom spécifique à une culture, a été supprimée.

**Batch de scénarios + parité ITK géographique — livré le 2026-07-20** (lots 1, 2, 5).
Leviers `yield_multipliers`/`cost_multipliers`, règles `forbid_crops`/`attribute_forbidden`,
contrainte `crop_share_bound`, canal `enable_add`, ~24 bans ITK câblés, 25 scénarios,
`docs/gams_port_inventory.md`. **Aucun solve n'a été lancé** : la validation est unitaire
(`tests/test_scenario_overrides.py` résout les 25 scénarios sans résoudre le MILP).
→ Reste à faire : lancer `scripts/run_scenarios.py` en fin de journée pour vérifier qu'aucun
scénario n'est infaisable sur les données réelles, puis ajuster les seuils qui coincent.

**Chantier « indicateurs d'impact » — cadré le 2026-07-20, 3 specs.** Périmètre commun :
reporting seul, aucun effet sur l'allocation, donc aucun solve réel nécessaire pour valider.
1. **Eau + carbone organique du sol** — **livré le 2026-07-20**. Spec :
   `docs/superpowers/specs/2026-07-20-water-soil-carbon-indicators-design.md`.
   Validation unitaire seulement (aucun solve réel lancé).
2. **Score de stabilité / résilience** — **livré le 2026-07-20**. Spec :
   `docs/superpowers/specs/2026-07-20-resilience-stability-score-design.md`.
   Marge à risque climatique, concentration du revenu (HHI), perte sous choc de prix
   (δ configurable). Validation unitaire seulement (aucun solve réel lancé).
3. **Rpest (Tixier)** — risque de pollution de l'eau par les pesticides. Le plus lourd
   (7 sous-indicateurs, niveau parcelle) ; module GAMS dédié `R_PEST_NEW.txt`. Pas encore
   cadré. Données **complètes** (`Data_OTK` : `DT50`/`GUS`/`ADI`/`AQUATOX`/`QMA`/`KOC` ;
   `Data_Parc` : `RUI_PARC`/`DRAI_PARC`/`PENTE` ; `Data_Cult` : `COUV_SOL`/`PROF_SILLONS` ;
   `R_Tixier.txt` : 14 seuils).

## Différé (cadré, en attente d'une décision ou de données)

- **`Eq_AN_PA`** — `AN_PA` interdit si `Surf_Expl_Parc_init < AN_SURF_EXPL_MIN` : porte sur
  une taille d'**exploitation**, pas un attribut de parcelle, donc hors de portée de
  `attribute_forbidden`. Demande une règle catégorielle indexée par exploitation.

- **Bloc CF (canne fibre)** — sorti du plan ci-dessus, à replanifier séparément. Porte les
  équations `Eq_CF_*` uniquement : les 10 cultures `CF_*` sont **déjà** dans le modèle et
  valorisées via `Prix_Cult.txt`. Les fichiers `indice_H/{Prix,Rdt}_Cult_CF_{RESTIT,SMART}.txt`
  sont des variantes **territoire entier**, pas des tables CF — leur sens est à trancher avec
  la source avant câblage (cf. `VIGILANCE.md`) : c'est le vrai point bloquant du lot.
- **Contrainte `MO_MAX`** (plafond main d'œuvre) — hors plan Lot 3, à cadrer.
- **Part de bio (C2)** — bloqué : le bio n'est pas identifiable proprement dans les
  données, demande un arbitrage utilisateur.
  Spec : `docs/superpowers/specs/2026-07-17-bio-share-indicator-design-DEFERRED.md`.
- **Restauration collective / aide alimentaire / EGalim (C3)** — bloqué sur données
  externes (demande des cantines, besoins de l'aide alimentaire).
  Spec : `docs/superpowers/specs/2026-07-17-egalim-collective-catering-design-DEFERRED.md`.

## Améliorations identifiées, non cadrées

- **Performance du solve** — seul levier restant : la recherche MILP elle-même
  (`mip_rel_gap`/`mip_abs_gap`, warm start depuis `cult_2017`, pré-filtrage d'éligibilité
  plus agressif). Chacun change potentiellement le *résultat* → à cadrer comme sous-projet.
- **Cultures représentantes conscientes de la région** pour les familles région-codées
  (CS, CF, BC), au lieu d'un représentant global (`baseline_representative_crops`).
  Vérifier au passage s'il existe des valeurs `init` par agrégat côté GAMS
  (`STOCK_*_init`, `RESULTATS.txt:1853`) à porter comme représentantes officielles.
- **Classeur Excel à remplir, type bilan carbone** — export d'un fichier avec des cases
  vides à saisir par l'utilisateur (hypothèses, facteurs d'émission, postes non couverts par
  le modèle), réinjectable ensuite dans le reporting. À cadrer : périmètre exact des postes,
  sens de circulation (export seul ou aller-retour), et articulation avec l'indicateur GES
  existant (`environment.py`, fidèle au GAMS).
- **Intégration de l'élevage** — absent du modèle aujourd'hui (allocation purement végétale).
  Gros chantier : surfaces fourragères, cheptels, effluents/compost (lien avec le bloc CF),
  économie et main d'œuvre propres, place dans l'objectif et les quotas territoriaux.
  Vérifier d'abord ce que le GAMS d'origine contient sur le sujet.
- **Mapping géoréférencé des cultures, avant vs après** — carte des cultures par parcelle en
  entrée (baseline 2017) et en sortie (allocation optimisée), côte à côte. Bloqué par
  l'absence de géométrie : nécessite un jeu de parcelles (cadastre, RPG…) joint sur `ident`.
  Remplacerait les placeholders « non disponible » du dashboard.
- **Agrégats de restitution Nord Basse-Terre** — sets `EXPL_NBT`/`PARC_NBT` non portés ; côté
  GAMS ils alimentent des assolements par commune du NBT (`ASSOL_NBT*`). Reporting territorial
  plus fin, sans effet sur l'optimum.

- **Phosphore / potasse** — `Data_OTK` n'a qu'une colonne `AZOTE`, mais les engrais sont nommés
  par leur formule NPK (`08_20_20`, `11_11_33`, `DAP_18_46`, `KNO3`, `K2SO4`). P et K sont
  récupérables via une table de correspondance nom → NPK. Bricolage assumé, à cadrer.

- **Énergie / mix électrique** — **bloqué faute de données**. Aucune colonne carburant ou
  consommation dans `Data_OTK` ; demanderait des facteurs énergétiques par opération, à
  collecter. Seul indicateur d'impact de la liste initiale qui n'est pas calculable.

- **`REGION` vs `REGION_CODE`** — vérifier l'équivalence, documenter ou fusionner.
- **Unité GES** — clarifier l'échelle de `GES_SURF`/`GES_Q` avec la source et documenter un
  facteur explicite (hors parité GAMS ; sans effet sur le score composite min-max).
