# Situation de référence 2017 — conception

_2026-07-27._ Livré. Scripts : `scripts/build_reference_state.py`,
`scripts/compare_to_reference.py`.

## Le problème

Le modèle était noté contre l'observé depuis le 2026-07-21 (`reporting/calibration.py`), mais
la **référence elle-même** n'existait nulle part comme objet : elle était recalculée à
l'intérieur de chaque run, sous le nom de « côté entrée », et n'était donc consultable qu'à
travers un résultat de simulation. Trois conséquences :

- impossible de dire ce que vaut la référence sans lancer un solve ;
- ses hypothèses (cultures représentantes, règle de continuité de friche, exclusion des NC)
  étaient dispersées dans le code et dans `docs/04-vigilance.md`, jamais réunies en un endroit ;
- un écart observé/simulé était systématiquement lu comme un défaut du **modèle**, alors
  qu'une partie tient à ce que la référence ne peut pas dire.

`outputs/` étant gitignoré, ce document est le seul endroit versionné où vit ce raisonnement.

## Décisions de conception

**1. La référence réutilise les fonctions du modèle, elle ne les réimplémente pas.**
`decode_baseline_allocation`, `compute_base_crop_group`, `compute_type_expl`, `indicators.*`.
Une deuxième implémentation « propre » aurait divergé silencieusement. Corollaire voulu :
l'estimation centrale de la référence **est** le côté entrée d'un run, au chiffre près.

**2. Deux lectures de l'assolement, toutes deux publiées.** La règle GAMS de continuité de
friche (`ENTREES.txt:49-57`) bascule en NC toute parcelle dont `cult_2016` **et** `cult_2017`
sont en jachère : 1 208 ha passent de JA à NC. C'est la lecture qu'utilisent le modèle, la
typologie et le PAD, mais ce n'est pas ce que dit le RPG brut. Publier la seule lecture
résolue aurait rendu la reclassification invisible. La lecture brute est obtenue en passant à
`compute_base_crop_group` un `cult_2016` jamais en jachère, plutôt qu'en dupliquant la table
code → groupe.

**3. Encadrement plutôt que point unique sur les indicateurs.** L'observé n'a pas de culture
fine : toute économie de la référence passe par `baseline_representative_crops`. Un chiffre
unique se lirait comme une observation. Les bornes rejouent chaque parcelle avec la variante
la moins puis la plus intense **parmi celles qui y sont éligibles**.

Ce choix a produit le résultat le plus utile du lot : **le central sort de la fourchette par
le haut** sur ventes, revenu, heures, azote, GES et IFT — parce que la représentante n'est
souvent pas éligible là où elle est comptée (canne 31 %, maraîchage 61 %). Un encadrement
symétrique autour du central aurait masqué exactement ce que l'on cherchait. Détail et
conséquences sur le plafond de main d'œuvre : `docs/04-vigilance.md`.

**4. Le plancher de PAD appartient à la référence, pas au run.** Une parcelle n'est
reproductible que si au moins une variante fine de sa famille observée y est éligible ; ce qui
ne l'est pas est un écart qu'aucun objectif ne peut éviter. Mesuré à **1,5 %** (348 ha sur
23 578). C'est une propriété des données et du masque, donc elle est calculée une fois dans la
référence et rappelée colonne par colonne dans la comparaison.

Le résultat est un verdict à double sens : il **innocente** le modèle sur les vergers et les
agrumes (irréproductibles pour cause de portage d'un bug GAMS, `Eq_VE_PLUIE`), et il
**l'accuse** partout ailleurs — l'éligibilité n'explique pas les 48 % de PAD.

**5. La comparaison ne relit pas les données.** `compare_to_reference.py` ne consomme que les
CSV déjà écrits par le run et par la référence (~1 s). `pad_all_scales.py` reste l'outil qui
reconstruit le dataset, pour l'échelle île qu'aucun run n'écrit.

## Non-goals assumés

- **Aucune assise externe.** Rien ne recoupe les 23 578 ha cultivés avec une statistique
  publique (Agreste/DAAF). La référence vaut ce que vaut le jeu parcellaire local — l'article
  travaille sur 5 336 exploitations, ce jeu en porte 4 638. Noté dans `TODO.md`.
- **Aucune correction des représentantes.** Le diagnostic est posé et chiffré ; changer une
  représentante change le plafond de main d'œuvre donc l'optimum, c'est un lot à part.
- **Aucune géométrie.** Toujours pas de shapefile : les déclinaisons s'arrêtent à
  île / région / commune.
