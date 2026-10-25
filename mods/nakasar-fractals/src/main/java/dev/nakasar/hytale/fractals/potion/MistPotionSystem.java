package dev.nakasar.hytale.fractals.potion;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.entity.effect.ActiveEntityEffect;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.potion.MistPotions.Kind;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Potions des Brumes, quatre fois par seconde dans chaque monde où sont des joueurs :
 * <ul>
 *   <li>le temps restant de chaque potion s'écoule ({@link MistPotionState#elapse}) ;</li>
 *   <li>les effets affichés suivent les piles : {@code Nakasar_Fractal_Mist_<Type>_<piles>} dans une fractale,
 *   {@code ..._Dormant} (gris, sans bonus) ailleurs, avec la durée restante ; les autres crans sont retirés. Un joueur
 *   mort est laissé tel quel, ses effets reviennent quand il réapparaît ;</li>
 *   <li>Mobilité, dans une fractale : chaque gain d'endurance depuis le passage précédent est augmenté de
 *   {@link Kind#STAMINA_PER_STACK} par pile.</li>
 * </ul>
 */
public final class MistPotionSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 0.25f;
    /** Écart toléré entre la durée de l'effet affiché et celle de la potion avant de reposer l'effet. */
    private static final float DRIFT = 5f;
    private static final Map<World, float[]> ELAPSED = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        float[] elapsed = ELAPSED.computeIfAbsent(world, w -> new float[1]);
        elapsed[0] += dt;
        if (elapsed[0] < INTERVAL) {
            return;
        }
        float step = elapsed[0];
        elapsed[0] = 0f;
        if (!world.getPlayerRefs().isEmpty()) {
            world.execute(() -> step(world, step));
        }
    }

    private static void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        boolean active = MistPotions.active(world);
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            MistPotionState state = ref == null || !ref.isValid() ? null
                    : store.getComponent(ref, MistPotionState.getComponentType());
            if (state == null) {
                continue;
            }
            state.elapse(dt);
            if (store.getComponent(ref, DeathComponent.getComponentType()) != null) {
                state.lastStamina = Float.NaN;
                continue;
            }
            for (Kind kind : Kind.values()) {
                sync(store, ref, kind, state.stacks(kind), state.seconds(kind), active);
            }
            boostStamina(store, ref, state, active ? state.stacks(Kind.MOBILITY) : 0);
        }
    }

    /** Pose l'effet du bon cran (durée restante) et retire les autres crans de ce type. */
    private static void sync(Store<EntityStore> store, Ref<EntityStore> ref, Kind kind, int stacks, float seconds, boolean active) {
        String wanted = stacks > 0 ? kind.effect(stacks, active) : null;
        for (int n = 1; n <= MistPotions.MAX_STACKS; n++) {
            for (boolean a : new boolean[]{true, false}) {
                String id = kind.effect(n, a);
                if (!id.equals(wanted) && Hurt.has(store, ref, id)) {
                    Hurt.clear(store, ref, id);
                }
            }
        }
        if (wanted != null && Math.abs(remaining(store, ref, wanted) - seconds) > DRIFT) {
            Hurt.effect(store, ref, wanted, seconds);
        }
    }

    /** Secondes restantes de l'effet `effectId` sur l'entité (-1 s'il n'est pas actif). */
    private static float remaining(Store<EntityStore> store, Ref<EntityStore> ref, String effectId) {
        int index = EntityEffect.getAssetMap().getIndexOrDefault(effectId, -1);
        EffectControllerComponent effects = store.getComponent(ref, EffectControllerComponent.getComponentType());
        ActiveEntityEffect effect = index < 0 || effects == null ? null : effects.getActiveEffects().get(index);
        return effect == null ? -1f : effect.getRemainingDuration();
    }

    private static void boostStamina(Store<EntityStore> store, Ref<EntityStore> ref, MistPotionState state, int stacks) {
        EntityStatMap stats = store.getComponent(ref, EntityStatMap.getComponentType());
        EntityStatValue stamina = stats == null ? null : stats.get(DefaultEntityStatTypes.getStamina());
        if (stacks <= 0 || stamina == null) {
            state.lastStamina = Float.NaN;
            return;
        }
        float now = stamina.get();
        if (!Float.isNaN(state.lastStamina) && now > state.lastStamina && now < stamina.getMax()) {
            float bonus = (now - state.lastStamina) * Kind.STAMINA_PER_STACK * stacks;
            stats.addStatValue(DefaultEntityStatTypes.getStamina(), Math.min(bonus, stamina.getMax() - now));
            now = stats.get(DefaultEntityStatTypes.getStamina()).get();
        }
        state.lastStamina = now;
    }

    public static void clearAll() {
        ELAPSED.clear();
    }
}
