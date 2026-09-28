# La frise, point par point — ce que chaque date fait à la terre et à la vie guadeloupéennes

> À quoi sert ce fichier. La slide 11 ne porte que douze dates et douze libellés. Ce fichier
> porte ce qui se dit par-dessus, et surtout ce qu'on répond quand le jury demande « et
> concrètement, ça change quoi ? ». Une date n'est retenue sur la frise que parce qu'elle
> produit encore quelque chose aujourd'hui : un hectare qu'on ne peut pas replanter, un revenu
> qui dépend d'un arbitrage, un prix en rayon.
>
> **Convention de confiance** : ⬤ source institutionnelle primaire · ◐ rapport ou étude ·
> ○ presse et ordre de grandeur. Les chiffres du modèle sont recalculés depuis `outputs/`.

---

## 1946 — Départementalisation

**Le fait.** La loi du 19 mars 1946 transforme la colonie en département français. ⬤

**Le lien agronomique.** Rien ne change dans les champs, et c'est tout le problème : la
structure héritée de la plantation — la canne sur les meilleures terres, la propriété
concentrée, le vivrier renvoyé aux jardins — traverse le changement de statut intacte. Ce qui
change, c'est **qui écrit les règles** : à partir de là, et plus encore après l'entrée dans le
marché commun, les normes agricoles, sanitaires et commerciales qui s'appliquent en Guadeloupe
sont écrites à Paris puis à Bruxelles, pour des agricultures tempérées. ⬤

**Ce que ça change dans la vie.** C'est l'origine du régime dans lequel tout le reste se joue :
des transferts sociaux et publics qui soutiennent le revenu, et un cadre normatif conçu
ailleurs. Aujourd'hui encore, c'est ce qui explique qu'un agriculteur guadeloupéen remplisse
les mêmes formulaires qu'un céréalier beauceron, et qu'un légume dominiquais à 40 km ne puisse
pas entrer légalement alors qu'un légume néerlandais à 6 800 km le peut.

---

## 1968 — Les quotas sucriers européens

**Le fait.** L'organisation commune du marché du sucre entre en application : quotas, prix
garanti, débouché protégé. Le sucre des départements d'outre-mer y entre avec un accès
garanti. ⬤

**Le lien agronomique.** Le prix du sucre cesse d'être un prix mondial. La canne devient
rationnelle **non pas parce qu'elle rapporte, mais parce qu'elle est garantie** — et elle le
reste sur des terres où d'autres cultures seraient agronomiquement possibles. C'est le début de
la spécialisation que mon modèle retrouve en 2017 : canne, prairie et banane sur 90 % de la
surface.

**Ce que ça change dans la vie.** La protection n'a pas empêché la contraction : les usines ont
fermé les unes après les autres jusqu'à n'en laisser que deux. ○ Elle a en revanche fixé la
règle du jeu qui vaut encore : **la canne guadeloupéenne vit d'une décision européenne, pas
d'un marché.** Quand on discute aujourd'hui du revenu de 3 000 planteurs, on discute en réalité
d'une ligne budgétaire.

---

## 1981 — La réforme foncière : 60 % de canne inscrits dans le titre

**Le fait.** Après la crise sucrière, l'État, la SAFER, le Crédit Agricole et le département
installent des exploitants sur les terres des anciennes plantations, via des groupements
fonciers agricoles : 38 groupements, environ 9 000 ha, environ 800 exploitants. L'exploitant
détient ~40 % des parts et devient fermier ; **une clause impose 60 % de canne.** ⬤ (Sénat,
rapport n° 799 de 2023 ; SAFER Guadeloupe)

**Le lien agronomique.** C'est le cas le plus net de ma démonstration : une part de culture
fixée **par contrat**, sur des sols dont l'aptitude n'a rien à voir avec la décision. Et c'est
un verrou durable — un bail à long terme ne se renégocie pas à chaque campagne.

**Ce que ça change dans la vie.** Deux effets opposés, et il faut dire les deux. C'est une
redistribution réelle : des descendants d'ouvriers agricoles accèdent à la terre. Et c'est un
enfermement : ils accèdent à une terre dont l'usage est prescrit, en micro-exploitations
d'environ 4 ha. À la retraite, les parts sont le plus souvent reprises par d'autres membres du
groupement qui s'agrandissent, ce qui **bloque l'installation** — d'où les ~450 jeunes en
attente de terres. ◐

**Dans mon modèle.** C'est la contrainte `cs_gfa_minimum_share`. Elle est désactivée, parce que
l'activer rend le problème **infaisable** sur les données de 2017 — la même infaisabilité que
dans le modèle GAMS d'origine. Autrement dit : la règle de 1981 et l'assolement réellement
observé en 2017 ne sont pas compatibles. C'est un résultat, pas un bug.

---

## 1989 — POSEIDOM, le régime dérogatoire

**Le fait.** Le Conseil crée en décembre 1989 le premier programme d'options spécifiques à
l'éloignement et à l'insularité pour les DOM. Il deviendra POSEI, aujourd'hui régi par le
règlement (UE) n° 228/2013, adossé à l'article 349 du traité. ⬤

**Le lien agronomique.** Le programme a deux jambes qui tirent en sens inverse : une aide aux
**productions locales**, et un régime spécifique d'approvisionnement qui **subventionne
l'importation** de produits européens et d'intrants — dont l'alimentation du cheptel, sans quoi
il n'y a pas d'élevage local. ◐ Ce n'est pas une incohérence, c'est une tension, et elle est
structurante pour tout discours de souveraineté alimentaire.

**Ce que ça change dans la vie.** Ces aides représentent de l'ordre des **trois quarts de la
marge brute agricole** du territoire. ◐ Conséquence directe, et c'est celle que je dis au
jury : **quand mon modèle maximise une marge brute, il maximise très majoritairement une
décision administrative.** Le vrai arbitrage n'est pas le montant global du POSEI, qui bouge
peu — c'est sa **clé de répartition** entre filières traditionnelles et diversification. En
2024, un transfert de 500 000 € de l'enveloppe banane de Guadeloupe vers la diversification en
Martinique a été contesté puis annulé. ○ Le montant est dérisoire ; ce qu'il révèle ne l'est
pas.

---

## 1990-1993 — Interdit en France, toléré aux Antilles

**Le fait.** Le chlordécone est retiré du marché en France hexagonale en 1990, et maintenu aux
Antilles jusqu'en 1993 par dérogation, obtenue sous la pression de la filière banane. La
commission d'enquête de l'Assemblée nationale écrit que le maintien de la production bananière
a « souvent primé sur la protection de la santé publique et de l'environnement ». ⬤ (rapport
n° 2440, novembre 2019)

**Le lien agronomique.** C'est le point le plus contre-intuitif de toute la partie 2, et il est
purement agronomique. La molécule est fixée dans le sol — surtout les sols riches en matière
organique, andosols et sols ferrallitiques du sud de Basse-Terre — et elle passe dans
**l'organe récolté qui touche ce sol**. Donc : elle n'interdit **ni la canne ni la banane**,
qui sont des cultures aériennes. Elle interdit l'igname, la patate douce, le madère, la
dachine, la carotte, le melon, le concombre, la ciboule, et l'élevage au sol. ⬤ (DAAF ;
programme JAFA)

**Ce que ça change dans la vie.** Trois choses, et elles sont lourdes.
1. **Le verrou est sélectif, et il frappe l'assiette quotidienne.** Le pesticide autorisé pour
   sauver une filière d'exportation interdit aujourd'hui, pour des siècles, les cultures
   vivrières de base et les jardins familiaux. Il verrouille la sortie du modèle qu'il avait
   servi à protéger.
2. **La santé.** Contamination très large de la population, surincidence du cancer de la
   prostate, reconnaissance en maladie professionnelle pour les travailleurs agricoles en
   2021. ⬤ Et des zones de pêche fermées.
3. **La confiance.** Une dérogation obtenue pour une filière, une responsabilité de l'État
   reconnue trente ans plus tard, un non-lieu judiciaire pour prescription en janvier 2023. ⬤
   Cela conditionne l'accueil de **toute** politique agricole portée par l'État sur ce
   territoire — y compris, indirectement, celui d'un modèle d'aide à la décision commandé par
   un institut public.

**Dans mon modèle.** C'est une règle d'éligibilité par parcelle : le couple (parcelle, culture)
sensible sur une parcelle à risque n'existe tout simplement pas comme variable. 3 975 parcelles
sont au risque le plus élevé, dont 2 147 ha pour la seule Capesterre-Belle-Eau, et **zéro en
Grande-Terre**. Réserve à dire : les deux couches de risque du jeu de données sont agrégées en
sens opposés, et ce sont les contraintes qui lisent la version **permissive**. Le modèle est
donc, sur ce point, optimiste.

---

## 2006 — La réforme du sucre : le prix garanti baisse

**Le fait.** Sous la pression des règles du commerce international, l'Union abaisse fortement le
prix de référence du sucre. ⬤ Les compensations passent par les programmes d'aide, et la France
est autorisée à verser une aide nationale au secteur sucrier — jusqu'à 90 M€ par an. ◐

**Le lien agronomique.** La canne ne devient pas moins productive, elle devient moins payée. Ce
que la baisse du prix garanti ne couvre plus, l'aide publique le couvre : c'est le mécanisme
qui produit le chiffre de la slide 14, **plus de 80 % du prix de la canne payé par l'argent
public**. ○ (ordre de grandeur de presse, à annoncer comme tel)

**Ce que ça change dans la vie.** Le revenu du planteur devient **explicitement** un transfert,
et donc **explicitement négociable**. Chaque renouvellement de la convention canne devient un
rapport de force entre les planteurs, les deux usines et trois financeurs publics. C'est la
mécanique qui explosera en 2023.

---

## 2009 — La grève générale, 44 jours, la vie chère

**Le fait.** Du 20 janvier au 4 mars 2009, le mouvement contre la « pwofitasyon » paralyse
l'île. Il se termine par un accord salarial. ⬤ Suivront la loi pour le développement économique
des outre-mer, les observatoires des prix et le bouclier qualité-prix.

**Le lien agronomique.** C'est l'entrée de l'alimentation dans le champ politique central. Le
sujet n'est plus « comment produire », c'est **« pourquoi ce que je mange coûte 42 % de plus
qu'en France hexagonale »** — quand l'écart tous postes confondus n'est que de 16 %. ⬤ (Insee,
comparaison spatiale des prix 2022)

**Ce que ça change dans la vie.** Deux conséquences qui pèsent sur n'importe quel projet
agricole aujourd'hui.
- **Toute mesure qui renchérit l'assiette est politiquement explosive.** Cela contraint
  fortement les scénarios « vertueux » qu'un modèle peut proposer : un plafond d'azote ou de
  traitements qui ferait monter les prix alimentaires n'est pas neutre socialement, et mon
  modèle ne sait pas mesurer cet effet — il ne modélise aucun prix de marché local.
- **L'octroi de mer devient une cible.** Il est attaqué comme cause de la vie chère alors qu'il
  en explique 4,4 % ◐, qu'il représente près d'un tiers des ressources des communes ⬤, et qu'il
  est **le seul outil de protection tarifaire dont la Guadeloupe dispose en propre** pour sa
  production locale. On est en train de fragiliser le levier local le plus immédiatement
  actionnable.

---

## 2017 — Fin des quotas sucriers européens (1er octobre)

**Le fait.** Cinquante ans de protection s'arrêtent. Le sucre ultramarin passe en concurrence
frontale avec la betterave européenne, dont la production bondit de 16,8 à 20,2 millions de
tonnes dès la première campagne libéralisée. ⬤ Environ 60 % du sucre ultramarin part en
raffinerie européenne pour devenir du sucre blanc — le segment le plus exposé ; les 40 %
restants sont des sucres spéciaux, une niche qui, elle, tient. ◐

**Le lien agronomique.** Rien ne change dans le champ, tout change dans l'équation économique
du champ. À partir de là, la canne guadeloupéenne tient par **l'aide** et par **la niche**, plus
du tout par la protection. Et la comparaison avec la betterave est éclairante : ce sont deux
productions subventionnées, mais l'une l'est au titre de la politique agricole commune
ordinaire, l'autre au titre d'une **dérogation d'ultrapériphéricité**. Une politique se
défend ; **une exception se renégocie**, à chaque programmation.

**Ce que ça change dans la vie.** La canne n'est pas qu'une culture : c'est ~3 087
exploitations d'environ 4 ha ⬤, de l'ordre de 10 000 emplois de filière ○, deux usines dont une
traite 85 % de la production ○, le rhum, et la bagasse qui alimente une centrale raccordée au
réseau électrique de l'île. ○ Autrement dit, **la canne tient du revenu, de l'emploi, un
paysage et une part de l'électricité**. C'est ce qui donne sa gravité au résultat de ma partie
1 : quand l'optimisation répond « supprimez 2 231 hectares de canne », elle ne parle pas d'une
culture.

**Et c'est l'année de mes données.** Mon modèle décrit le territoire exactement au moment où sa
protection s'arrête. Toute la structure parcellaire que je manipule est celle de 2017.

---

## 2019 — La responsabilité de l'État reconnue

**Le fait.** La commission d'enquête de l'Assemblée nationale conclut à la responsabilité de
l'État, partagée avec les fabricants, les distributeurs et les organisations professionnelles.
⬤ Suivent le plan Chlordécone IV (2021-2027, 92 M€ puis 130 M€) ⬤ et la reconnaissance en
maladie professionnelle.

**Le lien agronomique.** La reconnaissance produit un objet très concret pour un modélisateur :
**une cartographie**. C'est parce que les teneurs ont été mesurées et les parcelles classées que
je peux écrire une règle d'éligibilité par parcelle plutôt qu'une hypothèse globale. Ma
contrainte la plus politique est directement la fille d'une décision de réparation.

**Ce que ça change dans la vie.** Un plan de dépollution et de suivi sanitaire, des analyses de
sols gratuites, un accompagnement des jardins familiaux — et, en face, un non-lieu judiciaire
qui laisse un sentiment d'impunité. Le paradoxe à tenir : **plus le classement des sols est
précis, plus il est utile agronomiquement, et plus il matérialise une perte de valeur
foncière** pour celui dont la parcelle est classée.

---

## 2023 — Convention canne, aide de 447 €/ha

**Le fait.** Une convention pluriannuelle fixe le prix payé au planteur à 109-113 € la tonne
selon la richesse en sucre ○ ; un décret du 30 janvier 2023 institue une aide d'État de
**447 € par hectare** de canne livrée en sucrerie. ⬤ La campagne 2023 est paralysée à partir du
1er mars, et dénouée par une compensation financière abondée par le département, l'État, la
Région et l'usine. ○

**Le lien agronomique.** La canne se récolte dans une fenêtre courte, et la richesse en sucre
se dégrade si la coupe attend. Un conflit n'est donc pas un simple arrêt de travail : il
détruit de la valeur dans le champ, semaine après semaine. C'est ce qui rend ces négociations
si brutales et si rapides à conclure par de l'argent public d'urgence.

**Ce que ça change dans la vie.** Sur une exploitation de 4 ha, 447 €/ha, c'est environ
1 800 € par an — l'ordre de grandeur d'un complément de revenu, pas d'un chiffre d'affaires.
**Le dispositif d'aide à la canne fonctionne de fait comme un instrument de revenu et de
cohésion sociale déguisé en politique agricole**, dans un département à chômage structurellement
élevé. Et l'étage qu'on voit le moins est le plus déterminant : une partie de l'aide va **à
l'usine**, pour qu'elle achète la canne plus cher. Elle est comptabilisée comme soutien
industriel, perçue comme soutien agricole, et elle donne un pouvoir de négociation considérable
à un acheteur en situation de monopsone.

---

## 2025 — Chambres d'agriculture : le MODEF en tête

**Le fait.** Élections de janvier 2025, premier collège : MODEF 30,76 % et 12 sièges ;
JA-FNSEA 25,14 % et 2 sièges ; Confédération paysanne 23,88 % ; Coordination rurale 11,89 % ;
FDSEA 8,33 %. Au niveau national, JA-FNSEA fait 46,70 % et arrive en tête dans 72 chambres,
le MODEF 1,48 %. Le scrutin a été annulé par le tribunal administratif. ⬤

**Le lien agronomique.** Ce n'est pas anecdotique : les chambres instruisent les dossiers,
siègent dans les commissions, orientent le conseil technique et pèsent sur la répartition des
aides. Une chambre tenue par une organisation attachée à la petite exploitation et au vivrier
ne défend pas les mêmes arbitrages qu'une chambre tenue par l'organisation majoritaire
hexagonale.

**Ce que ça change dans la vie.** Le verrou syndical qui structure l'agriculture hexagonale
**n'existe pas ici sous la même forme**. Attention à la formulation : ce n'est pas que les
agriculteurs y seraient moins politisés — cinq listes concurrentes et un scrutin annulé disent
l'inverse —, c'est qu'ils le sont **selon d'autres lignes**. Pour un projet de recherche qui
veut discuter de changement de pratiques, c'est à double tranchant : **aucun interlocuteur
unique ne peut bloquer la discussion, mais aucun ne peut l'imposer non plus.** Il n'y a pas de
raccourci ; il faut y aller ferme par ferme, ou par les organisations de producteurs.

---

## 2027 — Les échéances

**Le fait.** La décision (UE) 2021/991 qui autorise le différentiel d'octroi de mer en faveur
des produits fabriqués localement — jusqu'à 20 ou 30 points — expire le **31 décembre 2027**. ⬤
Le plan Chlordécone IV s'arrête la même année. ⬤ Et la prochaine programmation européenne se
prépare dans la même fenêtre.

**Le lien agronomique.** Tout ce qui protège ou compense arrive à échéance en même temps : le
seul outil tarifaire local, le plan de réparation sanitaire, et l'arbitrage entre filières
traditionnelles et diversification dans le programme européen.

**Ce que ça change dans la vie.** Ce qui se décide en 2026-2027 fixe la décennie suivante :
le prix relatif du produit local en rayon, les moyens du suivi sanitaire, et la part d'argent
public qui va à la diversification plutôt qu'à l'export. **C'est exactement la fenêtre où un
outil d'évaluation *ex ante* a une utilité** — et c'est l'argument le plus solide pour dire que
mon travail sert à quelque chose, à condition qu'on l'adosse à des acteurs.

---

## Les quatre chaînes à retenir

Si tu ne dois tenir que quatre enchaînements en tête, ce sont ceux-là. Chacun part d'une date
et finit dans la vie de quelqu'un.

1. **La terre est prescrite.** 1981 → une clause de 60 % de canne dans un titre de propriété →
   9 000 ha dont l'usage est fixé par contrat → et un modèle dans lequel cette clause s'écrit
   exactement comme la pente.
2. **Le revenu est administratif.** 1968 → 1989 → 2006 → 2017 : le prix garanti disparaît,
   l'aide le remplace → trois quarts de la marge brute viennent d'une décision publique → toucher
   à l'assolement, c'est toucher au revenu de milliers de familles, pas à une culture.
3. **L'alternative est empoisonnée, et sélectivement.** 1990-93 → la molécule interdit les
   racines et les tubercules, pas la canne ni la banane → **le verrou porte précisément sur ce
   qu'il faudrait développer pour nourrir l'île**.
4. **Le sujet politique, c'est le prix de l'assiette.** 2009 → +42 % sur l'alimentaire → toute
   politique agricole se juge à cet étalon → et c'est justement ce que mon modèle ne sait pas
   calculer, puisqu'il ne modélise aucun débouché ni aucun prix de marché local.

Et la phrase qui les relie, celle de la slide : **l'assolement guadeloupéen d'aujourd'hui n'est
pas un optimum agronomique, c'est un dépôt de décisions publiques.**
