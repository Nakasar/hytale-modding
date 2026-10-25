package dev.nakasar.hytale.fractals.sirensreef;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.combat.BossStun;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.silentsurf.Moves;
import org.joml.Vector3d;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Canons des ombres (corniche du ravin, rempart du fort, pont du Fierté du Kraken). On s'y poste en utilisant le bloc :
 * les trois boulets arrivent en main ; clic droit avec l'un d'eux tire là où l'on regarde (jusqu'à {@value #RANGE}
 * blocs). Chaque boulet a son temps de recharge ; s'éloigner de plus de {@value #LEAVE} blocs, ou réutiliser le canon,
 * le fait quitter (les boulets disparaissent).
 * <ul>
 *   <li>Ricochet : {@value #RIPPLE_COUNT} impacts de {@value #RIPPLE_RADIUS} blocs, {@value #RIPPLE_STEP} blocs plus
 *   loin à chaque rebond ;</li>
 *   <li>Mitraille : un impact de {@value #SCATTER_RADIUS} blocs, gros dégâts, étourdit les ennemis ;</li>
 *   <li>Glace : un impact de {@value #ICE_RADIUS} blocs qui gèle les ennemis {@value #ICE_SECONDS} s.</li>
 * </ul>
 * Tout impact fait sauter les mines, abat la palissade du ravin et entame la défiance des boss
 * ({@link SirensReef#impact}). Les boulets ne blessent pas les joueurs.
 */
final class ShadowCannon {

    static final String[] KINDS = {"Ripple", "Scatter", "Ice"};
    static final String[] ITEMS = {"Nakasar_Fractal_Cannon_Ripple", "Nakasar_Fractal_Cannon_Scatter",
            "Nakasar_Fractal_Cannon_Ice"};
    static final float[] RELOAD = {4f, 8f, 15f};
    static final double RANGE = 70;
    static final double LEAVE = 3.5;
    /** Vitesse du boulet (blocs/s) : l'impact tombe au bout de distance / vitesse. */
    static final double SPEED = 45;
    static final double RIPPLE_RADIUS = 2.5;
    static final double RIPPLE_STEP = 3;
    static final int RIPPLE_COUNT = 3;
    static final float RIPPLE_DAMAGE = 60f;
    static final double SCATTER_RADIUS = 4;
    static final float SCATTER_DAMAGE = 150f;
    static final float SCATTER_STUN = 2f;
    static final double ICE_RADIUS = 5;
    static final float ICE_DAMAGE = 40f;
    static final float ICE_SECONDS = 4f;
    static final String ICE_EFFECT = "Nakasar_Fractal_Frozen_Shot";
    /** La palissade du ravin s'abat sous un impact à moins de rayon + {@value #WALL_REACH} blocs. */
    static final double WALL_REACH = 3;

    private final UUID[] gunners = new UUID[SirensReefLayout.CANNONS.length];
    private final Map<UUID, long[]> ready = new HashMap<>();

    static Vector3d center(int i) {
        int[] c = SirensReefLayout.CANNONS[i];
        return new Vector3d(c[0] + 0.5, c[1], c[2] + 0.5);
    }

    /** Le canon le plus proche du bloc utilisé (le modèle déborde de sa case). */
    private static int at(int x, int y, int z) {
        int best = -1;
        double d = 2.5;
        for (int i = 0; i < SirensReefLayout.CANNONS.length; i++) {
            int[] c = SirensReefLayout.CANNONS[i];
            double e = Math.sqrt(Math.pow(c[0] - x, 2) + Math.pow(c[1] - y, 2) + Math.pow(c[2] - z, 2));
            if (e <= d) {
                d = e;
                best = i;
            }
        }
        return best;
    }

    void use(World world, Store<EntityStore> store, SirensReef.State st, PlayerRef player, int x, int y, int z) {
        int i = at(x, y, z);
        Ref<EntityStore> ref = player.getReference();
        if (i < 0 || ref == null || !ref.isValid()) {
            return;
        }
        UUID id = player.getUuid();
        if (id.equals(gunners[i])) {
            leave(store, ref, i);
            SirensReef.tell(st, player, "cannon.left");
            return;
        }
        if (gunners[i] != null && manned(world, store, i)) {
            SirensReef.tell(st, player, "cannon.busy");
            return;
        }
        for (int k = 0; k < gunners.length; k++) {
            if (id.equals(gunners[k])) {
                leave(store, ref, k);       // un seul canon à la fois
            }
        }
        gunners[i] = id;
        for (String item : ITEMS) {
            if (Carried.count(store, ref, item) == 0) {
                Carried.giveIfRoom(store, ref, item, 1);
            }
        }
        Telegraphs.particle(store, "Nakasar_Fractal_Cannon_Smoke", new Vector3d(center(i)).add(0, 1, 0), 0.6f);
        player.sendMessage(Message.translation(SirensReef.MESSAGES + "cannon.manned"));
    }

    private boolean manned(World world, Store<EntityStore> store, int i) {
        PlayerRef p = player(world, gunners[i]);
        Vector3d at = p == null ? null : Telegraphs.position(store, p.getReference());
        return at != null && Telegraphs.horizontal(at, center(i)) <= LEAVE && Math.abs(at.y() - center(i).y()) < 3;
    }

    private void leave(Store<EntityStore> store, Ref<EntityStore> ref, int i) {
        gunners[i] = null;
        if (ref != null && ref.isValid()) {
            for (String item : ITEMS) {
                Carried.removeAll(store, ref, item);
            }
        }
    }

    /** Qui s'est éloigné de son canon (ou est mort, ou parti) le quitte. */
    void step(World world, Store<EntityStore> store, SirensReef.State st) {
        for (int i = 0; i < gunners.length; i++) {
            if (gunners[i] == null || manned(world, store, i)) {
                continue;
            }
            PlayerRef p = player(world, gunners[i]);
            leave(store, p == null ? null : p.getReference(), i);
            if (p != null) {
                SirensReef.tell(st, p, "cannon.left");
            }
        }
    }

    void fire(World world, Store<EntityStore> store, SirensReef.State st, PlayerRef player, String kind) {
        int k = Arrays.asList(KINDS).indexOf(kind);
        int i = -1;
        for (int c = 0; c < gunners.length; c++) {
            if (player.getUuid().equals(gunners[c])) {
                i = c;
            }
        }
        Ref<EntityStore> ref = player.getReference();
        Vector3d feet = Telegraphs.position(store, ref);
        Vector3d look = Moves.look(store, ref);
        if (k < 0 || i < 0 || feet == null || look == null) {
            return;
        }
        long now = System.nanoTime();
        long[] times = ready.computeIfAbsent(player.getUuid(), u -> new long[KINDS.length]);
        if (now < times[k]) {
            SirensReef.tell(st, player, "cannon.reload");
            return;
        }
        Vector3d muzzle = new Vector3d(center(i)).add(0, 1.2, 0);
        Vector3d eye = new Vector3d(feet).add(0, 1.6, 0);
        Vector3d hit = Moves.cast(world.getChunkStore(), eye, look, RANGE);
        if (hit == null) {
            SirensReef.tell(st, player, "cannon.miss");
            return;
        }
        times[k] = now + Telegraphs.seconds(RELOAD[k]);
        Telegraphs.particle(store, "Nakasar_Fractal_Cannon_Smoke", muzzle, 1f);
        Telegraphs.sound(store, "SFX_Weapon_Goblin_Cannon_Fire", muzzle);
        double length = muzzle.distance(hit);
        for (double t = 2; t < length; t += 2) {
            Telegraphs.particle(store, "Nakasar_Fractal_Cannon_Trail", new Vector3d(muzzle).lerp(hit, t / length), 1f);
        }
        Vector3d ground = new Vector3d(hit);
        Vector3d flat = new Vector3d(look.x(), 0, look.z());
        flat = flat.lengthSquared() < 1e-4 ? new Vector3d(1, 0, 0) : flat.normalize();
        Vector3d along = flat;
        float flight = (float) (length / SPEED);
        Delayed.later(world, flight, s -> land(world, s, st, kind, ground, along));
    }

    private static void land(World world, Store<EntityStore> store, SirensReef.State st, String kind, Vector3d at,
                             Vector3d along) {
        switch (kind) {
            case "Ripple" -> {
                for (int n = 0; n < RIPPLE_COUNT; n++) {
                    Vector3d spot = new Vector3d(along).mul(n * RIPPLE_STEP).add(at);
                    Delayed.later(world, 0.25f * n, s -> {
                        boom(s, spot, RIPPLE_RADIUS, "Nakasar_Fractal_Cannon_Blast");
                        SirensReef.impact(world, s, st, spot, RIPPLE_RADIUS, RIPPLE_DAMAGE, null, 0f, 2);
                    });
                }
            }
            case "Scatter" -> {
                boom(store, at, SCATTER_RADIUS, "Nakasar_Fractal_Cannon_Blast");
                SirensReef.impact(world, store, st, at, SCATTER_RADIUS, SCATTER_DAMAGE, BossStun.EFFECT, SCATTER_STUN, 4);
            }
            default -> {
                boom(store, at, ICE_RADIUS, "Nakasar_Fractal_Ice_Burst");
                Telegraphs.sound(store, "SFX_Ice_Ball_Death", at);
                SirensReef.impact(world, store, st, at, ICE_RADIUS, ICE_DAMAGE, ICE_EFFECT, ICE_SECONDS, 3);
            }
        }
    }

    private static void boom(Store<EntityStore> store, Vector3d at, double radius, String particle) {
        Telegraphs.particle(store, particle, at, (float) (radius / 2.5));
        Telegraphs.sound(store, "SFX_Explosion_Boomshroom", at);
    }

    /** Tout le monde quitte les canons (fin du combat, remise à zéro). */
    void clear(World world, Store<EntityStore> store) {
        for (int i = 0; i < gunners.length; i++) {
            if (gunners[i] != null) {
                PlayerRef p = player(world, gunners[i]);
                leave(store, p == null ? null : p.getReference(), i);
            }
        }
    }

    private static PlayerRef player(World world, UUID id) {
        for (PlayerRef p : world.getPlayerRefs()) {
            if (p.getUuid().equals(id)) {
                return p;
            }
        }
        return null;
    }
}
