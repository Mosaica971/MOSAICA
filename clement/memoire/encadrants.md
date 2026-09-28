# Encadrants — les quatorze questions, et où leurs réponses atterrissent

> Fusionne `questions-encadrants.md` (préparation) et `mail-encadrants.md` (version envoyée),
> supprimés le 2026-08-16. **Consigner les réponses ici, au fur et à mesure.**

**Principe de rédaction, à ne pas perdre de vue** : le mémoire est écrit **sans ces réponses**
et il est déposable en l'état. Chaque marqueur `\attente{n}` dans le `.tex` signale une phrase
que la réponse **enrichira**, jamais un trou qui bloque. La prose qui précède un marqueur dit ce
qui est vrai aujourd'hui (« à ma connaissance », « le dépôt n'en garde pas trace ») ; la réponse
viendra la préciser, pas la combler.

Les marqueurs sont comptés dans le `.log` (`ATTENTE : Qn`) et se masquent d'un coup en passant
`\attentesvisiblesfalse` dans `preambule.tex` — sans toucher à la prose.

---

## Les quatorze questions et leur point de chute

| # | Question | Où elle atterrit | Ce qu'elle change |
|---|---|---|---|
| 1 | La trace la plus concrète de CALALOU entre 2021 et 2026 | Ch. 5 § *catalogue écrit seul*, `\attentebloc{1}` | ouvre ou ferme l'argument sur ce que la lignée a déplacé ; c'est **la** question du chapitre |
| 2 | MOSAICA a onze ans : a-t-il servi à une décision réelle ? | Intro § *lignée et commande* + Ch. 5 § *parité* | décide si le mémoire peut écrire que le modèle est un instrument **de recherche** ou un instrument **de décision** |
| 3 | Concertation : avec qui, et pouvoir réel des concertés ? | Ch. 4 encadré réflexif + Ch. 5 § *catalogue écrit seul* | la gradation à trois niveaux (proposer / réagir / ratifier) ; sans elle, le mémoire ne peut que constater l'absence |
| 4 | Évaluation d'impact de CALALOU et TI-FIG ? | Ch. 5, dans `\attentebloc{1}` | si « non », dire si c'est un choix, une contrainte de financement, ou un usage |
| 5 | Qui finance TI-FIG, et les financeurs participent-ils ? | Intro § *lignée et commande* | situe la commande ; un financeur qui siège n'est pas un financeur qui verse |
| 6 | Livrables contractuels, échéances, réception | Intro § *lignée et commande* | dit si ce travail est un **livrable** ou un **moyen** |
| 7 | Mesures engageantes ou incitatives pour l'intégration des résultats | Ch. 5 § *performativité* | c'est la question de la performativité, en version institutionnelle |
| 8 | Que devient le travail après le financement ? | Conclusion, `\attentebloc{8}` | toute la dernière page : successeur, échéance, forme de la passation |
| 9 | Diffusion du livre blanc, retours écrits, restitutions | Ch. 5 § *catalogue écrit seul* | même bloc que Q1 ; une diffusion sans retour est un fait, pas un silence |
| 10 | Pourquoi le modèle n'a pas évolué entre 2015 et 2021 | Intro § *lignée et commande* | financement, demande ou personne — les trois lectures ne disent pas la même chose du projet |
| 11 | Un article est-il envisagé, avec qui, quelle place ? | Conclusion, dernier paragraphe | et sur quoi : mon analyse est que les trois résultats transférables sont **méthodologiques**, cf. plus bas |
| 12 | Restitution prévue en Guadeloupe, sous quelle forme ? | Ch. 5 § *positionnement* | la restitution est la contrepartie concrète de la question de légitimité |
| 13 | Travail de l'unité avec les organisations agricoles guadeloupéennes | Ch. 5 § *positionnement* | liens institutionnels, conventions, contacts |
| 14 | La question de la légitimité d'un modèle prescriptif s'est-elle posée ? | Ch. 5 § *positionnement* + annexe B (chlordécone) | si elle s'est posée, la section cesse d'être une position personnelle et devient un fait du projet |

---

## Les réponses

*(Une section par question. Coller la réponse telle quelle, puis noter en une ligne ce qu'elle
change dans le `.tex` — c'est cette seconde ligne qui fait le travail.)*

### Q1 — la trace concrète de CALALOU
> *(en attente)*

### Q2 — MOSAICA a-t-il servi à une décision réelle
> *(en attente)*

### Q3 — la concertation et le pouvoir réel des concertés
> *(en attente)*

### Q4 — évaluation d'impact
> *(en attente)*

### Q5 — financeurs de TI-FIG
> *(en attente)*

### Q6 — livrables contractuels
> *(en attente)*

### Q7 — mesures engageantes ou incitatives
> *(en attente)*

### Q8 — la suite après le financement
> *(en attente)*

### Q9 — diffusion du livre blanc
> *(en attente)*

### Q10 — la pause 2015-2021
> *(en attente)*

### Q11 — l'article
> *(en attente)*

### Q12 — restitution en Guadeloupe
> *(en attente)*

### Q13 — les organisations agricoles
> *(en attente)*

### Q14 — la légitimité d'un modèle prescriptif
> *(en attente)*

---

## Ce qui reste en réserve — à poser de vive voix, pas par écrit

Le courriel envoyé couvre les quatorze questions ci-dessus. Le reste de la préparation garde sa
valeur comme **relances**, et deux blocs n'ont pas leur place à l'écrit.

**Sur la lignée et le terrain.** Qu'attendiez-vous exactement au moment de la lettre de mission,
et à quel moment avez-vous vu que ce serait une reconstruction d'outil ? Les enquêtes prévues
sont-elles reportées sur quelqu'un d'autre ou abandonnées ? Où en est la microferme dont les
vingt-cinq variantes portent le nom — les données existent-elles quelque part ?

**Sur la suite du code.** Quelqu'un d'autre que moi a-t-il déjà lancé un run complet ? Sinon,
deux heures ensemble avant mon départ, c'est le seul test de transmissibilité qui compte. Un
successeur est-il prévu ? Le dépôt doit-il devenir public — cela change ce que je peux mettre en
annexe. Quel est le statut juridique des données (RPG, Agreste, couches chlordécone) ?

**Points techniques à leur soumettre plutôt qu'à leur annoncer.** Tous sont documentés et portés
tels quels dans la version Python, sans rien corriger en silence ; ils sont dans
l'annexe~B du mémoire.

- Les **deux couches de chlordécone agrégées en sens opposés** — c'est le point le plus sérieux,
  parce que ce sont les contraintes d'éligibilité qui lisent la lecture la plus permissive.
- **`Eq_VE_PLUIE` interdit les vergers pluviaux sur tout le territoire** — était-ce connu, et
  faut-il relire à cette lumière le déficit de vergers de la calibration (8 ha simulés contre
  311 observés) ?
- **Le plancher de prairie du GAMS vaut la surface observée de 2017**, le fichier le documente
  lui-même ainsi. Circulaire au sens strict — était-ce assumé ?
- **Les rendements valent 2 à 4 fois ceux d'Agreste**, sauf le melon. Écart de définition,
  échelle expérimentale, autre chose ?
- Les **reprises manuelles** de l'assolement observé (419 parcelles reclassées, trois pentes
  ramenées à 45°) : y en a-t-il d'autres avant de citer l'observé comme référence ?
- ⚠ **Certains de ces comportements sont dans le GAMS d'origine.** Formulation qui marche, au
  futur et sans mise en cause : *« je les ai portés tels quels et je les documente ; avant toute
  valorisation, il faut savoir lesquels ont pu affecter des résultats antérieurs. »* C'est un
  service rendu, et la seule façon de ne pas les laisser derrière soi.

**Sur l'article, mon analyse à leur soumettre.** Le portage seul n'est pas publiable ; trois
résultats le sont, et ils sont **méthodologiques et non agronomiques** : une contrainte de
politique publique satisfaite à coût nul par relabellisation quand les données ne distinguent
pas les cultures qu'elle vise ; un front ε-contrainte entièrement inactif parce que paramétré
sur la mauvaise référence ; un score composite qui classe sur la finesse d'une nomenclature. Je
n'ai trouvé aucun des trois documenté ailleurs.

**Bloc contexte — à ne poser que de vive voix, et peut-être pas du tout.** Qui, dans TI-FIG, est
basé en Guadeloupe et depuis combien de temps ? Y a-t-il des chercheurs ou ingénieurs
guadeloupéens dans le projet ? À l'écrit ces questions se lisent comme un jugement sur l'unité ;
de vive voix, ce sont des questions de recherche. Elles n'ont d'intérêt que si elles éclairent
une décision de rédaction (Ch. 5 § *positionnement*).
