# Version envoyable — à copier-coller

*(Ce qui est au-dessus de la ligne est pour toi. Tout ce qui est en dessous s'envoie tel
quel. La version de travail, avec le pourquoi de chaque question, reste dans
`questions-encadrants.md`.)*

**Trois remarques avant d'envoyer :**

1. **Les questions sont numérotées** — ça n'est pas cosmétique : on répond beaucoup plus
   volontiers à « 4, 7 et 12 » qu'à un bloc de prose, et tu récupères des réponses ciblées.
2. **Le bloc D (points techniques)** est le seul qui touche à leur propre travail. Il est
   rédigé en demande de vérification et non en constat, ce qui est à la fois plus juste — tu
   peux te tromper — et plus facile à recevoir. La question de savoir si des résultats publiés
   en dépendent est formulée au futur (« avant toute valorisation »), ce qui la rend sûre à
   l'écrit.
3. **Le bloc F est délicat.** Il est isolé à la fin exprès : tu le supprimes d'un coup de
   souris si tu préfères le garder pour une conversation. Mon avis : à l'écrit il peut être lu
   comme un jugement sur l'unité ; de vive voix, c'est une question de recherche. Je le
   couperais.

---
--- COUPER ICI — tout ce qui suit s'envoie tel quel ---
---

Bonjour Jean-Marc, bonjour Loïc,

Je suis en train de rédiger mon mémoire (dépôt le 26 août) et j'aimerais y situer le travail
dans le contexte plus large de TI-FIG et de ce qui l'a précédé. Il y a un ensemble de choses
que je ne peux pas reconstituer depuis le code et les données, et qui feraient beaucoup pour
la qualité du document.

J'ai numéroté les questions pour que vous puissiez répondre seulement à celles qui vous
parlent, dans l'ordre que vous voulez — même en deux lignes chacune. Si vous préférez qu'on en
parle de vive voix, je suis évidemment disponible, et je peux venir avec le tout.

---

## A. Les cinq questions les plus importantes

Si vous ne deviez en traiter que quelques-unes, ce sont celles-là.

1. Quelle est la trace la plus concrète que **CALALOU** ait laissée entre 2021 et 2026 — une
   décision, une aide, une orientation reprise quelque part, une suite donnée au livre blanc ?

2. **MOSAICA a onze ans.** A-t-il déjà servi, une fois, à éclairer une décision réelle depuis
   la publication de 2015 ?

3. Y a-t-il eu **concertation avec les acteurs** (agriculteurs, chambres, élus, associations,
   organisations de producteurs) sur CALALOU ou TI-FIG ? Si oui, lesquels — et surtout : de
   quoi pouvaient-ils réellement décider ? Proposer des scénarios, ou réagir à des scénarios
   déjà construits ?

4. **Qui fera tourner ce modèle après mon départ ?** C'est la question qui décide de ce que
   tout le reste vaut, et j'aimerais qu'on y réponde concrètement avant fin août.

5. Existe-t-il, ou est-il prévu, une **évaluation d'impact** des projets CALALOU et TI-FIG ?
   Si non, est-ce un choix, une contrainte de financement, ou simplement une chose qui ne se
   fait pas dans ce type de projet ?

## B. Gouvernance, financement, portée

6. Qui finance TI-FIG, et les financeurs participent-ils au projet (comité de pilotage,
   réunions, arbitrages) ?

7. Quels sont les livrables contractuels de TI-FIG, à quelles échéances, et qui les
   réceptionne ?

8. Y a-t-il des **mesures engageantes ou incitatives** prévues pour que les acteurs intègrent
   réellement les résultats du projet, ou le projet s'arrête-t-il à la production de
   connaissance ?

9. Que devient le travail après la fin du financement — quelqu'un est-il chargé de la suite ?

10. À qui le livre blanc de CALALOU a-t-il été diffusé, et y a-t-il eu des retours écrits ou
    des restitutions publiques ?

11. Entre l'article de 2015 et le démarrage de CALALOU en 2021, le modèle n'a pas évolué.
    Est-ce faute de financement, de demande, ou de personne disponible ?

## C. La suite du modèle et du code

12. Est-ce que l'un de vous deux, ou quelqu'un d'autre que moi, a déjà lancé un run complet ?
    Si non, je propose qu'on le fasse ensemble avant mon départ — c'est deux heures, et c'est
    le seul vrai test de transmissibilité.

13. Un successeur est-il prévu — stage, CDD, thèse — et à quelle échéance ?

14. Le dépôt de code doit-il devenir public (forge INRAE, GitHub) ? Quelle est la politique de
    l'unité sur ce point ? Cela change ce que je peux mettre en annexe du mémoire.

15. Quel est le statut juridique des données que j'utilise (RPG, Agreste, couches
    chlordécone) ? Que puis-je citer, reproduire ou publier ?

16. Le code est aujourd'hui en anglais et la documentation en français. Faut-il basculer
    entièrement en anglais pour la suite, ou le français est-il un choix de l'unité ?

17. La note technique interne que je dois vous laisser : à qui doit-elle s'adresser, et sous
    quelle forme la voulez-vous ?

## D. Points techniques que j'aimerais vérifier avec vous

En reprenant le modèle GAMS et la documentation des données, je suis tombé sur plusieurs
points que je préfère vous soumettre plutôt que trancher seul. Je les ai tous documentés et
portés tels quels dans la version Python, sans rien corriger en silence.

18. **Les deux couches chlordécone sont agrégées en sens opposés** : `RISQUE_CLD` prend le
    *minimum* de la classe rencontrée sur la parcelle, `CLD_REEL` le *maximum*. Ce sont les
    contraintes d'éligibilité de l'igname tutorée et de la prairie pâturée qui lisent
    `RISQUE_CLD`, donc la lecture la plus favorable : une parcelle à cheval sur une zone saine
    et une zone contaminée est traitée comme saine. Est-ce un choix assumé, un effet du
    traitement SIG, ou quelque chose qui n'avait pas été remarqué ?

19. **`Eq_VE_PLUIE` interdit les vergers pluviaux sur l'ensemble du territoire** : le test
    porte sur une colonne absente de la table, donc il est toujours vrai. `VE_PLUIE` ne peut
    apparaître dans aucune sortie. Est-ce que c'était connu ? Et faut-il relire à cette lumière
    le déficit de vergers que je constate en calibration (8 ha simulés contre 311 observés) ?

20. **Le plancher de surface en prairie du GAMS vaut la surface observée de 2017** — le
    fichier le documente lui-même ainsi. Il est donc circulaire au sens strict. Était-ce
    assumé ? (J'ai vérifié que mes conclusions ne dépendent pas de sa valeur, mais j'aimerais
    savoir comment vous le lisez.)

21. **Les rendements de `Rdt_Cult` valent 2 à 4 fois ceux publiés par Agreste**, sauf pour le
    melon. Comme cette table est celle de l'article de 2015, je ne l'ai pas touchée. Est-ce un
    écart de définition, un effet d'échelle expérimentale, autre chose ?

22. La documentation des données mentionne plusieurs **reprises manuelles** : 419 parcelles
    reclassées de café/cacao vers la canne, des surfaces d'ACA modifiées pour 2016, et trois
    parcelles de plus de 45° de pente ramenées à 45°. Y en a-t-il d'autres dont je devrais
    tenir compte avant de présenter l'assolement observé comme référence de calibration ?

23. Plusieurs de ces comportements viennent du modèle GAMS d'origine. **Avant toute
    valorisation**, il faudrait qu'on regarde ensemble lesquels ont pu peser sur des résultats
    antérieurs — je préfère poser la question maintenant que la laisser ouverte.

## E. Valorisation

24. Un article est-il envisagé à partir de ce travail ? Avec qui, à quelle échéance, et quelle
    serait ma place ?

25. Sur quoi porterait-il selon vous ? De mon côté, les trois résultats qui me semblent les
    plus transférables ne sont pas agronomiques mais méthodologiques : une contrainte de
    politique publique qui peut être satisfaite à coût nul quand les données ne distinguent pas
    les cultures qu'elle vise ; un front de Pareto entièrement inactif parce que paramétré sur
    la mauvaise référence ; et un score composite qui classe les politiques sur la finesse
    d'une nomenclature plutôt que sur leur performance. Je n'ai trouvé aucun des trois
    documenté ailleurs.

26. Y a-t-il une restitution prévue en Guadeloupe, et sous quelle forme ?

## F. Contexte du travail

27. Qui, dans TI-FIG, est basé en Guadeloupe, et depuis combien de temps ?

28. Comment l'unité travaille-t-elle avec les organisations agricoles guadeloupéennes — liens
    institutionnels, conventions, contacts ?

29. La question de la légitimité d'un modèle prescriptif produit depuis un centre de recherche
    national s'est-elle déjà posée dans le projet ? Sous quelle forme, et qu'en a-t-on fait ?

---

Merci d'avance — même des réponses courtes me seraient très utiles, et je suis disponible
quand vous voulez pour en discuter de vive voix.

Bien à vous,
Clément
