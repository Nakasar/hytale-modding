package dev.nakasar.hytale.fractals.sunquapeak;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Gates;
import dev.nakasar.hytale.fractals.arena.Moves;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * La corniche des cascades (GW2 : le chemin de l'eau). Toutes les {@value #SURGE_EVERY} s, les cascades déferlent :
 * une bande rouge de {@link SunquaPeakLayout#SURGE_LENGTH} x {@link SunquaPeakLayout#SURGE_WIDTH} blocs au pied de chaque
 * chute (même constantes que le test du coup), puis qui y est encore est jeté vers le vide et mis à terre (le filet
 * anti-chute le ramène au point de retour). Trois élémentaires d'eau effrayés se cachent dans des niches : un joueur
 * accroupi à moins de {@value #CALM_REACH} blocs pendant {@value #CALM_SECONDS} s le rassure ; au premier qui s'y essaie,
 * deux esprits de l'eau enragés surgissent. Les trois rassurés, la barrière s'ouvre.
 */
final class WaterPath {

    static final float SURGE_FIRST = 6f;
    static final float SURGE_EVERY = 9f;
    static final float SURGE_WINDUP = 2f;
    static final float SURGE_PART = 0.08f;
    static final double SURGE_PUSH = 13;
    static final double CALM_REACH = 3;
    static final float CALM_SECONDS = 3f;
    static final int SPRITES = 2;

    private boolean begun;
    private final Ref<EntityStore>[] frightened = newRefs(SunquaPeakLayout.NOOKS.length);
    private final float[] calm = new float[SunquaPeakLayout.NOOKS.length];
    private final boolean[] calmed = new boolean[SunquaPeakLayout.NOOKS.length];
    private final boolean[] stirred = new boolean[SunquaPeakLayout.NOOKS.length];
    private final List<Ref<EntityStore>> sprites = new ArrayList<>();
    private float surge;
    private float glow;

    @SuppressWarnings("unchecked")
    private static Ref<EntityStore>[] newRefs(int n) {
        return (Ref<EntityStore>[]) new Ref[n];
    }

    /** Vrai quand les trois élémentaires sont rassurés. */
    boolean step(World world, Store<EntityStore> store, SunquaPeak.State st, List<PlayerRef> players, float dt) {
        if (!begun) {
            if (SunquaPeak.near(store, players, Spawns.point(SunquaPeakLayout.WATER_START), 6).isEmpty()) {
                return false;
            }
            begin(world, store);
        }
        List<PlayerRef> here = Spawns.in(store, players, SunquaPeakLayout.WATER_ZONE);
        sprites.removeIf(ref -> !Spawns.alive(store, ref));
        surge += dt;
        if (surge >= SURGE_EVERY && !here.isEmpty()) {
            surge = 0f;
            surge(world, store);
        }
        glow += dt;
        boolean show = glow >= 1f;
        if (show) {
            glow = 0f;
        }
        int done = 0;
        for (int i = 0; i < calm.length; i++) {
            if (calmed[i]) {
                done++;
                continue;
            }
            Vector3d nook = Spawns.point(SunquaPeakLayout.NOOKS[i]);
            boolean anyone = false;
            for (PlayerRef p : SunquaPeak.near(store, here, nook, CALM_REACH)) {
                if (Moves.crouching(store, p.getReference())) {
                    anyone = true;
                    SunquaPeak.tell(st, p, "water.calming");
                }
            }
            if (!anyone) {
                continue;
            }
            if (!stirred[i]) {
                stirred[i] = true;
                stir(world, store, st, nook);
            }
            calm[i] += dt;
            if (show) {
                Telegraphs.particle(store, "Nakasar_Fractal_Calm_Glow", nook, 0.8f);
            }
            if (calm[i] >= CALM_SECONDS) {
                calmed[i] = true;
                done++;
                Telegraphs.particle(store, "Nakasar_Fractal_Calm_Glow", nook, 1.6f);
                Telegraphs.sound(store, "SFX_Water_MoveIn", nook);
                Spawns.remove(store, frightened[i]);
                frightened[i] = null;
                Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "water.calmed")
                        .param("count", count()).param("total", calm.length));
            }
        }
        return done == calm.length;
    }

    private int count() {
        int n = 0;
        for (boolean c : calmed) {
            n += c ? 1 : 0;
        }
        return n;
    }

    private void begin(World world, Store<EntityStore> store) {
        begun = true;
        surge = SURGE_EVERY - SURGE_FIRST;
        Gates.checkpoint(world, SunquaPeakLayout.WATER_START, SunquaPeak.MESSAGES + "checkpoint");
        Vector3d face = Spawns.point(SunquaPeakLayout.WATER_START);
        for (int i = 0; i < frightened.length; i++) {
            Vector3d at = Spawns.point(SunquaPeakLayout.NOOKS[i]);
            frightened[i] = Spawns.spawn(store, SunquaPeak.FRIGHTENED, at, Telegraphs.yawToward(at, face));
            if (frightened[i] != null && frightened[i].isValid()) {
                store.ensureAndGetComponent(frightened[i], Invulnerable.getComponentType());
            }
        }
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "water.intro"));
    }

    /** Le premier qui s'accroupit près d'un élémentaire fait surgir des esprits de l'eau. */
    private void stir(World world, Store<EntityStore> store, SunquaPeak.State st, Vector3d nook) {
        for (int k = 0; k < SPRITES; k++) {
            double a = Math.random() * Math.PI * 2;
            Vector3d at = SunquaPeak.ground(world, new Vector3d(nook.x() + Math.cos(a) * 4, nook.y(), nook.z() + Math.sin(a) * 4));
            Ref<EntityStore> ref = st.foe(world, store, SunquaPeak.WATER_SPRITE, at, nook, false);
            if (ref != null) {
                sprites.add(ref);
                Telegraphs.particle(store, "Water_Splash", at, 1f);
            }
        }
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "water.sprites"));
    }

    /** Les cascades déferlent : bande rouge, puis poussée vers le vide. */
    private void surge(World world, Store<EntityStore> store) {
        float windup = SURGE_WINDUP * FractalRuns.windupFactor(world);
        long now = System.nanoTime();
        List<Telegraphs.Strip> strips = new ArrayList<>();
        for (double[] s : SunquaPeakLayout.SURGES) {
            strips.add(new Telegraphs.Strip(new Vector3d(s[0], s[1], s[2]), s[3], SunquaPeakLayout.SURGE_LENGTH,
                    SunquaPeakLayout.SURGE_WIDTH, now, windup));
        }
        Spawns.tellAll(world, Message.translation(SunquaPeak.MESSAGES + "water.surge"));
        TelegraphSystem.start(world, (w, s, t) -> {
            boolean ready = true;
            for (Telegraphs.Strip strip : strips) {
                ready &= strip.step(s, t);
            }
            if (!ready) {
                return false;
            }
            List<UUID> thrown = new ArrayList<>();
            for (int i = 0; i < strips.size(); i++) {
                Telegraphs.Strip strip = strips.get(i);
                double facing = SunquaPeakLayout.SURGES[i][3];
                for (double along = 1; along < SunquaPeakLayout.SURGE_LENGTH; along += 3) {
                    Telegraphs.particle(s, "Nakasar_Fractal_Waterfall_Surge", strip.at(along, 0), 1f);
                }
                Telegraphs.sound(s, "SFX_Water_MoveIn", strip.origin());
                for (PlayerRef p : SunquaPeak.strike(w, s, strip, SURGE_PART, SunquaPeak.KNOCKED_DOWN, 1.2f)) {
                    if (!thrown.contains(p.getUuid())) {
                        thrown.add(p.getUuid());
                        Moves.velocity(s, p.getReference(), new Vector3d(Math.cos(facing) * SURGE_PUSH, 5,
                                Math.sin(facing) * SURGE_PUSH));
                    }
                }
            }
            return true;
        });
    }
}
