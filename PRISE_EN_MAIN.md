# Prise en main — MOSAICA

Toutes les commandes du dépôt. Tout part de la **racine**, avec le venv `.venv/`
(PowerShell : `.venv\Scripts\python`). Données (`data/`), sorties (`outputs/`) et
historique de solve ne sont pas versionnés.

## Installer sur un nouveau PC

```powershell
git clone <url-du-repo>                             # data/ outputs/ non inclus, copie-les à part
python -m venv .venv                                # NE PAS copier le .venv d'un autre PC
.venv\Scripts\python -m pip install -e ".[dev]"     # dépendances + pytest (HiGHS via highspy)
.venv\Scripts\python -m pytest tests\test_readers.py  # vérifier l'install
```

## Commandes

| Commande | Quoi |
|---|---|
| `python main.py` | Résolution complète → `outputs/output_N/`. Aucun argument (tout est dans `config.yaml`). **Lent** (~30–55 min plein territoire, goulot = recherche B&B). |
| `python scripts/run_scenarios.py` | Batch de scénarios (`case_studies/guadeloupe/scenarios.yaml`) : overrides sur le config de référence, un `output_N/` par run + `batch_summary_*.csv/.md`. `--scenarios <fichier>`, `--stop-on-error`. Lance de vrais solves. |
| `python -m pytest tests\<fichier>.py` | Tester un fichier — à privilégier en itération (la plupart des tests sont sans données, donc rapides). |
| `python -m pytest` | Suite complète — **LENTE (~29 min)**, quelques tests construisent le vrai dataset et résolvent. Vérification finale seulement. |
| `python scripts/display_datasets.py` | Inspecter le dataset produit par le `config.yaml` courant (sets/paramètres/scalaires). Aucun argument. |
| `python scripts/profile_solver.py --island 1` | Chronométrer données / construction / solve sur une sous-zone. Options cumulables : `--island`, `--region`, `--farm`, `--plot`. Dès qu'un filtre est donné, les quotas territoriaux sont désactivés automatiquement. |
| `python scripts/evaluate_calibration.py outputs\output_12` | Noter un run contre l'assolement **réellement observé** en 2017 : PAD par culture, par sous-région, par exploitation, matrice de confusion des types, taux de correspondance parcellaire. ~7 s, **aucun solve**. `--all` pour tous les runs. Les nouveaux runs le font déjà tout seuls. |
| `python scripts/build_reference_state.py` | (Re)construire la **situation de référence 2017** dans `outputs/reference_2017/` : assolement observé, typologie, indicateurs encadrés, plancher de PAD. ~5 s, aucun solve, déterministe. À relancer si `config.yaml` change (année, `zone_filter`, cultures représentantes). |
| `python scripts/compare_to_reference.py outputs\output_1` | Mettre un run **face à la référence** : verdicts, assolement observé/simulé par groupe, indicateurs comparés à la fourchette d'incertitude de l'observé, types d'exploitation. Écrit `comparaison_reference.md` dans le run. ~1 s, lit les CSV déjà produits. |
| `python scripts/pad_all_scales.py outputs\output_1` | Le PAD aux **cinq échelles** (territoire, île, région, exploitation, parcelle). ~7 s, reconstruit le dataset. |
| `python scripts\repair_allocation.py outputs\output_3 --crops AG,VE_BTGT,VE_PLUIE --min-surface 335 --out outputs\_warmstart_plu` | Réparer l'allocation d'un run pour qu'elle satisfasse un nouveau **plancher de surface**, et en faire un point de départ (*warm start*). Audite le résultat et refuse de le présenter comme faisable s'il ne l'est pas. `--freeze` protège les cultures qu'une autre contrainte fixe. |
| `streamlit run case_studies\guadeloupe\dashboard\app.py` | Dashboard **lecture seule** sur les runs passés (ne résout ni n'écrit rien). |

## Accélérer un solve : le *warm start*

Au-delà de ~309 000 variables binaires, HiGHS ne trouve plus de bonne solution initiale tout
seul : il explore à l'aveugle faute d'*incumbent* à comparer. Lui en fournir un change
**uniquement la vitesse à laquelle l'optimum est prouvé**, jamais l'optimum lui-même — le
solveur garantit toujours le même écart de 1 % à la même borne.

Mesuré sur la configuration d'`output_3` réamorcée par sa propre solution : **720 s à froid,
209 s à chaud**, objectif identique.

1. Renseigner `solver.warm_start_from: outputs/output_3` dans `config.yaml`.
2. `main.py` charge, applique et **audite** le départ. S'il viole une contrainte, il le dit et
   repart à froid — parce que HiGHS ignore un départ infaisable *en silence*, et qu'un run
   paraîtrait alors réamorcé tout en se comportant comme à froid.
3. Pour amorcer un run qui **ajoute** une contrainte, réparer d'abord l'ancienne allocation
   avec `scripts/repair_allocation.py` (voir le tableau ci-dessus).

## Calibration : le modèle colle-t-il à la réalité ?

Trois outils, dans cet ordre :

1. **`scripts/build_reference_state.py`** construit la situation de référence — l'état
   initial observé, indépendant de tout run. Lire son `outputs/reference_2017/REFERENCE.md`
   **avant** d'interpréter un écart : il dit ce que la référence peut et ne peut pas dire.
2. **`scripts/compare_to_reference.py`** met un run en face.
3. **`scripts/evaluate_calibration.py`** et la page « Calibration » du dashboard donnent le
   détail par culture, sous-région et exploitation.

La méthode et les seuils viennent de l'article de référence (Chopin et al. 2015, §2.6) :
**PAD < 15 %** à l'échelle du territoire, **< 20 %** par sous-région et par exploitation,
**80 %** des exploitations dans leur type d'origine.

> **Attention à la comparaison** (vérifié le 2026-07-27, cf. `VIGILANCE.md`). L'article publie
> son PAD **par culture**, jamais agrégé : le seuil de 15 % qualifie « 8 usages sur 10 ». Notre
> « PAD territorial » est une ligne TOTAL maison, plus sévère ; l'équivalent direct est la ligne
> *Cultures sous seuil*. De même, sa Table 5 compte les parcelles **non cultivées** dans le
> dénominateur (accords gratuits, `Eq_NOCULT_NC` les verrouille) alors que nous les excluons : à
> sa convention, `output_1` afficherait 60,5 % / 67,8 % au lieu de 56,0 % / 64,3 %. Et il ne
> publie **aucune** table de PAD par exploitation — le seuil « 20 % … and farms » n'y est jamais
> instancié. Enfin son année de base est **2010** (25 057 parcelles, 5 336 exploitations), la
> nôtre 2017 (24 734 parcelles, 4 638 exploitations) : même foncier, sept ans de concentration.

**État au 2026-07-28** (`output_3`), après activation du plafond plantain et du plancher de
prairie — deux contraintes fondées sur des sources extérieures au modèle :

| Métrique | 2026-07-26 | `output_2` | **`output_3`** | Seuil / article |
|---|---:|---:|---:|---:|
| Types d'exploitation reproduits | 64,0 % | 67,0 % | **86,9 %** | 80 % (article : 81 %) |
| Parcelles bien simulées | 56,0 % | 59,8 % | **67,6 %** | article : 66 % |
| Surface bien simulée | 64,3 % | 69,0 % | **77,1 %** | article : 77 % |
| Cultures sous seuil | 0/11 | 2/11 | **4/11** | 8/10 |
| PAD territorial | 48,4 % | 31,7 % | 6,6 % | 15 % |

Le modèle **atteint désormais la qualité de calibration publiée** sur les types, les parcelles
et la surface. Trois précautions de lecture, dans l'ordre d'importance :

- ⚠ **Ne pas citer le PAD territorial de 6,6 %.** Le plancher épingle la prairie, dont le PAD
  est nul par construction ; le total en hérite. Les chiffres solides sont les trois premières
  lignes, et surtout la **canne revenue à 12 782 ha contre 12 813 observés** (PAD 0,2 %, contre
  20 %) sans qu'aucune contrainte ne la nomme.
- **Le solveur n'y est pour rien** : trois graines HiGHS ne déplacent le PAD que de 0,15 point,
  et le plan observé de 2017 vaut 15 % de moins que l'optimum sous notre propre objectif —
  quinze fois la tolérance du solveur.
- Plusieurs indicateurs tombent **dans la fourchette d'incertitude de l'observé** lui-même
  (l'assolement 2017 n'est connu qu'au niveau agrégé), et l'éligibilité impose un plancher
  irréductible de 1,5 % de PAD.

Ce qui reste, par ordre de poids : les **petites cultures** — ananas 461 ha contre 133 observés,
vergers 8 contre 311, melon 4 contre 189, jachère 418 contre 621. Aucune n'a de plafond ou de
plancher sourcé à ce jour.

**La référence a désormais une assise externe.** Recoupée avec la Statistique agricole annuelle
2017 (Agreste), notre jeu parcellaire couvre 87 % de la SAU et restitue la canne à **98 %**
(12 813 ha contre 13 066) et les cultures fruitières à 90 %. La prairie, elle, n'est déclarée
qu'à 64 % : ~3 500 ha d'herbe manquent à l'univers parcellaire, ce qui borne désormais le modèle
par les données et non par ses équations.

Lire `VIGILANCE.md`, entrée « Calibration », avant d'interpréter un résultat.

## Dashboard — trois pages

- **Accueil (`app.py`)** — un seul run : recap, indicateurs entrée/sortie, figures par
  culture/région, revenu net & coût MO.
- **Comparaison (`pages/2_Comparaison.py`)** — plusieurs runs côte à côte. Une **série** =
  (run × côté entrée/sortie), cochable. Barres : x ∈ {culture, sous-culture, région, île} ×
  mesure ∈ {surface, production, revenu, marge, subvention, ventes, coût MO, heures, ETP},
  empilement optionnel par une 2ᵉ dimension. Canne (CS/CF) colorée par irrigation×récolte,
  les autres par sous-culture. Axe y log à échelle figée (mode groupé seulement).
  2ᵉ vue : coordonnées parallèles normalisées. Les runs sans `csv/facts_*.csv` sont ignorés.
- **Calibration (`pages/3_Calibration.py`)** — un run face à l'observé 2017 : verdicts sur
  les trois seuils, PAD par culture, heatmap PAD région × culture, matrice de confusion des
  types d'exploitation, concordance parcellaire, distribution du PAD par exploitation. Un
  run non scoré affiche la commande à lancer.

## Réglages clés de `config.yaml`

`case_studies/guadeloupe/config.yaml` pilote tout :

- **`data`** : `year` (colonne économique `2017`–`2022`/`init`/`calib` — n'agit que sur
  l'économie, la structure reste 2017) et `scenario` (`RESTIT` | `SMART`).
- **`labor`** : `hours_per_etp` (défaut 1607) et `cost_per_hour` (0 = MO non valorisée).
  Reporting uniquement — n'affectent pas l'optimum.
- **`zone_filter`** (désactivé par défaut) : `include`/`exclude` sur
  `islands`/`regions`/`farms`/`plots`. ⚠ ne redimensionne pas les quotas territoriaux.
- **`constraints`** / **`objectives`** : listes activées par `enable: true` (exactement
  **un** objectif actif). Certaines entrées sont désactivées volontairement — lire le
  commentaire avant de basculer un flag.
- **`solver`** : `name` (`appsi_highs`) et `args` (options HiGHS).

## Contenu d'un `outputs/output_N/`

`recap.json`/`recap.md` (synthèse entrée→sortie→delta), `config_used.yaml`,
`csv/` (tous les CSV, dont `facts_<côté>.csv` qui alimente le dashboard comparatif),
`plots/` (PNG).

## Où régler quoi

```
case_studies\guadeloupe\config.yaml   # pilote tout
case_studies\guadeloupe\scenarios.yaml # batch de scénarios
VIGILANCE.md                          # points ouverts / limites de données — à lire avant de commencer
TODO.md                               # idées à implémenter
```
