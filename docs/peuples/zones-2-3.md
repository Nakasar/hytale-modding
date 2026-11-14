# Peuples d'Orbis, étape 8 : les Feran (zone 2) et les Renoncés (zone 3)

Étape 8 du plan d'implémentation du GDD (https://claude.ai/artifact/FJ15VjWp3pgnt9kmRWjfV7) : deux nouveaux peuples, chacun
avec son village, ses PNJ, ses demandes, ses échoppes, sa chaîne de quêtes, son climat et ses raids. Construite sur
l'étape 7 (camp trork, PR #111).

| | Feran | Renoncés |
|---|---|---|
| Zone | 2 (désert) | 3 (toundra) |
| Id du peuple | `Feran` | `Renonce` (un id contenant « Outlander » tomberait dans le groupe vanilla du culte) |
| Plan de village | `Feran_Oasis` (prefabs vanilla `Npc/Feran/…`) | `Renonce_Givre` (prefabs vanilla `Npc/Outlander/…`) |
| Sol | sable, place en gravier de sable | neige, place en gravier |
| Climat | soif | froid |
| Raids | Scaraks (`Nakasar_Peuples_Raid_Feran`) | culte outlander (`Nakasar_Peuples_Raid_Renonce`) |
| Trophée de raid | `Nakasar_Peuples_Trophy_Scarak` (chitine) | `Nakasar_Peuples_Trophy_Cult` (crânes) |
| Objet de passage | Bracelet de vent (saut x1,35) | Manteau du givre (annule le froid) |

Tout le contenu (plans, rôles, dialogues, demandes, échoppes, raids, objets, effets, icônes, langues) est généré par
`mods/nakasar-peuples/tools/generate_zones.py`. Les langues de l'étape 8 forment un bloc en tête des deux fichiers
`nakasar_peuples.lang`, réécrit à chaque passage. Le générateur échoue si une clé du bloc existe déjà ailleurs dans le
fichier, ou si un titre de demande dépasse **24 caractères**. Kevin, le 14 novembre 2026 : « Tous les titres doivent tenir et ne
pas être coupés » dans le suivi d'objectifs.

    cd mods/nakasar-peuples
    python3 tools/generate_zones.py --preview /chemin/apercus   # plans PNG des deux villages en option

## Les villages se posent seuls

`zone/ZoneSeeder` tourne dans le monde par défaut, 45 s après son ouverture, si un peuple n'a pas encore de village
(`VillageRegistry.isSeeded`). Les étapes sont les suivantes :

1. Il cherche, hors du thread du monde, un point de la zone du peuple autour du joueur ou de l'apparition. La recherche
   utilise `SpiralSearchUtil` sur le générateur du monde, dans un rayon de 6000 blocs, et n'accepte que les zones
   `Zone2_Tier*` ou `Zone3_Tier*` (pas les bords).
2. Il essaie ensuite des sites de 100 à 500 blocs plus loin dans la zone. Un site convient si son centre et ses quatre
   bords sont dans la zone, si au moins 60 % de son sol est celui du peuple (sable pour les Feran, neige ou terre froide
   pour les Renoncés), et si son relief ne dépasse pas 10 blocs.
3. Il pose le village avec `VillageBuilder`, comme le village kweebec automatique.

D'abord les Feran, puis les Renoncés. Le journal du serveur trace la recherche : `Nakasar Peuples : zone … trouvée`, ou un avertissement quand aucun site ne convient.

## Soif (zone 2)

De 9 h à 18 h (heure du jeu), un joueur en zone 2 a soif quand il est à la fois :

- en plein soleil, sans aucun bloc dans les 24 blocs au-dessus de lui ;
- à plus de 2 blocs de l'eau ;
- à plus de 10 blocs d'un abri d'Écho ;
- hors d'une oasis feran.

Tant qu'il a soif, il porte l'effet `Nakasar_Peuples_Thirst` et son endurance ne remonte plus.
L'**Outre d'oasis** (`Nakasar_Peuples_Oasis_Waterskin`, échoppe feran) se boit comme une potion vanilla et donne
l'effet `Nakasar_Peuples_Quenched` pendant 20 minutes : pas de soif.

La **Graine d'Écho** de la chaîne kweebec se plante désormais en zone 2 (clic droit). Elle pose 4 blocs à l'est le
bassin vanilla `Kweebec_Oak_Water_Pool_005`, qui devient un abri contre la soif (sauvegardé dans la ressource de monde
`Nakasar_Peuples_Zones`). La graine monte aussi le joueur au rang Toléré chez les Feran. C'est le pont du GDD entre
les zones 1 et 2. Porter la graine révèle la position de l'oasis feran, une fois par joueur.

## Froid (zone 3)

Le froid reprend l'hypothermie de la fractale Tempête de neige (effets `Nakasar_Peuples_Hypothermia_1` à `_5`, icônes
copiées). Hors d'un abri et loin d'un feu (à plus de 5 blocs d'un feu de camp allumé, d'un brasero ou de lave), le
joueur gagne une pile toutes les 6 s, jusqu'à 10 piles. À l'abri, au chaud ou dans le hameau des Renoncés, il perd une
pile toutes les 1,2 s. Chaque pile retire 0,2 % des PV max par seconde (cause `Nakasar_Peuples_Cold`). Le **Manteau du
givre** porté annule le froid. Porter le Bracelet de vent révèle la position du hameau des Renoncés.

## La ruche scarak (zone 2)

La ruche n'est pas un bâtiment (il n'existe pas de prefab vanilla de ruche en surface). C'est une jauge de 0 à 100 par
monde, qui commence à 20 et gagne 8 chaque matin.

- Elle a 5 niveaux de 20 points. Chaque niveau ajoute un Scarak à chaque vague des raids feran et 5 % de chances de
  raid chaque matin.
- Tuer un Scarak retire 2 points, un pillard scarak 1, la Broodmother 12.
- Quand la ruche perd un niveau, elle lance une riposte : un raid est prévu sur l'oasis feran la plus proche, avec la
  cause « Ruche ».

## Chaînes de quêtes

Elles suivent le modèle kweebec : le chef propose une étape par rang, et les étapes 2 à 4 sont des demandes de chaîne
(poids 0, jamais tirées au tableau).

| Étape | Feran | Renoncés |
|---|---|---|
| 1 (Toléré) | remplir le bassin : 8 Essences d'eau | nourrir les fuyards : 8 Viandes cuites |
| 2 (Ami) | « Les totems du vent » : poser 4 statues du vent | « Les totems du Prêtre » : abattre un Prêtre et deux cultistes |
| 3 (Ami) | « L'entrée de la ruche » : abattre ses gardiens | « Ramener les bateaux » : 32 troncs de sapin |
| 4 (Hôte) | « Escorter le Windwalker » | « Tenir le fort » : défense pendant un raid |
| 5 (Champion) | « La Broodmother », puis le Bracelet de vent | le Manteau du givre |

## Le reste

- **Demandes du tableau** : 9 chez les Feran, 8 chez les Renoncés. Ce sont des collectes, de l'artisanat, des chasses,
  une missive, une escorte et une défense.
- **Échoppes** : 3 par peuple (Toléré, Ami, Hôte). On y trouve par exemple l'Outre d'oasis chez les Feran et des
  vêtements de laine chez les Renoncés.
- **Rôles** : chaque peuple a son crieur, son guetteur, son marchand, son chef et son captif. Il a aussi ses métiers :
  porteuse d'eau et guetteur chez les Feran, chasseur chez les Renoncés, bâtisseur, garde et ancien pour les deux. Le
  défenseur est un Longtooth chez les Feran et un Hunter chez les Renoncés.
- **Assaillants** : `Nakasar_Peuples_Raider_Scarak_{Fighter,Louse,Defender,Broodmother}` et
  `Nakasar_Peuples_Raider_Cult_{Cultist,Berserker,Brute,Marauder}`.
- **Hostilités** : chaque pillard est hostile aux PNJ de son peuple proie et aux joueurs, et amical envers les autres
  pillards (`RaidAttitudeSystem`, `Raids.preys`).
- **Pas de rival** : à la différence des Kweebecs et des Trorks, les Feran et les Renoncés n'ont pas de rival
  (`People.rival()` vaut null). Ni les Scaraks ni le culte ne sont des peuples du mod.

## Nouvelles commandes

| Commande | Accès | Effet |
|---|---|---|
| `/village generer feran` / `renonce` | admin | pose un village de ce peuple devant soi (comme `generer` et `generer trork`) |
| `/village semer feran` / `renonce` | admin | relance la pose automatique d'un village dans sa zone, même si le peuple en a déjà un |
| `/village zone` | tous | zone où l'on se trouve, climat forcé, état de la soif, du froid et de la ruche, villages feran et renoncés |
| `/village climat soif` / `froid` / `aucun` | admin | force un climat sur soi, quelle que soit la zone (`aucun` rend la main à la zone) |
| `/village ruche [points]` | admin | affiche la ruche, ou fixe sa jauge |

Les commandes des étapes précédentes s'appliquent au village le plus proche, quel que soit son peuple : `rep`,
`reppeuple`, `chaineetape`, `demande`, `raidlancer`, `raidfinir`, `palier`, `essor`, etc.

## Tester en jeu

1. **Pose automatique.** Créer un monde neuf, attendre une minute et chercher dans le journal les lignes
   `Nakasar Peuples : zone`. Puis `/village liste` : un village feran et un village renoncé doivent apparaître. Sinon,
   `/village semer feran`.
2. **Village et PNJ.** `/village generer feran` sur du sable plat, puis `/village palier 3` pour voir tous les
   bâtiments. Parler au chef avec `/village tchat Feran_Chef`, puis au marchand et au crieur.
3. **Chaîne.** `/village rep 1000`, puis `/village chaineetape 1` à `5` près du chef pour parcourir les étapes. Pour
   tester l'étape 1 pour de vrai, donner 8 `Ingredient_Water_Essence`.
4. **Soif.** Se placer en plein désert entre 9 h et 18 h (`/time noon`, ou `/village climat soif` ailleurs). L'icône de
   soif doit apparaître et l'endurance ne doit plus remonter. Elle doit disparaître sous un toit, près de l'eau ou
   après avoir bu une Outre d'oasis.
5. **Graine d'Écho.** `/give Nakasar_Peuples_Echo_Seed`, puis clic droit en zone 2 : le bassin apparaît à 4 blocs à
   l'est et il n'y a plus de soif à côté.
6. **Froid.** Faire `/village climat froid` dehors : les piles d'hypothermie montent, puis redescendent près d'un feu
   de camp allumé. `/give Nakasar_Peuples_Frost_Mantle`, puis équiper le manteau : plus de froid.
7. **Bracelet.** `/give Nakasar_Peuples_Wind_Bracelet` : on doit sauter plus haut, et le message révèle le hameau des
   Renoncés.
8. **Raids.** Près de l'oasis, `/village raidlancer` : des Scaraks attaquent les Feran. Près du hameau, le culte
   attaque les Renoncés. Faire `/village ruche 100`, puis relancer un raid : les vagues doivent être plus grosses.
   Tuer quelques Scaraks, puis `/village ruche` : la jauge doit avoir baissé.
9. **Titres.** Ouvrir chaque demande (`/village demande Feran_Gather_Water 1`, etc.) : les titres doivent tenir en
   entier dans le suivi d'objectifs.

## À vérifier en jeu

- Les plans `Feran_Oasis` et `Renonce_Givre` : orientation des huttes et des bateaux, entrées.
- Les animations des métiers sur les modèles Feran et Outlander.
- La recherche de zone. Si elle rate, ses lignes de journal donnent le point trouvé et les sites essayés.
- La soif et le froid sous un vrai abri vanilla.
- L'icône de soif dessinée et l'effet sur l'endurance.
- Le bassin de la Graine d'Écho : est-ce que son eau coule ?
- Les attaques des Scaraks et des cultistes du raid contre les villageois.
