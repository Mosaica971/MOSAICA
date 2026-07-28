# Pourquoi le portage CALIB ne reproduit pas les résultats de l'article — investigation de parité

_2026-07-27._ Investigation systématique (skill `systematic-debugging`) de l'écart entre notre
portage Python du modèle **CALIB** de MOSAICA et les résultats publiés par Chopin et al. (2015).

> **⚠ Partiellement corrigé le même jour** par
> `2026-07-27-modalites-solveur-plantain-design.md`, à lire ensuite. Ce qui tient : la fidélité
> du portage (objectif, AVERS, économie, mapping, bans). Ce qui change :
> - **Le blocage #2 (« gap MIP ») n'est pas une cause majeure.** Mesuré : le plan observé vaut
>   15 % de moins que l'optimum sous notre propre objectif, et trois graines HiGHS donnent
>   0,15 point de PAD d'écart. La frontière plate prairie/canne est réelle mais pèse ~3 %.
> - **Le blocage #1 se précise** : l'article travaille sur **2010** (nous 2017) ; à parcelles et
>   hectares quasi identiques il a 5 336 fermes contre nos 4 638 — de la concentration foncière,
>   pas un échantillonnage différent.
> - **La cause dominante manquait** : le plantain (+20,9 M€ sur un écart de 12,8 M€), et la
>   contrainte qui le borne (`Eq_BC_QUOTA_MAX`) existe dans le GAMS comme dans l'article.

## La question

L'article annonce, pour son modèle **CALIB** (celui que valide le §3.1) :
- PAD territorial **< 15 %** sur 8 usages/10 (Fig. 4) ;
- **81 %** des exploitations dans le bon type (Table 4) ;
- 66 % des parcelles / 77 % de la surface bien simulées (Table 5).

Notre portage, avec les **mêmes** coefficients et le **même** objectif, donne (run `output_2`) :
PAD **49,3 %**, types **63,3 %**, parcelles 55,1 % / surface 63,1 %. Le modèle est censé être
identique. **Où sont les points de blocage ?**

## Méthode

Comparaison source-à-source : GAMS (`old_code_gms_format_now_txt/`) et l'article
(`Chopin et al 2015 pour Hal.pdf`) contre notre pipeline, sans jamais se fier à la mémoire de
session. Diagnostics parcellaires sur `output_2` (sans solve).

## Ce qui est CONFIRMÉ FIDÈLE (écarté comme cause)

1. **Objectif** : `SOLVE CALIB using mip maximizing REV_MARKOVITZ_GWAD` (OPTIMISATION.txt:179).
   C'est notre `maximize_risk_adjusted_gross_margin`. ✓
2. **Coefficients d'aversion (Table 2)** : l'article dit explicitement (§2.5) que Table 2 **est**
   le résultat de la calibration par 100 itérations — « the set of risk aversion coefficients
   that provided satisfying results ». Nos valeurs (`_AVERS_BY_TYPE_EXPL` : 1.3/1.2/0.3/1.4/
   0.55/2.4/0/2.3) = Table 2 à l'identique. ✓ **Ce ne sont pas des coefficients à re-tuner : ce
   sont déjà les coefficients calibrés.**
3. **Économie (marge incl. subventions)** : GAMS `MB_HA_Cult = PB_HA_Cult − CV_HA_Cult` avec
   `PB = (Rdt×(Prix+Bagasse) + SUB_TOT)/Durée×12` (OPTIMISATION.txt:22-41). Notre
   `margin = sales − cost + subsidy` reproduit exactement. Canne, prairie, plantain, ananas
   comparés à Table 1 : prairie 1602 ≈ Table 1 1590 ✓ ; les marges de canne subvention-dominées
   (jusqu'à 4023) viennent des données sources (`indice_H/`), GAMS lisait les mêmes. ✓
4. **Mapping RPG code → groupe de base** : `_RPG_CODE_TO_BASE_GROUP` = ENTREES.txt:60-105 à
   l'identique. Donc, sur *nos* fermes, chaque ferme reçoit le bon type observé et donc le bon
   AVERS. ✓
5. **Direction des bans chlordécone** : `Eq_IG_CLD` (forbid IG_TUT si RISQUE_CLD≤3) et
   `Eq_PN_PIQ_CLD` (forbid PN_PIQ si RISQUE_CLD==1) — nos règles `max_risk_threshold` /
   `exact_risk_value` ont la **bonne** direction (les commentaires de config étaient trompeurs,
   le code juste). ✓

## LES POINTS DE BLOCAGE (causes réelles de l'écart)

### Blocage #1 — Provenance des données : 4588 fermes vs 5336 (article)

La Table 4 de l'article totalise **5336 exploitations** ; notre extrait en a **4588** (−14 %).
Les distributions par type diffèrent aussi (proportions proches pour les gros types, mais arbo
2,3 %→1,5 %, maraîchers 2,9 %→4,7 %, canniers-éleveurs 16 %→13 %). Comme le mapping typologique
est identique (point fidèle #4), cet écart est **purement une différence de jeu de données** :
notre `data/` est un sous-ensemble différent de la base géographique de l'article. Non corrigeable
ici (données absentes). Fixe un plafond structurel : agrégats de surface et population
d'exploitations différents ⟹ PAD et matrice de confusion ne peuvent pas coïncider exactement.

### Blocage #2 — Le gap MIP de 1 % noie la frontière prairie/canne

Le vrai mécanisme de l'effondrement « éleveurs → canniers » (recall éleveurs article 98 %,
nous 53 %). Diagnostic parcellaire sur les 3054 ha de prairie observée passés en canne :
- l'essentiel est sur des fermes à **AVERS élevé** (2,40 : 1572 ha ; 2,30 : 651 ha) — donc bien
  des éleveurs, pas des canniers ;
- **la prairie y était ÉLIGIBLE** (2585/2660 plots, 2972 ha) — le solveur avait le choix ;
- **882 plots (1403 ha) partent en canne alors que la prairie est éligible ET meilleure** au
  vrai AVERS (radj prairie 1602 vs canne 1034-1386). Sous un objectif séparable par parcelle,
  c'est **impossible** à l'optimum exact.

Explication : `mip_rel_gap = 0.01`. Objectif = 85,9 M€ ⟹ **859 k€ de tolérance**. La frontière
prairie(1602)/canne(1521-1617, dont les variantes Marie-Galante à Var_Rdt=0) est distante de
**< 1 %** sur une large surface ; le solveur y est **indifférent** et résout ~3000 ha
arbitrairement, majoritairement en canne. Le leak « irrationnel » (~1403 ha × ~300 €/ha ≈ 420 k€)
tient entièrement dans le gap. **Ce n'est pas un bug de modèle : c'est de la tolérance de solveur
sur une frontière économiquement plate.** Contrainte : au gap par défaut (1e-4) le solve complet
ne terminait pas en 37 h (cf. VIGILANCE) — le gap ne peut donc pas être annulé, seulement resserré
prudemment.

### Blocage #3 — Petites déviations CALIB (chacune modeste, cumulables)

Équations **présentes dans le bloc modèle CALIB** de GAMS mais absentes/altérées chez nous :
- **`Eq_PN_PIQ_CLD` appliqué à tort** : il interdit la prairie sur les 3975 plots RISQUE_CLD==1
  (16 % du territoire), mais il **n'est pas dans le bloc CALIB** (commenté en SCENARIO,
  MODELE.txt:626) — contrairement à `Eq_IG_CLD` qui, lui, y est. **CORRIGÉ 2026-07-27** (désactivé) :
  la prairie repasse de 76,5 % à 90 % des plots éligibles.
- **`Eq_AN_PA` non porté** (différé) : interdit AN_PA sur les exploitations trop petites. L'ananas
  est +488 % sur-planté (132→780 ha). Candidat de portage (règle catégorielle indexée ferme).
- **`Eq_CF_*` non câblé** (bloc canne fibre) : présent en CALIB, économie faible, effet probable
  mineur.
- **`Eq_CS_GFA` désactivé** par choix (infaisable avec le plafond de main d'œuvre) — mais il
  *forcerait plus* de canne, donc n'aide pas la prairie.
- **`Eq_BA_QUOTA_Expl` écarté** : sa RHS `REF_BAN_EXPL_init` lit `Matrice_Parc_Cult` sur les
  variantes fines de banane, absentes de l'observé agrégé ⟹ REF≡0. C'est un plafond (`=l=`), il
  ne peut de toute façon pas *restaurer* la banane sous-plantée (plantain la colonise, 1252 ha).

## Conclusion : la nature de l'écart

L'article a atteint 81 %/<15 % en calibrant l'AVERS (Table 2) **sur ses 5336 fermes**. Sur notre
extrait de 4588 fermes, avec les mêmes coefficients et la même économie, l'optimum exact devrait
s'en approcher — mais **(a)** le jeu de données diffère (blocage #1, irréductible) et **(b)** le
gap de 1 % qu'impose la tractabilité brouille une frontière prairie/canne économiquement plate
(blocage #2). Ce ne sont **pas des bugs de portage** ; ce sont les deux contraintes réelles qui
séparent notre CALIB du CALIB de l'article. Les corrections de parité fidèles (blocage #3),
en commençant par `Eq_PN_PIQ_CLD`, réduisent l'écart sans dévier du CALIB.

## Corrections appliquées (fidèles au CALIB) et mesures

1. **Désactiver `Eq_PN_PIQ_CLD`** (fait) — parité CALIB, prairie éligible 76,5 %→90 % des plots.
   Effet mesuré (output_3) : PAD 49,3→49,0 %, types 63,3→63,8 %. **Marginal** — confirme que le
   gap MIP, pas l'éligibilité, domine.
2. **Resserrer le gap MIP** — **TESTÉ (output_4, gap 1e-3) et ABANDONNÉ.** Le solve tape le
   time_limit d'1 h avec un incumbent identique à la solution 1 % (PAD 49,3, types 63,7 — zéro
   prairie récupérée). Le B&B ne ferme pas la frontière plate en temps traitable. `solver.py`
   modifié pour charger l'incumbent sur `maxTimeLimit` ; gap laissé à 1 % (optimum traitable).
   **Le leak de prairie est une limite d'intractabilité B&B, pas un bouton de réglage.**
3. **Porter `Eq_AN_PA`** (fait) — AN_PA interdit sur fermes < 10 ha (via colonne `SURF_EXPL_PARC`).
   Vraie contrainte CALIB, gagnée en fidélité. Effet mesuré : voir run combiné.

## Verdict final

Sur les trois points de blocage : #1 (données, 4588 vs 5336 fermes) est **irréductible** ;
#2 (gap MIP) est un **diagnostic correct mais non actionnable** (intractabilité B&B sur frontière
plate) ; #3 (déviations CALIB) est **corrigé** mais d'effet marginal. **Conclusion : notre CALIB
est fidèle** (objectif, AVERS, économie, mapping, bans tous vérifiés exacts) ; l'écart aux 81 %/
<15 % de l'article vient d'un **jeu de données différent** et d'une **frontière prairie/canne
économiquement plate que le B&B ne tranche pas comme la leur** — pas de bug de portage. Les
corrections de parité (#3) rapprochent sans dévier, mais le plateau ~49 %/64 % est structurel.

Mesures dans VIGILANCE.md (entrée calibration) et la mémoire `project_calibration_workstream`.
