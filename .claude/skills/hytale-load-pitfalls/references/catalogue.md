# Catalogue des pièges rencontrés (Hytale 0.7.2)

Chaque ligne : symptôme en jeu → cause → parade (et si elle est automatique). Ajouter une ligne à chaque nouveau
piège.

## Le mod (ou tout) ne charge pas

| Symptôme | Cause | Parade |
|---|---|---|
| Aucun pack ne charge, même vanilla : `GameplayConfig 'Default' doesn't exist`, `Missing default DamageCause assets` | une entrée de `Dependencies` (REQUIRED) du manifest est absente ou désactivée pour le monde | `OptionalDependencies` entre nos mods (lint) |
| Plugin qui échoue au setup : `SystemType dependency isn't registered` | `SystemDependency` sur une classe de système jamais enregistrée (`EntityStatsSystems.Regenerate`) | dépendre de `NPCPlugin.NPCEntityRegenerateStatsSystem` / `EntityStatsModule.PlayerRegenerateStatsSystem` (lint) |
| Mod entier rejeté à la validation des marqueurs | un rôle rejeté parce qu'il cite un drop vanilla inexistant (`Drop_Zombie_Aberrant_Big`) | `validateAssets -Drefs` contre `vanilla-refs-0.7.2.txt` |
| Rôle de boss rejeté (`CombatInteractionValidator`) | plus d'une interaction taguée `AimingReference` dans une chaîne d'Attack | `validateRoles` les compte |
| Rôle volant rejeté | `MaintainDistance`/`TakeOff`/`Land` sans contrôleur Walk (Fly seul) | Walk avec MinHover/MaxHover comme les esprits vanilla ; `validateRoles` |
| Attaque de rôle rejetée | RootInteraction d'Attack sans `"Tags": {"Attack": ["Melee"|"Ranged"]}` | `validateRoles` |
| Interaction entière rejetée | `WorldSoundEventId` stéréo (`*_Local`, mais aussi `SFX_Drop_*`, `SFX_Drag_*`, …) | `validateAssets -Dstereo` + lint ; les volumes de déclenchement peuvent jouer du stéréo |
| Bloc rejeté au chargement | enum en MAJUSCULES Java (`FACING_PLAYER`) au lieu du CamelCase (`FacingPlayer`) | lint ; `BlockType` imbriqué décodé à part par ValidateAssets |
| Objet entier rejeté | un champ invalide (Icon, ItemSoundSetId, PlayerAnimationsId, BlockBreakingDecalId, HitboxType, MaterialQuantity.ItemId, fichier Common absent) | recettes dans des fichiers séparés ; `validateAssets` |
| Recette invisible | `Categories` qui ne correspond à aucun onglet `Bench.Categories[].Id` | lire l'établi vanilla |

## Ça charge mais ça casse en jeu

| Symptôme | Cause | Parade |
|---|---|---|
| Crash du monde `Invalid entity reference` | action `Despawn` avec `"Force": true` (l'entité se retire pendant son propre tick) | jamais Force ; `validateRoles` + lint |
| Damier rose et noir | id de bloc inconnu dans un prefab/worldgen, ou mauvaise syntaxe d'état (`*<Objet>_State_Definitions_<État>`) | `validateAssets -Dblocks` |
| Structure absente, sans erreur | chemin de prefab préfixé `Prefabs/` (relatif à `Server/Prefabs/`) ou dossier inexistant | lint |
| Îles enfoncées / disparues en worldgen | `wg.column()` force Y = 81 avant `distance_to` | positions de distance à Y = 81 |
| Retour au monde dès l'arrivée par portail | le portail de retour apparaît sur le point d'arrivée et autorise le retour après 15 s ; un client lent y est renvoyé | `SpawnReturnPortal false` + portail de retour placé à côté dans le prefab |
| Objet porté « perdu » | `canRemoveItemStack(new ItemStack(id, 1))` compare la durabilité | compter par id (lint) |
| Objet au sol impossible à ramasser par Interact | le client ne cible jamais les entités d'objet | ramassage accroupi (`arena/CrouchPickup`) |
| Coups sur un bloc sans effet dans une instance | `BlockModificationAllowed false` : `DamageBlockEvent` jamais émis | PNJ gelés ou interactions Use |
| Blocs cassés et lâchés à l'ouverture d'une porte | les blocs `Material Empty` dans le battant (3×3) sont détruits | `generate_prefabs.door_swings` + vérification |
| Élite restée invulnérable / joueur resté gelé après redémarrage | état temporaire sauvegardé (Invulnerable, Frozen) | composants sans codec, nettoyage au chargement/déchargement |
| Lumière d'un joueur vue par tous | `DynamicLight` est diffusé à tous les spectateurs | file privée (`PrivateNightLightSystem`) (lint) |
| PNJ figé 1,5 s après apparition | `SpawnLockTime` par défaut de 1,5 s | le baisser dans le rôle (vrilles : 0,5) |
| Grand mob coincé | porte plus basse que sa hitbox (× échelle) | portes ≥ hauteur de hitbox |
| Barre de vie qui oscille | régénération naturelle du PNJ contre la vie fixée | `PinnedHealth` après `NPCEntityRegenerateStatsSystem` |
| Système qui agit deux fois | deux instances de la même classe de système enregistrées | une seule instance, paramétrée par registre |
| Annotations d'erreur en CI sans échec | logs stderr du serveur pendant ValidateRoles | filtrés depuis PR #22 |
| Vitesse d'un projectile à 0 au lancement | `getVelocity` vaut 0 au spawn | `SimplePhysicsProvider` nextTickVelocity |
| Rotation de projectile fausse | `SpawnRotationOffset` Yaw est en RADIANS | |

## Pièges d'outillage

| Symptôme | Cause | Parade |
|---|---|---|
| Fichier texte multiplié (README de 56 000 lignes) | `s.replace(old, new)` avec `old` vide | `git diff --stat` + lint |
| Diff énorme sur un prefab inchangé | générateur non déterministe (`Tower0.prefab.json`) | `git checkout` après génération ; graines fixes |
| MDX du wiki qui ne compile pas | accolades non échappées, `<img>` brut, ids `{#…}` non ASCII | voir skill `hytale-ingame-feedback` (wiki) |
