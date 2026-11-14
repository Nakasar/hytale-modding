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
