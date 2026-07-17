# Part de bio — cadrage (chantier C2, DIFFÉRÉ)

> **Statut : différé.** Spec de cadrage écrite le 2026-07-17 pour reprise ultérieure sans
> re-exploration. Ne pas implémenter tel quel : la faisabilité dépend d'une décision de
> l'utilisateur (voir « Verrou »). Les chantiers A, B, C1 sont faits et mergés (voir
> `docs/superpowers/specs/2026-07-17-{dashboard-run-name-labels,environmental-indicators-and-composite-score,food-self-sufficiency-indicators}-design.md`).

## Objectif visé

Mesurer la « part de bio » d'un scénario : part de la surface / production / valeur issue de
l'agriculture biologique, comme indicateur de reporting (pas une contrainte du modèle),
intégré au dashboard comme les indicateurs des chantiers B/C1.

## Verrou : le bio n'est pas identifiable proprement dans les données actuelles

Exploration du 2026-07-17 :

- **Aucun attribut bio/AB/HVE explicite** dans `Data_Cult.txt` (lignes d'attributs :
  SURF_PARC_*, ALTI_*, PENTE_*, PLUVIO_*, CLD, MW, COUV_SOL, PROF_SILLONS, BESOIN_EAU_*,
  LONG_RAC, KCROP, HRES, CARB, RAC, BIOM_AER — rien sur la certification bio).
- Le seul marqueur est le **token `BIO` dans 8 codes de culture**, **tous en maraîchage** :
  `MA_PLBIO`, `MA_MOBIO`, `MA_BAG_BIO_I`, `MA_BAG_BIO_NI`, `MA_BRF_BIO_I`, `MA_BRF_BIO_NI`,
  `MA_PAI_BIO_I`, `MA_PAI_BIO_NI`.
- **Piège** : dans les codes `MA_<mulch>_<fert>_<irrig>` (ex. `MA_BAG_BIO_I`), le token `BIO`
  est le **type de fertilisation** (amendement organique : BIO/VEG/FER/NON), **pas une
  certification bio**. Cf. le commentaire dans `dashboard/comparison.py` (« le token
  fertilisation BIO/VEG/FER/NON reste littéral, non documenté dans le GAMS »). `MA_PLBIO` /
  `MA_MOBIO` sont d'autres variantes encore.
- Conséquence : aucune banane, canne, igname, arbo « bio » n'existe dans le jeu de 84
  cultures. Une « part de bio » calculée depuis les codes serait (a) un **proxy de pratique**
  (fertilisation organique), pas de certification, et (b) **limitée au maraîchage**.

Le GAMS d'origine ne calcule aucun indicateur « part de bio » (aucune référence trouvée).

## Décision requise avant implémentation (à poser à l'utilisateur)

1. **Définition du « bio »** : (a) proxy « fertilisation organique » depuis les 8 codes
   maraîchage — assumé et documenté comme partiel ; ou (b) attendre une **vraie
   classification bio** ajoutée en donnée (recommandé).
2. Si (b) : quelle source ? Idéalement une **nouvelle colonne booléenne `BIO`** (ou une liste
   de codes certifiés) dans `Data_Cult.txt`, à fournir par l'utilisateur / la DAAF. Cela
   généraliserait l'indicateur à toutes les familles et le rendrait défendable.
3. **Assiette** : part de bio en **surface**, en **production (tonnes)**, et/ou en **valeur
   de vente (€)** ? (EGalim raisonne en valeur d'achat — cohérence avec C3.)

## Architecture proposée (si l'utilisateur choisit d'avancer)

Cohérente avec B/C1 :

- **Classification bio** : une fonction/param `is_bio_cult(crop) -> bool`. Source, par ordre
  de préférence : (a) colonne `Data_Cult["BIO"]` si ajoutée ; sinon (b) fallback
  `config.yaml reporting.bio.crop_codes` (liste explicite, défaut = les 8 codes token-BIO),
  pour ne PAS coder en dur une heuristique de sous-chaîne fragile.
- **Indicateurs** (`reporting/indicators.py`) : `compute_bio_share(dataset, allocation, basis)`
  où `basis ∈ {surface, production, sales}` = (Σ mesure sur cultures bio) / (Σ mesure totale).
  Réutilise `compute_surface_by_key` / `compute_production_tonnes_by_crop` / `compute_sales_by_crop`.
- **Persistance** (`report.py`) : `recap["bio"]` = `{input, output, delta}` avec les parts par
  assiette. Colonne `is_bio` optionnelle dans la table facts (permettrait un empilement
  bio/non-bio dans les graphes existants).
- **Dashboard** : indicateur `bio_share_*` (bénéfice) dans le profil + score composite ;
  éventuellement un empilement bio/non-bio dans le graphe de surface/production existant.

## Tests (TDD, data-free)

- `is_bio_cult` / classification depuis config vs colonne donnée.
- `compute_bio_share` par assiette sur un mini-dataset (cultures bio et non-bio mélangées).
- `recap["bio"]` présent et cohérent (delta).

## Recommandation

**Ne pas implémenter le proxy token-BIO** comme « part de bio » officielle (trompeur :
fertilisation ≠ certification, maraîchage seulement). **Attendre une vraie classification
bio en donnée** (colonne `BIO` dans `Data_Cult` ou liste de codes certifiés). L'architecture
ci-dessus est prête à l'accueillir via `reporting.bio.crop_codes` / colonne `Data_Cult["BIO"]`.
