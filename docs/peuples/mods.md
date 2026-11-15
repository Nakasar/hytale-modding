# Peuples d'Orbis : le mod

Mod `mods/nakasar-peuples` (manifest `Nakasar:Peuples`, jar `Nakasar-Peuples-<version>.jar`, plugin
`dev.nakasar.hytale.peuples.PeuplesPlugin`). Des villages vivants des peuples d'Orbis, façon Millénaire, qui grandissent
avec l'aide du joueur. Le game design document validé par Kevin le 14 novembre 2026 :
https://claude.ai/artifact/FJ15VjWp3pgnt9kmRWjfV7 (plan en 9 étapes, une PR par étape).

Le mod est indépendant des mods Vampires et Fractales (recommandation du GDD) : aucune dépendance de manifest, les
briques communes sont copiées (comme entre Vampires et Fractales).

## Étape 1 : le socle

### Villages

Un village est un objet sauvegardé avec le monde : la ressource de monde `Nakasar_Peuples_Villages`
(`village/VillageRegistry`, enregistrée comme `ReputationData` du ReputationPlugin vanilla) garde pour chaque village son
nom, son peuple, son palier (0 campement, 1 hameau, 2 village, 3 bourg), sa jauge d'essor (partagée par tous les
joueurs) et la position de son cœur, de son dépôt et de son tableau.

| Bloc | Rôle | Asset |
|------|------|-------|
| `Nakasar_Peuples_Village_Heart` | ancre du village, invisible et traversable (comme `Nakasar_Prison_Cell`) | `Item/Items/Nakasar/Peuples/` |
| `Furniture_Kweebec_Chest_Small` | dépôt : le coffre kweebec vanilla, lu par le Java | vanilla |
| `Nakasar_Peuples_Board_Kweebec` | tableau : enfant (`Parent`) du panneau vanilla `Furniture_Kweebec_Sign`, seule son interaction `Use` change | `Item/Items/Nakasar/Peuples/` |

Les peuples et leurs blocs sont dans `village/People` (Kweebecs seulement à l'étape 1). Les seuils d'essor par palier
sont dans `village/Tiers` (100, 250, 500 : premier jet, réglé à l'étape 3). Une jauge pleine attend son chantier
(étape 5) au lieu de déborder.

Le **tableau** ouvre la page texte vanilla `BlockLorePage` (déjà éprouvée par les notes du mod Vampires) remplie par
le Java (`village/VillageBoard`) : peuple et palier, jauge d'essor, rang du joueur (« Étranger » jusqu'à l'étape 4),
demandes (vides jusqu'à l'étape 3) et contenu du dépôt (lu dans le composant vanilla `ItemContainerBlock` du coffre).
C'est la page du GDD ; la maquette plus riche (`images/tableau_village.png`, boutons Prendre/Rendre) viendra avec les
demandes, une fois la page .ui du dialogue confirmée en jeu.

### Dialogues

Les dialogues sont des assets JSON du mod : `Server/Nakasar/Dialogues/<peuple>/<id>.json`, un magasin d'assets
enregistré par le plugin comme les rangs de réputation vanilla (l'id est le nom du fichier). Format (classe
`dialogue/Dialogue`) :

```json
{
  "NpcNameKey": "nakasar_peuples.dialogue.X.npc",
  "RoleKey": "nakasar_peuples.dialogue.X.role",
  "People": "Kweebec",
  "Entries": [ { "Node": "Retour", "Conditions": [ { "Type": "Flag", "Flag": "X_Met" } ] }, { "Node": "Accueil" } ],
  "Nodes": [
    { "Id": "Accueil", "TextKey": "...", "Responses": [
      { "TextKey": "...", "HintKey": "...", "Conditions": [ ... ], "FailKey": "...", "Effects": [ ... ], "Next": "Presentation" }
    ] }
  ]
}
```

- Nœud d'entrée : la première entrée dont les conditions sont remplies, sinon le premier nœud.
- Quatre réponses au plus. Une réponse dont une condition manque reste visible et affiche sa condition (`FailKey`).
- Les effets s'appliquent dans l'ordre ; le premier qui échoue (objet manquant, inventaire plein) arrête la suite et le
  dialogue reste sur le nœud. Sans `Next`, la fenêtre se ferme.
- Conditions du socle : `Flag`, `NotFlag`, `InVillage` (`People` facultatif), `VillageTier` (`Min`), `HasItem`
  (`ItemId`, `Quantity`). Effets : `SetFlag`, `ClearFlag`, `GiveItem`, `TakeItem`, `AddEssor` (`Amount`),
  `SendMessage` (`TextKey`), `OpenBoard`. Les deux familles sont des `CodecMapCodec` (`dialogue/DialogueTypes`) : les
  étapes suivantes y ajoutent le rang de peuple (ReputationPlugin vanilla), les objectifs, l'étape de chaîne, l'heure.
- Les drapeaux sont gardés avec le joueur (composant `Nakasar_Peuples_Player`, `player/PeuplesPlayer`).

La **fenêtre** (`dialogue/DialoguePage`, maquette `images/dialogue_bas_ecran.png`) est une `InteractiveCustomUIPage`
sur la mise en page du pack `Common/UI/Custom/Pages/Nakasar/Peuples/DialoguePage.ui`. C'est une boîte en bas de l'écran,
façon Baldur's Gate / Divinity, la moitié haute restant à la scène :

- cadre vanilla `$C.@DecoratedContainer` (comme le tableau du village) et léger dégradé sombre en bas de l'écran ;
- en-tête : `#NpcName`, `#NpcRole`, `#Standing` (« peuple · rang », `Dialogues.standing`) ;
- `#Line` (réplique), `#Aside` (absents du jour), séparateur `$C.@PanelSeparatorFancy` ;
- `#Answer0..3` : des `Button` vanilla (pas des `TextButton`) portant le numéro, `#Text0..3` et `#Hint0..3`
  (« — effet » ; grisée : `.Disabled`, texte gris et « — condition » en ambre) ;
- à droite, `#Portrait` (`AssetImage`, comme la page vanilla des Souvenirs) dans un cadre, et `#Leave` dessous
  (Échap ferme aussi).

**Portraits** : `dialogue/Portraits` choisit, d'après le modèle du PNJ (`ModelComponent`), un portrait tête et buste
recadré dans les rendus vanilla `Common/Icons/ModelsGenerated/<Modèle>.png`. Ils sont livrés sous
`Common/Icons/Nakasar/Peuples/Portraits/` par `tools/generate_portraits.py --assets <Assets.zip>` (46 modèles des
peuples). Une variante sans rendu vanilla prend celui du plus long préfixe (`Kweebec_Sapling_Pink` → `Kweebec_Sapling`) ;
un modèle sans rendu (`Klops_Merchant`) n'a pas de portrait (le cadre est masqué).

**Caméra de dialogue** (`dialogue/DialogueCamera`) : quand un PNJ parle, le serveur pose la caméra du client derrière
l'épaule du joueur, cadrant le joueur et le PNJ (paquet `SetServerCamera`, celui de `/camera topdown`). Elle revient à
la vue normale à la fermeture (`onDismiss`, Partir, effet qui ferme, autre fenêtre ouverte à sa place). Pas de caméra
si le PNJ est à plus de 9 blocs ou si aucune place libre (épaule droite, gauche, plus près) n'a de ligne de vue sans
bloc plein. Chaque joueur peut la couper ou la rétablir avec `/village camera` (drapeau `option.dialogueCameraOff`).

Le **secours** reste le même dialogue mené dans le tchat (`/village tchat`, `/village repondre`), qui ne dépend
d'aucune page.

Dialogue d'essai : `Kweebec_Essai` (Brindille, jardinière) passe par toutes les conditions et tous les effets.

### Commande `/village`

| Sous-commande | Qui | Effet |
|---------------|-----|-------|
| `fonder <nom> <peuple>` | opérateur | cœur sous les pieds, dépôt 2 blocs à l'est, tableau 2 blocs à l'ouest (cases vides exigées, 64 blocs entre deux villages) ; `_` dans le nom donne une espace |
| `effacer` | opérateur | retire le cœur et le tableau du village le plus proche ; le dépôt reste avec son contenu |
| `essor <n>`, `palier <n>` | opérateur | règle la jauge et le palier du village le plus proche |
| `info`, `tableau`, `liste` | joueur | état du village le plus proche (48 blocs) dans le tchat, son tableau, tous les villages |
| `parler <dialogue>` | joueur | ouvre le dialogue dans la fenêtre du mod |
| `tchat <dialogue>`, `repondre <n>` | joueur | le même dialogue dans le tchat (0 : partir) |
| `drapeaux`, `oublier` | joueur | ses drapeaux de dialogue, et leur remise à zéro |
| `camera` | joueur | coupe ou rétablit la caméra qui cadre le joueur et le PNJ pendant les dialogues |

Les sous-commandes d'opérateur demandent la permission `nakasar.peuples.admin`.

### Validation hors ligne

`validateAssets` (copie de celui des Fractales) décode aussi les dialogues avec le codec du plugin (types de
conditions et d'effets, nœuds en double, `Next` et entrées vers un nœud absent, plus de 4 réponses) et vérifie que
chaque clé `...Key` existe dans les `.lang` fr-FR et en-US et chaque `ItemId` dans le pack ou dans
`tools/vanilla-item-ids-0.7.2.txt`.

### Tester en jeu

1. Monde créatif, opérateur : `/village fonder Bosquet_d'essai Kweebec` sur un terrain plat dégagé.
2. Utiliser le panneau kweebec à l'ouest : le tableau s'ouvre (Campement, essor 0 / 100, dépôt vide).
3. Poser quelques objets dans le coffre kweebec à l'est, rouvrir le tableau : ils sont listés.
4. `/village essor 40`, rouvrir : la jauge avance. `/village palier 1` : Hameau.
5. `/village parler Kweebec_Essai` : la fenêtre de dialogue. Avec 3 `Plant_Seeds_Carrot` en poche : « Je peux aider le
   village ? » puis « Voici trois graines » (+10 d'essor), puis le cadeau (2 pommes, une seule fois).
6. Si la fenêtre ne s'affiche pas : `/village tchat Kweebec_Essai` et `/village repondre 1`... mène le même dialogue.
7. Quitter et relancer le serveur : `/village liste` retrouve le village, l'essor et le palier ; `/village drapeaux`
   retrouve les drapeaux.

### À vérifier en jeu (fenêtre de dialogue en bas d'écran)

- La boîte s'affiche-t-elle en bas, centrée, avec le portrait qui dépasse au-dessus à droite ? Le dégradé du bas
  (`RunicContainerBottomGradient`) assombrit-il bien le bas de l'écran ?
- Survol des réponses (fond bleu sombre), réponse grisée non cliquable avec sa condition en ambre, couleurs des
  `TextSpans` respectées ?
- La caméra glisse-t-elle derrière l'épaule et regarde-t-elle le PNJ (sinon : signe du tangage ou du lacet à inverser
  dans `DialogueCamera.send`) ? Revient-elle bien à la normale avec Échap, Partir, et en ouvrant l'échoppe ?
- `/camera reset` (vanilla) rend la vue si jamais elle restait bloquée.

### À vérifier en jeu (étape 1)

- La fenêtre `DialoguePage.ui` s'ouvre-t-elle ? (si le client signale une erreur de page, envoyer le message et, si
  possible, le fichier vanilla `Common/UI/Custom/Pages/BlockLorePage.ui` d'Assets.zip pour caler la syntaxe).
- Les clics sur les réponses reviennent-ils au serveur et la page change-t-elle de nœud sans se fermer ?
- Le tableau hérite-t-il bien du modèle du panneau kweebec (`Parent` sur un bloc vanilla, première fois dans le dépôt) ?
- Le coffre posé par le Java a-t-il son inventaire (sinon le tableau dit « Le dépôt du village a disparu ») ?
- Le village survit-il au redémarrage (ressource de monde) ?

### Hors de l'étape 1

Les demandes (étape 3), la réputation et les rangs (étape 4, groupes et rangs du ReputationPlugin vanilla), les chantiers
(étape 5) et les raids (étape 6) s'ajoutent à `Village` et à `PeuplesPlayer`.

## Étape 2 : le premier village kweebec

### Plan du village

Un plan (`Server/Nakasar/VillageLayouts/<Id>.json`, asset `VillageLayout`) place des prefabs **vanilla**
(`Server/Prefabs/Npc/Kweebec/Oak/...`, règle n° 2) autour du cœur. Il est écrit par
`tools/generate_village_layouts.py`, qui lit les emprises de `tools/vanilla-prefabs-0.7.2.txt` (relevées dans
Assets.zip), refuse tout chevauchement (3 blocs entre bâtiments, 1 pour les lanternes et les bancs) et dessine un
aperçu (`--preview DIR`). Chaque bâtiment a un palier : seul le campement (palier 0) est collé à la génération, les
autres attendent les chantiers (étape 5).

| Palier | Bâtiments du plan `Kweebec_Oak` (rayon 65) |
| --- | --- |
| 0, campement | deux abris, tour de guet, potager (lanternes et bancs : dans le cœur) |
| 1, hameau | puits, échoppe, une maison, enclos des lapins |
| 2, village | grande maison, maison des gardes, deuxième tour, deuxième échoppe |
| 3, bourg | le Grand-Père, grand potager |

Les prefabs vanilla gardent leurs marqueurs d'apparition : des Kweebecs (villageois, marchand, patrouilles de
Razorleaf et de Sproutlings, lapins) apparaissent dans le campement.

### Génération

`VillageBuilder` charge les chunks, aplanit la place (chemin de terre) et l'emprise de chaque bâtiment (herbe, 2 blocs
de marge plate), à au plus 4 blocs de la hauteur de la place, puis colle
les prefabs comme l'action vanilla `PrefabPasteAction`, puis pose le cœur du peuple, le dépôt, le tableau (étape 1) et la
bannière aux places que donne le plan.

Le terrassement (`Grading`, aussi utilisé par les chantiers) traite toutes les plateformes en une passe :
- talus d'un bloc de pente au plus vers le relief d'origine, sur 8 blocs au-delà des marges ; seules les colonnes qui
  l'exigent sont retouchées, les sols non naturels (chemins, constructions) et les emprises réservées jamais ;
- arbres retirés en entier (tronc, branches, racines remplacées par de la terre, et le feuillage qu'ils portent : chaque
  feuille appartient au bois le plus proche) dès qu'un de leurs blocs ou une de leurs feuilles surplombe une colonne
  retouchée, jusqu'à 14 blocs autour du site ;
- toute grappe de bois et de feuilles qui ne touche plus aucun bloc solide est retirée, ainsi que les plantes sans sol.

### Cœur du village (place propre à chaque peuple)

Le cœur n'est plus un carré de chemin avec un coffre et un panneau : chaque peuple a sa place mise en scène, écrite par
`tools/generate_village_hearts.py` dans la clé `Heart` du plan (positions du tableau, du dépôt et de la bannière avec
leur orientation vers le cœur, puis un « pas » par palier). La place s'enrichit à chaque chantier fini.

| Plan | Cœur | Pièces vanilla, par palier |
| --- | --- | --- |
| `Kweebec_Oak` | clairière du rejeton | chêne qui grandit (Oak Stage 1, 2, 2, 3) sur un tertre de mousse, bassin `Water_Pool_005` (palier 1), lampadaires et bancs kweebecs, auvent de feuilles sur poteaux au-dessus du tableau |
| `Trork_Camp` | arbre aux trophées | `Trork_Warning_002`, foyer `Fireplace_001`, rondins pour s'asseoir, râtelier `Misc_Large_002` (palier 2), cercle de pierres |
| `Feran_Oasis` | bassin de l'oasis | bassin de grès (eau du mod), palmiers qui poussent, colonnes à torche, auvent de toile orange, pots et tabourets |
| `Renonce_Givre` | foyer des repentis | camp `Outlander_Misc_003`, rondins de sapin, sapins enneigés (palier 1), braseros (palier 2) |
| `Slothian_Monastere` | jardin de veille | sanctuaire slothian (son bloc d'apparition retiré), touffes de bambou, jardinières |

Chaque pas pose, dans l'ordre : les pièces vanilla (`Pieces`), les blocs un à un (`Set`, `"x y z rotation Bloc"`,
`Empty` pour vider), retire les blocs qui ne servent plus s'ils sont toujours là (`Clear`, ex. le jeune chêne remplacé),
puis l'eau (`Fluids`, prefab `Server/Prefabs/Nakasar/Peuples/Hearts/*_Fluids` du mod : `Blocks.set` ne pose pas de
fluide). Coordonnées relatives au cœur, y = 0 à la surface de la place. Rotations : lacet 0 sud, 1 est, 2 nord, 3 ouest ;
rondin couché 4 (le long de z) et 5 (le long de x), comme dans les prefabs vanilla ; chapiteau = `Pillar_Base` en 8.

`VillageHeart` ne touche jamais aux inventaires ni au cœur, au tableau, au dépôt et à la bannière. Au passage de palier
(village habité), un bloc n'est remplacé que s'il est naturel, vide, du sol de la place ou du cœur lui-même, et une pièce
vanilla n'est pas collée si un coffre se trouve dessous. Les villages fondés avant les cœurs (`HeartTier` absent) gardent
leur ancienne place.

Aperçus : `python3 tools/generate_village_hearts.py --vanilla dump.json --preview DIR --palette pal.json` (le dump vient
de `tools/extract_vanilla_prefabs.py Assets.zip pieces.txt dump.json --palette pal.json`, la liste des pièces de
`--list`). Le script refuse un bloc inconnu, un meuble de plusieurs cases posé bloc à bloc, un bloc hors de la place ou
une case réservée occupée.

`VillageSeeder` pose tout seul **le premier village kweebec du monde par défaut** : 15 s après le démarrage, il essaie
40 sites sur des cercles de 280 à 700 blocs autour du point d'apparition (ordre tiré du seed), et prend le premier
couvert d'herbe à 80 %, sans eau, avec au plus 9 blocs de relief. Le monde garde la trace du village posé ; si aucun
site ne convient, il réessaie au démarrage suivant avec d'autres sites. Les noms viennent de `VillageNames` (liste
kweebec, sans doublon dans le monde).

#### Plusieurs villages par peuple

Une fois le premier lieu d'un peuple posé (village kweebec, camp trork, oasis feran, hameau renoncé, monastère
slothian), `zone/MoreVillagesSeeder` pose les suivants, 150 s après le démarrage puis un à la fois, jusqu'à
`People.naturalVillages()` en tout : **3 Kweebecs, 3 Feran, 2 Trorks, 2 Renoncés, 2 Slothians**. Écarts retenus :

- **600 à 1200 blocs** du village du même peuple le plus proche. À 600 blocs, les terrains de chasse des demandes
  (220 blocs autour du cœur), la veille des raids et la vie du village (160 blocs) ne se chevauchent jamais, et la
  bannière (révélée à 300 blocs) ne se voit pas depuis l'autre village. Au plus 1200 blocs, pour que les villages d'un
  peuple forment une région et restent à portée des caravanes (2400 blocs au plus).
- **Au moins 300 blocs** de tout village d'un autre peuple.
- Dans la **terre ferme de la zone du peuple** (centre et quatre bords du plan entier, ni rivage ni océan ; zone 1 pour
  les Kweebecs et les Trorks), sur son sol, sans eau et avec un relief modéré, comme le premier lieu.

Les villages se posent avec `VillageBuilder` (même nivellement `Grading` que le premier). Le registre garde le compte
(`MoreSeeded`) ; une recherche sans site compte un échec (`MoreFailures`), et un peuple n'est plus cherché après trois
échecs. `/village semer <peuple>` pose un village de plus à la main avec les mêmes règles, et `/village zone` les liste
tous. Un monde existant reçoit ses villages suivants au prochain démarrage.

#### Le colon : fonder un village sans être Champion

`outpost/Settlers` : un village au palier max (`Tiers.MAX`) fait venir un colon au plus une fois tous les 7 jours de
jeu (`Village` : `SettlerDay`, `SettlerActive`, `SettlerOwner`). Le PNJ n'est pas sauvegardé : il apparaît au poste
(cœur + 4, -4) quand un joueur passe à moins de 48 blocs (`Nakasar_Peuples_<Peuple>_Settler`), puis, accepté, suit son
joueur (`…_Settler_Follow`, ramené près de lui au-delà de 32 blocs, retiré quand il se déconnecte). Lui parler ailleurs
lance `zone/SiteRules.check` (règles communes avec `MoreVillagesSeeder` : écarts 600/300, fondations prévues, zone et
rivage, sol, eau, relief) : la condition de dialogue `SettlerSite` choisit le nœud (« Ici » ou la raison), le détail
chiffré part dans le tchat. « Fondons le village ici » enregistre un `Outpost` avec `From` = village du colon : bâti au
matin suivant comme un avant-poste ; s'il échoue, le colon rentre à son village. Rôles, dialogue `Colon` et textes :
`tools/generate_settlers.py`. `/village colon` (ops) fait venir un colon tout de suite au village le plus proche.

### Bannière et entrée

- La **bannière** (`Nakasar_Peuples_Banner_Kweebec`, statue kweebec vanilla en parent) est posée au nord de la place.
  Elle porte un marqueur de carte découvrable (icônes `tools/generate_map_icons.py`) : `VillageEntrySystem` le révèle
  au joueur qui passe à moins de 300 blocs, et il reste ensuite sur sa carte et sa boussole.
- À moins de 40 blocs du cœur, un **titre d'écran** donne le nom du village, puis « peuple · rang · humeur » (le rang
  est « Étranger » jusqu'à l'étape 4). Il revient après être ressorti au-delà de 52 blocs.
- `VillageNoRegenSystem` : aucun PNJ à moins de 96 blocs d'un village ne se régénère (règle permanente n° 1).

### Nouvelles commandes

| Sous-commande | Qui | Effet |
| --- | --- | --- |
| `generer` | opérateur | bâtit un village kweebec (palier 0) centré sous les pieds, nom tiré de la liste |
| `site` | opérateur | nom, position, distance et direction du village le plus proche, à toute distance |

`effacer` retire aussi la bannière ; les bâtiments collés et le dépôt restent.

### Tester en jeu (étape 2)

1. Nouveau monde (ou monde existant : le village se pose au démarrage suivant). Attendre ~20 s après l'arrivée ; le
   journal du serveur dit `recherche d'un site de village kweebec` puis `village ... généré en x y z`.
2. `/village site` : nom, distance et direction du village. S'y rendre : la bannière apparaît sur la carte vers
   300 blocs, puis le titre d'écran à l'entrée du campement.
3. Vérifier les bâtiments, les Kweebecs, le tableau (ouest du cœur) et le dépôt (est).
4. Ailleurs, sur un terrain d'herbe : `/village generer` bâtit un second village sous les pieds (il faut être à plus
   de 146 blocs du premier).
5. Redémarrer : le village reste, aucun second village automatique n'apparaît.

### À vérifier en jeu (étape 2)

- Les prefabs se collent-ils (sinon `prefab introuvable` / `zone du prefab ... pas chargée` dans le journal) ? Les
  portes des maisons sont-elles tournées vers la place (abri ouest rotation 0, abri est 180°) ?
- Les Kweebecs des marqueurs d'apparition apparaissent-ils, et les patrouilles restent-elles dans le campement ?
- Le terrain aplani est-il propre (marches, trous, arbres coupés en l'air) ?
- La bannière garde-t-elle le modèle de la statue avec son marqueur de carte ? Le marqueur apparaît-il sur la carte
  après la révélation sans reconnexion ?
- Le titre d'écran s'affiche-t-il une seule fois par entrée ?

## Étape 3 : les demandes du tableau

### Modèles et tirage

Un modèle de demande est un asset JSON `Server/Nakasar/Requests/<Peuple>/<Id>.json` (`RequestTemplate`, décodé et
vérifié par `validateAssets` : type, paliers, objet, bande, distances, textes fr-FR et en-US). Chaque matin (6 h de jeu),
le tableau de chaque village tire **trois demandes** parmi les modèles de son peuple et de son palier, au poids, en
préférant trois types différents. Une demande remplie est remplacée tout de suite par une autre.

| Type | Ce qu'il faut faire | Modèles kweebecs | Essor |
| --- | --- | --- | --- |
| Récolte | déposer des objets au dépôt (ou les rendre) | baies rouges ×20, sève ×10, graines de carotte ×12, tronc de chêne ×16 | 10 |
| Fabrication | idem, objets fabriqués | lanternes kweebecs ×4, pain ×3 | 15 |
| Chasse | abattre la bande posée à 80-150 blocs ; les Trorks du même rôle tués à moins de 220 blocs du village comptent aussi | 2 guerriers + 1 chasseur, ou 2 cogneurs | 15 |
| Livraison | porter la missive (donnée à la prise) au guetteur posé à 90-150 blocs | guetteur Razorleaf | 10 |
| Escorte | délivrer le jeune captif gardé par 2 gardes trorks (80-140 blocs) et le ramener à moins de 14 blocs du cœur | captif orange | 20 |
| Défense | être au village la nuit (20 h à 6 h) : 4 Trorks attaquent à 30 blocs du cœur, il faut les abattre avant l'aube | 3 guerriers + 1 chasseur | 25 |

Récompense : l'essor au village (une seule fois par demande du tableau, même à plusieurs joueurs) et des **feuilles de
sève** (`Nakasar_Peuples_Favor_Kweebec`, faveur kweebec, modèle de la sève vanilla) au joueur, au sol si son sac est
plein. Une demande prise tient jusqu'au premier matin au moins 12 h plus tard ; échue, abandonnée ou échouée (captif
mort, aube sur une défense), elle se retire et la missive est reprise.

Les bandes, le guetteur et le captif ne sont posés que quand le joueur passe à moins de 72 blocs du lieu, ne sont pas
sauvegardés (ils reviennent à la session suivante) et ne se régénèrent jamais (règle n° 1).

### Suivi à l'écran (Objectives vanilla)

Le Java garde l'état des demandes (sauvegardé avec le joueur) ; le HUD les affiche avec les paquets vanilla
`TrackOrUpdateObjective` / `UntrackObjective` : titre, village et récompense, et une ligne de tâche avec l'avancement,
la distance et la direction du lieu (mise à jour chaque seconde quand elle change).

### Où prendre et rendre une demande

- **Le tableau** (ouest du cœur) : utilisé normalement, il ouvre le tableau à boutons, aux couleurs du peuple
  (`BoardPage_<Peuple>.ui`, générées par `tools/generate_board_ui.py` ; `BoardPage.ui` neutre pour un peuple sans
  thème ; maquettes `peuples/maquettes/tableau-par-peuple/`). En haut, le bandeau du peuple : emblème vanilla de la
  page des Souvenirs teinté à sa couleur (Voidtaken pour les Slothians, faute d'icône), palier, devise
  (`boardPage.motto.<Peuple>`), villageois, rang du joueur et sa jauge. À gauche, les trois demandes en cartes : icône
  d'objet vanilla du type (ou l'objet demandé), récompenses (essor, réputation, faveur en icône), jauge d'avancement
  d'une demande prise, **Prendre** / **Abandonner**. À droite, l'essor (jauge), le chantier (matériaux en icônes
  d'objets, coche verte quand le compte est bon ; ou fin des travaux et bâtiments), le dépôt en icônes et l'alerte de
  raid. En bas, les absents, **Rendre** et **Version texte** (page BlockLore). **Accroupi**, il ouvre directement la
  page texte (secours si la page à boutons ne s'affiche pas). `ValidateAssets` vérifie que chaque élément rempli par
  `BoardPage.java` existe dans chaque page et que chaque texture citée existe (pack ou
  `tools/vanilla-ui-textures-0.7.7.txt`).
- **Le crieur** (`Nakasar_Peuples_Kweebec_Crier`), posé deux blocs au sud du tableau quand un joueur approche : son
  dialogue `Kweebec_Crieur` ouvre les demandes, ou reprend les objets portés si le joueur a une demande ici. Tué, il
  revient au matin.
- Le dépôt : se tenir à moins de 6 blocs du coffre compte ce qu'il contient pour les récoltes et fabrications prises.
- Le tchat, avec les commandes ci-dessous.

Nouveaux types de dialogue : condition `HasRequest` (`RequestType` optionnel), effets `OpenRequests` et
`TurnInRequests`.

### Nouvelles commandes

| Sous-commande | Qui | Effet |
| --- | --- | --- |
| `demandes` | joueur | ouvre le tableau à boutons du village le plus proche |
| `mesdemandes` | joueur | liste ses demandes en cours, avec avancement, distance et direction |
| `prendre <n>` | joueur | prend la demande n° 1 à 3 |
| `rendre` | joueur | rend le dépôt et le sac pour ses demandes de ce village |
| `abandonner <n>` | joueur | abandonne sa demande n° 1 à 3 |
| `demande <modèle> [case]` | opérateur | pose ce modèle au tableau (ex. `Kweebec_Escort_Captive 2`) |
| `renouveler` | opérateur | tire trois nouvelles demandes |

`info` montre maintenant l'état des demandes ; `effacer` retire aussi le crieur.

### Tester en jeu (étape 3)

1. Aller au village kweebec (`/village site`). Le crieur apparaît devant le tableau ; l'utiliser ouvre son dialogue,
   « Montre-moi les demandes » ouvre le tableau à boutons. Utiliser le tableau donne la même page ; accroupi, la page
   texte.
2. **Récolte** : `/village demande Kweebec_Gather_Seeds 1`, puis **Prendre** la case 1. Le suivi d'objectif apparaît
   au HUD. Avoir 12 graines de carotte (`Plant_Seeds_Carrot`, récoltées ou données en créatif), les mettre dans le dépôt (est du cœur) :
   l'avancement monte, la demande se remplit, l'essor monte de 10 au tableau (`/village info`) et on reçoit une
   feuille de sève. Variante : garder les graines dans le sac et cliquer **Rendre**.
3. **Chasse** : `/village demande Kweebec_Hunt_Trorks 1`, prendre, suivre la direction du HUD ; la bande apparaît à
   moins de 72 blocs du lieu ; chaque Trork tué fait monter le compteur.
4. **Livraison** : `/village demande Kweebec_Delivery_Missive 1`, prendre (une missive arrive dans le sac), aller au
   guetteur et l'utiliser.
5. **Escorte** : `/village demande Kweebec_Escort_Captive 1`, prendre, battre les deux gardes, s'approcher du captif
   (il suit à moins de 14 blocs) et le ramener près du cœur.
6. **Défense** : `/village demande Kweebec_Defense_Night 1`, prendre, `/time midnight` en restant au village : une
   alerte annonce l'attaque et sa direction ; abattre les 4 Trorks avant l'aube.
7. Échéance : prendre une demande puis `/time` jusqu'au surlendemain matin : elle échoue (« Demande échue »).
8. Redémarrer : les demandes prises et leur avancement restent, le suivi revient au HUD.

### À vérifier en jeu (étape 3)

- Le suivi d'objectif vanilla au HUD : titre, description, ligne de tâche, compteur, et son retrait.
- Le tableau à boutons par peuple : mise en page, boutons (Prendre, Abandonner, Rendre, Version texte), teinte des
  emblèmes (couleur du `PatchStyle` ; sinon livrer des copies recolorées), jauges (`ProgressBar` à remplissage
  `Board/Bar_<Peuple>.png`), icônes d'objets (`ItemIcon`), pastilles qui prennent la largeur de leur texte.
- L'interaction avec le crieur, le guetteur et le captif (touche d'utilisation, mot « Parler ») et l'apparence
  vanilla choisie (Kweebec rose, Razorleaf, orange).
- Le captif qui suit le joueur ; les Trorks de la défense qui marchent vers le cœur (point de laisse).
- La feuille de sève et la missive (modèles de la sève et du parchemin vanilla en main et au sol).

## Étape 4 : la réputation

### Deux réputations, un rang

Chaque joueur a deux réputations (GDD, Jauges) :

- **de village**, propre à chaque village, gardée avec le joueur (`PeuplesPlayer`, champs `Reputation` et `Visits`) ;
- **de peuple**, partagée par tous les villages d'un peuple, tenue par le `ReputationPlugin` vanilla (groupe
  `Nakasar_Peuples_Kweebec`, stockage par joueur). Elle reçoit un tiers de chaque gain ou perte de village.

Le rang d'un joueur dans un village est celui de la **meilleure des deux** : un ami des Kweebecs est accueilli dans un
village kweebec qu'il découvre. Hors des villages, seul le rang de peuple compte.

| Rang | Réputation | Attitude des villageois | Ce qu'il ouvre |
| --- | --- | --- | --- |
| Honni | -1000 à -100 | hostile (les gardes attaquent) | seule la première demande, pour se racheter |
| Étranger | -100 à 50 | neutre (gardes méfiants, petits qui fuient) | une demande au tableau, échoppe fermée |
| Toléré | 50 à 200 | neutre | les trois demandes, troc de base |
| Ami | 200 à 500 | amicale | échoppe avancée |
| Hôte | 500 à 1000 | amicale | réserve de l'hôte (tenue kweebec, lit, mobilier) |
| Champion | 1000 et plus | vénérée | toutes les échoppes (parcelle et avant-poste : étapes suivantes) |

Les rangs sont des assets vanilla `Server/NPC/Reputation/Ranks/Nakasar_Peuples_<Rang>.json` ; `validateAssets`
vérifie qu'ils collent à l'enum `Rank` (bornes, attitude). Un joueur neuf part de 0 (Étranger).

### Gains et pertes

| Action | Village | Peuple |
| --- | --- | --- |
| Remplir une demande | + l'essor de la demande (10 à 25), à chaque joueur qui la remplit | + un tiers |
| Frapper un villageois du peuple | -5 | -1 |
| Tuer un villageois du peuple | -40 | -13 |
| Casser un bloc d'un bâtiment collé, du dépôt, du tableau ou de la bannière (pas les potagers) | -2 par bloc | 0 |
| Absence de plus de 10 jours de jeu | -10 par jour de plus, jamais sous Toléré | |

Hors de tout village, frapper ou tuer un Kweebec coûte la même chose à la réputation de peuple seule. Chaque changement
s'annonce par une notification ; un changement de rang l'annonce au tchat avec ce que le nouveau rang ouvre. Une
demande peut fixer son gain avec le champ optionnel `Reputation` (sinon son essor).

### Attitude des villageois

Un fournisseur d'attitude Java (`VillageAttitudeSystem`, priorité 90, avant celui du ReputationPlugin à 100) donne à
un PNJ du groupe de réputation l'attitude du rang du joueur dans le village de son peuple le plus proche (moins de 96
blocs). Le groupe de réputation couvre le groupe vanilla `Kweebec` (tous les rôles `Kweebec*` : Razorleaf, jeunes,
marchand vanilla) et le groupe du mod `Nakasar_Peuples_Kweebec` (crieur, marchand). Les rôles vanilla font le reste :
les gardes Razorleaf attaquent un joueur hostile et surveillent un neutre, les petits fuient, tous sont calmes avec un
ami.

### Le marchand et les échoppes

La marchande (`Nakasar_Peuples_Kweebec_Merchant`, Kweebec Rootling) est posée deux blocs au sud du dépôt quand un
joueur approche, comme le crieur ; tuée, elle revient au matin. Son dialogue `Kweebec_Marchand` change selon le rang et
ouvre l'une des trois échoppes de troc vanilla (`Server/BarterShops/Nakasar_Peuples_Kweebec_<Rang>.json`), payées en
feuilles de sève, stock partagé par le monde et renouvelé tous les 3 jours à 6 h :

| Échoppe | Rang | Contenu (objets vanilla) |
| --- | --- | --- |
| Troc de base | Toléré | graines, sève, pâte, et un lot tournant de nourriture |
| Échoppe avancée | Ami | lanternes kweebecs, essence de vie concentrée, baies rares et tartes, un lot de recettes |
| Réserve de l'hôte | Hôte | casque et plastron kweebecs, lit kweebec, un lot de peluches et de jeunes chênes |

La page est la `BarterPage` vanilla (celle du marchand kweebec), donc pas de nouvelle page `.ui`. Secours au tchat :
`/village troc`, et `/village tchat Kweebec_Marchand` pour le dialogue.

Le crieur gagne un accueil Honni (« Que viens-tu faire ici ? ») qui ne propose que les demandes. Le tableau affiche le
rang du joueur, sa réputation et ce que le rang ouvre ; sous Toléré, les cases 2 et 3 sont fermées.

Nouveaux types de dialogue : condition `Rank` (`Min`, `Max`, `Scope` `Village`|`People`, `People`), effets
`OpenShop` (`Shop` optionnel : sans lui, la meilleure échoppe du rang) et `AddReputation` (`Amount`). L'en-tête des
dialogues montre le rang du joueur.

### Nouvelles commandes

| Sous-commande | Qui | Effet |
| --- | --- | --- |
| `reputation` | joueur | rang, réputations de village et de peuple, ce qu'ouvre le rang, échoppe ouverte |
| `troc` | joueur | ouvre la meilleure échoppe que le rang ouvre |
| `rep <valeur>` | opérateur | fixe sa réputation de village (Toléré 50, Ami 200, Hôte 500, Champion 1000) |
| `reppeuple <valeur>` | opérateur | fixe sa réputation de peuple (ReputationPlugin vanilla) |

### Tester en jeu (étape 4) : un étranger et un ami

1. Aller au village kweebec (`/village site`) avec un joueur neuf : le titre d'entrée dit « Étranger ».
   `/village reputation` donne 0 et 0. Le tableau n'ouvre que la case 1. Les gardes Razorleaf suivent le joueur du
   regard, les petits s'écartent. La marchande (sud du dépôt) refuse le troc : « il faut être Toléré ».
   `/village troc` répond pareil.
2. `/village rep 220` : notification et message « Tu es maintenant Ami ». Les gardes se calment, les petits ne fuient
   plus. La marchande propose « Troc » et « Échoppe avancée » ; « Réserve de l'hôte » reste grisé avec son indice.
   Ouvrir les deux échoppes, acheter un objet avec des feuilles de sève (`/give Nakasar_Peuples_Favor_Kweebec 64`).
3. `/village rep -150` : rang Honni. Les gardes attaquent ; le crieur n'offre que les demandes ; le tableau garde la
   case 1 pour se racheter.
4. Peuple : `/village rep 0` puis `/village reppeuple 300`. Le rang du village redevient Ami grâce au peuple.
5. Pertes : `/village rep 60`, frapper un villageois (-5 et notification), casser un bloc d'une maison (-2, une
   notification toutes les 6 s au plus), puis remplir une demande (`/village demande Kweebec_Gather_Seeds 1`) : +10.
6. Redémarrer : réputations, rang et stock des échoppes restent.

### À vérifier en jeu (étape 4)

- L'attitude change bien selon le rang (priorité 90 avant le ReputationPlugin), y compris pour les PNJ du prefab déjà
  chargés.
- La `BarterPage` vanilla ouverte depuis le dialogue : titre, prix en feuilles de sève, stock, renouvellement.
- L'apparence Kweebec Rootling de la marchande et sa place devant le dépôt.
- Le marchand vanilla du prefab (`Kweebec_Merchant`) ouvre encore sa boutique vanilla sans condition de rang.
- Pas encore fait : la perte pour un coffre du village vidé (aucun événement de retrait de conteneur connu), la
  parcelle de l'hôte et l'avant-poste du champion (étapes suivantes).

## Étape 5 : les chantiers et la vie du village

Le village grandit sous les yeux du joueur : quand la jauge d'essor est pleine et que le dépôt contient les
matériaux du palier, un chantier s'ouvre. Autour des bâtiments du palier suivant monte un chantier propre au peuple
(voir « Chantiers par peuple »), des bâtisseurs y travaillent, puis le prefab vanilla est collé au bout de la durée du
chantier.

### Le chantier

`VillageLifeSystem` passe toutes les 2 s, seulement pour les villages qui ont un joueur à moins de 160 blocs. Il ouvre
le chantier quand la jauge est pleine, et le finit quand l'heure de fin est passée.

| Palier | Durée (heures de jeu) | Matériaux pris au dépôt |
| --- | --- | --- |
| 1 | 24 | 24 `Wood_Oak_Trunk`, 16 `Rock_Stone_Cobble`, 12 `Ingredient_Fibre` |
| 2 | 24 | 48 `Wood_Oak_Trunk`, 32 `Wood_Hardwood_Planks`, 24 `Soil_Clay_Brick`, 4 `Furniture_Kweebec_Lantern` |
| 3 | 24 | 64 `Wood_Oak_Trunk`, 32 `Plant_Leaves_Oak`, 4 `Plant_Sapling_Oak`, 20 `Ingredient_Life_Essence` |

Les tables sont dans `tools/generate_village_layouts.py` (`CHANTIERS`), qui écrit `Chantiers` dans
`Nakasar/VillageLayouts/Kweebec_Oak.json`.

- À l'ouverture, les matériaux sont retirés du coffre du dépôt. Chaque parcelle est ensuite aplanie, ou débarrassée
  de ses ruines. Les grands bâtiments reçoivent la première phase du chantier de leur peuple, sur un anneau d'un bloc
  autour de leur emprise (voir ci-dessous).
- Une parcelle où un joueur a construit n'est jamais touchée. Le bâtiment est sauté et le tableau le dit.

### Chantiers par peuple

Les échafaudages des débuts étaient provisoires (Kevin, 15 novembre 2026). Chaque peuple bâtit selon ses techniques,
en 4 phases réparties sur la durée du chantier : préparation, montée, charpente, finitions. Le code est dans
`village/SiteStyle.java`. Tous les blocs sont vanilla et viennent des prefabs vanilla du peuple (Npc/Kweebec,
Npc/Trork, Npc/Feran, Npc/Outlander, Npc/Slothian dans Assets.zip 0.7.2).

![Les 4 phases du chantier de chaque peuple](images/chantiers-phases.png)

| Peuple | Préparation | Montée | Charpente | Finitions |
| --- | --- | --- | --- | --- |
| Kweebecs | jardin semé (fleurs, fougères, mousse), buissons aux angles | troncs de chêne couverts de lierre aux angles | guirlande de feuillage, touffes aux angles, lianes qui pendent | grandes fleurs, lanternes kweebec à des cordes |
| Trorks | pieux d'os, tas d'os, rondins entassés | palissade de rondins de hêtre (ouverture au milieu des côtés) | auvents de cuir sur les angles | crânes, torches grossières |
| Feran | briques de grès qui sèchent, poteries, argile | premier rang de briques, poteaux de bois sec | deuxième rang, ombrières de peau sur les angles | torches feran aux ouvertures |
| Renoncés | cairns de schiste, rondins de sapin, caisse | poteaux de sapin, passerelle basse de bois mort | passerelle haute, chaînes | torches aux angles |
| Slothians | mousse, fougères, jeunes bambous | cannes de bambou aux angles et au milieu des côtés | cannes plus hautes que le toit, plancher tropical, lianes | torches de jungle |

- Le plan d'une phase est une fonction pure de l'emprise, du sol de pose et de la phase. `VillageLifeSystem` appelle
  `Chantiers.grow` : quand la phase du moment (selon l'heure de jeu entre le début et la fin) dépasse celle déjà posée,
  le chantier de chaque grand bâtiment passe à la nouvelle phase et une ligne propre au peuple s'affiche dans le tchat
  (`chantier.phase.<Peuple>.<n>`). La phase posée n'est pas sauvegardée : après un redémarrage, la phase en cours est
  reposée à l'identique, sans message.
- On ne pose que dans l'air, dans les plantes (hors feuillages) ou à la place de nos propres blocs d'une autre phase.
  On ne retire que les blocs que le plan pose à cette position, toutes phases confondues. Les retraits se font de haut
  en bas, les poses de bas en haut. Ce qui va au sol (fleurs, poteries, os) n'est posé que sur un bloc plein.
- Le tas de matériaux du centre diminue à la phase 3 et disparaît à la phase 4.
- Les blocs posés par les chantiers sont dans `Burning.REQUIRED_BLOCKS` : validateAssets vérifie qu'ils existent.
- Le repérage des blocs gênants ne change pas. Les parcelles sont toutes examinées avant que la première phase ne soit
  posée, et le chantier des bâtiments en travaux est retiré avant de bâtir une parcelle sautée puis dégagée.

### Blocs qui gênent un chantier

Une parcelle est sautée dès qu'un seul bloc « posé à la main » se trouve dans son emprise, au-dessus du sol de pose,
sur `min(hauteur du prefab, 12)` niveaux. Comptent comme naturels, donc ne gênent pas : relief (`Soil_`, `Rock_` hors
briques, pavés, poli, lisse, demi-blocs, escaliers, chemins), `Plant_`, troncs, branches et racines, `Ore_`, `Rubble_`,
`Fluid_`, et quelques `Deco_` naturels (ruches, nids, coquillages, toiles, os).

- À l'ouverture du chantier, chaque parcelle sautée est annoncée dans le tchat avec son nombre de blocs gênants et le
  premier trouvé (id et coordonnées). Le journal du serveur garde la même ligne.
- Le tableau et `/village chantier` donnent la même ligne : pour les parcelles sautées du chantier en cours, ou pour
  celles du prochain chantier avant qu'il ne s'ouvre.
- `/village genes [bâtiment]` liste les coordonnées (12 dans le tchat, 64 repères au plus par parcelle) et affiche pendant
  60 s, au seul joueur, le contour de la parcelle examinée (fil de fer jaune) et un cube rose sur chaque bloc gênant.
  Ce sont les formes de débogage du moteur (celles de `/debug shape`) : aucun bloc ni entité n'est posé.
- Une parcelle dégagée avant la fin du chantier est bâtie à la fin, sans attendre le chantier suivant.
- Toutes les parcelles sont examinées avant de poser le moindre chantier, pour que le chantier d'un bâtiment ne
  fasse pas sauter son voisin.
- À la fin, le chantier est retiré et le prefab collé. Le palier monte, la jauge repart à 0, et un titre s'affiche à
  tous les joueurs à moins de 160 blocs (avec un message dans le chat).
- Un chantier en cours se voit au tableau (heures restantes, bâtiments, parcelles sautées). Sinon le tableau dit ce
  qu'il manque : jauge, matériaux déposés/attendus, nombre de bâtiments et durée.

### Bâtiment brûlé

`Burning` remplace les blocs d'un bâtiment par leur version calcinée vanilla : bois vers `Wood_Burnt_*` ou
`Wood_Blackwood_*` (25 % du bois au-dessus de 3 blocs s'effondre), feuillages vers `Plant_Leaves_Burnt` (45 %, le
reste disparaît), plantes et déco retirées, meubles en demi-planches noires (20 %), herbe vers `Soil_Grass_Burnt`,
terre vers `Soil_Dirt_Burnt`, mousse et litière vers `Soil_Ash`. Les coffres et autres conteneurs ne sont jamais
touchés.

Un bâtiment brûlé fait perdre un palier au village (recommandation du GDD pour un raid perdu ; les raids arrivent à
l'étape 6). Le chantier en cours est annulé et la jauge repart à 0. Le chantier suivant rebâtit les bâtiments brûlés
de son palier, ruines débarrassées. Pour l'instant, seule la commande `bruler` déclenche un incendie.

### Les villageois à métier

Chaque palier ajoute des Kweebecs vanilla à métier, avec leur rôle (`Nakasar_Peuples_Kweebec_<Métier>`, généré par
`tools/generate_villagers.py`) et leur dialogue (`Kweebec_<Métier>`).

| Villageois | Palier | Travail | Maison |
| --- | --- | --- | --- |
| Jardinière | 0 | Potager | Abri ouest |
| Bâtisseur | 0 | chantier en cours | Abri est |
| Guetteur | 0 | Tour de guet | Abri est |
| Puisatière | 1 | Puits | Maison sud-ouest |
| Éleveur | 1 | Enclos | Maison sud-ouest |
| Garde | 2 | Tour est | Maison des gardes |
| Soigneuse | 2 | Grande maison | Grande maison |
| Ancien | 3 | Grand-père | Grand-père |
| Jardinier du bourg | 3 | Grand potager | Grande maison |

- Le jour, chacun reste près de son poste et y joue l'animation de son métier (Interact, Feed, LookAround...) ou flâne
  autour. La nuit (20 h à 6 h), il rentre chez lui, ou reste à son poste si sa maison a brûlé.
- Le bâtisseur va devant le premier bâtiment du chantier. Pendant un chantier, jusqu'à 3 aides de jour s'ajoutent, un
  par bâtiment.
- Un villageois bloqué à plus de 18 blocs de sa cible pendant 40 s est téléporté, mais seulement si aucun joueur n'est
  à moins de 20 blocs de lui ni de sa cible.
- Un villageois tué revient le lendemain (jour de jeu).
- Les villageois n'apparaissent que si un joueur est à moins de 72 blocs. Ils ne sont pas sauvegardés, le système les
  recrée.
- Parler à un villageois ouvre son dialogue de métier. Le bâtisseur répond aussi sur l'état du chantier (effet
  `ChantierStatus`, condition `Chantier`). Ce dialogue a son repli en texte dans le chat, comme les autres.

### Nouvelles commandes

| Sous-commande | Qui | Effet |
| --- | --- | --- |
| `chantier` | joueur | état du chantier en cours, ou ce qu'attend le prochain (jauge, matériaux, ruines) |
| `metiers` | joueur | villageois à métier présents et postes à pourvoir, aides de chantier |
| `genes [bâtiment]` | joueur | blocs qui gênent les chantiers : coordonnées et repères en jeu pendant 60 s |
| `lancer` | opérateur | ouvre le chantier du palier suivant sans jauge ni matériaux |
| `finir` | opérateur | finit le chantier en cours tout de suite |
| `bruler [bâtiment]` | opérateur | brûle un bâtiment (au hasard dans le palier le plus haut si aucun n'est donné), le village perd un palier |
| `palier <n>` | opérateur | bâtit d'un coup jusqu'au palier n (sans chantier) |

### Tester en jeu (étape 5) : le village grandit sous les yeux

1. `/village site` puis `/village metiers` : la jardinière, le bâtisseur et le guetteur sont à leur poste (potager,
   tour de guet). Leur parler ouvre leur dialogue.
2. `/village chantier` : le tableau dit ce qu'attend le palier 1. Mettre les matériaux dans le coffre du dépôt
   (`/give Wood_Oak_Trunk 24`, `/give Rock_Stone_Cobble 16`, `/give Ingredient_Fibre 12`), puis `/village essor 100`.
   En moins de 2 s, les matériaux disparaissent du coffre, les parcelles sont aplanies et le jardin est semé.
   Le bâtisseur et ses aides y vont. `/village chantier` donne les heures restantes.
3. Attendre 24 h de jeu (`/time` pour avancer) : toutes les 6 h le chantier change de phase (troncs, feuillage et
   lianes, lanternes) avec une ligne dans le tchat. Ou `/village finir` : le chantier disparaît, le puits, l'échoppe,
   la maison sud-ouest et l'enclos apparaissent, avec le titre « palier 1 ». La puisatière et l'éleveur arrivent.
4. La nuit (`/time midnight`), les villageois rentrent dans leur maison ; au matin ils retournent au poste.
5. `/village lancer` puis `/village finir` pour les paliers 2 et 3 : garde, soigneuse, ancien, jardinier du bourg.
6. `/village bruler Grande_Maison` : la maison est noircie et à moitié effondrée, coffres intacts, le village perd un
   palier et la soigneuse dort à son poste. `/village lancer` puis `/village finir` : la maison est rebâtie.
7. Construire un mur sur une parcelle vide, puis lancer le chantier : ce bâtiment est sauté et `/village chantier` le
   signale.
8. Redémarrer pendant un chantier : il reprend avec la même heure de fin.

### À vérifier en jeu (étape 5)

- Que les animations de métier jouent sur le modèle Kweebec_Sapling (Interact, Feed, LookAround, Rest...).
- Le retour à la maison la nuit : le Seek et la laisse (`setLeashPoint`) suffisent-ils à passer les portes des prefabs ?
- L'allure des chantiers de chaque peuple, et que leur retrait ne laisse rien derrière (voir « Chantiers par
  peuple »). Que le lierre (`Plant_Vine`, rotations 0 à 3 supposées tournées vers le tronc), les lianes
  (`Plant_Vine_Hanging`) sous le feuillage et les lanternes sous les cordes tiennent sans tomber.
- L'allure d'un bâtiment brûlé (proportions d'effondrement et de feuilles restantes).
- Que l'aplanissement des parcelles ne coupe pas le relief autour de façon trop visible.
- Le titre de fin de chantier, et sa portée de 160 blocs.

## Étape 6 : les raids et la chaîne kweebec

Une nuit, une bande trork marche sur le village. Les gardes du village se battent aux côtés du joueur. Au bout, un
bilan : victoire ou défaite, et un bâtiment brûle si le raid est perdu. La chaîne de quêtes kweebec, menée par le chef
du village, finit par la Graine d'Écho.

### Quand un raid arrive

Un raid est attendu (sauvegardé avec le village) pour une nuit donnée, pour l'une de ces causes :

- **palier gagné** : le village attire un raid la nuit qui suit ;
- **tirage du matin** : 10 %, 20 %, 30 % ou 40 % de chances selon le palier, jamais moins de 2 nuits après le dernier raid ;
- **demande de défense** du tableau, ou **veillée** de la chaîne : le raid vient la nuit même ;
- **commande** (`raidprevoir`, `raidlancer`).

Le raid commence de nuit, avant 4 h, et seulement si un joueur est à moins de 80 blocs du cœur. Personne n'est venu ?
Le raid attend la prochaine nuit, sans pénalité. Un redémarrage pendant un raid le fait reprendre depuis l'annonce, lui
aussi sans pénalité.

### Déroulé

1. **Annonce, 1 min.** Les tambours (cor vanilla) sonnent, un titre et un message donnent la direction du camp trork, à
   42 blocs du cœur (deux camps à partir du palier 2). Les gardes Razorleaf (1, 2, 4 ou 6 selon le palier) se postent
   autour du cœur. L'évènement de monde `Nakasar_Peuples_Raid` (moteur des brèches vanilla) place le compte à rebours
   sur la carte, avec l'icône de la brèche gobeline.
2. **Assaut, 5 min au plus.** La vague apparaît au camp : 5, 7, 9 ou 12 assaillants (pillards, cogneurs, brutes, puis un
   chef de guerre à partir du palier 2). Au camp, l'évènement joue le titre « Les Trorks attaquent ! » et le cri du chef
   trork. Les assaillants marchent sur le cœur et frappent à vue joueurs et Kweebecs. Les gardes ne quittent pas leur
   poste de plus de 24 blocs.
3. **Bilan.**
   - Victoire (tous les assaillants abattus) : +30 d'essor, et pour chaque joueur présent +50 de réputation et 4 Feuilles
     de sève. Les joueurs qui ont abattu un assaillant reçoivent aussi un Trophée trork.
   - Défaite : temps écoulé, village abandonné 90 s, ou tous les gardes tombés avec un Trork au cœur. Un bâtiment brûle
     et le village perd un palier, comme le recommande le GDD. Un village sans plan voit sa jauge d'essor se vider.
   - Les demandes de défense sont remplies à la victoire et échouent à la défaite.
   - Le bilan s'affiche au tableau (page texte) et avec `/village raid`.

Aucun PNJ du raid ne se soigne (règle n° 1 ; `VillageNoRegenSystem` couvre aussi les raids). Les apparences, armes,
attaques, butins et sons sont vanilla (règle n° 2).

### Les PNJ du raid

| Rôle | Apparence et arme vanilla | PV | Dégâts |
| --- | --- | --- | --- |
| `Nakasar_Peuples_Raider_Trork_Warrior` | Trork_Warrior, hache de bataille | 61 | 23 |
| `Nakasar_Peuples_Raider_Trork_Mauler` | Trork_Mauler, masse | 61 | 23 |
| `Nakasar_Peuples_Raider_Trork_Brawler` | Trork_Brawler, gourdin | 80 | 20 |
| `Nakasar_Peuples_Raider_Trork_Warlord` | Trork_Guard, hache de bataille | 150 | 28 |
| `Nakasar_Peuples_Kweebec_Defender` | Razorleaf, lance de feuille | 105 | 14 |

Les rôles du mod sont nécessaires parce que les rôles vanilla ne se battraient pas entre eux. Les Razorleaf vanilla ne
voient que les joueurs, et les Trorks vanilla dorment la nuit. `RaidAttitudeSystem` (fournisseur d'attitude de
priorité 80) rend les pillards hostiles aux Kweebecs, et réciproquement. Le générateur est `tools/generate_raids.py`.

### La chaîne kweebec

Le chef (Treesinger vanilla, à l'est du cœur, dialogue `Kweebec_Chef`) propose une étape par rang :

| Étape | Rang | Ce qu'il faut faire | Réputation |
| --- | --- | --- | --- |
| 1. Soigner les jeunes pousses | Toléré | donner 10 Sève au chef | +80 |
| 2. Libérer les prisonniers | Ami | escorte depuis le camp trork (90 à 150 blocs, 3 gardiens) | +120 |
| 3. Replanter le bosquet brûlé | Ami | planter 6 pousses de chêne dans le bosquet calciné (60 à 110 blocs) | +150 |
| 4. Veiller le Grand-Père | Hôte | repousser le raid que la veillée attire la nuit même | +200 |
| 5. La Graine d'Écho | Champion | le chef donne la Graine d'Écho | — |

- Les étapes 2 à 4 sont des demandes (modèles `Kweebec_Chain_*`, jamais au tableau). Elles n'expirent pas et posent le
  drapeau `Kweebec_Chain_<n>` quand elles sont remplies.
- La plantation est un nouveau type de demande, `Plant`. À l'approche, le lieu devient un bosquet brûlé (sol calciné,
  souches) ; chaque pousse plantée, ou chaque arbre qui en a poussé, compte.
- La Graine d'Écho (modèle du sac de graines de chêne vanilla) ne se plante pas encore : elle sert à l'étape 8.
- Le générateur est `tools/generate_chain.py`. Le garde et le guetteur répondent « Aux armes ! » pendant un raid, et
  sinon donnent une rumeur et l'état du raid attendu.

### Nouvelles commandes

| Sous-commande | Qui | Effet |
| --- | --- | --- |
| `raid` | joueur | raid attendu ou en cours au village le plus proche, bilan du dernier |
| `chaine` | joueur | étapes de chaîne faites et prochaine étape |
| `raidlancer` | opérateur | lance un raid tout de suite (de jour aussi) |
| `raidfinir <gagne\|perdu>` | opérateur | bilan tout de suite |
| `raidannuler` | opérateur | annule le raid en cours ou attendu |
| `raidprevoir` | opérateur | prévoit un raid cette nuit |
| `chaineetape <0-5>` | opérateur | règle les étapes de chaîne faites |

### Tester en jeu (étape 6) : une nuit gagnée, une nuit perdue

Préparation : un village kweebec généré (`/village generer`), palier 1 au moins (`/village palier 1`), pour avoir un
bâtiment à brûler.

**Nuit gagnée**

1. `/time midnight`, puis `/village raidprevoir`. En moins d'une seconde, les tambours sonnent. Le titre « Tambours de
   guerre » et le message donnent la direction. Deux gardes Razorleaf se postent au cœur, et le compte à rebours
   apparaît sur la carte.
2. Au bout d'1 min, 7 Trorks apparaissent à environ 42 blocs, avec le titre « Les Trorks attaquent ! ». Ils marchent sur
   le cœur, et les gardes les attaquent dès qu'ils les voient.
3. Les abattre tous : titre « Raid repoussé » et bilan dans le chat (+30 essor, +50 réputation, 4 Feuilles de sève,
   Trophée trork). `/village raid` et le tableau (accroupi) montrent le bilan.

**Nuit perdue**

1. Le lendemain soir (`/time midnight`), `/village raidlancer`. S'éloigner à plus de 160 blocs pendant 90 s, ou
   `/village raidfinir perdu`.
2. Titre « Le village brûle » : un bâtiment du palier le plus haut est noirci et le village perd un palier. Le bilan
   le nomme.

**Chaîne**

1. `/village rep 60`, puis parler au chef avec 10 Sève (`/give Ingredient_Tree_Sap 10`) : étape 1.
2. `/village rep 250` : le chef propose l'escorte, puis le bosquet (`/give Plant_Seeds_Oak 6`).
3. `/village rep 600` : la veillée prévoit le raid de la nuit ; le gagner remplit l'étape 4.
4. `/village rep 1000` : le chef donne la Graine d'Écho. `/village chaineetape <n>` saute des étapes.

Le joueur peut aussi prendre la défense au tableau (`/village demande Kweebec_Defense_Night 1`, puis `/village prendre 1`) :
le raid vient la nuit même.

### À vérifier en jeu (étape 6)

- Que les gardes et les pillards se battent vraiment (fournisseur d'attitude de priorité 80, capteur `Mob` sur les PNJ).
- Que les attaques vanilla `Trork_Warrior_Battleaxe_*` vont avec les masses et gourdins du cogneur et de la brute.
- Le compte à rebours sur la carte, le titre au camp et le cri du chef trork (évènement de monde).
- La marche sur le cœur : est-ce que le Seek et la laisse suffisent à traverser le village ?
- Le bosquet brûlé : allure, et que les graines de chêne posées comptent bien (bloc `Plant_Sapling_Oak`).
- L'allure du Trophée trork et de la Graine d'Écho en main (modèles de blocs et de sac vanilla).

## Étape 7 : la route trork, la Peinture de guerre et le Klops errant

La zone 1 offre maintenant deux routes : le village kweebec (étapes 2 à 6) ou le camp trork. Aider l'un coûte auprès
de l'autre. Le Klops errant passe de l'un à l'autre, troque et confie des colis.

### Le camp trork

- Posé tout seul (`TrorkCampSeeder`) à 220-450 blocs du premier village kweebec, une fois celui-ci posé. Les sites
  suivent les mêmes règles (herbe, pas d'eau, relief modéré), avec 60 % d'herbe au lieu de 80 %. À la main :
  `/village generer trork`.
- Plan `Trork_Camp` (`tools/generate_village_layouts.py`) : 16 prefabs vanilla `Npc/Trork` « feuilles » (feu de camp,
  tentes, tours de guet, terrier, piège, réserves, entrepôt...). Les Encampment vanilla ne servent pas, parce qu'ils
  posent des `Prefab_Spawner_Block`. Les quatre paliers se bâtissent par chantiers, avec de la viande, des peaux, du
  bois, de la pierre et des os.
- Les Trorks du camp sont des **rôles vanilla** (`Trork_Guard`, `Trork_Warrior`, `Trork_Hunter`, `Trork_Brawler`,
  `Trork_Sentry`, `Trork_Shaman`), postés comme les métiers kweebecs, sans dialogue. Leur IA vanilla lit le rang du
  joueur au camp : Honni, ils attaquent ; neutre, ils saluent ; amical, ils l'ignorent.
- Le crieur (`Trork_Sentry`), la marchande (`Trork_Doctor_Witch`) et le chef (`Trork_Chieftain`) sont des rôles du mod,
  immobiles. Le dépôt est le coffre grossier vanilla, le tableau le panneau grossier, la bannière des crânes vanilla
  (marqueur de carte « Camp trork »).
- Un camp trork n'est jamais pillé par un raid.

![Plan du camp trork : paliers 0 à 3, postes des Trorks](images/plan_trork_camp.png)

### Réputation trork

- Groupe de réputation `Nakasar_Peuples_Trork` (groupe PNJ vanilla `Trork` = `*Trork*`). Un joueur commence **Honni
  (-250)** auprès du peuple et de chaque camp (`People.initialReputation`, contrôlé par validateAssets).
- Hors d'un camp, les Trorks sauvages suivent la réputation de peuple : hostiles tant qu'elle est basse. Frapper ou tuer
  un Trork hors d'un camp ne coûte rien. Les bandes des demandes et les pillards des raids ne coûtent jamais rien.
- Les pillards des raids restent hostiles à tout joueur, même ami des Trorks ou peint.

### Apprivoiser par la viande

Les Trorks vanilla repèrent la viande au sol à 15 blocs, vont la ramasser et la mangent (`Dropped_Meat`). Un Trork qui
voit un joueur hostile le poursuit d'abord : il faut jeter la viande et s'éloigner.

- `MeatOfferings` suit la viande (tout objet `*meat*`) jetée par un joueur à moins de 40 blocs d'un camp. Si elle
  disparaît sans qu'un joueur la ramasse, avec un Trork à moins de 4 blocs, le joueur gagne +15 de réputation au camp
  par morceau (4 au plus par tas).
- Le crieur et le chef prennent aussi 5 Viande crue contre +40, même au rang Honni.
- La viande mène au plus jusqu'à **Toléré** (50). Au-delà, il faut les demandes du tableau et la chaîne.

### Demandes du camp

Les titres tiennent dans le suivi du HUD : 24 caractères au plus, contrôlé par le générateur.

| Demande | Type | Palier | Quoi |
|---|---|---|---|
| Viande pour le feu | récolte | 0 | 8 Viande crue |
| Des peaux | récolte | 0 | 6 Peau légère |
| Du bois pour le camp | récolte | 0 | 16 Tronc de chêne |
| Des os à graver | récolte | 1 | 8 Fragment d'os |
| Brochettes du festin | fabrication | 2 | 4 Brochette de viande |
| Chasser les loups | chasse | 0 | 2 loups noirs à 70-130 blocs |
| Chasser le Mosshorn | chasse | 1 | 1 Mosshorn à 80-140 blocs |

La faveur trork est la **Dent de trophée** (modèle du fragment d'os vanilla). La marchande ouvre trois échoppes : la
camelote au rang Toléré, les armes trorks vanilla au rang Ami, l'armure trork vanilla au rang Hôte.

### La chaîne trork (chef « Croc-de-Fer »)

| Étape | Rang | Quoi | Réputation |
|---|---|---|---|
| 1. Nourrir le feu | Toléré | donner 10 Viande crue au chef | +80 |
| 2. Chasser les loups | Ami | 3 loups noirs à 60-120 blocs | +120 |
| 3. Abattre deux Mosshorns | Ami | 2 Mosshorns à 80-140 blocs | +150 |
| 4. Battre le clan rival | Hôte | un cogneur et deux gardes trorks à 120-180 blocs | +200 |
| 5. Peinture de guerre | Champion | le chef donne la Peinture de guerre | |

### Réputations croisées (`reputation/Rivals`)

- Chaque gain de réputation de village chez un peuple retire la moitié de ce gain à la réputation de peuple de son
  rival (Kweebecs et Trorks).
- Chaque étape de chaîne d'un peuple fait perdre **un rang** chez le rival, sur la réputation de peuple et sur celle de
  chacun de ses villages. La valeur garde sa place dans le rang d'en dessous. Honni ne descend plus.

### La Peinture de guerre

- Pot `Nakasar_Peuples_War_Paint` (modèle de la petite potion rouge vanilla). Le clic secondaire met ou ôte la peinture.
  Le pot n'est pas consommé. Le drapeau `Trork_War_Paint` est sauvegardé avec le joueur.
- Peint, le joueur a une teinte ocre rouge et une icône d'effet. Hors d'un camp, les Trorks sont au moins neutres envers
  lui. Les Kweebecs le voient un rang plus bas : une échoppe ou une étape de chaîne peut se fermer.

### Le Klops errant

- Un seul par monde, rôle `Nakasar_Peuples_Klops_Wanderer` (modèle Klops_Merchant). Chaque jour de jeu, il s'arrête dans
  un autre village du mod : les villages sont rangés par id, et le jour modulo leur nombre choisit le village. Il
  n'apparaît qu'à l'approche d'un joueur, à l'ouest du cœur, et part au changement de jour. S'il est tué, il revient le
  lendemain.
- Son dialogue `Klops_Errant` propose trois choses :
  - le troc `Nakasar_Peuples_Klops` : 2 faveurs de n'importe quel peuple contre un Rouage klops, et des rouages contre
    du lin, des potions ou des faveurs ;
  - un **colis** pour un autre village, tiré au hasard : arriver à moins de 12 blocs de son cœur avec le colis le livre,
    pour 3 rouages et +30 de réputation dans ce village ;
  - la tournée du lendemain.

### Nouvelles commandes

| Commande | Qui | Effet |
|---|---|---|
| `/village generer trork` | op | pose un camp trork autour du joueur |
| `/village klops` | joueurs | où est le Klops aujourd'hui et demain, et pour qui est le colis porté |
| `/village peinture` | op | donne le pot de Peinture de guerre |

### Tester en jeu (étape 7) : les deux routes de la zone 1

**Route trork**

1. Nouveau monde : le village kweebec se pose (15 s), puis le camp trork (40 s), avec deux lignes « posé » dans le
   journal du serveur. Sinon, s'éloigner et lancer `/village generer trork`. `/village liste` donne les deux lieux.
2. Approcher du camp : les gardes trorks attaquent (Honni, -250). `/village reputation` le confirme.
3. Jeter de la viande crue (`/give Food_Wildmeat_Raw 16`, la touche de lâcher) vers un Trork, puis reculer. Quand il la
   mange, une notification donne +15 par morceau. Arrivé à Toléré, les Trorks du camp saluent au lieu d'attaquer.
   Autre moyen : parler au crieur ou au chef avec 5 viandes.
4. Tableau du camp : prendre « Viande pour le feu » et vérifier que le titre tient dans le suivi.
5. Chaîne : `/village rep 60` au camp, puis le chef avec 10 viandes (étape 1). Une notification annonce la chute d'un
   rang chez les Kweebecs. `/village rep 250` : les loups, puis les Mosshorns ; `/village rep 600` : le clan rival ;
   `/village rep 1000` : la Peinture de guerre.
6. Peinture : clic secondaire avec le pot. La teinte et l'icône apparaissent. Loin du camp, un Trork sauvage croisé
   en chemin ne doit plus attaquer. Au village kweebec, `/village reputation` montre un
   rang de moins.

**Route kweebec**

1. Remplir une demande kweebec : la notification « -N auprès des Trorks » s'affiche.
2. `/village chaineetape 1` puis une étape réelle de la chaîne kweebec : le rang trork descend d'un cran.

**Klops**

1. `/village klops` dit où il est aujourd'hui. Y aller (ou `/time` au lendemain) : le Klops errant se tient à l'ouest du
   cœur.
2. Lui parler : troc, colis (message avec village, distance, direction), tournée.
3. Porter le colis jusqu'au cœur de l'autre lieu : « Colis livré », 3 rouages, +30 de réputation.

### À vérifier en jeu (étape 7)

- Que les Trorks vanilla mangent bien la viande jetée près d'un joueur hostile, ou qu'il faille s'éloigner, et que le
  ramassage par le Trork retire bien l'objet (la viande est comptée à sa disparition, avec un Trork à moins de 4 blocs).
- Que les Trorks vanilla postés au camp (laisse déplacée par le Java) restent près de leur poste, et qu'ils dorment la
  nuit sans quitter le camp.
- Que l'attitude neutre donne bien le salut (Reputation_Switch) et que l'amical les rend indifférents.
- L'allure des prefabs `Npc/Trork` côte à côte, et la bannière de crânes (marqueur de carte).
- La teinte de la Peinture de guerre (EntityTopTint/BottomTint sur un joueur) et son icône (potion vanilla).
- L'allure en main de la Dent de trophée, du Rouage klops (tas de ferraille) et du colis (rouleau de lin).
- Que le Klops répond (rôle Generic interactif) et que l'effet `KlopsParcel` donne bien le colis.

## Étape 8 : les Feran (zone 2) et les Renoncés (zone 3)

Page à part : [zones-2-3.md](zones-2-3.md). Elle couvre les deux nouveaux peuples, la soif, le froid, la ruche
scarak, la pose automatique des villages dans leur zone, les nouvelles commandes et les tests en jeu.

## Étape 9 : les Slothians (zone 4), le Vide et l'avant-poste du champion

Page à part : [zone-4.md](zone-4.md). Elle couvre le monastère slothian, la corruption du Vide, les raids du Vide,
l'avant-poste du champion (Pierre de fondation), les nouvelles commandes et les tests en jeu. Le wiki joueur a un
onglet **Peuples** (`docs/wiki/peuples/`).

## PNJ tués : retour au matin (`village/Absences`)

Un PNJ du village tué (crieur, marchand, chef, ou villageois d'un métier ouvert) revient au matin suivant, à 6 h de jeu,
quand un joueur passe près du village. Pour que les joueurs le sachent :
- le tableau du village (page à boutons et version texte) liste les absents sous « Absents, de retour à 6 h (dans N h) »,
  avec leur nom et leur métier ;
- en ouvrant leur dialogue, les autres PNJ du village en parlent dans la voix de leur peuple (ligne `#Aside` de la
  fenêtre de dialogue, ou une ligne du tchat). Au-delà de trois absents, la réplique dit « A, B et N autres ».

Les aides du chantier ne sont pas listées : ils ne reviennent qu'au prochain chantier. Un métier fermé (bâtiment brûlé)
non plus.

Tester en jeu : tuer le crieur, ouvrir le tableau puis parler au marchand ; dormir jusqu'au matin : le crieur revient et
la ligne disparaît.

## Apparitions sûres et guetteur qui reste

**Point sûr** (`Terrain.safeFeet` / `Terrain.safeSpot`) : toutes les apparitions de PNJ du mod passent par la même
recherche. Un point est sûr s'il réunit ces conditions :
- un sol naturel existe (pas de vide) ;
- il n'y a ni eau ni lave sur le sol ou à hauteur du corps ;
- deux blocs sont libres au-dessus (herbes et fleurs permises) ;
- au moins trois voisins sont à un bloc près (pas de pente impraticable).

La recherche part du point voulu et s'élargit par anneaux. Elle sert à :
- **Demandes et chaîne** : le lieu tiré est déplacé une fois au point sûr le plus proche, à 24 blocs au plus, puis 48.
  Le guetteur, le captif et le bosquet s'y posent. La bande de chasse et les gardiens se posent sur des points sûrs
  autour. Un lieu déjà fixé par une ancienne sauvegarde est revu une fois par session.
- **Raids** : chaque camp est à 8 blocs au plus de l'angle tiré. Les assaillants et les gardes sont posés sur des
  points sûrs.
- **Klops** : à 6 blocs au plus de son étape.
- **Villageois** : un poste sous l'eau ou dans la lave est décalé de 3 blocs au plus. Un poste dans un bâtiment reste
  où il est.

**Guetteur des missives** : il ne disparaît plus à la remise. Il reste à son poste (« Il reprend sa garde ») et part
quand aucun joueur n'est à moins de 56 blocs (`RequestSpawns.release` / `stepLingering`).

## Bâtiments de métier, étape 1 : panneau de commandes et savoir-faire (`workshop/`)

GDD des bâtiments de métier (approuvé le 15 novembre 2026) : chaque bâtiment du plan dont le villageois à métier
produit quelque chose a son niveau (I à III), sa jauge de savoir-faire et son propre panneau de commandes. L'étape 1
pose l'état, le panneau, les commandes et la jauge ; la montée de niveau (commande de maître, chantier de 12 h) vient
à l'étape 2.

- **Bâtiments** : asset `Server/Nakasar/Workshops/<Peuple>_<Bâtiment>.json` (plan, bâtiment, métier, icône, place du
  panneau), généré par `tools/generate_workshops.py` à partir des plans. 15 bâtiments : Kweebecs (enclos, potager,
  puits, maison de soins, tour de la garde), Trorks (piège, feu de camp, entrepôt), Feran (entrée de l'oasis, hutte de
  la garde), Renoncés (maison du chasseur, tour du fort), Slothians (étal des cendres, temple de veille, porte du
  monastère). Un bâtiment est ouvert quand son bâtiment est debout et que son métier existe au palier du village.
- **État** : `village/WorkshopState`, sauvegardé avec le village (`Workshops` du village) : niveau, savoir-faire,
  spécialité, commandes du jour, place du panneau.
- **Panneau** : le panneau vanilla du peuple (même bloc que le tableau du village), posé par le Java devant le bâtiment
  à la place calculée par le générateur (face tournée vers la place, décalée de l'entrée), seulement sur une case vide
  ou de végétation. L'utiliser ouvre `WorkshopPage_<Peuple>.ui` (`tools/generate_workshop_ui.py`) ; accroupi, la
  version texte.
- **Commandes** : modèles de demande ordinaires rangés dans `Server/Nakasar/Requests/<Peuple>/<Bâtiment>/`, avec
  `Workshop`, `MinLevel`, `MaxLevel`, `Knowledge` (et `Specialty` pour l'étape 3). Le tableau du village ne les tire
  plus ; chaque bâtiment en tire 2 à 6 h (3 au niveau III). Rang Toléré pour en prendre une ; un joueur suit au plus 3
  demandes ou commandes à la fois (hors étapes de chaîne). Remplie : savoir-faire au bâtiment (borné à la jauge du
  niveau : 200 au niveau I, 400 au niveau II), 5 d'essor au village, faveurs et réputation au joueur, une fois par
  commande comme l'essor.
- **Validation** : `ValidateAssets` vérifie les bâtiments (plan, bâtiment, métier, au moins 3 commandes), le
  `Workshop` des commandes et les ids remplis par `WorkshopPage.java` dans chaque mise en page.

### Nouvelles commandes

- `/village atelier` : bâtiments de métier ouverts du village le plus proche ; `/village atelier <id>` ouvre la page.
- `/village savoirfaire <id> <quantité>` (ops) : ajoute du savoir-faire.

### Tester en jeu (étape 1)

1. `/village generer` puis `/village palier 1` (le village kweebec gagne puits et enclos).
2. Attendre une seconde près des bâtiments : un panneau kweebec apparaît devant le potager, le puits et l'enclos.
3. L'utiliser : la page montre l'enclos des lapins, niveau I, son éleveur, la jauge 0/200 et 2 commandes.
4. Prendre « Carottes des lapins », déposer 10 carottes au dépôt : +30 de savoir-faire, +5 d'essor, une nouvelle commande.
5. Accroupi devant le panneau : la version texte.

### À vérifier en jeu (étape 1)

- Le panneau est-il bien tourné vers la place et hors du passage ? Ne bouche-t-il aucune entrée ?
- Le panneau d'un bâtiment bâti par un chantier apparaît-il dans la seconde où un joueur est près ?

## Bâtiments de métier, étape 2 : niveaux II et III

- Quand la jauge est pleine (200 au niveau I, 400 au niveau II) et que le village a le palier voulu (village pour le
  niveau II, bourg pour le III), le panneau propose la **commande de maître** du niveau (`<Bâtiment>_Master_<niveau>`,
  `Master: true`, hors tirage du jour). Elle n'expire pas, ne compte pas dans les 3 suivies et ne se remplit qu'une
  fois pour le village (id `master-<village>-<bâtiment>-<niveau>-<reconversion>`).
- Ensuite **« Lancer le chantier »** (rang Toléré) prend au dépôt les matériaux de l'asset (`Upgrades`, la moitié des
  3 premiers matériaux du chantier du palier correspondant du plan) et lance 12 h de travaux (heures de jeu).
- À la fin : niveau suivant, jauge à zéro, commandes retirées (3 au niveau III), décor vanilla du peuple posé à côté du
  panneau (`Decor`, seulement dans l'air au-dessus d'un bloc), annonce et titre à l'écran aux joueurs proches.
- Pas encore de variante de prefab plus grande : le décor suffit tant que les emprises de niveau III ne sont pas
  réservées dans les plans (à voir avec les emplacements de l'étape 6).

## Bâtiments de métier, étape 3 : spécialités et élevage

- **Spécialités** (`Specialties` de l'asset `Workshop`, `tools/generate_workshops.py`) : 3 par enclos, 2 pour les autres
  bâtiments de métier. Au niveau II, le bouton **« Choisir la spécialité »** du bandeau ouvre `WorkshopSpecialtyPage`
  (une carte par spécialité, mise en page par peuple). Rang **Ami** (réponse de Kevin, au lieu d'Hôte), pour tout le
  village, annoncé aux joueurs proches. Changer ensuite est une **reconversion** : une fois tous les 7 jours de jeu, le
  savoir-faire du niveau retombe à 0 et la commande de maître est à refaire (nouvel id) ; impossible pendant les travaux.
- **Enclos des quatre autres peuples** au palier 1, prefabs du mod en blocs vanilla seulement
  (`Server/Prefabs/Nakasar/Peuples/Pens/<Peuple>_Pen`, `tools/generate_pens.py`, 13 × 13, clôture du bois du peuple,
  barrière tournée vers la place, auge et foin) : fosse aux bêtes trork (-32, 14), enclos de l'oasis feran (-13, -20),
  bergerie du givre renoncée (-19, -15), bauge de veille slothiane (40, -13). Chacun a son villageois : dresseur trork
  (rôle vanilla `Trork_Hunter`), éleveuse feran, berger renoncé, gardien de la bauge slothian (rôles et dialogues du mod).
  `generate_village_layouts.load_bounds` lit les emprises des prefabs du mod ; `ValidateAssets` les accepte.
- **Bêtes** (`workshop/Livestock`) : 3, 5 puis 7 selon le niveau, celles de base puis celles de la spécialité au niveau
  II, posées comme les villageois (joueur à moins de 72 blocs, non sauvegardées, point sûr de l'intérieur de l'enclos,
  attachées à son centre). Rôles vanilla `Tamed_*` d'abord ; sinon rôles du mod sur le modèle vanilla
  (`Nakasar_Peuples_Pen_{Wolf_Trork,Wolf_White,Tortoise,Archaeopteryx,Trillodon,Snail_Magma}`, Generic, flânent et
  n'attaquent jamais). **Aucun butin** : le rôle est marqué « butin déjà lâché » dès l'apparition (le système vanilla
  `NPCDamageSystems.DropDeathItems` saute alors la liste de butin). Pas de régénération (`VillageNoRegenSystem`, 96
  blocs). Tuée, une bête manque jusqu'au matin ; tuée par un joueur, **-5 de réputation** de village
  (`LivestockDeathSystem`).

### Nouvelles commandes

- `/village niveauatelier <bâtiment> <niveau>` (admin, test) : met le bâtiment au niveau voulu, savoir-faire à 0,
  reconversion libre (la spécialité est oubliée sous le niveau II).

### Tester en jeu (étape 3)

1. Près d'un village kweebec au palier 1 ou plus : trois lapins dans l'enclos (`Tamed_Bunny`, `Tamed_Rabbit`, en plus
   des lapins des marqueurs du prefab vanilla).
2. `/village niveauatelier Kweebec_Enclos 2`, puis le panneau de l'enclos : bouton « Choisir la spécialité ». Avec le
   rang Ami (`/village reputation` au besoin), choisir « Bergerie » : annonce, les lapins partent, cinq moutons arrivent.
3. Rouvrir le choix : les autres cartes disent « encore 7 jour(s) ». `/village niveauatelier Kweebec_Enclos 2` remet la
   reconversion libre.
4. Tuer une bête : aucun objet au sol, message de réputation (-5), elle revient le lendemain matin.
5. Camp trork, oasis feran, hameau renoncé, monastère slothian au palier 1 : l'enclos est collé avec le chantier, le
   villageois s'y poste, les bêtes de base apparaissent.

### À vérifier en jeu (étape 3)

- Rotation des clôtures, des coins et de la barrière des prefabs d'enclos (relevées dans le prefab vanilla
  `Kweebec_Oak_Bunny_Area_003`) ; la barrière doit faire face à la place.
- Animations des rôles du mod (loups, tortue, trillodon, archéoptéryx au sol, escargot de magme).
- Les moutons restent tondables (récolte vanilla des `Tamed_Sheep`) : à couper si c'est une source gratuite de laine.

## Bâtiments de métier, étape 4 : boutiques et Part de l'Hôte

- **Une boutique par bâtiment, spécialité et niveau** : boutiques de troc vanilla
  `Server/BarterShops/Nakasar_Peuples_W_<Bâtiment>_<Base|Spécialité>_<Niveau>.json`, payées en faveurs du peuple,
  stock renouvelé tous les 3 jours à 6 h (comme le marchand vanilla). Le niveau I (et un bâtiment sans spécialité) vend
  la « Base » ; aux niveaux II et III la boutique de la spécialité reprend la base et ajoute ses échanges. Données :
  `SHOPS` dans `tools/generate_workshops.py` (objets vanilla seulement, vérifiés contre `vanilla-item-ids-0.7.2.txt`).
- **Le rang choisit le niveau vu** : Toléré I, Ami II, Hôte III, jamais plus que le niveau du bâtiment
  (`Workshops.shopLevel`). Bouton « Boutique (niveau N) » sur la carte des offres du panneau ; fermée si le villageois
  du bâtiment est absent (il revient au matin) ou si le bâtiment est détruit (le panneau n'ouvre plus).
- **Part de l'Hôte** (Kevin : niveau III seulement) : chaque matin, le bâtiment dépose un petit lot de sa production
  (le premier échange du niveau II de sa spécialité) pour chaque joueur de rang Hôte : bouton « Prendre la Part de
  l'Hôte », un lot par joueur et par jour de jeu (`WorkshopState.ShareDay/ShareTaken`). Le lot tombe aux pieds si
  l'inventaire est plein. C'est une caisse virtuelle : pas de coffre ouvert à tous.
- `ValidateAssets` vérifie que chaque bâtiment a sa boutique du niveau I, chaque spécialité ses boutiques II et III et
  son lot.

### Tester en jeu (étape 4)

1. Panneau d'un bâtiment au rang Toléré : la carte des offres dit « niveau I », le bouton ouvre la boutique de troc.
2. `/village niveauatelier Kweebec_Potager 3`, choisir « Verger », passer Ami : la boutique montre les baies (niveau
   II) ; passer Hôte : tartes et salades (niveau III), et le bouton « Prendre la Part de l'Hôte » (6 baies rouges).
   Le reprendre : refusé jusqu'au matin.
3. La nuit, quand le villageois est rentré : la carte dit qu'il est absent, pas de bouton Boutique.

### À vérifier en jeu (étape 4)

- La page vanilla de troc affiche bien le titre traduit (`nakasar_peuples.barter.W_*.title`).
- Prix et quantités : à équilibrer après quelques soirées de jeu.

## Bâtiments de métier, étape 5 : spécialités de garde en raid

Un bâtiment de garde ouvert, au niveau II ou plus, renforce les raids selon sa spécialité (`RAID` dans
`tools/generate_workshops.py`, champ `Raid` de la spécialité, lu par `Workshops.raidBonus` au début du raid) :

| Bâtiment | Spécialité | En raid |
|---|---|---|
| Tour de la garde (Kweebec) | Archers | 2 gardes de plus postés à la tour |
| Tour de la garde (Kweebec) | Vigiles | +1 garde au cœur, PV des gardes × 1,25 |
| Hutte de la garde (Feran) | Lanciers | PV des gardes × 1,35 |
| Hutte de la garde (Feran) | Coureurs | +1 garde au cœur |
| Tour du fort (Renoncés) | Arbalétriers | 2 gardes de plus postés à la tour |
| Tour du fort (Renoncés) | Gardes du givre | +1 garde au cœur, PV des gardes × 1,25 |
| Porte du monastère (Slothians) | Lances | PV des gardes × 1,5 |
| Porte du monastère (Slothians) | Veilleurs | +1 garde au cœur |

Au niveau III, les gardes de plus (au cœur ou postés) prennent +1. Les PV sont un modificateur du maximum posé au
premier pas du raid, gardes pleins de vie à ce moment-là ; aucun soin ensuite (règle n° 1). Les Trorks ne subissant
pas de raid, la Fosse de combat n'a pas d'effet en raid (sa ligne ne le promet plus).

### Tester en jeu (étape 5)

1. `/village niveauatelier Kweebec_Tour_Est 2`, choisir « Archers », puis `/time midnight` et `/village raidprevoir` : le journal dit 2 gardes de plus, deux gardes apparaissent à la tour.
2. Reconvertir en « Vigiles » (`/village niveauatelier Kweebec_Tour_Est 2` libère la reconversion), relancer : un garde
   de plus au cœur, barre de vie plus longue.

### À vérifier en jeu (étape 5)

- Les gardes postés à la tour : point sûr au centre de son emprise, ils peuvent apparaître sur le toit ; à déplacer
  devant la porte si c'est gênant.

## Bâtiments de métier, étape 6 : emplacements libres E1 et E2

Chaque plan de village réserve deux terrains de 24 × 24 blocs (`tools/plots.py`, champ `Plots` du plan). Kevin :
E1 s'ouvre au palier 2, E2 au palier 3 ; des piquets (barrière vanilla du peuple aux quatre coins et un écriteau de
chantier) marquent le terrain un palier plus tôt. Les plans ont grandi pour les loger :

| Plan | E1 (palier 2) | E2 (palier 3) | Rayon |
|---|---|---|---|
| Kweebec_Oak | 28, -37 | -22, -42 | 65 |
| Trork_Camp | 20, -37 | 7, 45 | 59 |
| Feran_Oasis | -2, 40 | 55, 0 | 68 |
| Renonce_Givre | 28, -30 | -39, 13 | 60 |
| Slothian_Monastere | 0, 51 | 48, 19 | 67 |

Le bouton **Emplacements** du panneau du village ouvre la page `PlotPage` (`village/PlotPage.java`, mise en page par
peuple générée par `tools/generate_workshop_ui.py`) : les deux terrains, puis le catalogue des 5 projets du peuple
pour le terrain sélectionné. Toute la logique est dans `village/Plots.java`, l'état est sauvegardé avec le village
(`PlotState` : projet, chantier, dernière démolition, piquets).

- **Choisir** (rang Ami) : un projet par terrain, changeable sans frais tant que le chantier n'est pas lancé. Un projet
  ne peut être que sur un terrain, sauf le deuxième élevage.
- **Lancer le chantier** (rang Ami) : les 3 matériaux du terrain sont pris au dépôt du village (`MATERIALS`), le
  terrain est aplani, l'échafaudage du peuple monte en 4 phases pendant 24 h de jeu, puis le prefab vanilla est collé
  et le villageois du projet arrive. C'est alors un bâtiment de métier complet : panneau, niveaux I à III, deux
  spécialités, boutiques, Part de l'Hôte.
- **Démolir** (rang Ami) : retire les blocs au-dessus du sol de l'emprise (sauf les coffres et autres conteneurs),
  rend un quart des matériaux au dépôt, et le bâtiment repart au niveau I. Une démolition tous les 7 jours de jeu
  par terrain.

Un projet est modélisé par deux bâtiments du plan (`E1_<Projet>`, `E2_<Projet>`, champ `Plot`) et deux métiers
(`<Métier>_E1`, `<Métier>_E2`). Les chantiers de palier ne les collent jamais, sauf pour rebâtir leurs ruines après un
raid perdu. `tools/generate_workshops.py` en fait 50 bâtiments de métier `<Peuple>_<E1|E2>_<Projet>`.

| Peuple | Projets |
|---|---|
| Kweebec | Atelier d'archerie, Herboristerie, Grand bassin, Menuiserie, Deuxième enclos |
| Trork | Forge de guerre, Camp des bûcherons, Carrière, Tannerie, Deuxième fosse |
| Feran | Caravansérail, Tissage, Citerne, Volerie des plumes, Deuxième enclos |
| Renoncés | Forge, Fumoir, Cabane de pêche, Chenil (Loups de garde : +1 garde en raid), Deuxième bergerie |
| Slothians | Scriptorium, Cabane de pêche, Sanctuaire, Puits de basalte, Deuxième bauge |

Le deuxième élevage reprend les commandes, les bêtes, les spécialités et les boutiques de l'enclos de base (champ
`Twin` du bâtiment de métier). Deux élevages du même genre ne peuvent pas avoir la même spécialité
(`Workshops.twinWith`, ligne d'état sur la page des spécialités).

Les villageois des projets réutilisent les rôles et les dialogues du peuple (garde, soigneuse, puisatière, marchand,
guetteur…) : noms et répliques peuvent donc se répéter avec ceux du village. Les prefabs viennent tous du jeu (règle
n° 2), sauf les enclos du mod (`Nakasar/Peuples/Pens/`). Le Sanctuaire slothian prend le petit temple
`Slothian_Disabled_Temple_Medium_001` : le temple prévu (`Temple_003`, 8 × 23) ne tient pas dans le terrain.

### Tester en jeu (étape 6)

1. `/village palier 1` : les piquets d'E1 apparaissent. `/village palier 2` : E1 s'ouvre, les piquets d'E2 apparaissent.
2. `/village rep 220` (rang Ami), puis panneau du village, **Emplacements**, terrain E1 : choisir un projet,
   le changer, y renoncer.
3. Déposer les matériaux affichés dans le coffre du dépôt, **Lancer le chantier** : les piquets partent, l'échafaudage
   monte. `/village finir` finit le chantier d'emplacement au pas suivant : le bâtiment est collé, son villageois
   arrive, son panneau de métier est posé.
4. Sur E2 (`/village palier 3`), le même projet est refusé (« déjà sur l'autre terrain »), sauf le deuxième élevage.
5. **Démolir** : le bâtiment disparaît, un quart des matériaux revient au dépôt ; une deuxième démolition est refusée
   pendant 7 jours.

### À vérifier en jeu (étape 6)

- La démolition enlève tout ce qui dépasse du sol dans l'emprise, pas seulement les blocs du prefab : un bloc posé par
  un joueur sur le bâtiment part avec lui (les conteneurs restent).
- Les piquets sur un sol en pente ou dans l'eau, l'écriteau de chantier (orientation).
- Le panneau de métier des projets : posé dans le terrain, hors de l'emprise du prefab.
