# Design — Expose `year` / `scenario` in config (+ fully commented `config.yaml`)

_Date : 2026-07-13. Statut : validé par l'utilisateur, prêt pour le plan d'implémentation._

## Contexte et problème

`case_studies/guadeloupe/data_pipeline.py` fige l'année et le scénario en constantes
de module :

```python
YEAR = "2017"
SCENARIO = "RESTIT"
```

- `YEAR` sélectionne une **colonne** dans ~17 tables `indice_H` (prix, rendements,
  aides, durées…). Les colonnes disponibles sont `init, calib, 2017, 2018, 2019, 2020,
  2021, 2022` : **les années 2017→2022 existent réellement** en données.
- `SCENARIO` est un **suffixe de nom de fichier** sur 2 tables :
  `Matrice_OTK_Cult_{SCENARIO}.txt` et `MAE_Compost_Cult_{SCENARIO}.txt`. Les deux
  scénarios `RESTIT` et `SMART` existent réellement en données.

Coder ces deux dimensions en dur empêche toute comparaison multi-années / multi-scénarios
et bloque la brique C (comparaison de scénarios, conçue séparément). Ce point est déjà
tracé dans `docs/04-vigilance.md` (« `YEAR`/`SCENARIO` codés en dur », sévérité mineure).

## Portée (décidée avec l'utilisateur)

- **`year` pilote l'économie uniquement** (série temporelle des tables `indice_H`,
  2017→2022). La **structure du parcellaire reste figée à 2017** : les fichiers
  structurels (`CULT_2017.set`, `EXPL_PARC_2017.set`, `BV_2017.set`,
  `Data_Parc_Gwad_2017.txt`, etc.) n'existent **que** pour 2017 — aucune donnée d'une
  autre année n'existe. On ne paramètre donc PAS les suffixes `_2017` structurels.
- **`scenario` pilote `Matrice_OTK_Cult_*` et `MAE_Compost_Cult_*`** (les 2 seuls
  fichiers scénario-suffixés effectivement chargés aujourd'hui).
- **`var_rdt_cult` reste sur la colonne `"init"`** (variance de référence,
  `data_pipeline.py:67`) — délibérément **non** piloté par `year`.
- **Ajout demandé** : commenter intégralement `config.yaml` en anglais (chaque section
  et chaque argument), de façon claire. Pur commentaire, aucun risque de parité.

### Non-goals

- Parcellaire multi-années (données inexistantes).
- Fichiers CF scénario-spécifiques (`Prix_Cult_CF_*`, `Rdt_Cult_CF_*`) : présents en
  données mais **jamais chargés** par le pipeline actuel → hors périmètre, noté comme
  écart connu dans `docs/04-vigilance.md`.
- Comparaison multi-runs / orchestration de scénarios : c'est la brique C, un
  sous-projet distinct. Ce design se contente de rendre chaque run paramétrable, ce qui
  débloque la brique C sans la réaliser.

## Approche retenue

**Passthrough via une section `data:` de la config** (approche A du brainstorming).
Alternatives écartées : une couche d'abstraction `DataContext` (B, YAGNI — la brique C
pourra simplement appeler `build_dataset` avec des `config["data"]` différents) ; un
override par variable d'environnement / CLI (C, casse le pattern « tout piloté par la
config » du projet).

## Design détaillé

### 1. Config

Nouvelle section top-level dans `case_studies/guadeloupe/config.yaml` :

```yaml
data:
  year: "2017"        # column selected in the indice_H tables (prices, yields, subsidies):
                      # one of 2017..2022 (also init/calib). Drives ECONOMICS ONLY —
                      # the plot/farm structure stays pinned to 2017 (no other year exists).
  scenario: "RESTIT"  # RESTIT | SMART. Selects Matrice_OTK_Cult_<scenario> and
                      # MAE_Compost_Cult_<scenario>. Does NOT yet drive the CF files.
```

### 2. Pipeline (`data_pipeline.py`)

- `build_dataset` lit :
  ```python
  year = config.get("data", {}).get("year", "2017")
  scenario = config.get("data", {}).get("scenario", "RESTIT")
  ```
  Les défauts `2017`/`RESTIT` garantissent (a) la **parité** — un config sans section
  `data:` reproduit le comportement actuel à l'identique — et (b) que les tests à
  mini-config existants continuent de passer sans modification.
- Suppression des constantes de module `YEAR` / `SCENARIO`.
- Les ~17 sélections `[YEAR]` → `[year]` ; les 2 f-strings `{SCENARIO}` → `{scenario}`.
- `var_rdt_cult = read_wide_table(...)["init"]` **reste inchangé**.

### 3. Validation (fail-fast, message clair)

Petite fonction utilitaire (dans `data_pipeline.py`) appelée en tête de `build_dataset`,
avant toute lecture year/scenario-dépendante :

- **année** : doit appartenir aux colonnes réellement présentes dans une table canonique
  (`Prix_Cult.txt`). Sinon `ValueError` listant les années disponibles.
- **scénario** : les fichiers `Matrice_OTK_Cult_{scenario}.txt` **et**
  `MAE_Compost_Cult_{scenario}.txt` doivent exister. Sinon `ValueError` listant les
  scénarios détectés (glob sur `Matrice_OTK_Cult_*.txt`).

But : lever une erreur explicite en amont plutôt qu'un `KeyError` pandas opaque au milieu
du pipeline.

### 4. Traçabilité

`_build_recap` (`reporting/report.py`) ajoute `recap["data"] = {"year": ..., "scenario":
...}`, écrit à la fois dans le récap texte et le YAML de `outputs/output_N/`. Permet de
savoir a posteriori quelle année/scénario a produit un run (utile pour la brique C et le
dashboard). Affichage dashboard : non requis ici.

### 5. Documentation complète de `config.yaml`

Commenter en anglais **chaque** section top-level et **chaque** argument non trivial :
`solver`, `labor`, `baseline_representative_crops`, `crop_families`, `objectives`,
`constraints`, `eligibility_criteria`, `categorical_rules`, et la nouvelle `data`. Les
commentaires expliquent le rôle (quoi/pourquoi), pas la syntaxe YAML. Préserver les
commentaires existants qui documentent des choix de parité (ex. entrées désactivées
`enable: false` avec leur raison) — les compléter, pas les écraser.

**Chaque entrée de `crop_families` et de `constraints` est commentée individuellement**,
en commentaire **inline** (sur la même ligne que l'argument), sans alourdir la lecture.
Règle pratique selon la forme de l'entrée :

- **Entrée sur une seule ligne** (ex. `an: &SC_AN [AN, AN_NU, AN_PA]`, ou une contrainte
  dont les `args` tiennent sur la ligne) → commentaire en fin de ligne :
  `an: &SC_AN [AN, AN_NU, AN_PA]  # aubergine family: base group + fine variants`.
- **Entrée multi-lignes** (familles `cs`, `ma` ; contraintes dont les `args:` sont un bloc
  sur plusieurs lignes) → un commentaire concis sur la **ligne d'en-tête** de l'entrée
  (`cs: &SC_CS  # ...` ou `- name: farm_area_ratio_min  # ...`). On n'ajoute PAS de
  commentaire en fin de liste crochetée multi-lignes (illisible).

Pour une famille : dire quel groupe de cultures elle représente. Pour une contrainte :
dire quelle règle elle impose et ce que signifie son `label`/ses paramètres clés (ex.
`max_share`, `ratio`, `threshold`, `sense`). Les longs blocs de commentaire existants qui
justifient une entrée `enable: false` (rationale de parité GAMS) sont **conservés tels
quels** ; l'inline ne les remplace pas.

## Plan de tests (data-free, style existant)

1. Config par défaut (sans section `data:`) → `year == "2017"`, `scenario == "RESTIT"`.
2. Validation : une année absente (ex. `"1999"`) lève `ValueError` avec le bon message ;
   un scénario inconnu (ex. `"BOGUS"`) lève `ValueError` listant RESTIT/SMART.
3. Changer `scenario` change bien le chemin `Matrice_OTK_Cult_*` construit (vérifiable
   sans solve, par paramétrage/mock du chemin) ; `var_rdt_cult` reste sur `"init"`.
4. Pas de vrai solve dans ces tests (respecte la contrainte de rapidité de la suite).

## Documentation à mettre à jour

- **`CLAUDE.md`** : retirer la mention « `YEAR = "2017"` et `SCENARIO = "RESTIT"` sont
  des constantes de module codées en dur » ; documenter la section `data:` et le fait que
  `year` ne pilote que l'économie.
- **`docs/04-vigilance.md`** : déplacer le point mineur « `YEAR`/`SCENARIO` codés en dur » vers
  « Résolu » ; ajouter/mettre à jour l'écart connu « `scenario` ne pilote pas encore les
  fichiers CF ».

## Impact / risques

- Aucun changement de signature : tous les appelants passent déjà `config`.
- Parité préservée par les défauts `2017`/`RESTIT`.
- Risque principal : oublier une des ~17 sélections `[YEAR]` ou toucher par erreur
  `var_rdt_cult` → couvert par les tests et une relecture ligne à ligne.
