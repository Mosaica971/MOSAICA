# Plan et forme — ce qui gouverne la réécriture

> Fusionne l'ancien `PLAN.md` (quoi écrire) et `FORME.md` (comment ça se compose), le
> 2026-08-16. Les parties **exécutées** des deux fichiers ont été retirées : elles vivent
> désormais dans le `.tex` lui-même, chaque chapitre portant en tête son budget et sa thèse.
> Ce qui reste ici est ce qui **gouverne encore** la réécriture par Clément.
>
> Contraintes d'école (`student_context/Consignes pour les PFE2526.pdf`) : 30 p de cœur,
> **police 12**, figures comprises, annexes ≤ 20 p, résumés FR et EN ≤ 2 p, soutenance 20 min
> + 20 min de questions.

---

## 1. La règle de sélection — opposable, à ne pas assouplir

453 items du corpus portent une destination de chapitre, pour 30 pages. Sans règle, le tri se
fait au goût — ce que le corpus existe pour empêcher.

> **Un item entre dans le cœur s'il satisfait (A) et au moins un de (B1, B2, B3).**
>
> - **(A)** il porte un `chiffre`, ou il ferme une branche, ou il renverse un verdict ;
> - **(B1)** il est sur une des 12 chaînes les plus profondes du graphe ;
> - **(B2)** sa `severite` est `critique` ou `majeur` ;
> - **(B3)** sans lui, un chiffre cité ailleurs dans le cœur serait faux ou mal lu.

Tout le reste descend **sans être perdu** : annexes (le détail), note technique interne (les 195
items `note`), oral (les 130 items `oral`). Conséquence : **l'annexe n'est pas un dépotoir,
c'est la couche de preuve** — le cœur affirme, l'annexe établit. L'introduction le dit en une
phrase, et les consignes l'autorisent explicitement.

## 2. La question, et pourquoi le plan en découle

Le mémoire a un problème d'énoncé à résoudre avant tout le reste : **la commande n'a pas été
exécutée**. Traiter ça comme une excuse condamne le document ; il faut en faire la question.

> **Question :** que faut-il avoir établi sur un modèle d'allocation hérité pour que ses
> résultats prospectifs soient **opposables** — c'est-à-dire défendables devant quelqu'un qui
> les conteste ?

Trois réponses, trois chapitres : **le porter fidèlement** (sans quoi tout désaccord est
indémêlable) → Ch. 2 ; **établir ce qu'il reproduit du réel**, et à quel prix → Ch. 3 ;
**mesurer ce qu'il ne permet pas de conclure** → Ch. 4.

Et la réponse d'ensemble, à donner en conclusion **sans en changer les termes** : *le livrable
opposable de ce stage n'est pas un jeu de scénarios, c'est un instrument dont on sait exactement
ce qu'il peut et ne peut pas dire.*

## 3. Le budget, et où on en est

| partie | budget | mesuré au 2026-08-16 | thèse du chapitre |
|---|---:|---:|---|
| Introduction | 2,5 | 2 | le stage n'a pas répondu à la commande, il a reconstruit l'instrument qu'elle supposait acquis |
| Ch. 1 terrain et objet | 2,0 | 2 | l'allocation des terres est un problème de choix sous contraintes serrées, et l'outil censé le traiter n'était pas exploitable |
| Ch. 2 porter | 6,0 | 6 | la fidélité à l'**artefact** est ce qui rend opposable tout désaccord ultérieur entre les deux modèles |
| Ch. 3 calibrer | 7,0 | 7 | un écart se diagnostique, se décompose et se nomme — ce qui y résiste désigne un **mécanisme absent**, pas une erreur de réglage |
| Ch. 4 explorer | 7,0 | 7 | un classement de politiques n'a de sens que **relativement à un forçage**, et le dispositif doit énoncer ce qu'il ne peut pas trancher |
| Ch. 5 discussion | 4,0 | 4 | ce qui rend ce travail utilisable n'est pas ce qu'il affirme, c'est ce qu'il **délimite** |
| Conclusion | 1,5 | 3 | ⚠ le seul dépassement — voir § 6 |
| **cœur** | **30** | **31** | **30/30 une fois les marqueurs d'attente masqués** |
| Annexes A-F | 20 | 15 | de la marge : A, B et C peuvent s'étoffer |

Ch. 3 et Ch. 4 prennent la moitié du volume : c'est là que sont les résultats, et un jury lit un
mémoire pour ses résultats.

## 4. Les règles de forme — à tenir dès la première ligne réécrite

Elles sont tenues dans la version actuelle. Les rompre en réécrivant coûte une passe de
correction complète.

1. **`\enquote{}` partout.** Jamais `\guillemotleft~…~\guillemotright{}` : la forme manuelle est
   fragile et se voit dès qu'une ligne se coupe au mauvais endroit.
2. **siunitx partout** — `\SI{}{\percent}`, `\SI{}{\ha}`, `\SI{}{\euros}`, `\num{}`. Jamais de
   nombre nu, jamais d'unité écrite à la main, **y compris dans les tableaux**. C'est ce qui
   garantit la virgule décimale et l'espace fine des milliers. Attention : `\SI{x}{}` avec une
   unité vide échoue — c'est `\num{x}`.
3. **Aucun flottant non cité.** Chaque `\label{fig:…}` / `\label{tab:…}` a son `\ref` dans la
   prose. Vérifié : 0 référence non résolue.
4. **Aucun chiffre saisi à la main dans le cœur** — tout vient de `chiffres.tex`. Trois
   exceptions subsistent, listées dans `ETAT.md`.
5. **Références en français explicite** : `chapitre~\ref{}`, `§~\ref{}`, `tableau~\ref{}`,
   `figure~\ref{}`, `annexe~\ref{}`, `équation~\eqref{}`. **Ne pas remettre `cleveref`** sans
   refaire le test décrit dans `preambule.tex` — il plante sur une référence avant-coureuse dès
   la passe 1, donc fatalement.
6. **Légende au-dessus des tableaux, en dessous des figures**, et `[tbp]` — jamais `[H]`, qui
   force des blancs en bas de page.

Ce qui a été tranché et qu'il ne faut pas rouvrir : **une seule colonne** (à 12 pt imposé, deux
colonnes donnent 42-45 signes par ligne et cassent tous les objets larges) ; **classe `report`
avec `\titleclass{\chapter}{straight}`** (les chapitres s'enchaînent sans saut de page — cela
valait 4 à 5 pages de blanc) ; **interligne 1,15 et marges 3 cm** ; **titres de chapitre en
verbes** (*Porter*, *Calibrer*, *Explorer*), qui portent l'argument du mémoire.

## 5. Les flottants — huit, tous cités

| id | objet | ch | état |
|---|---|---|---|
| `tab:programme` | taille du programme et coût de sa résolution | 2 | **fait** (macros) |
| `fig:fil` | un fil de justification : fait mesuré → branche fermée (TikZ, sans dépendance) | 2 | **fait** |
| `tab:attribution` | les trois barreaux de calibration | 3 | **fait** |
| `fig:calibration` | observé vs simulé par groupe RPG | 3 | **fait** (`build_figures.py`) |
| `fig:spectre` | les deux catalogues en tableaux ordonnés, dégradé + encadrés (TikZ) | 4 | **fait** (refait le 17/08) |
| `tab:grille` | marge brute par cellule politique × forçage | 4 | **fait** |
| `fig:regret` | regret par politique et par forçage (TikZ, depuis les macros) | 4 | **fait** |
| `tab:front-budget` | front marge × enveloppe publique | 4 | **fait** (`tables/`) |

Deux figures envisagées ont été abandonnées et **il ne faut pas les reprendre sans raison** :
les 20 durées de solve (le tableau `tab:programme` porte déjà le fait, min/max/CV) et le graphe
complet du corpus — 455 nœuds forment une pelote illisible, et `fig:fil` est ce qui se lit.

## 6. Ce qui reste à faire, par ordre

1. **Une page de trop dans le cœur (31/30) — et elle est exactement l'échafaudage.** Mesuré :
   **31 pages marqueurs d'attente visibles, 30 pages une fois `\attentesvisiblesfalse` posé**
   dans `preambule.tex`. Le budget est donc tenu dès que les réponses des encadrants sont
   intégrées (ou renoncées). Si un resserrage est quand même souhaité, le point faible est la
   conclusion, qui fait 3 pages pour 1,5 budgetées : la liste des cinq chantiers ouverts peut
   tenir en trois lignes.
2. **Les deux logos manquent** — `figures/logo-n7.pdf` et `figures/logo-inrae.pdf`. La page de
   garde affiche des cadres de remplacement. C'est une **exigence explicite** des consignes.
   10 minutes.
3. **`REF-05`** — l'axe le plus exposé du corpus n'est pas écrit (Ch. 5, marqueur `\arediger`).
   Le tenir franchement ou ne pas le tenir ; une clause de style y serait pire que le silence.
   *Décision de Clément, personne d'autre ne peut la prendre.*
4. **Mention « CONFIDENTIEL »** — à trancher avec Blazy et Guindé ; si elle s'applique, elle doit
   figurer très visiblement sur la garde.
5. **Incohérence de dates sur la garde** — « mai — octobre 2026 » alors que la soutenance est du
   1er au 4 septembre et le dépôt le 26/08.
6. **Vérifier volume / pages / DOI de la bibliographie.** Les dix entrées de méthode (Haimes,
   Mavrotas, Wald, Savage, Starr, Markowitz, Hazell & Norton, Howitt, Tixier) ont été saisies de
   mémoire : auteurs, titres et années sont sûrs, la pagination l'est moins.
7. **Pas de liste des figures / tableaux**, délibérément : sept flottants ne le justifient pas et
   les consignes ne le demandent pas. À revoir au-delà de quinze.

## 7. La liste de contrôle avant dépôt

- [x] `\annoncecoeur` annonce le compte de pages — 31/30 avec l'échafaudage, **30/30 sans** (§ 6.1)
- [x] zéro `Overfull hbox` au-delà de 5 pt
- [x] zéro encadré `MATIÈRE` restant dans le `.log`
- [ ] zéro `A REDIGER` — il en reste **un**, volontaire (`REF-05`, § 6.3)
- [x] chaque flottant est cité par la prose, et sa légende se suffit à elle-même
- [x] zéro référence ou citation non résolue
- [ ] chaque chiffre du corps vient d'une macro de `chiffres.tex` (trois exceptions connues)
- [ ] `audit_corpus.py --strict` passe ; `MET-32` reste la seule violation, volontaire
- [x] chaque résultat des Ch. 3 et 4 est accompagné de sa réserve
- [x] la conclusion répond à la question de l'introduction **dans ses termes**
- [x] les résultats négatifs sont présents et nommés comme tels
- [x] les branches fermées sont dans l'annexe B avec leur mesure — ou l'aveu qu'il n'y en a pas
- [x] aucune annexe n'est orpheline : chacune est appelée depuis le corps
- [x] résumés FR et EN ≤ 2 p chacun, 8 mots-clés

## 8. Ce qui produit l'effet « thèse », et qui n'est pas typographique

À garder en tête en réécrivant : ce n'est pas le nombre de colonnes, ce sont sept propriétés,
toutes vérifiables, et le corpus les fournit déjà.

| propriété | concrètement |
|---|---|
| **une question, et sa réponse** | l'intro pose une question ; la conclusion y répond en une phrase, sans en changer les termes |
| **le triplet énoncé / mesure / réserve** | aucun résultat sans la mesure qui l'établit ET la phrase qui dit ce qu'il ne dit pas |
| **traçabilité numérique** | aucun chiffre saisi à la main |
| **les résultats négatifs comptent** | P10 hors d'atteinte, 4 cultures sur 11 sous le seuil, la marge négative sous crise |
| **les branches coupées sont dites** | ce qui a été écarté, et par quelle mesure |
| **les verdicts renversés sont dits** | on a cru X, on a mesuré, c'était faux |
| **réflexivité ancrée** | chaque affirmation de posture adossée à un fait mesuré, jamais à une impression |

Le triplet de la deuxième ligne est **l'unité de composition** des chapitres 2 à 4 : un
paragraphe = un énoncé, sa mesure, sa réserve. C'est laborieux, et c'est exactement ce qui
distingue un rapport de stage d'un chapitre de thèse.
