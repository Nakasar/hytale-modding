# Formats des modèles Hytale 0.7.2 (lus dans Assets.zip et confirmés en jeu quand c'est dit)

## Repères et unités

| Format | Unités par bloc | Origine | Avant |
|---|---|---|---|
| Bloc / prop / objet tenu (`format` prop) | 32 | centre du bas du bloc, Y vers le haut | +Z |
| Personnage (`format` character) | 64 | au sol | +Z |

- Texture : **1 texel par unité** ; atlas petits (coffre vanilla 64×96).
- Un enfant est positionné par rapport au **centre de la boîte parente** (position + offset), pas par rapport à
  son coin (preuve : les cadres du couvercle de Chest_Epic à (±13,0,0)).
- `shape.offset` décale la boîte par rapport au pivot du nœud : pour un couvercle, pivot sur la charnière.
- `shadingMode` : `standard`, ou `fullbright` pour ce qui brille.
- Une rotation positive autour de X penche le haut d'un nœud vers l'avant (+Z) (moteur `fractal_anim`).

## Blocs en modèle (BlockType)

- `DrawType "Model"`, `CustomModel "Blocks/…blockymodel"`, `CustomModelTexture [{Texture, Weight: 1}]`,
  `CustomModelScale` optionnel, `Opacity "Transparent"`, `Material "Solid"`, `HitboxType` (`Full`,
  `Brazier_Small`, `Torch`, `Potion`, `Plant_Large`, `Bench_Campfire`…).
- `VariantRotation "NESW"` : bloc orientable. Table supposée `FRONTS = [(0,1),(1,0),(0,-1),(-1,0)]` pour la
  rotation k (non vérifiée en jeu). En prefab, yaw 0 regarde le SUD (+Z), 1 l'est, 2 le nord, 3 l'ouest (vérifié).
- Icône : `IconProperties {Scale, Translation[2], Rotation [22.5, 45, 22.5]}`.
- Animation en boucle : `CustomModelAnimation "Blocks/Animations/…blockyanim"`.
- États : `State.Definitions.<Nom>` surcharge `CustomModel`, `CustomModelTexture`, `CustomModelAnimation`, `Light`
  (null = éteint), `Particles`, `AmbientSoundEventId`, `InteractionHint`. Torche : interaction Use
  `{"Type":"ChangeState","Changes":{"default":"Off","On":"Off","Off":"On"}}`. Coffre : `OpenWindow`/`CloseWindow`.
- Particules : `Particles [{SystemId, Scale, TargetNodeName, PositionOffset{Y}}]`.
- Une erreur dans le BlockType imbriqué n'est pas vue par `Item.CODEC` : `ValidateAssets` le décode avec
  `BlockType.CODEC`.
- Un bloc `Material Empty` dans le battant d'une porte est cassé et lâché quand la porte s'ouvre.

## Objets tenus (prop)

- Garder l'enveloppe de `fm.build_model` : un nœud racine vide au nom du modèle (`shape none`) avec les pièces
  en enfants (`generate_item_models.prop_model`). Sans elle, l'objet est mal tenu.

## Personnages

- Humanoïde : `Server/Models/X.json` avec `"Parent": "Player"` (rig, hitbox, toutes les animations),
  `Model: Characters/Player.blockymodel`, peau `Characters/Player_Textures/Player_Greyscale.png` +
  `GradientSet: Skin` + `GradientId`.
- **La tête du rig n'a pas de face avant** : toujours ajouter l'attachement
  `Characters/Body_Attachments/Faces/Player_Face_Detached.blockymodel` + une texture de
  `Faces_Detached_Textures/` (GradientSet Skin), sinon la tête est transparente vue de face (vu en jeu).
- Vêtements : `DefaultAttachments [{Model, Texture, GradientSet, GradientId}]`, cosmétiques de
  `Cosmetics/CharacterCreator/*.json`. Gradient sets connus : Hair, Skin, Eyes_Gradient, Colored_Cotton,
  Pastel_Cotton, Fantasy_Cotton(_Dark), Shiny_Fabric, Faded_Leather, Ornamented_Metal.
- Attachement `.blockymodel` : `{"nodes":[…],"format":"character","lod":"auto"}` ; nœuds racines nommés comme un
  os, `shape.type none`, `settings.isPiece true` ; enfants box/quad avec `textureLayout {offset, mirror, angle}`
  par face.
- Os du rig Player : Pelvis > Belly > Chest > {R/L-Shoulder > Arm > Forearm > Hand, Head > {Neck,
  *-Eye/Ear/Mouth-Attachment}, Back-Attachment}, Pelvis > R/L-Thigh > Calf > Foot.
- Le `Parent` d'un modèle impose ses animations : `Ghoul` est un prédateur accroupi (animations de chien) et
  rend un bipède enfoncé dans le sol.

## Animations (.blockyanim)

- `{formatVersion, duration (images), holdLastKeyframe, nodeAnimations{<nœud>: {position[], orientation[]
  (deltas en quaternions), shapeStretch[], shapeVisible[], shapeUvOffset[]}}}` ; clés `{time, delta,
  interpolationType}`. 60 images/s.
- Attaques de PNJ : `Server/Item/Animations/<Id>.json` (chemin ThirdPerson, `WiggleWeights` obligatoire) et dans
  l'interaction `Effects.ItemPlayerAnimationsId` + `ItemAnimationId`.

## Icônes d'effet

- `EntityEffect.StatusEffectIcon` = chemin sous Common (`UI/StatusEffects/Poison.png` 512², ou
  `Icons/ItemsGenerated/…` 64²). Icône absente = croix rouge.
