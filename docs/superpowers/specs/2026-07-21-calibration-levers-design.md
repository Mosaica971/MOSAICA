# Faire baisser le PAD : rétablir les mécanismes du modèle GAMS `CALIB`

_2026-07-21 — suite directe de `2026-07-21-calibration-validation-design.md`, qui a fourni
la métrique. Cette spec s'attaque à ce que la métrique a révélé._

## Point de départ

`scripts/evaluate_calibration.py` sur `outputs/output_12` : PAD territorial **193 %**, 7,3 %
des types d'exploitation reproduits, 7 % des parcelles. Dix des onze cultures observées
disparaissent, le maraîchage passe de 1 087 à 24 155 ha.

L'enquête dans le source GAMS a identifié la cause, et elle n'est pas une : **le modèle
résolu aujourd'hui n'est pas celui que l'article évalue**. `MODELE.txt:443-695` déclare trois
modèles — `INIT`, `CALIB`, `SCENARIO`. L'article évalue `CALIB` (§3.1), qui contient 76
équations. Cinq mécanismes de `CALIB` manquent chez nous, et ce sont précisément ceux qui
empêchent la bascule vers le maraîchage.

## Ce que l'enquête a établi

### L'aversion au risque est correctement portée — mais jamais utilisée

Vérification ligne à ligne contre `OPTIMISATION.txt:1745-1754` et `MODELE.txt:427` :

- les huit coefficients sont exacts (1.30 / 1.20 / 0.30 / 0.55 / 2.40 / 0.00 / 2.30, plus le
  dédoublement du type 4 en 41→0.50 et 42→1.60) ;
- l'objectif est algébriquement identique : GAMS `Σ(X·MB) − AVERS·Σ(X·MB·Var_Rdt)`, nous
  `Σ(Y·surface·MB·(1 − AVERS·Var_Rdt))` ;
- `AVERS` est indexé sur `STOCK_TYPE_EXPL("init")`, la typologie **observée** — c'est bien ce
  que fait `compute_avers`.

Sur les vraies données : 862 fermes de type 4, toutes avec un `TYPE_EXPL_Bis` renseigné,
**aucun `AVERS` NaN**. Correct, mais fragile : le dictionnaire Python n'a pas de clé 4 et
dépend de ce que le BIS soit toujours posé. Un NaN rendrait l'objectif indéfini.

`maximize_risk_adjusted_gross_margin` est en `enable: false` depuis une revue du 2026-07-08.

### Le risque est ce qui distingue les cultures

| Culture | Marge €/ha | `Var_Rdt` |
|---|---|---|
| MA_ROTA | 27 929 | **0,65** |
| PN_PIQ | 1 602 | **0,00** |
| CS_NGT_NISM | 1 521 | 0,20 |

Marge pondérée par l'aversion :

| `AVERS` | MA_ROTA | CS_NGT_NISM |
|---|---|---|
| 0,30 | 22 483 | 1 430 |
| 1,40 | 2 514 | 1 095 |
| 2,40 | **−15 640** | 791 |

Point d'équilibre à `AVERS ≈ 1,48` ; **2 505 exploitations sur 4 638 (54 %) sont au-dessus**.
Chez les éleveurs le maraîchage devient négatif : le modèle préfère la prairie, de variance
nulle. C'est le mécanisme décrit par l'article.

### Le plafond de main-d'œuvre est le verrou physique

La solution actuelle réclame **21 593 ETP**. La Guadeloupe de 2017 en comptait **3 598**.
Facteur 6. `Eq_MO_MAX_Expl` (`MODELE.txt:368`, Eq. 5 de l'article) plafonne chaque
exploitation au travail qu'exigeait son assolement observé. Une ferme cannière dispose de
12,7 h/ha ; le maraîchage en demande 1 653.

**Le point qui avait fait différer ce portage est plus nuancé que ne le dit `VIGILANCE.md`.**
La formule GAMS littérale (`ENTREES.txt:463-469`) calcule le plafond sur `Matrice_Parc_Cult`,
qui pointe sur les codes **agrégés** — et 9 des 12 n'ont aucune ligne ITK
(`Matrice_OTK_Cult` : colonnes AN/BA/BC/CS/IG/MA/NC/PN/VE entièrement nulles ; seules AG, JA
et ME, les familles sans variante fine, sont renseignées). Le plafond littéral serait donc
nul pour la plupart des fermes, et le modèle GAMS lui-même produirait une allocation vide.
Avec les cultures représentantes, **aucune des 4 588 fermes n'a un plafond nul**.

### Quatorze cultures que le GAMS interdit et que nous autorisons

Les équations `Eq_*_SUPP` (`MODELE.txt:324-340`) suppriment purement des activités :
les 8 codes agrégés (`AN`, `BA`, `BC`, `CS`, `IG`, `MA`, `PN`, `VE`), `TH`, `PN_TOUR`, les 10
`CF_*`, `CS_SBT_NISM`, `CS_MG_NIM`. Aucune n'est portée. Notre run a placé 528 parcelles sur
`TH`, que le GAMS bannit. Environ **350 000 variables fantômes** en découlent, sur 1,68 M.

Corollaire : `baseline_representative_crops` fait pointer la prairie sur `PN_TOUR`, culture
interdite par le GAMS. La bonne représentante est `PN_PIQ`, celle sur laquelle porte
`Eq_PN_PROD_MIN`.

### Les minima de production ne concernent pas la calibration

`Eq_*_PROD_MIN` et les objectifs alimentaires (`Eq_LEG/TUB/FRU/PAT_PROD_OBJ`) figurent dans
le modèle **`SCENARIO` seulement**, pas dans `CALIB`. Hors périmètre.

## Les cinq changements

### 1. Activer l'objectif de Markowitz

`config.yaml` : `maximize_risk_adjusted_gross_margin` → `enable: true`,
`maximize_gross_margin` → `enable: false` (exactement un objectif actif).

Plus une valeur de repli explicite : `_AVERS_BY_TYPE_EXPL[4] = 1.40`, la valeur que GAMS pose
avant de l'écraser par 41/42. Aucun effet sur les données réelles (le BIS est toujours posé),
mais supprime la possibilité d'un `AVERS` NaN, qui propagerait un objectif indéfini.

### 2. Porter les suppressions `Eq_*_SUPP`

14 entrées `forbid_crops` dans `config.yaml`, regroupées sous un commentaire commun ancré sur
`MODELE.txt:324-340`. Les codes agrégés méritent leur propre commentaire : ils existent pour
**encoder la baseline observée**, pas pour être choisis — leur économie est nulle, donc le
solveur ne les choisirait de toute façon jamais, mais ils coûtent des variables.

### 3. Corriger la prairie représentante

`baseline_representative_crops` : `PN: PN_TOUR` → `PN: PN_PIQ`.

Effet de bord assumé : les indicateurs du **côté entrée** changent (marge, ETP, production de
la prairie), et le golden snapshot bougera. C'est une correction, pas une régression.

### 4. Porter `Eq_MO_MAX_Expl`

Nouvelle contrainte **générique** dans `core/model/constraints.py` :

```python
@register_constraint("farm_labor_hours_max")
def build_farm_labor_hours_max_constraint(model, inputs, *, label, slack=1.0, **_args)
```

`Σ_{parcelles de la ferme} Y[p,c] · surface[p] · crop_labor_hours_per_ha[c] ≤ slack ·
farm_labor_capacity_hours[ferme]`

Deux champs nouveaux dans `ModelInputs`, en vocabulaire neutre :
`crop_labor_hours_per_ha` et `farm_labor_capacity_hours`. `core/` continue de ne rien savoir
de la Guadeloupe.

Le plafond est calculé dans `data_pipeline` : pour chaque parcelle, sa surface multipliée par
la MO/ha de la **culture représentante** de son groupe observé, sommé par exploitation. La
substitution par les représentantes est la même hypothèse, déjà documentée, que celle des
indicateurs d'entrée — elle est ici étendue à une contrainte qui **influence l'allocation**,
ce qui est un changement de nature à consigner dans `VIGILANCE.md`.

`slack` (défaut 1.0) mirroir des multiplicateurs de scénario que GAMS garde en commentaire
juste sous la formule (`ENTREES.txt:470-472` : « x 1.7 pour S1, x 1.3 pour S2, x 10 pour S3 »).
Il donne le moyen de relâcher le plafond sans toucher au code si 1.0 se révèle trop dur.

Pas de risque d'infaisabilité : une exploitation qui ne peut rien planter laisse ses parcelles
vides, ce que `at_most_one_crop_per_plot` autorise.

### 5. Réactiver `Eq_CS_GFA`

L'infaisabilité documentée est réelle et chirurgicale : **3 fermes sur 4 588** (`E1471`,
`E273`, `E3955`) ont toutes leurs parcelles verrouillées en friche par `friche_lock`, donc
zéro parcelle éligible à la canne, alors que la contrainte en exige 60 %.

Nouvel argument `skip_when_no_eligible_area` (défaut `false`, donc comportement actuel
inchangé pour qui ne le demande pas), mis à `true` dans `config.yaml` : la contrainte rend
`Constraint.Feasible` au lieu de `Constraint.Infeasible` quand la ferme n'a aucune parcelle
éligible à la culture exigée. **C'est une déviation assumée du GAMS**, à consigner : le GAMS
serait infaisable là où nous ignorons la ferme. Portée : 3 fermes, ~0,07 % des exploitations.

## Ordre d'application et mesure

Les cinq changements partent ensemble, par choix de l'utilisateur. Pour que le diagnostic
reste possible si le résultat déçoit, chacun est un **commit séparé** et les quatre premiers
sont **désactivables par un drapeau de config** — seul le portage de `Eq_MO_MAX_Expl` ajoute
du code neuf, et il est lui aussi derrière un `enable`.

La mesure se fait en un solve réel puis `scripts/evaluate_calibration.py` sur le run produit.
Le solve devrait être **plus rapide** qu'avant (~350 000 variables retirées par les
suppressions), ce qui est le seul effet secondaire favorable de ce lot.

## Ce que cette spec ne promet pas

Aucune valeur de PAD cible. Toute l'analyse ci-dessus est **analytique** : elle démontre que
les mécanismes manquants sont ceux qui bloquent la bascule observée, elle ne prédit pas le
chiffre qui sortira. Les leviers 1 et 4 ont un effet mécanique démontrable ; le levier 5 ne
couvre que 5 286 ha de GFA contre 12 813 ha de canne observés, soit 41 % du besoin.

Il restera vraisemblablement un écart. Les canniers **spécialisés** (`AVERS = 0.30`, 1 371
fermes) ne sont retenus ni par l'aversion au risque ni par le GFA s'ils n'en ont pas : seul le
plafond de main-d'œuvre les gèle. Si le PAD reste élevé après ce lot, c'est là qu'il faudra
regarder en premier.

## Hors périmètre

- Les équations `Eq_*_PROD_MIN` et les objectifs alimentaires : modèle `SCENARIO`, pas
  `CALIB`.
- Le bloc canne fibre (`Eq_CF_*` au-delà de la suppression `Eq_CF_SUPP`) : lot séparé déjà
  cadré dans `TODO.md`.
- Toute recherche itérative sur les coefficients Ø (§2.5 de l'article) : ils sont déjà ceux de
  la Table 2.
- Le réglage de `slack` : le défaut 1.0 est la lecture fidèle ; l'ajuster demande d'abord une
  mesure.
