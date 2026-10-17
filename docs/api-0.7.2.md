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
- Le composant `BenchBlock` est posé par `BenchSystems.OnAddOrRemoved` sur les blocs qui ont un `Bench` et un
  état de bloc ; d'où le `State { Id: "crafting" }` des établis vanilla. Les interactions d'ouverture par
  défaut sont `*Simple_Crafting_Default`, `*Diagram_Crafting_Default`, `*Structural_Crafting_Default`.
- `BlockType` utile : `DrawType` (`Cube`, `Model`, `CubeWithModel`…), `CustomModel`, `CustomModelTexture[]`,
  `Material` (`Solid`/`Empty`), `Opacity` (`Solid`, `Semitransparent`, `Cutout`, `Transparent`),
  `VariantRotation` (`None`, `NESW`, `UpDownNESW`…), `PlacementSettings.RotationMode` (`FACING_PLAYER`,
  `BLOCK_NORMAL`…), `HitboxType` (défaut `Full`), `Gathering.Breaking{GatherType, ItemId, Quantity, DropList}`.
- `.blockymodel` = JSON : `nodes[]` avec `position`, `orientation` (quaternion), `shape{type, offset, size,
  stretch, textureLayout, settings}`, `children[]` (`BlockyModelBoundsParser`).
