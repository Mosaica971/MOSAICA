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

### Majeur — Données de main d'œuvre non portées (ETP)
Le modèle GAMS d'origine calcule bel et bien la main d'œuvre
(`MO_Ha_Cult_init(SC)` par culture, `MO_Parc_init(SP)` par parcelle,
`ENTREES.txt:31,469`, agrégée en `MO_Gwad`/`MO_Gwad_Moy_ha` dans
`OPTIMISATION.txt:2015-2019` et affichée dans `RESULTATS.txt:137-138`
"TRAVAIL_TOT"/"TRAVAIL_MOY_HA"). Mais ces données n'ont jamais été portées
dans `data/tables/` côté Python (aucun fichier `MO_*`/`Travail_*`) — ce n'est
donc pas un manque de donnée source, juste un portage GAMS→Python non fait.
L'indicateur "revenu / ETP de travail" demandé reste donc non calculable
tant que ce portage n'est pas fait.
**Prochain fix possible** : porter `MO_Ha_Cult_init` (et sa source amont
dans `DONNEES.txt`/`ENTREES.txt`) vers un nouveau `data/tables/MO_Cult.txt`,
suivant le même pattern que `Prix_Cult.txt`/`Rdt_Cult.txt`.
_Constaté le 2026-07-09._

### Majeur — Comparaison entrée/sortie limitée à la résolution du groupe RPG
`cult_2017` (l'allocation observée, utilisée comme baseline "entrée") n'encode
les cultures qu'à la résolution de 12 groupes RPG
(`case_studies/guadeloupe/farm_typology._RPG_CODE_TO_BASE_GROUP`), alors que
le solveur alloue parmi ~84 cultures fines (`CULT_2017.set`), chacune avec
son propre rendement/subvention/marge à l'hectare. Il n'existe aucune table
officielle fine→groupe dans le repo Python. Le modèle GAMS d'origine, lui,
définissait une taxonomie `SC_*` bien plus riche (~40 familles,
`old_code_gms_format_now_txt/SETS.txt` lignes 113-607) qui aurait permis ce
rapprochement — mais elle n'est que partiellement portée dans
`config.yaml` (`crop_families`: 8 familles sur ~40, seulement celles utiles
aux contraintes actuellement actives). Construire un mapping fine→groupe par
préfixe de nom serait une supposition non validée (des cultures comme
`CF_*`/`TH` n'apparaissent dans aucun des deux schémas existants).
**Conséquence pour la brique A** : les indicateurs de production/subvention/
revenu par culture ne sont calculés qu'en sortie (résolution fine, précise) ;
côté entrée, seuls les indicateurs de surface/nombre de parcelles/diversité
sont calculés (résolution 12 groupes RPG, précise) ; les écarts entrée/sortie
se limitent aux agrégats indépendants de la résolution (surface totale
cultivée, nb parcelles actives, nb exploitations).
**Prochain fix possible** : porter la taxonomie `SC_*` de `SETS.txt` dans
`config.yaml` (comme déjà fait pour les 8 familles existantes) pour permettre
une comparaison entrée/sortie par famille de culture.
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
- [x] **C. Exclusion de zones** (parcelles/exploitations/régions/îles) avant optimisation, pour tests à petite échelle et scénarios de transition locale — voir `zone_filter` dans `config.yaml` (`core/data/zone_filter.py`).
- [ ] **D. Performance du solver** — nécessite d'abord un profilage pour diagnostiquer où le temps est perdu.
- [ ] **E. Remise à niveau du code** (suppression du mort, commentaires concis) — a priori continu, au fil des autres briques.

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

## Résolu

_(rien pour l'instant)_
