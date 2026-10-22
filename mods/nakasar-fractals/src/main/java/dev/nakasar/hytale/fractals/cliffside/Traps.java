package dev.nakasar.hytale.fractals.cliffside;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.TelegraphSystem;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Pièges de la Falaise, menés par {@link Cliffside#step} (thread du monde) :
 * <ul>
 *   <li>gargouilles du saut : cycle de {@value #GUST_CYCLE} s décalé par statue, poussière d'annonce pendant
 *   {@value #GUST_AT} s puis deux souffles qui projettent vers le vide (+z) sur {@link CliffsideLayout#GUST_REACH}
 *   blocs ; chaque levier du haut fait taire un groupe ;</li>
 *   <li>dalles piégées du tunnel : pointes, {@value #PLATE_PART} des PV, une fois toutes les {@value #PLATE_COOLDOWN} s
 *   par joueur ;</li>
 *   <li>foyers de la passerelle du torse : toutes les {@value #FIRE_INTERVAL} s, deux foyers sur trois s'embrasent
 *   (cercle rouge de {@value #FIRE_WARNING} s, puis {@value #FIRE_PART} des PV et brûlure) ; le foyer sûr tourne ;</li>
 *   <li>bombes des rampes : une toutes les {@value #BOMB_INTERVAL} s descend la rampe case par case sous un cercle rouge ;
 *   qui la croise est projeté de côté ({@value #BOMB_PART} des PV) ; le levier R1 ou R2 arrête sa rampe.</li>
 * </ul>
 * Les leviers figent qui les tire ({@value #LEVER_ROOT} s).
 */
final class Traps {

    static final float GUST_CYCLE = 5f;
    static final float GUST_AT = 1.2f;
    static final float GUST_AGAIN = 1.9f;
    static final double GUST_UP = 4;
    static final double GUST_PUSH = 9;
    static final float PLATE_PART = 0.18f;
    static final float PLATE_COOLDOWN = 2f;
    static final float FIRE_INTERVAL = 7f;
    static final float FIRE_WARNING = 2.2f;
    static final float FIRE_PART = 0.25f;
    static final float BOMB_INTERVAL = 5f;
    static final float BOMB_STEP = 0.25f;
    static final double BOMB_RADIUS = 1.6;
    static final float BOMB_PART = 0.12f;
    static final float LEVER_ROOT = 4f;
    static final String SPIKES = "Nakasar_Fractal_Spikes";
    static final String LEVER_ROOTED = "Nakasar_Fractal_Lever_Rooted";

    private static final Set<Long> TRAPPED = new HashSet<>();

    static {
        for (CliffsideLayout.Plate plate : CliffsideLayout.PLATES) {
            if (plate.trapped()) {
                TRAPPED.add(WorldBlocks.key(plate.x(), CliffsideLayout.PLATE_Y, plate.z()));
            }
        }
    }

    /** Une bombe sur sa rampe : la case où elle est, les joueurs déjà projetés. */
    private static final class Bomb {
        final int ramp;
        int cell;
        float wait;
        final Set<UUID> hit = new HashSet<>();

        Bomb(int ramp) {
            this.ramp = ramp;
        }
    }

    /** Leviers tirés (index de {@link CliffsideLayout#LEVERS}). */
    private final boolean[] pulled = new boolean[CliffsideLayout.LEVERS.length];
    private final Map<UUID, Float> plateCooldown = new HashMap<>();
    private final float[] bombClock = new float[CliffsideLayout.RAMPS.length];
    private final List<Bomb> bombs = new ArrayList<>();
    private float clock;
    private float fireClock;
    private int fireCycle;

    void step(World world, Store<EntityStore> store, Cliffside.State st, List<PlayerRef> players, float dt) {
        float before = clock;
        clock += dt;
        if (Cliffside.anyIn(store, players, CliffsideLayout.JUMP_ZONES.get(0))) {
            gargoyles(store, players, before, clock);
        }
        plates(store, players, dt);
        if (st.stage == Cliffside.Stage.CHEST && Cliffside.anyIn(store, players, CliffsideLayout.CHEST_DECK)) {
            fires(world, store, dt);
        } else {
            fireClock = 0f;
        }
        boolean ramps = (st.stage == Cliffside.Stage.RAMPS || st.stage == Cliffside.Stage.ARENA)
                && Cliffside.anyIn(store, players, CliffsideLayout.JUMP_ZONES.get(1));
        bombs(store, players, ramps, dt);
    }

    // --- gargouilles ------------------------------------------------------------------------------

    private void gargoyles(Store<EntityStore> store, List<PlayerRef> players, float before, float now) {
        for (CliffsideLayout.Gargoyle g : CliffsideLayout.GARGOYLES) {
            if (pulled[g.group()]) {
                continue;
            }
            float a = (before + g.offset()) % GUST_CYCLE;
            float b = (now + g.offset()) % GUST_CYCLE;
            Vector3d mouth = new Vector3d(g.x() + 0.5, g.y() + 0.3, g.z() + 1.2);
            if (crossed(a, b, 0f)) {
                Telegraphs.particle(store, "Nakasar_Fractal_Gust_Windup", mouth, 1f);
            }
            if (crossed(a, b, GUST_AT) || crossed(a, b, GUST_AGAIN)) {
                Telegraphs.particle(store, "Nakasar_Fractal_Gust", mouth, 1f);
                gust(store, players, g);
            }
        }
    }

    /** Vrai si la phase est passée par `t` entre `a` (exclu) et `b` (inclus), cycle compris. */
    private static boolean crossed(float a, float b, float t) {
        return a <= b ? a < t && t <= b : t > a || t <= b;
    }

    private static void gust(Store<EntityStore> store, List<PlayerRef> players, CliffsideLayout.Gargoyle g) {
        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null || at.x() < g.x() - 1 || at.x() >= g.x() + 2 || at.y() < g.y() - 3 || at.y() >= g.y() + 2
                    || at.z() < g.z() || at.z() > g.z() + CliffsideLayout.GUST_REACH) {
                continue;
            }
            Velocity velocity = store.getComponent(ref, Velocity.getComponentType());
            if (velocity != null) {
                velocity.addInstruction(new Vector3d(0, GUST_UP, GUST_PUSH), null, ChangeVelocityType.Set);
            }
        }
    }

    // --- dalles -------------------------------------------------------------------------------------

    private void plates(Store<EntityStore> store, List<PlayerRef> players, float dt) {
        plateCooldown.replaceAll((uuid, left) -> left - dt);
        plateCooldown.values().removeIf(left -> left <= 0f);
        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null || plateCooldown.containsKey(player.getUuid())) {
                continue;
            }
            int x = (int) Math.floor(at.x());
            int y = (int) Math.floor(at.y() - 0.1);
            int z = (int) Math.floor(at.z());
            if (y != CliffsideLayout.PLATE_Y || !TRAPPED.contains(WorldBlocks.key(x, y, z))) {
                continue;
            }
            plateCooldown.put(player.getUuid(), PLATE_COOLDOWN);
            Telegraphs.particle(store, "Nakasar_Fractal_Spikes", new Vector3d(x + 0.5, y + 1.05, z + 0.5), 1f);
            Telegraphs.sound(store, "SFX_Ability_Ground_Slam_Spike_Erupt", at);
            Hurt.percent(store, ref, PLATE_PART, SPIKES);
        }
    }

    // --- foyers ---------------------------------------------------------------------------------------

    private void fires(World world, Store<EntityStore> store, float dt) {
        fireClock += dt;
        if (fireClock < FIRE_INTERVAL) {
            return;
        }
        fireClock = 0f;
        int safe = fireCycle++ % CliffsideLayout.FIRES.length;
        float warning = FIRE_WARNING * FractalRuns.windupFactor(world);
        for (int i = 0; i < CliffsideLayout.FIRES.length; i++) {
            if (i == safe) {
                continue;
            }
            double[] f = CliffsideLayout.FIRES[i];
            Vector3d center = new Vector3d(f[0], f[1], f[2]);
            Telegraphs.circle(store, center, CliffsideLayout.FIRE_RADIUS, warning);
            Delayed.later(world, warning, s -> {
                Telegraphs.particle(s, "Fire_AoE", center, 1.4f);
                Telegraphs.sound(s, "SFX_Emit_Goblin_Flame_Quadrant_Blast", center);
                for (PlayerRef player : world.getPlayerRefs()) {
                    Ref<EntityStore> ref = player.getReference();
                    Vector3d at = Telegraphs.position(s, ref);
                    if (at != null && Telegraphs.horizontal(at, center) <= CliffsideLayout.FIRE_RADIUS
                            && Math.abs(at.y() - center.y()) <= 3) {
                        Hurt.percent(s, ref, FIRE_PART, "Fire");
                        Hurt.effect(s, ref, "Burn", 3f);
                    }
                }
            });
        }
    }

    // --- bombes -----------------------------------------------------------------------------------------

    private void bombs(Store<EntityStore> store, List<PlayerRef> players, boolean active, float dt) {
        if (active) {
            for (int r = 0; r < CliffsideLayout.RAMPS.length; r++) {
                if (pulled[CliffsideLayout.GARGOYLE_LEVERS + r]) {
                    continue;
                }
                bombClock[r] += dt;
                if (bombClock[r] >= BOMB_INTERVAL) {
                    bombClock[r] = 0f;
                    bombs.add(new Bomb(r));
                }
            }
        }
        for (Iterator<Bomb> it = bombs.iterator(); it.hasNext(); ) {
            Bomb bomb = it.next();
            bomb.wait -= dt;
            if (bomb.wait > 0f) {
                continue;
            }
            bomb.wait = BOMB_STEP;
            double[][] cells = CliffsideLayout.RAMPS[bomb.ramp];
            if (bomb.cell >= cells.length) {
                double[] last = cells[cells.length - 1];
                Telegraphs.particle(store, "Nakasar_Fractal_Bomb_Blast", new Vector3d(last[0], last[1] + 0.3, last[2]), 1f);
                Telegraphs.sound(store, "SFX_Goblin_Lobber_Bomb_Death", new Vector3d(last[0], last[1], last[2]));
                it.remove();
                continue;
            }
            double[] c = cells[bomb.cell++];
            Vector3d at = new Vector3d(c[0], c[1], c[2]);
            Telegraphs.circle(store, at, BOMB_RADIUS, BOMB_STEP * 2);
            for (PlayerRef player : players) {
                Ref<EntityStore> ref = player.getReference();
                Vector3d p = Telegraphs.position(store, ref);
                if (p == null || bomb.hit.contains(player.getUuid()) || Telegraphs.horizontal(p, at) > BOMB_RADIUS
                        || Math.abs(p.y() - at.y()) > 2) {
                    continue;
                }
                bomb.hit.add(player.getUuid());
                Velocity velocity = store.getComponent(ref, Velocity.getComponentType());
                if (velocity != null) {
                    double side = p.z() >= at.z() ? 8 : -8;
                    velocity.addInstruction(new Vector3d(0, 5, side), null, ChangeVelocityType.Set);
                }
                Telegraphs.particle(store, "Nakasar_Fractal_Bomb_Blast", new Vector3d(p).add(0, 0.5, 0), 0.6f);
                Hurt.percent(store, ref, BOMB_PART, "Physical");
            }
        }
    }

    // --- leviers ------------------------------------------------------------------------------------------

    /** Un joueur tire le levier du bloc (x, y, z). */
    void pull(World world, Store<EntityStore> store, Cliffside.State st, Ref<EntityStore> ref, PlayerRef player,
              int x, int y, int z) {
        int index = -1;
        for (int i = 0; i < CliffsideLayout.LEVERS.length; i++) {
            int[] l = CliffsideLayout.LEVERS[i];
            if (l[0] == x && l[1] == y && l[2] == z) {
                index = i;
            }
        }
        if (index < 0) {
            return;
        }
        if (pulled[index]) {
            Cliffside.tell(st, player, "lever.done");
            return;
        }
        pulled[index] = true;
        Hurt.effect(store, ref, LEVER_ROOTED, LEVER_ROOT);
        Telegraphs.sound(store, "SFX_Lever_Metal_On", new Vector3d(x + 0.5, y + 0.5, z + 0.5));
        String key = index < CliffsideLayout.GARGOYLE_LEVERS ? "lever.gargoyles" : "lever.bombs";
        for (PlayerRef p : world.getPlayerRefs()) {
            p.sendMessage(Message.translation(Cliffside.MESSAGES + key));
        }
        if (index >= CliffsideLayout.GARGOYLE_LEVERS) {
            int ramp = index - CliffsideLayout.GARGOYLE_LEVERS;
            bombs.removeIf(b -> b.ramp == ramp);
        }
    }
}
