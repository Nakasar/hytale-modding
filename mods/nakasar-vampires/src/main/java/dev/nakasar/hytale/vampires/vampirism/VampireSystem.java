package dev.nakasar.hytale.vampires.vampirism;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.tick.DelayedEntitySystem;
import com.hypixel.hytale.protocol.ColorLight;
import com.hypixel.hytale.protocol.SoundCategory;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.asset.type.soundevent.config.SoundEvent;
import com.hypixel.hytale.server.core.entity.effect.ActiveEntityEffect;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.modules.entity.component.DynamicLight;
import com.hypixel.hytale.server.core.modules.entity.component.HealthRegenState;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageCause;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageSystems;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.world.SoundUtil;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.TargetUtil;
import dev.nakasar.hytale.vampires.purifying.LightAura;
import dev.nakasar.hytale.vampires.purifying.PurifyingFireSystem;
import org.joml.Vector3d;

import java.util.Map;

/**
 * La vie d'un joueur vampire, quatre fois par seconde.
 *
 * <ul>
 *   <li><b>Faim de sang.</b> Le sang baisse de rassasié à affamé en {@value Vampire#DAYS_TO_STARVE} jours du monde
 *       (durées de jour et de nuit du monde, même si le temps y est figé). En survie, un joueur ne régénère que par
 *       les effets des repas ; un vampire régénère selon son palier ({@link BloodStage}), affiché par un effet de
 *       statut, et la régénération naturelle reste coupée ({@link HealthRegenState}). Les effets de nourriture (ids
 *       qui commencent par {@link #FOOD_EFFECT_PREFIXES}, ceux de Server/Entity/Effects/Food du jeu 0.7.2) sont
 *       retirés dès qu'ils apparaissent : la nourriture n'a plus d'effet.</li>
 *   <li><b>Affamé.</b> Les battements de cœur du vivant le plus proche (moins de {@value #HEARTBEAT_RADIUS} blocs)
 *       se font entendre, de plus en plus vite quand il approche. Le malus d'attaque est dans
 *       {@link VampireDamageSystem}.</li>
 *   <li><b>Soleil</b> ({@link SunExposure}), atténué par les protections : potions de protection solaire (effets
 *       {@value #SUN_PROTECTION_PREFIX}1 à 3) et vêtements occultes portés. Il brûle ({@value #SUN_DPS} dégâts par
 *       seconde en plein soleil) et éblouit (effets {@value #SUNBURN} et {@value #SUNBURN_LIGHT}) ; la vulnérabilité
 *       et le malus d'attaque sont dans {@link VampireDamageSystem}.</li>
 *   <li><b>Lumière purificatrice.</b> Près d'une torche ou d'une lanterne des chasseurs, ou d'une aura de lumière, le
 *       vampire perd {@value #PURIFYING_DPS} point de vie par seconde.</li>
 *   <li><b>Vision nocturne.</b> La nuit, une faible lumière rouge l'entoure (lumière d'entité, vue aussi par les
 *       autres joueurs). Elle ne remplace pas une lumière déjà posée (aura de lumière).</li>
 * </ul>
 * Tout est par joueur : chaque vampire a son composant {@link Vampire}, sauvegardé avec lui.
 */
public final class VampireSystem extends DelayedEntitySystem<EntityStore> {

    /** Préfixes des effets de repas du jeu (dossier Server/Entity/Effects/Food d'Assets.zip 0.7.2). */
    static final String[] FOOD_EFFECT_PREFIXES = {"Food_", "FruitVeggie_Buff_", "HealthRegen_Buff_", "Meat_Buff_"};
    static final String SUN_PROTECTION_PREFIX = "Nakasar_Sun_Protection_";
    static final String SUNBURN = "Nakasar_Sunburn";
    static final String SUNBURN_LIGHT = "Nakasar_Sunburn_Light";
    static final String SUN_CAUSE = "Nakasar_Sunlight";
    static final String PURIFYING_CAUSE = "Nakasar_Purifying_Light";
    static final String HEARTBEAT_SOUND = "SFX_Nakasar_Heartbeat";
    /** Dégâts par seconde en plein soleil. */
    static final float SUN_DPS = 2f;
    /** Dégâts par seconde près d'une lumière purificatrice. */
    static final float PURIFYING_DPS = 1f;
    static final float HEARTBEAT_RADIUS = 14f;
    /** Au-delà, l'éblouissement fort remplace le léger. */
    static final float STRONG_GLARE = 0.6f;

    /** Atténuation du soleil par niveau de potion (1 à 3) : part du soleil qui reste. */
    private static final float[] POTION_SUN_LEFT = {1f, 0.6f, 0.3f, 0f};
    /** Vêtements occultes : part du soleil qui reste quand on les porte. */
    private static final Map<String, Float> GARMENT_SUN_LEFT = Map.of(
            "Armor_Nakasar_Occult_Hood", 0.7f,
            "Armor_Nakasar_Occult_Mantle", 0.75f);
    /** Lumière de vision nocturne : faible et rougeâtre. */
    private static final ColorLight NIGHT_LIGHT = new ColorLight((byte) 6, (byte) 5, (byte) 2, (byte) 2);

    private static final float INTERVAL = 0.25f;
    private static final Query<EntityStore> QUERY = Query.and(Vampire.getComponentType(),
            Player.getComponentType(), TransformComponent.getComponentType(), EntityStatMap.getComponentType());

    private final PurifyingFireSystem purifyingFires;

    public VampireSystem(PurifyingFireSystem purifyingFires) {
        super(INTERVAL);
        this.purifyingFires = purifyingFires;
    }

    @Override
    public Query<EntityStore> getQuery() {
        return QUERY;
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false; // lit les blocs du monde et les feux purificateurs
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        Vampire vampire = chunk.getComponent(index, Vampire.getComponentType());
        EntityStatMap stats = chunk.getComponent(index, EntityStatMap.getComponentType());
        Vector3d position = chunk.getComponent(index, TransformComponent.getComponentType()).getPosition();
        if (buffer.getComponent(ref, DeathComponent.getComponentType()) != null) {
            return;
        }
        World world = buffer.getExternalData().getWorld();

        hunger(dt, ref, vampire, stats, world, buffer);
        sun(dt, ref, vampire, position, store, buffer);
        purifyingLight(dt, ref, vampire, position, store, buffer);
        nightVision(ref, vampire, store, buffer);
        if (vampire.getStage() == BloodStage.STARVING) {
            heartbeat(dt, ref, vampire, position, buffer);
        } else {
            vampire.heartbeatIn = 0f;
        }
    }

    private static void hunger(float dt, Ref<EntityStore> ref, Vampire vampire, EntityStatMap stats, World world,
                               CommandBuffer<EntityStore> buffer) {
        int daySeconds = world.getDaytimeDurationSeconds() + world.getNighttimeDurationSeconds();
        if (daySeconds > 0) {
            vampire.addBlood(-dt / (Vampire.DAYS_TO_STARVE * daySeconds));
        }
        BloodStage stage = vampire.getStage();
        if (stage != vampire.shownStage) {
            if (vampire.shownStage != null) {
                Vampires.removeEffect(ref, vampire.shownStage.effectId, buffer);
            }
            if (Vampires.applyEffect(ref, stage.effectId, -1f, buffer)) {
                vampire.shownStage = stage;
            }
        }

        HealthRegenState regen = buffer.getComponent(ref, HealthRegenState.getComponentType());
        if (regen == null) {
            regen = new HealthRegenState();
            regen.setRegenEnabled(false);
            buffer.putComponent(ref, HealthRegenState.getComponentType(), regen);
        } else if (regen.isRegenEnabled()) {
            regen.setRegenEnabled(false);
        }
        EntityStatValue health = stats.get(DefaultEntityStatTypes.getHealth());
        if (stage.regenPerSecond > 0f && health != null && health.get() > 0f && health.get() < health.getMax()) {
            stats.addStatValue(DefaultEntityStatTypes.getHealth(), stage.regenPerSecond * dt);
        }
        stripFoodEffects(ref, buffer);
    }

    /** Retire les effets de nourriture : un vampire ne tire rien des repas. */
    private static void stripFoodEffects(Ref<EntityStore> ref, CommandBuffer<EntityStore> buffer) {
        EffectControllerComponent effects = buffer.getComponent(ref, EffectControllerComponent.getComponentType());
        if (effects == null) {
            return;
        }
        for (ActiveEntityEffect active : effects.getAllActiveEntityEffects()) {
            EntityEffect effect = EntityEffect.getAssetMap().getAsset(active.getEntityEffectIndex());
            if (effect != null && effect.getId() != null && isFoodEffect(effect.getId())) {
                effects.removeEffect(ref, active.getEntityEffectIndex(), buffer);
            }
        }
    }

    private static boolean isFoodEffect(String id) {
        for (String prefix : FOOD_EFFECT_PREFIXES) {
            if (id.startsWith(prefix)) {
                return true;
            }
        }
        return false;
    }

    private static void sun(float dt, Ref<EntityStore> ref, Vampire vampire, Vector3d position,
                            Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        float sun = SunExposure.at(ref, position, store, buffer);
        if (sun > 0f) {
            sun *= protection(ref, buffer);
        }
        vampire.sun = sun;
        if (sun <= 0f) {
            vampire.pendingSunDamage = 0f;
            return;
        }
        Vampires.applyEffect(ref, sun >= STRONG_GLARE ? SUNBURN : SUNBURN_LIGHT, 1f, buffer);
        vampire.pendingSunDamage += SUN_DPS * sun * dt;
        vampire.pendingSunDamage = damage(ref, vampire.pendingSunDamage, SUN_CAUSE, buffer);
    }

    /** Part du soleil qui atteint le vampire malgré ses potions et ses vêtements (1 sans protection). */
    static float protection(Ref<EntityStore> ref, CommandBuffer<EntityStore> buffer) {
        float left = 1f;
        for (int level = POTION_SUN_LEFT.length - 1; level >= 1; level--) {
            if (Vampires.hasEffect(ref, SUN_PROTECTION_PREFIX + level, buffer)) {
                left = POTION_SUN_LEFT[level];
                break;
            }
        }
        if (left <= 0f) {
            return 0f;
        }
        InventoryComponent.Armor armor = buffer.getComponent(ref, InventoryComponent.Armor.getComponentType());
        ItemContainer worn = armor == null ? null : armor.getInventory();
        if (worn != null) {
            for (short slot = 0; slot < worn.getCapacity(); slot++) {
                ItemStack stack = worn.getItemStack(slot);
                if (stack != null && !ItemStack.isEmpty(stack)) {
                    left *= GARMENT_SUN_LEFT.getOrDefault(stack.getItemId(), 1f);
                }
            }
        }
        return left;
    }

    private void purifyingLight(float dt, Ref<EntityStore> ref, Vampire vampire, Vector3d position,
                                Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
        if (!purifyingFires.nearFire(buffer.getExternalData().getWorld().getChunkStore(), store, position)) {
            vampire.pendingLightDamage = 0f;
            return;
        }
        vampire.pendingLightDamage += PURIFYING_DPS * dt;
        vampire.pendingLightDamage = damage(ref, vampire.pendingLightDamage, PURIFYING_CAUSE, buffer);
    }

    /** Inflige les points entiers de {@code pending} (cause {@code causeId}) et renvoie le reste. */
    private static float damage(Ref<EntityStore> ref, float pending, String causeId, CommandBuffer<EntityStore> buffer) {
        if (pending < 1f) {
            return pending;
        }
        float amount = (float) Math.floor(pending);
        DamageCause cause = DamageCause.getAssetMap().getAsset(causeId);
        if (cause != null) {
            DamageSystems.executeDamage(ref, buffer, new Damage(new Damage.EnvironmentSource(causeId), cause, amount));
        }
        return pending - amount;
    }

    private static void nightVision(Ref<EntityStore> ref, Vampire vampire, Store<EntityStore> store,
                                    CommandBuffer<EntityStore> buffer) {
        if (buffer.getComponent(ref, LightAura.getComponentType()) != null) {
            return; // l'aura de lumière tient la lumière et rendra la nôtre à sa fin
        }
        DynamicLight light = buffer.getComponent(ref, DynamicLight.getComponentType());
        boolean night = !SunExposure.isDay(store);
        if (night && light == null) {
            buffer.putComponent(ref, DynamicLight.getComponentType(), new DynamicLight(new ColorLight(NIGHT_LIGHT)));
            vampire.nightLightByUs = true;
        } else if (!night && vampire.nightLightByUs) {
            removeNightLight(ref, vampire, buffer);
        }
    }

    /** Retire la lumière de vision nocturne si c'est la nôtre (matin, guérison). */
    static void removeNightLight(Ref<EntityStore> ref, Vampire vampire, CommandBuffer<EntityStore> buffer) {
        DynamicLight light = buffer.getComponent(ref, DynamicLight.getComponentType());
        if (vampire.nightLightByUs && light != null && NIGHT_LIGHT.equals(light.getColorLight())) {
            buffer.tryRemoveComponent(ref, DynamicLight.getComponentType());
        }
        vampire.nightLightByUs = false;
    }

    /** Affamé : le cœur du vivant le plus proche bat, plus vite à mesure qu'il approche. */
    private static void heartbeat(float dt, Ref<EntityStore> ref, Vampire vampire, Vector3d position,
                                  CommandBuffer<EntityStore> buffer) {
        vampire.heartbeatIn -= dt;
        if (vampire.heartbeatIn > 0f) {
            return;
        }
        Vector3d nearest = null;
        double nearestSq = HEARTBEAT_RADIUS * HEARTBEAT_RADIUS;
        for (Ref<EntityStore> other : TargetUtil.getAllEntitiesInSphere(position, HEARTBEAT_RADIUS, buffer)) {
            if (other.equals(ref) || !Vampires.isLiving(other, buffer)) {
                continue;
            }
            TransformComponent transform = buffer.getComponent(other, TransformComponent.getComponentType());
            if (transform == null) {
                continue;
            }
            double distanceSq = transform.getPosition().distanceSquared(position);
            if (distanceSq < nearestSq) {
                nearestSq = distanceSq;
                nearest = transform.getPosition();
            }
        }
        if (nearest == null) {
            vampire.heartbeatIn = 1f;
            return;
        }
        int sound = SoundEvent.getAssetMap().getIndexOrDefault(HEARTBEAT_SOUND, -1);
        if (sound >= 0) {
            SoundUtil.playSoundEvent3dToPlayer(ref, sound, SoundCategory.SFX,
                    nearest.x, nearest.y + 1.0, nearest.z, buffer);
        }
        // 0,6 s collé au vivant, 1,6 s au bord du rayon.
        vampire.heartbeatIn = 0.6f + (float) (Math.sqrt(nearestSq) / HEARTBEAT_RADIUS);
    }
}
