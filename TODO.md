# TODO — idées à implémenter

Ce qui reste à faire. Les limites connues et non planifiées sont dans `VIGILANCE.md`.

## En cours / prêt à coder

**Batch de scénarios + parité ITK géographique — livré le 2026-07-20** (lots 1, 2, 5).
Leviers `yield_multipliers`/`cost_multipliers`, règles `forbid_crops`/`attribute_forbidden`,
contrainte `crop_share_bound`, canal `enable_add`, ~24 bans ITK câblés, 25 scénarios,
`docs/gams_port_inventory.md`. **Aucun solve n'a été lancé** : la validation est unitaire
(`tests/test_scenario_overrides.py` résout les 25 scénarios sans résoudre le MILP).
→ Reste à faire : lancer `scripts/run_scenarios.py` en fin de journée pour vérifier qu'aucun
scénario n'est infaisable sur les données réelles, puis ajuster les seuils qui coincent.

## Différé (cadré, en attente d'une décision ou de données)

- **`Eq_AN_PA`** — `AN_PA` interdit si `Surf_Expl_Parc_init < AN_SURF_EXPL_MIN` : porte sur
  une taille d'**exploitation**, pas un attribut de parcelle, donc hors de portée de
  `attribute_forbidden`. Demande une règle catégorielle indexée par exploitation.

- **Bloc CF (canne fourragère)** — sorti du plan ci-dessus, à replanifier séparément.
  Inclut le chargement des fichiers scénario-dépendants `Prix_Cult_CF_{RESTIT,SMART}.txt`
  et `Rdt_Cult_CF_{RESTIT,SMART}.txt`, présents en données mais jamais lus par le pipeline.
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
- **`REGION` vs `REGION_CODE`** — vérifier l'équivalence, documenter ou fusionner.
- **Unité GES** — clarifier l'échelle de `GES_SURF`/`GES_Q` avec la source et documenter un
  facteur explicite (hors parité GAMS ; sans effet sur le score composite min-max).
