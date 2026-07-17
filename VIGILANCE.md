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

### Majeur — L'allocation fine 2017 en entrée n'a jamais existé (indicateurs d'entrée = hypothèse)
La baseline observée `cult_2017` n'encode la culture qu'au niveau **agrégat/RPG** (12 codes :
AG, AN, BC, BA, VE, CS, PN, MA, JA, ME, NC, IG — `farm_typology._RPG_CODE_TO_BASE_GROUP`).
**Le GAMS d'origine faisait pareil** : `Matrice_Parc_Cult` (ENTREES.txt:64-102) mappe chaque
code RPG vers un code **agrégat**, jamais une variante fine. La variante technique de 2017
(quel système de canne, etc.) n'a donc **jamais été observée** — ce n'est pas un portage
manquant, la donnée n'existe nulle part. Les codes agrégats sont dans `CULT_2017.set` avec
une économie nulle (rdt/prix/travail = 0) : ils servent à représenter la baseline, et le
solveur réalloue vers les variantes fines (84 cultures) en sortie.
**Conséquence / choix (point 4, brique A)** : pour tout de même calculer production/
subvention/revenu/ETP **en entrée**, on substitue une **variante fine représentante par
famille** (`config.yaml baseline_representative_crops`), puis on réutilise les indicateurs de
sortie. Les indicateurs d'entrée et les écarts entrée/sortie reposent donc sur cette
**hypothèse** (documentée, configurable), pas sur une allocation fine réellement observée.
**Prochain fix possible / à raffiner** : (a) rendre le représentant **conscient de la
région** pour les familles région-codées (CS, CF, BC) plutôt qu'un seul représentant global ;
(b) vérifier s'il existe des valeurs « init » par agrégat dans le GAMS (`STOCK_*_init`,
RESULTATS.txt:1853) à porter comme représentatives officielles.
_Constaté le 2026-07-09, reformulé et adressé le 2026-07-13._

### Mineur — Indicateur GES : magnitude élevée (fidèle au GAMS, unités source à surveiller)
Le GES/ha porté (`environment.compute_ges_per_ha_cult`, chantier B) reproduit **à
l'identique** la formule GAMS (`OPTIMISATION.txt:118-127`), terme surfacique `GES_SURF` +
terme production `GES_Q·Rdt` sur les opérations non-amorties, le tout `/COEFF_C_CO2` (0.272).
Sur vraies données le max atteint ~1.6e5 « t CO₂/ha/an », dominé par `COND_EXP_ME`
(conditionnement-export melon, `GES_Q=2156.8` — fret aérien, réellement très carboné) et des
`GES_SURF` jusqu'à 2769. Ces valeurs viennent **des données sources** (`Data_OTK.txt`), pas
d'un bug : le GAMS produirait les mêmes. L'unité annoncée « t CO₂ » est probablement
incohérente avec l'échelle réelle des colonnes (kg ?), mais **corriger dévierait de la
parité**. Le score composite normalise en min-max → l'échelle absolue ne fausse pas le
classement. **À faire si besoin d'un GES physiquement interprétable** : clarifier l'unité de
`GES_SURF`/`GES_Q` avec la source et documenter un facteur d'échelle explicite (hors parité).
_Constaté le 2026-07-17._

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

### Majeur — Dashboard comparatif multi-scénarios (page « Comparaison »)
_Résolu le 2026-07-13._ Nouvelle page Streamlit `dashboard/pages/2_Comparaison.py` (multipage,
à côté de la vue mono-run) pour comparer plusieurs `output_N` côte à côte. Backbone : une
**table de faits tidy par run et par côté**, `csv/facts_<side>.csv` (une ligne par
`culture × région` + île, toutes mesures), produite par `indicators.compute_facts_table`. Le
dashboard pivote librement : **x ∈ {culture, sous-culture, région, île}**, **mesure y** au
choix (surface, production, revenu, marge, subvention, coût MO, heures, ETP), **empilement**
par une 2ᵉ dimension. Une « série » = **(run × côté)**, cochable — ce qui unifie « paires
entrée/sortie » et « scénario vs scénario ». Règles de couleur : la **canne (CS/CF)** est
colorée par sa combinaison irrigation×récolte (3 modalités réelles : `NISM`/`NIM`/`IM` ;
l'irrigué est toujours mécanisé), région ignorée ; les autres cultures par sous-culture.
Axe **y log à limites figées partagées** (mode groupé uniquement — une pile ne s'additionne pas
en log ; l'empilé reste linéaire), plancher positif pour le zéro. 2ᵉ vue : **coordonnées
parallèles normalisées** (Gini, revenu net, ETP, production… un axe par indicateur, une ligne
par série). Toute la logique de données est dans `dashboard/comparison.py` (pur, testé) ; la
page ne fait que câbler les widgets + matplotlib. NB : la refonte des **PNG statiques** (brique
D) est volontairement minimisée — les demandes « jolis histogrammes groupés/empilés » vivent
désormais dans le dashboard ; les PNG par culture restent simples.

### Mineur — Coût de la main d'œuvre + revenu net exposés (réglage `labor.cost_per_hour`)
_Résolu le 2026-07-13._ La MO n'est **pas** monétisée dans le coût variable GAMS (comptée en
heures seulement, cf. `economics.py`). On ajoute donc un indicateur de reporting (n'affecte
**pas** l'optimum) : `labor.cost_per_hour` (€/h) dans `config.yaml` → `coût_MO = Σ heures ×
cost_per_hour`, et un **revenu net = marge brute − coût MO**, calculés côté entrée ET sortie.
`compute_economic_totals` expose désormais aussi `total_gross_margin`, `total_variable_cost`
(dérivé = produit brut − marge), `total_labor_cost`, `total_net_revenue`. CSV/PNG
`gross_margin_by_crop_*` et `labor_cost_by_crop_*` par côté. Défaut `cost_per_hour=0` →
revenu net = marge brute (rétro-compatible). Caveat côté entrée : mêmes cultures
représentantes que les autres indicateurs économiques (point 4). Réorg au passage : **tous
les `.csv` d'un run sont désormais sous `output_N/csv/`** (les `recap.*`/`config_used.yaml`
restent à la racine, les PNG sous `plots/`) ; `dashboard/loaders.load_csv` lit `csv/` avec
repli sur la racine pour les anciens dossiers.

### Mineur — `year`/`scenario` exposés dans la config (plus de constantes codées en dur)
_Résolu le 2026-07-13 (brique #3)._ `data_pipeline.py` ne fige plus `YEAR`/`SCENARIO` en
constantes de module : une section `data: {year, scenario}` de `config.yaml` les pilote
(défauts `2017`/`RESTIT` → comportement historique reproduit à l'identique). `year`
sélectionne la colonne des tables `indice_H` (`2017`–`2022`, ou `init`/`calib`) et ne pilote
que **l'économie** — la structure du parcellaire reste figée à 2017 (seule année dont les
données structurelles existent). `scenario` (`RESTIT`|`SMART`) sélectionne
`Matrice_OTK_Cult_<scenario>` et `MAE_Compost_Cult_<scenario>`. Validation *fail-fast*
(`ValueError` listant années/scénarios disponibles) ; `var_rdt_cult` reste délibérément sur
sa colonne `init`. L'année/scénario du run est enregistrée dans le recap (JSON + markdown).
Tests dans `tests/test_guadeloupe_pipeline.py`. Spec :
`docs/superpowers/specs/2026-07-13-expose-year-scenario-config-design.md`.
**Écart connu restant** : `scenario` ne pilote PAS encore les fichiers CF scénario-spécifiques
(`Prix_Cult_CF_{RESTIT,SMART}.txt`, `Rdt_Cult_CF_{RESTIT,SMART}.txt`), qui existent en données
mais ne sont pas chargés par le pipeline. À porter si les cultures CF deviennent
scénario-dépendantes.

### Majeur — Indicateurs d'entrée (production/subvention/revenu/ETP) via cultures représentantes (point 4)
_Résolu le 2026-07-13._ Les indicateurs par culture et l'ETP sont désormais calculés **en
entrée** (baseline 2017), plus seulement en sortie. Mécanisme : `indicators.
decode_baseline_representative_allocation` remappe chaque famille agrégat de la baseline vers
une variante fine représentante (`config.yaml baseline_representative_crops` : AN→AN_NU,
BA→BA_INT, BC→BC_BT, CS→CS_NGT_NISM, IG→IG_PLA, MA→MA_ROTA, PN→PN_TOUR, VE→VE_BTGT ; AG/ME/JA
gardent leur économie propre ; NC exclu), puis on réutilise les indicateurs de sortie.
`report.py` écrit production/subvention/revenu/ETP par culture **des deux côtés** (fichiers
`*_input.csv`/`*_output.csv` + figures) et un bloc `recap["economics"]` = {input, output,
delta} (production t, subvention €, revenu €, ETP). Le dashboard affiche les deux côtés + les
écarts. **C'est une hypothèse** (le représentant par famille) — voir le point ouvert
« L'allocation fine 2017 en entrée n'a jamais existé ». Validé sur vraies données (0 NaN,
totaux finis). (NB : le helper `indicators.crop_family(code)`, ajouté « au cas où » pour
agréger par famille mais jamais utilisé, a été supprimé le 2026-07-13 lors de la passe
qualité — la famille reste le préfixe avant `_` si besoin de la recalculer.)

### Mineur — Vérification couverture des cultures (les 84 sont bien implémentées)
_Vérifié le 2026-07-13, suite à un doute sur AG/NC absents de `config.yaml`._ Les 84 cultures
de `CULT_2017.set` ont **toutes** des données économiques (Prix/Rdt/OTK) et une entrée
d'éligibilité — rien n'est silencieusement absent. `crop_families` dans le config n'est **pas**
l'univers des cultures, juste un regroupement pour contraintes. AG (agrumes), ME (melon), JA
(jachère) sont de vraies cultures mono-code (AG est même choisie sur 222 parcelles au run
complet). Les codes AN/BA/BC/CS/IG/MA/PN/VE (agrégats) + NC ont une économie nulle → jamais
choisis en sortie : c'est voulu (ils représentent la baseline, cf. point 4). NB : au run
complet le margin-max ne retient que ~9 cultures et **abandonne totalement la canne à sucre et
la banane export** (aucun min-quota ne les force) — résultat d'optimisation, pas un bug de
couverture, mais à garder en tête.


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
