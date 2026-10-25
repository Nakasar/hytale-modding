package dev.nakasar.hytale.fractals.potion;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
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
 *   <li>le temps restant de chaque potion s'écoule ({@link MistPotionState#elapse}) ; hors des fractales et de
 *   l'Observatoire (retour dans le monde), toutes les piles sont retirées (Kevin, 25 octobre 2026) ;</li>
 *   <li>les effets affichés suivent les piles : {@code Nakasar_Fractal_Mist_<Type>_<piles>} dans une fractale,
 *   {@code ..._Dormant} (gris, sans bonus) dans l'Observatoire, avec la durée restante ; les autres crans sont retirés. Un joueur
 *   mort est laissé tel quel, ses effets reviennent quand il réapparaît ;</li>
 *   <li>Mobilité, dans une fractale : chaque gain d'endurance depuis le passage précédent est augmenté de
 *   {@link Kind#STAMINA_PER_STACK} par pile.</li>
 * </ul>
 */
public final class MistPotionSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 0.25f;
    /** Écart toléré quand l'effet affiché dure plus longtemps que la potion. */
    private static final float DRIFT = 5f;
    /** Potion rebue : la durée de la potion dépasse celle de l'effet affiché de plus que cela, l'effet est reposé. */
    private static final float REFRESH = 1f;
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
        boolean kept = MistPotions.kept(world);
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            MistPotionState state = ref == null || !ref.isValid() ? null
                    : store.getComponent(ref, MistPotionState.getComponentType());
            if (state == null || state.isIdle()) {
                continue;
            }
            if (kept) {
                state.elapse(dt);
            } else {
                state.clear();
            }
            if (store.getComponent(ref, DeathComponent.getComponentType()) != null) {
                state.lastStamina = Float.NaN;
                continue;
            }
            if (!state.swept) {
                sweep(store, ref);
                state.swept = true;
            }
            for (Kind kind : Kind.values()) {
                sync(store, ref, state, kind, active);
            }
            boostStamina(store, ref, state, active ? state.stacks(Kind.MOBILITY) : 0);
        }
    }

    /** Retire tous les crans, une fois par chargement du joueur (effets sauvegardés d'une session précédente). */
    private static void sweep(Store<EntityStore> store, Ref<EntityStore> ref) {
        for (Kind kind : Kind.values()) {
            for (int n = 1; n <= MistPotions.MAX_STACKS; n++) {
                Hurt.clear(store, ref, kind.effect(n, true));
                Hurt.clear(store, ref, kind.effect(n, false));
            }
        }
    }

    /**
     * Pose l'effet du bon cran avec la durée restante et retire le cran affiché avant. L'effet est reposé s'il manque
     * (mort, retrait), si la potion a été rebue (durée remontée) ou s'il dépasse la potion de plus de {@value #DRIFT} s.
     */
    private static void sync(Store<EntityStore> store, Ref<EntityStore> ref, MistPotionState state, Kind kind, boolean active) {
        int k = kind.ordinal();
        int stacks = state.stacks(kind);
        float seconds = state.seconds(kind);
        String wanted = stacks > 0 ? kind.effect(stacks, active) : null;
        if (state.shown[k] != null && !state.shown[k].equals(wanted)) {
            Hurt.clear(store, ref, state.shown[k]);
        }
        state.shown[k] = wanted;
        if (wanted == null) {
            return;
        }
        float remaining = Hurt.remaining(store, ref, wanted);
        if (remaining < 0f || seconds - remaining > REFRESH || remaining - seconds > DRIFT) {
            Hurt.effect(store, ref, wanted, seconds);
        }
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
