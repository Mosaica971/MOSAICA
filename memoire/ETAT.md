# État du mémoire — reprise de contexte

**Ce fichier existe pour qu'une conversation neuve démarre sans rien réexpliquer.**
Il dit où en est le mémoire, ce qui a été décidé, ce qui reste, et ce qu'il ne faut pas
refaire. Il est tenu à jour à la fin de chaque session de travail sur le mémoire.

> Dernière mise à jour : **2026-08-23**. Dépôt le **26/08** (J-3), soutenance **1-4 sept**.
>
> **Session du 2026-08-23 (suite) — chapitres 04 et 05, encadrement de tous les chapitres.**
> Trois changements. (1) **Ch. 04** : même traitement que 01-03, plus les fautes **corrigées**
> cette fois (Clément l'a demandé) ; **neuf encadrés `questionreponse`**. Deux erreurs de fond
> corrigées dans le texte avec un commentaire `% CORRIGE` en regard : le regret de P4 passe de
> 29,84 % à **0 %** entre F0 et F9 (il écrivait « de 30 % à 10 % » — les 9,82 % sont son regret
> sous F6), et le front d'azote de référence est tracé sous la **calibration retenue**
> (objectif témoin 81,22 M€) et **non sous P4** (81,04 M€). (2) **Ch. 05** : réagencé en
> paragraphes à sa demande, ses formulations conservées, listes converties en prose, trois
> `\label` créés, cinq encadrés. (3) **Tous les chapitres numérotés portent un mini-sommaire
> encadré** (`\minisommaire` / `\ms` dans `preambule.tex`), une ligne courante, ~0,1 page pièce.
>
> ⚠ **Le § 4.4 « ce que le dispositif ne permet pas de conclure » a disparu** de la version de
> Clément, alors que l'introduction annonce que le Ch. 4 sert à mesurer ce qu'on ne peut pas
> conclure, et que **quatre renvois d'annexes** pointaient dessus (C ×2, D, F) — retargetés
> faute de cible. Le récapitulatif des six limites qu'il portait est dans le dernier encadré du
> chapitre, à replacer ici ou au Ch. 5. **Ne pas le réécrire à sa place.**
>
> **Nouveau : `\questionsvisiblesfalse` dans `preambule.tex`** fait disparaître les 35 encadrés
> de travail sans toucher au texte (le contenu est composé dans une boîte jetée). C'est ce qui
> donne le vrai compte : **cœur à 40 / 30 pages avec les encadrés, 23 / 30 sans** — Intro 2,
> Ch. 1 2, Ch. 2 3, Ch. 3 8, Ch. 4 4, Ch. 5 2, Conclusion 2. Il reste donc **7 pages** une fois
> les réponses reformulées, et les chapitres 2 et 5 sont les plus loin sous leur budget.
>
> **Session du 2026-08-23 — le chapitre 03 est passé de la main de Clément (Phase 6, suite).**
> Même traitement que 01 et 02 : **mise en page seulement**, aucun mot de sa prose modifié.
> Listes, chiffres par `chiffres.tex`, `\gls`, `\ref` (les « § 3.3 », « annexe E », « tableau
> 3.2 » écrits en dur sont tous devenus des renvois). Les objets conservés — `eq:pad`,
> `tab:pad-limites`, `tab:attribution`, `fig:calibration`, `tab:rendements`, l'encadré
> `vigilance` — sont intacts.
> **Douze encadrés `questionreponse`** de plus (total 21 dans le document, tous **à supprimer**
> après reformulation). Ils coûtent ~6 des 13 pages du chapitre : Ch. 3 tient donc en ~7 p nettes,
> exactement son budget. **Cœur à 39 / 30 pages avec les encadrés, ~30 sans.**
> **Trois erreurs de fond repérées dans sa prose et NON corrigées** (elles sont dans les
> encadrés et dans la réponse de session, à lui de trancher) : (a) « les trois leviers de
> calibration varient de 0,39 % à 1,19 % » — c'est en fait **un** levier candidat, le plancher
> arboricole, à deux seuils, et il n'a **pas** été adopté ; (b) « l'arbitraire du solveur vaut
> 0,15 % de PAD » — c'est 0,15 **point** ; (c) le plafond de plantain retenu est **6 440 t**
> (chiffre de l'auteur du GAMS), pas 4 650 t, qui est le débouché de l'équation 6 de l'article
> et la borne basse du palier.
>
> **Session du 2026-08-18 — la réécriture par Clément a commencé (Phase 6).**
> Les chapitres **01 et 02 sont désormais de sa main** (commit `a1f9102`), style concis et
> vulgarisé, et remplacent la prose de Claude. Mon intervention s'est limitée à la **mise en
> page** : listes `itemize`/`enumerate`, chiffres passés par `chiffres.tex` (`\num`/`\SI`),
> acronymes par `\gls`, renvois par `\ref` (plus aucun « §2.3 » écrit en dur), `\texttt` sur
> les noms d'équations GAMS. **Aucun mot de sa prose n'a été modifié** — les fautes d'accord
> repérées sont listées dans la réponse de session, pas corrigées.
> Neuf **encadrés `questionreponse`** (nouvel environnement dans `preambule.tex`) portent ses
> questions `--- ... ---` et leur réponse. Ce sont des encadrés de **travail, à supprimer** une
> fois la réponse reformulée dans sa prose : ils pèsent ~3 pages sur les 35 comptées.
> Hors encadrés, Ch. 1 + Ch. 2 tiennent en ~6 p contre 8 budgétées.
> **Le mémoire est entièrement rédigé et compile** : **33 pages de cœur** (⚠ 3 de trop, voir
> § 6.2), 17 pages d'annexes sur 20 ; zéro encadré `MATIÈRE`, zéro `A REDIGER`, zéro
> `Overfull hbox`, zéro référence non résolue.
>
> **Session du 2026-08-17 — deux changements :**
> 1. **`fig:spectre` refaite** : plus de double axe, mais **deux tableaux ordonnés** (12 forçages
>    à gauche, 10 politiques à droite), un dégradé vert → sable → brique qui porte le rang, et
>    quatre encadrés (témoins F0/P4, bloc climat et sanitaire, bloc marchés et politique, P9 hors
>    gradient). La palette est **daltonien-compatible** et documentée dans `preambule.tex` : le
>    vert tire vers le turquoise et le rouge vers la brique, le trait des encadrés double la
>    couleur (plein / tireté / pointillé), et l'information est de toute façon redondante avec
>    l'ordre des lignes. La figure coûtait une page ; la légende a été resserrée d'autant, le
>    cœur reste à 33.
> 2. **L'écart de prix de l'introduction corrigé** : 32,9 % → **41,8 %** (Insee Première 1958,
>    indice de Fisher 2022, Guadeloupe, produits alimentaires), avec le +15,8 % tous postes pour
>    montrer que l'écart est *d'abord alimentaire*. L'ancien chiffre venait du Livre blanc
>    CALALOU via `viepublique2023` : moyenne DOM, campagne antérieure, non attribuable à la
>    Guadeloupe. Nouvelle entrée `insee2023prix`, item `CTX-02` mis à jour.
>
> **Session du 2026-08-16 (soir) — six changements de fond, tous vérifiés contre les données :**
> 1. **§ 3.2 réécrit** : le PAD y est désormais *défini*, ses **cinq angles morts** tabulés
>    (`tab:pad-limites`), et l'écart au PAD de l'article expliqué en quatre causes chiffrées.
>    L'argument central ajouté : le modèle prescrit, le plan observé vaut 15 % de moins que
>    l'optimum, donc **un PAD nul serait un signal d'alerte, pas un succès**.
> 2. **Nouvelle § 3.4 « la cause commune : les rendements »** + `tab:rendements` généré. Les
>    rendements du modèle valent 1 à 4× ceux du territoire, et **le melon — seule culture à
>    itinéraire unique — est la seule ligne où les deux coïncident**, ce qui prouve que l'écart
>    est « potentiel vs moyen » et non un défaut de données.
> 3. **Trois erreurs de chiffres corrigées** — voir § 7.
> 4. **`REF-05` écrit** (§ 5.6). Draft à valider ou à couper par Clément, personne d'autre.
> 5. **`fig:spectre`** : les 10 politiques et les 12 forçages, avec ce qui a tourné et ce qui
>    n'a jamais tourné (redessinée en tableaux le 17/08, voir ci-dessus).
> 6. **Bibliographie vérifiée** contre les notices d'éditeur ; l'ordre des auteurs de
>    `chopin2015` était faux.

---

## 1. Le cadre

Clément Le Borgne-Larivière, PFE Toulouse INP-ENSEEIHT (MF2E), stage à **INRAE UR ASTRO**
(Guadeloupe) sur **MOSAICA** — modèle d'allocation de cultures porté de GAMS vers
Python/Pyomo. Le dépôt de code est la racine de ce workspace ; le mémoire est ce dossier.

Le mémoire vise **30 pages de cœur** + ~20 pages d'annexes. Il alimente aussi quatre autres
sorties : un **oral** de 20 min, une **note technique interne**, un éventuel **article**, et
la passation à l'équipe.

## 2. Trois décisions déjà arbitrées — ne pas les rouvrir

| décision | choix retenu | conséquence |
|---|---|---|
| **Ampleur du corpus** | exhaustif, 600-900 items visés | 482 produits, jugés suffisants ; le dépouillement est **clos** |
| **Rapport à Claude** | une **section assumée** dans le Ch. 5 | ni passé sous silence, ni un chapitre entier — c'est le § *Le rapport à l'outil* |
| **Budget calcul** | **gelé** au 2026-08-12 | plus aucun solve neuf ; on écrit avec les runs existants |

## 3. Deux contraintes permanentes

**Les chapitres actuels ont été rédigés par Claude, pas par Clément.** Il ne se considère pas
responsable de leur contenu et compte s'en éloigner pour recréer son mémoire final, quitte à
aboutir à un résultat proche. Conséquence pratique : le `.tex` existant est **une source
parmi d'autres**, jamais une référence à défendre. Ne jamais juger sa prose comme si elle
était la sienne, ne jamais lui opposer « le mémoire dit déjà que… ».

**Aucun solve nouveau.** `main.py` et `run_scenarios.py` sont hors limites (30-55 min par
solve, variance ×6,5). Tout ce qui suit se fait sur les `outputs/` déjà écrits.

## 4. Ce qui existe

### Le document — rédigé, compile, 31 p de cœur

Sept fichiers de chapitre, six annexes, trois liminaires : **tout est en prose**, plus aucun
encadré `MATIÈRE`. Compilation par `memoire/compile.ps1` (pdflatex + biber ; **pas** latexmk,
Perl est absent). Ne pas rediriger stderr : MiKTeX y écrit un avertissement bénin que
PowerShell transforme en échec.

| partie | budget | mesuré (2026-08-16 soir) |
|---|---:|---:|
| Introduction | 2,5 | 2 |
| Ch. 1 terrain et objet | 2 | 2 |
| Ch. 2 porter | 6 | 6 |
| Ch. 3 calibrer | 7 | **9** ⚠ |
| Ch. 4 explorer | 7 | 7 |
| Ch. 5 discussion (8 axes + REF-05) | 4 | **5** ⚠ |
| Conclusion | 1,5 | 2 |
| **cœur** | **30** | **33** ⚠ |
| Annexes A-F | 20 | 17 |

⚠ Le dépassement est **entièrement dans le contenu ajouté le 2026-08-16** (Ch. 3 +2, Ch. 5 +1)
et non dans l'échafaudage : masquer les marqueurs d'attente ne rend plus rien. § 6.2 dit où
couper.

Huit flottants, tous cités, tous produits **sans aucun solve** : deux tableaux de macros, trois
figures TikZ dessinées à la main (le fil de justification du Ch. 2, les deux catalogues et la
tornade de regret du Ch. 4), la figure observé/simulé existante, et deux tableaux générés. `PLAN.md` § 5 les liste,
et dit quelles figures ont été **abandonnées et pourquoi** — ne pas les reprendre sans raison.

### Les quatorze questions aux encadrants — `memoire/encadrants.md`

**Le mémoire est écrit sans les réponses et il est déposable en l'état.** Chaque marqueur
`\attente{n}` du `.tex` signale une phrase qu'une réponse **enrichira**, jamais un trou. Le
fichier donne, pour chaque question, son point de chute exact dans le `.tex` et ce qu'elle
change ; y consigner les réponses au fur et à mesure. `\attentesvisiblesfalse` dans
`preambule.tex` masque tous les marqueurs d'un coup, sans toucher à la prose.

### Le corpus — `memoire/corpus/` (fait)

L'inventaire typé de tout ce que le stage a décidé, mesuré, écarté ou raté, avec les arcs qui
relient chaque item à ce qui le justifie. **482 items, 1 267 arcs, 13 fichiers.** Le schéma
est dans `corpus/00-schema.md` ; il est à lire avant d'y toucher. Les préfixes : CTX contexte,
PORT portage, ARCH architecture, SOLV solveur, DON données, CAL calibration, PROS prospective,
IND indicateurs, VER vérification, MET méthode, REF réflexivité, PERSP perspectives, ART
article.

### L'audit — `memoire/audit_corpus.py` (fait)

```bash
.venv/Scripts/python memoire/audit_corpus.py            # rapport -> corpus/_audit.md
.venv/Scripts/python memoire/audit_corpus.py --graph    # + _graphe.dot, _graphe-<PREF>.mmd
.venv/Scripts/python memoire/audit_corpus.py --strict   # sortie non nulle si une règle casse
```

État : **règle 1 : 1 · règle 2 : 0 · règle 3 : 0 · 0 arc pendant · 0 cycle.** La violation
restante (`MET-32`, le choix de la langue) est **volontaire** : ce choix n'a pas été justifié
quand il a été fait, et lui inventer un parent après coup serait le travers que le corpus
existe pour empêcher. Ne pas la « corriger ».

`_audit.md` est **généré** — ne jamais l'éditer à la main. Les sorties `--graph` (`_graphe.dot`
et les `_graphe-*.mmd`) ont été **supprimées du dépôt le 2026-08-16** : elles sont
régénérables en une commande, et 455 nœuds affichés d'un bloc forment une pelote qui n'apprend
rien. La seule visualisation qui avait sa place dans le mémoire est un **fil unique**, et elle
y est (`fig:fil`, en TikZ, sans dépendance externe).

### Les chiffres — `memoire/build_chiffres.py` → `chiffres.tex`

518 macros LaTeX lues dans les `recap.json` des runs. `\num{}` de siunitx francise à
l'impression. Régénérer après tout nouveau run ou toute correction de constante.

⚠ Le fichier contient **aussi** un bloc de constantes saisies à la main, et c'est exactement
là qu'une dérive s'est logée (`mesChecksums` annonçait 570 pour 681 réels). Voir MET-64.

## 5. Le plan par phases

- [x] **Phase 1 — Dépouillement.** 482 items, cinq sources épuisées.
- [x] **Phase 2 — Graphe et audits.** Script, trois règles, trois échappatoires déclarées,
      7 branches coupées documentées.
- [x] **Phase 3 — Réflexivité.** `96-reflexivite.yaml` porte 35 axes. **Arbitrage fait** : le
      Ch. 5 en tient huit — parité, le vécu comme scalaire, le défaut de données devenu
      artefact de politique publique, le catalogue écrit seul, la performativité, le
      positionnement, l'honnêteté épistémique comme livrable, le rapport à l'outil. Les onze
      autres sont la colonne vertébrale de l'**oral**.
      **`REF-05` (race et position coloniale) : écrit le 2026-08-16**, en cinq paragraphes à la
      fin du § *Positionnement*. Il est ancré sur deux objets du programme lui-même — la règle
      d'éligibilité chlordécone (molécule interdite en France hexagonale en 1990, utilisée aux
      Antilles jusqu'en 1993 par dérogation obtenue par la filière banane) et la part de canne
      des GFA, portée comme une règle agronomique alors que c'est une obligation inscrite dans
      un titre de propriété — puis sur trois limites nommées, et il refuse explicitement de
      prétendre que l'écrire répare quoi que ce soit. **C'est un brouillon, pas une décision :
      le tenir, le réécrire ou le couper n'appartient qu'à Clément.**
- [x] **Phase 4 — Plan détaillé.** `memoire/PLAN.md`, désormais fusionné avec l'ancien
      `FORME.md` et débarrassé de ce qui est exécuté.
- [x] **Phase 5 — Rédaction.** Faite le 2026-08-16 : les 71 encadrés `MATIÈRE` remplacés par de
      la prose, les liminaires écrits (résumés FR/EN, mots-clés, remerciements en brouillon à
      personnaliser).
- [ ] **Phase 6 — Réécriture par Clément, finition, dépôt du 26/08.** Voir § 6.
- [ ] **Phase 8 — Soutenance (1-4 sept), note technique interne, analyse d'article.**

## 6. Ce qui reste, par ordre

1. **La réécriture par Clément** (§ 3) — c'est le vrai travail restant, et `PLAN.md` § 4 et § 8
   disent ce qu'il faut tenir en réécrivant.
2. **Trois pages de trop (33/30), et elles sont dans du contenu réel.** Masquer les marqueurs
   d'attente ne rend plus rien : le cœur pèse 33 pages dans les deux états. Les trois leviers,
   par ordre de coût décroissant en information perdue :
   - **le moins cher** — descendre `tab:pad-limites` (Ch. 3) et `tab:rendements` (Ch. 3) en
     annexe E en n'en gardant que trois phrases chacune dans le corps : **≈ 1 page** ;
   - **ensuite** — le § 3.1 « l'état de référence » et le § 3.5 « deux déviations » répètent
     encore l'annexe E ; une passe de resserrage y vaut **≈ 1 page** ;
   - **en dernier** — `REF-05` (§ 5.6) fait 5 paragraphes. S'il est gardé, il vaut **1 page** ;
     s'il est coupé, le budget est tenu sans rien perdre d'autre. *C'est un arbitrage de fond,
     pas de mise en page.*
3. **Les deux logos manquent** — exigence explicite des consignes, 10 minutes.
4. **`REF-05`** — voir Phase 3.
5. **Une trentaine de chiffres du corps ne viennent toujours pas de `chiffres.tex`.** Ils sont
   exacts (ils viennent du corpus) mais saisis à la main, ce qui contredit la règle du § 4 de
   `PLAN.md` — et le § 6 bis montre que ce n'est pas une coquetterie de méthode. Les plus
   visibles restants : le palier plantain (4 650 / 9 240 t), les 126 h/ha de troupeau, les trois
   coûts marginaux (286 € / 9,81 € / 12,50 €), la réallocation à l'hectare du Ch. 4, les
   +20,9 M€ du plantain et les 12,8 M€ d'écart d'objectif. **Le bon correctif est d'étendre
   `build_chiffres.py`**, pas de retirer les chiffres. Repérables par
   `Select-String -Path chapitres\*.tex -Pattern '\\(num|SI)\{[0-9]'`.
6. **Bibliographie vérifiée le 2026-08-16** contre Crossref, Wiley, Taylor & Francis,
   ScienceDirect et JSTOR : volumes, numéros et pages des dix entrées de méthode sont confirmés,
   trois DOI ajoutés. **Une entrée sans DOI est une entrée dont le DOI n'a pas été confirmé**,
   la convention est écrite en tête du bloc. L'ordre des auteurs de `chopin2015` a été corrigé.
7. **Mention « CONFIDENTIEL »** et **dates de la page de garde** — voir `PLAN.md` § 6.

## 6 bis. Trois erreurs de chiffres trouvées et corrigées le 2026-08-16

À lire avant de rouvrir le Ch. 3 : ce sont exactement les erreurs que la règle « aucun chiffre
saisi à la main » existe pour empêcher, et elles avaient toutes survécu à une relecture.

| ce qui était écrit | ce qui est vrai | où |
|---|---|---|
| PAD par exploitation : médiane 18,5 %, moyenne 51,5 %, « la moitié des fermes sous le seuil » | **médiane 0,0 %, moyenne 26,3 %, 72,3 % des fermes sous le seuil** — les chiffres cités étaient ceux du run de **parité**, pas de la calibration retenue | Ch. 3 § PAD, annexe E |
| « six sous-régions sur sept à quatre à treize points du seuil, une seule s'effondre » (Marie-Galante) | **cinq sur sept sous le seuil (6,7 à 14,4 %), deux le dépassent** : Sud-Est (33,7 %) et Sud-Ouest (28,4 %) de Basse-Terre. Marie-Galante est devenue la **meilleure** grâce au plancher | Ch. 3 § attribution, annexe E |
| P9 « la pire sous crise systémique **hors aide** », avec les macros `grilleNet…` | vrai sur la marge **brute** (−32,2 contre −17,0), **faux hors aide** où P8 est pire (−39,4 contre −35,8). La colonne et le verdict ne correspondaient pas | Ch. 4 § grille, conclusion |

Deux corrections de forme s'y ajoutent : le seuil de l'article est **15 %** au territoire mais
**20 %** en sous-région et à la ferme (le mémoire n'en citait qu'un), et l'ordre des auteurs de
`chopin2015` était faux — la version publiée est **Chopin, Doré, Guindé, Blazy** (le PDF HAL en
donne trois ordres différents, c'est la notice de l'éditeur qui fait foi).

**Le correctif structurel est fait** : `build_chiffres.py` génère désormais les deux échelles
qui manquaient (`\calib*FermesPadMediane`, `\calib*Regions*`) ainsi que `tables/rendements.tex`,
au lieu de les laisser à la saisie manuelle.

## 7. Points ouverts qui pèsent sur le fond

**`CAL-100` est traité, et c'est un choix à assumer.** Le Ch. 3 donne désormais le chiffre —
4 cultures sur 11 sous le seuil contre 8 sur 10 publiées — et le tient plutôt que de le subir :
le PAD par culture pénalise les petits postes, où se concentre tout l'écart résiduel, et un
modèle qui reproduit 77 % de la surface en manquant les petits postes est un modèle dont on
connaît le domaine de validité. La réserve est répétée en conclusion, délibérément.

**`PERSP-60/62` — deux courriels à envoyer, pas des chantiers.** (a) La clé de répartition
mensuelle des précipitations **existe** dans le rapport technique ; l'indicateur d'irrigation
nette était déclaré non calculable à tort. (b) Les deux couches de chlordécone sont agrégées
en sens **opposés** — `RISQUE_CLD` au Minimum, `CLD_REEL` au Maximum — et ce sont les
contraintes d'éligibilité qui lisent la version permissive. Les deux sont écrits dans la
conclusion et dans l'annexe B ; il reste à les **poser aux encadrants**.

## 8. Commandes utiles

```bash
powershell memoire/compile.ps1                   # pdflatex + biber, puis compte de pages
.venv/Scripts/python memoire/audit_corpus.py     # audit du corpus
.venv/Scripts/python memoire/build_chiffres.py   # régénère chiffres.tex
.venv/Scripts/python memoire/build_figures.py    # régénère les figures
.venv/Scripts/python scripts/golden_snapshot.py --check   # 681 checksums, ~7 s
.venv/Scripts/python scripts/check_references.py          # garde-fou des 3 runs de référence
```

## 9. Où va quelle connaissance

- Un **trap ou une limite de données** → `docs/04-vigilance.md` (français, lu en premier par
  un nouveau venu).
- Un **item de mémoire** → le fichier `corpus/` de son domaine, avec ses arcs.
- **Ce qui reste à implémenter** → `TODO.md`.
- **Une investigation entière**, avec ses impasses → une spec dans `docs/superpowers/specs/`.
- **Ce qui gouverne la rédaction** (règle de sélection, budget, règles de forme) → `PLAN.md`.
- **Une réponse des encadrants** → `encadrants.md`, avec ce qu'elle change dans le `.tex`.
- **L'avancement du mémoire** → ce fichier.
