# Dashboard de visualisation (brique B) — Design

## Contexte

`outputs/output_N/` (brique A, mergee dans `gams-parity-phase2` le 2026-07-10)
persiste deja, pour chaque run : `recap.json`/`recap.md`, `allocation_input.csv`/
`allocation_output.csv`, et 5 PNG (production/subvention/revenu par culture en
sortie, surface par region en entree et en sortie). `case_studies/guadeloupe/
reporting/indicators.py` calcule deja plus d'indicateurs qu'il n'en persiste
(`compute_subsidy_per_tonne_by_crop`, `compute_subsidy_per_euro_sold_by_crop`,
`compute_revenue_by_farm`, `compute_gini`, `compute_shannon_diversity`,
`compute_surface_by_island_and_key`) : ils existent, sont testes, mais
`report.py::generate_report` ne les appelle pas encore.

Decisions actees avec l'utilisateur (2026-07-10) :
- Merger brique A dans `gams-parity-phase2` avant de commencer B (fait).
- Dashboard = app Streamlit interactive.
- Lecture seule sur `outputs/output_N/` : aucun bouton "lancer un run" dans
  l'app ; lancer `main.py` reste une action manuelle, separee.
- Trous de donnees connus (ETP, vraie carte geo) : placeholder "non
  disponible" + reference a `VIGILANCE.md`, pas de portage de donnees avant B.

## Non-goals

- Pas de carte geographique reelle (bloque, cf. `VIGILANCE.md` "Pas de
  donnees geographiques") : remplace par une repartition ILE/REGION/COMMUNE.
- Pas de revenu/ETP (bloque, cf. `VIGILANCE.md` "Donnees de main d'oeuvre non
  portees") : affiche "non disponible".
- Pas d'indicateurs `*_by_crop` (production/vente/subvention/revenu par
  culture) cote entree : la baseline (`cult_2017`) n'est connue qu'a la
  resolution des 12 groupes RPG, qui n'ont pas de rendement/prix propres
  (cf. `VIGILANCE.md` "Comparaison entree/sortie limitee a la resolution du
  groupe RPG"). Cote entree, seuls les indicateurs bases sur la seule surface
  (surface/nombre de parcelles/diversite par groupe, repartition geo) sont
  affiches.
- Pas de lancement de run depuis l'UI (lecture seule, voir ci-dessus).
- Pas de comparaison multi-runs dans cette premiere version (un run a la fois
  via un selecteur) — extension possible plus tard si besoin.

## Architecture

Deux parties independantes :

**B1 — etendre `generate_report` pour persister les indicateurs deja
codes.** `report.py` calcule deja `output_allocation`/`input_allocation` ;
il suffit d'appeler les fonctions d'`indicators.py` qui ne le sont pas
encore et d'ecrire leur resultat en CSV dans `output_dir/` (a cote des CSV
d'allocation existants) :
- `subsidy_per_tonne_by_crop.csv`, `subsidy_per_euro_sold_by_crop.csv`
  (sortie uniquement — dependent de rdt/prix fins).
- `revenue_by_farm.csv` + `gini_revenue_by_farm` (scalaire) dans `recap.json`
  (sortie uniquement).
- `shannon_diversity_by_region.csv`, `shannon_diversity_by_island.csv`
  (entree ET sortie — ne dependent que de la surface, donc valides aux deux
  resolutions).
- `surface_by_island_input.csv`/`surface_by_island_output.csv` (symetrique
  au `surface_by_region_*` deja fait).

**B2 — app Streamlit read-only.**
`case_studies/guadeloupe/dashboard/app.py` :
1. Liste les dossiers `outputs/output_*/`, trie par numero, `st.selectbox`
   pour choisir un run (par defaut le plus recent).
2. Charge `recap.json` + tous les CSV du dossier choisi (fonctions pures
   dans `case_studies/guadeloupe/dashboard/loaders.py`, testables sans
   Streamlit).
3. Rend, en sections Streamlit (`st.tabs` ou `st.expander`) :
   - **Recap** : objectif/valeur, solveur, contraintes actives + args,
     duree, timestamp (depuis `recap.json`).
   - **Entree** (baseline `cult_2017`) : surface/parcelles/exploitations
     actives, surface par groupe RPG (`allocation_input.csv`), repartition
     ILE/REGION, diversite de Shannon. Bandeau "revenu/ETP : non disponible
     (voir VIGILANCE.md)" et "carte des cultures : non disponible (pas de
     donnees geo), repartition ILE/REGION affichee a la place".
   - **Sortie** : memes indicateurs de surface/parcelles + production
     (tonnes), subvention (€, €/tonne, €/€ vendu), revenu total et par
     exploitation + Gini, par culture fine (84 cultures).
   - **Entree vs sortie** : les deltas deja dans `recap.json["delta"]`
     (surface totale, parcelles actives, exploitations actives) — les
     seuls deltas valides vu la difference de resolution.
4. Chaque graphique utilise les widgets natifs Streamlit
   (`st.bar_chart`/`st.dataframe`) sur les CSV charges, pas les PNG
   statiques (deja generes par brique A mais pas la source du dashboard
   interactif — les PNG restent utiles pour un coup d'oeil rapide hors
   dashboard).

## Data flow

```
outputs/output_N/{recap.json, allocation_input.csv, allocation_output.csv,
                  subsidy_per_tonne_by_crop.csv, subsidy_per_euro_sold_by_crop.csv,
                  revenue_by_farm.csv, shannon_diversity_by_*.csv,
                  surface_by_island_*.csv, plots/*.png}
        |
        v  (loaders.py: pure functions, path -> DataFrame/dict)
case_studies/guadeloupe/dashboard/app.py (Streamlit widgets only, no computation)
```

`loaders.py` contient toute la logique testable (parsing JSON/CSV, jointures
pour l'affichage) ; `app.py` ne fait qu'appeler `loaders.py` et des appels
`st.*`. C'est la meme separation "coeur testable / wiring UI mince" que
`report.py` vs `indicators.py`.

## Error handling

- `outputs/` absent ou vide : l'app affiche un message ("Aucun run trouve —
  lancez `python main.py` d'abord.") au lieu de planter.
- Un `output_N/` incomplet (CSV manquant, ex. genere par une ancienne
  version de `report.py` avant B1) : chaque section du dashboard gere
  l'absence de son fichier independamment (`st.info("indicateur non
  disponible pour ce run")`) plutot que de faire planter toute la page.

## Testing

- B1 : tests unitaires sur `generate_report` (etendre
  `tests/test_guadeloupe_reporting_report.py` existant) verifiant que les
  nouveaux fichiers sont bien ecrits avec le bon contenu, sur le meme jeu de
  donnees factice a 2 parcelles deja utilise par ce fichier de test.
- B2 : tests unitaires sur `loaders.py` (nouveau `tests/
  test_guadeloupe_dashboard_loaders.py`) avec des fixtures `tmp_path`
  imitant un `output_N/` — pas de test Streamlit UI (hors de portee
  raisonnable pour ce projet), juste la couche de chargement/transformation
  des donnees.
- Verification manuelle : un run reel mais restreint (`zone_filter` sur une
  petite region/exploitation, cf. brique D) sert de fixture pour lancer
  `streamlit run` et verifier visuellement le rendu — ce n'est pas le run
  complet reserve a la demande de fin de journee.

## Dependances

Ajoute `streamlit` a `pyproject.toml` (`dependencies`).
