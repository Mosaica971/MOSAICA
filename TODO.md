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

**Situation de référence — livrée le 2026-07-27.** `scripts/build_reference_state.py` écrit
`outputs/reference_2017/` (état initial observé : assolement brut/résolu, déclinaisons
région/île/commune, typologie et AVERS, indicateurs encadrés, plancher de PAD par groupe) et
`scripts/compare_to_reference.py` met un run en face (`comparaison_reference.md` dans le run).
Aucun solve, déterministe. Le `REFERENCE.md` produit documente ce que la référence **ne peut
pas** dire — c'est la partie qui compte. Reste ouvert : la référence n'a **aucune assise
externe** (pas de recoupement Agreste/DAAF des surfaces 2017), donc elle vaut ce que vaut le
jeu parcellaire local ; si un jour une statistique publique est disponible, la comparer aux
23 578 ha cultivés de `reference_land_use.csv` trancherait la question du périmètre (l'article
travaille sur 5 336 fermes, nous 4 638).

**`Eq_BC_QUOTA_MAX` (plafond plantain) — instruit, mesuré et ACTIVÉ à 6 440 t le 2026-07-27.**
Spec : `docs/superpowers/specs/2026-07-27-modalites-solveur-plantain-design.md`. Le plantain
était **la** cause dominante de l'écart de calibration (+20,9 M€ sur un écart total de 12,8 M€ ;
la substitution banane→plantain de 1 298 ha explique à elle seule l'effondrement du Sud-Est
Basse-Terre, notre unique sous-région hors norme). L'équation existe dans le GAMS mais est
commentée des deux blocs modèles ; **l'article la décrit pourtant explicitement (Éq. 6)**.
Effet : PAD **48,4 → 31,7 %**, types **64,0 → 67,0 %**, surface **64,3 → 69,0 %**, et la banane
export remonte de 978 à 2 213 ha contre 1 921 observés — sans qu'aucune contrainte ne la
nomme. Coût 3,7 % d'objectif. Le balayage du seuil (4 650 → 40 000 t) montre un **palier plat**
dont l'optimum est **loin** de l'observé : la contrainte corrige un mécanisme, elle ne recopie
pas une réponse. Première déviation assumée au bloc `CALIB` ; `enable: false` y ramène.
→ Reste à faire : `outputs/reference_2017/` n'a pas besoin d'être reconstruit (il ne dépend pas
des contraintes), mais les runs **antérieurs** au 2026-07-27 ne sont plus comparables au nouveau
défaut — le préciser si on les ressort. Et le seuil est un chiffre de **2010** : si une
statistique de consommation de plantain plus récente apparaît, la substituer.

**Plancher de prairie — donnée trouvée et plancher ACTIVÉ le 2026-07-28.** Spec :
`docs/superpowers/specs/2026-07-28-plancher-prairie-design.md`. La Statistique agricole annuelle
2017 (Agreste, *Mémento Guadeloupe* éd. 2019) fournit l'assise exogène qui manquait :
9 595 ha de surfaces toujours en herbe et 40 449 têtes de bovins (≈ 29 771 UGB), soit
3,10 UGB/ha — exactement le chargement des recensements 2010 et 2020 (3,13 et 2,45). Le modèle
sans plancher impliquait **9,99 UGB/ha**, agronomiquement impossible : le défaut est prouvé hors
modèle. `pn_prod_min` activé à **6 096 ha** (paramètre GAMS, 27 % sous les 8 341 ha exogènes).
Effet : types **67,0 → 86,9 %**, parcelles **59,8 → 67,6 %**, surface **69,0 → 77,1 %**, canne
revenue à 12 782 ha contre 12 813 observés. Ne pas citer le PAD territorial (6,6 %) : le
plancher épingle la prairie.
→ **Deux points ouverts.** (a) Ce sont désormais **le périmètre parcellaire**, et non le modèle,
qui borne la prairie : les ~3 500 ha d'herbe non déclarée sont des parcelles absentes de
l'univers, pas des parcelles mal étiquetées (notre canne est à 98 % d'Agreste). Les récupérer
demanderait d'élargir le jeu parcellaire. (b) Le PAD résiduel est porté par les **petites
cultures** — ananas (461 ha contre 133), vergers (8 contre 311), melon (~0 contre 189), jachère
(418 contre 621) : aucune n'a de plafond ou plancher sourcé à ce jour, et c'est le prochain
gisement.
→ **Assise externe de la référence : point clos.** Notre jeu couvre 87 % de la SAU 2017 et
restitue la canne à 98 %, les fruits à 90 %.

**PAD résiduel — diagnostiqué le 2026-07-29, deux leviers instruits.** Détail complet dans
`VIGILANCE.md`, entrée « Le PAD résiduel ». Le résultat de fond est que **les rendements du
modèle valent 2 à 4 fois ceux du territoire** (ananas 34 contre 12,3 t/ha, plantain 26 contre
9,0, maraîchage 43,9 contre 10,8, agrumes 20 contre 5,2 ; seul le melon tombe juste) : la marge
de ces cultures est surestimée en amont, ce qui explique qu'il faille des plafonds de marché.
Rendements = `Rdt_Cult` = Table 1 de l'article, donc **intouchables sous mandat de parité**.
→ **Les deux leviers sont BLOQUÉS PAR LE SOLVEUR, pas par la modélisation — et c'est prouvé.**
Plafond ananas à 7 000 t et plancher arboricole à 200 ha : les deux tapent la limite d'1 h avec
un incumbent incohérent (canne et banane reculent, ce qu'aucune de ces contraintes ne peut
causer). Une solution **faisable** construite à la main en quelques secondes depuis `output_3`
(script de réparation, cf. `VIGILANCE.md`) vaut **80,91 M€** contre les 76,46 de HiGHS : l'écart
est de 4,45 M€, soit 5,5 %. Le coût réel du plancher arboricole est de **0,39 % à 200 ha et
1,19 % à 335 ha**, du même ordre que les deux contraintes déjà adoptées. **Rien n'a été adopté :
aucun run portant ces contraintes n'est exploitable en l'état.**
→ **Warm start — LIVRÉ le 2026-07-29.** `core/model/warm_start.py` (écriture de l'allocation
dans `model.Y` + **audit de faisabilité avant solve**), `core/reporting/run_folder.read_allocation`,
`solver.warm_start_from` en config, `scripts/repair_allocation.py` pour réparer une allocation
face à un nouveau plancher de surface. 7 tests sans données (`tests/test_warm_start.py`).
Mesuré : **720 s à froid → 209 s à chaud**, objectif identique, sur la configuration d'`output_3`
réamorcée par sa propre solution. Le point non évident : HiGHS **jette un départ infaisable en
silence**, donc l'audit n'est pas un confort — sans lui un run paraît réamorcé et se comporte
comme à froid. Vérifié en vrai : la réparation par défaut cassait `Eq_BA_JA` sur 318
exploitations, l'audit l'a attrapée.
→ **Données pour le levier B, déjà réunies** : Agreste 2017 atteste 385 ha de fruitiers (283
agrumes + 102 autres) contre 18 ha simulés ; à notre couverture de 87 %, **335 ha**. **Nuance à
documenter si on l'adopte** : `Eq_PLU_PROD_MIN` existe côté GAMS **en tonnes**, pas en surface —
la forme surface existe dans l'idiome GAMS (`Eq_PN_PROD_MIN`) mais ce serait une déviation de
forme, pas seulement de seuil, donc un cran de plus que les deux précédentes.
→ **Écartés, avec la raison** : igname (259 ha simulés contre 227 attestés, le plafond de
l'auteur mordrait à peine) ; melon (sous-planté, et échec reconnu de l'article lui-même, cause
hors modèle) ; jachère (aucune source externe).

**Déficit de prairie — diagnostic du 2026-07-27, conservé pour l'historique.** Il portait sur
l'état sans plancher (6 109 → 2 980 ha) ; le plancher ci-dessus l'a refermé. Détail dans
`VIGILANCE.md`, entrée dédiée. Résumé : 62 % du déficit était de l'économie légitime, 36 %
l'effet de couplage du plafond de main d'œuvre (revenir à la prairie coûte +113 h/ha), 2 % de
résidu ; et 30 % du total (Marie-Galante, 1 042 ha) tenait sur un écart de **0,94 %** entre
`CS_MG_NISM` (1 617 €/ha) et `PN_PIQ` (1 602) — fragile, pas faux.
→ **Ne pas** re-tuner l'AVERS ni « corriger » les 126 h/ha de `PN_PIQ` : la main d'œuvre de la
prairie diverge bien de la Table 1 de l'article (126 contre 70, seule ligne dans ce cas), mais
elle est recalculée exactement depuis `Data_OTK` par la formule GAMS — ce n'est pas un bug, et
même à 70 h/ha la prairie resterait à 22,9 €/h contre 99-156 pour la canne.

**Pistes fermées le 2026-07-27, ne pas rouvrir sans élément neuf.**
- *Le solveur.* Trois graines HiGHS donnent 48,44 / 48,29 / 48,31 de PAD (0,025 % d'écart
  d'objectif) : l'arbitraire de branchement vaut 0,15 point. Et le plan observé, valorisé au
  mieux sous notre propre objectif, est **15 % sous l'optimum** — quinze fois le gap MIP. Le
  diagnostic « frontière plate prairie/canne » du matin reste juste mais pèse 3 % du problème.
- *Retirer des contraintes absentes du `CALIB`.* Il n'y en a que deux (`SURF_PARC_MAX`, et
  l'exemption d'irrigation manquante sur `PLUVIO_MIN`) et elles sont **inertes** : +0 paire
  éligible. Le portage est propre de ce côté.
- *Reproduire l'année de base de l'article.* Elle est **2010** ; `Data_RPG_Gwad` commence en
  2012. Hors d'atteinte. (Au passage : leurs 5 336 fermes contre nos 4 638 sur le même nombre de
  parcelles et d'hectares, c'est de la concentration foncière, pas un échantillonnage différent.)

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
  → **Chiffré le 2026-07-27** : la représentante n'est éligible que sur **31 %** des hectares
  de canne observés, 61 % du maraîchage, 63 % du plantain (table complète dans
  `outputs/reference_2017/csv/reference_representative_eligibility.csv`, analyse dans
  `VIGILANCE.md`). Ce n'est plus une amélioration cosmétique : la représentante inéligible
  fausse l'économie de la référence **et** le plafond de main d'œuvre, donc l'optimum. Le
  correctif naturel est de choisir la représentante **par parcelle** parmi les variantes
  éligibles (la borne « bas/haut » de `build_reference_state.py` fait déjà ce calcul).
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
