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
  à distance, utiliser un `Selector`. `Raycast` s'arrête à la première entité (un allié devant le PNJ
  prend le sort) : préférer `{"Id":"Stab","StartDistance":0,"EndDistance":N,...}` (toutes les entités de la
  ligne) avec `"HitEntityRules":[{"Matchers":[{"Type":"Player"}],"Next":{"Interactions":[...]}}]`, qui ne
  lance le `Next` que sur les joueurs.
- Sensor `Count` (`Count`, `Range`, `IncludeGroups`) : plafonner des invocations en comptant un groupe.
- `Parallel` exige au moins 2 branches (`Interactions`) : la première tourne dans la chaîne, les autres en
  fork.
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

## Pièges vus en jeu (0.7.2)

- Une RootInteraction utilisée par l'action `Attack` d'un rôle doit porter le tag `Attack` avec un seul type :
  `"Tags": {"Attack": ["Melee"]}` (ou `Ranged`, `Block`). Sans lui, le `CombatInteractionValidator` refuse le rôle
  entier. `tools/ValidateRoles.java` le vérifie hors jeu.
- `Effects.WorldSoundEventId` exige un son mono : les variantes `*_Local` (stéréo, pour `LocalSoundEventId`) font
  rejeter toute l'interaction. `ValidateAssets.java` le signale.
- `EntityEffect.StatusEffectIcon` : chemin d'une image sous `Common` (par ex. `UI/StatusEffects/Poison.png`). Sans
  icône, ou avec un chemin faux, le jeu affiche une croix rouge.
- Ne pas hériter de `Ghoul` pour un bipède : c'est un prédateur accroupi animé comme un chien (`Hound`), il
  paraît s'enfoncer dans le sol en marchant.

## Modèles humanoïdes

`"Parent": "Player"`, `"Model": "Characters/Player.blockymodel"`, peau
`Characters/Player_Textures/Player_Greyscale.png` avec `GradientSet: "Skin"` (`GradientId` numérique, `"28"`
très pâle). Visage, cheveux et vêtements vont dans `DefaultAttachments[{Model, Texture, GradientSet,
GradientId}]`, repris de `Cosmetics/CharacterCreator/*.json` (sets `Hair`, `Eyes_Gradient`, `Colored_Cotton`,
`Fantasy_Cotton`, `Shiny_Fabric`, `Faded_Leather`… avec `Black`, `Red`, `White`). Une pièce sur mesure est un
`.blockymodel` dont le nœud racine porte le nom d'un os (`Chest`, `Head`…) avec `settings.isPiece: true` ;
exemple : `mods/nakasar-mobs/tools/generate_vampire_models.py`.
- La tête (`Head`) n'a pas de face avant : sans l'attachement `Characters/Body_Attachments/Faces/Player_Face_Detached.blockymodel`
  (texture `Faces_Detached_Textures/*.png`, `GradientSet: "Skin"`, cf. `Cosmetics/CharacterCreator/Faces.json`), la tête est
  transparente vue de face, même avec `Player_With_Face`.
