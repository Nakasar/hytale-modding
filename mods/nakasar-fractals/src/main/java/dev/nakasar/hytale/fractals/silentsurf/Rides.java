package dev.nakasar.hytale.fractals.silentsurf;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.WorldBlocks;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;
import java.util.UUID;

/**
 * Trajets guidés du Ressac silencieux (GW2 : tyroliennes, canons à vent, champignons rebondissants), d'après les
 * courbes de {@link SilentSurfLayout#RIDE_PATHS}. Hytale n'a ni câble ni rail pour les joueurs : à chaque tick, le
 * serveur pose la vitesse du joueur pour qu'il suive un point qui avance sur la courbe (le client reçoit un
 * {@code ChangeVelocity}, comme pour un recul). Trop loin du point (plus de {@value #SNAP} blocs : décalage du client),
 * il y est replacé.
 * <ul>
 *   <li>tyrolienne : Utiliser l'ancre ; s'accroupir lâche le câble ;</li>
 *   <li>canon à vent : Utiliser le canon ; le canon en l'air est la suite d'un rebond ;</li>
 *   <li>champignon : se poser sur son chapeau (bloc {@value SilentSurf#BOUNCE_CAP}).</li>
 * </ul>
 * Un trajet peut enchaîner sur un autre ({@link SilentSurfLayout#RIDE_NEXT}) ou lâcher le joueur avec une vitesse
 * ({@link SilentSurfLayout#RIDE_RELEASE}). Tant qu'il roule, et {@value #LANDING} s après, la chute ne blesse pas.
 */
final class Rides {

    static final int ZIP = 0;
    static final int CANNON = 1;
    static final int BOUNCE = 2;
    static final double SNAP = 6;
    static final double GAIN = 5;
    static final double MAX_SPEED = 40;
    static final float LANDING = 3f;
    static final float BOUNCE_COOLDOWN = 0.8f;
    static final double CAP_REACH = 4;

    private static final double[][] LENGTHS = new double[SilentSurfLayout.RIDE_PATHS.length][];

    static {
        for (int r = 0; r < LENGTHS.length; r++) {
            double[][] path = SilentSurfLayout.RIDE_PATHS[r];
            double[] acc = new double[path.length];
            for (int i = 1; i < path.length; i++) {
                acc[i] = acc[i - 1] + dist(path[i - 1], path[i]);
            }
            LENGTHS[r] = acc;
        }
    }

    private static final class Active {
        final Ref<EntityStore> ref;
        int ride;
        double s;
        int tick;

        Active(Ref<EntityStore> ref, int ride) {
            this.ref = ref;
            this.ride = ride;
        }
    }

    private final Map<UUID, Active> active = new HashMap<>();
    private final Map<UUID, Long> bounced = new HashMap<>();
    private long last;

    boolean riding(UUID player) {
        return active.containsKey(player);
    }

    void cancel(UUID player) {
        active.remove(player);
    }

    /** Départ du trajet `ride` (bloc utilisé ou chapeau de champignon) ; refusé tant que sa rencontre n'est pas finie. */
    boolean start(SilentSurf.State st, PlayerRef player, int ride) {
        int lock = SilentSurfLayout.RIDE_LOCK[ride];
        if (lock > 0 && !st.cleared[lock]) {
            SilentSurf.tell(st, player, "ride.locked");
            return false;
        }
        Ref<EntityStore> ref = player.getReference();
        if (ref == null || !ref.isValid()) {
            return false;
        }
        st.gear.cancel(player.getUuid());
        active.put(player.getUuid(), new Active(ref, ride));
        return true;
    }

    /** Ancre de tyrolienne ou canon à vent utilisé en (x, y, z). */
    void use(World world, Store<EntityStore> store, SilentSurf.State st, PlayerRef player, int x, int y, int z) {
        int[][] blocks = SilentSurfLayout.RIDE_BLOCKS;
        for (int i = 0; i < blocks.length; i++) {
            if (blocks[i][0] == x && blocks[i][1] == y && blocks[i][2] == z) {
                int ride = SilentSurfLayout.RIDE_BLOCK_RIDE[i];
                if (start(st, player, ride) && SilentSurfLayout.RIDE_KIND[ride] == CANNON) {
                    Telegraphs.particle(store, "Nakasar_Fractal_Wind_Burst", new Vector3d(x + 0.5, y + 0.5, z + 0.5), 1.2f);
                    Telegraphs.sound(store, "SFX_Goblin_Feastmaster_Slam", new Vector3d(x + 0.5, y, z + 0.5));
                }
                return;
            }
        }
    }

    /** Un tick du monde : avance les trajets en cours, fait rebondir qui se pose sur un champignon. */
    void tick(World world, Store<EntityStore> store, SilentSurf.State st, long now) {
        float dt = last == 0 ? 0.033f : Math.min(0.1f, (now - last) / 1e9f);
        last = now;
        Iterator<Map.Entry<UUID, Active>> it = active.entrySet().iterator();
        while (it.hasNext()) {
            Map.Entry<UUID, Active> e = it.next();
            Active a = e.getValue();
            Vector3d at = Telegraphs.position(store, a.ref);
            if (at == null) {
                it.remove();
                continue;
            }
            int kind = SilentSurfLayout.RIDE_KIND[a.ride];
            if (kind == ZIP && a.s > 1.5 && Moves.crouching(store, a.ref)) {
                it.remove();   // on lâche le câble
                continue;
            }
            double[] lengths = LENGTHS[a.ride];
            a.s += SilentSurfLayout.RIDE_SPEED[a.ride] * dt;
            if (a.s >= lengths[lengths.length - 1]) {
                int next = SilentSurfLayout.RIDE_NEXT[a.ride];
                st.safe(e.getKey(), LANDING);
                if (next >= 0) {
                    a.ride = next;
                    a.s = 0;
                    if (SilentSurfLayout.RIDE_KIND[next] == CANNON) {
                        Telegraphs.particle(store, "Nakasar_Fractal_Wind_Burst", at, 1.2f);
                    }
                    continue;
                }
                double[] out = SilentSurfLayout.RIDE_RELEASE[a.ride];
                Vector3d release = new Vector3d(out[0], out[1], out[2]);
                if (release.lengthSquared() < 0.01) {
                    release = tangent(a.ride, a.s).mul(kind == ZIP ? 3 : 2);
                    release.y = Math.max(release.y, 0);
                }
                Moves.velocity(store, a.ref, release);
                it.remove();
                continue;
            }
            Vector3d target = point(a.ride, a.s);
            if (at.distance(target) > SNAP) {
                Moves.teleport(store, a.ref, target);
                continue;
            }
            Vector3d v = tangent(a.ride, a.s).mul(SilentSurfLayout.RIDE_SPEED[a.ride])
                    .add(new Vector3d(target).sub(at).mul(GAIN));
            if (v.length() > MAX_SPEED) {
                v.normalize().mul(MAX_SPEED);
            }
            Moves.velocity(store, a.ref, v);
            st.safe(e.getKey(), LANDING);
            if (++a.tick % 4 == 0) {
                String fx = kind == ZIP ? "Nakasar_Fractal_Zip_Spark" : kind == CANNON ? "Nakasar_Fractal_Wind_Trail" : null;
                if (fx != null) {
                    Telegraphs.particle(store, fx, new Vector3d(at).add(0, kind == ZIP ? 2.6 : 0.8, 0), 1f);
                }
            }
        }
        bounces(world, store, st, now);
    }

    /** Joueurs posés sur un chapeau de champignon : rebond vers le trajet du champignon le plus proche. */
    private void bounces(World world, Store<EntityStore> store, SilentSurf.State st, long now) {
        ChunkStore chunks = world.getChunkStore();
        for (PlayerRef p : Spawns.alivePlayers(world, store)) {
            UUID id = p.getUuid();
            if (active.containsKey(id)) {
                continue;
            }
            Long until = bounced.get(id);
            if (until != null && now < until) {
                continue;
            }
            Vector3d at = Telegraphs.position(store, p.getReference());
            if (at == null) {
                continue;
            }
            int bx = (int) Math.floor(at.x());
            int by = (int) Math.floor(at.y() - 0.2);
            int bz = (int) Math.floor(at.z());
            if (!SilentSurf.BOUNCE_CAP.equals(WorldBlocks.name(chunks, bx, by, bz))) {
                continue;
            }
            int best = -1;
            double bestD = CAP_REACH;
            double[][] caps = SilentSurfLayout.CAPS;
            for (int i = 0; i < caps.length; i++) {
                double d = Telegraphs.horizontal(at, Spawns.point(caps[i]));
                if (d < bestD && Math.abs(caps[i][1] - at.y()) < 2.5) {
                    bestD = d;
                    best = i;
                }
            }
            bounced.put(id, now + Telegraphs.seconds(BOUNCE_COOLDOWN));
            if (best < 0) {
                continue;
            }
            st.safe(id, LANDING);
            if (start(st, p, SilentSurfLayout.CAP_RIDE[best])) {
                Telegraphs.particle(store, "Nakasar_Fractal_Bounce", at, 1f);
                Telegraphs.sound(store, "SFX_Goblin_Feastmaster_Slam", at);
            } else {
                Moves.velocity(store, p.getReference(), new Vector3d(0, 9, 0));   // simple rebond sur place
            }
        }
    }

    // --- courbes --------------------------------------------------------------------------------------------

    static Vector3d point(int ride, double s) {
        double[][] path = SilentSurfLayout.RIDE_PATHS[ride];
        double[] acc = LENGTHS[ride];
        int i = 1;
        while (i < path.length - 1 && acc[i] < s) {
            i++;
        }
        double seg = acc[i] - acc[i - 1];
        double t = seg <= 0 ? 1 : Math.max(0, Math.min(1, (s - acc[i - 1]) / seg));
        double[] a = path[i - 1];
        double[] b = path[i];
        return new Vector3d(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t);
    }

    static Vector3d tangent(int ride, double s) {
        Vector3d a = point(ride, Math.max(0, s - 0.5));
        Vector3d b = point(ride, s + 0.5);
        Vector3d d = b.sub(a);
        return d.lengthSquared() < 1e-6 ? new Vector3d() : d.normalize();
    }

    private static double dist(double[] a, double[] b) {
        double dx = a[0] - b[0];
        double dy = a[1] - b[1];
        double dz = a[2] - b[2];
        return Math.sqrt(dx * dx + dy * dy + dz * dz);
    }
}
