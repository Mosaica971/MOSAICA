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

**RÉOUVERTURE 2026-07-27 — investigation de parité « pourquoi pas les résultats CALIB de
l'article ».** Question reposée : l'article annonce CALIB à PAD <15 % / types 81 %, on obtient
49 % / 63 % avec le même modèle. Investigation systématique source-à-source (spec
`docs/superpowers/specs/2026-07-27-calib-parity-rootcause-design.md`). **Écarté comme cause (tout
fidèle, vérifié)** : objectif Markowitz, coefficients AVERS (l'article dit lui-même §2.5 que
Table 2 **est** le résultat calibré des 100 itérations — donc pas à re-tuner), économie
marge-incl-subventions (`MB_HA = PB − CV`, `PB` inclut `SUB_TOT`, OPTIMISATION.txt:41), mapping
RPG→groupe (ENTREES.txt:60-105 identique), direction des bans chlordécone. **Trois points de
blocage réels identifiés :**
1. **Provenance des données** : l'article a 5336 fermes, on en a 4588 (−14 %). Distributions par
   type différentes. Comme le mapping typologique est identique, c'est un écart de **jeu de
   données** pur (notre `data/` est un sous-ensemble différent), non corrigeable. Plafond
   structurel sur PAD et matrice de confusion.
2. **Le gap MIP de 1 % noie la frontière prairie/canne.** Diagnostic parcellaire : sur les 3054 ha
   prairie→canne, 1403 ha partent en canne **alors que la prairie était éligible ET meilleure au
   vrai AVERS** (radj prairie 1602 vs canne 1034-1386) — impossible à l'optimum exact. Cause :
   objectif 85,9 M€ × gap 1 % = 859 k€ de tolérance, et la frontière prairie(1602)/canne(1521-1617,
   variantes Marie-Galante à Var_Rdt=0) est plate à <1 %. Le solveur y est indifférent, résout
   ~3000 ha arbitrairement en canne. **Pas un bug modèle — tolérance de solveur sur frontière
   plate.** **Resserrer le gap est un cul-de-sac, TESTÉ (output_4, gap 1e-3)** : le solve tape le
   time_limit d'1 h avec un incumbent identique à la solution à 1 % (PAD 49,3, types 63,7 — zéro
   prairie récupérée). Le B&B ne ferme pas cette frontière en temps traitable et les heuristiques
   HiGHS ne trouvent pas la solution riche en prairie. `solver.py` charge désormais l'incumbent
   sur `maxTimeLimit` (au lieu de lever) ; le gap reste à 1 % (optimum traitable). Le leak de
   prairie est donc une **limite d'intractabilité B&B**, pas un bouton de réglage.
3. **Petites déviations CALIB.** `Eq_PN_PIQ_CLD` était appliqué à tort (interdit la prairie sur
   16 % des plots, RISQUE_CLD==1) alors qu'il est **absent du bloc modèle CALIB** (commenté en
   SCENARIO ; `Eq_IG_CLD`, lui, y est). **CORRIGÉ** (désactivé `exact_risk_value`) : prairie
   éligible 76,5 %→90 % des plots. Reste `Eq_AN_PA` non porté (ananas +488 %), `Eq_CF_*` non câblé.
La conclusion « aucun bug de sur-attractivité » du 2026-07-23 tient (économie fidèle) ; ce qui
change, c'est de **nommer le gap MIP et la provenance des données** comme les vraies causes, pas
un plateau mystérieux.

**Situation de référence formalisée + reproduction sur machine neuve (2026-07-27).** L'état
initial observé est désormais un artefact à part entière : `scripts/build_reference_state.py`
→ `outputs/reference_2017/` (assolement observé, typologie, indicateurs encadrés, plancher de
PAD), et `scripts/compare_to_reference.py` met un run en face. Trois choses qu'il fallait
nommer et qui ne l'étaient pas :
1. **Le plancher de PAD imposé par l'éligibilité est de 1,5 %** (348 ha sur 23 578 : agrumes
   52, vergers 167, canne 84, plantain 26…), le double si l'on compte l'excès créé ailleurs.
   **L'écart de 48 % ne s'explique donc PAS par le masque d'éligibilité** — c'est un choix
   d'optimisation, pas une impossibilité. Les vergers et agrumes irreproductibles le sont
   d'ailleurs pour une raison de portage (`Eq_VE_PLUIE` interdite partout, bug GAMS fidèle),
   pas d'agronomie.
2. **Le PAD par exploitation a une médiane de 18,5 % pour une moyenne de 51,5 %** : la moitié
   des fermes est sous le seuil de 20 % de l'article, l'écart est concentré sur une minorité
   (quartiles 0 / 18,5 / 88,7). Ne pas lire « 48 % » comme un écart uniforme.
3. **Plusieurs indicateurs du run tombent dans la fourchette d'incertitude de l'observé**
   lui-même (subvention, revenu, azote, ETP) : l'assolement 2017 n'étant connu qu'au niveau
   agrégé, l'écart au « central » n'y démontre rien. Cf. REFERENCE.md §4.1.
Le run `output_1` sur la machine neuve redonne exactement l'état documenté (PAD 48,4 %, types
64,0 %, parcelles 56,0 %, surface 64,3 %) : la reproductibilité est vérifiée. Le solve tient
en **140 s** (308 847 variables après les suppressions), très loin des 30-55 min historiques.

**RÉOUVERTURE 2026-07-27 (2) — modalités de l'article, impact du solveur, cause dominante.**
Trois questions reposées, trois réponses chiffrées. Elles **invalident partiellement** le verdict
du bloc précédent (« blocage #2 : le gap MIP ») et **identifient une cause dominante unique**.

*(a) Les modalités de l'article ne sont pas celles qu'on lui prêtait.*
1. **L'année de base de l'article est 2010, pas 2017** (« the crops grown on them in 2010 »,
   recensement Agreste 2010) : 25 057 parcelles, 27 350 ha, 5 336 exploitations. Nous : 24 734
   parcelles, 26 137 ha, 4 638 exploitations. **Région par région les parcelles et les hectares
   collent à quelques % près** (CGT 1601/1540, NGT 5561/5269, NBT 4325/4251…) : c'est le **même
   territoire et les mêmes champs**, avec 13 % d'exploitations en moins — sept ans de
   concentration foncière (5,13 → 5,64 ha/ferme), pas « un sous-ensemble différent » comme le
   disait le diagnostic du matin. `Data_RPG_Gwad` commençant en 2012, leur année de base est
   **structurellement hors d'atteinte**.
2. **Le PAD de l'article est par culture, jamais agrégé.** Éq. 7 somme sur les parcelles pour
   **une activité** ; le seuil <15 % qualifie « 8 usages sur 10 ». Notre chiffre de tête (ligne
   TOTAL) est une agrégation que l'article ne fait nulle part, et plus sévère. La métrique
   comparable est `crops_within_threshold` (0/11 contre 8/10 — et leurs 10 usages fusionnent
   vergers et agrumes). Lecture utile du 48,4 % : les totaux entrée/sortie s'équilibrant, il
   signifie que **24,2 % de la surface observée porte la mauvaise culture** au niveau agrégé.
3. **Table 5 compte les parcelles NC, nous les excluons.** Leur dénominateur est la base entière
   (25 057 / 27 350 ha) et `Eq_NOCULT_NC` verrouille les NC : ce sont des accords gratuits. À
   leur convention, `output_1` passe de 56,0 %/64,3 % à **60,5 % / 67,8 %** (2 537 parcelles /
   2 559 ha NC des deux côtés). Quatre points relevaient de la définition.
4. **Ni moyenne ni médiane** : Tables 4 et 5 sont des **rapports de sommes** (vérifié : la
   moyenne de leurs 7 taux de surface donnerait 71 %, pas les 77 % publiés) — comme nos lignes
   TOTAL. Et **l'article ne publie aucune table de PAD par exploitation** : le seuil « 20 % …
   and farms » n'est jamais instancié, l'évaluation à l'échelle ferme *est* la matrice de types.
   Notre médiane de 18,5 % est une métrique maison ; la statistique comparable est la part des
   fermes sous seuil (2 312/4 588 = 50,4 %).
5. **Six de nos sept sous-régions sont à 4–13 points de l'article** ; une seule s'effondre :
   **Sud-Est Basse-Terre, 36,9 % contre 61,4 %** (surface 38 % contre 66 %). L'erreur est
   localisée, pas diffuse.

*(b) Le solveur est hors de cause, des deux côtés.*
- **Le plan observé vaut 15 % de moins que l'optimum sous notre propre objectif.** Valorisé en
  donnant à chaque parcelle la meilleure variante fine éligible de sa famille observée (borne
  haute, contraintes de ferme ignorées) : **72,2 M€ contre 85,0 M€**. Le gap MIP est de 1 %.
  L'écart à combler est **quinze fois** la tolérance. Le diagnostic « frontière plate
  prairie/canne » du bloc précédent reste exact mais pèse ~0,4 M€ sur 12,8, soit **3 %**.
- **Trois graines HiGHS** (défaut/7/42), même modèle, même gap : PAD 48,44 / 48,29 / 48,31,
  types 64,04 / 63,97 / 63,91, objectif à 21 k€ près (0,025 %). **L'arbitraire de branchement
  vaut 0,15 point de PAD.** Il n'y a pas de bouton solveur.
- Le plan observé demande 5,68 M h contre un plafond de 6,25 M h : la main d'œuvre ne l'interdit
  pas non plus.

*(c) La cause dominante est le plantain, et la contrainte qui manque existe dans le GAMS.*
Décomposition de l'écart de 12,8 M€ par groupe (objectif ajusté au risque) : **BC +20,9 M€**,
CS +4,0, AN +3,7, MA +1,9, contre BA −9,4, PN −5,7, ME −1,5. **Le plantain vaut à lui seul plus
que la totalité de l'écart.** Substitution dominante après prairie→canne : **banane export →
plantain, 1 298 ha**, concentrée en Sud-Est Basse-Terre (BA 1 427 → 311 ha, BC 81 → 1 488 ha) —
exactement la sous-région qui s'effondre. Mécanisme arithmétique : `BC_BT` 11 386 €/ha à
`Var_Rdt` 0,20 sans subvention **et sans rotation obligatoire** ; `BA_INT` est meilleur à
l'unité (9 099 contre 7 971 à AVERS 1,2) **mais `Eq_BA_JA` impose 20 % de jachère** (116 €/ha),
ce qui ramène le mélange à 7 602 €/ha : **le plantain gagne de 4,9 %**. Ce n'est PAS le plafond
de main d'œuvre (saturation médiane 48,6 % sur les 138 exploitations qui basculent).
`Eq_BC_QUOTA_MAX` (MODELE.txt:385) est **commentée dans les deux blocs modèles** (lignes 551 et
668) alors que **l'article la décrit, Éq. 6** : « maximum thresholds … current consumption for
non-exported crops, such as plantain … (respectively 4500 and 150 tons) ». Le run produit
**74 757 t** ; le paramètre GAMS vaut 40 000 t et **mord déjà**. Mesures :

| Variante | PAD | Types | Parcelles | Surface | BC ha | BA ha | Objectif |
|---|---|---|---|---|---|---|---|
| base | 48,4 % | 64,0 % | 56,0 % | 64,3 % | 2 875 | 978 | 84,98 M€ |
| plafond 40 000 t (paramètre GAMS) | **38,1 %** | 65,4 % | 58,7 % | 67,7 % | 1 527 | **1 993** | 84,29 M€ |
| plafond 6 440 t (commentaire GAMS) | **31,7 %** | **67,0 %** | **59,8 %** | **69,0 %** | 247 | 2 213 | 81,79 M€ |
| _observé_ | — | — | — | — | _147_ | _1 921_ | — |

À 40 000 t la banane revient à 1 993 ha contre 1 921 observés (PAD 3,8 %, contre 49 %) pour
**0,8 % d'objectif**. Le plantain reste à 247 ha contre 147 observés même au plafond serré :
**la contrainte ne force pas la culture** — contrairement aux « plafonds de marché » écartés le
2026-07-23, qui étaient calés *sur* l'observé (PAD nul par construction). Les trois valeurs
candidates (40 000 t paramètre, 6 440 t commentaire de l'auteur, 4 650 t article) sont toutes
**exogènes à l'assolement observé**.

**Balayage du seuil — le test qui distingue une correction d'un ajustement.**

| seuil (t) | 4 650 | 6 440 | 9 240 | 15 000 | 25 000 | 40 000 | désactivé |
|---|---|---|---|---|---|---|---|
| PAD | 31,7 | 31,7 | **31,2** | 34,4 | 36,4 | 38,1 | 48,4 |
| types | 66,8 | 67,0 | **67,1** | 65,8 | 65,6 | 65,4 | 64,0 |
| surface | 69,0 | 69,0 | **69,3** | 68,6 | 68,2 | 67,7 | 64,3 |
| plantain (ha) | 179 | 247 | 355 | 577 | 960 | 1 527 | 2 875 |

Deux lectures. (1) **Palier plat de 4 650 à 9 240 t** — facteur 2 sur le seuil, 0,5 point de
PAD, soit à peine plus que le bruit de solveur mesuré (0,15) : le résultat ne dépend pas de la
valeur, seulement de l'existence d'un plafond à l'échelle du marché. (2) **L'optimum du palier
est à 9 240 t (×2,4 l'observé), pas au seuil le plus serré** : un paramètre servant de variable
d'ajustement s'améliorerait de façon monotone en se rapprochant de l'observé. C'est la
différence de fond avec les plafonds écartés le 2026-07-23.

**ACTIVÉ le 2026-07-27 à 6 440 t** (chiffre de l'auteur du GAMS ; corroboré par l'Éq. 6 de
l'article, 4 650 t, et par notre propre production observée, 3 827 t). Valeur choisie parce
qu'elle est **sourçable**, pas parce qu'elle note le mieux — le palier rendant le choix
indifférent au score, prendre 9 240 t pour 0,5 point serait précisément le sur-ajustement qu'on
évite. **C'est la première déviation assumée au bloc `CALIB`** depuis la clôture du 2026-07-23 :
`enable: false` y ramène. _2026-07-27._

**Rien à retirer côté sur-contraintes.** Diff équation par équation contre la liste `CALIB`
(MODELE.txt:450-565). Deux règles n'ont pas d'équivalent GAMS et se révèlent **inertes** :
`SURF_PARC_MAX` (GAMS n'a que `Eq_SURF_MIN_Parc` ; la colonne vaut 1 000 ha pour les 84
cultures) et l'absence d'exemption d'irrigation sur `PLUVIO_MIN` (`Eq_PLUVIOMIN_PARC` a
`AND IRRIG_PARC = 0` ; mais `PLUVIO_MIN` = 0 et `PLUVIO_MAX` = 10 000 partout). Retirer les
deux : **+0 paire éligible**, plancher de PAD inchangé à 348 ha. Le portage est propre.
Résolu au passage : le recouvrement `Eq_ME_MG` / règle melon `REGION_CODE` (entrée « Mineur »
plus bas) est sans enjeu — 8 647 parcelles avec les deux, 8 683 sans la seconde. Et le melon est
éligible sur 7 721 parcelles pour 0 ha planté : son PAD de 100 % est **économique**, pas
structurel (l'article échoue aussi sur le melon, à 100 %, pour une autre raison). _2026-07-27._

**Résultat des corrections fidèles (runs complets)** : baseline output_2 → output_5
(PN_PIQ_CLD désactivé + Eq_AN_PA porté, gap 1 %) : PAD **49,3→48,4 %**, types **63,3→64,0 %**,
parcelles **55,1→56,0 %**, surface **63,1→64,3 %**. Gains modestes mais **cohérents sur toutes les
métriques**, uniquement par parité CALIB (retrait d'une contrainte à tort, ajout d'une vraie
contrainte CALIB) — pas de forçage. Confirme le plateau ~48 %/64 % comme structurel (données +
intractabilité B&B), l'article atteignant 81 %/<15 % sur SES 5336 fermes avec le même modèle.
_2026-07-27._

### Majeur — Le déficit de prairie : diagnostic complet (2026-07-27)
Premier poste d'erreur depuis l'activation du plafond plantain : **6 109 ha observés → 2 980
simulés** (`output_2`, PAD 51 %). 3 489 ha de prairie observée ne sont pas reconduits (360 ha
de prairie apparaissent ailleurs). Analyse parcellaire, sans solve.

**Où elle va.** 83 % en canne (2 881 ha), 12 % en banane (413 ha), le reste dispersé.
Géographiquement c'est **Marie-Galante** qui s'effondre : 1 357 → 228 ha (−83 %), et la seule
variante `CS_MG_NISM` absorbe **1 042 ha**. Par type observé, seuls les éleveurs (AVERS 2,4) et
canniers-éleveurs (2,3) en gardent — 54 % et 32 % ; tous les autres types en perdent 78 à 100 %.

**Pourquoi.** Décomposition des 3 489 ha (la prairie est éligible sur **100 %** d'entre eux) :
1. **2 149 ha — le modèle préfère franchement autre chose** (+2,42 M€). Économie légitime.
2. **1 258 ha — le choix est *moins bon* à l'hectare** (−0,45 M€ au total) **mais le retour à la
   prairie est impossible à solution figée, faute d'heures.** La prairie demande 126 h/ha contre
   12,7 pour la canne : rebasculer coûte +113 h/ha que la ferme a déjà dépensées ailleurs.
3. **66 ha (49 k€) de résidu réellement inexpliqué.**

**Ceci corrige le « blocage #2 » du 2026-07-27 matin.** Celui-ci concluait que 1 403 ha partaient
en canne « alors que la prairie était éligible ET meilleure — impossible à l'optimum exact »,
et l'imputait au gap MIP. Le raisonnement comparait des marges ajustées **parcelle par
parcelle** en oubliant que l'objectif est séparable mais **pas les contraintes** :
`Eq_MO_MAX_Expl` couple toutes les parcelles d'une exploitation. Ces hectares ne sont pas un
artefact de solveur (les trois graines donnent PN à 2 576 / 2 581 / 2 571 ha) : ils sont
l'optimum d'un problème couplé.

**Le bloc de Marie-Galante est fragile, pas faux.** `CS_MG_NISM` vaut 1 617,1 €/ha et `PN_PIQ`
1 602,0, tous deux à `Var_Rdt` nul : la canne gagne de **15 €/ha, soit 0,94 %, indépendamment de
l'aversion**. 1 042 ha — 30 % du déficit — tiennent sur un écart inférieur au gap MIP et à
toute incertitude de données plausible. Resserrer le gap ne changerait rien (la canne gagne
vraiment) ; un point de subvention en plus ou en moins inverserait le résultat.

**La main d'œuvre de la prairie diverge de la Table 1 de l'article — seule ligne dans ce cas.**
Contrôle des six systèmes de la Table 1 : rendements et marges collent (banane −0,7 %, igname
0,0 %, plantain 0,0 %, ananas +0,2 %, prairie +0,8 %, canne +4,6 %) et la main d'œuvre aussi
(banane 1 558 vs 1 560, igname 991 vs 990, plantain 609 vs 620, ananas 436 vs 450, canne 12,7
vs 15) — **sauf la prairie : 126 h/ha contre 70 publiées, +80 %**. Ce n'est **pas** un bug de
portage : recalculée à la main depuis `Data_OTK` avec la formule `ENTREES.txt:463-465`, la
valeur tombe exactement sur 126,0 (ABREUVEMENT 360×0,20 = 72 h, DEPLACEMENT_PIQ 180×0,25 = 45,
SAILLIS 6, TRAITEMENT_BOV 3 ; `Duree_Cycle` = 12 donc l'annualisation est neutre). C'est une
divergence entre les tables 2017 et l'article de 2010. Sans effet décisif de toute façon : même
à 70 h/ha la prairie serait à 22,9 €/h contre 99-156 pour la canne.

**Le vrai mécanisme manquant, nommé précisément.** Les 126 h/ha de la prairie sont **entièrement
du travail de troupeau** — abreuvement, déplacement du piquet, saillies, traitements bovins ;
aucune opération agronomique. Le modèle peut donc **liquider un cheptel gratuitement** et
redéployer 126 h/ha de travail d'éleveur vers la canne (12,7 h/ha) ou les cultures. Ce qui
manque n'est pas l'économie de l'élevage — elle est bien dans la marge de `PN_PIQ` (bœuf inclus,
0,66 t/ha à 5 400 €/t) — mais une **variable d'état** interdisant la liquidation sans coût.
L'article le reconnaît lui-même en §4.5.

**`Eq_PN_PROD_MIN` : la raison de son rejet était la mauvaise.** Le verdict du 2026-07-23
(« rend le MILP intraitable ») laissait croire à une infaisabilité. Vérifié : **0 exploitation
sur 4 638** est incapable de porter sa propre prairie observée, même en mettant partout ailleurs
la culture éligible la moins gourmande en heures. Le plancher est donc **faisable** ; il reste à
écarter, mais pour la bonne raison — son seuil GAMS (`QUOTA_PN_PIQ_MIN` = 6 096) **est**
l'assolement observé (6 109 ha), c'est un forçage circulaire, et il est dans le bloc `SCENARIO`,
pas `CALIB`. Contrairement au plafond plantain, aucune source exogène ne le fonde.

**Ce qu'il faudrait pour le refermer** : une statistique externe de cheptel (effectifs bovins
Agreste/DAAF × chargement ha/UGB) donnerait un plancher de surface fourragère **exogène à
l'assolement observé** — le seul correctif non circulaire. Donnée absente du dépôt. Cf. `TODO.md`.
_2026-07-27._

**DONNÉE TROUVÉE ET PLANCHER ACTIVÉ — 2026-07-28.** Spec :
`docs/superpowers/specs/2026-07-28-plancher-prairie-design.md`. La Statistique agricole annuelle
**2017** (Agreste, *Mémento Guadeloupe* éd. 2019, champ « exploitations ») donne notre année
exacte.

*Assise externe de la référence — point ouvert de `TODO.md` désormais clos.* Notre jeu
parcellaire couvre **87 %** de la SAU 2017 (26 137 ha contre 30 066) et restitue la **canne à
98 %** (12 813 contre 13 066), les fruits à 90 %, les légumes à 76 %. La référence n'est plus
« ce que vaut le jeu parcellaire local ».

*Le RPG sous-déclare la prairie — 64 % (6 109 contre 9 595 ha) contre une couverture générale de
87 %.* Ce n'est pas un problème d'étiquetage : si les ~3 500 ha manquants étaient des parcelles
de notre univers classées en canne, notre canne dépasserait Agreste — elle est à 98 %. **Ce sont
des parcelles absentes de l'univers parcellaire.** Conséquence : ces hectares ne sont pas
récupérables *dans* notre périmètre, et c'est le périmètre — plus le modèle — qui borne
désormais la prairie.

*Preuve physique du défaut.* Cheptel bovin au 1ᵉʳ décembre 2017 : 40 449 têtes ≈ **29 771 UGB**
(ratio RA2020/SAA2019). Chargement implicite : sur les 9 595 ha d'Agreste **3,10 UGB/ha**, ce qui
tombe pile sur les repères des recensements (RA2010 32 056/10 250 = 3,13 ; RA2020 27 496/11 222 =
2,45) ; sur les **2 980 ha du modèle sans plancher, 9,99 UGB/ha** — trois à quatre fois le réel,
agronomiquement impossible. Le défaut est donc prouvé **hors modèle**, pas par désaccord avec
notre propre référence.

*Balayage du plancher* (PAD / types / parcelles / surface / canne) :

| plancher | PAD | PAD hors PN | types | parcelles | surface | canne |
|---|---|---|---|---|---|---|
| aucun | 31,7 % | — | 67,0 % | 59,8 % | 69,0 % | 15 425 |
| **6 096 ha** | 6,6 % | — | **86,9 %** | **67,6 %** | **77,1 %** | **12 782** |
| 7 218 ha | 15,7 % | 14,9 % | 84,2 % | 66,2 % | 75,0 % | 11 633 |
| 8 341 ha | 23,2 % | 18,5 % | 84,3 % | 67,0 % | 74,6 % | 11 121 |
| 9 595 ha | 32,6 % | 24,0 % | 82,0 % | 65,2 % | 72,2 % | 10 530 |

_(observé : canne 12 813 ha. Le point 7 218 a tapé la limite d'1 h, son incumbent est
prouvablement sous-optimal — 77,77 M€ quand 8 341, plus contraint, atteint 78,99. Ne pas
surinterpréter.)_ Les métriques que le plancher **ne contraint pas** tiennent sur toute la plage
exogène — types 82-87 %, parcelles 65-68 %, surface 72-77 %, au niveau ou au-dessus des 81 % /
66 % / 77 % de l'article — donc le gain n'est pas un artefact du seuil. En revanche tout se
dégrade en montant, y compris hors prairie, parce que la canne y descend sous son niveau
**attesté** : forcer la prairie au-delà de l'observable revient à la prendre à la culture la
mieux mesurée.

**ACTIVÉ à 6 096 ha** (paramètre GAMS `QUOTA_PN_PIQ_MIN`), **27 % SOUS** les 8 341 ha exogènes
(9 595 × 87 %) : conservateur, et sa proximité avec l'observé (13 ha) n'est pas de la
circularité mais le même raisonnement fait par l'auteur du GAMS. **Seconde déviation assumée au
bloc `CALIB`** (`Eq_PN_PROD_MIN` est dans `SCENARIO`).

**À ne PAS revendiquer** : le PAD territorial de 6,6 %. Le plancher épingle la prairie, dont le
PAD est nul par construction. Les chiffres à citer sont **types 86,9 %, parcelles 67,6 %,
surface 77,1 %**, et surtout la **canne revenue à 12 782 ha contre 12 813 observés** (PAD 0,24 %
contre 20,4 %) sans qu'aucune contrainte ne la nomme.

**Deux verdicts antérieurs corrigés** : « plancher intraitable » (2026-07-23) est **faux** — il
datait du modèle à 900 000+ variables, le solve prend **170 s** à 309 000 (mais ~1 h aux seuils
intermédiaires) ; « plancher circulaire » (mon objection du 2026-07-27) est **levée** par la
statistique externe. _2026-07-28._

### Majeur — Le PAD résiduel : les rendements du modèle sont 2 à 4× ceux du territoire
_2026-07-29._ Après le plafond plantain et le plancher de prairie, le PAD résiduel d'`output_3`
vaut 1 556 ha de déviation, portée par les petites cultures. La Statistique agricole annuelle
2017 (Agreste, *Mémento Guadeloupe* éd. 2019, p. 16-17 : superficie **et production** par
culture) permet pour la première fois de les confronter à une source externe.

| | Agreste 2017 | observé (RPG) | simulé | sim / Agreste |
|---|---|---|---|---|
| Canne | 13 066 ha | 12 813 | 12 782 | **98 %** |
| Prairie | 9 595 | 6 109 | 6 096 | 64 % |
| Maraîchage | 1 946 | 1 087 | 1 149 | 59 % |
| Melon | 294 | 189 | 4 | **1 %** |
| Agrumes | 283 | 101 | 10 | **4 %** |
| Igname | 227 | 145 | 259 | 114 % |
| Ananas | 183 | 133 | **461** | **252 %** |
| Plantain | 120 | 147 | 247 | **206 %** |
| Autres fruits | 102 | 311 | 8 | 8 % |

**LA CAUSE COMMUNE — les rendements.** Agreste donne production ET surface, donc un rendement
territorial observé. Confronté au nôtre :

| | rdt Agreste | rdt modèle | | | rdt Agreste | rdt modèle |
|---|---|---|---|---|---|---|
| Ananas | 12,3 t/ha | **34,0** | | Agrumes | 5,2 | **20,0** |
| Plantain | 9,0 | **26,0** | | Igname | 10,0 | 17,8 |
| Maraîchage | 10,8 | **43,9** | | Vergers | 6,4 | 14,5 |
| | | | | **Melon** | 19,9 | **20,0** ✓ |

Une part de l'écart est légitime — Agreste moyenne tous les producteurs, nos `Rdt_Cult`
décrivent des itinéraires techniques spécifiés — mais un facteur 3 à 4 ne s'explique pas par
cela seul, et le melon, lui, tombe juste. **Conséquence directe : la marge de ces cultures est
mécaniquement surestimée, donc le modèle en couvre l'île dès qu'aucun débouché ne les borne.**
C'est la cause commune du plantain (2026-07-27), de l'ananas et de l'igname. Les rendements
viennent de `Rdt_Cult` et correspondent à la Table 1 de l'article : **sous mandat de parité on
n'y touche pas**, mais ils expliquent *pourquoi* des plafonds de marché sont nécessaires — ce
ne sont pas des béquilles, ils compensent une productivité surévaluée en amont.

**POURQUOI L'ARBORICULTURE DISPARAÎT (−394 ha, le plus gros écart restant).** Pas l'éligibilité :
`VE_BTGT` est possible sur 11 060 parcelles et `AG` sur 3 154. C'est le **rendement horaire** —
canne mécanisée 179-204 €/h, ananas paillé 33, plantain 17,3, igname 14,7, maraîchage 13,6,
**vergers 11,0 et agrumes 11,1**. Les fruitiers sont le pire €/h de toutes les cultures
intensives : sous plafond de main d'œuvre ils sortent les premiers. Sur les 405 ha
d'arboriculture observée perdus, 137 vont à mieux, 102 à moins bon **dont 99 ha bloqués faute
d'heures** — mécanisme de couplage identique à celui de la prairie. À noter : **136 ha d'anciens
vergers partent en prairie**, effet de bord du plancher activé la veille, qui se sert en partie
sur les terres arboricoles.

**L'ANANAS est concentré sur `AN_PA`** (430 des 461 ha), la variante paillage plastique à
16 363 €/ha et 33 €/h — meilleur rendement horaire de toutes les cultures intensives. Elle est
plantée chez des **bananiers (137 ha), canniers diversifiés (108) et canniers spécialisés
(106)**, presque nulle part chez des arboriculteurs : 430 ha d'ananas intensif surgissant chez
des canniers est en soi un signal d'implausibilité.

**TRACTABILITÉ — le modèle a atteint sa limite, et c'est PROUVÉ.** Les deux leviers testés
échouent de la même façon : le solve tape la limite d'une heure et rend un incumbent incohérent.

| | objectif incumbent (1 h) | canne | banane |
|---|---|---|---|
| `output_3` (référence) | 81,22 M€ | 12 782 | 2 047 |
| + plafond ananas 7 000 t | 74,26 M€ | 12 340 | 1 725 |
| + plancher arboricole 200 ha | 76,46 M€ | 12 361 | 1 741 |

Une contrainte sur l'ananas ou les vergers n'a aucune raison de faire reculer la canne et la
banane : signature classique d'un branch-and-bound perdu. **Démonstration formelle** (script de
réparation, sans solve) : en partant de l'allocation d'`output_3` et en basculant vers le
meilleur fruitier éligible les parcelles où cela coûte le moins — en respectant le plafond de
main d'œuvre ferme par ferme et sans toucher aux cultures déjà contraintes (prairie sous
plancher, jachère et banane liées par `Eq_BA_JA`, plantain sous plafond) — on obtient une
solution **faisable pour toutes les contraintes** valant :

| plancher | solution réparée (faisable) | incumbent HiGHS | coût réel du levier |
|---|---|---|---|
| 200 ha | **80,91 M€** | 76,46 M€ | **0,39 %** de l'objectif |
| 335 ha | **80,26 M€** | (non convergé) | **1,19 %** |

Une solution construite en quelques secondes bat de **4,45 M€ (5,5 %)** ce que HiGHS trouve en
une heure. **L'incumbent est donc prouvablement sous-optimal, ce n'est plus une présomption.**
Corollaire : le plancher arboricole coûte en réalité ~1 % d'objectif, du même ordre que le
plafond plantain (3,7 %) et le plancher de prairie (0,7 %) — **le levier est bon marché, c'est
le solveur qui échoue**. Aucun run portant ces contraintes n'est exploitable en l'état : je n'en
ai donc adopté aucune. Le déblocage est un **warm start**, et l'heuristique de réparation
ci-dessus en fournit un directement. Cf. `TODO.md`.

**LEVIERS ÉCARTÉS, avec la raison.** *Igname* : 259 ha simulés contre 227 attestés (114 %), et le
plafond de l'auteur (4 600 t) mordrait juste au niveau produit (4 604 t) — gain nul. *Melon* :
sous-planté, un plafond n'y peut rien ; l'article échoue aussi à 100 % sur cette culture, pour
une raison hors modèle (terres louées à un exportateur). *Jachère* (418 contre 621 ha) : aucune
source externe.

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

**Chiffré le 2026-07-27 : la représentante est souvent une culture que le modèle lui-même
interdirait sur la parcelle qu'elle représente.** Part de la surface observée où la
représentante est éligible : **canne 31 %** (`CS_NGT_NISM` est le système du Nord
Grande-Terre, cantonné à trois communes, et vaut pourtant les 12 813 ha de canne du
territoire), maraîchage 61 % (`MA_ROTA` exige l'irrigation), plantain 63 %, banane export
69 %, igname 71 %, vergers 46 %, agrumes 48 %. Seules prairie, melon et jachère sont à 100 %.
Deux effets : (a) l'économie de la référence est valorisée par des systèmes techniques
impossibles là où ils sont comptés — visible au fait que le central sort par le haut de la
fourchette des variantes éligibles sur ventes, revenu, heures, azote, GES, IFT ; (b) le
plafond de main d'œuvre hérite du même biais. Table complète :
`outputs/reference_2017/csv/reference_representative_eligibility.csv`. C'est l'argument
chiffré derrière l'entrée « cultures représentantes conscientes de la région » de `TODO.md`.
_2026-07-27._

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
