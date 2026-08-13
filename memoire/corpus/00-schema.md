# Corpus — schéma et conventions

Ce dossier n'est pas un document. C'est **l'inventaire typé de tout ce que le stage a décidé,
mesuré, écarté ou raté**, avec les arcs qui relient chaque item à ce qui le justifie et aux
branches qu'il a fermées.

Il sert à quatre choses, dans cet ordre :

1. **Prouver qu'aucun choix n'est arbitraire.** Tout item `retenu` **et décidé** — `choix`,
   `methode`, `organisation`, `perspective` — doit porter un arc `parce-que`. Un `resultat`,
   une `donnee`, une `notion`, un `piege` ou une `erreur` en est dispensé : un fait ne se
   justifie pas, il s'établit, et c'est `source:` qui en répond. (La première version de la
   règle ne faisait pas cette distinction et réclamait une justification à des faits, ce qui
   noyait les vrais manques sous 26 fausses alertes.)
2. **Prouver que les branches coupées l'ont été sur mesure et non par intuition.** Tout item
   `statut: ecarte` doit porter un arc `mesure-par`. Un écart sans mesure est une opinion.
3. **Dériver le plan** du mémoire, des annexes, de l'oral et de la note technique depuis la
   topologie plutôt que depuis le goût du rédacteur.
4. **Contrôler la couverture** : un item destiné à un chapitre et absent du `.tex` est un oubli.

---

## Schéma d'un item

```yaml
- id: SOLV-02                        # PREFIXE-nn, stable, jamais réattribué
  titre: >
    Un solve arrêté à la limite de temps rend un incumbent prouvablement faux
  type: piege                        # cf. table ci-dessous
  statut: retenu                     # cf. table ci-dessous
  severite: majeur                   # critique | majeur | mineur | null
  quand: 2026-07-29                  # date de l'établissement du fait, si connue
  source:                            # d'où vient l'affirmation — vérifiable
    - docs/04-vigilance.md#B.2
    - scripts/repair_allocation.py
    - commit 0c51607
  chiffre: [mesIncumbentGain, mesIncumbentEcart]   # macros de chiffres.tex, ou []
  destination: [ch2, oral]           # ch0..ch6 | annexeA..F | oral | note | article | aucune
  arcs:
    parce-que: [SOLV-01]             # le nœud parent : ce qui rend cet item nécessaire
    justifie: [SOLV-05, SOLV-06]     # les enfants : ce que cet item rend nécessaire
    ferme-la-branche: [SOLV-B1]      # l'alternative explorée puis coupée
    mesure-par: [VER-04]             # le protocole qui a tranché
    contredit: []                    # un item antérieur que celui-ci renverse
  critique: >
    Découvert tard. Les leviers de calibration instruits en juillet ont été
    diagnostiqués « bloqués par la modélisation » avant qu'on établisse que
    c'était le solveur.
```

Champs obligatoires : `id`, `titre`, `type`, `statut`, `source`, `destination`.
Tout le reste peut être `null` ou absent.

### Les trois échappatoires, et pourquoi elles sont des champs et non du silence

Une règle sans exception se contourne en silence. Chacune des trois règles ci-dessous
a donc une sortie **déclarée**, que l'audit **compte et affiche** — ce qui rend
l'exception opposable au lieu de la cacher dans une prose de `critique:`.

| champ | remplace | ce qu'il affirme |
|---|---|---|
| `racine: true` | un `parce-que` | c'est un axiome, posé et non déduit |
| `sans-mesure: <raison>` | un `mesure-par` | la branche est coupée par une **preuve** ou une contrainte externe, pas par une mesure |
| `verdict-anterieur: <texte>` | un `contredit` | la croyance renversée n'avait pas d'`id` parce qu'on ne l'avait jamais écrite |

Le troisième est le cas **normal**, pas l'exception : sur 19 verdicts renversés, 19
portaient sur une croyance jamais consignée. C'est précisément ce qui les rend
intéressants — on ne consigne pas ce qu'on croit évident.

---

## `type` — la nature de l'item

| valeur | ce que c'est | exemple |
|---|---|---|
| `choix` | une décision de conception prise et assumée | porter les bugs GAMS tels quels |
| `resultat` | un fait établi par une mesure | la canne revient à 12 782 ha sans contrainte |
| `piege` | une lecture qui produit un chiffre faux mais crédible | citer le PAD territorial de 6,6 % |
| `erreur` | une faute commise, corrigée ou non | la règle de sol de l'ananas était inversée |
| `notion` | un concept à expliquer au lecteur | branch-and-bound, warm start, borne LP |
| `methode` | un protocole de travail ou de preuve | balayage de seuil pour distinguer correction et ajustement |
| `organisation` | une pratique de projet, de code, de documentation | un commit = un fait mesuré, message en français |
| `donnee` | ce que le jeu contient ou ne contient pas | pas de pluviométrie mensuelle |
| `perspective` | ce qui reste à faire, et ce qui le rend nécessaire | intégrer l'élevage, porter MAELIA |
| `reflexivite` | un retour sur la position, la posture, l'effet du travail | le catalogue politique écrit seul |

## `statut` — où en est l'item

| valeur | sens |
|---|---|
| `retenu` | en vigueur dans le dépôt aujourd'hui |
| `ecarte` | exploré puis abandonné — **doit porter un `mesure-par`** |
| `differe` | identifié, non fait, avec la raison |
| `erreur-a-posteriori` | fait ou cru, puis démenti — **doit porter un `contredit`** |
| `ouvert` | question non tranchée à la fin du stage |

## `severite`

Reprend la convention de `docs/04-vigilance.md` : `critique` (fausse un résultat),
`majeur` (limite fonctionnelle réelle), `mineur` (à connaître). `null` hors pièges.

## `destination`

`ch0` intro · `ch1` terrain · `ch2` porter · `ch3` calibrer · `ch4` explorer ·
`ch5` discussion · `ch6` conclusion · `annexeA` formulation · `annexeB` portage ·
`annexeC` scénarios · `annexeD` résultats · `annexeE` calibration · `annexeF` chronologie ·
`oral` · `note` (note technique interne) · `article` · `aucune` (archivé, ne sert nulle part).

**Le budget commande.** Le cœur du mémoire vaut 30 pages et est déjà à 25 avec des
placeholders : `destination: [chN]` est un engagement de place, pas une étiquette de thème.

---

## Les cinq arcs

| arc | question à laquelle il répond |
|---|---|
| `parce-que` | qu'est-ce qui a rendu ce choix nécessaire ? (remonte vers la racine) |
| `justifie` | qu'est-ce que ce choix a rendu nécessaire ? (descend vers les feuilles) |
| `ferme-la-branche` | quelle alternative a-t-on explorée puis coupée, ici ? |
| `mesure-par` | quel protocole a tranché ? un balayage, trois graines, un calcul hors modèle |
| `contredit` | quel verdict antérieur cet item renverse-t-il ? |

`parce-que` et `justifie` sont réciproques, et **les fichiers restent volontairement
asymétriques** : on pose le sens qui vient à l'écriture, `audit_corpus.py` pose l'autre en
mémoire. Tenir les deux sens à la main sur 1 267 arcs produirait des incohérences sans
ajouter d'information.

## L'audit

```bash
.venv/Scripts/python memoire/audit_corpus.py            # rapport -> corpus/_audit.md
.venv/Scripts/python memoire/audit_corpus.py --graph    # + _graphe.dot, _graphe-<PREFIXE>.mmd
.venv/Scripts/python memoire/audit_corpus.py --strict   # sortie non nulle si une règle casse
```

Le rapport `_audit.md` est **généré** : ne pas l'éditer. Il donne, outre les trois règles,
la charge par destination (le budget de pages), les chaînes les plus profondes (les fils
narratifs), les macros de `chiffres.tex` jamais citées, et les items destinés à un chapitre
dont aucun chiffre n'apparaît dans le `.tex` correspondant.

Les items de branche coupée portent le suffixe `-B` (`SOLV-B1`) : ce sont des nœuds à part
entière, avec leur propre `mesure-par`, parce qu'**une branche coupée sans raison consignée
est le seul vrai défaut de méthode que ce corpus cherche à débusquer**.

---

## Fichiers

| fichier | domaine | préfixe |
|---|---|---|
| `10-contexte-commande.yaml` | territoire, projet TI-FIG, lettre de mission, ce qui a dérivé | `CTX` |
| `20-portage-gams.yaml` | parité, bugs portés, équations, inventaire | `PORT` |
| `30-architecture-logicielle.yaml` | registre, core/case_study, YAML, dashboard | `ARCH` |
| `40-solveur-tractabilite.yaml` | MILP, branch-and-bound, warm start, symétrie, borne LP | `SOLV` |
| `50-donnees.yaml` | ce que le jeu contient, ce qu'il ne contient pas, le SIG | `DON` |
| `60-calibration.yaml` | PAD, référence 2017, déviations, plateau | `CAL` |
| `70-prospective.yaml` | politiques, forçages, fronts, robustesse, grille | `PROS` |
| `80-indicateurs.yaml` | environnement, eau, carbone, Rpest, résilience, score composite | `IND` |
| `90-verification-outillage.yaml` | tests, golden, références, feasibility, audits | `VER` |
| `95-methode-organisation.yaml` | commits, docs, specs, langue, style de code, rythme | `MET` |
| `96-reflexivite.yaml` | position, posture, performativité, encadrement, rapport à Claude | `REF` |
| `97-perspectives.yaml` | élevage, pêche, MAELIA, anglais, Excel, formation, multi-périodes | `PERSP` |
| `98-article.yaml` | ce qui est neuf vs Chopin 2015, ce qui manque | `ART` |
