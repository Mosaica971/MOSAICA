# Fichier de vigilance

Points d'attention sur le code MOSAICA, d'une session à l'autre : zones peu claires,
trous de données, limites assumées. Les **choses à faire** vivent dans `TODO.md` ;
ici on ne garde que le *pourquoi* et l'état des lieux.

Sévérités : **Critique** (fausse un résultat) / **Majeur** (limite fonctionnelle réelle) /
**Mineur** (amélioration).

## Points ouverts

### Majeur — Pas de données géographiques
Aucun shapefile/GeoJSON, et `Data_Parc_Gwad_2017.txt` n'a ni lat/long ni identifiant de
géométrie. Pas de vraie carte des cultures possible : le reporting spatial s'agrège par
`ILE`/`REGION`/`COMMUNE`. _2026-07-09._

### Majeur — L'allocation fine 2017 en entrée n'a jamais existé (indicateurs d'entrée = hypothèse)
La baseline `cult_2017` n'encode la culture qu'au niveau **agrégat/RPG** (12 codes, cf.
`farm_typology._RPG_CODE_TO_BASE_GROUP`). **Le GAMS faisait pareil** (`Matrice_Parc_Cult`,
`ENTREES.txt:64-102`) : la variante technique de 2017 n'a jamais été observée, ce n'est pas
un portage manquant. Les codes agrégats sont dans `CULT_2017.set` avec une économie nulle ;
le solveur réalloue vers les 84 variantes fines en sortie.
**Conséquence** : pour calculer production/subvention/revenu/ETP **en entrée**, on substitue
une variante fine représentante par famille (`config.yaml baseline_representative_crops`).
Les indicateurs d'entrée et les écarts entrée/sortie reposent donc sur cette **hypothèse**,
documentée et configurable. _2026-07-09, adressé le 2026-07-13._

### Majeur — Le run complet reste lent (~30–55 min), avec une variance énorme
1 683 058 variables ; historique pour cette taille : 1622s, 2600s, 3132s, 3310s, 3442s (×2,1
pour un problème identique). Le goulot est la **recherche branch-and-bound**, pas l'enveloppe
Pyomo→HiGHS (~15s, négligeable) : le profilage brique D avait conclu l'inverse parce que le
sous-ensemble testé se résolvait entièrement au presolve (0 nœud B&B). Confirmé par le revert
APPSI ci-dessous. _2026-07-10._

### Mineur — Indicateur GES : magnitude élevée (fidèle au GAMS)
`environment.compute_ges_per_ha_cult` reproduit à l'identique `OPTIMISATION.txt:118-127`. Le
max atteint ~1.6e5 « t CO₂/ha/an », dominé par `COND_EXP_ME` (fret aérien melon, `GES_Q=2156.8`)
et des `GES_SURF` jusqu'à 2769. Ces valeurs viennent **des données sources** (`Data_OTK.txt`) :
le GAMS produirait les mêmes. L'unité annoncée « t CO₂ » est probablement fausse (kg ?), mais
corriger dévierait de la parité ; le score composite normalise en min-max, donc le classement
n'est pas faussé. _2026-07-17._

### Mineur — `zone_filter` ne redimensionne pas les quotas territoriaux
Choix assumé (section « Non-goals » de la spec zone-exclusion) : un sous-ensemble peut devenir
infaisable vis-à-vis de seuils pensés pour tout le territoire. Contournement : désactiver
manuellement les `territory_production_bound` concernées pour les runs à petite échelle
(c'est ce que fait automatiquement `profile_solver.py`). _2026-07-10._

### Majeur — Bug GAMS porté fidèlement sur les vergers (`Eq_VE_BTGT` / `Eq_VE_PLUIE`)
`MODELE.txt:305-307` interroge `Data_RPG_Gwad` sur des colonnes `REGION`/`ILE` **absentes**
de cette table (elle n'a que `ident` + `cult_2012..cult_2017`). GAMS renvoie 0 sans broncher,
donc le comportement réel est : `VE_BTGT` interdite en `REGION = 4` **seulement** (et non
`{4,5}`), et `VE_PLUIE` interdite **sur toute parcelle** (le test `0 ≠ 1` est toujours vrai).
Décision du 2026-07-20 : porter le comportement réel (mandat de parité). Les variantes
« intention présumée » sont dans `config.yaml` en `enable: false` juste à côté — basculer les
paires suffit. **Conséquence : `VE_PLUIE` n'apparaîtra jamais en sortie.** Si un jour on
compare à des données observées de vergers, c'est le premier suspect.
Détail : `docs/gams_port_inventory.md`. _2026-07-20._

### Majeur — `Eq_MO_MAX_Expl` (plafond main d'œuvre) non porté
`MO_Expl_init` suppose l'allocation fine 2017 par parcelle, qui n'a jamais existé (cf. le
point sur la baseline agrégée) : les codes agrégats portent des OTK/MO nuls, donc le plafond
serait calculé sur une base vide. Voie de réactivation : approximer via les cultures
représentantes (`baseline_representative_crops`), au prix d'une hypothèse supplémentaire.
Cf. `docs/gams_port_inventory.md`. _2026-07-20._

### Majeur — Bloc canne fourragère (CF) non câblé
Toutes les équations `Eq_CF_*` (bans géographiques, `Eq_CF_MIN`, `Eq_CF_T0..T8`) restent hors
modèle. À noter : les bans CF passent par `REGION` (BT↔{4,6}, SBT↔5, NGT↔3, CGT↔1, EGT↔2),
mapping **différent** de la canne à sucre qui passe par `COMMUNE` — à confirmer au câblage.
Lot séparé, cf. `TODO.md`. _2026-07-20._

**Précision du 2026-07-20 (corrige la formulation initiale).** Les 10 cultures `CF_*` sont
bien dans `CULT_2017.set`, éligibles et économiquement valorisées : elles tirent leur prix de
`Prix_Cult.txt` (45 €) comme les autres. Ce qui manque, ce sont (a) les contraintes `Eq_CF_*`
et (b) l'exploitation de `indice_H/Prix_Cult_CF_{RESTIT,SMART}.txt` et
`Rdt_Cult_CF_{RESTIT,SMART}.txt`. **Ces fichiers ne sont pas des tables « prix des CF »** :
ce sont des variantes **territoire entier** de `Prix_Cult`/`Rdt_Cult` (mêmes lignes, toutes
cultures) décrivant un monde où la filière CF existe. Elles diffèrent de la table de base
au-delà des CF (ex. `AN_NU`/`AN_PA` 1100→1200, `BC_*` 800→700) et, contre-intuitivement,
y mettent les `CF_*` à **prix 0**. Le sens exact (scénario alternatif ? table obsolète ?)
est à trancher avec la source **avant** tout câblage — brancher naïvement ces fichiers
changerait l'économie de cultures sans rapport avec la canne fourragère.
Nomenclature : le GAMS dit « canne **fibre** » (`DECLAR_OPT.txt:437`), comme
`crop_labels.py`. C'est ce fichier qui écrivait « fourragère » à tort — corrigé ici, le
titre de la section est conservé pour la continuité des recherches.

### Majeur — Piège : deux ordres de types de sol incompatibles
`SOL.set` et les colonnes de `Data_Sol.txt` sont ordonnés `NITISOL, ANDOSOL, FERRALSOL,
AUTRES, VERTISOL`. Le GAMS mappe la colonne numérique `TYPE_SOL` de `Data_Parc` dans un ordre
**différent** : `1→VERTISOL, 2→FERRALSOL, 3→ANDOSOL, 4→NITISOL, 5→AUTRES`
(`OPTIMISATION.txt:2880-2896`). Indexer `Data_Sol` par position produit des coefficients faux
mais plausibles — **erreur silencieuse**. Toujours mapper par nom. _2026-07-20._

### Majeur — Pas de pluviométrie mensuelle (bloque le besoin d'irrigation net)
La formule GAMS du besoin en eau déduit `PLUVIO_01_PARC`..`PLUVIO_12_PARC`, colonnes
**absentes** de `Data_Parc_Gwad_2017.txt` (qui n'a qu'un `PLUVIO_PARC` annuel). GAMS renvoie 0
sur colonne manquante — même mécanique que le bug `Eq_VE_PLUIE`. Conséquence : la pluie n'a
**jamais** été déduite, l'indicateur est un besoin en eau **brut des cultures**, pas un besoin
net d'irrigation. Ne pas l'étiqueter « irrigation ». Débloquable par une série pluviométrique
mensuelle par parcelle. _2026-07-20._

### Mineur — Second bug GAMS sur le besoin en eau (`max(0, ·)` manquant)
`OPTIMISATION.txt:2527-2538` : le `$` ne conditionne que le terme pluie, pas la soustraction.
Quand le besoin est inférieur à la pluie, l'expression vaut `BESOIN − 0 = BESOIN` au lieu de
`0`. Intention manifeste : `max(0, besoin − pluie)`. Comportement réel porté (mandat de
parité), variante corrigée en `enable: false` à côté. **Tant que la pluie mensuelle est
absente, les deux variantes donnent le même résultat** — le choix ne devient visible que si
les données mensuelles arrivent. _2026-07-20._

### Mineur — Unité du besoin en eau : facteur 10 omis par le GAMS
`BESOIN_EAU_MM` est en mm/mois (~100 mm × 12 ≈ 1200 mm/an, réaliste). 1 mm sur 1 ha = 10 m³,
donc le besoin en m³ vaut `mm × ha × 10`. Le GAMS omet ce facteur et divise par 1e6
(`OPTIMISATION.txt:2559`) ; l'auteur avait lui-même laissé « pourquoi x 10 ? » en commentaire
(`DECLAR_OPT.txt:2114`). Le portage Python expose des m³ corrects via une constante nommée.
Sans effet sur le classement (score composite en min-max), comme pour le GES. _2026-07-20._

### Mineur — Bilan carbone : flux annuel seulement, pas de trajectoire
Le GAMS itère `C_ORG = C_ORG + (entrées − sorties)` sur plusieurs années (`NB_BOUCLE`,
`OPTIMISATION.txt:2946`). Le modèle Python est mono-année / mono-solve : seul le **flux annuel**
est portable. Une trajectoire pluriannuelle demanderait de ré-allouer année après année —
autre projet. À noter aussi : `C_ENTREE_AMDT` n'est annualisé ni par `Duree_Cycle` ni par
`Duree_Plant` (`OPTIMISATION.txt:2919`), contrairement à azote/GES/coûts. Reproduit fidèlement,
mais ressemble à un oubli côté source. _2026-07-20._

### Mineur — Données présentes jamais lues par le pipeline
Inventaire au 2026-07-20 de ce qui traîne dans `data/` sans être chargé :
- `Data_Sol.txt` (`KAER`, `DENS`, `PROF`, `KOC`) et `R_Tixier.txt` (14 seuils
  Favorable/Défavorable) — **ce ne sont pas des indicateurs d'érosion** (erreur d'analyse
  initiale). `R_Tixier` porte les seuils de **Rpest** (Tixier et al.), indicateur de risque de
  **pollution de l'eau par les pesticides**, développé précisément pour les systèmes bananiers
  de Guadeloupe. Module GAMS dédié `R_PEST_NEW.txt`, jamais porté. Données **complètes** :
  `Data_OTK` fournit `DT50`/`GUS`/`ADI`/`AQUATOX`/`QMA`/`KOC`/`DOSE`, `Data_Parc` fournit
  `RUI_PARC`/`DRAI_PARC`/`PENTE`/`PLUVIO_PARC`, `Data_Cult` fournit `COUV_SOL`/`PROF_SILLONS`.
  Rien à collecter. Cf. `TODO.md`.
- `Data_OTK` porte aussi `HOUDART_TOX_SCORE`/`HOUDART_SOLUB_SCORE`/`HARMFUL_FACTOR`
  (2ᵉ méthode pesticides, spécifique Antilles) et `DLRAT`/`BIRD` (écotoxicité), inexploités.
- `indice_H/RS_Cult.txt`, `indice_H/Cout_Transp_Cult_LAM.txt`, `indice_H/Rdt_Cult_INIT.txt`
  — colonnes économiques inutilisées ; les deux premières sont à 0 sur les lignes inspectées,
  donc probablement sans effet, à confirmer.
- Sets `EXPL_NBT` (824), `PARC_NBT` (4811), `CULTIV_2017` (83), `NONBOIS_2017` (79),
  `VAR_C`/`VAR_OTK`/`VAR_SOL`/`VAR_PARC_2017` — sous-ensembles GAMS non portés. `NBT` =
  **Nord Basse-Terre** (pas « non bâti ») : côté GAMS ces sets n'alimentent que des
  agrégats de **restitution** (`ASSOL_NBT*`, `DECLAR_OPT.txt:242+`, assolement par commune
  du NBT), pas le périmètre d'optimisation. Enjeu de reporting territorial fin, pas de
  parité de résultat.
- `Avers.txt` — délibérément ignoré (stub uniforme), cf. commentaire `config.yaml:122`.
_2026-07-20._

### Mineur — `BESOIN_EAU_01`..`12` sont plates : tout indicateur mensuel de l'eau est dégénéré
Vérification sur `Data_Cult.txt` (revue finale de la branche `indicateurs-eau-carbone`,
2026-07-20) : les 12 colonnes mensuelles `BESOIN_EAU_01`..`BESOIN_EAU_12` sont **identiques
pour les 84 cultures** — la table ne porte qu'un chiffre mensuel plat, pas un vrai profil
saisonnier. Conséquence : le mois de pointe (`water_need_peak_month_m3`, ajouté par ce lot)
vaut toujours exactement le total annuel / 12, donc aucune information au-delà du total —
c'est pourquoi il reste dans le recap mais est exclu du score composite du dashboard
(`INDICATOR_DIRECTION` / `_ENV_INDICATORS`). Le CSV mensuel par côté envisagé pour le
dashboard a été abandonné pour la même raison (12 lignes identiques se liraient comme une
vraie courbe). Un futur indicateur mensuel de l'eau (saisonnalité, pic de tension) restera
dégénéré tant qu'un vrai profil `BESOIN_EAU_*` mensuel n'est pas fourni en amont. _2026-07-20._

### Mineur — `Eq_ME_MG` et la règle melon `REGION_CODE` se recouvrent peut-être
`Eq_ME_MG` interdit ME en `REGION = 7` (macro-région) ; la règle `region_crop_forbidden`
préexistante interdit ME dans 18 `REGION_CODE` (petites régions). Référentiels distincts,
les deux restrictives — l'intersection est sûre, mais on ignore si la seconde était censée
remplacer la première. À vérifier avec la source des données. _2026-07-20._

### Mineur — Le margin-max abandonne canne et banane export
Au run complet, l'objectif marge-max ne retient que ~9 cultures et laisse tomber totalement
la canne à sucre et la banane export (aucun min-quota ne les force). Résultat d'optimisation,
pas un bug de couverture — mais à garder en tête. Les 84 cultures de `CULT_2017.set` ont bien
toutes des données économiques et une entrée d'éligibilité. _2026-07-13._

## Résolu

- **`REGION` vs `REGION_CODE`** (2026-07-20) — deux référentiels bien **distincts**, pas une
  redondance. `data_parc["REGION"]` (entier 1–7) est la macro-région agronomique du GAMS :
  c'est elle qu'utilisent les bans ITK désormais portés. `REGION_CODE` (R0–R27, calculé via
  `REG_PARC_2017.set`) désigne les petites régions et ne sert qu'à la règle melon. Les deux
  restent nécessaires. Cf. `docs/gams_port_inventory.md`.
- **Bans ITK géographiques GAMS** (2026-07-20) — les ~24 équations `Eq_CS_*`, `Eq_IG_*_ILE`,
  `Eq_BA_*`, `Eq_BC_*`, `Eq_AG_*`, `Eq_VE_*`, `Eq_MA_TO_CHOU_JA_LOC`, `Eq_ME_MG` sont portées
  via la règle générique `attribute_forbidden` (+ `forbid_crops`), pilotées depuis
  `config.yaml`. Deux d'entre elles reproduisent un bug GAMS — voir le point ouvert dédié.
- **Dashboard comparatif multi-scénarios** (2026-07-13) — page `dashboard/pages/2_Comparaison.py`,
  adossée à une table de faits tidy par run et par côté (`csv/facts_<side>.csv`,
  `indicators.compute_facts_table`). Logique de données dans `dashboard/comparison.py` (pur, testé).
  Les PNG statiques restent volontairement simples : les graphes riches vivent dans le dashboard.
- **Coût MO + revenu net** (2026-07-13) — la MO n'est pas monétisée dans le coût variable GAMS
  (heures seulement) : `labor.cost_per_hour` ajoute un indicateur de reporting (n'affecte **pas**
  l'optimum) et un revenu net = marge brute − coût MO. Défaut 0 → rétro-compatible. Au passage,
  tous les CSV d'un run sont sous `output_N/csv/`.
- **`year`/`scenario` en config** (2026-07-13) — plus de constantes de module ; validation
  fail-fast. `var_rdt_cult` reste délibérément sur sa colonne `init`.
  Spec : `2026-07-13-expose-year-scenario-config-design.md`.
- **Indicateurs d'entrée via cultures représentantes** (2026-07-13) — voir le point ouvert
  correspondant pour l'hypothèse sous-jacente.
- **Interface APPSI persistante : testée puis revertée** (2026-07-10) — le gain ~25% mesuré sur
  l'île 1 ne tient pas à pleine échelle (3310s, dans la fourchette habituelle). Retour à
  `SolverFactory('appsi_highs')` (commit `de00f98`).
- **Barre de progression : synchrone obligatoire** (2026-07-10) — `appsi_highs` charge le modèle
  dans `capture_output(capture_fd=True)` ; toute I/O de progression concurrente depuis un thread
  corrompt les fd du process et casse **tout vrai run**. `run_with_progress` est synchrone (ETA
  statique avant, durée après). Spec : `2026-07-10-solver-progress-capture-fd-conflict.md`.
- **Indicateur ETP depuis les itinéraires techniques** (2026-07-10) — `MO_EXPL` dans `Data_OTK.txt`,
  formule `ENTREES.txt:463-469` portée par `economics.compute_labor_hours_per_ha_cult`. Conversion
  heures→ETP via `labor.hours_per_etp` (défaut 1607). Sortie uniquement.
- **Figures : noms de cultures explicites** (2026-07-10) — `crop_labels.py`, porté de
  `DESCRIPTION_SETS.txt`. Le token fertilisation des `MA_*` reste littéral (non documenté en GAMS).
- **Briques A–E** (2026-07-09 → 07-10) — sauvegarde des résultats, dashboard, `zone_filter`,
  profilage solver, remise à niveau du code : toutes livrées.
