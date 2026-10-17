# Conception des mods

## nakasar-runes (plugin Java + assets)

Tout est en JSON sauf trois interactions impossibles en pur asset, écrites en Java et enregistrées sous
les types `Nakasar_TeleportCasterToImpact`, `Nakasar_Dominate` et `Nakasar_RootNpc`.

Fichiers communs : `Server/Abilities/Keywords/Nakasar_*.json` (mots-clés affichés sur les runes),
`Server/Languages/{fr-FR,en-US}/nakasar_runes.lang` (noms et descriptions).

Chaque rune suit le schéma vanilla : objet `Rune_Nakasar_<X>` (`Ability.Slot: Core`, coût en mana,
cooldown, mots-clés, attributs) → `Root_Nakasar_Ability_<X>` → `Nakasar_Ability_<X>_Cast`
(`StatsCondition UseAbilityCost` → `Parallel` [ effet, `TriggerCooldown`, `ChangeStat` ]).

| Rune | Coût / CD | Portée | Effet |
|------|-----------|--------|-------|
| Baiser du Vampire (`Rune_Nakasar_VampireKiss`) | 30 mana / 4 s | mêlée (balayage horizontal 2,8 m) | 18 dégâts physiques (× attribut `Damage`), `EntityStatsOnHit Health +12` au lanceur (vol de vie, dégressif sur plusieurs cibles) |
| Domination (`Rune_Nakasar_Domination`) | 45 mana / 12 s | mêlée (estoc 3 m) | `Nakasar_Dominate` : attitude `FRIENDLY` forcée pendant `Duration` (6 s), effet visuel `Nakasar_Dominated` (teinte violette). PNJ uniquement |
| Téléportation (`Rune_Nakasar_Blink`) | 35 mana / 8 s | distance (projectile) | `Projectile_Config_Nakasar_Blink` ; à l'impact (entité ou terrain) `TriggerAbilityFX` puis `Nakasar_TeleportCasterToImpact` téléporte le lanceur 0,6 m en retrait du point d'impact |
| Chaînes spectrales (`Rune_Nakasar_SpectralChains`) | 40 mana / 10 s | distance (projectile) | `Projectile_Config_Nakasar_Chains` ; sur entité : FX « pointe de terre » bleutée, effet `Nakasar_Spectral_Chains` (`DisableAll`, attaques, abilities et esquive désactivées, knockback nul, particules `Stunned`) pendant `Duration` (3 s) + `Nakasar_RootNpc` (composant `Frozen`) pour les PNJ |

Attributs lisibles par les runes de support : `Damage` (Vampire), `Duration`
(Domination, Chaînes), `Speed` (projectiles).

### Interactions Java

- `TeleportCasterToImpactInteraction` : lit la position du projectile (ou `HIT_LOCATION`), recule de
  `BackOffset` vers le lanceur, ajoute `VerticalOffset`, pose un composant `Teleport` sur le lanceur.
- `DominateInteraction` : cible = PNJ avec `WorldSupport` ; `overrideAttitude(lanceur, attitude, durée)`
  ; applique `EffectId` si fourni. Clés JSON : `Duration`, `DurationAttribute`, `EffectId`, `Attitude`.
- `RootNpcInteraction` : ajoute `Frozen` à la cible PNJ et programme son retrait (`world.scheduleAfter`)
  ; une seconde application prolonge la durée, et un PNJ déjà gelé par quelqu'un d'autre (`/npc freeze`) n'est pas touché. Clés : `Duration`, `DurationAttribute`.

## nakasar-spear (pack d'assets)

Objet `Weapon_Nakasar_Spear_Iron` : rig `PlayerAnimationsId: Spear` (deux mains), famille `Spear`,
jauge `SignatureEnergy` (+20 max). Les dégâts sont surchargeables par objet via `InteractionVars`
(`Swing_Left_Damage`, `Swing_Right_Damage`, `Thrust_Damage`, `Spin_Charged_Damage`,
`Signature_Rush_Damage`, `Signature_Spin_Damage`), comme les armes vanilla.

### Attaque principale (`Root_Nakasar_Spear_Primary` → `Nakasar_Spear_Primary`)

`Charging` (animation `ThrowCharging`) :

- relâché tout de suite (`"0"`) → `Nakasar_Spear_Combo`, un `Chaining` (fenêtre 1,6 s) :
  1. `Nakasar_Spear_Swing_Left` : balayage horizontal vers la gauche (14 dégâts, +2 signature)
  2. `Nakasar_Spear_Swing_Right` : balayage vers la droite (14, +2)
  3. `Nakasar_Spear_Thrust` : petit pas en avant (`ApplyForce`) + estoc `Stab` 3,8 m (24 dégâts,
     knockback, +4 signature), puis `CancelChain` pour repartir du premier coup
- maintenu 0,8 s (`"0.8"`) → `Nakasar_Spear_Spin_Charged` : coup circulaire `AOECircle` rayon 3,5 m
  (20 dégâts, knockback radial `Point`, +3 signature)

### Ultime (`Root_Nakasar_Spear_Signature` sur `Ability1` → `Nakasar_Spear_Signature`)

`StatsCondition SignatureEnergy 100 %` (sinon son d'erreur) → `Serial` :

0. `ChangeStat SignatureEnergy -100 %` en tête : la jauge est consommée même si la chaîne est
   interrompue ensuite (coup reçu, changement d'objet)
1. préparation 0,2 s (animation `StabDashCharging`)
2. ruée : `ApplyForce` vers l'avant (force 12) puis `Repeat ×4` de `Nakasar_Spear_Signature_Rush_Stab`
   (petite poussée + estoc 3,5 m, 16 dégâts chacun, cadence ~0,28 s)
3. `Nakasar_Spear_Signature_Spin` : coup circulaire rayon 4 m, 40 dégâts, forte projection
4. `CancelChain`

### Réglages

Toutes les valeurs (dégâts, portées, durées, forces) sont dans les JSON cités ; aucun code.

## nakasar-halloween (pack d'assets)

Fragment d'Orbis ouvert depuis l'Ancienne passerelle vanilla (`Portal_Device`) avec la clé
`PortalKey_Nakasar_Halloween`. Chaîne : clé (`PortalKey.PortalType`) → `PortalTypes/Nakasar_Halloween`
(textes, objectifs, 30 min) → `Instances/Nakasar_Halloween_Fragment/instance.bson` (générateur
`HytaleGenerator`, météo forcée, début à 20 h) → structure de monde `Nakasar_Halloween` → biome
`Nakasar_Halloween_Barrens`.

### Génération (`tools/generate_worldgen.py`)

- **Terrain** : plaine vallonnée autour de y = 81 (deux bruits simplex), sol d'herbe et de terre
  brûlées, couches de terre, gravier puis pierre / ardoise / schiste.
- **Aplanissement** : les positions des structures sont exportées (`ExportAs`) et réutilisées par le
  terrain : le relief tombe à zéro dans un rayon de 34 blocs autour de chaque structure, pour qu'elle
  repose à plat.
- **Structures aléatoires** : une maille de 150 blocs (avec jitter) tire une structure par cellule,
  à plus de 110 blocs du point d'apparition et du château du comte. Poids : crypte 3, champ de
  citrouilles 3, château hanté 2, cimetière hanté / araignées / morts-vivants 1,5 chacun.
- **Château du comte** : toujours à 190 blocs au nord du point d'apparition (objectif du portail).
- **Décor** : arbres morts et pendus (maille de 13), tas d'os, tombes isolées, nids d'araignées,
  citrouilles (maille de 29), plantes mortes et toiles (maille de 3).
- **Environnements** : `Nakasar_Env_Halloween_Haunted` à moins de 45 blocs d'une structure (PNJ plus
  dangereux, densité plus forte), `Nakasar_Env_Halloween` ailleurs.

### Prefabs (`tools/generate_prefabs.py`, 35 fichiers)

| Dossier | Nombre | Contenu |
|---------|--------|---------|
| `Crypts` | 3 | Mausolée (pierre, ardoise, schiste) et salle funéraire enterrée : cercueils, ossements, toiles |
| `HauntedCastles` | 2 | Château en ruine 33×33 (pierre ou ardoise) : tours, courtines, donjon (table, lustre, chambre), puits |
| `DraculaCastle` | 1 | Château du comte 41×41 en basalte : flèches, salle du trône au tapis rouge, crypte sous le donjon, roseraie de sang, pendus |
| `Cemeteries/{Haunted,Spiders,Undead}` | 2 × 3 | Cimetière abandonné : hanté (bougies, citrouilles effrayantes, lanterne), envahi d'araignées (toiles, cocons) ou de morts-vivants (tombes ouvertes, ossements) |
| `PumpkinFields` | 3 | Champ de citrouilles clôturé de bois mort, avec épouvantail et citrouilles-lanternes |
| `Trees` | 8 | Arbres morts et arbres de pendus |
| `Decor/*` | 4 × 3 | Tas d'os, tombes isolées, nids d'araignées, carrés de citrouilles |

Les ruines varient d'une instance à l'autre grâce aux préfixes de probabilité (`70%Bloc`).

### PNJ

- `Nakasar_Halloween_Undead` (tout le fragment) : squelettes, archers, zombies, araignées, chauves-souris, corbeaux.
- `Nakasar_Halloween_Haunted` (près des structures) : spectres, goules, soldats et archimages squelettes,
  zombies aberrants, araignées des cavernes, élites et loups-garous (rares).
