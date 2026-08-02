# Score de stabilité : exposition d'une allocation aux aléas climatiques et économiques

_2026-07-20 — spec 2 sur 3 du chantier « indicateurs d'impact »._

## Contexte

Le modèle compare aujourd'hui des scénarios sur leur performance **moyenne** : marge, revenu,
production, ETP, et depuis la spec 1 l'eau et le carbone du sol. Rien ne dit à quel point ce
résultat est **fragile**. Deux scénarios de marge identique ne se valent pas si l'un la tire de
cultures stables et diversifiées et l'autre du maraîchage en monoculture.

Cette spec ajoute trois indicateurs d'exposition. Périmètre, comme les autres lots du
chantier : **reporting seul**. Calculés après le solve, ils n'influencent ni l'allocation ni la
faisabilité, et aucun solve réel n'est nécessaire pour les valider.

La spec 3 (Rpest / Tixier) reste à cadrer.

## Ce que ces indicateurs mesurent — et ce qu'ils ne mesurent pas

Ils mesurent l'**exposition d'une allocation figée**. La question posée est : *si l'aléa tombe
une fois les assolements décidés, qu'est-ce qui est en jeu ?*

Ils ne mesurent **pas** la résilience au sens de la capacité d'adaptation. Un vrai test
d'adaptation demanderait de ré-optimiser sous contrainte choquée et d'observer de combien
l'optimum se dégrade. Ce n'est pas ce qui est construit ici, et l'écrire importe : « score de
stabilité » se lira spontanément comme « résilience », ce qu'il n'est pas.

### Distinction à ne pas perdre : les leviers de scénario font déjà l'autre chose

`config.yaml` expose déjà `price_multipliers` et `yield_multipliers` (le pipeline commente ce
dernier « climate shock »). Ces leviers appliquent le choc **avant** le solve, donc
l'optimiseur s'y adapte : ils répondent à « quel est le meilleur assolement dans un monde
choqué ? ». Les indicateurs de cette spec appliquent le choc **après**, sur une allocation
donnée : « que devient *cet* assolement si le choc tombe ? ».

| | Levier `*_multipliers` existant | Indicateur de cette spec |
|---|---|---|
| Choc appliqué | avant le solve | après, allocation figée |
| L'optimiseur s'adapte | oui | non |
| Coût | un solve réel (~30-55 min) | post-traitement, gratuit |

Les deux sont légitimes et complémentaires. Confondre les deux ferait conclure au doublon et
supprimer l'un des deux.

## Les trois indicateurs

### 1. Marge à risque climatique

```
climate_margin_at_risk       = Σ_parcelles  surface × marge/ha × Var_Rdt[culture]     (euros)
climate_margin_at_risk_ratio = climate_margin_at_risk / marge_totale                  ([0,1])
```

**Ancrage GAMS.** `Var_Rdt_Cult` est une **fraction de perte de marge**, pas un coefficient de
variation. Le GAMS l'emploie ainsi aux deux endroits où il apparaît :
- `OPTIMISATION.txt:70` — `MB_Ha_Cult_Pond = MB_Ha_Cult − MB_Ha_Cult × Var_Rdt_Cult("INIT")`
- `MODELE.txt:427` — pénalité de l'objectif Markovitz : `Σ X × MB_Ha_Cult × Var_Rdt_Cult × AVERS`

Il n'y a donc **ni carré, ni covariance, ni hypothèse d'indépendance** à formuler : la perte
attendue est linéaire en surface. Une première esquisse de cette spec proposait une variance de
portefeuille façon Markowitz avec des bornes indépendant/choc commun ; c'était fondé sur une
lecture erronée de `Var_Rdt_Cult` et a été abandonné.

**Les données sont saines** (vérifié sur `Var_Rdt_Cult.txt`, colonne `init`, 84 cultures) :
10 valeurs distinctes de 0 à 1, identiques sur toutes les colonnes d'année — ce qui est
cohérent avec le pipeline qui épingle délibérément `var_rdt_cult` sur `init`.

| `Var_Rdt` | Cultures |
|---|---|
| 0 | `CS` (agrégat), `CS_MG_*` (canne Marie-Galante), `JA` (jachère), `PN*` (prairies) |
| 0,1 – 0,45 | 36 cultures |
| 0,65 – 0,7 | 31 cultures, dont les 28 `MA_*` (maraîchage) |
| 1,0 | `NC` (non cultivé) |

Le classement est agronomiquement crédible : maraîchage le plus exposé, prairies et jachère
nulles. Ce contrôle de non-dégénérescence est fait **avant** conception, précisément parce que
la spec 1 a livré un indicateur (mois de pointe du besoin en eau) rendu inutile par des données
plates que personne n'avait regardées.

**Pas de pondération par `AVERS`.** L'indicateur mesure l'exposition objective ; le pondérer par
l'aversion déclarée des exploitants mélangerait exposition et préférence, et rendrait deux
territoires non comparables. `AVERS` reste disponible et sert déjà à l'objectif Markovitz.

### 2. Concentration du revenu (Herfindahl)

```
revenue_concentration_hhi = Σ_cultures (revenu_culture / revenu_total)²        ([1/n, 1])
```

`Var_Rdt` capture un risque **intrinsèque à la culture**. Il ne voit pas qu'un scénario tirant
80 % de son revenu d'une seule culture est fragile à tout ce qui frappe cette culture —
effondrement de prix, maladie, fermeture d'un marché, retrait d'une aide. Les deux angles sont
complémentaires.

**Sur le revenu, pas sur la marge — c'est délibéré.** La marge peut être négative pour certaines
cultures, surtout côté baseline où les cultures représentantes ne sont pas choisies pour leur
rentabilité. Un indice de Herfindahl sur des parts négatives n'a aucun sens : les parts ne
somment plus à 1 et l'indice peut sortir de [0,1]. Le revenu (ventes + subventions) est toujours
≥ 0, donc l'indice reste bien défini.

Le cas dégénéré `revenu_total = 0` (allocation vide, ou zone filtrée sans culture valorisée)
renvoie `0.0`, pas une division par zéro.

Complémentaire de `compute_shannon_diversity`, déjà présent, qui mesure la diversité en
**surface**. Une monoculture de surface peut être diversifiée en revenu et réciproquement.

### 3. Perte sous choc de prix

```
price_shock_margin_loss       = Σ_parcelles surface × δ × rdt × prix / durée_cycle × 12
price_shock_margin_loss_ratio = price_shock_margin_loss / marge_totale
```

`δ` (défaut **0,20**) est configurable dans `config.yaml`, sous la clé
`resilience.price_shock_delta`.

**Forme close, pas de recalcul de la chaîne économique.** La marge vaut
`ventes + subventions − coûts variables`, avec
`ventes = rdt × (prix + bagasse) / durée_cycle × 12` (`economics.compute_sales_per_ha_cult`).
Un choc `δ` sur `prix_cult` :
- ne touche pas les **subventions** — POSEI et les aides sont des montants fixes, pas indexés
  sur les cours ;
- ne touche pas les **coûts variables** — récolte et transport sont proportionnels au rendement,
  pas au prix ;
- ne touche pas la **bagasse**, valorisation énergétique d'un sous-produit, dont le prix ne suit
  pas les cours du produit principal. C'est un choix ; il est signalé ici parce qu'il est
  discutable, et le changer est une ligne.

La perte est donc exactement `δ × rdt × prix / durée_cycle × 12` par hectare, sans réexécuter
`economics.py`.

Le choc est **uniforme sur toutes les cultures**. Un choc ciblé sur les seules cultures d'export
(banane, canne) serait plus réaliste pour la Guadeloupe, mais imposerait de maintenir dans la
config une liste de cultures export à faire suivre les 84 cultures — coût de maintenance
disproportionné pour un indicateur de comparaison. Le choc uniforme se lit simplement comme
« quelle part de la marge repose sur le revenu de marché ».

## Architecture

Un module pur, sans I/O, testable sans `data/`, sur le modèle de `water.py` et `soil_carbon.py`.

### `case_studies/guadeloupe/resilience.py`

```
compute_climate_margin_at_risk_per_ha_cult(margin_per_ha_cult, var_rdt_cult) -> Series
compute_price_shock_loss_per_ha_cult(rdt_cult, prix_cult, duree_cycle_cult, delta) -> Series
compute_revenue_concentration_hhi(revenue_by_crop: Series) -> float
```

Les deux premières rendent des taux **par culture**, appliqués ensuite à l'allocation — même
motif que tous les indicateurs existants sauf le carbone du sol. Aucune n'est parcellaire :
`Var_Rdt` et le choc de prix dépendent de la culture seule, pas du sol ni de la parcelle. Le
module est donc plus simple que `soil_carbon.py`.

### Agrégation — `reporting/indicators.py`

Nouvelle fonction `compute_resilience_totals(dataset, allocation, price_shock_delta)`, distincte
de `compute_environmental_totals` : ces indicateurs ne sont pas environnementaux, et
`compute_environmental_totals` est déjà chargée.

Elle renvoie les cinq scalaires : `climate_margin_at_risk`, `climate_margin_at_risk_ratio`,
`revenue_concentration_hhi`, `price_shock_margin_loss`, `price_shock_margin_loss_ratio`.

Réutilise `compute_total_revenue_by_crop`, déjà présent, pour alimenter le HHI.

### Intégration au dashboard — les deux endroits, pas un seul

| Fichier | Ajout |
|---|---|
| `dashboard/comparison.py` | 5 entrées dans `INDICATOR_DIRECTION`, toutes `cost` |
| `dashboard/pages/2_Comparaison.py` | nouveau groupe `_RESILIENCE_INDICATORS`, fusionné dans `_INDICATOR_LABELS` |

**Les deux sont nécessaires.** `INDICATOR_DIRECTION` ne fait qu'annoter le sens d'un indicateur ;
c'est l'appartenance à un groupe du sélecteur qui le rend atteignable par
`compute_composite_scores`. La spec 1 a livré quatre indicateurs branchés au seul
`INDICATOR_DIRECTION` : ils étaient **du code mort**, invisibles du picker, et aucun test ne
pouvait l'attraper puisque les tests du composite appellent la fonction directement. Ne pas
refaire cette erreur.

Les cinq scalaires sont en direction `cost` : pour chacun, plus haut = plus fragile.

**Deux paires fortement corrélées, à ne pas sélectionner ensemble.** `climate_margin_at_risk` et
son `_ratio` ne diffèrent que par la normalisation, idem pour le choc de prix. Les exposer tous
les cinq laisse l'utilisateur libre, mais un commentaire dans `_RESILIENCE_INDICATORS` doit
avertir que cocher une valeur absolue et son ratio double le poids de cet axe dans le score
composite — le même piège de colinéarité qui a fait retirer le mois de pointe en spec 1.

Comme pour tous les indicateurs, tout est décliné **entrée** (baseline via
`baseline_representative_crops`) et **sortie** (allocation optimisée).

## Limites, à reporter dans `docs/04-vigilance.md`

**1. Exposition, pas adaptation.** Aucun de ces indicateurs ne ré-optimise. Voir la section
« Ce que ces indicateurs mesurent ».

**2. Le risque de la baseline est une hypothèse.** Côté entrée, la culture de chaque parcelle
vient de `baseline_representative_crops` ; son `Var_Rdt` et son prix sont donc hérités d'un
représentant choisi, pas observés. Même réserve que pour tous les indicateurs d'entrée, déjà
documentée. Elle mord un peu plus ici : `Var_Rdt` varie de 0 à 0,7 **à l'intérieur** de
certaines familles, donc le choix du représentant déplace sensiblement le risque de la baseline.

**3. `NC` porte `Var_Rdt = 1,0`.** « Non cultivé » affecté d'une perte de 100 % est un artefact
du tableau source. Vérifié : `NC` a bien `Prix_Cult = 0` et `Rdt_Cult = 0`, donc sa
contribution au **choc de prix** est exactement nulle. En revanche sa contribution à la **marge
à risque** vaut `marge_NC × 1,0`, et sa marge n'est pas mécaniquement nulle — elle vaut
`subventions − coûts variables`, potentiellement non nulle. Si `NC` est allouée sur une surface
notable, elle pèsera donc à taux plein dans l'indicateur climatique. À mesurer au câblage :
si la contribution est significative, il faudra décider de l'exclure explicitement. À noter que
le GAMS maintient un set dédié `CULT_NON_NC_2017` (« toutes les cultures sauf `NC` »), signe que
`NC` y était déjà traitée à part.

**4. Le choc de prix ne touche ni bagasse ni subventions.** Choix documenté ci-dessus.

## Tests

Convention du repo : configs minuscules montées à la main, pas de lecture de `data/`
(cf. `tests/test_guadeloupe_constraints.py`). Aucun test de ce lot ne résout de MILP.

- `tests/test_guadeloupe_resilience.py` — les trois fonctions pures isolément, sur des valeurs
  calculées à la main. Plus, spécifiquement :
  - une culture à `Var_Rdt = 0` ne contribue rien à la marge à risque ;
  - le HHI d'une monoculture vaut 1,0, celui de `n` cultures à parts égales vaut `1/n` — les
    deux bornes, pas seulement un cas intermédiaire ;
  - le HHI d'un revenu total nul renvoie `0.0` sans lever ;
  - le HHI est insensible à une culture de revenu nul (elle ne doit pas peser dans `n`) ;
  - `δ = 0` annule la perte sous choc ; `δ = 1` la porte au revenu de marché entier.
- `tests/test_guadeloupe_reporting_resilience.py` — `compute_resilience_totals` sur un `Dataset`
  monté à la main : les cinq scalaires, côté entrée comme sortie, et les ratios cohérents avec
  leurs numérateurs.
- `tests/test_guadeloupe_dashboard_comparison.py` (étendre) — **un test qui échouerait si les
  indicateurs n'étaient branchés qu'à `INDICATOR_DIRECTION`** : vérifier que chacune des cinq
  clés est présente dans `_INDICATOR_LABELS` du sélecteur. C'est le test qui manquait en spec 1.

Attention, leçon de la spec 1 : étendre une fonction partagée casse les `Dataset` montés à la
main dans les autres fichiers de test. Après implémentation, lancer la suite complète hors
solve réel (`--deselect tests/test_main.py --ignore=tests/test_guadeloupe_pipeline.py`) et
compléter additivement toute fixture cassée, sans jamais modifier une assertion existante.

## Hors périmètre

- Toute contrainte ou objectif s'appuyant sur ces indicateurs. L'objectif
  `maximize_risk_adjusted_gross_margin` **existe déjà** (porté en phase 2, désactivé par défaut)
  et fait exactement cela côté optimisation — il n'y a rien à construire, seulement un solve
  réel à lancer un jour pour le comparer à la baseline marge-max.
- La ré-optimisation sous choc (ce serait une vraie mesure d'adaptation, un autre projet).
- Le choc ciblé sur les cultures d'export.
- Rpest / Tixier, qui a sa propre spec.
- Les graphes statiques : les visualisations riches vivent dans le dashboard (décision du
  2026-07-13).
