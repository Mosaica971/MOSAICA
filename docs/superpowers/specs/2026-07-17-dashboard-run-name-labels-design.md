# Dashboard — libellés de scénarios par `run_name` (chantier A)

## Contexte

Le dashboard (brique B, `apps/dashboard/`) identifie aujourd'hui
chaque run par le nom de son dossier (`output_N`), parfois enrichi de
`année/scénario` (ex. `output_1 · sortie (2017/RESTIT)`). Or `recap.json` porte
désormais un champ `run_name` bien plus parlant, positionné par le batch runner
(`scripts/run_scenarios.py` → `config["run_name"]`, persisté par
`reporting/report.py`). Objectif : afficher ce `run_name` partout où le dashboard
montre « output_N ».

État des données : sur les 12 runs présents, seuls `output_1` et `output_2` n'ont
pas de `run_name` (runs antérieurs à la fonctionnalité). Le fallback doit rester
robuste pour eux.

## Objectif

Remplacer l'étiquette « output_N » par le `run_name` du `recap.json`, avec fallback
sur le nom de dossier quand `run_name` est absent, aux deux endroits qui étiquettent
un run : le `selectbox` de la page principale et les libellés de séries de la page
de comparaison.

## Décisions retenues

- **Affichage** : seul le `run_name` (pas de suffixe `année/scénario`).
- **Fallback** : garder le nom de dossier `output_N` tel quel quand `run_name` est
  absent ou vide.
- **Côté entrée/sortie conservé** dans les libellés de la page de comparaison : deux
  séries d'un même run (entrée vs sortie) doivent rester distinctes.
- **Collision de `run_name`** (deux runs de même nom) : suffixer le nom de dossier
  entre parenthèses **uniquement en cas de doublon** (option 1). Un nom unique reste
  propre (`baseline · sortie`) ; un doublon devient `baseline · sortie (output_3)`.

## Changements

### 1. Helper unique — `loaders.py`

```python
def run_display_name(run_dir: Path, recap: dict) -> str:
    """run_name du recap, ou nom de dossier en fallback."""
    return recap.get("run_name") or run_dir.name
```

Source de vérité unique du « nom lisible d'un run », réutilisée par les deux pages.

### 2. Page principale — `app.py`

Le `selectbox` « Run » (ligne ~33) affiche aujourd'hui `path.name` via `format_func`.
Le `format_func` a besoin du recap : charger en amont un dict `{run_dir: recap}` pour
les runs listés, puis `format_func = lambda path: run_display_name(path, recaps[path])`.
Un recap illisible (OSError/ValueError) retombe sur `{}` → fallback nom de dossier.

### 3. Page de comparaison — `comparison.py` + `pages/2_Comparaison.py`

`series_label()` reçoit aujourd'hui `run_dir.name` et produit
`{run} · {sortie|entrée} (année/scénario)`. Nouveau contrat :

```python
def series_label(display_name: str, side: str) -> str:
    side_fr = {"output": "sortie", "input": "entrée"}.get(side, side)
    return f"{display_name} · {side_fr}"
```

`_discover_series()` (dans `pages/2_Comparaison.py`) passe désormais
`run_display_name(run_dir, recap)` au lieu de `run_dir.name`, et ne passe plus
`year`/`scenario`.

**Désambiguïsation des doublons** : `_discover_series()` construit `series_catalog`
en deux temps pour n'appliquer le suffixe de dossier qu'en cas de collision réelle :

1. Calculer le libellé de base `series_label(display_name, side)` pour chaque
   `(run, side)` ayant une table `facts`.
2. Si un même libellé de base apparaît pour plus d'un `run_dir`, suffixer
   ` ({run_dir.name})` à ces occurrences uniquement ; sinon le laisser tel quel.

Cela garantit l'unicité des clés du dict `series_catalog` (une collision écraserait
sinon silencieusement une série) tout en gardant les libellés propres dans le cas
courant.

## Hors périmètre

- Le recap Markdown (`report.py`) affiche déjà `run_name` s'il est présent — inchangé.
- Aucune modification du pipeline, du solveur, ou du format de `recap.json`.
- Chantiers B (indicateurs GES/IFT/azote/chlordécone, score agrégé) et C (autonomie
  alimentaire) : specs séparées, traitées ensuite.

## Tests

Les fonctions dashboard sont Streamlit-free et testables (cf. `tests/`). Ajouter des
tests unitaires purs :

- `run_display_name` : renvoie `run_name` s'il existe ; retombe sur le nom de dossier
  si absent, vide, ou recap `{}`.
- `series_label` : format `{display} · sortie` / `{display} · entrée`.
- Désambiguïsation : deux runs de même `run_name` → suffixe dossier sur les deux ;
  noms uniques → pas de suffixe.
