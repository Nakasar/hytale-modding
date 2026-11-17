package dev.nakasar.hytale.peuples.population;

import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.ChunkStore;
import dev.nakasar.hytale.peuples.village.Blocks;
import dev.nakasar.hytale.peuples.village.Chantiers;
import dev.nakasar.hytale.peuples.village.Terrain;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.Villages;

/**
 * Le cimetière du village : une tombe ({@value #TOMB}, modèle vanilla Furniture_Village_Tombstone) par habitant mort,
 * posée en rangées juste hors du plan, du côté fixé par l'id du village. Une tombe se lit (épitaphe,
 * {@link ReadTombInteraction}) et ne se casse pas.
 */
public final class Cemetery {

    public static final String TOMB = "Nakasar_Peuples_Tombstone";

    /** Distance au bord du plan, tombes par rangée, écarts entre tombes et entre rangées. */
    static final int MARGIN = 6;
    static final int PER_ROW = 6;
    static final int SPACING = 2;
    static final int ROW_GAP = 3;
    /** Emplacements essayés au plus pour une tombe (arbre, rocher, eau). */
    static final int TRIES = 12;
    /** Tombes au plus par village ; au-delà, les plus anciennes restent seules dans la chronique. */
    static final int MAX = 72;

    private Cemetery() {
    }

    /** Pose les tombes des morts qui n'en ont pas encore, si le terrain est chargé. */
    static void placePending(World world, Village village, PopulationState p) {
        for (Inhabitant h : p.inhabitants) {
            if (h.alive() || h.tomb != null || p.nextTomb >= MAX) {
                continue;
            }
            for (int i = 0; i < TRIES && h.tomb == null && p.nextTomb < MAX; i++) {
                int[] s = slot(village, p.nextTomb);
                int ground = new Terrain(world).surface(s[0], s[1]);
                if (ground == Terrain.NONE) {
                    return; // pas chargé : on réessaiera
                }
                ChunkStore chunks = world.getChunkStore();
                String under = Blocks.name(chunks, s[0], ground, s[1]);
                String current = Blocks.name(chunks, s[0], ground + 1, s[1]);
                boolean free = under != null && Terrain.isGround(under) && (current == null || Terrain.isVegetation(current));
                if (free && !Blocks.set(chunks, s[0], ground + 1, s[1], TOMB, s[2])) {
                    return;
                }
                p.nextTomb++;
                if (free) {
                    h.tomb = new int[] {s[0], ground + 1, s[1]};
                }
            }
        }
    }

    /** Position du n-ième emplacement : rangées tangentes au plan, côté tiré de l'id du village. */
    static int[] slot(Village village, int n) {
        VillageLayout layout = Chantiers.layout(village);
        int r = (layout == null ? Villages.RADIUS : layout.radius()) + MARGIN;
        double angle = Math.floorMod(village.id().hashCode(), 360) * Math.PI / 180.0;
        double cx = Math.cos(angle);
        double cz = Math.sin(angle);
        int row = n / PER_ROW;
        int col = n % PER_ROW - PER_ROW / 2;
        double dist = r + row * ROW_GAP;
        int x = village.x() + (int) Math.round(cx * dist - cz * col * SPACING);
        int z = village.z() + (int) Math.round(cz * dist + cx * col * SPACING);
        // Les tombes regardent le village.
        int rotation = Math.floorMod((int) Math.round((angle + Math.PI) / (Math.PI / 2)), 4);
        return new int[] {x, z, rotation};
    }

    /** Le mort dont la tombe est en (x, y, z), ou null. */
    public static Inhabitant at(Village village, int x, int y, int z) {
        for (Inhabitant h : village.population().all()) {
            if (h.tomb != null && h.tomb[0] == x && h.tomb[1] == y && h.tomb[2] == z) {
                return h;
            }
        }
        return null;
    }
}
