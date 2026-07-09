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

### Majeur — Pas de données ETP / travail
Aucune occurrence de "ETP" (ni d'équivalent travail/main d'œuvre) dans tout le
repo. L'indicateur "revenu / ETP de travail" demandé n'est donc pas
calculable actuellement.
**Prochain fix possible** : identifier une source de données ETP par
exploitation ou par culture (temps de travail par ha et par itinéraire
technique, éventuellement dans les fichiers GAMS d'origine
`old_code_gms_format_now_txt/` s'ils existent) avant de pouvoir l'ajouter au
dashboard.
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
- [x] **A. Sauvegarde des résultats** (`outputs/output_N/` + récap + PNG) — en cours d'implémentation.
- [ ] **B. Dashboard de visualisation** — dépend de A pour les données de sortie ; le côté "entrée" peut démarrer indépendamment.
- [ ] **C. Exclusion de zones** (parcelles/exploitations/régions/îles) avant optimisation, pour tests à petite échelle et scénarios de transition locale.
- [ ] **D. Performance du solver** — nécessite d'abord un profilage pour diagnostiquer où le temps est perdu.
- [ ] **E. Remise à niveau du code** (suppression du mort, commentaires concis) — a priori continu, au fil des autres briques.

## Résolu

_(rien pour l'instant)_
