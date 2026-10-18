# PNJ dans le serveur 0.7.2 : notes vérifiées dans le jar

Référence complète des briques d'IA (sensors, actions, mouvements, avec champs et valeurs par défaut) :
[npc-reference-0.7.2.md](npc-reference-0.7.2.md), générée par
`java mods/nakasar-mobs/tools/ValidateRoles.java --descriptors docs/npc-reference-0.7.2.md`.

## Fichiers

| Quoi | Chemin dans le pack |
|------|---------------------|
| Rôle (IA, PV, apparence) | `Server/NPC/Roles/**` (id = nom du fichier) |
| Modèle | `Server/Models/**` (`Parent` pour hériter d'un modèle vanilla) |
| Butin | `Server/Drops/**` |
| Groupes | `Server/NPC/Groups/**` (`IncludeRoles`) |
| Apparitions | `Server/NPC/Spawn/World` (par environnement), `Spawn/Markers` (point fixe), `Spawn/Beacons` |
| Attaques | `Server/Item/RootInteractions` + `Server/Item/Interactions` (comme les armes) |
| Effets | `Server/Entity/Effects/**` |

## Rôles

- `Type` : `Generic`, `Abstract` (`Parameters`, valeurs lues avec `{"Compute": "Nom"}`) ou `Variant`
  (`Reference` + `Modify`).
- L'IA est un arbre `{Sensor, BodyMotion, HeadMotion, Actions, ActionsBlocking, Instructions}` : la
  première branche dont le sensor réussit gagne.
- `StateTransitions` : `{States:[{From,To}], Actions}` joue des actions au changement d'état (pratique
  pour lancer les minuteurs de sorts à l'entrée en combat).
- Une clé inconnue n'est **pas** une erreur : le serveur écrit seulement `WARN Unknown JSON attribute`.
  `ValidateRoles.java` compte ces lignes comme des erreurs.

## Pièges

- `Fly` : `Gravity` doit être > 0.
- `TimerStart` : `StartValueRange` doit être > 0 (0,1 pour « tout de suite »).
- Un minuteur non répété qui arrive à 0 passe à `STOPPED` : tester « recharge terminée » avec
  `{"Type":"Timer","Name":"X","State":"STOPPED"}`, puis `TimerRestart` après le sort.
- L'action `Attack` ne démarre pas tant qu'une autre attaque tourne.
- `LaunchProjectile` utilise les anciens assets `Projectile` ; pour viser un joueur avec une interaction
  à distance, un sélecteur `{"Type":"Selector","Selector":{"Id":"Raycast","Distance":N}}` suffit.
- `EntityEffect` : `ApplicationEffects.HorizontalSpeedMultiplier`, `Debuff`, `Invulnerable`,
  `DamageResistance`, `ModelOverride`.
- `ItemDropList` : `Container.Type` = `Multiple` / `Choice` / `Single` / `Droplist` / `Empty` ; `Single`
  contient `Item{ItemId, QuantityMin, QuantityMax}`, `Weight` règle les chances d'un `Choice`.
- `SpawnMarker` : `NPCs[{Name, Weight, RealtimeRespawnTime, SpawnAfterGameTime, Flock}]`,
  `RealtimeRespawn`, `ExclusionRadius`. Un bloc portant le composant
  `BlockEntity.Components.SpawnMarkerBlock.Config.SpawnMarker` crée le marqueur là où il est posé (y
  compris dans un prefab).
- `WorldNPCSpawn` : `Environments`, `NPCs[{Id, Weight}]`, `DayTimeRange`.

## Filtrer des dégâts en Java

Sous-classe de `DamageEventSystem`, groupe `DamageModule.get().getFilterDamageGroup()`, enregistrée avec
`getEntityStoreRegistry().registerSystem(...)`. `Damage.getSource()` est un `Damage.EntitySource`
(`ProjectileSource` en hérite, `getRef()` = le tireur) ; `damage.setCancelled(true)` annule le coup.
Exemple : `mods/nakasar-mobs/src/main/java/dev/nakasar/hytale/mobs/domination/`.

## Validation hors jeu

`ValidateRoles.java` démarre juste assez du serveur (`NPCPlugin.setupNPCLoading()` sur des stores d'assets
vides) pour charger les rôles avec le vrai `BuilderManager`. Les références vers d'autres assets (modèles
vanilla, interactions) sont listées `REF` sans compter comme erreurs ; passer les dossiers `Server` des
packs requis en arguments pour qu'elles soient résolues.
