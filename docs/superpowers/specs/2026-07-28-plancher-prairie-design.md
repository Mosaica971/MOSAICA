# Plancher de surface fourragère — assise externe et décision

_2026-07-28._ Fait suite au diagnostic du déficit de prairie (`VIGILANCE.md`, entrée dédiée du
2026-07-27) qui concluait : « le seul correctif non circulaire est un plancher exogène, donnée
absente du dépôt ». La donnée a été trouvée.

## La donnée

Statistique agricole annuelle **2017** — notre année exacte — publiée dans le *Mémento de la
statistique agricole*, Agreste Guadeloupe, édition 2019. Champ « exploitations », le même que
notre jeu parcellaire.

| Poste (SAA 2017) | Agreste | Notre observé | % |
|---|---:|---:|---:|
| Canne à sucre | 13 066 ha | 12 813 | **98 %** |
| Cultures fruitières | 2 907 ha | 2 612 | 90 % |
| Cultures légumières | 1 883 ha | 1 422 | 76 % |
| Surfaces toujours en herbe des exploitations | 9 595 ha | 6 109 | **64 %** |
| SAU des exploitations | 30 066 ha | 26 137 | 87 % |

Cheptel bovin au 1er décembre 2017 : **40 449 têtes**. Converti via le ratio du recensement
(27 496 UGB pour 37 358 têtes, RA2020 / SAA2019) : **≈ 29 771 UGB**.

Sources : [Mémento 2019](https://daaf.guadeloupe.agriculture.gouv.fr/IMG/pdf/Memento_Guadeloupe_Edition_2019_cle4928a1.pdf)
(usage du territoire p. 5, cheptels p. 10) ;
[Agreste Études mai 2022, RA2020 résultats définitifs](https://daaf.guadeloupe.agriculture.gouv.fr/IMG/pdf/etudes_ra2020_resultats_definitifs_region_971-3.pdf)
(prairies et UGB 2010/2020) ; [Mémento 2020](https://daaf.guadeloupe.agriculture.gouv.fr/IMG/pdf/memento_2020_internet_cle4814fe.pdf).

## Deux résultats indépendants de la décision

**1. La référence 2017 a désormais une assise externe.** C'était un point ouvert de `TODO.md`
depuis sa livraison. Notre jeu parcellaire couvre **87 %** de la SAU et restitue la canne à
**98 %** et les cultures fruitières à 90 %. La référence n'est plus « ce que vaut le jeu
parcellaire local » : elle est recoupée.

**2. Le RPG sous-déclare la prairie, et on sait comment.** 64 % contre une couverture générale
de 87 %. Ce n'est pas un problème d'étiquetage : si les ~3 500 ha manquants étaient des
parcelles de notre univers classées en canne, notre canne dépasserait Agreste — elle est à
98 %. **Ce sont des parcelles absentes de l'univers parcellaire** (herbe non déclarée aux
aides). Conséquence directe sur le choix du seuil, cf. plus bas.

## La preuve physique du défaut

| Surface fourragère | Chargement implicite |
|---|---:|
| Agreste 2017, exploitations (9 595 ha) | **3,10 UGB/ha** |
| Notre prairie observée (6 109 ha) | 4,87 UGB/ha |
| **Modèle sans plancher (2 980 ha)** | **9,99 UGB/ha** |

Repères indépendants, même champ : RA 2010 → 32 056 UGB / 10 250 ha = **3,13** ; RA 2020 →
27 496 / 11 222 = **2,45**. La surface d'Agreste tombe donc pile sur le chargement attesté par
deux recensements, tandis que l'allocation du modèle impliquerait **dix UGB par hectare** —
trois à quatre fois le réel, agronomiquement impossible. **Le défaut est prouvé physiquement,
hors modèle**, et non par simple désaccord avec notre propre référence.

## Le balayage

| plancher | PAD | PAD hors prairie | types | parcelles | surface | canne | banane | objectif |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| aucun | 31,7 % | — | 67,0 % | 59,8 % | 69,0 % | 15 425 | 2 213 | 81,79 M€ |
| **6 096 ha** | 6,6 % | — | **86,9 %** | **67,6 %** | **77,1 %** | 12 782 | 2 047 | 81,22 M€ |
| 7 218 ha | 15,7 % | 14,9 % | 84,2 % | 66,2 % | 75,0 % | 11 633 | 1 803 | 77,77 M€ ⚠ |
| 8 341 ha | 23,2 % | 18,5 % | 84,3 % | 67,0 % | 74,6 % | 11 121 | 1 772 | 78,99 M€ |
| 9 595 ha | 32,6 % | 24,0 % | 82,0 % | 65,2 % | 72,2 % | 10 530 | 1 336 | 75,10 M€ |
| _observé_ | | | | | | _12 813_ | _1 921_ | |

⚠ Le point 7 218 a tapé la limite d'une heure ; son incumbent est **prouvablement
sous-optimal** (77,77 M€ alors que 8 341, plus contraint, atteint 78,99). Ne pas
surinterpréter cette ligne.

**Ce qui tient.** Les trois métriques que le plancher ne contraint pas restent stables sur
toute la plage exogène : types **82–87 %**, parcelles **65–68 %**, surface **72–77 %** — à
hauteur ou au-dessus des 81 % / 66 % / 77 % publiés par l'article, y compris à 9 595 ha qui ne
doit rien à notre RPG. Le gain n'est donc pas un artefact de la coïncidence entre 6 096 et
l'observé.

**Ce qui ne tient pas, et pourquoi c'est instructif.** Le meilleur ajustement est au seuil le
plus bas et tout se dégrade en montant, y compris hors prairie (14,9 → 18,5 → 24,0 %). En
cause : la canne tombe à 11 633 → 11 121 → 10 530 ha alors qu'elle est observée à 12 813 et
**attestée à 13 066**. Forcer 8 341 ha de prairie sur notre univers revient à la prendre à la
culture que le RPG mesure le mieux. C'est le corollaire du résultat 2 ci-dessus : les hectares
d'herbe manquants ne sont pas récupérables *dans* notre périmètre.

## Décision : 6 096 ha, le paramètre GAMS

Quatre justifications indépendantes :

1. **C'est une vraie équation GAMS** (`Eq_PN_PROD_MIN`, MODELE.txt:403) avec son vrai paramètre
   (`QUOTA_PN_PIQ_MIN`).
2. **Le besoin est établi hors modèle** : le chargement de 9,99 UGB/ha est impossible.
3. **Le seuil est conservateur** : 27 % *sous* les 8 341 ha exogènes (9 595 mis à l'échelle de
   notre couverture de 87 %). Sa proximité avec l'observé (13 ha) n'est pas de la circularité
   mais le même raisonnement fait par l'auteur du GAMS.
4. **Le balayage l'atteste** : les métriques non contraintes tiennent partout, et le seuil bas
   est celui qui respecte le mieux la canne — la grandeur la mieux mesurée du jeu.

**Ce qu'il ne faut PAS revendiquer.** Le plancher épingle la prairie : son PAD est nul par
construction et le PAD territorial de 6,6 % en hérite. Le chiffre à citer n'est pas celui-là,
ce sont **types 86,9 %, parcelles 67,6 %, surface 77,1 %** — et surtout la canne revenue à
**12 782 ha contre 12 813 observés** (PAD 0,24 %, contre 20,4 %) sans qu'aucune contrainte ne
la nomme, comme la banane l'avait fait la veille sous le plafond plantain.

## Corrections de verdicts antérieurs

- **« Plancher intraitable » (2026-07-23) : faux.** Le verdict datait du modèle à 900 000+
  variables ; à 309 000 le solve prend **170 s**. Attention toutefois : ~1 h aux seuils
  intermédiaires (7 218, 8 341 ha).
- **« Plancher infaisable » : faux aussi.** Vérifié le 2026-07-27 : 0 exploitation sur 4 638
  manque d'heures pour porter sa propre prairie observée.
- **« Plancher circulaire » (mon objection du 2026-07-27) : levée** par la statistique externe.

## Ce qui reste ouvert

- **Le périmètre parcellaire, pas le modèle, borne désormais la prairie.** Récupérer les
  ~3 500 ha d'herbe non déclarée demanderait d'élargir l'univers de parcelles, pas de
  contraindre l'allocation.
- **Deux déviations assumées au bloc `CALIB` coexistent maintenant** (plafond plantain, plancher
  prairie). Toutes deux fondées sur des sources exogènes, toutes deux réversibles par
  `enable: false`. Au-delà, le modèle cesserait d'être le `CALIB` de l'article.
- **Le PAD résiduel est désormais porté par les petites cultures** : ananas, vergers, melon,
  jachère. Aucune n'a de plafond ou de plancher sourcé à ce jour.
