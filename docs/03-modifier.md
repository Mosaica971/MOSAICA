# 03 — Modifier le modèle

## L'idée centrale : le registre piloté par config

Contraintes, objectifs, critères d'éligibilité et règles catégorielles sont des **fonctions
Python enregistrées par un nom**, puis sélectionnées et paramétrées **entièrement depuis le
YAML**. Conséquence pratique : *pour changer le comportement du modèle, on édite le plus souvent
la config, pas le code.*

```
@register_constraint("mon_truc")   →   CONSTRAINT_REGISTRY["mon_truc"]
                                            ↓
config.yaml:  - name: mon_truc          resolve_enabled() garde enable: true,
                enable: true            résout le nom, renvoie (fonction, args)
                args: {seuil: 42}            ↓
                                        builder.py appelle fonction(model, inputs, **args)
```

⚠ **Le piège n°1 : un builder non importé n'est pas enregistré.** Les décorateurs ne s'exécutent
qu'à l'import du module. `core/model/builder.py` importe les builders génériques ;
`case_studies/guadeloupe/model/model.py` importe en plus ceux du cas d'étude. Si votre module
n'est importé nulle part sur le chemin vers `build_crop_allocation_model`, la config qui le nomme
lève `KeyError: Unknown component`.

---

## Ajouter une contrainte

**D'abord : est-ce vraiment une nouvelle contrainte ?** Les builders génériques existants
couvrent beaucoup, depuis le YAML seul :

| Builder | Ce qu'il exprime |
|---|---|
| `territory_production_bound` | plafond/plancher sur une **production physique** (t, ou ha avec `use_yield: false`) |
| `territory_indicator_bound` | plafond/plancher sur **n'importe quel taux par hectare** exposé par le cas d'étude — azote, IFT, GES, eau, carbone, heures, euros de subvention |
| `zone_indicator_bound` | la même borne **par île / région / bassin / exploitation** (`threshold_per_ha` × les hectares de la zone = la forme directive nitrates) |
| `crop_share_bound` | une part d'un groupe de cultures dans un autre |
| `farm_area_share_max` | une part maximale de surface par exploitation |
| `farm_labor_hours_max` | le plafond de main d'œuvre par exploitation |
| `baseline_inertia_min` | une part de la surface qui reste dans son usage 2017 |

Un plafond d'azote, une enveloppe de dépense publique et un plancher d'emploi sont **le même
builder** avec un `indicator:` différent. Écrire du code pour ça est une erreur.

### Si c'est vraiment nouveau

```python
# core/model/constraints.py  (ou case_studies/<cas>/model/constraints.py si c'est spécifique)
@register_constraint("plafond_machin")
def build_plafond_machin(
    model: pyo.ConcreteModel,
    inputs: ModelInputs,
    *,
    label: str,        # OBLIGATOIRE : c'est par lui qu'un scénario cible cette entrée
    crops: list[str],
    threshold: float,
    **_args,           # OBLIGATOIRE : absorbe les clés que la config peut porter en plus
) -> None:
    total = sum(
        model.Y[plot, crop] * inputs.plot_surface_ha[plot]
        for plot, crop in inputs.eligible_pairs
        if crop in set(crops)
    )
    # ⚠ PIÈGE DU BOOLÉEN TRIVIAL : sum() sur zéro paire renvoie un 0 Python, pas une
    # expression Pyomo. Le comparer produit un bool nu, que Pyomo REFUSE.
    if isinstance(total, (int, float)):
        setattr(model, label, pyo.Constraint(
            expr=pyo.Constraint.Feasible if total <= threshold else pyo.Constraint.Infeasible))
        return
    setattr(model, label, pyo.Constraint(expr=total <= threshold))
```

```yaml
# config.yaml
constraints:
  - name: plafond_machin
    enable: true
    args: {label: machin_max, crops: [CS, BA], threshold: 1000}
```

**Trois règles à respecter :**

1. **`label:` toujours.** C'est la clé que `enable`/`disable`/`set_args` d'un scénario utilisent
   pour cibler *une* entrée. Sans label, ils tombent sur le `name`, qui peut être partagé par
   six entrées.
2. **`**_args` toujours.** Sinon toute clé supplémentaire dans la config fait exploser le build.
3. **Le garde du booléen trivial** dès que l'ensemble de termes peut être vide.

**Un test, sans données.** C'est le style du dépôt (`tests/test_guadeloupe_constraints.py`) :

```python
def test_plafond_machin_borne_la_surface():
    inputs = ModelInputs(
        plot_surface_ha={"P1": 10.0, "P2": 5.0},
        crop_margin_per_ha={"CS": 100.0},
        eligible_pairs=[("P1", "CS"), ("P2", "CS")],
    )
    model = build_crop_allocation_model(inputs, {
        "constraints": [{"name": "plafond_machin", "enable": True,
                         "args": {"label": "machin_max", "crops": ["CS"], "threshold": 12.0}}],
        "objectives": [{"name": "maximize_gross_margin", "enable": True, "args": {}}],
    })
    assert hasattr(model, "machin_max")
```

---

## Ajouter un objectif

Même mécanique, registre `OBJECTIVE_REGISTRY`, dans `core/model/objectives.py`.

⚠ **Exactement un objectif doit être actif** — `build_crop_allocation_model` lève sinon. Un
scénario qui change d'objectif doit donc `enable` le nouveau **et** `disable` l'ancien dans le
même bloc.

⚠ **Un run qui change d'objectif n'est pas comparable aux autres sur la colonne `objective`** :
ce n'est pas la même fonction. Comparez sur les colonnes physiques et économiques (marge brute,
ETP, azote, IFT…), qui sont calculées à l'identique quel que soit l'objectif.

---

## Ajouter une règle d'éligibilité

L'éligibilité est une matrice booléenne parcelle × culture : les **bornes numériques**
(altitude, pente, pluviométrie, taille) intersectées avec les **règles catégorielles**.

```python
# core/data/eligibility.py
@register_categorical_rule("ma_regle")
def rule_ma_regle(
    plot_attributes: pd.DataFrame, *, crops: list[str], colonne: str, **_args
) -> tuple[list[str], pd.Series]:
    """Renvoie (les cultures à interdire, la condition sur les parcelles)."""
    return crops, plot_attributes[colonne] > 42
```

Une règle reçoit la table des parcelles et renvoie `(cultures, condition)` ; `forbid_where`
efface ensuite ces cultures sur les parcelles qui matchent.

⚠ **Chaque règle interdit son propre sous-ensemble, et le masque garde l'UNION des interdits.**
Donc une entrée `attribute_forbidden` fait un **ET** de ses conditions, et un **OU** s'exprime en
**plusieurs entrées**. C'est exactement comme est écrit le ban sol/île du melon dans
`config.yaml`.

Une règle activée dans `config.yaml` se lève dans un scénario en **désactivant son label** —
c'est ainsi qu'un scénario rouvre une interdiction.

---

## Ajouter une culture

Le plus intrusif, parce que les données commandent. Dans l'ordre :

1. **`data/sets/CULT_2017.set`** — le code de la culture. Sans lui, rien n'existe.
2. **`data/tables/`** — une ligne dans chaque table indexée par culture : `Prix_Cult`,
   `Rdt_Cult`, `Data_Cult` (bornes agronomiques), `Matrice_OTK_Cult_<scénario>` (l'itinéraire
   technique, d'où sortent azote, IFT, GES, heures…), `Var_Rdt_Cult`.
3. **`domain/crop_families.py`** — sur quel groupe RPG la culture se replie. Sans ça, la
   calibration ne sait pas la comparer à l'observé et `baseline_inertia_min` l'ignore.
4. **`domain/crop_labels.py`** — le nom lisible pour les figures.
5. **`config.yaml`** — l'ajouter aux `crop_families` concernées, et aux règles catégorielles qui
   doivent la contraindre.
6. **`crop_groups.yaml`** — si elle appartient à un groupe de scénarios (`vivrier`, `bio_…`).

**Puis vérifier.** Une culture ajoutée sans itinéraire distinct est une **copie symétrique** —
le pire cas pour le branch-and-bound, et un piège de modélisation (une contrainte de part qui
distingue des cultures que la donnée ne distingue pas est satisfaite par simple renommage, à
coût nul). Le détecteur existe :

```bash
python scripts/check_scenario_feasibility.py --scenarios <fichier>   # signale les groupes symétriques
python scripts/golden_snapshot.py --check                            # dérive numérique ailleurs
```

Voir [04 — Vigilance](04-vigilance.md#karusmart) : 25 cultures du jeu de données sont exactement
ce cas.

---

## Ajouter un indicateur

Un indicateur traverse quatre couches. Sauter la dernière est l'erreur classique.

1. **Le calcul par culture** — un module de `domain/` (`environment.py`, `water.py`…) qui produit
   une série `culture → taux/ha`.
2. **Le pipeline** — `data_pipeline.build_dataset` range cette série dans
   `dataset.parameters["mon_taux_per_ha_cult"]`.
3. **Le reporting** — `reporting/indicators.py` l'applique à l'allocation (helper `rate()` de
   `compute_facts_table`), et le total atterrit dans le recap.
4. **Le rendre bornable** — ajouter l'entrée à `_INDICATOR_PARAMETERS` dans
   `case_studies/<cas>/model/model.py`. **C'est ce qui permet à un scénario d'écrire
   `territory_indicator_bound` dessus, sans une ligne de code de plus.**

**Pour l'exposer au score composite du dashboard, il faut DEUX ajouts** :
`INDICATOR_DIRECTION` dans `apps/dashboard/comparison.py` (le sens : coût ou bénéfice) **et** un
groupe de `_INDICATOR_LABELS` dans `pages/2_Comparaison.py` (l'appartenance au sélecteur). Le
premier seul ne branche rien.

⚠ **Deux pièges d'unité, tous deux rencontrés pour de vrai** :
- un taux par culture ne peut pas porter une dépendance à la **parcelle**. L'eau n'est prélevée
  que sur les parcelles irrigables : sans `plot_weight: irrigable`, une borne compte 56 Mm³ là où
  le rapport en annonce 35. Le carbone a le même problème (le bilan dépend du type de sol).
- **le seuil doit être exprimé dans les termes de la contrainte, pas lus sur `recap.json`.**

---

## Changer de solveur

```yaml
# config.yaml
solver:
  name: appsi_highs        # nom Pyomo SolverFactory
  args:                    # passés tels quels au solveur
    time_limit: 3600
    mip_rel_gap: 0.01
```

Pour un autre solveur (CBC, Gurobi…), changer `name` suffit *en principe* — `core/solve/solver.py`
ne fait qu'un `SolverFactory(name)`. Trois réserves mesurées :

- **le `warm_start`** est mappé sur le kwarg `warmstart` de Pyomo, que tous les solveurs ne
  supportent pas de la même façon ;
- **le conflit de descripteurs de fichiers** décrit dans [02](02-arborescence.md) est spécifique à
  `appsi_highs`, mais la règle « ne pas lancer le solve en arrière-plan » reste la plus sûre ;
- l'interface **APPSI persistante** a été testée puis **revertée** : le gain de ~25 % mesuré sur
  une île ne tient pas à pleine échelle.

`solver.args.time_limit` est le levier à relever pour un scénario dur (un plancher de surface
arboricole, un empilement de plafonds). ⚠ Un solve qui tape la limite rend un **incumbent
prouvablement sous-optimal** : le vérifier avant d'interpréter (voir
[04](04-vigilance.md#tractabilite)).

---

## Écrire un scénario

Un scénario est un jeu d'**overrides** sur `config.yaml`. Quatre canaux, et un seul sait créer :

| Canal | Ce qu'il fait |
|---|---|
| `overrides: {chemin.pointé: valeur}` | remplace une valeur scalaire / un dict / une clé entière |
| `enable: [token]` / `disable: [token]` | bascule `enable:` sur les entrées correspondant au **label** (à défaut au `name`) |
| `set_args: [{label, args}]` | fusionne des arguments dans l'entrée portant ce label |
| `enable_add: [{name, section, args}]` | **ajoute une entrée qui n'existe pas** dans la config de base |

⚠ `set_args` ne sait patcher qu'une entrée **déjà déclarée**. C'est pour ça que `azote_max` et
`emploi_min` vivent en `enable: false` dans `config.yaml` : des coquilles vides qui donnent prise
aux balayages.

⚠ **Asymétrie à connaître** : `apply_overrides` applique toujours `enable` **avant** `disable`.
Un token désactivé par l'un des deux specs reste désactivé quoi que dise l'autre. Un forçage qui
doit réactiver ce qu'une politique a coupé doit passer par `enable_add`.

⚠ **Composition politique × forçage** : quand les deux écrivent le même chemin pointé et que les
deux valeurs sont des **listes**, elles sont **concaténées** (c'est ce que veulent les listes de
multiplicateurs). Tout le reste est un remplacement, le forçage gagnant.

**Toujours valider avant de payer des heures de calcul :**

```bash
python scripts/run_scenarios.py --scenarios <fichier> --dry-run
python scripts/check_scenario_feasibility.py --scenarios <fichier>
```

---

## Avant de committer

```bash
python -m pytest tests/<les fichiers touchés>.py       # rapide
python scripts/golden_snapshot.py --check              # si pipeline/domain/core.data/indicators
python scripts/check_references.py                     # si le modèle ou la config a bougé
python -m pytest                                       # vérification finale (~29 min)
```

Et **lisez le commentaire avant de basculer un `enable:`**. Plusieurs entrées de `config.yaml`
sont désactivées volontairement, correctes et testées, mais provoquant une infaisabilité réelle
(et conforme au GAMS) sur les données 2017. La raison est écrite juste au-dessus.
