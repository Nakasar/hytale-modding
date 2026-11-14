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
