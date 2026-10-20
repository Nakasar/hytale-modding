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
 * Corruption du marteau du culte, quatre fois par seconde dans la Falaise :
 * <ul>
 *   <li>le prendre en main (le marteau arrive dans l'inventaire) coûte {@value #PICKUP_PART} des PV max ;</li>
 *   <li>porté, +1 charge par seconde ; posé, -{@value #DECAY} par seconde, et la charge Brise-sceau se perd ;</li>
 *   <li>paliers 10/20/30 : effets {@code Nakasar_Fractal_Corruption_1..3} (dégâts subis +8 % par palier) ; dès 20 le
 *   porteur ne fait plus que 70 % de ses dégâts (filtre de {@code cliffside.CliffsideDamageFilter}) ;</li>
 *   <li>à 30, étourdi {@value #STUN_30} s ; à 40, le marteau lui échappe (au sol, à ses pieds) et il est étourdi
 *   {@value #STUN_40} s.</li>
 * </ul>
 * Hors de la Falaise, le marteau est retiré de l'inventaire (une fois par seconde).
 */
public final class HammerSystem extends TickingSystem<EntityStore> {

    private static final float INTERVAL = 0.25f;
    private static final float OUTSIDE_INTERVAL = 1f;
    public static final float PICKUP_PART = 0.10f;
    public static final float DECAY = 4f;
    public static final float STUN_30 = 2f;
    public static final float STUN_40 = 3f;
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
            if (ref == null || !ref.isValid() || store.getComponent(ref, DeathComponent.getComponentType()) != null) {
                continue;
            }
            Hammer.Carrier carrier = Hammer.CARRIERS.computeIfAbsent(player.getUuid(), u -> new Hammer.Carrier());
            boolean carrying = Hammer.carries(store, ref);
            if (carrying && !carrier.carrying) {
                Hurt.percent(store, ref, PICKUP_PART, CAUSE);
                player.sendMessage(Message.translation(MESSAGES + "taken"));
            }
            carrier.carrying = carrying;
            Vector3d at = Telegraphs.position(store, ref);
            if (carrying) {
                carrier.stacks += dt;
                if (carrier.stacks >= 40f) {
                    Hammer.remove(store, ref);
                    if (at != null) {
                        Hammer.drop(store, at);
                    }
                    carrier.carrying = false;
                    carrier.charged = false;
                    Hurt.effect(store, ref, STUN, STUN_40);
                    player.sendMessage(Message.translation(MESSAGES + "dropped"));
                } else if (carrier.stacks >= 30f && !carrier.stunnedAt30) {
                    carrier.stunnedAt30 = true;
                    Hurt.effect(store, ref, STUN, STUN_30);
                    player.sendMessage(Message.translation(MESSAGES + "stun"));
                }
            } else {
                carrier.stacks = Math.max(0f, carrier.stacks - DECAY * dt);
                carrier.charged = false;
                if (carrier.stacks < 30f) {
                    carrier.stunnedAt30 = false;
                }
            }
            int tier = carrier.stacks >= 30f ? 3 : carrier.stacks >= 20f ? 2 : carrier.stacks >= 10f ? 1 : 0;
            if (tier > 0) {
                Hurt.effect(store, ref, TIER + tier, 0.6f);
            }
            carrier.sinceFx += dt;
            if (at != null && carrier.sinceFx >= 0.5f && (carrier.charged || carrier.carrying)) {
                carrier.sinceFx = 0f;
                Telegraphs.particle(store, carrier.charged ? "Nakasar_Fractal_Hammer_Charged" : "Nakasar_Fractal_Corruption_Pulse",
                        new Vector3d(at).add(0, 0.2, 0), 1f);
            }
        }
    }
}
