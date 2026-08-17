# Audit du corpus

Genere par `memoire/audit_corpus.py`. Ne pas editer a la main.

## Inventaire

- **490 items** dont 455 factuels et 35 axes reflexifs
- **1267 arcs** poses
- 7 branches coupees documentees

| statut | items |   | type | items |
|---|---:|---|---|---:|
| `retenu` | 349 |  | `choix` | 115 |
| `ouvert` | 41 |  | `resultat` | 87 |
| `ecarte` | 24 |  | `methode` | 63 |
| `erreur-a-posteriori` | 22 |  | `piege` | 56 |
| `differe` | 19 |  | `perspective` | 39 |
|  |  |  | `donnee` | 35 |
|  |  |  | `erreur` | 29 |
|  |  |  | `organisation` | 19 |
|  |  |  | `notion` | 8 |
|  |  |  | `reflexivite` | 4 |

### Charge par destination

| destination | items |
|---|---:|
| `note` | 195 |
| `oral` | 130 |
| `ch3` | 106 |
| `ch4` | 100 |
| `ch2` | 98 |
| `article` | 91 |
| `ch5` | 90 |
| `annexeE` | 62 |
| `annexeA` | 40 |
| `annexeB` | 37 |
| `ch6` | 33 |
| `annexeC` | 25 |
| `annexeD` | 21 |
| `ch1` | 18 |
| `ch0` | 8 |
| `annexeF` | 6 |

## REGLE 1 — choix retenus sans `parce-que` — 1

Portee : les items DECIDES (`choix`, `methode`, `organisation`, `perspective`). Un fait ne se justifie pas, il se source. Un choix retenu sans `parce-que` est, litteralement, un choix non justifie : soit on lui trouve son parent, soit on le declare `racine: true` en assumant que c'est un axiome.

- `MET-32` (95-methode-organisation.yaml) — Le code est en ANGLAIS, la documentation et les commentaires en FRANÇAIS

## REGLE 1 bis — axiomes declares — 2

Ce que le stage a pose sans le deduire de rien. La liste doit rester courte : c'est la surface d'attaque du memoire.

- `DON-50` — `data/` est GITIGNORÉ — le code échoue sur un clone frais tant que les fichiers ne sont pas là
- `MET-01` — MESURER AVANT DE CONCLURE — la règle que le stage s'est donnée, et qui a renversé quatre verdicts

## REGLE 2 — branches ecartees sans `mesure-par` — 0

Un ecart sans mesure est une opinion.

Aucun.

## REGLE 2 bis — ecarts assumes sur argument, sans mesure — 6

Declares via `sans-mesure:`. Ce sont des positions defendables, pas des trous : chacune doit pouvoir etre soutenue a l'oral telle quelle.

- `CTX-B1` — ⚠ CE N'EST PAS UNE BRANCHE COUPÉE, C'EST UNE BRANCHE JAMAIS OUVERTE — et le dire ainsi est le seul traitement honnête. La bifurcation n'a jamais été posée expli
- `ARCH-B1` — Le critère de la décision n'est pas mesurable par un solve : c'est la lisibilité du fichier de configuration par un non-développeur. Cinq règles nommées, chacun
- `SOLV-B2` — Coupée sur une contrainte de destination, pas sur une performance : le modèle doit pouvoir être relancé par un successeur d'une unité INRAE sans démarche de lic
- `DON-B1` — Fermée par le MANDAT, et un mandat ne se mesure pas. `Rdt_Cult` EST la Table 1 de Chopin et al. (2015) : la corriger romprait la parité au point exact où elle s
- `PROS-B1` — Coupée sur un THÉORÈME, et aucun banc d'essai ne l'établirait mieux : une somme pondérée ne peut atteindre que les points du front situés sur son enveloppe conv
- `ART-B1` — L'absence de mesure EST la raison de l'écart, et c'est un cas rare où le vide du champ est le contenu : un « software paper » revendique la réutilisabilité, et 

## REGLE 3 — verdicts renverses sans antecedent — 0

Aucun.

## REGLE 3 bis — verdict anterieur donne en clair — 19

La croyance renversee n'avait pas d'id parce qu'on ne l'avait jamais ecrite. C'est le cas normal, et c'est le materiau du chapitre sur la methode.

- `PORT-05` — « L'inventaire de portage dit l'état du modèle. » Il le disait au moment où il a été écrit, et rien dans le dépôt ne signalait qu'il avait cessé de le
- `PORT-23` — « Le piège des deux ordres de types de sol est identifié et documenté (PORT-22), donc il ne me mordra pas. » Il a mordu, dans le port, sur l'ananas, e
- `PORT-24` — « Les bans chlordécone sont posés à l'envers dans la configuration » — verdict tiré du COMMENTAIRE, qui était faux, alors que le code en dessous était
- `PORT-31` — « `Eq_PN_PIQ_CLD` et `Eq_IG_CLD` sont deux contraintes chlordécone de même nature, donc actives dans le même bloc. » Elles ne le sont pas : le GAMS n'
- `ARCH-60` — « La séparation `core/` ↔ `case_studies/` ↔ `apps/` garantit qu'une même intention n'est écrite qu'une fois. » Elle garantit qu'on ne s'IMPORTE pas de
- `ARCH-61` — « Un fichier qui s'exécute correctement est un fichier correct. » Il tournait depuis le début : c'est l'outillage d'analyse, pas l'interpréteur, qui l
- `ARCH-62` — « Le nom dit ce que la chose est. » `GeometryJoin.coverage` annonçait une part et rendait un effectif ; aucun appelant ne s'en servait, donc rien ne l
- `ARCH-64` — « Toute duplication est un défaut à supprimer. » La moitié de celle-ci en était un et a été fusionnée ; l'autre (`CONFIG_PATH`) a été CONSERVÉE délibé
- `ARCH-68` — « L'ordre d'application de `enable_add` et `set_args` est un détail de plomberie. » C'est une décision de SÉMANTIQUE : une politique POSE une contrain
- `SOLV-22` — « Le plafond ananas et le plancher arboricole coûtent trop cher au modèle : ces contraintes sont bloquées par la MODÉLISATION. » Elles étaient bloquée
- `CAL-53` — « L'écart de calibration vient d'une frontière plate entre prairie et canne, que le gap MIP laisse arbitrer au hasard. » Le verdict n'était pas FAUX —
- `CAL-B10` — Deux verdicts successifs, tous deux miens, tous deux renversés. (1) 23/07 : « le plancher de prairie est rejeté pour intraitabilité » — mauvaise raiso
- `PROS-40` — « Un front ε-contrainte se paramètre sur le réalisé de la configuration de référence. » Il se paramètre sur la borne de sa POLITIQUE HÔTE : sous P8, c
- `PROS-60` — « Deux blocs de configuration écrits séparément et corrects séparément composent un scénario faisable. » Les planchers vivriers réclamaient 6 222 537 
- `IND-41` — « Un score composite normalisé indicateur par indicateur traite tous les critères équitablement. » Il traite équitablement les COLONNES, pas les enjeu
- `IND-71` — « Documenter un piège suffit à s'en prémunir. » Le piège des deux registres a été commis DANS la spec qui le documente, par son auteur, et corrigé en 
- `MET-14` — « Une documentation tenue à jour avec discipline reste juste. » La discipline a tenu partout sauf sur deux lignes, pendant trois semaines, dans le doc
- `MET-31` — « Commenter abondamment rend un code plus sûr. » Un commentaire qui reformule un COMMENT est vérifiable, donc destiné à dériver, et il est cru sur par
- `MET-64` — « Les chiffres du mémoire ne peuvent pas dériver, puisqu'ils sont GÉNÉRÉS depuis les `recap.json` des runs. » Ils le sont presque tous. `mesChecksums`

## Forme — 0

Aucun.

## Arcs pendants — 0

Un arc qui pointe vers un id inexistant. C'est toujours une faute : soit la cible reste a ecrire, soit la reference est fausse.

Aucun.

## Symetrie parce-que / justifie — 443 arcs completes

**Ce n'est pas une liste de defauts.** Le corpus est saisi en ne posant qu'un sens de l'arc (celui qui vient naturellement a l'ecriture) ; le script pose l'autre. Les .yaml restent volontairement asymetriques — les tenir a jour dans les deux sens a la main produirait des incoherences sans rien ajouter, puisque l'information est la meme.

## Macros de chiffre inconnues — 0

Aucun.

## Couverture des chapitres — 9 manquants

Items destines a un chapitre : 67 controlables (ils portent un chiffre), 329 incontrolables automatiquement. **58 couverts.**

| item | chapitre | titre |
|---|---|---|
| `SOLV-20` | ch4 | Un solve arrêté à la limite de temps rend un incumbent PROUVABLEMENT f |
| `SOLV-40` | ch5 | Les 25 variantes maraîchères « Karusmart » sont identiques au bit près |
| `SOLV-73` | ch5 | Un run réduit peut mesurer un gain qui n'existe pas à pleine échelle |
| `CAL-95` | ch5 | LE CENTRAL SORT DE LA FOURCHETTE PAR LE HAUT — et c'est le résultat le |
| `PROS-31` | ch4 | RÉSULTAT CENTRAL — la marge brute varie en SENS INVERSE du plafond de  |
| `PROS-31` | ch6 | RÉSULTAT CENTRAL — la marge brute varie en SENS INVERSE du plafond de  |
| `PROS-41` | ch5 | Une politique peut être HORS D'ATTEINTE sans être infaisable — l'axe P |
| `PERSP-30` | ch6 | CHOISIR LA REPRÉSENTANTE PAR PARCELLE — le meilleur rapport qualité /  |
| `ART-36` | ch5 | Preuve 6 — des activités symétriques rendent une contrainte de politiq |

## Macros definies et jamais citees — 417

Chaque macro non citee est un chiffre calcule pour rien, ou une place qui reste a ecrire dans le .tex.

`\calibBcSeulAzote`, `\calibBcSeulAzoteHa`, `\calibBcSeulCellulesOk`, `\calibBcSeulCulturesTotal`, `\calibBcSeulDuree`, `\calibBcSeulEau`, `\calibBcSeulEtp`, `\calibBcSeulFermes`, `\calibBcSeulFermesOk`, `\calibBcSeulFermesOkPct`, `\calibBcSeulFermesPadMediane`, `\calibBcSeulFermesPadMoyenne`, `\calibBcSeulFermesTotal`, `\calibBcSeulGes`, `\calibBcSeulIft`, `\calibBcSeulMarge`, `\calibBcSeulMargeM`, `\calibBcSeulObjectif`, `\calibBcSeulParcellesActives`, `\calibBcSeulProduction`, `\calibBcSeulRegionsOk`, `\calibBcSeulRegionsPadHorsMin`, `\calibBcSeulRegionsPadMax`, `\calibBcSeulRegionsPadMin`, `\calibBcSeulRegionsPadOkMax`, `\calibBcSeulRegionsTotal`, `\calibBcSeulRevenuNet`, `\calibBcSeulSubvention`, `\calibBcSeulSubventionM`, `\calibBcSeulSurfaceHa`, `\calibPariteAzote`, `\calibPariteAzoteHa`, `\calibPariteCellulesOk`, `\calibPariteDuree`, `\calibPariteEau`, `\calibPariteEtp`, `\calibPariteFermes`, `\calibPariteFermesOk`, `\calibPariteFermesOkPct`, `\calibPariteFermesPadMediane`, `\calibPariteFermesPadMoyenne`, `\calibPariteFermesTotal`, `\calibPariteGes`, `\calibPariteIft`, `\calibPariteMarge`, `\calibPariteMargeM`, `\calibPariteObjectif`, `\calibPariteParcellesActives`, `\calibPariteProduction`, `\calibPariteRegionsOk`, `\calibPariteRegionsPadHorsMin`, `\calibPariteRegionsPadMax`, `\calibPariteRegionsPadMin`, `\calibPariteRegionsPadOkMax`, `\calibPariteRegionsTotal`, `\calibPariteRevenuNet`, `\calibPariteSubvention`, `\calibPariteSubventionM`, `\calibPariteSurfaceHa`, `\calibRetenuAzote`, `\calibRetenuAzoteHa`, `\calibRetenuCellulesOk`, `\calibRetenuDuree`, `\calibRetenuEau`, `\calibRetenuEtp`, `\calibRetenuFermes`, `\calibRetenuFermesOk`, `\calibRetenuFermesTotal`, `\calibRetenuGes`, `\calibRetenuIft`, `\calibRetenuMarge`, `\calibRetenuMargeM`, `\calibRetenuObjectif`, `\calibRetenuParcellesActives`, `\calibRetenuProduction`, `\calibRetenuRevenuNet`, `\calibRetenuSubvention`, `\calibRetenuSubventionM`, `\calibRetenuSurfaceHa`, `\frontazoteHuitObjBas`, `\frontazoteHuitObjHaut`, `\frontazoteHuitPenteBas`, `\frontazoteHuitPenteExacte`, `\frontazoteHuitPenteHaut`, `\frontazoteHuitPlateau`, `\frontazoteHuitSeuilBas`, `\frontazoteHuitSeuilHaut`, `\frontazoteHuitTemoin`, `\frontazoteHuitcinqEtp`, `\frontazoteHuitcinqMargeM`, `\frontazoteHuitcinqObj`, `\frontazoteHuitcinqObjM`, `\frontazoteHuitcinqSeuil`, `\frontazoteHuitdeuxEtp`, `\frontazoteHuitdeuxMargeM`, `\frontazoteHuitdeuxObj`, `\frontazoteHuitdeuxObjM`, `\frontazoteHuitdeuxSeuil`, `\frontazoteHuitquatreEtp`, `\frontazoteHuitquatreMargeM`, `\frontazoteHuitquatreObj`, `\frontazoteHuitquatreObjM`, `\frontazoteHuitquatreSeuil`, `\frontazoteHuittroisEtp`, `\frontazoteHuittroisMargeM`, `\frontazoteHuittroisObj`, `\frontazoteHuittroisObjM`, `\frontazoteHuittroisSeuil`, `\frontazoteHuitunEtp`, `\frontazoteHuitunMargeM`, `\frontazoteHuitunObj`, `\frontazoteHuitunObjM`, `\frontazoteHuitunSeuil`, `\frontazoteRefObjBas`, `\frontazoteRefObjHaut`, `\frontazoteRefPenteBas`, `\frontazoteRefPenteExacte`, `\frontazoteRefPenteHaut`, `\frontazoteRefPlateau`, `\frontazoteRefSeuilBas`, `\frontazoteRefSeuilHaut`, `\frontazoteRefTemoin`, `\frontazoteRefcinqEtp`, `\frontazoteRefcinqMargeM`, `\frontazoteRefcinqObj`, `\frontazoteRefcinqObjM`, `\frontazoteRefcinqSeuil`, `\frontazoteRefdeuxEtp`, `\frontazoteRefdeuxMargeM`, `\frontazoteRefdeuxObj`, `\frontazoteRefdeuxObjM`, `\frontazoteRefdeuxSeuil`, `\frontazoteRefquatreEtp`, `\frontazoteRefquatreMargeM`, `\frontazoteRefquatreObj`, `\frontazoteRefquatreObjM`, `\frontazoteRefquatreSeuil`, `\frontazoteReftroisEtp`, `\frontazoteReftroisMargeM`, `\frontazoteReftroisObj`, `\frontazoteReftroisObjM`, `\frontazoteReftroisSeuil`, `\frontazoteRefunEtp`, `\frontazoteRefunMargeM`, `\frontazoteRefunObj`, `\frontazoteRefunObjM`, `\frontazoteRefunSeuil`, `\frontsubvQuatreDualBas`, `\frontsubvQuatrePente`, `\frontsubvQuatrePenteBas`, `\frontsubvQuatrePenteExacte`, `\frontsubvQuatrePenteHaut`, `\frontsubvQuatrePlateau`, `\frontsubvQuatrePoints`, `\frontsubvQuatreProuves`, `\frontsubvQuatreSeuilBas`, `\frontsubvQuatrecinqEtp`, `\frontsubvQuatrecinqMargeM`, `\frontsubvQuatrecinqObj`, `\frontsubvQuatrecinqObjM`, `\frontsubvQuatrecinqSeuil`, `\frontsubvQuatredeuxEtp`, `\frontsubvQuatredeuxMargeM`, `\frontsubvQuatredeuxObj`, `\frontsubvQuatredeuxObjM`, `\frontsubvQuatredeuxSeuil`, `\frontsubvQuatrequatreEtp`, `\frontsubvQuatrequatreMargeM`, `\frontsubvQuatrequatreObj`, `\frontsubvQuatrequatreObjM`, `\frontsubvQuatrequatreSeuil`, `\frontsubvQuatreseptEtp`, `\frontsubvQuatreseptMargeM`, `\frontsubvQuatreseptObj`, `\frontsubvQuatreseptObjM`, `\frontsubvQuatreseptSeuil`, `\frontsubvQuatresixEtp`, `\frontsubvQuatresixMargeM`, `\frontsubvQuatresixObj`, `\frontsubvQuatresixObjM`, `\frontsubvQuatresixSeuil`, `\frontsubvQuatretroisEtp`, `\frontsubvQuatretroisMargeM`, `\frontsubvQuatretroisObj`, `\frontsubvQuatretroisObjM`, `\frontsubvQuatretroisSeuil`, `\frontsubvQuatreunEtp`, `\frontsubvQuatreunMargeM`, `\frontsubvQuatreunObj`, `\frontsubvQuatreunObjM`, `\grilleMeilleureFneuf`, `\grilleMeilleureFsix`, `\grilleMeilleureFzero`, `\grilleMeilleureNetFneuf`, `\grilleMeilleureNetFsix`, `\grilleMeilleureNetFzero`, `\mesForcagesVus`, `\mesHuitBorneLp`, `\mesHuitEcartPct`, `\mesPdixViolationsP`, `\mesPlancherPad`, `\mesPolitiquesVues`, `\mesPrairieExogene`, `\mesPrairieHautParcelles`, `\mesPrairieHautSurface`, `\mesPrairieHautTypes`, `\mesPrairieRpg`, `\mesSauAgreste`, `\obsHaAG`, `\obsHaAN`, `\obsHaIG`, `\obsHaJA`, `\obsHaMA`, `\obsHaME`, `\obsHaVE`, `\obsParcellesCultivees`, `\obsReclassementNc`, `\obsSurfaceNonCultivee`, `\obsSurfaceTotale`, `\padBcSeulAG`, `\padBcSeulAN`, `\padBcSeulBA`, `\padBcSeulBC`, `\padBcSeulCS`, `\padBcSeulIG`, `\padBcSeulJA`, `\padBcSeulMA`, `\padBcSeulME`, `\padBcSeulPN`, `\padBcSeulVE`, `\padPariteAG`, `\padPariteAN`, `\padPariteBA`, `\padPariteBC`, `\padPariteCS`, `\padPariteIG`, `\padPariteJA`, `\padPariteMA`, `\padPariteME`, `\padParitePN`, `\padPariteVE`, `\padRetenuAG`, `\padRetenuAN`, `\padRetenuBA`, `\padRetenuBC`, `\padRetenuIG`, `\padRetenuJA`, `\padRetenuMA`, `\padRetenuME`, `\padRetenuVE`, `\prosEcartFzeroApres`, `\prosEcartFzeroRepris`, `\prosPcinqAzote`, `\prosPcinqDuree`, `\prosPcinqEau`, `\prosPcinqEtp`, `\prosPcinqFlag`, `\prosPcinqGes`, `\prosPcinqHhi`, `\prosPcinqIft`, `\prosPcinqMarge`, `\prosPcinqObjectif`, `\prosPcinqObjectifM`, `\prosPcinqProuve`, `\prosPcinqSubvention`, `\prosPcinqSurfaceHa`, `\prosPhuitAzote`, `\prosPhuitDuree`, `\prosPhuitEau`, `\prosPhuitEtp`, `\prosPhuitFlag`, `\prosPhuitGes`, `\prosPhuitHhi`, `\prosPhuitIft`, `\prosPhuitMarge`, `\prosPhuitObjectif`, `\prosPhuitObjectifM`, `\prosPhuitProuve`, `\prosPhuitSubvention`, `\prosPhuitSurfaceHa`, `\prosPneufAzote`, `\prosPneufDuree`, `\prosPneufEau`, `\prosPneufEtp`, `\prosPneufFlag`, `\prosPneufGes`, `\prosPneufHhi`, `\prosPneufIft`, `\prosPneufMarge`, `\prosPneufObjectif`, `\prosPneufObjectifM`, `\prosPneufProuve`, `\prosPneufSubvention`, `\prosPneufSurfaceHa`, `\prosPquatreAzote`, `\prosPquatreDuree`, `\prosPquatreEau`, `\prosPquatreEtp`, `\prosPquatreFlag`, `\prosPquatreGes`, `\prosPquatreHhi`, `\prosPquatreIft`, `\prosPquatreMarge`, `\prosPquatreObjectif`, `\prosPquatreObjectifM`, `\prosPquatreProuve`, `\prosPquatreSubvention`, `\prosPquatreSurfaceHa`, `\prosPseptAzote`, `\prosPseptDuree`, `\prosPseptEau`, `\prosPseptEtp`, `\prosPseptFlag`, `\prosPseptGes`, `\prosPseptHhi`, `\prosPseptIft`, `\prosPseptMarge`, `\prosPseptObjectif`, `\prosPseptObjectifM`, `\prosPseptProuve`, `\prosPseptSubvention`, `\prosPseptSurfaceHa`, `\prosPsixAzote`, `\prosPsixDuree`, `\prosPsixEau`, `\prosPsixEtp`, `\prosPsixFlag`, `\prosPsixGes`, `\prosPsixHhi`, `\prosPsixIft`, `\prosPsixMarge`, `\prosPsixObjectif`, `\prosPsixObjectifM`, `\prosPsixProuve`, `\prosPsixSubvention`, `\prosPsixSurfaceHa`, `\prosPunAzote`, `\prosPunDuree`, `\prosPunEau`, `\prosPunEtp`, `\prosPunFlag`, `\prosPunGes`, `\prosPunHhi`, `\prosPunIft`, `\prosPunMarge`, `\prosPunObjectif`, `\prosPunObjectifM`, `\prosPunProuve`, `\prosPunSubvention`, `\prosPunSurfaceHa`, `\rdtAgresteAG`, `\rdtAgresteAN`, `\rdtAgresteBC`, `\rdtAgresteIG`, `\rdtAgresteMA`, `\rdtAgresteME`, `\rdtAgresteVE`, `\rdtModeleAG`, `\rdtModeleAN`, `\rdtModeleBC`, `\rdtModeleIG`, `\rdtModeleMA`, `\rdtModeleME`, `\rdtModeleVE`, `\rdtRapportAG`, `\rdtRapportAN`, `\rdtRapportBC`, `\rdtRapportIG`, `\rdtRapportMA`, `\rdtRapportME`, `\rdtRapportVE`, `\reallocReallocBudgetLignes`, `\regretNetPhuitFneuf`, `\regretNetPhuitFzero`, `\regretNetPneufFneuf`, `\regretNetPneufFzero`, `\regretNetPquatreFneuf`, `\regretNetPquatreFsix`, `\regretNetPquatreFzero`, `\regretNetPseptFsix`, `\regretNetPseptFzero`, `\regretNetPsixFsix`, `\regretNetPsixFzero`, `\regretPneufFzero`, `\regretPquatreFneuf`, `\regretPsixFsix`, `\simBcSeulAG`, `\simBcSeulAN`, `\simBcSeulBA`, `\simBcSeulBC`, `\simBcSeulCS`, `\simBcSeulIG`, `\simBcSeulJA`, `\simBcSeulMA`, `\simBcSeulME`, `\simBcSeulPN`, `\simBcSeulVE`, `\simPariteAG`, `\simPariteAN`, `\simPariteBA`, `\simPariteCS`, `\simPariteIG`, `\simPariteJA`, `\simPariteMA`, `\simPariteME`, `\simParitePN`, `\simPariteVE`, `\simRetenuAG`, `\simRetenuAN`, `\simRetenuBA`, `\simRetenuBC`, `\simRetenuIG`, `\simRetenuJA`, `\simRetenuMA`, `\simRetenuME`, `\simRetenuPN`, `\simRetenuVE`

## Topologie

- 32 racines (aucun `parce-que`)
- 213 feuilles (aucun `justifie`)
- 0 items isoles (aucun arc, dans aucun sens)
- 0 cycles

Les douze chaines les plus profondes — ce sont les fils narratifs du memoire :

| item | profondeur | titre |
|---|---:|---|
| `CTX-01` | 20 | Un système agricole structuré par deux filières d'exportation sur un t |
| `CTX-02` | 19 | ~80 % des produits alimentaires consommés dans les DOM sont importés ; |
| `CTX-10` | 18 | CALALOU (2021-2025) est l'ancêtre direct : « de la fourchette à la fou |
| `CTX-20` | 17 | La commande — concevoir des scénarios agro-économiques de développemen |
| `CTX-21` | 16 | La lettre de mission prévoyait des ENQUÊTES de terrain et l'acquisitio |
| `SOLV-B1` | 16 | BRANCHE COUPÉE — rester en GAMS et n'ajouter qu'une couche de scripts |
| `CTX-11` | 15 | CALALOU a utilisé MOSAICA (version GAMS) dans son WP4, alimenté par le |
| `CTX-22` | 15 | Le stage a été réorienté : reconstruire l'outil avant de pouvoir simul |
| `CTX-B1` | 14 | BRANCHE COUPÉE — reprendre le pipeline CALALOU (scénarios Reloc / Nutr |
| `ARCH-01` | 14 | La formulation ne mentionne la Guadeloupe nulle part — elle parle de p |
| `SOLV-06` | 13 | Pyomo + HiGHS (`appsi_highs`) plutôt que GAMS, Gurobi ou CPLEX |
| `PORT-02` | 12 | La justification du mandat — sans lui, tout désaccord ultérieur entre  |

## Les branches coupees — 7

C'est le tableau de la demonstration : ce qui a ete retenu, ce que cela a ferme, et ce qui a tranche.

| retenu | ferme | mesure par |
|---|---|---|
| `PORT-01` Mandat de parité — reproduire le comportement RÉ | `PORT-B1` BRANCHE COUPÉE — un port « amélioré » qui corrig | `PORT-20` |
| `ARCH-32` Cinq règles catégorielles de `core/` sont des ca | `ARCH-B1` BRANCHE COUPÉE — factoriser les cinq règles caté | **aucune** |
| `SOLV-06` Pyomo + HiGHS (`appsi_highs`) plutôt que GAMS, G | `SOLV-B1` BRANCHE COUPÉE — rester en GAMS et n'ajouter qu' | `PORT-10`, `PORT-20`, `PORT-22` |
| `SOLV-06` Pyomo + HiGHS (`appsi_highs`) plutôt que GAMS, G | `SOLV-B2` BRANCHE COUPÉE — un solveur commercial (Gurobi,  | **aucune** |
| `PROS-10` L'ε-contrainte plutôt qu'une somme pondérée : on | `PROS-B1` BRANCHE COUPÉE — agréger marge et azote dans une | **aucune** |
| `MET-32` Le code est en ANGLAIS, la documentation et les  | `MET-B2` BRANCHE COUPÉE (pour l'instant) — tout basculer  | `MET-33` |
| `ART-01` Le portage lui-même n'est pas un résultat publia | `ART-B1` BRANCHE COUPÉE — « MOSAICA-Py : une réimplémenta | **aucune** |
