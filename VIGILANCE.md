# Fichier de vigilance

Suivi, d'une session Claude Code à l'autre, des points d'attention sur le code
MOSAICA : zones peu claires, trous de données, prochains fix à gérer. Ce
fichier est mis à jour à chaque session de travail — les entrées traitées sont
déplacées dans "Résolu" plutôt que supprimées, pour garder une trace.

Sévérités : **Critique** (bloque une fonctionnalité demandée ou fausse un
résultat) / **Majeur** (limite fonctionnelle réelle, contournement possible) /
**Mineur** (amélioration, pas bloquant).

## Points ouverts

### Majeur — Pas de données géographiques
Aucun shapefile/GeoJSON/GPKG dans le repo, et `Data_Parc_Gwad_2017.txt` ne
contient ni latitude/longitude ni identifiant de géométrie. Une vraie "carte
des cultures par parcelle" n'est donc pas réalisable en l'état ; la brique de
reporting (A) s'appuie à la place sur une répartition par `ILE`/`REGION`/
`COMMUNE` (colonnes déjà présentes dans `Data_Parc_Gwad_2017.txt`).
**Prochain fix possible** : obtenir une géométrie des parcelles (cadastre
guadeloupéen, RPG, ou autre source), jointe sur `ident`, pour activer une
vraie carte dans le dashboard (brique B).
_Constaté le 2026-07-09._

### Mineur — ETP en entrée limité à la résolution RPG (sortie OK)
_L'indicateur ETP lui-même est fait (voir "Résolu — Indicateur ETP…")._ Le seul reliquat :
l'ETP **en entrée** (baseline 2017) n'est pas calculable finement, car la baseline n'est
connue qu'à la résolution des 12 groupes RPG (comme les autres indicateurs par culture),
alors que le taux de travail `MO_Ha_Cult` est par culture fine. L'ETP **en sortie** est
précis. Même cause racine que le point "Comparaison entrée/sortie limitée à la résolution
du groupe RPG" ci-dessus.
**Prochain fix possible** : porter l'allocation fine initiale (`Matrice_Parc_Cult` du
GAMS) pour débloquer tous les indicateurs par culture en entrée d'un coup, dont l'ETP.
_Constaté le 2026-07-10._

### Majeur — Comparaison entrée/sortie limitée à la résolution du groupe RPG
`cult_2017` (l'allocation observée, utilisée comme baseline "entrée") n'encode
les cultures qu'à la résolution de 12 groupes RPG
(`case_studies/guadeloupe/farm_typology._RPG_CODE_TO_BASE_GROUP`), alors que
le solveur alloue parmi ~84 cultures fines (`CULT_2017.set`), chacune avec
son propre rendement/subvention/marge à l'hectare. Il n'existe aucune table
officielle fine→groupe dans le repo Python. Le modèle GAMS d'origine, lui,
définissait une taxonomie `SC_*` bien plus riche (~40 familles,
`old_code_gms_format_now_txt/SETS.txt` lignes 113-607) qui aurait permis ce
rapprochement — mais elle n'est que partiellement portée dans
`config.yaml` (`crop_families`: 8 familles sur ~40, seulement celles utiles
aux contraintes actuellement actives). Construire un mapping fine→groupe par
préfixe de nom serait une supposition non validée (des cultures comme
`CF_*`/`TH` n'apparaissent dans aucun des deux schémas existants).
**Conséquence pour la brique A** : les indicateurs de production/subvention/
revenu par culture ne sont calculés qu'en sortie (résolution fine, précise) ;
côté entrée, seuls les indicateurs de surface/nombre de parcelles/diversité
sont calculés (résolution 12 groupes RPG, précise) ; les écarts entrée/sortie
se limitent aux agrégats indépendants de la résolution (surface totale
cultivée, nb parcelles actives, nb exploitations).
**Prochain fix possible** : porter la taxonomie `SC_*` de `SETS.txt` dans
`config.yaml` (comme déjà fait pour les 8 familles existantes) pour permettre
une comparaison entrée/sortie par famille de culture.
_Constaté le 2026-07-09._

### Mineur — `YEAR`/`SCENARIO` codés en dur
`case_studies/guadeloupe/data_pipeline.py` fixe `YEAR = "2017"` et
`SCENARIO = "RESTIT"` en constantes de module plutôt qu'en config. Ça
complique la comparaison multi-années/multi-scénarios et l'exclusion de zones
par scénario (brique C, à venir).
**Prochain fix possible** : exposer `year`/`scenario` dans `config.yaml`.
_Constaté le 2026-07-09._

### Mineur — `REGION` vs `REGION_CODE` potentiellement redondants
`Data_Parc_Gwad_2017.txt` a une colonne `REGION`, et `data_pipeline.py`
calcule en plus `REGION_CODE` via la jointure avec `REG_PARC_2017.set`. Pas
vérifié si ce sont deux référentiels différents (l'un GAMS legacy, l'autre
recalculé) ou une vraie redondance.
**Prochain fix possible** : vérifier l'équivalence, documenter ou fusionner.
_Constaté le 2026-07-09._

## Roadmap (sous-projets identifiés, non encore cadrés)

Cadrés dans l'ordre choisi avec l'utilisateur le 2026-07-09 :
- [x] **A. Sauvegarde des résultats** (`outputs/output_N/` + récap + PNG) —
  mergée dans `gams-parity-phase2` le 2026-07-10 (commit `9ee9b24`). Task 12
  (vérif manuelle end-to-end via `main.py` complet) reste différée à la
  demande de fin de journée.
- [x] **B. Dashboard de visualisation** — app Streamlit en lecture seule sur
  `outputs/output_N/`, voir `case_studies/guadeloupe/dashboard/`
  (`loaders.py` + `app.py`) et `docs/superpowers/specs/
  2026-07-10-dashboard-design.md`. `generate_report` persiste maintenant
  aussi subvention/tonne, subvention/€ vendu, revenu par exploitation + Gini,
  diversité de Shannon, surface par île. Revenu/ETP et carte géographique
  réelle restent des placeholders "non disponible" (voir points ouverts
  ci-dessous) ; côté entrée, seuls les indicateurs de surface sont affichés
  (résolution RPG, cf. point ouvert "Comparaison entrée/sortie limitée...").
- [x] **C. Exclusion de zones** (parcelles/exploitations/régions/îles) avant optimisation, pour tests à petite échelle et scénarios de transition locale — voir `zone_filter` dans `config.yaml` (`core/data/zone_filter.py`).
- [x] **D. Performance du solver** — profilé (voir `scripts/profile_solver.py`
  et `core/model/timing.py`) sur un sous-ensemble réduit (île 1, 8376
  parcelles, quotas territoriaux désactivés). Aucun réglage `solver.args`
  (threads/parallel/presolve) ne change la durée de façon mesurable — voir le
  nouveau point ouvert "Le vrai goulot d'étranglement..." ci-dessous.
- [x] **E. Remise à niveau du code** (suppression du mort, commentaires concis) — a priori continu, au fil des autres briques.

### Mineur — `zone_filter` ne redimensionne pas les quotas territoriaux
`territory_production_bound` (quotas min/max sur toute la Guadeloupe, dans
`config.yaml`) n'est pas recalculé quand `zone_filter` restreint les parcelles : un
sous-ensemble (ex: une seule île) peut devenir infaisable vis-à-vis de seuils pensés
pour tout le territoire. C'est un choix assumé (voir la section "Non-goals" de
`docs/superpowers/specs/2026-07-10-zone-exclusion-filter-design.md`), pas un bug.
**Prochain fix possible** : si ça devient gênant en pratique, désactiver
manuellement (`enable: false`) les `territory_production_bound` concernées dans
`config.yaml` pour les runs à petite échelle.
_Constaté le 2026-07-10._

### Majeur — Le run complet reste lent (~30–55 min) ; seul levier restant = la recherche MILP
Le run `main.py` complet (1 683 058 variables) prend de l'ordre de 30 à 55 min, avec une
**variance run-à-run énorme** (historique pour cette taille : 1622s, 2600s, 3132s, 3310s,
3442s — ×2,1 pour un problème identique). Le profilage (brique D, `scripts/profile_solver.py`)
avait fait croire que le goulot était l'enveloppe `SolverFactory('appsi_highs')` (LegacySolver)
convertissant le modèle Pyomo vers HiGHS (~15s sur l'île 1). Mais ce n'est vrai que sur un
sous-ensemble résolu **entièrement au presolve (0 nœud B&B)**. Sur le vrai problème le goulot
est la **recherche branch-and-bound elle-même** (des milliers de secondes) ; les ~15s
d'enveloppe sont négligeables. Confirmé par le run complet du 2026-07-10 : l'interface APPSI
persistante (qui supprime ces 15s) n'a donné **aucun gain mesurable** (3310s, en plein dans la
fourchette de l'ancien solveur) — elle a donc été **revertée** (voir "Résolu" ci-dessous).
**Prochain fix possible (si la perf redevient prioritaire)** : agir sur la *recherche*, pas
l'enveloppe — tolérance de gap MIP (`mip_rel_gap`/`mip_abs_gap` via `solver.args`, accepter
une solution à ε% de l'optimum pour couper le B&B tôt), warm start depuis l'allocation
observée `cult_2017`, ou réduction du nombre de variables binaires (pré-filtrage d'éligibilité
plus agressif). Chacun demande de vérifier l'impact sur le *résultat* (contrairement à un simple
changement d'enveloppe, neutre sur l'optimum), donc à cadrer comme un vrai sous-projet.
_Constaté le 2026-07-10._

## Résolu

### Majeur — Interface APPSI persistante : testée puis revertée (aucun gain à pleine échelle)
_Investigué et **rollback** le 2026-07-10._ On a migré `solve_model` de
`SolverFactory('appsi_highs')` vers l'interface APPSI persistante
(`pyomo.contrib.appsi.solvers.highs.Highs`) — commit `3c8e450` — en pariant sur le gain ~25%
mesuré sur l'île 1. Le run complet a montré que ce gain **ne tient pas** à pleine échelle (le
goulot est la recherche B&B, pas l'enveloppe — voir le point ouvert ci-dessus). Le **solveur**
est donc revenu à `SolverFactory('appsi_highs')` (commit `de00f98`) ; `CLAUDE.md` (issu du
`/init`) est conservé. Le spec `2026-07-10-solver-appsi-persistent-interface-design.md` garde
l'analyse au cas où l'on retenterait APPSI, marqué **reverté** en tête.

### Majeur — Barre de progression : synchrone obligatoire (conflit `capture_output`/thread)
_Résolu le 2026-07-10._ La barre `tqdm` animée lançait le solve dans un **thread de fond**.
Or `SolverFactory('appsi_highs')` route vers le **même** `pyomo...highs.Highs.set_instance`
que l'interface persistante, qui charge le modèle dans `capture_output(capture_fd=True)`
(redirection des fd stdout/stderr du process + verrou global). Toute I/O de progression
concurrente corrompt cet état → `semaphore released too many times`, stdout cassé — **à
chaque vrai run** (terminal, fichier ou pipe ; seul pytest y échappe car ses flux n'ont pas
de vrai `fileno`). Ce n'est donc PAS spécifique à APPSI : la barre animée n'a jamais été
viable dans cet environnement (Pyomo 6.10.1). `run_with_progress` est désormais **synchrone**
(solve sur le thread principal, ETA statique avant + durée après ; `tqdm` retiré). C'est la
seule option qui tourne sur de vrais fd. Vérifié end-to-end sur sous-ensemble `zone_filter`
(exit 0, stdout propre). Voir `docs/superpowers/specs/
2026-07-10-solver-progress-capture-fd-conflict.md`.

### Majeur — Indicateur ETP (emploi) calculé depuis les itinéraires techniques
_Résolu le 2026-07-10 — corrige le faux "point ouvert" « Données de main d'œuvre non
portées »._ Le temps de travail n'était pas une donnée manquante : `Data_OTK.txt` porte la
colonne `MO_EXPL` (heures par opération), et le GAMS calcule `MO_Ha_Cult` exactement comme le
coût variable mais pondéré par `MO_EXPL` au lieu de `PRIX_UNIT` (`ENTREES.txt:463-469`).
`economics.compute_labor_hours_per_ha_cult` reproduit cette formule (annualisée
`/Duree_Cycle*12`, amortissement `/Duree_Plant`), câblée dans `data_pipeline`. Les indicateurs
`indicators.compute_labor_hours_by_plot`/`compute_etp_by_key`/`compute_total_etp` donnent
l'ETP par parcelle/exploitation/région/île/total, avec conversion heures→ETP configurable
(`config.yaml` `labor.hours_per_etp`, défaut 1607 h/an = base légale). Persisté par
`report.py` (CSV + `etp_by_region.png` + `total_etp` dans le recap) et affiché au dashboard.
**Sortie uniquement** (l'entrée reste limitée à la résolution RPG, voir point ouvert). Validé
sur vraies données : 0 NaN, taux plausibles (canne mécanisée ~7-13 h/ha, banane ~1000-1560).

### Mineur — Figures : noms de cultures explicites + style
_Résolu le 2026-07-10._ Les figures affichaient les codes de variables (AN, CS_BT_NISM…).
`case_studies/guadeloupe/crop_labels.py` (porté de `DESCRIPTION_SETS.txt`) mappe chaque code
→ nom FR ; `plots.py` les utilise, avec un style matplotlib soigné (séparateurs de milliers,
rotation, grille, légende hors cadre) — sans dépendance seaborn (choix utilisateur). Les 24
sous-types maraîchage `MA_*` sont décodés partiellement (mulch + irrigation ; le token
fertilisation BIO/VEG/FER/NON reste littéral, non documenté dans le GAMS).
