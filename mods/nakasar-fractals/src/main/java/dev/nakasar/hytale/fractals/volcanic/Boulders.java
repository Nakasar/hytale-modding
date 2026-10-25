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
 * Le couloir aux rochers du Volcanique, galerie courbe qui descend vers le nord : tant qu'un joueur est dans le
 * couloir, un rocher en feu sort de la bouche du haut toutes les {@value #INTERVAL} s (grondement {@value #RUMBLE} s
 * avant), puis dévale la pente le long de {@link VolcanicLayout#BOULDER_PATH} à {@value #SPEED} blocs/s sur toute la
 * largeur de la voie, un cercle rouge devant lui. Qui est sur sa route (hors des niches) perd {@value #PART} des PV
 * max et brûle ; il laisse derrière lui une traînée de feu ({@value #TRAIL_LIFE} s).
 */
final class Boulders {

    static final float INTERVAL = 5f;
    static final float RUMBLE = 1.5f;
    static final double SPEED = 9;
    static final float PART = 0.60f;
    static final float TRAIL_LIFE = 4f;
    static final double TRAIL_RADIUS = 1.5;
    static final double TRAIL_STEP = 2.5;
    /** Un joueur à moins de la demi-largeur de la voie (+ cette marge : le bord irrégulier) du rocher est touché ; le
     *  fond des niches est au-delà. */
    static final double HIT_MARGIN = 1.4;
    /** Le couloir pour le déclenchement : à moins de la demi-largeur + cette marge du chemin. */
    static final double AREA_MARGIN = 3;
    /**
     * Les premiers et derniers blocs du chemin ne comptent ni pour le déclenchement ni pour les coups : derrière la porte
     * du camp, le rocher sort de la bouche sans toucher ; il se brise avant le palier nord (point de retour).
     */
    static final int SAFE_START = 4;
    static final int SAFE_END = 9;

    private static final class Boulder {
        /** Distance parcourue le long du chemin (un point par bloc). */
        double s;
        double lastTrail;
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

    /** Point du chemin à la distance `s` (interpolé entre deux points). */
    static Vector3d along(double s) {
        double[][] path = VolcanicLayout.BOULDER_PATH;
        int last = path.length - 1;
        double t = Math.max(0, Math.min(s, last));
        int i = Math.min((int) t, last - 1);
        double f = t - i;
        double[] a = path[i];
        double[] b = path[i + 1];
        return new Vector3d(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f);
    }

    /** Vrai si `at` est dans le couloir (près du chemin, à sa hauteur). */
    static boolean inCorridor(Vector3d at) {
        if (VolcanicLayout.CAMP.contains(at.x(), at.y(), at.z())) {
            return false;
        }
        double reach = VolcanicLayout.CORRIDOR_HALF_WIDTH + AREA_MARGIN;
        double[][] path = VolcanicLayout.BOULDER_PATH;
        for (int i = SAFE_START; i < path.length - SAFE_END; i++) {
            double[] point = path[i];
            if (Math.hypot(at.x() - point[0], at.z() - point[2]) <= reach && at.y() >= point[1] - 2 && at.y() <= point[1] + 6) {
                return true;
            }
        }
        return false;
    }

    static boolean anyInCorridor(Store<EntityStore> store, List<PlayerRef> players) {
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null && inCorridor(at)) {
                return true;
            }
        }
        return false;
    }

    void step(World world, Store<EntityStore> store, List<PlayerRef> players, boolean active, float dt) {
        double end = VolcanicLayout.BOULDER_PATH.length - 1 - SAFE_END;   // il se brise avant le palier nord
        if (active) {
            clock += dt;
            if (clock >= INTERVAL) {
                clock = 0f;
                boulders.add(new Boulder());
                Telegraphs.sound(store, "SFX_Goblin_Feastmaster_Slam", along(0));
            }
        }
        double reach = VolcanicLayout.CORRIDOR_HALF_WIDTH + HIT_MARGIN;
        for (Iterator<Boulder> it = boulders.iterator(); it.hasNext(); ) {
            Boulder b = it.next();
            if (b.wait > 0f) {
                b.wait -= dt;
                Telegraphs.particle(store, "Nakasar_Fractal_Boulder_Rumble", along(1), 1f);
                continue;
            }
            b.s = Math.min(b.s + SPEED * dt, end);
            Vector3d at = along(b.s);
            boolean harmful = b.s >= SAFE_START;
            Telegraphs.particle(store, "Nakasar_Fractal_Boulder", at, 2f);
            double ahead = b.s + SPEED * 0.5;
            if (harmful && ahead <= end) {
                // Cercle de la taille exacte de la zone touchée (reach, corps compris), là où le rocher sera dans 0,5 s ;
                // aucun au-delà de `end`, où il se brise sans plus toucher personne.
                Telegraphs.circle(store, along(ahead), reach - Telegraphs.BODY, 0.5f);
            }
            for (PlayerRef player : players) {
                Ref<EntityStore> ref = player.getReference();
                Vector3d p = Telegraphs.position(store, ref);
                if (p == null || !harmful || b.hit.contains(player.getUuid()) || Telegraphs.horizontal(p, at) > reach
                        || p.y() < at.y() - 1 || p.y() > at.y() + 3) {
                    continue;
                }
                b.hit.add(player.getUuid());
                Telegraphs.particle(store, "Nakasar_Fractal_Rock_Impact", new Vector3d(p).add(0, 0.5, 0), 1f);
                Hurt.percent(store, ref, PART, Volcanic.FIRE_CAUSE);
                Hurt.effect(store, ref, "Burn", 4f);
                player.sendMessage(Message.translation(Volcanic.MESSAGES + "boulder.hit"));
            }
            if (harmful && b.s - b.lastTrail >= TRAIL_STEP) {
                b.lastTrail = b.s;
                trails.add(new Trail(at));
            }
            if (b.s >= end) {
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
