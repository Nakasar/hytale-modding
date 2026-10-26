package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * La terrasse de la Tristesse (GW2 : la Tristesse de la montagne prisonnière des rochers tombés, l'orbe sombre et le
 * Marché des marées). On y tombe depuis le surplomb (chute amortie). Cinq rochers à briser autour de l'îlot moussu ;
 * l'orbe sombre au-dessus lie un joueur ({@link Tether}) : ses charges font frapper plus fort, mais à
 * {@value Tether#MAX_STACKS} la marée le submerge ; il faut se passer le lien. Toutes les {@value #SPLASH_EVERY} s, des
 * éclats d'eau : un cercle rouge de {@value #SPLASH_RADIUS} blocs sous chaque joueur. Les rochers brisés, la Tristesse
 * est libre. Personne sur la terrasse pendant {@value SunquaPeak#RESET_SECONDS} s : les rochers retombent, neufs.
 */
final class Sorrow {

    static final float SPLASH_FIRST = 6f;
    static final float SPLASH_EVERY = 10f;
    static final double SPLASH_RADIUS = 2.5;
    static final float SPLASH_WINDUP = 1.6f;
    static final float SPLASH_PART = 0.1f;

    private final Tether tether = new Tether();
    private Ref<EntityStore> sorrow;
    private final List<Ref<EntityStore>> boulders = new ArrayList<>();
    private boolean engaged;
    private boolean checkpoint;
    private int broken;
    private float idle;
    private float splash;
    private float glow;
    private int epoch;

    Tether tether() {
        return tether;
    }

    /** Vrai quand les rochers sont brisés. */
    boolean step(World world, Store<EntityStore> store, SunquaPeak.State st, List<PlayerRef> players, float dt) {
        Vector3d c = Spawns.point(SunquaPeakLayout.SORROW);
        double radius = SunquaPeakLayout.SORROW_RADIUS;
        List<PlayerRef> here = SunquaPeak.near(store, players, c, radius + 3);
        if (!engaged) {
            if (!SunquaPeak.near(store, players, c, radius).isEmpty()) {
                engage(world, store, st, c);
            }
            return false;
        }
        if (here.isEmpty()) {
            idle += dt;
            if (idle >= SunquaPeak.RESET_SECONDS) {
                clear(world, store);
                Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "sorrow.reset"));
            }
            return false;
        }
        idle = 0f;
        for (int i = boulders.size() - 1; i >= 0; i--) {
            if (!Spawns.alive(store, boulders.get(i))) {
                Vector3d at = Telegraphs.position(store, boulders.get(i));
                boulders.remove(i);
                broken++;
                if (at != null) {
                    Telegraphs.particle(store, "Nakasar_Fractal_Boulder_Burst", at, 1.5f);
                }
                Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "sorrow.boulder")
                        .param("count", broken).param("total", SunquaPeakLayout.BOULDERS.length));
            }
        }
        if (boulders.isEmpty()) {
            tether.stop(world, store);
            epoch++;
            Telegraphs.particle(store, "Nakasar_Fractal_Calm_Glow", c, 2f);
            Spawns.remove(store, sorrow);
            sorrow = null;
            return true;
        }
        Vector3d orb = Spawns.point(SunquaPeakLayout.DARK_ORB);
        glow += dt;
        if (glow >= 0.5f) {
            glow = 0f;
            Telegraphs.particle(store, "Nakasar_Fractal_Dark_Orb", orb, 1.2f);
        }
        tether.step(world, store, orb, here, dt);
        splash += dt;
        if (splash >= SPLASH_EVERY) {
            splash = 0f;
            splash(world, store, here);
        }
        return false;
    }

    private void engage(World world, Store<EntityStore> store, SunquaPeak.State st, Vector3d c) {
        engaged = true;
        idle = 0f;
        broken = 0;
        splash = SPLASH_EVERY - SPLASH_FIRST;
        epoch++;
        if (!checkpoint) {
            checkpoint = true;
            Gates.checkpoint(world, SunquaPeakLayout.SORROW, SunquaPeak.MESSAGES + "checkpoint");
        }
        sorrow = Spawns.spawn(store, SunquaPeak.SORROW, c, 0f);
        if (sorrow != null && sorrow.isValid()) {
            store.ensureAndGetComponent(sorrow, Invulnerable.getComponentType());
        }
        for (double[] b : SunquaPeakLayout.BOULDERS) {
            Vector3d at = Spawns.point(b);
            Ref<EntityStore> ref = st.foe(world, store, SunquaPeak.BOULDER, at, c, false);
            if (ref != null) {
                boulders.add(ref);
            }
        }
        tether.begin();
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "sorrow.enter"));
    }

    private void splash(World world, Store<EntityStore> store, List<PlayerRef> here) {
        float windup = SPLASH_WINDUP * FractalRuns.windupFactor(world);
        long now = System.nanoTime();
        List<Telegraphs.Circle> circles = new ArrayList<>();
        for (PlayerRef p : here) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null) {
                circles.add(new Telegraphs.Circle(at, SPLASH_RADIUS, now, windup));
            }
        }
        int e = epoch;
        TelegraphSystem.start(world, (w, s, t) -> {
            if (epoch != e) {
                return true;
            }
            boolean ready = true;
            for (Telegraphs.Circle circle : circles) {
                ready &= circle.step(s, t);
            }
            if (!ready) {
                return false;
            }
            for (Telegraphs.Circle circle : circles) {
                Telegraphs.particle(s, "Water_Splash", circle.origin(), 1.2f);
                SunquaPeak.strike(w, s, circle, SPLASH_PART, null, 0f);
            }
            return true;
        });
    }

    private void clear(World world, Store<EntityStore> store) {
        tether.stop(world, store);
        Spawns.removeAll(store, boulders);
        boulders.clear();
        Spawns.remove(store, sorrow);
        sorrow = null;
        engaged = false;
        epoch++;
    }
}
