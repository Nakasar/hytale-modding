# Peuples d'Orbis, étape 9 : les Slothians (zone 4), le Vide et l'avant-poste du champion

Dernière étape du plan d'implémentation du GDD (https://claude.ai/artifact/FJ15VjWp3pgnt9kmRWjfV7) : le cinquième peuple,
son climat, la récompense des champions et l'onglet **Peuples** du wiki joueur. Construite sur l'étape 8 (PR #118).

| | Slothians |
|---|---|
| Zone | 4 (terres brûlées, `Zone4_Tier*`) |
| Id du peuple | `Slothian` |
| Plan de village | `Slothian_Monastere` (rayon 59), prefabs vanilla `Npc/Slothian/Disabled/…` et monuments `Monuments/Incidental/Slothian/Land/…` |
| Sol | boue sèche, place en pavés de basalte ; site sur herbe brûlée, terre brûlée, cendre, sable cendré, boue sèche |
| Dépôt, tableau, bannière | coffre de jungle vanilla, panneau du temple d'émeraude (`Furniture_Temple_Emerald_Sign`), brasero de jungle |
| Climat | corruption du Vide |
| Raids | Vide (`Nakasar_Peuples_Raid_Slothian`, « Montée du Vide ») |
| Trophée de raid | `Nakasar_Peuples_Trophy_Void` |
| Faveur | `Nakasar_Peuples_Favor_Slothian`, Cendre bénie (modèle des gravats de charbon) |
| Fin de chaîne | `Nakasar_Peuples_Vigil`, Veille des Slothians (modèle du cœur du Vide) |

Tout le contenu est généré par `mods/nakasar-peuples/tools/generate_slothians.py`, qui réutilise les briques de
`generate_zones.py` (rôles de service et de métier, raids, dialogues, demandes, échoppes, langues). Les langues forment
un bloc « étape 9 » en tête des deux fichiers `nakasar_peuples.lang` (contrôle des doublons et des titres de 24
caractères, comme à l'étape 8).

    cd mods/nakasar-peuples
    python3 tools/generate_slothians.py --preview /chemin/apercus   # plan PNG du monastère en option

## Les rôles, écrits depuis les modèles vanilla

Le rôle vanilla `Slothian` n'est qu'un squelette abstrait : tous les rôles du peuple sont écrits par le mod sur les
modèles vanilla `Slothian_{Villager,Scout,Monk,Elder,Warrior}` (parent « Player », donc les animations du squelette
joueur : `Crouch`, `Sit`, `SitGround`, `IdlePassive`…).

| Rôle | Modèle | Poste |
|---|---|---|
| Crieur, marchand, bâtisseur, porteur de cendres | Slothian_Villager | tableau, dépôt, chantier, étal des cendres |
| Guetteur (missive), guetteur de métier | Slothian_Scout | au loin, l'affût |
| Moine égaré (captif), moine, Abbé (chef) | Slothian_Monk | escorte, temple de veille, est de la place |
| Doyenne | Slothian_Elder | monastère (palier 3) |
| Garde, gardien de raid | Slothian_Warrior, hache tribale vanilla | porte, autour du cœur |

Le gardien de raid frappe avec les coups de hache des Outlanders (même squelette). Pas de portrait de dialogue :
Assets.zip n'a pas de rendu `ModelsGenerated` des Slothians.

## Les Slothians s'ouvrent par leurs amis

Recommandation du GDD : les Slothians commencent **Étranger** et se « débloquent » par les peuples amis.
- `People.ally()` : Feran et Renoncés ont pour allié les Slothians. Chaque gain de réputation de village chez eux donne
  un quart (`Rivals.ALLY_SHARE`) à la réputation de peuple slothiane, avec une notification.
- Le Manteau du givre (porté ou dans le sac) révèle la position du monastère, comme le bracelet révèle les Renoncés.

## Corruption du Vide (zone 4)

En zone 4, loin d'un brasero ou d'un feu de camp allumé (5 blocs, la lave ne compte pas) et à plus de 48 blocs du cœur
du monastère, une pile de `Nakasar_Peuples_Void_<1..5>` toutes les 8 s (10 piles, une icône par paire). À l'abri
(effet `Nakasar_Peuples_Sanctuary`), une pile de moins toutes les 1,2 s. Chaque pile retire 0,15 % des PV max par
seconde (cause `Nakasar_Peuples_Void`). La **Robe du moine** (`Nakasar_Peuples_Monk_Robe`, parent plastron
Cindercloth vanilla, échoppe Ami) portée ou la **Veille** dans l'inventaire l'annulent.

## Demandes, chaîne, échoppes

- **Tableau** : 10 modèles (cendres, roche volcanique, essences du Vide, champignons, cierges ; chasse aux rampants et
  larves, chasse aux cristaux d'anomalie ; missive ; escorte du pèlerin ; défense de nuit). Rôles vanilla cités :
  `Crawler_Void`, `Larva_Void`, `Void_Anomaly_Crystal_Small`, `Skeleton_Burnt_Soldier` (ajoutés à
  `tools/vanilla-refs-0.7.2.txt`, vus dans Assets.zip 0.7.7).
- **Chaîne de l'Abbé** : 16 Cendres (Toléré, +80) → 3 cristaux d'anomalie (Ami, +120) → le moine perdu (Ami, +150) →
  tenir la faille, défense qui exige le **temple de veille** (condition Building, Hôte, +200) → la Veille (Champion,
  drapeau `Slothian_Chain_5`). Avec la Veille, le titre d'entrée de village ajoute « Veilleur du Vide ».
- **Échoppes** Toléré / Ami / Hôte : brasero et cierges de jungle, robe du moine, armes tribales vanilla, essences.

## Raids du Vide

| Rôle | Apparence, arme | PV | Dégâts | Butin |
|---|---|---|---|---|
| `Nakasar_Peuples_Raider_Void_Larva` | Larva_Void | 21 | 8 | `Empty` |
| `Nakasar_Peuples_Raider_Void_Crawler` | Crawler_Void | 70 | 16 | `Drop_Crawler_Void` |
| `Nakasar_Peuples_Raider_Void_Skeleton_Soldier` | Skeleton_Burnt_Soldier, épée rouillée | 124 | 22 | `Drop_Skeleton_Burnt_Soldier` |
| `Nakasar_Peuples_Raider_Void_Skeleton_Knight` | Skeleton_Burnt_Knight, épée rouillée | 160 | 26 | `Drop_Skeleton_Burnt_Knight` |

Attaques vanilla de chaque modèle ; cri d'annonce `SFX_Crawler_Void_Alerted`. `Raids.preys` : le Vide vise les rôles
`*Slothian*`.

## L'avant-poste du champion (`outpost/`)

- `Outposts.step` (toutes les 5 s, `ZoneSystem`) : un joueur Champion d'un peuple reçoit une fois une **Pierre de
  fondation** (`Nakasar_Peuples_Foundation_Stone`, drapeau `Foundation_<peuple>`).
- Clic secondaire avec la pierre (`Nakasar_Peuples_ZoneItem`, action `Foundation`) : `OutpostPage.ui` (maquette
  `avant_poste.png`) liste les cinq avant-postes avec leur condition (Champion du peuple ; pour les Trorks, la Peinture
  de guerre suffit). « Choisir » puis « Fonder l'avant-poste » : écart aux villages et aux autres fondations vérifié
  (`VillageBuilder.spacing`), pierre prise, fondation sauvegardée dans la ressource `Nakasar_Peuples_Zones` (champ
  `Outposts`).
- Au premier matin d'un jour suivant (6 h), le plan du peuple est bâti au palier 0 sous un nom de `VillageNames` :
  c'est un village ordinaire (demandes, chantiers, raids). Échec : la pierre est rendue (au retour du joueur s'il est
  absent). Une seule fondation en attente par joueur.

## Nouvelles commandes

| Commande | Accès | Effet |
|---|---|---|
| `/village generer slothian` | admin | pose un monastère slothian devant soi |
| `/village semer slothian` | admin | relance la pose automatique dans la zone 4 (recherche jusqu'à 12 000 blocs) |
| `/village climat vide` | admin | force la corruption du Vide sur soi, quelle que soit la zone |
| `/village avantposte liste` | admin | liste les avant-postes du monde (en attente ou bâtis) |
| `/village avantposte pierre` | admin | donne une Pierre de fondation |
| `/village avantposte finir` | admin | fait arriver tout de suite les colons des fondations en attente |

## Tester en jeu

1. **Monastère.** `/village generer slothian` sur un terrain plat, puis `/village palier 3` : les 12 bâtiments, la
   bannière-brasero, le dépôt et le tableau. Parler au chef : `/village tchat Slothian_Chef`.
2. **Pose automatique.** Monde neuf, une minute, puis `/village liste` (ou `/village semer slothian`) ; journal :
   `Nakasar Peuples : zone 4 … trouvée`.
3. **Alliés.** Près de l'oasis feran, remplir une demande : notification « +N auprès des Slothians ».
4. **Vide.** `/village climat vide` dehors : piles de corruption (icônes Void), qui redescendent près d'un brasero ou
   d'un feu de camp allumé (icône Sanctuaire). `/give Nakasar_Peuples_Monk_Robe`, l'équiper : plus de corruption.
5. **Chaîne.** `/village rep 1000` puis `/village chaineetape 1` à `5` près de l'Abbé ; l'étape 4 demande le temple de
   veille (`/village palier 2`). Avec `Nakasar_Peuples_Vigil` dans le sac, entrer dans un village : « Veilleur du Vide ».
6. **Raid.** Près du monastère, la nuit : `/village raidlancer` : larves, rampants et squelettes brûlés attaquent.
7. **Avant-poste.** `/village reppeuple 1000` près d'un village (Champion du peuple) : la pierre arrive en quelques
   secondes. Aller à plus de 150 blocs de tout village, clic secondaire avec la pierre, choisir, Fonder ; puis
   `/village avantposte finir` (ou dormir jusqu'au matin) : le campement apparaît. `/village avantposte liste`.
8. **Titres.** `/village demande Slothian_Hunt_Crystals 1`, etc. : les titres tiennent dans le suivi.

## À vérifier en jeu

- Le plan `Slothian_Monastere` : orientation des monuments (étal, affût, temple), entrées, temple au palier 2.
- Les animations `Crouch` / `Sit` / `SitGround` sur les modèles slothians, la hache du gardien.
- La fenêtre de l'avant-poste : mise en page, couleurs des conditions, boutons « Choisir ».
- Les cristaux d'anomalie (ils volent) comme cibles de chasse, le rampant du Vide contre les Slothians.
- La recherche de zone 4 (plus loin que les zones 2 et 3).
