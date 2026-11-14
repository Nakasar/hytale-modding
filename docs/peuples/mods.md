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

La **fenêtre** (`dialogue/DialoguePage`, maquette `images/dialogue.png`) est une `InteractiveCustomUIPage` sur la mise
en page du pack `Common/UI/Custom/Pages/Nakasar/Peuples/DialoguePage.ui` : `#NpcName`, `#Line`, `#Answer0..3` avec leur
ligne `#Hint0..3`, et `#Leave`. Ce premier jet est écrit sans fichier .ui vanilla sous les yeux (syntaxe de la
documentation communautaire), sans import de `Common.ui` ni fond, pour limiter ce qu'il faut confirmer en jeu. Le
**secours** est le même dialogue mené dans le tchat (`/village tchat`, `/village repondre`), qui ne dépend d'aucune page.

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
| 0, campement | deux abris, tour de guet, potager, deux lanternes, deux bancs |
| 1, hameau | puits, échoppe, une maison, enclos des lapins |
| 2, village | grande maison, maison des gardes, deuxième tour, deuxième échoppe |
| 3, bourg | le Grand-Père, grand potager |

Les prefabs vanilla gardent leurs marqueurs d'apparition : des Kweebecs (villageois, marchand, patrouilles de
Razorleaf et de Sproutlings, lapins) apparaissent dans le campement.

### Génération

`VillageBuilder` charge les chunks, aplanit la place (chemin de terre) et l'emprise de chaque bâtiment (herbe, 2 blocs
de marge plate, fondu de 4 blocs vers le relief, arbres abattus), à au plus 4 blocs de la hauteur de la place, puis colle
les prefabs comme l'action vanilla `PrefabPasteAction`, et pose cœur, dépôt, tableau (étape 1) et bannière.

`VillageSeeder` pose tout seul **le premier village kweebec du monde par défaut** : 15 s après le démarrage, il essaie
40 sites sur des cercles de 280 à 700 blocs autour du point d'apparition (ordre tiré du seed), et prend le premier
couvert d'herbe à 80 %, sans eau, avec au plus 9 blocs de relief. Le monde garde la trace du village posé ; si aucun
site ne convient, il réessaie au démarrage suivant avec d'autres sites. Les noms viennent de `VillageNames` (liste
kweebec, sans doublon dans le monde).

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

- **Le tableau** (ouest du cœur) : utilisé normalement, il ouvre le tableau à boutons (`BoardPage.ui`, sur les modèles
  vanilla de `Common.ui`, maquette `tableau_village.png`) : les trois demandes avec **Prendre** / **Abandonner** à
  gauche, l'état du village et **Rendre** à droite, **Version texte** pour la page BlockLore. **Accroupi**, il ouvre
  directement la page texte (secours si la page à boutons ne s'affiche pas).
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
- Le tableau à boutons `BoardPage.ui` : mise en page, boutons (Prendre, Abandonner, Rendre, Version texte), défilement
  de l'état à droite ; chemin `../../../Common.ui`.
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
matériaux du palier, un chantier s'ouvre. Des échafaudages montent autour des bâtiments du palier suivant, des
bâtisseurs y travaillent, puis le prefab vanilla est collé au bout de la durée du chantier.

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
  de ses ruines. Les grands bâtiments reçoivent un échafaudage en blocs vanilla : poteaux `Wood_Hardwood_Beam` tous les
  4 blocs, à 1 bloc du bâtiment, planchers `Wood_Hardwood_Planks_Half` tous les 5 niveaux (18 blocs de haut au plus)
  et un tas de `Wood_Oak_Trunk` au centre. Il n'existe pas de bloc « échafaudage » vanilla.
- Une parcelle où un joueur a construit n'est jamais touchée. Le bâtiment est sauté et le tableau le dit.

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
- Toutes les parcelles sont examinées avant de poser le moindre échafaudage, pour que l'échafaudage d'un bâtiment ne
  fasse pas sauter son voisin.
- À la fin, l'échafaudage est retiré et le prefab collé. Le palier monte, la jauge repart à 0, et un titre s'affiche à
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
   En moins de 2 s, les matériaux disparaissent du coffre, les parcelles sont aplanies et les échafaudages montent.
   Le bâtisseur et ses aides y vont. `/village chantier` donne les heures restantes.
3. Attendre 24 h de jeu (`/time` pour avancer), ou `/village finir` : les échafaudages tombent, le puits, l'échoppe,
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
- L'allure des échafaudages, et que leur retrait ne laisse rien derrière.
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
