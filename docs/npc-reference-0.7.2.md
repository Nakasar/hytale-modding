# Briques des rôles de PNJ (serveur Hytale 0.7.2)

Généré par `java -cp Server-0.7.2.jar mods/nakasar-mobs/tools/ValidateRoles.java --descriptors docs/npc-reference-0.7.2.md`.
`*` = obligatoire ; `(computable)` = accepte `{"Compute": "..."}`.

## Action / AdjustPosition  [Experimental]
Offsets every position in the incoming set by a fixed vector and runs its nested actions against the offset positions.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Actions*: ObjectRef <ActionList> — Actions to run against the offset positions
- Offset*: Array <Double> (computable) — The offset to apply to each incoming position

## Action / Appearance  [Stable]
Change model of NPC to given appearance.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Appearance*: Asset <Model> — Model name to use

## Action / ApplyEntityEffect  [Stable]
Applies an entity effect to the target or self
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- EntityEffect*: Asset <EntityEffect> (computable) — The entity effect to apply
- UseTarget: Boolean = true (computable) — Use the sensor-provided target for the action, self otherwise

## Action / Attack  [Experimental]
Let NPC start an attack. When an attack is running no new attack is started.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Attack: Asset <Interaction> (computable) — Attack pattern to use
- AttackType: Flag <[Primary, Secondary, Ability1, Ability2, Ability3, Ability4]> = Primary (computable) — The interaction type to use
- ChargeFor: Double = 0.0 (computable) — How long to charge for
- AttackPauseRange: Array <Double> = [0.0, 0.0] (computable) — Range of minimum pause between attacks
- AimingTimeRange: Array <Double> = [0.0, 0.0] (computable) — A range from which to pick a random value denoting the max time the NPC will wait for aiming before launching the attack.
- LineOfSight: Boolean = false — Check Line of Sight before firing
- AvoidFriendlyFire: Boolean = true — Tries to avoid friendly fire if true
- BallisticMode: Flag <[Short, Long, Alternate, Random]> = Short — Trajectory to use
- MeleeConeAngle: Double = 30.0 — Cone angle considered for on target for melee
- DamageFriendlies: Boolean = false — Whether this attack should bypass ignored damage groups and deal damage to the target
- SkipAiming: Boolean = false — Whether aiming should be skipped an the attack just executed immediately.
- ChargeDistance: Double = 0.0 (computable) — If this is a charge attack, the distance required for the charge
- InteractionVars: CodecObject <RootInteraction> — Set of interaction vars for modifying the interaction

## Action / Beacon  [Experimental]
Let the NPC send out a message to a target group of entities within a certain distance.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Message*: String (computable) — Message to send to targets
- Range: Double = 64.0 (computable) — The maximum range to send the message
- TargetGroups*: AssetArray <TagSet> (computable) — The target group(s) to send the message to
- SendTargetSlot: String (computable) — The target slot of the marked entity to send. Omit to send own position
- ExpirationTime: Double = 1.0 — The number of seconds that the message should last. -1 represents infinite time.
- SendCount: Integer = -1 — Tne number of entities to send the message to. -1 will send to all.

## Action / BlockHitInteraction  [Stable]
Iterate the BlockCollisionProvider supplied by a SensorChargeBlockCollisions and queue the configured root interaction (as InteractionType.Collision) once per hit block position.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Interaction*: Asset <Interaction> (computable) — The root interaction to run on each hit block

## Action / Crouch  [Stable]
Set NPC crouching state
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Crouch: Boolean = true (computable) — True for crouching, false for non-crouching

## Action / DelayDespawn  [Stable]
Delay the despawning cycle for some amount of time
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Time*: Double — How long to set the to delay
- Shorten: Boolean = false — Set the delay to either the current delay or the given time. Whatever is smaller.

## Action / Despawn  [Stable]
Trigger the NPC to start the despawning cycle. If the script contains a despawn sensor it will run that action/motion before removing.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Force: Boolean = false — Force the NPC to remove automatically

## Action / Die  [Stable]
Kill the NPC
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC

## Action / DisplayName  [Stable]
Set the name displayed above NPC
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- DisplayName*: String (computable) — Name to display above NPC

## Action / DropItem  [Stable]
Drop an item. Can be a specific item, or from a drop table
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Delay: Array <Double> = [1.0, 1.0] (computable) — Range of time to delay in seconds
- Item: Asset <Item> (computable) — A specific item to drop
- DropList: Asset <ItemDropList> (computable) — A reference to an item drop list
- ThrowSpeed: Double = 1.0 — The throw speed to use
- Distance: Array <Double> = [1.0, 1.0] — The range from which to pick a distance to throw the item
- DropSector: Array <Double> = [0.0, 0.0] — The sector to spread drops in relative to view direction of NPC
- PitchHigh: Boolean = false — Whether to pitch high or pitch low instead

## Action / EntityHitInteraction  [Stable]
Iterate the EntityCollisionProvider supplied by a SensorChargeEntityCollisions and queue the configured root interaction (as InteractionType.Collision) once per hit entity.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Interaction*: Asset <Interaction> (computable) — The root interaction to run on each hit entity

## Action / ForEach  [Experimental]
Runs its nested actions once per matched target/position. Requires a sensor that exposes a multi-target set.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- IsolatePerTarget: Boolean = false — Give each target (keyed by entity UUID) its own action-instance so deferred/stateful nested actions don't clobber each other across targets.
- Actions*: ObjectRef <ActionList> — Actions to run for each matched target
- MaxTargets: Integer = 16.0 (computable) — Maximum number of targets to run the actions for in a single tick
- TargetCount: Array <integer> = [-1, -1] (computable) — Pick a random number of the matched targets each tick instead of running every one.
- ClearOncePerTarget: Boolean = true (computable) — Reset Once actions between targets so they fire for every target rather than only the first

## Action / IgnoreForAvoidance  [Stable]
Set the target slot of an entity that should be ignored during avoidance
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- TargetSlot*: String (computable) — The target slot containing the entity to be ignored

## Action / Inventory  [Stable]
Add or remove a number of items from an inventory. Can also be used to equip them.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Operation: Flag <[Add, Remove, Equip, ClearHeldItem, RemoveHeldItem, SetHotbar, EquipHotbar, SetOffHand, EquipOffHand]> = Add (computable) — Operation to perform
- Count: Integer = 1.0 (computable) — Number of items to add/remove
- Item: Asset <Item> (computable) — Item type to add, remove, or equip
- UseTarget: Boolean = true (computable) — Use the sensor-provided target for the action
- Slot: Integer = 0.0 (computable) — The hotbar or off-hand slot to affect

## Action / LockOnInteractionTarget  [Stable]
Locks on to the currently iterated player in the interaction instruction
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- TargetSlot: String = LockedTarget (computable) — The target slot to use
- Rebind: Boolean = false (computable) — Whether the target slot rebinds to the entity, so it survives short reloads or role changes.

## Action / Log  [Stable]
Log a message to console.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Message*: String (computable) — Text to print to console.

## Action / MakePath  [WorkInProgress]
Constructs a transient path for the NPC based on a series of rotations and distances
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Path*: ObjectRef <Path> — A transient path definition

## Action / ModelAttachment  [Stable]
Set an attachment on the current NPC model
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Slot*: String (computable) — The attachment slot to set
- Attachment*: String (computable) — The attachment to set, or empty to remove

## Action / Nothing  [Stable]
Do nothing. Used often as placeholder.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC

## Action / Notify  [Stable]
Directly notifies a target NPC with a beacon message
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Message*: String (computable) — The message to send
- ExpirationTime: Double = 1.0 — The number of seconds that the message should last. -1 represents infinite time.
- UseTargetSlot: String — A marked target to send to instead of the target provided by a sensor. Omit to use the target provided by the sensor.

## Action / OverrideAltitude  [Stable]
Temporarily override the preferred altitude of a flying NPC. Must be refreshed each tick
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- DesiredAltitudeRange*: Array <Double> (computable) — The desired altitude range

## Action / OverrideAttitude  [Stable]
Override this NPCs attitude towards the provided target for a given duration
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Attitude*: Flag <[IGNORE, HOSTILE, NEUTRAL, FRIENDLY, REVERED]> (computable) — The attitude to set
- Duration: Double = 10.0 (computable) — The duration to override for

## Action / ParentState  [Stable]
Set the main state of NPC from within a component
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- State*: String — The alias of the external state to set, as defined by _ImportStates in parameters
- ClearHeadMotion: Boolean = true — Whether the head motion will be cleared during the state transition actions
- ClearBodyMotion: Boolean = true — Whether the body motion will be cleared during the state transition actions

## Action / PickUpItem  [Stable]
Pick up an item. In hoover mode, will match to the Item array. Otherwise, requires a target to be provided e.g. by a DroppedItemSensor
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Delay: Array <Double> = [1.0, 1.0] (computable) — Range of time to delay in seconds
- Range: Double = 1.0 (computable) — The range the item will be picked up from
- StorageTarget: Flag <[Hotbar, Inventory, Destroy]> = Hotbar (computable) — Where to prioritise putting the item
- Hoover: Boolean = false — Suck up all items in range
- Items: AssetArray <Item> (computable) — A list of glob item patterns to match

## Action / PlaceBlock  [Stable]
Place a block (chosen by another action) at a position returned by a Sensor if close enough
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Range: Double = 3.0 (computable) — The range to target position before block will be placed
- AllowEmptyMaterials: Boolean = false (computable) — Whether it should be possible to replace blocks that have empty material

## Action / PlayAnimation  [Experimental]
Play an animation
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Slot*: Flag <[Status, Action, Face]> — The animation slot to play on
- Animation: String (computable) — The animation ID to play

## Action / PlaySound  [Stable]
Plays a sound to players within a specified range.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Delay: Array <Double> = [0.0, 0.0] (computable) — Optional delay in seconds before the action fires.
- SoundEventId*: Asset <SoundEvent> (computable) — The sound event to play
- PositionSource: Flag <[Self, Sensor]> = Self — Self: play at this NPC. Sensor: play at the sensor position.

## Action / ProjectToGround  [Experimental]
Projects every position in the incoming set straight down to the top of the first solid block beneath it (dropping positions with no ground within MaxScanDown or in an unloaded chunk) and runs its nested actions against the grounded positions.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Actions*: ObjectRef <ActionList> — Actions to run against the grounded positions
- MaxScanDown: Integer = 128.0 (computable) — Maximum number of blocks to scan downward looking for ground

## Action / Random  [Stable]
Execute a single random action from a list of weighted actions.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Actions*: Array <WeightedAction> — List of possible actions

## Action / RecomputePath  [Stable]
Force recomputation of path finder solution
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC

## Action / ReleaseTarget  [Stable]
Clear locked target for NPC.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- TargetSlot: String = LockedTarget (computable) — The target slot to release

## Action / Remove  [Stable]
Erase the target entity from the world (no death animation).
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- UseTarget: Boolean = true (computable) — Use the sensor-provided target for the action

## Action / ResetBlockSensors  [Stable]
Resets a specific block sensor by name, or all block sensors by clearing the current targeted block
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- BlockSets: AssetArray <BlockSet> (computable) — The searched blocksets to reset block sensors for

## Action / ResetInstructions  [Stable]
Force reset instructionList, either by name, or as a whole
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Instructions: Array <String> = null (computable) — The instructionList to reset

## Action / ResetPath  [Stable]
Resets the current patrol path this NPC follows.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC

## Action / ResetSearchRays  [Stable]
Resets a specific search ray sensor cached position by name, or all search ray sensors
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Names: Array <String> = null (computable) — The search ray sensor ids

## Action / Role  [Stable]
Change the Role of the NPC
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Role*: Asset <Role> (computable) — The name of the Role to change to
- ChangeAppearance: Boolean = true (computable) — Whether the appearance of the new Role should be used
- State: String (computable) — State name to set
- DetachFromSpawning: Boolean = false (computable) — Whether the NPC should be removed from world-spawn population tracking and despawning after the role change

## Action / Sequence  [Stable]
Execute list of actions.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Blocking: Boolean = false — Do not execute an action unless the previous action could execute
- Atomic: Boolean = false — Only execute actions if all actions can be executed
- Actions*: ObjectRef <ActionList> — List of actions

## Action / SetAlarm  [Stable]
Set a named alarm on the NPC
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Name*: String (computable) — The name of the alarm to set
- DurationRange*: Array <TemporalAmount> (computable) — The duration range from which to pick a duration to set the alarm for

## Action / SetBlockToPlace  [Stable]
Set the block type the NPC will place
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Block*: Asset <Item> (computable) — The block item type

## Action / SetFlag  [Stable]
Set a named flag to a boolean value
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Name*: String (computable) — The name of the flag
- SetTo: Boolean = true (computable) — The value to set the flag to

## Action / SetHealthRegen  [Experimental]
Enable/Disable Health Regen
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- EnableRegen*: Boolean (computable) — Enable/disable health regeneration

## Action / SetInteractable  [Stable]
Set whether the currently iterated player in the interaction instruction should be able to interact with this NPC
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Interactable: Boolean = true (computable) — Toggle whether the currently iterated player in the interaction instruction should be able to interact with this NPC
- Hint: String — The interaction hint translation key to show for this player (e.g. 'interactionHints.trade')
- ShowPrompt: Boolean = true — Whether to show the F-key interaction prompt. Set to false for contextual-only interactions (e.g. shearing with tools). Defaults to true.

## Action / SetInvulnerable  [Stable]
Enable/disable damage invulnerability on the NPC
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Invulnerable*: Boolean (computable) — Whether the NPC should become invulnerable to damage

## Action / SetLeashPosition  [Stable]
Sets the NPCs current position to the spawn/leash position to be used with the Leash Sensor.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- ToCurrent: Boolean = false — Set to the NPCs current position.
- ToTarget: Boolean = false — Set to the target position.

## Action / SetMarkedTarget  [Stable]
Explicitly sets a marked target in a given slot.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- TargetSlot: String = LockedTarget (computable) — The target slot to set a target to.
- Rebind: Boolean = false (computable) — Whether the target slot rebinds to the entity, so it survives short reloads or role changes.

## Action / SetStat  [Stable]
Sets (or adds to) an entity stat on the NPC.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Stat*: Asset <EntityStat> (computable) — The entity stat to affect.
- Value*: Double (computable) — The value to set the stat to.
- Add: Boolean = false (computable) — Add the value to the existing value instead of setting it.

## Action / Spawn  [Experimental]
Spawn an NPC
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- SpawnDirection: Double = 0.0 (computable) — Direction of spawn cone relative to view direction (in degrees)
- SpawnAngle: Double = 360.0 (computable) — Cone width of spawn direction (in degrees)
- FanOut: Boolean = false (computable) — Fan NPCs out equally over angle
- DistanceRange: Array <Double> = [1.0, 1.0] (computable) — Distance from spawner to spawn
- CountRange: Array <integer> = [5, 5] (computable) — Number of NPCs to spawn
- DelayRange: Array <Double> = [0.25, 0.25] (computable) — Time between consecutive spawns in seconds
- Kind*: String (computable) — NPC role to spawn
- Flock: Asset <FlockAsset> (computable) — Flock definition to spawn
- LaunchAtTarget: Boolean = false (computable) — Launch the spawned NPC at target position/entity
- PitchHigh: Boolean = true (computable) — If launching at a target, use high pitch
- LaunchSpread: Double = 0.0 (computable) — The radius of the circle centred on the target within which to spread thrown NPCs
- JoinFlock: Boolean = false (computable) — Whether to join the parent NPC's flock
- SpawnState: String (computable) — An optional state to set on the spawned NPC if it exists
- SpawnSubState: String (computable) — An optional substate to set on the spawned NPC if it exists
- PositionSource: Flag <[Self, Sensor]> = Self — Where to spawn relative to: Self (the spawner) or Sensor (the matched position)

## Action / SpawnInteraction  [WorkInProgress]
Spawn an interaction at a chosen position and orientation.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Delay: Array <Double> = [0.0, 0.0] (computable) — Optional delay in seconds before the action fires.
- Interaction*: Asset <Interaction> (computable) — The root interaction to run.
- PositionSource: Flag <[Self, Sensor]> = Self — Self: spawn at the acting entity's position. Sensor: spawn at the triggering sensor's position.
- OrientationSource: Flag <[Absolute, UseOwner, UseTarget, UseSensor]> = UseOwner — How the host is oriented. Absolute uses Yaw/Pitch/Roll. UseOwner copies the acting entity's facing. UseTarget copies the TargetSlot marked target's facing. UseSensor uses the sensed position's orientation.
- TargetSlot: String = LockedTarget (computable) — The marked target slot whose facing UseTarget copies.
- Yaw: Double = 0.0 (computable) — Absolute yaw in degrees.
- Pitch: Double = 0.0 (computable) — Absolute pitch in degrees.
- Roll: Double = 0.0 (computable) — Absolute roll in degrees.
- Ttl: Double = 5.0 (computable) — Seconds before the host force-despawns if its chain has not finished.

## Action / SpawnParticles  [WorkInProgress]
Spawn particle system visible within a given range with an offset relative to npc heading
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Delay: Array <Double> = [0.0, 0.0] (computable) — Optional delay in seconds before the action fires.
- ParticleSystem*: Asset <ParticleSystem> (computable) — Particle system to spawn
- Range: Double = 75.0 (computable) — Maximum visibility range
- Scale: Double = 1.0 (computable) — Particle scale multiplier
- Offset: Array <Double> = null (computable) — Offset relative to footpoint in view direction of NPC
- TargetNodeName: String (computable) — Target node name to position particles at
- IsDetachedFromModel: Boolean = false (computable) — Whether to attach particles to the model
- PositionSource: Flag <[Self, Sensor]> = Self — Self: attach particles to this NPC's model (uses TargetNodeName/IsDetachedFromModel). Sensor: spawn a world particle at the sensor position.

## Action / State  [Stable]
Set state of NPC. The state can be queried with a sensor later on.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- State*: String — State name to set
- ClearState: Boolean = true — Clear the state of things like set once flags on transition
- ClearHeadMotion: Boolean = true — Whether the head motion will be cleared during the state transition actions
- ClearBodyMotion: Boolean = true — Whether the body motion will be cleared during the state transition actions

## Action / StorePosition  [Stable]
Store the position from the attached sensor
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Slot*: String (computable) — The slot to store the position in

## Action / Test  [Experimental]
Test action to exercise attribute evaluation (DO NOT USE)
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Boolean: Boolean = true (computable) — Boolean True
- Double: Double = 0.0 (computable) — Double 0
- Float: Double = 0.0 (computable) — Float 0
- Int: Integer = 0.0 (computable) — Int 0
- String: String = Test (computable) — String Test
- Enum: Flag <[TraceFail, TraceSuccess, TraceSensorFailures, Flock, FlockDamage, MotionControllerSteer, Collisions, BlockCollisions, ProbeBlockCollisions, ChargeState, ChargePath, MotionControllerMove, MotionControllerMoveSkipIdle, ValidatePositions, SteeringRole, DisplayState, DisplayFlock, DisplayTime, DisplayTarget, DisplayAnim, DisplayLightLevel, DisplayCustom, DisplayHP, DisplayStamina, Overlaps, NonOverlaps, Pathfinder, DisplaySpeed, DisplayFreeSlots, DisplayInternalId, DisplayName, ValidateMath, VisAvoidance, VisSeparationSummed, VisSeparation, VisSeparationTargets, VisOrientation, VisAiming, VisMarkedTargets, VisSensorRanges, VisLeashPosition, VisSteeringPre, VisSteeringPost, VisTranslation, VisFlock, VisPath, VisChargePath, VisChargeProbe, VisChargeCollisions, VisChargeEntityHits, BeaconMessages]> = Collisions (computable) — Enum RoleDebugFlags Collisions
- EnumSet: FlagSet <[TraceFail, TraceSuccess, TraceSensorFailures, Flock, FlockDamage, MotionControllerSteer, Collisions, BlockCollisions, ProbeBlockCollisions, ChargeState, ChargePath, MotionControllerMove, MotionControllerMoveSkipIdle, ValidatePositions, SteeringRole, DisplayState, DisplayFlock, DisplayTime, DisplayTarget, DisplayAnim, DisplayLightLevel, DisplayCustom, DisplayHP, DisplayStamina, Overlaps, NonOverlaps, Pathfinder, DisplaySpeed, DisplayFreeSlots, DisplayInternalId, DisplayName, ValidateMath, VisAvoidance, VisSeparationSummed, VisSeparation, VisSeparationTargets, VisOrientation, VisAiming, VisMarkedTargets, VisSensorRanges, VisLeashPosition, VisSteeringPre, VisSteeringPost, VisTranslation, VisFlock, VisPath, VisChargePath, VisChargeProbe, VisChargeCollisions, VisChargeEntityHits, BeaconMessages]> = [Flock, Collisions] (computable) — EnumSet Collisions Flock
- Asset: Asset <Model> = Sheep (computable) — Asset Sheep
- DoubleArray: Array <Double> = [1.0, 2.0] (computable) — DoubleArray [1,2] 0-10
- StringArray: Array <String> = [a, b] (computable) — StringArray [a,b] 0-10

## Action / Timeout  [Stable]
Delay an action by a time which is randomly picked between a given minimum and maximum value.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Delay: Array <Double> = [1.0, 1.0] (computable) — Range of time to delay in seconds
- DelayAfter: Boolean = false — Delay after executing the action
- Action: ObjectRef <Action> — Optional action to delay

## Action / TimerContinue  [Stable]
Continue a timer
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Name*: String (computable) — The name of the timer

## Action / TimerModify  [Stable]
Modify values of a timer
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Name*: String (computable) — The name of the timer
- AddValue: Double = 0.0 (computable) — Add value to the timer
- MaxValue: Array <Double> = [0.0, 0.0] (computable) — Set the restart value range the timer can have
- Rate: Double = 0.0 (computable) — Set the rate at which the timer will decrease
- SetValue: Double = 0.0 (computable) — Set the value of the timer
- Repeating: Boolean = false (computable) — Whether to repeat the timer when countdown finishes

## Action / TimerPause  [Stable]
Pause a timer
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Name*: String (computable) — The name of the timer

## Action / TimerRestart  [Stable]
Restart a timer. Will be set to the original initial values.
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Name*: String (computable) — The name of the timer

## Action / TimerStart  [Stable]
Start a timer
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Name*: String (computable) — The name of the timer
- StartValueRange*: Array <Double> (computable) — The range from which to pick an initial value to start at
- RestartValueRange*: Array <Double> (computable) — The range from which to pick a value when the timer is restarted
- Rate: Double = 1.0 (computable) — The rate at which the timer will decrease
- Repeating: Boolean = false (computable) — Whether to repeat the timer when countdown finishes

## Action / TimerStop  [Stable]
Stop a timer
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- Name*: String (computable) — The name of the timer

## Action / ToggleStateEvaluator  [Stable]
Enable or disable the NPC's state evaluator
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- On*: Boolean — Whether or not to enable the state evaluator

## Action / TriggerSpawners  [Stable]
Trigger all, or up to a certain number of manual spawn markers in a radius around the NPC
- Once: Boolean = false — Execute only once
- Enabled: Boolean = true (computable) — Whether this action should be enabled on the NPC
- SpawnMarker: Asset <SpawnMarker> (computable) — The spawn marker type to trigger
- Range*: Double (computable) — The range within which to trigger spawn markers
- Count: Integer = 0.0 (computable) — The number of markers to randomly trigger (0 will trigger all matching validators)
- TargetSlot: String (computable) — A target slot to place the first spawned NPC in. If omitted, no slot will be used
- Rebind: Boolean = false (computable) — Whether the target slot rebinds to the spawned entity, so it survives short reloads or role changes.

## ActionList / ActionList  [Stable]
An array of actions to be executed
- *: Array <Action> — List of actions

## BodyMotion / AimCharge  [Stable]
Aim the NPC at a target position for performing a charge based on aiming information and ensure that the charge is possible before it's executed.
- RelativeTurnSpeed: Double = 1.0 (computable) — The relative turn speed modifier

## BodyMotion / Charge  [Stable]
Aim at a target and progress through locked-on, winding up, and charging motion states.
- RelativeTurnSpeed: Double = 1.0 (computable) — Relative turn speed during Aiming, LockedOn, and InStopRange
- LockedOnToleranceAngle: Double = 15.0 (computable) — Full view cone width in degrees. The target stays locked on while aim is within half this angle on either side
- LockedOnDurationRange: Array <Double> = [5.0, 5.0] (computable) — Random LockedOn phase duration in seconds before winding up. [0, 0] skips LockedOn
- WindingUpDurationRange: Array <Double> = [5.0, 5.0] (computable) — Random WindingUp phase duration in seconds before charging. [0, 0] skips WindingUp
- PostChargeDurationRange: Array <Double> = [2.0, 2.0] (computable) — Random rest duration in seconds after Obstructed, EntityHit, Knockback, or Finished
- WindingUpUninterruptable: Boolean = true (computable) — When true, WindingUp is not interrupted by target loss or aim drift
- WindingUpRelativeTurnSpeed: Double = 1.0 (computable) — Relative turn speed during WindingUp. Can be 0 to disable rotation in that phase
- ChargeRelativeSpeed: Double = 5.0 (computable) — Charge speed as a multiple of the motion controller maximum speed. Set to 0 when ChargeAbsoluteSpeed is used
- ChargeDistanceRange*: Array <Double> (computable) — Random maximum charge travel distance in blocks. Also caps travel distance in target charge modes. Targets farther than this are out of charge range
- ChargeDistanceMode: Flag <[MaxRange, TargetDist, TargetMaxColliderDist, TargetMinColliderDist, TargetMidColliderDist]> = MaxRange (computable) — How the charge travel distance is selected. Target modes use TargetDistanceRange. MaxRange ignores it
- TargetDistanceRange: Array <Double> = [0.0, 0.0] (computable) — Stop distance from the target for target charge modes. Positive stops short of the target. Negative stops past it. Unused when ChargeDistanceMode is MaxRange
- IgnoredBlockSet: Asset <BlockSet> (computable) — Blocks in this set are ignored by charge probes. The probe treats them as non-colliding and breathable for every breathing mode
- ProbeRelaxedConstraints: FlagSet <[WADE, DAMAGE, DROP, BREATHE, FENCE]> = [] (computable) — Constraints to relax during charge reachability probes. Wade allows liquid entry. Breathe allows entry into suffocating blocks
- ClearOnceOnStateChange: Boolean = true (computable) — When true, resets Once flags on the parent instruction whenever the charge state changes, so Once sensors can fire again for the new state
- ChargeAbsoluteSpeed: Double = 0.0 (computable) — Charge speed in blocks/s. Set to 0 to use ChargeRelativeSpeed instead. Exactly one of ChargeAbsoluteSpeed and ChargeRelativeSpeed must be non-zero
- ChargeAccelerationDistance: Double = 3.0 (computable) — Configured acceleration distance in blocks. The zone shrinks proportionally when acceleration and deceleration distances exceed charge travel distance. 0 disables acceleration
- ChargeAccelerationMinimumRelativeSpeed: Double = 0.15 (computable) — Minimum relative speed at the slow end of acceleration. 0 starts from a standstill. VelocityOverTime remaps the curve above this speed. DistanceOverTime uses it as the slow-end slope ratio
- ChargeAccelerationCurveMode: Flag <[VelocityOverTime, DistanceOverTime]> = DistanceOverTime (computable) — How to read the acceleration curve. VelocityOverTime reads it as the relative speed. DistanceOverTime reads it as the fraction of the acceleration distance covered
- ChargeAccelerationHalfTimeValue: Double = 0.5 (computable) — Controls the acceleration curve at half phase time. VelocityOverTime uses the underlying curve value before minimum-speed remapping. In DistanceOverTime, half the phase covers half this value of the acceleration distance. Values must be greater than 0 and less than 1
- ChargeAccelerationHalfTimeSteepness: Double = -1.0 (computable) — Normalized steepness at the underlying acceleration curve midpoint. Values from 0 to 1 map from flat to steep. Negative values use the harmonic mean. VelocityOverTime minimum-speed remapping can shift when this midpoint is sampled
- ChargeAccelerationEndSteepness: Double = -1.0 (computable) — Steepness of the acceleration curve at its fast end, which is the end of the phase. Values from 0 to 1 map from flat to steep. Negative values use the default. Only used in DistanceOverTime mode
- ChargeDecelerationDistance: Double = 3.0 (computable) — Configured deceleration distance in blocks. The zone shrinks proportionally when acceleration and deceleration distances exceed charge travel distance. 0 disables deceleration
- ChargeDecelerationMinimumRelativeSpeed: Double = 0.15 (computable) — Minimum relative speed at the slow end of deceleration. The NPC stops from this speed. 0 eases to a standstill. VelocityOverTime remaps the curve above this speed. DistanceOverTime uses it as the slow-end slope ratio
- ChargeDecelerationCurveMode: Flag <[VelocityOverTime, DistanceOverTime]> = DistanceOverTime (computable) — How to read the deceleration curve. VelocityOverTime reads it as the relative speed. DistanceOverTime reads it as the fraction of the deceleration distance still to cover
- ChargeDecelerationHalfTimeValue: Double = 0.5 (computable) — Controls the deceleration curve at half phase time. VelocityOverTime uses the underlying curve value before minimum-speed remapping. In DistanceOverTime, half the phase leaves half this value of the deceleration distance. Values must be greater than 0 and less than 1
- ChargeDecelerationHalfTimeSteepness: Double = -1.0 (computable) — Normalized steepness at the underlying deceleration curve midpoint. Values from 0 to 1 map from flat to steep. Negative values use the harmonic mean. VelocityOverTime minimum-speed remapping can shift when this midpoint is sampled
- ChargeDecelerationEndSteepness: Double = -1.0 (computable) — Steepness of the deceleration curve at its fast end, which is the start of the phase. Values from 0 to 1 map from flat to steep. Negative values use the default. Only used in DistanceOverTime mode
- IgnoredBlockSetTriggers: Boolean = false (computable) — When true, blocks in IgnoredBlockSet still fire trigger/damage interactions during the rail step
- EntityStopsCharge: Boolean = false (computable) — When true, the first entity (player or NPC) hit during the rail step clamps the charge and transitions to EntityHit. When false, entity hits are reported without stopping the charge
- BlockCollisionInteraction: Asset <Interaction> (computable) — Optional interaction queued for each pass-through block reported while charging
- NPCCollisionInteraction: Asset <Interaction> (computable) — Optional interaction queued for each accepted NPC collision during charging
- PlayerCollisionInteraction: Asset <Interaction> (computable) — Optional interaction queued for each accepted player collision during charging
- RepeatCollisionIgnoreDuration: Double = 0.2 (computable) — Duration in seconds for which repeated hits on the same entity are ignored by NPC and player collision interactions and SensorChargeEntityCollisions
- ClimbSlope: Double = 2.0 (computable) — Horizontal blocks per vertical block when smoothing CLIMB segments along the charge path. 0 disables climb smoothing. Otherwise, the climb starts as far back from the edge as this value allows. For example, 2 means two horizontal blocks per vertical block. The actual slope can become steeper but never shallower
- DropSlope: Double = 2.0 (computable) — Horizontal blocks per vertical block when smoothing DROP segments along the charge path. 0 disables drop smoothing. Otherwise, the drop lands as far past the edge as this value allows. The actual slope can become steeper but never shallower
- HorizontalSkipGapWidth: Double = 1.2 (computable) — Maximum horizontal run length in blocks for collapsing a same-height drop and climb dip. 0 disables dip collapsing. ClimbSlope and DropSlope control slope smoothing
- KnockbackThreshold: Double = 0.0 (computable) — Threshold for combined external velocity magnitude while Charging. Values below it are cleared. Values at or above it transition the charge to Knockback
- ProbeChargeRecomputeDistance: Double = 0.0 (computable) — Interval in blocks for re-validating a 2D walk path during Charging. Positive values set the interval. Values at or below 0 disable re-validation
- ProbeMinFrequency: Integer = 2.0 (computable) — Minimum reachability probe rate in probes per second. Probes at least this often. 0 forces a probe every tick and overrides ProbeMaxFrequency
- ProbeMaxFrequency: Integer = 10.0 (computable) — Maximum reachability probe rate in probes per second. ProbeMinFrequency 0 overrides this limit. 0 means every tick and requires ProbeMinFrequency to be 0
- ProbeMinDirectionChange: Double = 5.0 (computable) — Minimum angular change to target in degrees required before executing another reachability test

## BodyMotion / Flee  [Experimental]
Move away from a target using path finding or steering
- RelativeSpeed: Double = 1.0 (computable) — Maximum relative speed the NPC should move
- RelativeSpeedWaypoint: Double = 0.5 (computable) — Maximum relative speed the NPC should move close to waypoints
- WaypointRadius: Double = 0.5 (computable) — Radius to slow down around waypoints
- UseBestPath: Boolean = true (computable) — Use best partial path if goal can't be reached
- ThrottleDelayRange: Array <Double> = [3.0, 5.0] (computable) — Time to delay after no path finding solution found
- ThrottleIgnoreCount: Integer = 3.0 (computable) — How often no valid path solution can be found before throttling delay is applied
- BuildOptimisedPath: Boolean = true (computable) — Try to reduce number of nodes of generated path
- AvoidBlockDamage: Boolean = true (computable) — Should avoid environmental damage from blocks
- RelaxedMoveConstraints: Boolean = true (computable) — NPC can do movements like wading (depends on motion controller type)
- RelaxedConstraints: FlagSet <[WADE, DAMAGE, DROP, BREATHE, FENCE]> = [] (computable) — List of constraints to relax for this motion (new mode; empty = no relaxed constraints)
- BlendHeading: Double = 0.5 (computable) — Relative rotation angle into next waypoint when arriving at current waypoint
- PathSmoothing: Integer = 2.0 (computable) — Try to smooth followed path. Larger values smooth more.
- RejectionWeight: Double = 3.0 (computable) — Weight of rejection vector pushing entity closer to original path
- UseSteering: Boolean = true (computable) — Use simple/cheap steering if available
- SkipSteering: Boolean = true (computable) — Skip steering if target not reachable
- UsePathfinder: Boolean = true (computable) — Use path finder
- MinPathLength: Double = 2.0 (computable) — Minimum length of path required when not able to reach target (should be greater equal 2)
- DiagonalMoves: Boolean = true (computable) — Allow diagonal moves
- StepsPerTick: Integer = 50.0 (computable) — Steps per iteration
- MaxPathLength: Integer = 200.0 (computable) — Max path steps before aborting path finding
- MaxOpenNodes: Integer = 200.0 (computable) — Max open nodes before aborting path finding
- MaxTotalNodes: Integer = 900.0 (computable) — Max total node before aborting path finding
- Debug: String — Debugging flags
- DesiredAltitudeWeight: Double = -1.0 (computable) — How much this NPC prefers being within the desired height range
- WaitDistance: Double = 1.0 (computable) — Minimum distance target needs to move before recomputing path when no path can be found
- RecomputeDistance: Double = 10.0 (computable) — Maximum distance target can move before path is recomputed or 0 to supress recomputation
- ReprojectDistance: Double = 0.5 (computable) — Maximum distance target can move before position is reprojected
- AdjustRangeByHitboxSize: Boolean = false (computable) — Correct range by hitbox sizes of involved entities
- RecomputeConeAngle: Double = 0.0 (computable) — Recompute path when target leaves cone from initial position to target
- SlowDownDistance: Double = 8.0 (computable) — Distance from target when NPC should start to slowdown
- StopDistance: Double = 10.0 (computable) — Distance from target when NPC should halt
- Falloff: Double = 3.0 (computable) — Rate how fast the slowdown should happen relative to distance
- HoldDirectionTimeRange: Array <Double> = [2.0, 5.0] (computable) — How often to change heading
- ChangeDirectionViewSector: Double = 230.0 (computable) — The view sector the NPC uses to decide if it should switch direction
- DirectionJitter: Double = 45.0 (computable) — How much jitter in degrees to add to the heading the NPC uses
- ErraticDistance: Double = 4.0 (computable) — If the player is closer than this distance, the NPC will behave more erratically using the additional jitter parameter
- ErraticExtraJitter: Double = 45.0 (computable) — Extra jitter to add to the NPC heading on top of the standard when the target is too close
- ErraticChangeDurationMultiplier: Double = 0.5 (computable) — A multiplier to decrease the duration between direction changes when the target is too close

## BodyMotion / Land  [Experimental]
Try to land at the given position using a seek like motion
- RelativeSpeed: Double = 1.0 (computable) — Maximum relative speed the NPC should move
- RelativeSpeedWaypoint: Double = 0.5 (computable) — Maximum relative speed the NPC should move close to waypoints
- WaypointRadius: Double = 0.5 (computable) — Radius to slow down around waypoints
- UseBestPath: Boolean = true (computable) — Use best partial path if goal can't be reached
- ThrottleDelayRange: Array <Double> = [3.0, 5.0] (computable) — Time to delay after no path finding solution found
- ThrottleIgnoreCount: Integer = 3.0 (computable) — How often no valid path solution can be found before throttling delay is applied
- BuildOptimisedPath: Boolean = true (computable) — Try to reduce number of nodes of generated path
- AvoidBlockDamage: Boolean = true (computable) — Should avoid environmental damage from blocks
- RelaxedMoveConstraints: Boolean = true (computable) — NPC can do movements like wading (depends on motion controller type)
- RelaxedConstraints: FlagSet <[WADE, DAMAGE, DROP, BREATHE, FENCE]> = [] (computable) — List of constraints to relax for this motion (new mode; empty = no relaxed constraints)
- BlendHeading: Double = 0.5 (computable) — Relative rotation angle into next waypoint when arriving at current waypoint
- PathSmoothing: Integer = 2.0 (computable) — Try to smooth followed path. Larger values smooth more.
- RejectionWeight: Double = 3.0 (computable) — Weight of rejection vector pushing entity closer to original path
- UseSteering: Boolean = true (computable) — Use simple/cheap steering if available
- SkipSteering: Boolean = true (computable) — Skip steering if target not reachable
- UsePathfinder: Boolean = true (computable) — Use path finder
- MinPathLength: Double = 2.0 (computable) — Minimum length of path required when not able to reach target (should be greater equal 2)
- DiagonalMoves: Boolean = true (computable) — Allow diagonal moves
- StepsPerTick: Integer = 50.0 (computable) — Steps per iteration
- MaxPathLength: Integer = 200.0 (computable) — Max path steps before aborting path finding
- MaxOpenNodes: Integer = 200.0 (computable) — Max open nodes before aborting path finding
- MaxTotalNodes: Integer = 900.0 (computable) — Max total node before aborting path finding
- Debug: String — Debugging flags
- DesiredAltitudeWeight: Double = -1.0 (computable) — How much this NPC prefers being within the desired height range
- WaitDistance: Double = 1.0 (computable) — Minimum distance target needs to move before recomputing path when no path can be found
- RecomputeDistance: Double = 10.0 (computable) — Maximum distance target can move before path is recomputed or 0 to supress recomputation
- ReprojectDistance: Double = 0.5 (computable) — Maximum distance target can move before position is reprojected
- AdjustRangeByHitboxSize: Boolean = false (computable) — Correct range by hitbox sizes of involved entities
- RecomputeConeAngle: Double = 0.0 (computable) — Recompute path when target leaves cone from initial position to target
- Reachable: Boolean = false (computable) — Target must be reachable so that hitboxes can overlap
- HeightDifference: Array <Double> = [-1.0, 1.0] (computable) — Height difference allowed to target
- SlowDownDistance: Double = 8.0 (computable) — Distance when to slow down when approaching
- StopDistance: Double = 10.0 (computable) — Distance to stop at
- AbortDistance: Double = 96.0 (computable) — Distance to abort behaviour
- Falloff: Double = 3.0 (computable) — Deceleration when approaching target
- SwitchToSteeringDistance: Double = 20.0 (computable) — Distance below NPC can test if target is reachable and abort existing path
- GoalLenience: Double = 2.0 (computable) — The distance from the target landing point that is acceptable to land at

## BodyMotion / Leave  [Experimental]
Get away from current position using path finding
- RelativeSpeed: Double = 1.0 (computable) — Maximum relative speed the NPC should move
- RelativeSpeedWaypoint: Double = 0.5 (computable) — Maximum relative speed the NPC should move close to waypoints
- WaypointRadius: Double = 0.5 (computable) — Radius to slow down around waypoints
- UseBestPath: Boolean = true (computable) — Use best partial path if goal can't be reached
- ThrottleDelayRange: Array <Double> = [3.0, 5.0] (computable) — Time to delay after no path finding solution found
- ThrottleIgnoreCount: Integer = 3.0 (computable) — How often no valid path solution can be found before throttling delay is applied
- BuildOptimisedPath: Boolean = true (computable) — Try to reduce number of nodes of generated path
- AvoidBlockDamage: Boolean = true (computable) — Should avoid environmental damage from blocks
- RelaxedMoveConstraints: Boolean = true (computable) — NPC can do movements like wading (depends on motion controller type)
- RelaxedConstraints: FlagSet <[WADE, DAMAGE, DROP, BREATHE, FENCE]> = [] (computable) — List of constraints to relax for this motion (new mode; empty = no relaxed constraints)
- BlendHeading: Double = 0.5 (computable) — Relative rotation angle into next waypoint when arriving at current waypoint
- PathSmoothing: Integer = 2.0 (computable) — Try to smooth followed path. Larger values smooth more.
- RejectionWeight: Double = 3.0 (computable) — Weight of rejection vector pushing entity closer to original path
- MinPathLength: Double = 2.0 (computable) — Minimum length of path required when not able to reach target (should be greater equal 2)
- DiagonalMoves: Boolean = true (computable) — Allow diagonal moves
- StepsPerTick: Integer = 50.0 (computable) — Steps per iteration
- MaxPathLength: Integer = 200.0 (computable) — Max path steps before aborting path finding
- MaxOpenNodes: Integer = 200.0 (computable) — Max open nodes before aborting path finding
- MaxTotalNodes: Integer = 900.0 (computable) — Max total node before aborting path finding
- Debug: String — Debugging flags
- DesiredAltitudeWeight: Double = -1.0 (computable) — How much this NPC prefers being within the desired height range
- Distance*: Double (computable) — Minimum distance required

## BodyMotion / MaintainDistance  [Stable]
Maintain distance from a given position
- DesiredDistanceRange*: Array <Double> (computable) — The desired distance to remain at.
- TargetDistanceFactor: Double = 0.5 (computable) — A factor used to decide what distance to move to within the target range.
- MoveThreshold: Double = 1.0 (computable) — An extra threshold distance on either side of the desired range before the NPC will trigger movement.
- RelativeForwardsSpeed: Double = 1.0 (computable) — Maximum relative speed for the NPC moving forwards
- RelativeBackwardsSpeed: Double = 1.0 (computable) — Maximum relative speed for the NPC moving backwards
- MoveTowardsSlowdownThreshold: Double = 2.0 (computable) — The distance away from the target stopping point at which the NPC will start to slow down while moving towards the target
- StrafingDurationRange: Array <Double> = [0.0, 0.0] (computable) — How long to strafe for.
- StrafingFrequencyRange: Array <Double> = [2.0, 2.0] (computable) — How frequently to execute strafing

## BodyMotion / MatchLook  [Stable]
Make NPC body rotate to match look direction

## BodyMotion / Nothing  [Stable]
Do nothing

## BodyMotion / Path  [Stable]
Walk along a path.
- StartAtNearestNode: Boolean = true — Start at closest warp point
- PathWidth: Double = 0.0 — Walking corridor width
- NodeWidth: Double = 0.2 — Radius of warp point node
- MinRelSpeed: Double = 0.5 — Minimum relative walk speed
- MaxRelSpeed: Double = 0.5 — Maximum relative walk speed
- MinWalkDistance: Double = 0.0 — Minimum walk distance when PathWidth greater 0
- MaxWalkDistance: Double = 0.0 — Maximum walk distance when PathWidth greater 0
- Direction: Flag <[FORWARD, BACKWARD, RANDOM, ANY]> = FORWARD — Walking direction relative to order of nodes
- Shape: Flag <[LINE, LOOP, POINTS, CHAIN]> = LOOP (computable) — Shape of Path
- MinNodeDelay: Double = 0.0 — Minimum resting time at a node
- MaxNodeDelay: Double = 0.0 — Maximum resting time at a node
- UseNodeViewDirection: Boolean = false — Look into next node direction at node
- NodePauseScaleRange: Array <Double> = [0.2, 0.4] (computable) — The range from which to pick a value that defines the portion of the total node pause time that should be spent facing a direction before turning
- NodePauseExtraPercentRange: Array <Double> = [0.0, 0.2] (computable) — A range from which to pick the additional percentage of the directional pause time to add to it
- PickRandomAngle: Boolean = false — Whether to sweep left and right using the observation angle, or pick a random angle within the sector each time
- ViewSegments: Integer = 1.0 (computable) — The number of distinct segments to stop at when sweeping from left to right using the observation angle

## BodyMotion / Seek  [Experimental]
Move towards a target using path finding or steering
- RelativeSpeed: Double = 1.0 (computable) — Maximum relative speed the NPC should move
- RelativeSpeedWaypoint: Double = 0.5 (computable) — Maximum relative speed the NPC should move close to waypoints
- WaypointRadius: Double = 0.5 (computable) — Radius to slow down around waypoints
- UseBestPath: Boolean = true (computable) — Use best partial path if goal can't be reached
- ThrottleDelayRange: Array <Double> = [3.0, 5.0] (computable) — Time to delay after no path finding solution found
- ThrottleIgnoreCount: Integer = 3.0 (computable) — How often no valid path solution can be found before throttling delay is applied
- BuildOptimisedPath: Boolean = true (computable) — Try to reduce number of nodes of generated path
- AvoidBlockDamage: Boolean = true (computable) — Should avoid environmental damage from blocks
- RelaxedMoveConstraints: Boolean = true (computable) — NPC can do movements like wading (depends on motion controller type)
- RelaxedConstraints: FlagSet <[WADE, DAMAGE, DROP, BREATHE, FENCE]> = [] (computable) — List of constraints to relax for this motion (new mode; empty = no relaxed constraints)
- BlendHeading: Double = 0.5 (computable) — Relative rotation angle into next waypoint when arriving at current waypoint
- PathSmoothing: Integer = 2.0 (computable) — Try to smooth followed path. Larger values smooth more.
- RejectionWeight: Double = 3.0 (computable) — Weight of rejection vector pushing entity closer to original path
- UseSteering: Boolean = true (computable) — Use simple/cheap steering if available
- SkipSteering: Boolean = true (computable) — Skip steering if target not reachable
- UsePathfinder: Boolean = true (computable) — Use path finder
- MinPathLength: Double = 2.0 (computable) — Minimum length of path required when not able to reach target (should be greater equal 2)
- DiagonalMoves: Boolean = true (computable) — Allow diagonal moves
- StepsPerTick: Integer = 50.0 (computable) — Steps per iteration
- MaxPathLength: Integer = 200.0 (computable) — Max path steps before aborting path finding
- MaxOpenNodes: Integer = 200.0 (computable) — Max open nodes before aborting path finding
- MaxTotalNodes: Integer = 900.0 (computable) — Max total node before aborting path finding
- Debug: String — Debugging flags
- DesiredAltitudeWeight: Double = -1.0 (computable) — How much this NPC prefers being within the desired height range
- WaitDistance: Double = 1.0 (computable) — Minimum distance target needs to move before recomputing path when no path can be found
- RecomputeDistance: Double = 10.0 (computable) — Maximum distance target can move before path is recomputed or 0 to supress recomputation
- ReprojectDistance: Double = 0.5 (computable) — Maximum distance target can move before position is reprojected
- AdjustRangeByHitboxSize: Boolean = false (computable) — Correct range by hitbox sizes of involved entities
- RecomputeConeAngle: Double = 0.0 (computable) — Recompute path when target leaves cone from initial position to target
- Reachable: Boolean = false (computable) — Target must be reachable so that hitboxes can overlap
- HeightDifference: Array <Double> = [-1.0, 1.0] (computable) — Height difference allowed to target
- SlowDownDistance: Double = 8.0 (computable) — Distance when to slow down when approaching
- StopDistance: Double = 10.0 (computable) — Distance to stop at
- AbortDistance: Double = 96.0 (computable) — Distance to abort behaviour
- Falloff: Double = 3.0 (computable) — Deceleration when approaching target
- SwitchToSteeringDistance: Double = 20.0 (computable) — Distance below NPC can test if target is reachable and abort existing path

## BodyMotion / Sequence  [Stable]
Sequence of motions. Can be used in conjunction with 'Timer' to model more complex motions.
- Looped: Boolean = true — When true restart after last motion is finished
- RestartOnActivate: Boolean = false — Restart from first motion when NPC is activated.
- Motions*: Array <BodyMotion> — Array of motions

## BodyMotion / TakeOff  [Experimental]
Switch NPC from walking to flying motion controller
- JumpSpeed: Double = 0.0 — Speed to jump off

## BodyMotion / Teleport  [Experimental]
Teleport NPC to a position given by a sensor or to a random position nearby with an optional minimum offset up to a maximum offset
- OffsetRange: Array <Double> = [0.0, 0.0] — The minimum and maximum offset the NPC can be spawned from the target position
- MaxYOffset: Double = 5.0 — Maximum vertical offset from the target position in case of terrain obstacles
- OffsetSector: Double = 0.0 — The sector around the target in which to teleport to
- Orientation: Flag <[Unchanged, TowardsTarget, UseTarget]> = Unchanged — The direction to face after teleporting

## BodyMotion / TestProbe  [Experimental]
Debugging - Test probing
- AdjustX: Double = -1.0 — X block position adjustment
- AdjustZ: Double = -1.0 — Y block position adjustment
- AdjustDistance: Double = -1.0 — Set probe direction length for debugging
- SnapAngle: Double = -1.0 — Snap angle to multiples of value for debugging
- AvoidBlockDamage: Boolean = true — Should avoid environmental damage from blocks
- RelaxedMoveConstraints: Boolean = false — NPC can do movements like wading (depends on motion controller type)
- RelaxedConstraints: FlagSet <[WADE, DAMAGE, DROP, BREATHE, FENCE]> = [] — List of constraints to relax for this motion (new mode; empty = no relaxed constraints)

## BodyMotion / Timer  [Stable]
Execute a Motion for a specific maximum time. If the motion finishes earlier the Timer also finishes.
- Time: Array <Double> = [1.0, 1.0] (computable) — Range of time from which the random timer length can be chosen
- Motion*: ObjectRef <BodyMotion> — Motion to execute

## BodyMotion / Wander  [Stable]
Random movement in short linear pieces.
- MinWalkTime: Double = 2.0 (computable) — Minimum time to wander for a segment.
- MaxWalkTime: Double = 4.0 (computable) — Maximum time to wander for a segment.
- MinHeadingChange: Double = 0.0 (computable) — Approximate minimum heading change between segments
- MaxHeadingChange: Double = 90.0 (computable) — Approximate maximum heading change between segments
- RelaxHeadingChange: Boolean = true (computable) — Allow other directions when preferred directions blocked
- RelativeSpeed: Double = 0.5 (computable) — Relative wander speed
- MinMoveDistance: Double = 0.5 (computable) — Minimum distance to move in a segment
- StopDistance: Double = 0.5 (computable) — Distance to stop at target
- TestsPerTick: Integer = 1.0 (computable) — Direction tests per tick
- AvoidBlockDamage: Boolean = true (computable) — Should avoid environmental damage from blocks
- RelaxedMoveConstraints: Boolean = false (computable) — NPC can do movements like wading (depends on motion controller type)
- RelaxedConstraints: FlagSet <[WADE, DAMAGE, DROP, BREATHE, FENCE]> = [] (computable) — List of constraints to relax for this motion (new mode; empty = no relaxed constraints)
- DesiredAltitudeWeight: Double = -1.0 (computable) — How much this NPC prefers being within the desired height range

## BodyMotion / WanderInCircle  [Stable]
Random movement in short linear pieces inside circle around spawn position.
- MinWalkTime: Double = 2.0 (computable) — Minimum time to wander for a segment.
- MaxWalkTime: Double = 4.0 (computable) — Maximum time to wander for a segment.
- MinHeadingChange: Double = 0.0 (computable) — Approximate minimum heading change between segments
- MaxHeadingChange: Double = 90.0 (computable) — Approximate maximum heading change between segments
- RelaxHeadingChange: Boolean = true (computable) — Allow other directions when preferred directions blocked
- RelativeSpeed: Double = 0.5 (computable) — Relative wander speed
- MinMoveDistance: Double = 0.5 (computable) — Minimum distance to move in a segment
- StopDistance: Double = 0.5 (computable) — Distance to stop at target
- TestsPerTick: Integer = 1.0 (computable) — Direction tests per tick
- AvoidBlockDamage: Boolean = true (computable) — Should avoid environmental damage from blocks
- RelaxedMoveConstraints: Boolean = false (computable) — NPC can do movements like wading (depends on motion controller type)
- RelaxedConstraints: FlagSet <[WADE, DAMAGE, DROP, BREATHE, FENCE]> = [] (computable) — List of constraints to relax for this motion (new mode; empty = no relaxed constraints)
- DesiredAltitudeWeight: Double = -1.0 (computable) — How much this NPC prefers being within the desired height range
- Radius: Double = 10.0 (computable) — Radius of circle to wander in
- Flock: Boolean = false — Do not use
- UseSphere: Boolean = false — Use sphere

## BodyMotion / WanderInRect  [Stable]
Random movement in short linear pieces inside rectangle around spawn position.
- MinWalkTime: Double = 2.0 (computable) — Minimum time to wander for a segment.
- MaxWalkTime: Double = 4.0 (computable) — Maximum time to wander for a segment.
- MinHeadingChange: Double = 0.0 (computable) — Approximate minimum heading change between segments
- MaxHeadingChange: Double = 90.0 (computable) — Approximate maximum heading change between segments
- RelaxHeadingChange: Boolean = true (computable) — Allow other directions when preferred directions blocked
- RelativeSpeed: Double = 0.5 (computable) — Relative wander speed
- MinMoveDistance: Double = 0.5 (computable) — Minimum distance to move in a segment
- StopDistance: Double = 0.5 (computable) — Distance to stop at target
- TestsPerTick: Integer = 1.0 (computable) — Direction tests per tick
- AvoidBlockDamage: Boolean = true (computable) — Should avoid environmental damage from blocks
- RelaxedMoveConstraints: Boolean = false (computable) — NPC can do movements like wading (depends on motion controller type)
- RelaxedConstraints: FlagSet <[WADE, DAMAGE, DROP, BREATHE, FENCE]> = [] (computable) — List of constraints to relax for this motion (new mode; empty = no relaxed constraints)
- DesiredAltitudeWeight: Double = -1.0 (computable) — How much this NPC prefers being within the desired height range
- Width: Double = 10.0 — Rectangle width
- Depth: Double = 10.0 — Rectangle depth

## HashMap / HashMap  [Stable]
Non-empty list of motion controllers.
- *: Array <MotionController> — List of motion controllers

## HeadMotion / Aim  [Stable]
Aim at target considering weapon in hand.
- Spread: Double = 1.0 (computable) — Random targeting error
- HitProbability: Double = 0.33 (computable) — Probability of shot being straight on target
- Deflection: Boolean = false (computable) — Compute deflection for moving targets
- RelativeTurnSpeed: Double = 1.0 (computable) — The relative turn speed modifier

## HeadMotion / Nothing  [Stable]
Do nothing

## HeadMotion / Observe  [Stable]
Observe surroundings in various ways. This includes looking in random directions within an angle, or sweeping the head left and right, etc. Angles are relative to body angle at any given time.
- AngleRange*: Array <Double> (computable) — The angle range to observe in degrees
- PauseTimeRange: Array <Double> = [2.0, 2.0] (computable) — How long to continue looking in a given direction
- PickRandomAngle: Boolean = false (computable) — Whether to pick random angles within the range
- ViewSegments: Integer = 1.0 (computable) — The number of distinct segments to stop at when sweeping from left to right
- RelativeTurnSpeed: Double = 1.0 (computable) — The relative turn speed modifier

## HeadMotion / Rotate  [Stable]
Turn the head continuously at a fixed speed. The head stops at the head yaw limit of the model and pushes the body around from there. To turn the whole NPC smoothly, combine this with a body motion that follows the head, such as MatchLook.
- RotationSpeed*: Double (computable) — The turn speed in degrees per second
- ClearPitch: Boolean = true (computable) — Whether to clear the head pitch while turning

## HeadMotion / Sequence  [Stable]
Sequence of motions. Can be used in conjunction with 'Timer' to model more complex motions.
- Looped: Boolean = true — When true restart after last motion is finished
- RestartOnActivate: Boolean = false — Restart from first motion when NPC is activated.
- Motions*: Array <HeadMotion> — Array of motions

## HeadMotion / Timer  [Stable]
Execute a Motion for a specific maximum time. If the motion finishes earlier the Timer also finishes.
- Time: Array <Double> = [1.0, 1.0] (computable) — Range of time from which the random timer length can be chosen
- Motion*: ObjectRef <HeadMotion> — Motion to execute

## HeadMotion / Watch  [Stable]
Rotate to target.
- RelativeTurnSpeed: Double = 1.0 (computable) — The relative turn speed modifier

## IEntityFilter / Altitude  [Stable]
Matches targets if they're within the defined range above the ground
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- AltitudeRange*: Array <Double> (computable) — The range above the ground to match

## IEntityFilter / And  [Stable]
Logical AND of a list of filters
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- Filters*: Array <IEntityFilter> — List of filters

## IEntityFilter / Attitude  [Stable]
Matches the attitude towards the locked target
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- Attitudes*: FlagSet <[IGNORE, HOSTILE, NEUTRAL, FRIENDLY, REVERED]> (computable) — The attitudes to match

## IEntityFilter / Combat  [Stable]
Check the target's combat state. This includes whether they're attacking at all, if they're using a particular attack, etc
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- Sequence: Asset <Interaction> (computable) — The attack ID to check for.
- TimeElapsedRange: Array <Double> = [0.0, 3.4028234663852886E38] (computable) — The acceptable elapsed time range in seconds.
- Mode: Flag <[Sequence, Charging, Attacking, Melee, Ranged, Blocking, Any, None]> = Attacking (computable) — Type of combat to trigger on

## IEntityFilter / EntityEffect  [Stable]
Check whether an entity has a specific entity effect
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- EffectId*: Asset <EntityEffect> (computable) — The entity effect to check for.

## IEntityFilter / HeightDifference  [Stable]
Matches entities within the given height range
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- HeightDifference: Array <Double> = [-1.7976931348623157E308, 1.7976931348623157E308] (computable) — The height range to test entities in
- UseEyePosition: Boolean = true (computable) — Use eye position for height difference checks

## IEntityFilter / InsideBlock  [Stable]
Matches if the entity is inside any of the blocks in the BlockSet
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- BlockSet*: Asset <BlockSet> (computable) — The BlockSet to match against

## IEntityFilter / Inventory  [Stable]
Test various conditions relating to entity inventory. This includes whether it contains a specific item, item count, and free slots
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- Items: AssetArray <Item> = [*] (computable) — A list of glob item patterns to match
- CountRange: Array <integer> = [1, 2147483647] (computable) — The range of number of items that need to match the patterns
- FreeSlotRange: Array <integer> = [0, 2147483647] (computable) — The range designating the number of required free slots

## IEntityFilter / IsDead  [Stable]
Matches when the entity is dead.
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled

## IEntityFilter / IsExecutingInteraction  [Stable]
Matches when the entity is executing an interaction.
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled

## IEntityFilter / ItemInHand  [Stable]
Check if entity is holding an item
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- Items*: AssetArray <Item> (computable) — A list of glob item patterns to match
- Hand: Flag <[Main, OffHand, Both]> = Both (computable) — Which hand to check

## IEntityFilter / LineOfSight  [Stable]
Matches if there is line of sight to the target
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled

## IEntityFilter / MovementState  [Stable]
Check if the entity is in the given movement state
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- State*: Flag <[JUMPING, FLYING, CROUCHING, RUNNING, SPRINTING, FALLING, CLIMBING, WALKING, IDLE, ANY]> — The movement state to check

## IEntityFilter / NPCGroup  [Stable]
Returns whether the entity matches one of the provided NPCGroups
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- IncludeGroups: AssetArray <TagSet> (computable) — A set of NPCGroups to include in the match
- ExcludeGroups: AssetArray <TagSet> (computable) — A set of NPCGroups to exclude from the match

## IEntityFilter / Not  [WorkInProgress]
Invert filter test
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- Filter*: ObjectRef <IEntityFilter> — Filter to test

## IEntityFilter / Or  [Stable]
Logical OR of a list of filters
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- Filters*: Array <IEntityFilter> — List of filters

## IEntityFilter / SpotsMe  [Stable]
Checks if the entity can view the NPC in a given view sector or cone and without obstruction.
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- ViewAngle: Double = 90.0 — Angle used for view sector and view cone test
- ViewTest: Flag <[NONE, VIEW_SECTOR, VIEW_CONE]> = VIEW_SECTOR — Check if the entity is in the view cone, view sector, or neither
- TestLineOfSight: Boolean = true — Check if view to the npc is not obstructed

## IEntityFilter / StandingOnBlock  [Stable]
Matches the block directly beneath the entity against a BlockSet
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- BlockSet*: Asset <BlockSet> (computable) — The BlockSet to match against

## IEntityFilter / Stat  [Stable]
Match stat values of the entity
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- Stat*: Asset <EntityStat> (computable) — The stat value to check
- StatTarget*: Flag <[Value, Min, Max]> (computable) — The stat target
- RelativeTo*: Asset <EntityStat> (computable) — The stat value to check against
- RelativeToTarget*: Flag <[Value, Min, Max]> (computable) — The stat target
- ValueRange*: Array <Double> (computable) — The fractional range within which to trigger, with 1 being equal

## IEntityFilter / ViewSector  [Stable]
Matches entities within the given view sector
- Enabled: Boolean = true (computable) — Whether this entity filter should be enabled
- ViewSector: Double = 0.0 (computable) — View sector to test entities in (0 is treated as 360)

## ISensorEntityPrioritiser / Attitude  [Stable]
Prioritises return entities by attitude
- AttitudesByPriority*: FlagArray <[IGNORE, HOSTILE, NEUTRAL, FRIENDLY, REVERED]> (computable) — A prioritised list of attitudes

## Instruction / Instruction  [WorkInProgress]
An instruction with Sensor, and Motions and Actions, or a list of nested instructions.
- Name: String — Optional name for descriptor
- Tag: String — Internal identifier tag for debugging
- Enabled: Boolean = true (computable) — Whether this instruction should be enabled on the NPC
- Sensor: ObjectRef <Sensor> — Sensor for testing if instruction can be applied
- BodyMotion: ObjectRef <BodyMotion> — Body motion to be executed
- HeadMotion: ObjectRef <HeadMotion> — Head motion to be executed
- Actions: ObjectRef <ActionList> — Actions to be executed
- ActionsBlocking: Boolean = false — Do not execute an action unless the previous action could execute
- ActionsAtomic: Boolean = false — Only execute actions if all actions can be executed
- Instructions: Array <Instruction> — Optional nested list of instructions
- Continue: Boolean = false — Continue after this instruction was executed
- Weight: Double = 1.0 (computable) — Weighted chance of picking this instruction in a random instruction
- TreeMode: Boolean = false — Whether this instruction and its contents should be treated like a traditional behaviour tree.
- InvertTreeModeResult: Boolean = false (computable) — Whether or not to invert the result of TreeMode evaluation when passing up to parent TreeMode instructions

## Instruction / Random  [Stable]
Randomised list of weighted instructions. One will be selected at random and executed until the NPC state changes.
- Name: String — Optional name for descriptor
- Tag: String — Internal identifier tag for debugging
- Enabled: Boolean = true (computable) — Whether this instruction should be enabled on the NPC
- Sensor: ObjectRef <Sensor> — Sensor for testing if instruction can be applied
- Instructions: Array <Instruction> — List of weighted instructions to select from
- Continue: Boolean = false — Continue after this instruction was executed
- Weight: Double = 1.0 (computable) — Weighted chance of picking this instruction in a random instruction
- TreeMode: Boolean = false — Whether this instruction and its contents should be treated like a traditional behaviour tree.
- InvertTreeModeResult: Boolean = false (computable) — Whether or not to invert the result of TreeMode evaluation when passing up to parent TreeMode instructions
- ResetOnStateChange: Boolean = true (computable) — Whether to reset when NPC state changes
- ExecuteFor: Array <Double> = [1.7976931348623157E308, 1.7976931348623157E308] (computable) — How long to execute the chosen instruction before picking another

## Instruction / Reference  [Stable]
Prioritized instruction list that can be referenced from elsewhere in the file. Otherwise works like the default
- Parameters: Parameters — The parameter block for defining variables
- Name*: String — Name for referencing
- Tag: String — Internal identifier tag for debugging
- Enabled: Boolean = true (computable) — Whether this instruction should be enabled on the NPC
- Sensor: ObjectRef <Sensor> — Sensor for testing if instruction can be applied
- BodyMotion: ObjectRef <BodyMotion> — Body motion to be executed
- HeadMotion: ObjectRef <HeadMotion> — Head motion to be executed
- Actions: ObjectRef <ActionList> — Actions to be executed
- ActionsBlocking: Boolean = false — Do not execute an action unless the previous action could execute
- ActionsAtomic: Boolean = false — Only execute actions if all actions can be executed
- Instructions: Array <Instruction> — Optional nested list of instructions
- Continue: Boolean = false — Continue after this instruction was executed
- Weight: Double = 1.0 (computable) — Weighted chance of picking this instruction in a random instruction
- TreeMode: Boolean = false — Whether this instruction and its contents should be treated like a traditional behaviour tree.
- InvertTreeModeResult: Boolean = false (computable) — Whether or not to invert the result of TreeMode evaluation when passing up to parent TreeMode instructions

## MotionController / Dive  [WorkInProgress]
Provide diving abilities for NPC
- Type*: String — Type field
- EpsilonSpeed: Double = 1.0E-5 — Minimum speed considered non 0
- EpsilonAngle: Double = 3.0 — Minimum angle difference considered non 0 in degrees
- MaxHeadRotationSpeed: Double = 360.0 (computable) — Maximum rotation speed of the head in degrees
- ExternalVelocityDamping: Double = 0.5 (computable) — Damping of external velocity over time
- RunThreshold: Double = 0.7 (computable) — Relative threshold when running animation should be used
- RunThresholdRange: Double = 0.15 (computable) — Relative threshold range for switching between running/walking
- MaxSwimSpeed: Double = 3.0 (computable) — Maximum horizontal speed
- MaxDiveSpeed: Double = 8.0 — Maximum vertical speed
- MaxFallSpeed: Double = 10.0 — Terminal velocity falling in air
- MaxSinkSpeed: Double = 4.0 — Terminal velocity sinking in water
- Gravity: Double = 10.0 — Gravity
- Acceleration: Double = 3.0 — Acceleration
- MaxRotationSpeed: Double = 360.0 — Maximum rotational speed in degrees
- MaxSwimTurnAngle: Double = 90.0 — Maximum angle NPC can walk without explicit turning in degrees
- FastSwimThreshold: Double = 0.6 — Relative threshold when fast swimming animation should be used
- SwimDepth: Double = 0.4 — Minimum height NPC needs to be submerged to be able to swim
- SinkRatio: Double = 1.0 — Relative sink or climb speed while wandering
- MinDiveDepth: Double = 0.0 — 
- MaxDiveDepth: Double = 1.7976931348623157E308 — Maximum dive depth below surface desired
- MinDepthAboveGround: Double = 1.0 — Minimum distance from ground desired
- MinDepthBelowSurface: Double = 1.0 — Minimum distance from water surface desired
- MinWaterDepth: Double = 1.0 — 
- MaxWaterDepth: Double = 0.0 — 
- DesiredDepthWeight: Double = 0.0 — How much this NPC prefers being within the desired height range

## MotionController / Fly  [WorkInProgress]
Flight motion controller
- Type*: String — Type field
- EpsilonSpeed: Double = 1.0E-5 — Minimum speed considered non 0
- EpsilonAngle: Double = 3.0 — Minimum angle difference considered non 0 in degrees
- MaxHeadRotationSpeed: Double = 360.0 (computable) — Maximum rotation speed of the head in degrees
- ExternalVelocityDamping: Double = 0.5 (computable) — Damping of external velocity over time
- RunThreshold: Double = 0.7 (computable) — Relative threshold when running animation should be used
- RunThresholdRange: Double = 0.15 (computable) — Relative threshold range for switching between running/walking
- MinAirSpeed: Double = 0.1 — Minimum in air speed
- MaxHorizontalSpeed: Double = 8.0 (computable) — Maximum horizontal speed
- MaxClimbSpeed: Double = 6.0 — Maximum climbing speed
- MaxSinkSpeed: Double = 10.0 — Maximum sink/drop speed
- MaxFallSpeed: Double = 40.0 — Maximum fall speed
- MaxSinkSpeedFluid: Double = 4.0 — Maximum sink/fall speed in fluids
- MaxClimbAngle: Double = 45.0 — Maximum climb angle
- MaxSinkAngle: Double = 85.0 — Maximum sink angle
- Acceleration: Double = 4.0 — Maximum Acceleration
- Deceleration: Double = 4.0 — Maximum deceleration
- Gravity: Double = 40.0 — Gravity
- MaxTurnSpeed: Double = 180.0 — Maximum turn speed in degrees per second
- MaxRollAngle: Double = 45.0 — Maximum roll angle in degrees
- MaxRollSpeed: Double = 180.0 — Maximum roll speed in degrees per second
- RollDamping: Double = 0.8999999761581421 — Roll damping
- MinHeightOverGround: Double = 1.0 (computable) — Minimum height over ground
- MaxHeightOverGround: Double = 20.0 (computable) — Maximum height over ground
- FastFlyThreshold: Double = 0.6 — Relative threshold when fast flying animation should be used
- AutoLevel: Boolean = true — Set pitch to 0 when no steering forces applied
- DesiredAltitudeWeight: Double = 0.0 — How much this NPC prefers being within the desired height range

## MotionController / Walk  [WorkInProgress]
Provide walk on ground abilities for NPC
- Type*: String — Type field
- EpsilonSpeed: Double = 1.0E-5 — Minimum speed considered non 0
- EpsilonAngle: Double = 3.0 — Minimum angle difference considered non 0 in degrees
- MaxHeadRotationSpeed: Double = 360.0 (computable) — Maximum rotation speed of the head in degrees
- ExternalVelocityDamping: Double = 0.5 (computable) — Damping of external velocity over time
- RunThreshold: Double = 0.7 (computable) — Relative threshold when running animation should be used
- RunThresholdRange: Double = 0.15 (computable) — Relative threshold range for switching between running/walking
- MaxWalkSpeed: Double = 3.0 (computable) — Maximum horizontal speed
- MinWalkSpeed: Double = 0.1 (computable) — Minimum horizontal speed
- MaxFallSpeed: Double = 8.0 (computable) — Maximum fall speed
- MaxSinkSpeedFluid: Double = 4.0 (computable) — Maximum sink speed in fluids
- Gravity: Double = 10.0 (computable) — Gravity
- Acceleration: Double = 3.0 (computable) — Acceleration
- MaxRotationSpeed: Double = 360.0 (computable) — Maximum rotational speed in degrees
- MaxWalkTurnAngle: Double = 90.0 (computable) — Maximum angle NPC can walk without explicit turning in degrees
- BlendRestTurnAngle: Double = 60.0 (computable) — When NPC is blending heading and turn angle required is larger than this value speed is reduced
- BlendRestRelativeSpeed: Double = 0.2 (computable) — When NPC is blending heading relative speed used when reducing speed
- MaxClimbHeight: Double = 1.3 (computable) — Maximum height NPC can climb
- JumpHeight: Double = 0.5 (computable) — How high the NPC jumps above climb height
- MinJumpHeight: Double = 0.6 (computable) — Minimum height above which a jump will be attempted
- MinJumpDistance: Double = 0.2 (computable) — Minimum distance above which a jump will be executed
- JumpForce: Double = 1.5 (computable) — The force multiplier for the upward motion of the jump
- JumpBlending: Double = 1.0 (computable) — The blending of the upwards jump pattern
- JumpDescentBlending: Double = 1.0 (computable) — The blending of the jump descent pattern
- JumpDescentSteepness: Double = 1.0 (computable) — The steepness of the descent portion of the jump
- AscentAnimationType: Flag <[Walk, Jump, Climb, Fly, Idle]> = Walk (computable) — The animation to play when walking up a block
- ClimbSpeedMult: Double = 0.0 (computable) — Climb speed multiplier (const + multiplier * walkspeed ** power)
- ClimbSpeedPow: Double = 1.0 (computable) — Climb speed power (const + multiplier * walkspeed ** power)
- ClimbSpeedConst: Double = 5.0 (computable) — Climb speed constant (const + multiplier * walkspeed ** power)
- MinDescentAnimationHeight: Double = 1.0 (computable) — The min drop distance to switch from the standard walking animation to the specified descent animation
- DescendFlatness: Double = 0.7 (computable) — Relative scale how fast NPC moves forward while climbing down
- DescendSpeedCompensation: Double = 0.9 (computable) — Factor to compensate forward speed reduction while moving downwards
- DescentAnimationType: Flag <[Walk, Fall, Idle]> = Fall (computable) — The animation to play when moving down a block
- DescentSteepness: Double = 1.4 (computable) — The relative steepness of the descent
- DescentBlending: Double = 1.8 (computable) — The blending of the descent pattern
- MaxDropHeight: Double = 3.0 (computable) — Maximum height NPC considers drop safe
- MaxDropHeightRelaxedAdjustment: Double = 3.0 (computable) — Additional drop height when DROP constraint is relaxed
- FenceBlockSet: Asset <BlockSet> = Fence (computable) — Unclimbable blocks
- JumpRange: Array <Double> = [0.0, 0.0] (computable) — Jump distance range
- MinHover: Double = 0.0 (computable) — Minimum hover height over ground
- MinHoverClimb: Double = 0.0 (computable) — Minimum hover height over ground when climbing
- MinHoverDrop: Double = 0.0 (computable) — Minimum hover height over ground when dropping
- FloatsDown: Boolean = true (computable) — If true NPC floats down when hovering enabled else gravity decides
- MaxHover: Double = 0.0 (computable) — Maximum hover height over ground
- HoverFreq: Double = 0.0 (computable) — Hover frequency
- MinHitSlowdown: Double = 0.1 (computable) — The minimum percentage to slow down by when attacked from behind

## Path / Path  [Stable]
List of transient path points
- Waypoints*: Array <RelativeWaypointDefinition> — List of transient path points
- Scale: Double = 1.0 (computable) — Overall path scale

## RelativeWaypointDefinition / RelativeWaypointDefinition  [Stable]
A simple path waypoint definition where each waypoint is relative to the previous
- Rotation: Double = 0.0 — Rotation to turn from previous waypoint
- Distance*: Double — A distance to move from the previous waypoint

## Role / Abstract  [Stable]
Generic role for NPC with a core planner and list of Motion controllers.
- Debug: String — Debugging flags
- StartState: String = start — Initial state
- DefaultSubState: String = Default — The default sub state to reference when transitioning to a main state without a specified sub state
- DisableDamageFlock: Boolean = true — If true disables combat damage from flock members
- DisableDamageGroups: AssetArray <TagSet> (computable) — Members in this list of group won't cause damage
- BusyStates*: StringList — States during which this NPC is busy and can't be interacted with
- DefaultPlayerAttitude: Flag <[IGNORE, HOSTILE, NEUTRAL, FRIENDLY, REVERED]> = HOSTILE (computable) — The default attitude of this NPC towards players
- DefaultNPCAttitude: Flag <[IGNORE, HOSTILE, NEUTRAL, FRIENDLY, REVERED]> = NEUTRAL (computable) — The default attitude of this NPC towards other NPCs
- AttitudeGroup: Asset <AttitudeGroup> (computable) — The attitude group towards other NPCs this NPC belongs to (often species related)
- ItemAttitudeGroup: Asset <ItemAttitudeGroup> (computable) — This NPC's item attitudes
- MaxHealth*: Integer (computable) — Max health
- Appearance*: Asset <Model> (computable) — Model to use for rendering
- DisplayNames: StringList — List of possible display names to choose from
- NameTranslationKey*: String (computable) — The translation key for this NPC's name
- HiddenUIComponents: AssetArray <EntityUIComponent> (computable) — UI components to hide above this NPC
- OpaqueBlockSet: Asset <BlockSet> = Opaque — Blocks blocking line of sight
- Inertia: Double = 1.0 — Inertia
- KnockbackScale: Double = 1.0 (computable) — Scale factor for knockback
- UseFixedKnockback: Boolean = false (computable) — Use knockback fixes
- InventorySize: Integer = 0 — Number of available inventory slots
- HotbarSize: Integer = 3 — Number of available hotbar slots
- OffHandSlots: Integer = 0 — The number of slots for off-hand items
- HotbarItems: AssetArray <Item> (computable) — Hotbar items (e.g. primary weapon, secondary weapon, etc)
- OffHandItems: AssetArray <Item> (computable) — Off-hand items (e.g. shields, torches, etc)
- PossibleInventoryItems: Asset <ItemDropList> (computable) — A droplist defining the possible items the NPCs inventory could contain
- DefaultOffHandSlot: Integer = -1.0 (computable) — The default off-hand item slot (-1 is empty)
- Armor: AssetArray <Item> — Armor items
- DropList: Asset <ItemDropList> (computable) — Drop list to spawn when killed
- CollisionDistance: Double = 5.0 — Collision lookahead
- CollisionForceFalloff: Double = 2.0 — Falloff rate for collision force
- CollisionRadius: Double = -1.0 — Collision radius override
- CollisionViewAngle: Double = 320.0 — Collision detection view cone
- SeparationDistance: Double = 3.0 (computable) — Desired separation distance
- SeparationWeight: Double = 1.0 (computable) — Blend factor separation
- SeparationDistanceTarget: Double = 1.0 (computable) — Desired separation distance when close to target
- SeparationNearRadiusTarget: Double = 1.0 (computable) — Distance when using SeparationDistanceTarget
- SeparationFarRadiusTarget: Double = 5.0 (computable) — Use normal separation distance from further than this distance
- ApplyAvoidance: Boolean = false — Apply avoidance steering force
- AvoidanceFallCheck: Boolean = false (computable) — Deprecated no-op retained for backwards compatibility
- ApplySeparation: Boolean = false (computable) — Apply separation steering force
- AvoidanceMode: Flag <[Slowdown, Evade, Any]> = Any (computable) — Abilities to use for avoidance
- SeparationMode: Flag <[Legacy, Push]> = Legacy (computable) — Mode for separation calculation
- SeparationPushSafeDistanceMultiplier: Double = 0.8 (computable) — Push Mode: Multiplier to reduce target distance to avoid NPC jittering close to target
- SeparationLegacySteeringStrength: Double = 0.5 (computable) — Legacy mode: Separation steering strength
- SeparationPushSteeringStrength: Double = 0.8 (computable) — Push mode: Separation steering strength
- SeparationPushDistanceWeightDefault: Double = 1.0 (computable) — Push mode: falloff exponent for separation distance
- SeparationPushDistanceWeightTarget: Double = 8.0 (computable) — Push mode: falloff exponent when NPC is close to motion target
- SeparationPushDistanceWeightAttacker: Double = 8.0 (computable) — Push mode: falloff exponent towards other potential attackers when close to motion target
- SeparationPushSpeedScale: Double = 0.5 (computable) — Push mode: scale to increase smaller speeds for separation
- SeparationOverrideOrientation: Flag <[On, Off, Default]> = Default (computable) — Whether to override orientation of NPC when separating
- SeparationOverrideAlwaysSeparate: Flag <[On, Off, Default]> = Default (computable) — Whether to separate even if the NPC would rest
- SeparationOverrideNormalizeDistances: Flag <[On, Off, Default]> = Default (computable) — Whether to normalize distances when summing distances
- EntityAvoidanceStrength: Double = 1.0 — Blending factor avoidance
- StayInEnvironment: Boolean = false — Stay in spawning environment
- AllowedEnvironments: String — Allowed environment to walk in
- FlockSpawnTypes: Array <String> = null (computable) — Types of NPC this flock should consist off
- FlockSpawnTypesRandom: Boolean = false (computable) — Create a randomized flock if true else spawn in order of FlockSpawnTypes
- FlockAllowedNPC: Array <String> = null (computable) — List of NPCs allowed in flock
- FlockCanLead: Boolean = false (computable) — This NPC can be flock leader
- FlockWeightAlignment: Double = 1.0 — Blending flock alignment
- FlockWeightSeparation: Double = 1.0 — Blending flock separation
- FlockWeightCohesion: Double = 1.0 — Blending flock cohesion
- FlockInfluenceRange: Double = 10.0 — Influence radius flock forces
- CombatConfig: CodecObject <String> — The combat configuration providing optional combat action evaluator
- Invulnerable: Boolean = false (computable) — Makes NPC ignore damage
- IgnoreDisableNPCIncomingDamage: Boolean = false (computable) — Makes NPC still receive incoming damage when CombatConfig.disableNpcIncomingDamage is set to true
- BreathesInAir: Boolean = true (computable) — Can breath in air
- BreathesInWater: Boolean = false (computable) — Can breath in fluid/water
- PickupDropOnDeath: Boolean = false — Drop last picked item on death
- DeathAnimationTime: Double = 1.5 (computable) — How long to let the death animation play before removing
- DeathParticles: Asset <ParticleSystem> = Effect_Death (computable) — Particles to play when the NPC corpse is removed.
- DropDeathItemsInstantly: Boolean = false (computable) — Whether or not to drop death items instantly on death, or when the body disappears.
- DeathInteraction: Asset <Interaction> (computable) — Interaction to run on death
- DespawnAnimationTime: Double = 0.800000011920929 — How long to let the despawn animation play before removing
- SpawnParticles: Asset <ParticleSystem> (computable) — Particle system when spawning
- SpawnParticlesOffset: Array <Double> = null (computable) — Displacement from foot point to spawn relative to NPC heading
- SpawnParticlesTargetNode: String (computable) — Target node for spawn particles
- SpawnParticlesDetached: Boolean = true (computable) — Whether spawn particles should be attached to the model or not
- SpawnViewDistance: Double = 75.0 — View distance for spawn particle
- CorpseStaysInFlock: Boolean = false — Whether the NPC should stay in the flock until corpse removal or be removed at the moment of death
- OverrideHeadPitchAngle: Boolean = true (computable) — Whether to override the head pitch angle range
- HeadPitchAngleRange: Array <Double> = [-89.0, 89.0] (computable) — Head rotation pitch range to be used instead of model camera settings
- MotionControllerList*: ObjectRef <HashMap> — Motion controllers
- Instructions: Array <Instruction> — List of instructions
- InteractionInstruction: ObjectRef <Instruction> — Interaction instruction
- DeathInstruction: ObjectRef <Instruction> — Death instruction
- StateTransitions: ObjectRef <StateTransitionController> — State transition actions
- StateEvaluator: CodecObject <StateEvaluator> — A state evaluator
- InitialMotionController: String (computable) — The initial motion controller to set
- InteractionVars: CodecObject <RootInteraction> — Interaction vars to be used in interactions.
- IsMemory: Boolean = false (computable) — Used to define if the NPC has a Memory to record.
- MemoriesCategory: String = Other (computable) — Category to put the NPC in, as part of the Memories Plugin
- MemoriesNameOverride: String (computable) — Overrides the Memory name when set.
- MemoriesUnlockedBy: Flag <[Proximity, Kill]> = Proximity (computable) — How the player records this NPC's Memory entry.
- MemoriesKillRange: Double = 0.0 (computable) — Radius in blocks in which players record this NPC's Memory when it dies.
- SpawnLockTime: Double = 1.5 (computable) — How long the NPC should be locked and unable to perform behavior when first spawned

## Role / Generic  [Stable]
Generic role for NPC with a core planner and list of Motion controllers.
- Debug: String — Debugging flags
- StartState: String = start — Initial state
- DefaultSubState: String = Default — The default sub state to reference when transitioning to a main state without a specified sub state
- DisableDamageFlock: Boolean = true — If true disables combat damage from flock members
- DisableDamageGroups: AssetArray <TagSet> (computable) — Members in this list of group won't cause damage
- BusyStates*: StringList — States during which this NPC is busy and can't be interacted with
- DefaultPlayerAttitude: Flag <[IGNORE, HOSTILE, NEUTRAL, FRIENDLY, REVERED]> = HOSTILE (computable) — The default attitude of this NPC towards players
- DefaultNPCAttitude: Flag <[IGNORE, HOSTILE, NEUTRAL, FRIENDLY, REVERED]> = NEUTRAL (computable) — The default attitude of this NPC towards other NPCs
- AttitudeGroup: Asset <AttitudeGroup> (computable) — The attitude group towards other NPCs this NPC belongs to (often species related)
- ItemAttitudeGroup: Asset <ItemAttitudeGroup> (computable) — This NPC's item attitudes
- MaxHealth*: Integer (computable) — Max health
- Appearance*: Asset <Model> (computable) — Model to use for rendering
- DisplayNames: StringList — List of possible display names to choose from
- NameTranslationKey*: String (computable) — The translation key for this NPC's name
- HiddenUIComponents: AssetArray <EntityUIComponent> (computable) — UI components to hide above this NPC
- OpaqueBlockSet: Asset <BlockSet> = Opaque — Blocks blocking line of sight
- Inertia: Double = 1.0 — Inertia
- KnockbackScale: Double = 1.0 (computable) — Scale factor for knockback
- UseFixedKnockback: Boolean = false (computable) — Use knockback fixes
- InventorySize: Integer = 0 — Number of available inventory slots
- HotbarSize: Integer = 3 — Number of available hotbar slots
- OffHandSlots: Integer = 0 — The number of slots for off-hand items
- HotbarItems: AssetArray <Item> (computable) — Hotbar items (e.g. primary weapon, secondary weapon, etc)
- OffHandItems: AssetArray <Item> (computable) — Off-hand items (e.g. shields, torches, etc)
- PossibleInventoryItems: Asset <ItemDropList> (computable) — A droplist defining the possible items the NPCs inventory could contain
- DefaultOffHandSlot: Integer = -1.0 (computable) — The default off-hand item slot (-1 is empty)
- Armor: AssetArray <Item> — Armor items
- DropList: Asset <ItemDropList> (computable) — Drop list to spawn when killed
- CollisionDistance: Double = 5.0 — Collision lookahead
- CollisionForceFalloff: Double = 2.0 — Falloff rate for collision force
- CollisionRadius: Double = -1.0 — Collision radius override
- CollisionViewAngle: Double = 320.0 — Collision detection view cone
- SeparationDistance: Double = 3.0 (computable) — Desired separation distance
- SeparationWeight: Double = 1.0 (computable) — Blend factor separation
- SeparationDistanceTarget: Double = 1.0 (computable) — Desired separation distance when close to target
- SeparationNearRadiusTarget: Double = 1.0 (computable) — Distance when using SeparationDistanceTarget
- SeparationFarRadiusTarget: Double = 5.0 (computable) — Use normal separation distance from further than this distance
- ApplyAvoidance: Boolean = false — Apply avoidance steering force
- AvoidanceFallCheck: Boolean = false (computable) — Deprecated no-op retained for backwards compatibility
- ApplySeparation: Boolean = false (computable) — Apply separation steering force
- AvoidanceMode: Flag <[Slowdown, Evade, Any]> = Any (computable) — Abilities to use for avoidance
- SeparationMode: Flag <[Legacy, Push]> = Legacy (computable) — Mode for separation calculation
- SeparationPushSafeDistanceMultiplier: Double = 0.8 (computable) — Push Mode: Multiplier to reduce target distance to avoid NPC jittering close to target
- SeparationLegacySteeringStrength: Double = 0.5 (computable) — Legacy mode: Separation steering strength
- SeparationPushSteeringStrength: Double = 0.8 (computable) — Push mode: Separation steering strength
- SeparationPushDistanceWeightDefault: Double = 1.0 (computable) — Push mode: falloff exponent for separation distance
- SeparationPushDistanceWeightTarget: Double = 8.0 (computable) — Push mode: falloff exponent when NPC is close to motion target
- SeparationPushDistanceWeightAttacker: Double = 8.0 (computable) — Push mode: falloff exponent towards other potential attackers when close to motion target
- SeparationPushSpeedScale: Double = 0.5 (computable) — Push mode: scale to increase smaller speeds for separation
- SeparationOverrideOrientation: Flag <[On, Off, Default]> = Default (computable) — Whether to override orientation of NPC when separating
- SeparationOverrideAlwaysSeparate: Flag <[On, Off, Default]> = Default (computable) — Whether to separate even if the NPC would rest
- SeparationOverrideNormalizeDistances: Flag <[On, Off, Default]> = Default (computable) — Whether to normalize distances when summing distances
- EntityAvoidanceStrength: Double = 1.0 — Blending factor avoidance
- StayInEnvironment: Boolean = false — Stay in spawning environment
- AllowedEnvironments: String — Allowed environment to walk in
- FlockSpawnTypes: Array <String> = null (computable) — Types of NPC this flock should consist off
- FlockSpawnTypesRandom: Boolean = false (computable) — Create a randomized flock if true else spawn in order of FlockSpawnTypes
- FlockAllowedNPC: Array <String> = null (computable) — List of NPCs allowed in flock
- FlockCanLead: Boolean = false (computable) — This NPC can be flock leader
- FlockWeightAlignment: Double = 1.0 — Blending flock alignment
- FlockWeightSeparation: Double = 1.0 — Blending flock separation
- FlockWeightCohesion: Double = 1.0 — Blending flock cohesion
- FlockInfluenceRange: Double = 10.0 — Influence radius flock forces
- CombatConfig: CodecObject <String> — The combat configuration providing optional combat action evaluator
- Invulnerable: Boolean = false (computable) — Makes NPC ignore damage
- IgnoreDisableNPCIncomingDamage: Boolean = false (computable) — Makes NPC still receive incoming damage when CombatConfig.disableNpcIncomingDamage is set to true
- BreathesInAir: Boolean = true (computable) — Can breath in air
- BreathesInWater: Boolean = false (computable) — Can breath in fluid/water
- PickupDropOnDeath: Boolean = false — Drop last picked item on death
- DeathAnimationTime: Double = 1.5 (computable) — How long to let the death animation play before removing
- DeathParticles: Asset <ParticleSystem> = Effect_Death (computable) — Particles to play when the NPC corpse is removed.
- DropDeathItemsInstantly: Boolean = false (computable) — Whether or not to drop death items instantly on death, or when the body disappears.
- DeathInteraction: Asset <Interaction> (computable) — Interaction to run on death
- DespawnAnimationTime: Double = 0.800000011920929 — How long to let the despawn animation play before removing
- SpawnParticles: Asset <ParticleSystem> (computable) — Particle system when spawning
- SpawnParticlesOffset: Array <Double> = null (computable) — Displacement from foot point to spawn relative to NPC heading
- SpawnParticlesTargetNode: String (computable) — Target node for spawn particles
- SpawnParticlesDetached: Boolean = true (computable) — Whether spawn particles should be attached to the model or not
- SpawnViewDistance: Double = 75.0 — View distance for spawn particle
- CorpseStaysInFlock: Boolean = false — Whether the NPC should stay in the flock until corpse removal or be removed at the moment of death
- OverrideHeadPitchAngle: Boolean = true (computable) — Whether to override the head pitch angle range
- HeadPitchAngleRange: Array <Double> = [-89.0, 89.0] (computable) — Head rotation pitch range to be used instead of model camera settings
- MotionControllerList*: ObjectRef <HashMap> — Motion controllers
- Instructions: Array <Instruction> — List of instructions
- InteractionInstruction: ObjectRef <Instruction> — Interaction instruction
- DeathInstruction: ObjectRef <Instruction> — Death instruction
- StateTransitions: ObjectRef <StateTransitionController> — State transition actions
- StateEvaluator: CodecObject <StateEvaluator> — A state evaluator
- InitialMotionController: String (computable) — The initial motion controller to set
- InteractionVars: CodecObject <RootInteraction> — Interaction vars to be used in interactions.
- IsMemory: Boolean = false (computable) — Used to define if the NPC has a Memory to record.
- MemoriesCategory: String = Other (computable) — Category to put the NPC in, as part of the Memories Plugin
- MemoriesNameOverride: String (computable) — Overrides the Memory name when set.
- MemoriesUnlockedBy: Flag <[Proximity, Kill]> = Proximity (computable) — How the player records this NPC's Memory entry.
- MemoriesKillRange: Double = 0.0 (computable) — Radius in blocks in which players record this NPC's Memory when it dies.
- SpawnLockTime: Double = 1.5 (computable) — How long the NPC should be locked and unable to perform behavior when first spawned

## Role / Variant  [WorkInProgress]
Create a variant from an existing NPC JSON file

## Sensor / AdjustPosition  [Stable]
Perform adjustments to the wrapped sensor's returned position
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Sensor*: ObjectRef <Sensor> — Sensor to wrap
- Offset*: Array <Double> (computable) — The offset to apply to the returned position from the sensor

## Sensor / Age  [Stable]
Triggers when the age of the NPC falls between a certain range. Range is defined in terms of period (e.g. 1Y2M3W4D - 1 year, 2 months, 3 weeks, 4 days) or duration (e.g. 2DT3H4M - 2 days, 3 hours, 4 minutes)
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- AgeRange*: Array <TemporalAmount> (computable) — The age range within which to trigger

## Sensor / Alarm  [Stable]
Check the state of a named alarm and optionally clear it if the time has passed
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Name*: String (computable) — The name of the alarm to check
- State*: Flag <[SET, UNSET, PASSED]> (computable) — The state to check for
- Clear: Boolean = false (computable) — Whether to clear the alarm (unset it) if it has passed

## Sensor / And  [Stable]
Evaluate all sensors and execute action only when all sensor signal true. Target is provided by first sensor.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Sensors*: Array <Sensor> — List of sensors
- AutoUnlockTargetSlot: String (computable) — A target slot to unlock when sensor doesn't match anymore

## Sensor / Animation  [Stable]
Check if a given animation is being played
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Slot*: Flag <[Status, Action, Face]> (computable) — The animation slot to check
- Animation*: String (computable) — The animation ID to check for

## Sensor / Any  [Stable]
Sensor always signals true but doesn't return a target.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC

## Sensor / Beacon  [Stable]
Checks to see if any messages have been broadcasted by nearby NPCs.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Message*: String (computable) — The message to listen for
- Range: Double = 64.0 (computable) — The max distance beacons should be received from
- TargetSlot: String — A slot to store the sender as a target. If omitted no target will be stored
- ConsumeMessage: Boolean = true — Whether the message should be consumed by this sensor
- Rebind: Boolean = false — Whether the target slot rebinds to the entity, so it survives short reloads or role changes.

## Sensor / Block  [Experimental]
Checks for one of a set of blocks in the nearby area and caches the result until explicitly reset or the targeted block changes/is removed. All block sensors with the same sought blockset share the same targeted block once found
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Range*: Double (computable) — The range to search for the blocks in
- MaxHeight: Double = 4.0 (computable) — The vertical range to search for the blocks in
- Blocks*: Asset <BlockSet> (computable) — The set of blocks to search for
- Random: Boolean = false (computable) — Whether to pick at random from within the matched blocks or pick the closest
- Reserve: Boolean = false (computable) — Whether to reserve the found block to prevent other NPCs selecting it

## Sensor / BlockChange  [Stable]
Matches when a block from a blockset within a certain range is changed or interacted with
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Range*: Double (computable) — Max range to listen in
- SearchType: Flag <[PlayerFirst, PlayerOnly, NpcFirst, NpcOnly]> = PlayerOnly (computable) — Whether to listen for events triggered by players, npcs, or both in a certain order
- TargetSlot: String (computable) — A target slot to place the target in. If omitted, no slot will be used
- Rebind: Boolean = false (computable) — Whether the target slot rebinds to the entity, so it survives short reloads or role changes.
- BlockSet*: Asset <BlockSet> (computable) — Block set to listen for
- EventType: Flag <[DAMAGE, DESTRUCTION, INTERACTION]> = DAMAGE (computable) — The event type to listen for

## Sensor / BlockType  [Stable]
Checks if the block at the given position matches the provided block set
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Sensor*: ObjectRef <Sensor> — Sensor to wrap
- BlockSet*: Asset <BlockSet> (computable) — Block set to check against

## Sensor / CanInteract  [Stable]
Checks whether or not the player being iterated by the interaction instruction can interact with this NPC
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- ViewSector: Double = 0.0 (computable) — View sector to test the player in
- Attitudes: FlagSet <[IGNORE, HOSTILE, NEUTRAL, FRIENDLY, REVERED]> = [NEUTRAL, FRIENDLY, REVERED] (computable) — A set of attitudes to match

## Sensor / CanPlaceBlock  [Stable]
Test if the currently set block can be placed at the relative position given direction and offset
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Direction: Flag <[Forward, Backward, Left, Right]> = Forward (computable) — The direction to place relative to heading
- Offset: Flag <[HeadPosition, BodyPosition, FootPosition]> = BodyPosition (computable) — The offset to place at
- RetryDelay: Double = 5.0 (computable) — The amount of time to delay if a placement fails before trying to place something again
- AllowEmptyMaterials: Boolean = false (computable) — Whether it should be possible to replace blocks that have empty material

## Sensor / ChargeBlockCollisions  [Stable]
Match when the preceding BodyMotion Charge reports at least one block collision in the current rail-step tick. Provides a BlockCollisionProvider exposing the list of BlockHit entries to downstream actions.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- BlockFilter: Asset <BlockSet> (computable) — Optional BlockSet filter for reported collisions. Empty means pass all blocks

## Sensor / ChargeEntityCollisions  [Stable]
Match when the preceding BodyMotion Charge reports at least one entity collision in the current rail-step tick. Provides an EntityCollisionProvider exposing the filtered list of EntityHit entries to downstream actions.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- GetPlayers: Boolean = true (computable) — Include player hits from the charge motion
- GetNPCs: Boolean = true (computable) — Include NPC hits from the charge motion
- ExcludeOwnType: Boolean = false (computable) — When GetNPCs is true, exclude NPCs with the same role type as self

## Sensor / ChargeState  [Stable]
Test if a BodyMotion Charge is in one of the given states.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- States*: FlagSet <[Aiming, LockedOn, InStopRange, LostTarget, WindingUp, Launch, Charging, Obstructed, EntityHit, Knockback, Finished]> (computable) — The charge states that trigger this sensor

## Sensor / Count  [Stable]
Check if there is a certain number of NPCs or players within a specific range
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Count*: Array <integer> (computable) — Specifies the allowed number of entities (inclusive)
- Range*: Array <Double> (computable) — Range to find entities in (inclusive)
- IncludeGroups: AssetArray <TagSet> — Match for NPCs in these groups
- ExcludeGroups: AssetArray <TagSet> — Never match NPCs in these groups

## Sensor / Damage  [Stable]
Test if NPC suffered damage. A position is only returned when NPC suffered combat damage.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Combat: Boolean = true — Test for combat damage
- Friendly: Boolean = false — Test for damage from usually disabled damage groups
- IncludeDoT: Boolean = true — Count damage over time from entity effects as combat damage
- Drowning: Boolean = false — Test for damage from drowning
- Environment: Boolean = false — Test for damage from environment
- Other: Boolean = false — Test for other damage
- TargetSlot: String — The slot to use for locking on the target if damage is taken. If omitted, target will not be locked

## Sensor / DroppedItem  [Stable]
Triggers if a given item is within a certain range of the NPC. Will match anything if Items and Attitudes are not defined, otherwise will match items meeting either criteria.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Range*: Double (computable) — The range within which to look
- ViewSector: Double = 0.0 (computable) — View sector in which to look
- LineOfSight: Boolean = false (computable) — Requires line of sight to item
- Items: AssetArray <Item> (computable) — A list of glob item patterns to match. If omitted, will match any item
- Attitudes: FlagSet <[Ignore, Dislike, Neutral, Like, Love]> = [] (computable) — Attitudes to match

## Sensor / EntityEvent  [Stable]
Matches when an entity from a specific NPC group within a certain range is damaged, killed, or interacted with
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Range*: Double (computable) — Max range to listen in
- SearchType: Flag <[PlayerFirst, PlayerOnly, NpcFirst, NpcOnly]> = PlayerOnly (computable) — Whether to listen for events triggered by players, npcs, or both in a certain order
- TargetSlot: String (computable) — A target slot to place the target in. If omitted, no slot will be used
- Rebind: Boolean = false (computable) — Whether the target slot rebinds to the entity, so it survives short reloads or role changes.
- NPCGroup*: Asset <TagSet> (computable) — NPC group to listen for
- EventType: Flag <[DAMAGE, DEATH, INTERACTION]> = DAMAGE (computable) — The event type to listen for
- FlockOnly: Boolean = false (computable) — Whether to only listen for flock events

## Sensor / Eval  [Experimental]
Evaluate javascript expression and test truth value. Current values accessible are 'health' and 'blocked'.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Expression*: String — Javascript expression

## Sensor / Flag  [Stable]
Test if a named flag is set or not
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Name*: String (computable) — The name of the flag
- Set: Boolean = true (computable) — Whether the flag should be set or not

## Sensor / HasInteracted  [Stable]
Checks whether the currently iterated player in the interaction instruction has interacted with this NPC
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC

## Sensor / InAir  [Stable]
Return true if NPC is not on ground. No target is returned.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC

## Sensor / InWater  [Stable]
Check if NPC is currently in water
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC

## Sensor / InteractionContext  [Stable]
Checks whether the currently iterated player in the interaction instruction has interacted with this NPC in the given context
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Context*: String (computable) — The context of the interaction

## Sensor / IsBackingAway  [Stable]
Test if the NPC is currently backing away from something.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC

## Sensor / IsBusy  [Stable]
Tests if an NPC is in one of the defined Busy States.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC

## Sensor / Kill  [Stable]
Return true if NPC made a kill. Target position is killed entity position.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- TargetSlot: String (computable) — The target slot to check if killed. If omitted, will accept any entity killed

## Sensor / Leash  [Stable]
Triggers when the NPC is outside a specified range from the leash point
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Range*: Double (computable) — The farthest distance allowed from the leash point

## Sensor / Light  [Stable]
Check the light levels of the block an entity is standing on. Can test light intensity, sky light or block channel levels.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- LightRange: Array <Double> = [0.0, 100.0] (computable) — The light intensity percentage range
- SkyLightRange: Array <Double> = [0.0, 100.0] (computable) — The sky light percentage range
- SunlightRange: Array <Double> = [0.0, 100.0] (computable) — The sunlight percentage range
- RedLightRange: Array <Double> = [0.0, 100.0] (computable) — The red light percentage range
- GreenLightRange: Array <Double> = [0.0, 100.0] (computable) — The green light percentage range
- BlueLightRange: Array <Double> = [0.0, 100.0] (computable) — The blue light percentage range
- UseTargetSlot: String (computable) — A target slot to check. If omitted, will check self

## Sensor / Mob  [Stable]
Return true if entity matching specific attributes and filters is in range. Target is entity.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- MinRange: Double = 0.0 (computable) — Minimum range to test entities in
- Range*: Double (computable) — Maximum range to test entities in
- LockOnTarget: Boolean = false (computable) — Matched target becomes locked target
- Rebind: Boolean = false (computable) — Whether the locked target slot rebinds to the entity, so it survives short reloads or role changes.
- MultiTarget: Boolean = false (computable) — Expose all matching targets (primary in slot 0) so a ForEach action can run per target, instead of only the primary
- LockedTargetSlot: String = LockedTarget (computable) — The target slot to use for locking on or unlocking
- AutoUnlockTarget: Boolean = false (computable) — Unlock locked target when sensor not matching it anymore
- OnlyLockedTarget: Boolean = false (computable) — Test only locked target
- IgnoredTargetSlot: String (computable) — The target slot to use for ignoring
- UseProjectedDistance: Boolean = false (computable) — Use the projected movement direction vector for distance, rather than the Euclidean distance
- Prioritiser: ObjectRef <ISensorEntityPrioritiser> — A prioritiser for selecting results based on additional parameters
- Collector: ObjectRef <ISensorEntityCollector> — A collector which can process all checked entities and act on them based on whether they match or not
- Filters: Array <IEntityFilter> — A series of entity filter sensors to test
- GetPlayers: Boolean = false (computable) — Test players
- GetNPCs: Boolean = true (computable) — Test mobs/NPCs
- ExcludeOwnType: Boolean = true (computable) — Exclude NPCs of same type as current NPC

## Sensor / MotionController  [Experimental]
Test if specific motion controller is active.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- MotionController*: String — Motion controller name to test for

## Sensor / Nav  [Stable]
Queries navigation state
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- NavStates: FlagSet <[INIT, PROGRESSING, BLOCKED, DEFER, AT_GOAL, ABORTED]> = [] (computable) — Trigger when path finder is in one of the states or empty to match all
- ThrottleDuration: Double = 0.0 (computable) — Minimum time in seconds the path finder isn't able to reach target or 0 to ignore
- TargetDelta: Double = 0.0 (computable) — Minimum distance target has moved since path was computed or 0 to ignore

## Sensor / Not  [WorkInProgress]
Return true when the given sensor test fails.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Sensor*: ObjectRef <Sensor> — Sensor to test
- UseTargetSlot: String (computable) — A locked target slot to feed to action (if available)
- AutoUnlockTargetSlot: String (computable) — A target slot to unlock when sensor doesn't match anymore

## Sensor / OnGround  [Stable]
Return true if NPC is on ground. No target is returned.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC

## Sensor / Or  [Stable]
Evaluate sensors and execute action when at least one sensor signals true. Target is provided by first sensor signalling true.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Sensors*: Array <Sensor> — List of sensors
- AutoUnlockTargetSlot: String (computable) — A target slot to unlock when sensor doesn't match anymore

## Sensor / Path  [Stable]
Find a path based on various criteria. Provides the position of the nearest waypoint and the path itself
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Path: String (computable) — The name of the path. If left blank, will find the nearest path
- Range: Double = 10.0 (computable) — The range to test to nearest waypoint. 0 is unlimited
- PathType: Flag <[WorldPath, CurrentPrefabPath, AnyPrefabPath, TransientPath]> = AnyPrefabPath (computable) — The type of path to search for

## Sensor / Player  [Stable]
Return true if player matching specific attributes and filters is in range. Target is player.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- MinRange: Double = 0.0 (computable) — Minimum range to test entities in
- Range*: Double (computable) — Maximum range to test entities in
- LockOnTarget: Boolean = false (computable) — Matched target becomes locked target
- Rebind: Boolean = false (computable) — Whether the locked target slot rebinds to the entity, so it survives short reloads or role changes.
- MultiTarget: Boolean = false (computable) — Expose all matching targets (primary in slot 0) so a ForEach action can run per target, instead of only the primary
- LockedTargetSlot: String = LockedTarget (computable) — The target slot to use for locking on or unlocking
- AutoUnlockTarget: Boolean = false (computable) — Unlock locked target when sensor not matching it anymore
- OnlyLockedTarget: Boolean = false (computable) — Test only locked target
- IgnoredTargetSlot: String (computable) — The target slot to use for ignoring
- UseProjectedDistance: Boolean = false (computable) — Use the projected movement direction vector for distance, rather than the Euclidean distance
- Prioritiser: ObjectRef <ISensorEntityPrioritiser> — A prioritiser for selecting results based on additional parameters
- Collector: ObjectRef <ISensorEntityCollector> — A collector which can process all checked entities and act on them based on whether they match or not
- Filters: Array <IEntityFilter> — A series of entity filter sensors to test

## Sensor / Points  [Stable]
Find world points in range, optionally filtered by tag
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Range*: Double (computable) — Maximum range from the acting entity to search for points
- Tag: String (computable) — Only points carrying this tag match. Omit to match any point in range.

## Sensor / ProjectToGround  [Experimental]
Projects every position from the wrapped sensor straight down to the top of the first solid block beneath it, dropping positions with no ground within MaxScanDown or in an unloaded chunk
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Sensor*: ObjectRef <Sensor> — Sensor to wrap
- MaxScanDown: Integer = 128.0 (computable) — Maximum number of blocks to scan downward looking for ground

## Sensor / Random  [Stable]
Alternates between returning true and false for specified random durations
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- TrueDurationRange*: Array <Double> (computable) — The duration range to pick a random period to return true
- FalseDurationRange*: Array <Double> (computable) — The duration range to pick a random period to return false

## Sensor / ReadPosition  [Stable]
Read a stored position with some conditions
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Slot*: String (computable) — The slot to read the position from
- MinRange: Double = 0.0 (computable) — Minimum range from stored position
- Range*: Double (computable) — Maximum range from stored position
- UseMarkedTarget: Boolean = false (computable) — Whether to read from a marked target slot instead of a position slot

## Sensor / SearchRay  [Stable]
Fire a ray at a specific angle to see if what it hits matches a given sought block
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Name*: String (computable) — The id of this search ray sensor so the position can be cached
- Angle*: Double (computable) — Angle to fire the ray
- Range*: Double (computable) — How far to search
- Blocks*: Asset <BlockSet> (computable) — The blockset to search for
- MinRetestAngle: Double = 5.0 (computable) — The minimum change in NPC rotation before rays stop being throttled
- MinRetestMove: Double = 1.0 (computable) — The minimum distance the NPC needs to move while facing the same direction before rays stop being throttled
- ThrottleTime: Double = 0.5 (computable) — The delay between retests when an NPC is facing the same direction

## Sensor / Self  [Stable]
Test if the NPC itself matches a set of entity filters
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Filters*: Array <IEntityFilter> — A series of entity filter sensors to test

## Sensor / State  [Stable]
Signal if NPC is set to specific state.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- State*: String — State to compare to
- IgnoreMissingSetState: Boolean = false — Override and ignore checks for matching setter action that sets this state

## Sensor / Switch  [Stable]
Check if a computed boolean is true
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Switch*: Boolean (computable) — The switch to check

## Sensor / Target  [Stable]
Test if given target matches a series of criteria and optional entity filters
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- TargetSlot: String = LockedTarget (computable) — The target slot to check
- Range: Double = 1.7976931348623157E308 (computable) — Maximum range of locked target
- AutoUnlockTarget: Boolean = false (computable) — Unlock locked target if match fails
- Filters: Array <IEntityFilter> — A series of entity filter sensors to test

## Sensor / Time  [Stable]
Check if the day/year time is within some specified time. If you want to check a range of time which crosses through midnight and switches to the next day, use the greater time as the min value and the lesser value as the max value.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Period*: Array <Double> (computable) — The time period to trigger within
- CheckDay: Boolean = true — Check the day time.
- CheckYear: Boolean = false — Check the year time.
- ScaleDayTimeRange: Boolean = true — Whether to use a relative scale for the day time

## Sensor / Timer  [Stable]
Tests if a timer exists and the value is within a certain range.
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Name*: String (computable) — The name of the timer
- State: Flag <[RUNNING, PAUSED, STOPPED, ANY]> = ANY — The timer's state to check
- TimeRemainingRange: Array <Double> = [0.0, 1.7976931348623157E308] (computable) — The acceptable remaining time on the timer.

## Sensor / ValueProviderWrapper  [Stable]
Wraps a sensor and passes down some additional parameter overrides pulled from the value store
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- PassValues: Boolean = true (computable) — Used to enable/disable passing of values in components
- Sensor*: ObjectRef <Sensor> — Sensor to wrap
- ValueToParameterMappings*: Array <ValueToParameterMapping> — The mappings of values to override parameters

## Sensor / Weather  [Stable]
Matches the current weather at the NPCs position against a set of weather globs
- Once: Boolean = false — Sensor only triggers once
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC
- Weathers*: AssetArray <Weather> (computable) — The glob patterns to match against weather

## StateTransition / StateTransition  [Stable]
An entry containing a list of actions to execute when moving from one state to another
- States*: Array <StateTransitionEdges> — List of state transitions
- Actions*: ObjectRef <ActionList> — List of actions
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC

## StateTransitionController / StateTransitionController  [Stable]
A list of state transitions
- *: Array <StateTransition> — A list of state transition entries with lists of actions

## StateTransitionEdges / StateTransitionEdges  [Stable]
Sets of from and to states defining state transitions
- Priority: Integer = 0 — Priority for the actions in this transition
- From*: StringList — 
- To*: StringList — 
- Enabled: Boolean = true (computable) — Whether this sensor should be enabled on the NPC

## ValueToParameterMapping / ValueToParameterMapping  [Stable]
An entry containing a list of actions to execute when moving from one state to another
- ValueType*: Flag <[String, Int, Double]> — The type of the value being mapped
- FromValue*: String — The value to read from the value store
- ToParameter*: String — The parameter name to override

## WeightedAction / WeightedAction  [Stable]
A wrapped and weighted action intended to be used for Random action lists.
- Action*: ObjectRef <Action> — The action to run
- Weight*: Double (computable) — The weight representing how likely this action is to run

