# Documentation MOSAICA

MOSAICA affecte chaque parcelle agricole d'un territoire à **au plus une culture**, de façon à
maximiser la marge brute ajustée au risque, sous contraintes d'éligibilité agronomique, de règles
par exploitation et de quotas territoriaux. C'est un gros MILP binaire (~309 000 variables sur la
Guadeloupe 2017), résolu par HiGHS via Pyomo.

Ce dépôt est la **réécriture Python/Pyomo d'un modèle GAMS d'origine** (`context/gams/`). Le
mandat est la *parité* : le comportement legacy est porté fidèlement, y compris ses bugs, et
chaque déviation est délibérée et documentée.

## Par où commencer

| Vous voulez… | Lisez |
|---|---|
| lancer un calcul, un batch, le dashboard | **[01 — Utilisation](01-utilisation.md)** |
| savoir où vit quoi | **[02 — Arborescence](02-arborescence.md)** |
| ajouter une contrainte, une culture, un indicateur | **[03 — Modifier le modèle](03-modifier.md)** |
| interpréter un résultat sans vous tromper | **[04 — Vigilance](04-vigilance.md)** |
| porter le modèle sur un autre territoire | **[05 — Nouveau cas d'étude](05-nouveau-cas-etude.md)** |

**Si vous ne lisez qu'une seule page avant de citer un chiffre : [04 — Vigilance](04-vigilance.md).**
Le modèle produit des nombres crédibles là où ils ne veulent rien dire, et cette page dit lesquels.

## Installation

```powershell
git clone <url>
python -m venv .venv                              # ne PAS copier un .venv d'une autre machine
.venv\Scripts\python -m pip install -e ".[dev]"   # dépendances + pytest (HiGHS via highspy)
.venv\Scripts\python -m pytest tests\test_readers.py   # vérifier l'install (~1 s)
```

`data/` n'est **pas** dans le dépôt (tables d'entrée, shapefiles) : à copier à part. Sans lui,
tout ce qui touche aux données échoue ; les tests unitaires, eux, passent (ils sont sans données
par choix).

## Documentation de référence

- **[Inventaire du portage GAMS](gams_port_inventory.md)** — équation par équation, ce qui est
  porté, ce qui ne l'est pas, et pourquoi.
- **[Spécifications de conception](superpowers/specs/)** — une par chantier, avec le raisonnement
  et les mesures qui ont tranché. C'est là que vit le *pourquoi* d'une décision.
- **[Journal de vigilance](archives/journal-vigilance.md)** — le log complet des enquêtes
  (calibration, prairie, plantain, tractabilité). Volumineux ; la page 04 en est la synthèse
  actionnable.

## Sources externes (`context/`)

- `context/gams/` — le GAMS d'origine en `.txt`. **Source de vérité pour toute question de
  parité** : `MODELE.txt` (équations), `OPTIMISATION.txt` (calculs), `ENTREES.txt` (dérivations),
  `SETS.txt` (ensembles).
- `context/Chopin et al 2015 pour Hal.pdf` — l'article de référence. §2.6 définit la méthode de
  calibration (PAD) et les seuils, Tables 1 et 2 les rendements/marges et les coefficients
  d'aversion au risque.
- `context/Rapport technique variables MOSAICA_v2.docx` — dictionnaire des variables (non versionné).
