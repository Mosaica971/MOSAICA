# 05 — Créer un nouveau cas d'étude

## Verdict de portabilité

**Le noyau est portable ; le cas d'étude est à réécrire.** C'est le résultat attendu — un modèle
d'allocation ne peut pas deviner l'agronomie d'un territoire — mais la frontière est nette et
vérifiable.

| | État | Détail |
|---|---|---|
| `core/` | ✅ **réutilisable tel quel** | Vérifié : aucune mention de la Guadeloupe, du RPG, de `ILE`/`REGION`/`COMMUNE`/`GFA`. Il ne parle que de parcelles, cultures, exploitations, zones et taux par hectare. `farm_restricted_surface_ha` est le nom générique de « surface soumise à un régime foncier » — le GFA en est l'instance guadeloupéenne. |
| Points d'entrée | ✅ **paramétrés** | `main.py`, `run_scenarios.py`, `profile_solver.py`, `display_datasets.py` prennent `--case-study`. Le nom se résout dans `core/case_study.py`, ou depuis `$MOSAICA_CASE_STUDY`. |
| Le dashboard | ⚠ **partiellement** | Il lit des recaps génériques, mais importe `case_studies.guadeloupe.domain` pour les libellés et la géométrie. À généraliser au moment où un second cas existe, pas avant. |
| Scripts de calibration | ⚠ **par nature spécifiques** | `build_reference_state.py`, `compare_to_reference.py`, `evaluate_calibration.py`, `pad_all_scales.py` encodent la méthode de Chopin contre les 12 groupes RPG. Un autre territoire a ses propres groupes observés. |
| `case_studies/guadeloupe/` | ❌ **à réécrire** | C'est le point. |

**Ce qui reste honnêtement à faire pour un second cas d'étude** : généraliser les libellés du
dashboard, et décider si la méthode de calibration se factorise (elle est générique dans son
principe — PAD, matrice de confusion — mais pas dans son vocabulaire).

---

## Le contrat

Un cas d'étude est un paquet sous `case_studies/<nom>/` qui expose **exactement trois
fonctions** et un fichier de config :

```
case_studies/<nom>/
  config.yaml                      la config de référence
  pipeline/data_pipeline.py        build_dataset(config) -> Dataset
  model/model.py                   build_model(dataset, config) -> pyo.ConcreteModel
  reporting/report.py              generate_report(dataset, config, model, results, duration,
                                                   *, outputs_root) -> Path
```

Rien d'autre n'est appelé de l'extérieur. `core/case_study.py` résout ces trois points d'entrée
par nom, et `available()` liste ce qui est sur le disque.

⚠ **`model/model.py` est importé comme MODULE, jamais comme paquet** : `__init__.py` est vide,
donc importer le paquet n'exécute aucun décorateur et n'enregistre aucune contrainte.

---

## Étape par étape

### 1. Le squelette

```bash
mkdir -p case_studies/mon_territoire/{pipeline,model,domain,reporting}
# un __init__.py vide dans chacun
```

Vérifier tout de suite que le résolveur le voit :

```bash
python -c "from core.case_study import available; print(available())"
# -> ['guadeloupe', 'mon_territoire']   (dès que config.yaml existe)
```

### 2. `pipeline/data_pipeline.py` → un `Dataset`

C'est le seul module qui touche vos données. Il doit produire un
`Dataset(sets, parameters, scalars)` dont `parameters` contient au minimum :

| Clé | Contenu |
|---|---|
| `data_parc` | DataFrame indexé par parcelle, avec au moins `SURF_HA` |
| `margin_per_ha_cult` | Series culture → marge €/ha |
| `eligible_pairs` | liste de `(parcelle, culture)` — **c'est elle qui borne la taille du MILP** |

Puis, selon ce que vos contraintes utilisent : `farm_plots`, `farm_surface_ha`, `rdt_cult`,
`crop_variance_per_ha`, `farm_risk_aversion`, `labor_hours_per_ha_cult`,
`farm_labor_capacity_hours`, et un taux par hectare et par culture pour chaque indicateur.

**Réutilisez `core/data/`** : `readers.py` (formats `.set` / `.txt` GAMS), `eligibility.py`
(masque booléen), `zone_filter.py`. Si vos données sont dans un autre format, seul le lecteur
change.

⚠ **`eligible_pairs` est le levier de tractabilité n°1.** Ne créer une variable binaire que pour
les couples réellement possibles est ce qui rend le problème résoluble : 84 cultures × 24 734
parcelles = 2,1 M de couples théoriques, ramenés à ~309 000 par l'éligibilité.

### 3. `domain/` → la science, une culture à la fois

Des fonctions pures qui produisent des séries `culture → taux/ha`. Aucune obligation de structure :
c'est votre agronomie. La séparation qui vaut la peine d'être copiée est celle de la Guadeloupe —
un module par famille d'indicateurs (`economics`, `environment`, `water`, `soil_carbon`), testables
sans données.

⚠ **Un indicateur qui dépend de la PARCELLE et pas seulement de la culture ne passe pas par un
taux par culture.** Deux cas rencontrés : le carbone du sol (dépend du type de sol) et le
prélèvement d'eau (seules les parcelles irrigables prélèvent). Pour le second, la réponse
générique existe : `ModelInputs.plot_weights`.

### 4. `model/model.py` → assembler `ModelInputs`

Le plus court des trois. Il fait trois choses :

```python
from case_studies.mon_territoire.model import constraints as _c  # noqa: F401 (enregistre)
from core.model.builder import build_crop_allocation_model
from core.model.model_inputs import ModelInputs

def build_model(dataset, config):
    inputs = ModelInputs(
        plot_surface_ha=dataset.parameters["data_parc"]["SURF_HA"],
        crop_margin_per_ha=dataset.parameters["margin_per_ha_cult"],
        eligible_pairs=dataset.parameters["eligible_pairs"],
        # ... et tout ce que vos contraintes lisent
        crop_indicator_rates={"azote": {...}, "eau": {...}},
        plot_zones={"regions": {...}, "farms": {...}},
        plot_weights={"irrigable": {...}},
    )
    return build_crop_allocation_model(inputs, config)
```

**C'est ici que le vocabulaire local est traduit en vocabulaire générique** : votre
`surface_soumise_au_bail` devient `farm_restricted_surface_ha`, vos communes deviennent une
entrée de `plot_zones`. Gardez cette traduction ici et nulle part ailleurs — c'est elle qui tient
la frontière `core/` ↔ `case_studies/`.

L'import de `constraints` en `# noqa: F401` **n'est pas décoratif** : sans lui, aucune de vos
contraintes n'est enregistrée et toute config qui les nomme lève `KeyError`.

### 5. `config.yaml`

Structure minimale :

```yaml
data: {year: "2020", scenario: BASE}
solver: {name: appsi_highs, args: {time_limit: 3600, mip_rel_gap: 0.01}}
labor: {hours_per_etp: 1607, cost_per_hour: 0}

crop_families:
  cereales: [BLE, ORGE]

eligibility_criteria: [...]     # bornes numériques
categorical_rules: [...]        # interdits catégoriels

constraints:
  - name: at_most_one_crop_per_plot
    enable: true
    args: {}
  - name: territory_indicator_bound
    enable: true
    args: {label: plafond_azote, indicator: azote, sense: le, threshold: 1000000}

objectives:                     # EXACTEMENT un actif
  - name: maximize_gross_margin
    enable: true
    args: {}
```

**Commentez chaque entrée désactivée avec sa raison.** C'est la convention du dépôt et elle a une
valeur réelle : plusieurs `enable: false` de la Guadeloupe sont corrects et testés, mais
provoquent une infaisabilité authentique sur les données.

### 6. `reporting/report.py`

`generate_report(dataset, config, model, results, duration, *, outputs_root) -> Path`. Elle
décode la solution, calcule les indicateurs et écrit le dossier de run. Réutilisez
`core/reporting/run_folder.py` pour la création du dossier et la relecture d'allocation.

**Le contrat minimal du `recap.json`** — c'est lui que lisent le dashboard et les scripts de
batch :

```json
{
  "run_name": "...", "run_policy": null, "run_forcing": null, "run_sweep": null,
  "termination_condition": "optimal", "solve_duration_seconds": 209.4,
  "solver": {...}, "constraints": [...],
  "economics": {"output": {"total_gross_margin": 0, "total_etp": 0, ...}},
  "environment": {"output": {"total_azote": 0, ...}},
  "output": {"total_surface_ha": 0}
}
```

`constraints` est ce qui permet à `bound_indicators` de détecter rétroactivement les indicateurs
fixés par une contrainte — le piège n°1 de [04](04-vigilance.md#a1). Ne le sautez pas.

### 7. Faire tourner

```bash
python scripts/display_datasets.py --case-study mon_territoire     # les données sortent ?
python scripts/profile_solver.py --case-study mon_territoire       # ça se construit et ça résout ?
python main.py --case-study mon_territoire                         # un run complet
python scripts/run_scenarios.py --case-study mon_territoire \
       --scenarios case_studies/mon_territoire/scenarios.yaml --dry-run
```

Ou fixer le défaut une fois pour toutes :

```powershell
$env:MOSAICA_CASE_STUDY = "mon_territoire"
```

---

## Ce qu'il faut prévoir dès le départ

Cinq décisions qui coûtent cher si on les prend tard — chacune est un piège rencontré ici.

**1. Une source externe pour chaque seuil.** Un plafond ou un plancher calé **sur l'assolement
observé** produit un PAD nul par construction : il ne calibre rien, il force. Les deux déviations
retenues en Guadeloupe tiennent parce qu'elles sont sourcées ailleurs (paramètre GAMS d'origine,
statistique agricole nationale) et que le résultat ne dépend pas de la valeur exacte — un
**palier** sur le balayage du seuil le prouve. C'est le test qui distingue une correction d'un
ajustement.

**2. Des cultures réellement distinctes.** Deux cultures égales sur tous les paramètres que le
modèle lit sont interchangeables : désastre de branch-and-bound, et toute contrainte de part qui
les distingue est satisfaite **par simple renommage, à coût nul**. Lancer
`check_scenario_feasibility.py` dès le premier jeu de données — il les signale.

**3. Une variable d'état si un stock est en jeu.** Le modèle est **statique** : il peut liquider
un cheptel gratuitement et redéployer le travail d'éleveur ailleurs. Si votre territoire a des
stocks (cheptel, plantations pérennes, matériel), aucune contrainte de surface ne les représente
correctement. `baseline_inertia_min` en est un proxy grossier.

**4. La granularité de la baseline observée.** Si votre historique n'encode la culture qu'au
niveau agrégé, tout indicateur « en entrée » repose sur une **hypothèse** de variante
représentante — et cette hypothèse contamine le plafond de main d'œuvre, donc l'optimum. La
rendre configurable et documentée dès le départ.

**5. La taille du problème.** Au-delà de ~309 000 binaires, HiGHS ne trouve plus de bon incumbent
seul et un solve peut rendre un résultat **prouvablement faux** (voir
[04](04-vigilance.md#tractabilite)). Surveiller `eligible_pairs` et prévoir le warm start.

---

## Une fois que ça tourne

```bash
python scripts/golden_snapshot.py --write    # figer le comportement, puis --check après tout refactor
```

Écrire ensuite, dans l'ordre de rentabilité :

1. des **tests sans données** pour vos contraintes (config minuscule construite à la main) ;
2. un **`references.yaml`** avec vos runs de référence et la justification de chaque choix,
   gardé par `check_references.py` ;
3. votre propre section dans [04 — Vigilance](04-vigilance.md), au fur et à mesure que vous
   découvrez ce que vos données ne disent pas. C'est le document le plus utile du dépôt.
