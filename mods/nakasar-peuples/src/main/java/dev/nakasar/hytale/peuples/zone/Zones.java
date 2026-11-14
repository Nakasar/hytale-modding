package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.worldgen.chunk.ChunkGenerator;
import com.hypixel.hytale.server.worldgen.chunk.ZoneBiomeResult;

/**
 * Les zones du monde par défaut (World/Default/Zones.json : Zone1 à Zone4, chacune en paliers Zone<n>_Tier<t>, plus
 * Zone1_Spawn, les rivages et l'océan), lues dans le générateur vanilla comme la commande {@code /locate zone}. Un monde
 * sans ce générateur (instances des fractales, mondes plats) n'a pas de zone : 0.
 */
public final class Zones {

    private Zones() {
    }

    public static ChunkGenerator generator(World world) {
        try {
            return world.getChunkStore().getGenerator() instanceof ChunkGenerator g ? g : null;
        } catch (RuntimeException e) {
            return null;
        }
    }

    public static int seed(World world) {
        return (int) world.getWorldConfig().getSeed();
    }

    /** Nom de la zone en (x, z) (« Zone2_Tier1 »…), ou null. */
    public static String name(World world, int x, int z) {
        ChunkGenerator g = generator(world);
        if (g == null) {
            return null;
        }
        try {
            ZoneBiomeResult r = g.getZoneBiomeResultAt(seed(world), x, z);
            return r == null || r.getZoneResult() == null || r.getZoneResult().getZone() == null ? null
                    : r.getZoneResult().getZone().name();
        } catch (RuntimeException e) {
            return null;
        }
    }

    /** Numéro de zone (1 à 4) d'un nom de zone vanilla, 0 si aucun. */
    public static int number(String zoneName) {
        if (zoneName == null || !zoneName.startsWith("Zone") || zoneName.length() < 5) {
            return 0;
        }
        char c = zoneName.charAt(4);
        return c >= '1' && c <= '9' ? c - '0' : 0;
    }

    /** Numéro de zone en (x, z), 0 si aucun (océan compris : Zone<n>_Ocean garde son numéro). */
    public static int at(World world, double x, double z) {
        return number(name(world, (int) Math.floor(x), (int) Math.floor(z)));
    }

    /** Vrai si le nom de zone est la terre ferme de la zone `zone` (paliers ou départ, pas le rivage ni l'océan). */
    public static boolean inland(String zoneName, int zone) {
        return number(zoneName) == zone && (zoneName.contains("_Tier") || zoneName.contains("_Spawn"));
    }
}
