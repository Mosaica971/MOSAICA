# Fichier de vigilance

Points d'attention sur le code MOSAICA, d'une session à l'autre : zones peu claires,
trous de données, limites assumées. Les **choses à faire** vivent dans `TODO.md` ;
ici on ne garde que le *pourquoi* et l'état des lieux.

Sévérités : **Critique** (fausse un résultat) / **Majeur** (limite fonctionnelle réelle) /
**Mineur** (amélioration).

## Points ouverts

### Majeur — Calibration : finalisée à PAD 51 % (limite reproductible fidèle au `CALIB`)
_Chantier clos le 2026-07-23. Voir le bloc **FINALISATION** en fin d'entrée pour la décision
et l'état retenu ; ce qui suit est l'historique du diagnostic._

`reporting/calibration.py` note chaque run contre l'assolement réellement observé
en 2017, aux quatre échelles de Chopin et al. (2015) §2.6. Verdict initial sur `output_12` :

| Métrique | Obtenu | Article | Seuil |
|---|---|---|---|
| PAD territorial | **193 %** | < 15 % sur 8 usages/10 | 15 % |
| Cultures sous seuil | **0 / 11** | 8 / 10 | — |
| Types d'exploitation reproduits | **7,3 %** | 81 % | 80 % |
| Parcelles bien simulées | **7,0 %** | 66 % | — |
| Surface bien simulée | **4,5 %** | 77 % | — |

Dix des onze cultures observées disparaissent **entièrement** (12 813 ha de canne, 6 109 ha
de prairie, 1 921 ha de banane → 0), et le maraîchage passe de 1 087 à 24 155 ha (PAD
2 122 %). La matrice de confusion montre neuf types d'exploitation s'effondrant sur trois,
presque tous vers « Maraîchers ».

Deux causes probables, toutes deux cohérentes avec l'article :
1. l'objectif actif est `maximize_gross_margin`, pas l'utilité de Markowitz où le
   coefficient Ø freine chaque type d'exploitation. `maximize_risk_adjusted_gross_margin`
   existe et porte déjà les Ø de la Table 2, mais reste `enable: false` ;
2. `Eq_MO_MAX_Expl` (Eq. 5 de l'article) n'est pas portée — cf. l'entrée dédiée plus bas.
   Le maraîchage demande 990 à 1 560 h/ha contre 15 h/ha pour la canne mécanisée (Table 1
   de l'article) : sans plafond de main-d'œuvre par exploitation, rien ne limite la bascule.

**Ne pas lire un PAD élevé comme une régression du reporting** : c'est son diagnostic. Spec :
`docs/superpowers/specs/2026-07-21-calibration-validation-design.md`.

**Mesuré le 2026-07-23 : PAD 193 % → 51 %.** L'enquête GAMS a montré que le modèle résolu
n'était pas celui que l'article évalue (`MODELE.txt` déclare `INIT`/`CALIB`/`SCENARIO`,
l'article évalue `CALIB` §3.1). Leviers portés (spec `2026-07-21-calibration-levers-design.md`) :
objectif de Markowitz, 14 suppressions `Eq_*_SUPP`, prairie `PN_PIQ`, plafond de main d'œuvre.
`Eq_CS_GFA` **désactivée** (infaisable avec le plafond, cf. entrée dédiée), planchers de
production **désactivés** (`SCENARIO`, pas `CALIB`, et infaisables avec le plafond), et bug de
sol de l'ananas corrigé (règle inversée). État `output_13` et mesures suivantes :

| Métrique | Avant | Après | Article | Seuil |
|---|---|---|---|---|
| PAD territorial | 193 % | **51 %** | < 15 % sur 8/10 | 15 % |
| Types reproduits | 7,3 % | **63 %** | 81 % | 80 % |
| Parcelles conformes | 7 % | **54 %** | 66 % | — |
| Surface conforme | 4,5 % | **62 %** | 77 % | — |

Canne (22 %) et maraîchage (18 %) sont désormais bien reproduits. **Ce qui reste bloqué :
plantain sur-planté ~20× (147 → 2 905 ha) et prairie sous-plantée (6 109 → 2 278 ha).** Ni le
plafond de main d'œuvre ni l'aversion au risque ne les corrigent :
- balayage `slack` du plafond (2026-07-23) : `1.0` domine tout ; toute valeur < 1 dégrade PAD
  ET types de façon monotone. Le plafond est optimal, ce n'est pas le levier du plantain.
- le plantain a une marge de 11 387 €/ha (conforme Table 1 de l'article) et une variance de
  0,25 trop faible pour qu'un éleveur (AVERS 2,4) lui préfère la prairie : ré-ajuster AVERS ne
  peut pas l'inverser. Il est éligible sur 14 476 ha (bans géographiques `Eq_BC_*` corrects,
  vérifiés) et **aucune contrainte de `CALIB` ne plafonne son extension** (les `*_QUOTA_MAX`
  plantain/ananas/igname sont commentés dans le GAMS lui-même).
Hypothèse restante : la calibration serrée de l'article reposait sur un jeu d'AVERS re-tuné en
100 itérations (§2.5) contre **leurs** données complètes, non reconstructibles ici, ou sur une
réalité de marché (débouché plantain limité) qu'aucune équation `CALIB` n'encode. _2026-07-23._

**Investigation prairie et plantain (2026-07-23, expériences non committées).**
- **Plantain** : bug de sol ananas corrigé (committé). Un plafond de surface territorial sur
  plantain+ananas calés près de l'observé fait tomber le PAD à **33,6 %**, mais il **force**
  ces cultures (PAD nul par construction, pas émergent). Débouché de marché réel, mais écart
  assumé au `CALIB`. Non committé, à valider.
- **Prairie** : la moitié des 6 109 ha observés part en **canne mécanisée** (marge 2 400-3 500
  €/ha), qui bat légitimement la prairie (1 602, variance nulle). Éleveurs (AVERS 2,4) et
  canniers-éleveurs (2,3) la gardent déjà ; la fuite vient des **canniers diversifiés**
  (AVERS 1,4). **GAMS `CALIB` n'a AUCUNE contrainte de cheptel** (vérifié : seuls un ban
  chlordécone `Eq_PN_PIQ_CLD` et des suppressions) : il reproduisait la prairie par la seule
  aversion + économie. Deux tentatives de correction, toutes deux écartées :
  - re-tuner l'AVERS du type 4 : gain marginal (~2 % de PAD, prairie +261 ha) car les
    variantes de canne à très forte marge (jusqu'à 3 531) résistent même à AVERS 2,5 ;
  - contrainte d'inertie de cheptel (prairie ferme ≥ fraction × prairie observée) : **rend le
    MILP intraitable** (> 10 min même à 5 % d'écart, contre 175 s sans), en plus d'être une
    invention hors `CALIB` ancrée sur l'observé. Non retenue.
  Conclusion : la prairie sous-plantée (~3 100 ha d'écart) est le plafond dur ; la refermer
  demanderait le tuning AVERS complet de l'article contre ses données, hors de portée ici.
  _2026-07-23._

**FINALISATION (2026-07-23) — retenu : PAD 51 %, coefficients d'aversion publiés (Table 2).**
Trois voies pour descendre sous 51 % ont été instruites jusqu'au bout puis écartées, chacune
pour une raison de fond :

1. **Recalibration §2.5 de l'aversion** (descente de coordonnées sur les types 3/4/6/8,
   minimisant le PAD) → **39,9 %**, types 69 %, prairie récupère ~1 250 ha. **Mais** les
   coefficients trouvés sont économiquement absurdes : cannier spécialisé 0,30 → **2,50** (×8),
   cannier diversifié 1,40 → **3,20**, éleveur 2,40 → **3,60**. Un spécialiste « très averse »
   contredit la définition même du type (l'article les met à 0,30 *parce qu'*ils s'engagent sur
   une culture rentable). C'est de l'overfitting : l'aversion sert de variable d'ajustement pour
   compenser une absence structurelle (l'élevage), pas un vrai paramètre de risque.
2. **Plafonds de marché** (plantain + ananas calés ≈ observé) → **33,6 %**, mais ils **forcent**
   ces cultures (PAD nul par construction). Défendable pour des scénarios, pas pour de la
   calibration.
3. **Incorporer l'élevage** (le vrai correctif de la prairie). L'élevage est **déjà** dans la
   marge de la prairie (bœuf inclus). Le seul ajout possible est une **contrainte** de cheptel :
   plancher territorial de prairie (`Eq_PN_PROD_MIN`, vraie équation GAMS, seuil 6 096 ≈ observé)
   ou minimum par ferme. **Les deux forcent** (seuil ≈ observé) **et rendent le MILP intraitable**
   (> 10 min même à 10 % d'écart, contre 175 s sans) — testé en quatre formulations. Écarté.

**Pourquoi 51 % est le bon point d'arrêt.** L'investigation a confirmé que la canne est
**fidèlement valorisée** (rendements = Table 1, marges = Table 1, quota sucrier = GAMS et
non-contraignant dans les deux, bans de mécanisation/pente/sol corrects) : **aucun bug de
sur-attractivité**. L'écart résiduel — prairie, plantain, petites cultures — recoupe les limites
que **l'article reconnaît lui-même** (« manque de données sur le maraîchage et les prairies »,
melon à 100 % de PAD). Descendre plus bas exige de dégrader le sens des coefficients ou de
forcer : nommer la limite est plus honnête. Les trois leviers ci-dessus restent **disponibles**
(scripts dans l'historique, valeurs consignées ici) pour qui privilégierait un PAD bas sur la
fidélité, mais **ne sont pas le défaut**. _2026-07-23._

### Mineur — Reconstruction typologique et parcelles `NC`
`compute_type_expl` calcule `denom = surf_cultiv - surf_non`, où `surf_non` agrège `JA` et
`NC` : une parcelle non cultivée **diminue** le dénominateur et remonte toutes les parts
`PART_*`. `calibration.farm_type_confusion` recalcule donc les groupes de base depuis
`data_parc` sur l'univers complet, et non depuis `allocation_input.csv` qui écarte les `NC`.
Côté simulé, une parcelle que le solveur laisse sans culture compte comme `NC`. Conséquence :
`scripts/evaluate_calibration.py` **doit** reconstruire le `Dataset` (7 s), il ne peut pas
travailler sur les seuls CSV d'un run. Le script superpose d'ailleurs le config du run au
`config.yaml` courant au lieu de le reprendre tel quel : un run ancien peut nommer un
composant retiré du registre (`output_12` référence `melon_soil_restriction`, supprimée le
2026-07-21) et `build_dataset` lèverait. _2026-07-21._

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
**Mise à jour 2026-07-21** : le portage des suppressions `Eq_*_SUPP` fait tomber le problème
de 1 271 780 à **904 121 variables** (−29 %). Les durées ci-dessous sont donc pessimistes, et
le chiffre historique de 1 683 058 datait d'avant les bans ITK du 2026-07-20.
Historique pour l'ancienne taille : 1622s, 2600s, 3132s, 3310s, 3442s (×2,1
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

### Majeur — Le plafond de main d'œuvre repose sur les cultures représentantes
`Eq_MO_MAX_Expl` est porté depuis le 2026-07-21 (`farm_labor_hours_max`), mais **pas avec la
formule GAMS littérale**. Celle-ci (`ENTREES.txt:466-469`) calcule `MO_Expl_init` sur
`Matrice_Parc_Cult`, qui porte les codes **agrégés** — et 9 des 12 n'ont aucune ligne ITK
(colonnes `AN/BA/BC/CS/IG/MA/NC/PN/VE` de `Matrice_OTK_Cult` entièrement nulles ; seules
`AG`, `JA` et `ME`, les familles sans variante fine, sont renseignées). Le plafond littéral
serait donc quasi nul et le modèle GAMS lui-même n'allouerait rien.
`data_pipeline.compute_farm_labor_capacity_hours` valorise chaque famille observée via sa
variante représentante. **Conséquence à ne pas perdre de vue** : l'hypothèse
`baseline_representative_crops`, jusque-là cantonnée au reporting, **influence désormais
l'allocation**. Changer une représentante change le plafond, donc l'optimum. Les 50 fermes à
plafond nul sont exactement celles sans surface cultivée observée, ce qui est correct.
_2026-07-21._

### Majeur — Déviation assumée du GAMS sur `Eq_CS_GFA`
`cs_gfa_minimum_share` est réactivée avec `skip_when_no_eligible_area: true`. Trois fermes
(`E1471`, `E273`, `E3955`) ont toutes leurs parcelles verrouillées en friche par
`friche_lock` : la contrainte exige 60 % de canne sur une exploitation qui ne peut en porter
aucune. C'est **algébriquement infaisable, et le GAMS le serait aussi**. Nous choisissons de
perdre 3 fermes sur 4 588 (0,07 %) plutôt que la contrainte entière, parce qu'elle est l'un
des rares mécanismes qui retiennent la canne (5 286 ha sous GFA face à 12 813 ha observés).
Le drapeau est à `false` par défaut dans le builder : le comportement fidèle reste
l'option par défaut pour qui ne le demande pas. _2026-07-21._

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
**Suite (2026-07-21)** : c'était le symptôme, la cause est identifiée. `maximize_gross_margin`
ignore `Var_Rdt`, or c'est la seule chose qui sépare les cultures — MA_ROTA 27 929 €/ha à
`Var_Rdt` 0,65 contre CS_NGT_NISM 1 521 à 0,20 et PN_PIQ 1 602 à 0,00. L'objectif actif est
désormais `maximize_risk_adjusted_gross_margin`. Cette entrée décrit donc l'**ancien** défaut ;
elle est conservée pour qui rebasculerait sur la marge brute pure.

### Majeur — Le score de stabilité mesure l'exposition, pas l'adaptation
Les indicateurs de `resilience.py` (marge à risque, HHI, choc de prix) portent sur une
allocation **figée** : rien n'est ré-optimisé. Ils répondent à « si l'aléa tombe une fois les
assolements décidés, qu'est-ce qui est exposé ? », pas à « de combien l'optimum se dégrade-t-il
sous contrainte choquée ». À ne pas lire comme de la résilience. Une vraie mesure d'adaptation
demanderait de ré-optimiser sous choc — autre projet. À ne pas confondre non plus avec les
leviers `price_multipliers` / `yield_multipliers` de `config.yaml`, qui eux choquent les
entrées **avant** le solve et laissent l'optimiseur s'adapter. _2026-07-20._

### Mineur — `crop_variance_per_ha` porte un nom trompeur
Le paramètre contient `Var_Rdt_Cult`, qui est une **fraction de perte de marge**, pas une
variance ni un coefficient de variation (`OPTIMISATION.txt:70`, `MODELE.txt:427`). Non renommé
parce qu'il est consommé par l'objectif Markovitz et ses tests de la phase 2. Piège classique
pour qui voudrait bâtir un calcul de variance dessus : la perte est **linéaire** en surface,
sans carré ni covariance. _2026-07-20._

### Mineur — `NC` porte `Var_Rdt = 1,0`
« Non cultivé » affecté d'une perte de 100 % est un artefact du tableau source. Sans effet sur
le choc de prix (`Prix_Cult = 0` et `Rdt_Cult = 0`, vérifié), mais sa contribution à la marge à
risque vaut `marge_NC × 1,0`, et sa marge n'est pas mécaniquement nulle (`subventions − coûts`).
À mesurer sur un vrai run : si la contribution est significative, l'exclure explicitement. Le
GAMS maintient d'ailleurs un set dédié `CULT_NON_NC_2017`. _2026-07-20._

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
