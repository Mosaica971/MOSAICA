# État du mémoire — reprise de contexte

**Ce fichier existe pour qu'une conversation neuve démarre sans rien réexpliquer.**
Il dit où en est le mémoire, ce qui a été décidé, ce qui reste, et ce qu'il ne faut pas
refaire. Il est tenu à jour à la fin de chaque session de travail sur le mémoire.

> Dernière mise à jour : **2026-08-13**. Dépôt le **26/08** (J-13), soutenance **1-4 sept**.

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
| **Rapport à Claude** | une **section assumée** dans le Ch. 5 | ni passé sous silence, ni un chapitre entier |
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

### Le corpus — `memoire/corpus/` (fait)

L'inventaire typé de tout ce que le stage a décidé, mesuré, écarté ou raté, avec les arcs qui
reliént chaque item à ce qui le justifie. **482 items, 1 267 arcs, 13 fichiers.** Le schéma
est dans `corpus/00-schema.md` ; il est à lire avant d'y toucher.

| fichier | domaine | préfixe |
|---|---|---|
| `10-contexte-commande.yaml` | territoire, TI-FIG, lettre de mission | CTX |
| `20-portage-gams.yaml` | parité, bugs portés, inventaire d'équations | PORT |
| `30-architecture-logicielle.yaml` | registre, `core/`↔`case_studies/`, dashboard | ARCH |
| `40-solveur-tractabilite.yaml` | MILP, branch-and-bound, warm start, symétrie | SOLV |
| `50-donnees.yaml` | ce que le jeu contient et ne contient pas, le SIG | DON |
| `60-calibration.yaml` | PAD, référence 2017, déviations, plateau | CAL |
| `70-prospective.yaml` | politiques, forçages, fronts, robustesse | PROS |
| `80-indicateurs.yaml` | environnement, eau, carbone, Rpest, score composite | IND |
| `90-verification-outillage.yaml` | tests, golden, références, audits | VER |
| `95-methode-organisation.yaml` | commits, docs, specs, langue, rythme | MET |
| `96-reflexivite.yaml` | **forme différente** : 27 axes, à arbitrer par Clément | REF |
| `97-perspectives.yaml` | élevage, MAELIA, anglais, Excel, formation | PERSP |
| `98-article.yaml` | ce qui est neuf vs Chopin 2015, ce qui manque | ART |

### L'audit — `memoire/audit_corpus.py` (fait)

Vérifie les deux affirmations que le corpus fait sans quoi il ne vaut rien : aucun choix
retenu n'est arbitraire, aucune branche n'a été coupée au flair.

```bash
.venv/Scripts/python memoire/audit_corpus.py            # rapport -> corpus/_audit.md
.venv/Scripts/python memoire/audit_corpus.py --graph    # + _graphe.dot, _graphe-<PREF>.mmd
.venv/Scripts/python memoire/audit_corpus.py --strict   # sortie non nulle si une règle casse
```

État au 2026-08-13 : **règle 1 : 1 · règle 2 : 0 · règle 3 : 0 · 0 arc pendant · 0 cycle.**
La violation restante (`MET-32`, le choix de la langue) est **volontaire** : ce choix n'a pas
été justifié quand il a été fait, et lui inventer un parent après coup serait le travers que
le corpus existe pour empêcher. Ne pas la « corriger ».

`_audit.md` et les `_graphe-*` sont **générés** — ne jamais les éditer à la main.

### Les chiffres — `memoire/build_chiffres.py` → `chiffres.tex` (fait, vivant)

518 macros LaTeX lues dans les `recap.json` des runs, pour qu'aucun nombre du mémoire ne soit
saisi à la main. `\num{}` de siunitx francise à l'impression. Régénérer après tout nouveau run
ou toute correction de constante.

⚠ Le fichier contient **aussi** un bloc de constantes saisies à la main, et c'est exactement
là qu'une dérive s'est logée (`mesChecksums` annonçait 570 pour 681 réels). Voir MET-64.

### Le document — `memoire/memoire.tex` (à ~25 p sur 30)

Compilation : `memoire/compile.ps1` (pdflatex + biber ; **pas** latexmk, Perl est absent).
Ne pas rediriger stderr sur `compile.ps1` : MiKTeX y écrit un avertissement bénin que
PowerShell transforme en échec.

| partie | état |
|---|---|
| Ch. 0 introduction | squelette, 5 `\arediger` |
| Ch. 1 terrain et objet | rédigé, 1 `\arediger` |
| Ch. 2 porter | rédigé |
| Ch. 3 calibrer | rédigé (plancher de prairie traité honnêtement le 12/08) |
| Ch. 4 explorer | rédigé |
| Ch. 5 discussion | **squelette**, 5 `\arediger` — c'est le gros chantier |
| Ch. 6 conclusion | **squelette**, 3 `\arediger` |
| Annexes A-F | **six fichiers vides** |
| Liminaires | garde / remerciements / résumés FR-EN à écrire |

## 5. Le plan par phases

- [x] **Phase 1 — Dépouillement.** Cinq sources épuisées : le dépôt, `docs/`, les specs, le
      journal de vigilance, l'historique git, `context/` (dont le `Rapport technique
      variables MOSAICA_v2.docx`, jamais ouvert avant, et le livre blanc CALALOU). 482 items.
- [x] **Phase 2 — Graphe et audits.** Script, trois règles, trois échappatoires déclarées,
      7 branches coupées documentées. Commit `123b7a2`.
- [ ] **Phase 3 — Réflexivité.** Les 27 axes de `96-reflexivite.yaml` attendent l'arbitrage
      de Clément : valider / écarter / ajouter. **Lui seul peut écrire ce contenu** — chaque
      axe porte un `ancrage` (le fait mesuré qui l'empêche d'être un lieu commun), une
      `question` (ce que lui seul peut trancher) et un `risque` (comment l'axe rate). Sur 27,
      le Ch. 5 en tient 8 à 10.
- [ ] **Phase 4 — Plan détaillé.** Dériver le plan de la topologie du graphe plutôt que du
      goût, et arbitrer le budget de 30 pages. La charge par destination est déjà dans
      `_audit.md` (ch3 : 106 items, ch4 : 100, ch2 : 98, ch5 : 90 — il faudra couper).
- [ ] **Phase 5 — Rédaction.** Intro, Ch. 5, conclusion, les six annexes, résumés FR/EN,
      mots-clés, remerciements. 14 `\arediger` restants.
- [ ] **Phase 6 — Finition et dépôt du 26/08.**
- [ ] **Phase 8 — Soutenance (1-4 sept), note technique interne, analyse d'article.**

## 6. Points ouverts qui pèsent sur la rédaction

**`CAL-100` — un trou d'honnêteté, `severite: critique`.** Le Ch. 3 établit que « la métrique
réellement comparable à l'article est le nombre de cultures sous le seuil », puis ne donne
jamais le chiffre. Il vaut **4 sur 11**, contre **8 sur 10** publiées — alors que les trois
métriques mises en avant (types 86,9 %, parcelles 67,6 %, surface 77,1 %) atteignent ou
dépassent l'article. Écrire qu'une métrique est la bonne puis ne pas la citer est intenable
devant un jury : soit on la donne et on l'explique (le PAD par culture pénalise les petits
postes, où se concentre tout l'écart résiduel), soit on renonce à écrire qu'elle est la
métrique comparable.

**381 macros sur 518 ne sont citées nulle part.** Ce n'est pas un défaut : c'est la mesure
exacte de ce qui reste à écrire. Chaque politique P1-P9 et chaque front d'azote a ses ~14
chiffres générés et jamais imprimés — donc le Ch. 4 et les annexes D/E sont les vrais
chantiers de volume.

**17 items destinés à un chapitre n'y ont aucun chiffre**, dont `CAL-100`, `CAL-102` (les
deux signatures émergentes) et `PROS-31` (le résultat central du Ch. 4). Liste dans
`_audit.md`.

**`PERSP-60/62` — deux courriels à envoyer, pas des chantiers.** (a) La clé de répartition
mensuelle des précipitations **existe** dans le rapport technique ; l'indicateur d'irrigation
nette était déclaré non calculable à tort. (b) Les deux couches de chlordécone sont agrégées
en sens **opposés** — `RISQUE_CLD` au Minimum, `CLD_REEL` au Maximum — et ce sont les
contraintes d'éligibilité qui lisent la version permissive. Rien ne le signale nulle part.

## 7. Le graphe — ce qu'il faut en attendre

**Il n'y a rien à installer, et il n'y a pas de rendu visuel à produire.** La valeur du
graphe est l'**audit** : c'est lui qui prouve que rien n'est arbitraire, et il sort en texte
dans `_audit.md`. Le `.dot` et les `.mmd` sont un sous-produit ; 455 nœuds affichés d'un coup
forment une pelote illisible qui n'apprend rien.

La seule visualisation qui aurait sa place dans le mémoire est une **figure choisie** — par
exemple les 7 branches coupées avec leurs mesures, ou un fil narratif unique de la racine à
la feuille. Elle n'existe pas encore ; elle demande `winget install Graphviz.Graphviz` (ou un
TikZ écrit à la main, ce qui évite la dépendance et fera moins de 30 lignes).

## 8. Commandes utiles

```bash
.venv/Scripts/python memoire/audit_corpus.py     # audit du corpus
.venv/Scripts/python memoire/build_chiffres.py   # régénère chiffres.tex
.venv/Scripts/python memoire/build_figures.py    # régénère les figures
powershell memoire/compile.ps1                   # pdflatex + biber
.venv/Scripts/python scripts/golden_snapshot.py --check   # 681 checksums, ~7 s
.venv/Scripts/python scripts/check_references.py          # garde-fou des 3 runs de référence
```

## 9. Où va quelle connaissance

- Un **trap ou une limite de données** → `docs/04-vigilance.md` (français, lu en premier par
  un nouveau venu).
- Un **item de mémoire** → le fichier `corpus/` de son domaine, avec ses arcs.
- **Ce qui reste à implémenter** → `TODO.md`.
- **Une investigation entière**, avec ses impasses → une spec dans `docs/superpowers/specs/`.
- **L'avancement du mémoire** → ce fichier.
