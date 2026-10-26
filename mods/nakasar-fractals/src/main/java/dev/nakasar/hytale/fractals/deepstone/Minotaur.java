package dev.nakasar.hytale.fractals.deepstone;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Leash;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * L'esprit du Minotaure des ombres, dans la salle du cristal (GW2). Griffes, coup de cornes et bond : rôle JSON. En Java :
 * <ul>
 *   <li>voilé d'ombre, il ne prend aucun dégât ; la Lumière de Deldrimor à moins de {@value #REVEAL_RANGE} blocs le
 *   dévoile {@value #REVEAL_SECONDS} s (Exposé à la Lumière : +25 % de dégâts subis, ralenti) ;</li>
 *   <li>voilé, son ombre (fumée noire de {@value #AURA_RADIUS} blocs) ralentit et ronge ({@value #AURA_PART} des PV par
 *   seconde) ;</li>
 *   <li>à 75, 50 et 25 %, des diablotins des ombres ; à 50 %, un écharpeur ;</li>
 *   <li>lui et ses ombres vaincus, la porte nord s'ouvre. Personne dans la salle pendant {@value #RESET_SECONDS} s : il
 *   se fond dans les ombres (pas de soin : il revient neuf).</li>
 * </ul>
 */
final class Minotaur {

    static final double REVEAL_RANGE = 10;
    static final float REVEAL_SECONDS = 8f;
    static final double AURA_RADIUS = 4;
    static final float AURA_PART = 0.02f;
    static final float[] IMPS_AT = {0.75f, 0.5f, 0.25f};
    static final int IMPS = 3;
    static final float RESET_SECONDS = 25f;
    static final String VEIL = "Nakasar_Fractal_Shadow_Veil";
    static final String EXPOSED = "Nakasar_Fractal_Light_Vulnerability";

    private Ref<EntityStore> boss;
    private boolean engaged;
    private boolean beaten;
    private final List<Ref<EntityStore>> adds = new ArrayList<>();
    private int waves;
    private long revealedUntil;
    private float idle;
    private float fx;

    boolean vulnerable() {
        return System.nanoTime() < revealedUntil;
    }

    /** Vrai une fois le Minotaure et ses ombres vaincus. */
    boolean step(World world, Store<EntityStore> store, Deepstone.State st, List<PlayerRef> players, float dt) {
        Vector3d hall = Spawns.point(DeepstoneLayout.HALL_CENTER);
        List<PlayerRef> here = inHall(store, players);
        if (!engaged) {
            if (here.isEmpty()) {
                return false;
            }
            boss = st.boss(world, store, Deepstone.MINOTAUR, Spawns.point(DeepstoneLayout.MINOTAUR), hall);
            if (boss == null) {
                return false;
            }
            engaged = true;
            waves = 0;
            idle = 0f;
            revealedUntil = 0;
            Telegraphs.particle(store, "Nakasar_Fractal_Shadow_Rise", Spawns.point(DeepstoneLayout.MINOTAUR), 2f);
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "minotaur.enter"));
            return false;
        }
        adds.removeIf(ref -> !Spawns.alive(store, ref));
        if (!beaten && !Spawns.alive(store, boss)) {
            beaten = true;
        }
        if (beaten) {
            if (adds.isEmpty()) {
                return true;
            }
            return false;
        }
        if (here.isEmpty()) {
            idle += dt;
            if (idle >= RESET_SECONDS) {
                Spawns.remove(store, boss);
                Spawns.removeAll(store, adds);
                boss = null;
                engaged = false;
                Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "minotaur.reset"));
            }
            return false;
        }
        idle = 0f;
        int[] h = DeepstoneLayout.HALL;
        double radius = Math.min(h[1] - h[0], h[3] - h[2]) / 2.0 - 1;
        Leash.keepOnDisc(store, boss, hall, radius, 2, Deepstone.FALL_LIMIT);
        float health = Hurt.healthFraction(store, boss);
        if (waves < IMPS_AT.length && health <= IMPS_AT[waves] + 0.001f) {
            waves++;
            double[][] spots = DeepstoneLayout.HALL_IMPS;
            for (int i = 0; i < IMPS; i++) {
                Ref<EntityStore> ref = st.foe(world, store, Deepstone.IMP, Spawns.point(spots[(waves + i * 2) % spots.length]), true);
                if (ref != null) {
                    adds.add(ref);
                }
            }
            if (waves == 2) {
                Ref<EntityStore> ref = st.foe(world, store, Deepstone.MAULER, Spawns.point(spots[0]), true);
                if (ref != null) {
                    adds.add(ref);
                }
            }
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "minotaur.imps"));
        }
        if (!vulnerable()) {
            Hurt.effect(store, boss, VEIL, 1.5f);
            aura(store, players, dt);
        }
        return false;
    }

    /** Voilé : sa fumée ralentit et ronge qui s'en approche. */
    private void aura(Store<EntityStore> store, List<PlayerRef> players, float dt) {
        Vector3d at = Telegraphs.position(store, boss);
        if (at == null) {
            return;
        }
        fx += dt;
        if (fx >= 0.75f) {
            fx = 0f;
            Telegraphs.particle(store, "Nakasar_Fractal_Shadow_Aura", at, (float) (AURA_RADIUS / 4));
        }
        for (PlayerRef p : players) {
            Vector3d pos = Telegraphs.position(store, p.getReference());
            if (pos != null && Telegraphs.inCircle(pos, at, AURA_RADIUS)) {
                Hurt.effect(store, p.getReference(), "Nakasar_Fractal_Shadow_Touch", 1.5f);
                Hurt.percent(store, p.getReference(), AURA_PART * dt, Deepstone.CAUSE);
            }
        }
    }

    /** La Lumière de Deldrimor libérée en `at`. */
    void light(World world, Store<EntityStore> store, Vector3d at) {
        if (!engaged || boss == null) {
            return;
        }
        Vector3d b = Telegraphs.position(store, boss);
        if (b == null || Telegraphs.horizontal(b, at) > REVEAL_RANGE || Math.abs(b.y() - at.y()) > 5) {
            return;
        }
        boolean was = vulnerable();
        revealedUntil = System.nanoTime() + Telegraphs.seconds(REVEAL_SECONDS);
        Hurt.clear(store, boss, VEIL);
        Hurt.effect(store, boss, EXPOSED, REVEAL_SECONDS);
        Telegraphs.particle(store, "Nakasar_Fractal_Deldrimor_Glow", b, 1.5f);
        if (!was) {
            Spawns.tellAll(world, Message.translation(Deepstone.MESSAGES + "minotaur.revealed"));
        }
    }

    private static List<PlayerRef> inHall(Store<EntityStore> store, List<PlayerRef> players) {
        int[] h = DeepstoneLayout.HALL;
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef p : players) {
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at != null && at.x() >= h[0] && at.x() <= h[1] + 1 && at.z() >= h[2] && at.z() <= h[3] + 1
                    && Math.abs(at.y() - DeepstoneLayout.VAULT_Y) < 5) {
                out.add(p);
            }
        }
        return out;
    }
}
