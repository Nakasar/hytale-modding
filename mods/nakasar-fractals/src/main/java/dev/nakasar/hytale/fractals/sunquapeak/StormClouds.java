package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.List;

/**
 * Nuages d'orage de la Voix et du front d'orage d'Ai (GW2 : on les disperse d'un saut sous Bond chargé). Un nuage flotte
 * à {@value #HEIGHT_HINT} blocs du sol ; on le disperse en sautant dedans : pieds à moins de {@value #REACH} blocs de son
 * axe et pas plus de {@value #BELOW} blocs sous lui (hors de portée sans au moins deux charges). Tant qu'il en reste, la
 * foudre tombe : un cercle de {@value #BOLT_RADIUS} blocs sous un joueur au hasard toutes les {@value #BOLT_EVERY} s.
 */
final class StormClouds {

    static final int HEIGHT_HINT = 5;
    static final double REACH = 2.5;
    static final double BELOW = 1.5;
    static final float BOLT_EVERY = 3f;
    static final double BOLT_RADIUS = 2.5;
    static final float BOLT_WINDUP = 1.5f;
    static final float BOLT_PART = 0.12f;

    private final double[][] points;
    private final boolean[] gone;
    private boolean active;
    private float puff;
    private float bolt;
    private int epoch;

    StormClouds(double[][] points) {
        this.points = points;
        this.gone = new boolean[points.length];
    }

    void begin() {
        active = true;
        java.util.Arrays.fill(gone, false);
        puff = 1f;
        bolt = 0f;
        epoch++;
    }

    void stop() {
        active = false;
        epoch++;
    }

    boolean active() {
        return active;
    }

    /** Un pas : nuages, dispersions, foudre. Vrai quand le dernier nuage vient d'être dispersé. */
    boolean step(World world, Store<EntityStore> store, List<PlayerRef> here, float dt) {
        if (!active) {
            return false;
        }
        puff += dt;
        boolean show = puff >= 1f;
        if (show) {
            puff = 0f;
        }
        int left = 0;
        for (int i = 0; i < points.length; i++) {
            if (gone[i]) {
                continue;
            }
            Vector3d c = Spawns.point(points[i]);
            if (show) {
                Telegraphs.particle(store, "Nakasar_Fractal_Storm_Cloud", c, 1.4f);
            }
            for (PlayerRef p : here) {
                Vector3d at = Telegraphs.position(store, p.getReference());
                if (at != null && Telegraphs.horizontal(at, c) <= REACH && at.y() >= c.y() - BELOW && at.y() <= c.y() + 2) {
                    gone[i] = true;
                    Telegraphs.particle(store, "Nakasar_Fractal_Storm_Disperse", c, 1.5f);
                    Telegraphs.sound(store, "SFX_Ability_Wind_Strike_Slash", c);
                    break;
                }
            }
            if (!gone[i]) {
                left++;
            } else {
                Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "voice.cloud")
                        .param("count", points.length - remaining()).param("total", points.length));
            }
        }
        if (left == 0) {
            active = false;
            epoch++;
            return true;
        }
        bolt += dt;
        if (bolt >= BOLT_EVERY && !here.isEmpty()) {
            bolt = 0f;
            bolt(world, store, here);
        }
        return false;
    }

    private int remaining() {
        int n = 0;
        for (boolean g : gone) {
            n += g ? 0 : 1;
        }
        return n;
    }

    private void bolt(World world, Store<EntityStore> store, List<PlayerRef> here) {
        PlayerRef target = here.get((int) (Math.random() * here.size()));
        Vector3d at = Telegraphs.position(store, target.getReference());
        if (at == null) {
            return;
        }
        Telegraphs.Circle circle = new Telegraphs.Circle(at, BOLT_RADIUS, System.nanoTime(),
                BOLT_WINDUP * FractalRuns.windupFactor(world));
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (epoch != e) {
                return true;
            }
            if (!circle.step(s, t)) {
                return false;
            }
            Telegraphs.particle(s, "Lightning", circle.origin(), 1f);
            SunquaPeak.strike(w, s, circle, BOLT_PART, "Nakasar_Fractal_Dazed", 1.5f);
            return true;
        });
    }
}
