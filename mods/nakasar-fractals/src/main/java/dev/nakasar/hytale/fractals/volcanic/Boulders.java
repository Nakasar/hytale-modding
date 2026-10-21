package dev.nakasar.hytale.fractals.volcanic;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * Le couloir aux rochers du Volcanique : tant qu'un joueur est dans le couloir, un rocher en feu sort de la bouche du
 * volcan toutes les {@value #INTERVAL} s (grondement {@value #RUMBLE} s avant), puis dévale vers le sud à
 * {@value #SPEED} blocs/s sur toute la largeur, un cercle rouge devant lui. Qui est sur sa route (hors des niches)
 * perd {@value #PART} des PV max et brûle ; il laisse derrière lui une traînée de feu ({@value #TRAIL_LIFE} s).
 */
final class Boulders {

    static final float INTERVAL = 5f;
    static final float RUMBLE = 1.5f;
    static final double SPEED = 9;
    static final float PART = 0.60f;
    static final float TRAIL_LIFE = 4f;
    static final double TRAIL_RADIUS = 1.5;
    static final double TRAIL_STEP = 2.5;

    private static final class Boulder {
        double z = VolcanicLayout.BOULDER_START[2];
        double lastTrail = z;
        float wait = RUMBLE;
        final Set<UUID> hit = new HashSet<>();
    }

    private static final class Trail {
        final Vector3d at;
        float life;
        float tick;

        Trail(Vector3d at) {
            this.at = at;
        }
    }

    private final List<Boulder> boulders = new ArrayList<>();
    private final List<Trail> trails = new ArrayList<>();
    private float clock = INTERVAL - 1f;

    void step(World world, Store<EntityStore> store, List<PlayerRef> players, boolean active, float dt) {
        double[] start = VolcanicLayout.BOULDER_START;
        double x = start[0];
        double y = start[1];
        if (active) {
            clock += dt;
            if (clock >= INTERVAL) {
                clock = 0f;
                boulders.add(new Boulder());
                Telegraphs.sound(store, "SFX_Goblin_Feastmaster_Slam", new Vector3d(x, y, start[2]));
            }
        }
        double x0 = VolcanicLayout.CORRIDOR_X0;
        double x1 = VolcanicLayout.CORRIDOR_X1 + 1;
        for (Iterator<Boulder> it = boulders.iterator(); it.hasNext(); ) {
            Boulder b = it.next();
            if (b.wait > 0f) {
                b.wait -= dt;
                Telegraphs.particle(store, "Nakasar_Fractal_Boulder_Rumble", new Vector3d(x, y, b.z - 1), 1f);
                continue;
            }
            double from = b.z;
            b.z = Math.min(b.z + SPEED * dt, VolcanicLayout.BOULDER_END_Z);
            Vector3d at = new Vector3d(x, y, b.z);
            Telegraphs.particle(store, "Nakasar_Fractal_Boulder", at, 2f);
            Telegraphs.circle(store, new Vector3d(x, y, b.z + 3), 3.5, 0.5f);
            for (PlayerRef player : players) {
                Ref<EntityStore> ref = player.getReference();
                Vector3d p = Telegraphs.position(store, ref);
                if (p == null || b.hit.contains(player.getUuid()) || p.x() < x0 || p.x() > x1
                        || p.z() < from - 1.5 || p.z() > Math.min(b.z + 1.5, VolcanicLayout.BOULDER_END_Z) || p.y() < y - 1 || p.y() > y + 3) {
                    continue;
                }
                b.hit.add(player.getUuid());
                Telegraphs.particle(store, "Nakasar_Fractal_Rock_Impact", new Vector3d(p).add(0, 0.5, 0), 1f);
                Hurt.percent(store, ref, PART, Volcanic.FIRE_CAUSE);
                Hurt.effect(store, ref, "Burn", 4f);
                player.sendMessage(Message.translation(Volcanic.MESSAGES + "boulder.hit"));
            }
            if (b.z - b.lastTrail >= TRAIL_STEP) {
                b.lastTrail = b.z;
                trails.add(new Trail(new Vector3d(x, y, b.z)));
            }
            if (b.z >= VolcanicLayout.BOULDER_END_Z) {
                Telegraphs.particle(store, "Nakasar_Fractal_Rock_Impact", at, 1.5f);
                it.remove();
            }
        }
        for (Iterator<Trail> it = trails.iterator(); it.hasNext(); ) {
            Trail t = it.next();
            t.life += dt;
            t.tick += dt;
            if (t.life >= TRAIL_LIFE) {
                it.remove();
                continue;
            }
            if (t.tick < 1f) {
                continue;
            }
            t.tick = 0f;
            Telegraphs.particle(store, "Nakasar_Fractal_Fire_Trail", t.at, 1f);
            for (PlayerRef player : players) {
                Vector3d p = Telegraphs.position(store, player.getReference());
                if (p != null && Telegraphs.horizontal(p, t.at) <= TRAIL_RADIUS && Math.abs(p.y() - t.at.y()) <= 2) {
                    Hurt.effect(store, player.getReference(), "Burn", 2f);
                }
            }
        }
    }
}
