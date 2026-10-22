package dev.nakasar.hytale.fractals.hammer;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Corruption du marteau du culte, quatre fois par seconde dans la Falaise, par crans de {@value #CYCLE} s :
 * <ul>
 *   <li>recevoir le marteau coûte {@value #PICKUP_PART} des PV max ;</li>
 *   <li>le prendre en main sans Corruption ouvre le cran 1 : l'effet {@code Nakasar_Fractal_Corruption_<cran>} est
 *   posé pour {@value #CYCLE} s et se vide sous les yeux du joueur ;</li>
 *   <li>vidé, le cran monte de un si le marteau est encore en main, sinon il descend de un (à 0, plus rien) ;</li>
 *   <li>chaque cran : dégâts subis +8 % ; dès le cran 2, le porteur ne fait plus que 70 % de ses dégâts (filtre de
 *   {@code cliffside.CliffsideDamageFilter}) ; arriver au cran 3 étourdit {@value #STUN_3} s ; vouloir monter
 *   au-delà fait échapper le marteau (au sol, à ses pieds) et étourdit {@value #STUN_DROP} s.</li>
 * </ul>
 * Poser le marteau perd la charge Brise-sceau. Hors de la Falaise, le marteau est retiré (une fois par seconde).
 */
public final class HammerSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 0.25f;
    private static final float OUTSIDE_INTERVAL = 1f;
    public static final float PICKUP_PART = 0.10f;
    public static final float CYCLE = 10f;
    public static final int MAX_TIER = 3;
    public static final float STUN_3 = 2f;
    public static final float STUN_DROP = 3f;
    public static final String CAUSE = "Nakasar_Fractal_Corruption";
    public static final String STUN = "Hazard_Electric_Stun";
    private static final String TIER = "Nakasar_Fractal_Corruption_";
    private static final String MESSAGES = "nakasar_fractals_cliffside.hammer.";
    private static final Map<World, float[]> ELAPSED = Collections.synchronizedMap(new WeakHashMap<>());

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        float[] elapsed = ELAPSED.computeIfAbsent(world, w -> new float[1]);
        elapsed[0] += dt;
        boolean cliffside = "Cliffside".equals(FractalCatalog.fractalOf(world));
        float interval = cliffside ? INTERVAL : OUTSIDE_INTERVAL;
        if (elapsed[0] < interval || world.getPlayerRefs().isEmpty()) {
            return;
        }
        float step = elapsed[0];
        elapsed[0] = 0f;
        world.execute(() -> {
            if (cliffside) {
                step(world, step);
            } else {
                strip(world);
            }
        });
    }

    /** Hors de la Falaise : le marteau se dissipe. */
    private static void strip(World world) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid()) {
                continue;
            }
            Hammer.CARRIERS.remove(player.getUuid());
            if (Hammer.carries(store, ref) && Hammer.remove(store, ref)) {
                player.sendMessage(Message.translation(MESSAGES + "removed"));
            }
        }
    }

    private static void step(World world, float dt) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid()) {
                continue;
            }
            Hammer.Carrier carrier = Hammer.CARRIERS.computeIfAbsent(player.getUuid(), u -> new Hammer.Carrier());
            if (store.getComponent(ref, DeathComponent.getComponentType()) != null) {
                carrier.tier = 0;   // la mort efface les effets : on repart de zéro
                carrier.cycle = 0f;
                carrier.charged = false;
                continue;
            }
            boolean carrying = Hammer.carries(store, ref);
            if (carrying && !carrier.carrying) {
                Hurt.percent(store, ref, PICKUP_PART, CAUSE);
                player.sendMessage(Message.translation(MESSAGES + "taken"));
            }
            carrier.carrying = carrying;
            if (!carrying) {
                carrier.charged = false;
            }
            boolean holding = carrying && Hammer.holds(store, ref);
            if (carrier.tier == 0) {
                if (holding) {
                    setTier(store, ref, carrier, 1);
                }
            } else {
                carrier.cycle -= dt;
                if (carrier.cycle <= 0f) {
                    cycleEnd(store, ref, player, carrier, holding);
                }
            }
            Vector3d at = Telegraphs.position(store, ref);
            carrier.sinceFx += dt;
            if (at != null && carrier.sinceFx >= 0.5f && (carrier.charged || holding)) {
                carrier.sinceFx = 0f;
                Telegraphs.particle(store, carrier.charged ? "Nakasar_Fractal_Hammer_Charged" : "Nakasar_Fractal_Corruption_Pulse",
                        new Vector3d(at).add(0, 0.2, 0), 1f);
            }
        }
    }

    /** Un cran vient de se vider : on monte si le marteau est en main, on descend sinon. */
    private static void cycleEnd(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Hammer.Carrier carrier,
                                 boolean holding) {
        if (!holding) {
            setTier(store, ref, carrier, carrier.tier - 1);
            player.sendMessage(Message.translation(MESSAGES + (carrier.tier == 0 ? "cleansed" : "down"))
                    .param("tier", carrier.tier));
            return;
        }
        if (carrier.tier >= MAX_TIER) {
            Vector3d at = Telegraphs.position(store, ref);
            Hammer.remove(store, ref);
            if (at != null) {
                Hammer.drop(store, at);
            }
            carrier.carrying = false;
            carrier.charged = false;
            Hurt.effect(store, ref, STUN, STUN_DROP);
            setTier(store, ref, carrier, MAX_TIER);   // la Corruption reste ; elle descendra sans le marteau
            player.sendMessage(Message.translation(MESSAGES + "dropped"));
            return;
        }
        setTier(store, ref, carrier, carrier.tier + 1);
        if (carrier.tier == MAX_TIER) {
            Hurt.effect(store, ref, STUN, STUN_3);
            player.sendMessage(Message.translation(MESSAGES + "stun"));
        } else {
            player.sendMessage(Message.translation(MESSAGES + "up").param("tier", carrier.tier));
        }
    }

    /** Passe au cran `tier` : l'effet du cran est (re)posé pour un cycle entier, celui de l'ancien cran retiré. */
    private static void setTier(Store<EntityStore> store, Ref<EntityStore> ref, Hammer.Carrier carrier, int tier) {
        for (int t = 1; t <= MAX_TIER; t++) {
            if (t != tier) {
                Hurt.clear(store, ref, TIER + t);
            }
        }
        carrier.tier = Math.max(0, Math.min(MAX_TIER, tier));
        carrier.cycle = carrier.tier > 0 ? CYCLE : 0f;
        if (carrier.tier > 0) {
            Hurt.effect(store, ref, TIER + carrier.tier, CYCLE);
        }
    }
}
