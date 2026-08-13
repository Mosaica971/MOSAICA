# Questions aux encadrants — J.-M. Blazy et L. Guindé

**À poser avant le 26/08.** Plusieurs réponses changent le contenu du mémoire, pas seulement
son ton : `REF-26` (effet réel), `REF-25` (co-construction) et `REF-55` (la suite) attendent
des faits que le dépôt ne contient pas et que deux conversations peuvent fournir.

> **Ne pas arriver avec cette liste.** Quarante questions d'affilée est un interrogatoire, et
> les réponses seront courtes. Choisir **huit à dix** questions d'ouverture — celles marquées
> ★ — et garder le reste comme relances. Les blocs 1 à 4 se posent ensemble ; le bloc 6 mérite
> un moment à part, et le bloc 7 un moment choisi.

---

## 1. Ce que les projets ont déplacé

★ **Quelle est la trace la plus concrète que CALALOU ait laissée entre 2021 et 2026 ?**
Formulée ainsi plutôt qu'en « qu'est-ce que ça a changé », qui appelle une réponse générale.
On cherche un fait citable : une décision, une aide, une ligne de politique, une reprise par
un organisme.

- Le livre blanc — à qui a-t-il été envoyé, qui l'a lu, y a-t-il eu des retours écrits ?
- Y a-t-il eu une **restitution** aux acteurs du territoire ? Combien de personnes, qui ?
- Existe-t-il une **étude d'impact** de CALALOU ou de TI-FIG ? Si non, est-ce un choix, une
  contrainte de financement, ou simplement une chose qu'on ne fait pas ?
- ★ **MOSAICA a onze ans. A-t-il déjà servi à une décision réelle, une fois, depuis 2015 ?**
  C'est la question de fond, et elle vaut d'être posée sans détour.
- Entre l'article de 2015 et CALALOU en 2021, le modèle n'a pas évolué. Pourquoi cette pause —
  absence de financement, de demande, de personne ?

## 2. La gouvernance et les financeurs

★ **Qui finance TI-FIG, et le financeur siège-t-il dans le projet ?** (Ta question, gardée
telle quelle : elle est bien posée.)

- Y a-t-il un **comité de pilotage** ? Qui y siège, à quelle fréquence, avec quel pouvoir de
  décision sur le contenu scientifique ?
- Quels sont les **livrables contractuels** de TI-FIG, à quelles dates, et qui les réceptionne ?
  (Utile aussi pour toi : savoir si ton travail est un livrable ou un moyen.)
- Le financeur a-t-il un **intérêt dans le résultat** ? Une collectivité qui finance une étude
  d'allocation optimale peut avoir besoin d'une conclusion plutôt qu'une autre — la question
  est légitime et se pose calmement.
- Que se passe-t-il **après** la fin du financement ? Le modèle est-il censé continuer à vivre ?

## 3. La concertation, et le pouvoir réel des concertés

★ **Y a-t-il eu concertation, avec qui, et quels pouvoirs avaient-ils ?** (Ta question, et
c'est la meilleure de ta liste — le second membre est ce qui la rend sérieuse.)

Relances utiles, par ordre de dureté croissante :

- Les acteurs ont-ils pu **proposer** des scénarios, ou seulement **réagir** à des scénarios
  proposés ?
- Ont-ils pu contester l'**objectif** du modèle — « maximiser la marge ajustée du risque » —
  ou seulement les contraintes ?
- Y a-t-il eu des retours d'**agriculteurs** sur les résultats de Chopin et al. (2015) ?
  Qu'ont-ils dit ?
- ★ **Qui décide de ce qu'est une « bonne » allocation ?** Le modèle produit une carte
  prescriptive ; le critère qui la classe n'a été validé par personne d'extérieur au labo, à ma
  connaissance. Est-ce exact ?
- Les chambres d'agriculture, la Région, la DAAF, les organisations de producteurs de banane et
  de canne : lesquelles connaissent l'existence de ce modèle ?
- Y a-t-il des **mesures engageantes ou incitatives** pour que les résultats soient intégrés,
  ou le projet s'arrête-t-il à la production de connaissance ? (Ta question, gardée.)

## 4. La place de ce stage dans la lignée

- Qu'attendiez-vous exactement de ce stage **au moment de la lettre de mission** — et à quel
  moment avez-vous vu qu'il deviendrait un travail de reconstruction d'outil plutôt que de
  simulation ?
- La lettre prévoyait des **enquêtes de terrain** et l'acquisition de données technico-
  économiques sur la microferme. Est-ce reporté sur quelqu'un d'autre, ou abandonné ?
- ★ **Où en est la microferme Karusmart ?** Les 25 variantes maraîchères portent son nom et
  sont vides — identiques au bit près. Les données existent-elles quelque part, en cours
  d'acquisition, ou pas du tout ?

## 5. La suite du code, et ce que je laisse

★ **Qui fera tourner ce modèle après mon départ ?** La question n'est pas rhétorique :
`PERSP-E` (vous former à le lancer) est le chantier dont dépend la survie de tout le reste.

- Quelqu'un d'autre que moi a-t-il déjà lancé un run ? Si non, quand pouvons-nous le faire
  ensemble — c'est deux heures, et c'est le seul test qui compte.
- Un **successeur** est-il prévu (stage, CDD, thèse) ? À quelle échéance ?
- Le dépôt doit-il devenir **public** (GitHub, forge INRAE) ? Quelle est la politique de
  l'unité ? Cela change ce que je peux écrire dans le mémoire et en annexe.
- Quel est le **statut juridique des données** (RPG, Agreste, couches chlordécone) ? Que puis-je
  citer, reproduire, publier ? Le dépôt les exclut par précaution, mais la règle exacte
  m'échappe.
- Le passage du dépôt **en anglais** est différé faute de temps. Est-ce souhaitable de votre
  point de vue, ou le français est-il un choix de l'unité ?

## 6. Ce que le dépouillement a trouvé — à leur soumettre, pas à leur annoncer

> Ce bloc n'est pas une liste de questions : c'est le moment où tu leur apportes des résultats.
> Il vaut mieux le traiter comme tel — « j'ai trouvé ceci, comment le lisez-vous ? » — parce
> que plusieurs de ces points touchent à leur propre travail.

★ **Les deux couches de chlordécone sont agrégées en sens opposés.** `RISQUE_CLD` prend le
**Minimum** de la classe sur la parcelle, `CLD_REEL` le **Maximum**. Or ce sont les contraintes
d'éligibilité de l'igname tutorée et de la prairie pâturée qui lisent `RISQUE_CLD`, donc la
lecture **la plus favorable**. Une parcelle à cheval sur une zone saine et une zone contaminée
est traitée comme saine. Est-ce un choix assumé, un artefact de traitement SIG, ou une chose
que personne n'a relevée ? *(La réponse importe : sur un enjeu de santé publique, la
permissivité par défaut ne se documente nulle part.)*

- **`Eq_VE_PLUIE` interdit les vergers pluviaux sur tout le territoire** — le test `0 ≠ 1` est
  toujours vrai. `VE_PLUIE` ne peut donc apparaître dans aucune sortie. Était-ce connu ? Et
  faut-il lire le déficit de vergers de la calibration à cette lumière ?
- **Le plancher de prairie du GAMS vaut la surface observée de 2017**, le fichier le documente
  lui-même ainsi. Circulaire, donc — était-ce assumé comme tel ?
- **Les rendements du modèle valent 2 à 4 fois ceux d'Agreste**, sauf le melon. La Table 1 de
  l'article étant intouchable sous mandat de parité, je porte l'écart au lieu de le corriger.
  Comment le lisez-vous — définitions différentes, échelle expérimentale, autre chose ?
- ⚠ **La question difficile, et il faut la poser :** certains de ces défauts sont dans le GAMS
  d'origine. **Est-ce que des résultats publiés en dépendent ?** À poser sans mise en cause —
  la formulation qui marche est factuelle et tournée vers l'avenir : *« j'ai porté ces
  comportements tels quels et je les documente ; avant de publier quoi que ce soit, il faut
  savoir lesquels ont pu affecter des résultats antérieurs. »* C'est un service rendu, pas un
  reproche, et c'est aussi la seule façon de ne pas les laisser derrière soi.
- Trois parcelles de plus de 45° de pente ont été ramenées à 45° « pour ne pas avoir à modifier
  les seuils dans MOSAICA », et 419 parcelles ont été reclassées de café/cacao vers la canne.
  C'est documenté dans le rapport technique. Y a-t-il d'autres reprises de ce type dont je
  devrais tenir compte avant de citer l'observé comme référence ?

## 7. Le contexte du travail — à choisir son moment

> Ce bloc ne se pose pas dans la même conversation que le reste, et peut-être pas du tout. Il
> ne sert à rien si son but est de faire un point ; il sert s'il éclaire une décision de
> rédaction (`REF-05`, `REF-06`, `REF-25`).

- Qui, dans TI-FIG, est **basé en Guadeloupe**, et depuis combien de temps ? Y a-t-il des
  chercheurs ou des ingénieurs guadeloupéens dans le projet ?
- Comment l'unité travaille-t-elle avec les **organisations agricoles guadeloupéennes** — lien
  institutionnel, conventions, contacts personnels ?
- Est-ce que la question de la **légitimité** d'un modèle prescriptif produit depuis un centre
  de recherche national s'est déjà posée dans le projet ? Sous quelle forme, et qu'en a-t-on
  fait ?
- Comment les résultats sont-ils **restitués en Guadeloupe** — en français académique, dans
  quels lieux, devant qui ?

## 8. La suite scientifique — pour toi

- Un **article** est-il prévu à partir de ce travail ? Avec qui, à quelle échéance, et quelle
  serait ma place — auteur, co-auteur, remercié ?
- Sur quoi porterait-il selon vous ? *(Mon analyse : le portage seul n'est pas publiable, mais
  trois résultats le sont — une contrainte de politique publique satisfaite à coût nul par
  relabellisation ; un front ε-contrainte entièrement inactif parce que paramétré sur la
  mauvaise référence ; un score composite qui classe sur la finesse d'une nomenclature. Les
  trois sont des pièges de méthode, pas des résultats agronomiques, et je n'en ai trouvé aucun
  documenté ailleurs.)*
- La **note technique interne** : à qui doit-elle s'adresser, et sous quelle forme la voulez-vous ?

---

## Les cinq réponses qui changeraient le mémoire

Si le temps manque, ce sont celles-là qu'il faut ramener :

| question | ce qu'elle débloque |
|---|---|
| la trace concrète de CALALOU | `REF-26`, et l'ouverture du Ch. 5 |
| les pouvoirs réels des concertés | `REF-25`, la gradation à trois niveaux |
| le Minimum sur la chlordécone | `REF-05`, et une correction possible du modèle |
| qui fera tourner le modèle | `REF-52`, `REF-55`, et toute la conclusion |
| des résultats publiés en dépendent-ils | le périmètre de ce que le mémoire peut affirmer |
