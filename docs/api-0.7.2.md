# Notes API serveur Hytale 0.7.2

Vérifié avec `javap` sur `com.hypixel.hytale:Server:0.7.2` (Maven officiel). Classes Java 25.

## Plugin

- `manifest.json` à la racine du jar : `Group`, `Name`, `Version`, `Description`, `Authors`, `Main`,
  `IncludesAssetPack`, `ServerVersion`, `Dependencies` (`"Groupe:Nom": "plage"`). Identité = `Group:Name`.
- Un pack d'assets pur est le même manifest sans `Main`, dans un zip (ou un dossier) avec `Server/**`.
- `Main` étend `com.hypixel.hytale.server.core.plugin.JavaPlugin` ; `setup()` sert aux
  enregistrements, `shutdown()` au nettoyage.
- Les runes nécessitent la dépendance `"Hytale:Abilities": "*"`.

## Interaction personnalisée

```java
public final class MyInteraction extends SimpleInstantInteraction {
    public static final BuilderCodec<MyInteraction> CODEC = BuilderCodec
        .builder(MyInteraction.class, MyInteraction::new, SimpleInstantInteraction.CODEC)
        .documentation("...")
        .append(new KeyedCodec<>("Duration", Codec.FLOAT), (i, v) -> i.duration = v, i -> i.duration)
        .documentation("...").add()
        .build();

    @Override
    protected void firstRun(InteractionType type, InteractionContext context, CooldownHandler cooldowns) {
        // context.getEntity() : exécutant (projectile dans une chaîne ProjectileHit)
        // context.getOwningEntity() : propriétaire (le lanceur)
        // context.getTargetEntity() : cible (entité touchée)
        // échec : context.getState().state = InteractionState.Failed;
    }
}
```

Enregistrement dans `setup()` :
`getCodecRegistry(Interaction.CODEC).register("Nakasar_MyInteraction", MyInteraction.class, CODEC)`.
Le JSON l'utilise ensuite avec `"Type": "Nakasar_MyInteraction"`.

## Attributs de runes

- `ImpactModifiers.resolve(context, actingRef, accessor).getAttribute(name, fallback)` lit un attribut
  du *cast* (déclaré dans `Ability.Attributes` de la rune, modifié par les runes de support).
- Implémenter `AbilityAttributeBinding` (`collectAbilityAttributes(Consumer<String>)`) pour que
  l'audit `--validate-assets` compte l'attribut comme « lié ».
- Promesses des mots-clés livrés : `Damage` → attribut `Damage`, `Aoe` → `AoeScale`,
  `Duration` → `Duration`, `Projectile` → interaction `LaunchAbilityProjectile`.

## Composants et monde

| Besoin | API |
|--------|-----|
| Position / rotation | `TransformComponent` (`server.core.modules.entity.component`), `HeadRotation` |
| Téléporter un joueur | `Teleport.createForPlayer(Vector3dc, Rotation3fc)` puis `buffer.putComponent(ref, Teleport.getComponentType(), t)` |
| Point d'impact d'une chaîne | `context.getMetaStore().getMetaObject(Interaction.HIT_LOCATION)` (`Vector4d`) |
| Monde depuis un buffer | `((EntityStore) buffer.getExternalData()).getWorld()` ; `world.execute(Runnable)`, `world.scheduleAfter(Runnable, delay, unit)` |
| Immobiliser un PNJ | ajouter le composant `Frozen` (`Frozen.get()`), le retirer avec `tryRemoveComponent` ; le ré-ajouter sur une entité qui l'a déjà lève une exception |
| Attitude d'un PNJ | `WorldSupport.get(ref, accessor).overrideAttitude(targetRef, Attitude.FRIENDLY, secondes)` ; le champ interne `attitudeOverrideMemory` peut être `null` pour les rôles sans action `OverrideAttitude` (NPE) → initialisé par réflexion dans `DominateInteraction` |
| Effet d'entité | `EntityEffect.getAssetMap().getAsset(id)` puis `EffectControllerComponent.addEffect(ref, effect, secondes, OverlapBehavior.OVERWRITE, accessor, ownerRef)` |
| Journal | `HytaleLogger` (flogger) : `atInfo().log(...)`, `atWarning().withCause(e).log(...)` |

## Pièges rencontrés

- Les `Effects` (sons, particules, animation) d'une chaîne simulée côté serveur (projectile, entité
  d'ability) n'atteignent jamais le client : utiliser `TriggerAbilityFX`.
- Un `Selector` AOE dans la chaîne d'un projectile ne balaie pas : il ne touche que l'entité frappée.
- `Interactions` d'un `ProjectileConfig` hérité remplace toute la map : redéclarer `ProjectileHit` **et**
  `ProjectileMiss`, sinon le projectile reste planté dans le mur.
- `RunTime` sur un `Repeat` ne cadence pas les itérations : mettre la pause dans la chaîne forkée.
- `MovementEffects.DisableAll` ne bloque que les joueurs ; les PNJ ont besoin du composant `Frozen`.
- `EntityStatsOnHit` crédite toujours l'attaquant : `Health` y fait un vol de vie.

## Recettes et établis

- Dossiers d'assets (`AssetRegistryLoader`) : `Item/Items`, `Item/Recipes`, `Item/Block/Hitboxes`, `Item/Groups`…
  Les fichiers client (`.blockymodel`, textures, icônes) vont sous `Common/` du pack (`Blocks/`, `BlockTextures/`,
  `Items/`, `Icons/`…) et sont référencés sans ce préfixe.
- `CraftingRecipe` (fichier de `Item/Recipes` ou clé `Recipe` d'un objet) : `Input[]`, `Output[]`, `PrimaryOutput`,
  `OutputQuantity`, `BenchRequirement[]`, `TimeSeconds`, `KnowledgeRequired`, `RequiredMemoriesLevel`.
  Une recette inline prend l'objet porteur comme sortie et un id généré.
- `MaterialQuantity` : `ItemId` **ou** `ResourceTypeId` **ou** `ItemTag`, `Quantity`, `Metadata`.
- `BenchRequirement` : `Type` (`Crafting`, `Processing`, `DiagramCrafting`, `StructuralCrafting`), `Id`
  (= `BlockType.Bench.Id`), `Categories[]` (= ids de `Bench.Categories[]`, une recette sans catégorie connue
  n'apparaît nulle part : `BenchRecipeRegistry.categoryMap`), `RequiredTierLevel`, `RequiredAugmentTags`.
  Un id d'établi inconnu est accepté sans erreur (`computeIfAbsent`).
- `BlockType.Bench` : `Type`, `Id`, `DescriptiveLabel`, `TierLevels[]` (`UpgradeRequirement{Material[],TimeSeconds}`,
  `CraftingTimeReductionModifier`, `ExtraInputSlot`, `ExtraOutputSlot`), sons `LocalOpenSoundEventId`,
  `LocalCloseSoundEventId`, `CompletedSoundEventId`, `FailedSoundEventId`. `Crafting` ajoute `Categories[]`
  (`Id`, `Name` — défaut `server.benchCategories.{id}` —, `Icon`, `ItemCategories[]`).
- Le composant `BenchBlock` est posé par `BenchSystems.OnAddOrRemoved` sur les blocs qui ont un `Bench` et une
  entité de bloc : les établis vanilla déclarent `BlockType.BlockEntity { Components: { BenchBlock: {} } }`. `BlockType.State` n'a qu'une clé, `Definitions` (map d'états → BlockType
  partiels) ; la fenêtre de craft bascule les états `CraftCompleted` / `CraftCompletedInstant`
  (`SimpleCraftingWindow`). Une clé `Id` dans `State` est ignorée (journal « unused keys »).
- Validation : `Item.Icon`, `Bench.Categories[].Icon`, `CustomModel`, `CustomModelTexture` sont vérifiés contre
  les fichiers `Common/` présents (`CommonAssetValidator`) ; `ItemSoundSetId`, `PlayerAnimationsId`,
  `BlockBreakingDecalId`, `HitboxType` et `MaterialQuantity.ItemId` contre les assets chargés.
- Établi d'armes vanilla (`Bench_Weapon.json`) : `Bench.Id` `Weapon_Bench`, onglets `Weapon_Sword`, `Weapon_Mace`,
  `Weapon_Battleaxe`, `Weapon_Daggers`, `Weapon_Bow`, 3 paliers, `HitboxType: Bench_Weapon`, sons
  `SFX_Weapon_Bench_Open/Close/Craft`. Un échec de
  validation rejette **tout** l'asset (`AssetStore.recordFailedToLoad`), pas seulement le champ : d'où les
  recettes en fichiers séparés. `BlockSoundSetId` et `PhysicalMaterialId` inconnus ne font qu'un avertissement.
- `Support` = faces de support **requises** (`RequiredBlockFaceSupport`) ; `Supporting` = faces offertes. Les interactions d'ouverture par
  défaut sont `*Simple_Crafting_Default`, `*Diagram_Crafting_Default`, `*Structural_Crafting_Default`.
- `BlockType` utile : `DrawType` (`Cube`, `Model`, `CubeWithModel`…), `CustomModel`, `CustomModelTexture[]`,
  `Material` (`Solid`/`Empty`), `Opacity` (`Solid`, `Semitransparent`, `Cutout`, `Transparent`),
  `VariantRotation` (`None`, `NESW`, `UpDownNESW`…), `PlacementSettings.RotationMode` (`FACING_PLAYER`,
  `BLOCK_NORMAL`…), `HitboxType` (défaut `Full`), `Gathering.Breaking{GatherType, ItemId, Quantity, DropList}`.
- `.blockymodel` = JSON : `nodes[]` avec `position`, `orientation` (quaternion), `shape{type, offset, size,
  stretch, textureLayout, settings}`, `children[]` (`BlockyModelBoundsParser`).

## Portails et instances (fragment Halloween)

- L'Ancienne passerelle (`Portal_Device`) accepte tout objet qui a un bloc `PortalKey`
  (`PortalType`, `TimeLimitSeconds`, `AllowedEntryCount`). Le `PortalType`
  (`Server/PortalTypes/*.json`) donne `InstanceId`, `Description` (clés de traduction, `ThemeColor`,
  `DescriptionTags`, `Objectives`), `TimeLimitSeconds`, `CloseWhenEmpty`, `VoidInvasionEnabled`,
  `Spawn`, `GameplayConfig` (défaut `Portal`).
- Une instance est un dossier `Server/Instances/<id>/instance.bson` : un `WorldConfig` écrit en JSON.
  Le générateur moderne s'écrit `"WorldGen": { "Type": "HytaleGenerator", "WorldStructure": "<id>" }`.
- Les assets du générateur vivent dans `Server/HytaleGenerator/{Biomes,WorldStructures,...}`. Les types
  (`Density`, `Props`, `Positions`...) sont enregistrés dans l'initialiseur statique de
  `builtin.hytalegenerator.assets.AssetManager`. Un `ExportAs` déclare un nom global réutilisable
  par `Imported`.
- Un prop `Prefab` prend des chemins relatifs à `Server/Prefabs/` de chaque pack (`Nakasar/Halloween/Crypts`),
  fichier ou dossier (`PrefabPropAsset.loadPrefabBuffersFrom`). Un chemin introuvable ne logue rien et donne
  un prop vide : écrire `Prefabs/...` faisait disparaître toutes les structures (bug vu en jeu le 2026-10-17).
- Distance horizontale au centre du monde : densité `Axis` avec `"Axis": {"X": 0, "Y": 1, "Z": 0}` et une
  `Curve`. Les courbes `Manual` sont plates avant le premier point et après le dernier.
- Format prefab JSON : `version` 8, `blocks[{x,y,z,name,rotation}]`, nom avec préfixe de
  probabilité possible (`70%Bloc`), rotation = roll×16 + pitch×4 + yaw.
- `Environment` exige `WeatherForecasts` pour les 24 heures et `WeatherForecastSeed`.
- Couleurs : `#rrggbb` ou `#rrggbbaa` (aussi `rgb(...)`, `rgba(...)`).
- Pour décoder un asset hors serveur (`tools/ValidateAssets.java`) : `Options.parse`, un
  `HytaleServer` factice qui porte un `EventBus`, l'initialisation d'`AssetRegistryLoader`, et un
  `AssetExtraInfo` pour les codecs `ContainedAssetCodec`.
- Les enums des assets (`EnumCodec` en style `CAMEL_CASE`) s'écrivent en CamelCase : `"RotationMode": "FacingPlayer"`,
  pas le nom Java `FACING_PLAYER` (refusé : « Failed to find enum value »). Le `BlockType` d'un objet n'est pas
  décodé par `Item.CODEC` : `ValidateAssets` ne voit donc pas ces erreurs.
