package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.annex.Annexes;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.workshop.Workshops;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.List;

/**
 * Les bannières des lieux-dits tenus (GDD de la conquête, « Bannières ») : jusqu'à {@value #MAX_STANDARDS} bannières
 * aux couleurs du propriétaire accrochées aux murs du bâtiment (cherchées depuis la place, à {@value #HEIGHT} blocs du
 * sol, sous un mur plein et au-dessus de trois cases d'air), et un fanion planté près de la place. Changer de
 * propriétaire ou de blason, c'est changer l'id de ces blocs ; un lieu-dit libre les perd. Rien n'est posé tant que la
 * zone n'est pas chargée (un joueur à moins de {@value #RANGE} blocs), et on ne remplace jamais un bloc posé par un
 * joueur à la place d'une bannière.
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#BANNERS}) : {@code lieu-dit = x,y,z,rotation,S ou P;...}.
 */
public final class Banners {

    public static final int MAX_STANDARDS = 2;
    public static final int HEIGHT = 4;
    public static final int RANGE = 96;
    /** Pas au plus depuis la place vers le bâtiment pour trouver un mur. */
    private static final int REACH = 12;
    /** Colonnes (x local) d'où partir vers le bâtiment. */
    private static final int[] LANES = {-2, 2, -5, 5, 0};
    /** Places du fanion (coordonnées locales), la première libre. */
    private static final int[][] PENNANT = {{4, Hamlets.MARKET_Z}, {-4, Hamlets.MARKET_Z}, {4, Hamlets.MARKET_Z + 3}, {-4, Hamlets.MARKET_Z + 3}};

    private record Spot(int x, int y, int z, int rotation, boolean standard) {
        String format() {
            return x + "," + y + "," + z + "," + rotation + "," + (standard ? "S" : "P");
        }
    }

    private Banners() {
    }

    private static List<Spot> read(World world, Hamlets.Place h) {
        List<Spot> out = new ArrayList<>();
        String v = WorldLife.registry(world).get(WorldLifeRegistry.Part.BANNERS, h.id());
        if (v == null || v.isEmpty()) {
            return out;
        }
        for (String part : v.split(";")) {
            String[] p = part.split(",");
            try {
                out.add(new Spot(Integer.parseInt(p[0]), Integer.parseInt(p[1]), Integer.parseInt(p[2]), Integer.parseInt(p[3]), "S".equals(p[4])));
            } catch (RuntimeException ignored) {
                // place abîmée : oubliée
            }
        }
        return out;
    }

    private static void write(World world, Hamlets.Place h, List<Spot> spots) {
        StringBuilder sb = new StringBuilder();
        for (Spot s : spots) {
            if (!sb.isEmpty()) {
                sb.append(';');
            }
            sb.append(s.format());
        }
        WorldLife.registry(world).put(WorldLifeRegistry.Part.BANNERS, h.id(), sb.isEmpty() ? null : sb.toString());
    }

    /** Le blason d'un village a changé : ses lieux-dits seront repeints à la prochaine visite. */
    static void repaint(World world, Village v) {
        for (Hamlets.Place h : Allegiance.holdings(world, v)) {
            repaint(world, h);
        }
    }

    /** Le propriétaire a changé : repeint tout de suite si la zone est chargée (sinon au prochain pas près d'un joueur). */
    static void repaint(World world, Hamlets.Place h) {
        sync(world, h);
    }

    /** Le pas : chaque lieu-dit posé près d'un joueur porte les couleurs de son propriétaire. */
    static void step(World world, Store<EntityStore> store, List<Vector3d> players) {
        for (Hamlets.Place h : Hamlets.all(world)) {
            int[] m = h.market();
            if (h.stage() == Hamlets.BUILT && WorldLife.near(players, m[0], m[1], RANGE)) {
                sync(world, h);
            }
        }
    }

    private static void sync(World world, Hamlets.Place h) {
        if (h.stage() != Hamlets.BUILT) {
            return;
        }
        ChunkStore chunks = world.getChunkStore();
        Village owner = Allegiance.owner(world, h);
        List<Spot> spots = read(world, h);
        if (owner != null && spots.isEmpty()) {
            spots = find(world, h);
            if (spots.isEmpty()) {
                return;
            }
        }
        Heraldry.Arms arms = owner == null ? null : Heraldry.of(world, owner);
        List<Spot> keep = new ArrayList<>();
        boolean changed = false;
        for (Spot s : spots) {
            int id = Blocks.id(chunks, s.x(), s.y(), s.z());
            if (id == Blocks.UNLOADED) {
                keep.add(s);
                continue;
            }
            String here = Blocks.name(chunks, s.x(), s.y(), s.z());
            boolean ours = here == null || Heraldry.isStandard(here) || Heraldry.isPennant(here);
            if (!ours) {
                changed = true; // un joueur a pris la place : on l'oublie
                continue;
            }
            if (arms == null) {
                if (here != null) {
                    Blocks.set(chunks, s.x(), s.y(), s.z(), null, 0);
                }
                changed = true;
                continue;
            }
            String want = s.standard() ? arms.standard() : arms.pennant();
            if (!want.equals(here)) {
                Blocks.set(chunks, s.x(), s.y(), s.z(), want, s.rotation());
            }
            keep.add(s);
        }
        if (changed || !keep.equals(read(world, h))) {
            write(world, h, keep);
        }
    }

    /** Cherche les places des bannières (murs du bâtiment) et du fanion ; vide si la zone n'est pas chargée. */
    private static List<Spot> find(World world, Hamlets.Place h) {
        ChunkStore chunks = world.getChunkStore();
        Terrain terrain = new Terrain(world);
        List<Spot> out = new ArrayList<>();
        int[] back = Annexes.rotate(0, -1, h.rotation & 3);
        int rotation = back[0] != 0 ? 0 : 1;
        for (int lane : LANES) {
            if (out.size() >= MAX_STANDARDS) {
                break;
            }
            int[] start = h.world(lane, 1);
            int ground = terrain.surface(start[0], start[1]);
            if (ground == Terrain.NONE) {
                return List.of();
            }
            int y = Math.max(ground, h.y) + HEIGHT;
            int x = start[0], z = start[1];
            for (int step = 0; step < REACH; step++) {
                int nx = x + back[0], nz = z + back[1];
                int id = Blocks.id(chunks, nx, y, nz);
                if (id == Blocks.UNLOADED) {
                    return List.of();
                }
                if (Blocks.solid(chunks, nx, y, nz)) {
                    if (Blocks.isEmpty(chunks, x, y, z) && Blocks.isEmpty(chunks, x, y - 1, z) && Blocks.isEmpty(chunks, x, y - 2, z)
                            && !near(out, x, z)) {
                        out.add(new Spot(x, y, z, rotation, true));
                    }
                    break;
                }
                x = nx;
                z = nz;
            }
        }
        for (int[] p : PENNANT) {
            int[] at = h.world(p[0], p[1]);
            int y = Workshops.standY(chunks, terrain, at[0], at[1]);
            if (y == Workshops.UNLOADED_SPOT) {
                return List.of();
            }
            if (y != Terrain.NONE && Blocks.isEmpty(chunks, at[0], y, at[1])) {
                out.add(new Spot(at[0], y, at[1], h.rotation & 3, false));
                break;
            }
        }
        if (!out.isEmpty()) {
            PeuplesPlugin.get().getLogger().atInfo().log("Peuples (conquête) : %d bannières et fanion prévus au lieu-dit %s", out.size(), h.id());
        }
        return out;
    }

    private static boolean near(List<Spot> spots, int x, int z) {
        for (Spot s : spots) {
            if (Math.abs(s.x() - x) + Math.abs(s.z() - z) < 3) {
                return true;
            }
        }
        return false;
    }
}
