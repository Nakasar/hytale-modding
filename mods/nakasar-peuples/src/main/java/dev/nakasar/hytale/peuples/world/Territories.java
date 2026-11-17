package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.server.core.universe.world.World;
import dev.nakasar.hytale.peuples.annex.Routes;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

/**
 * Les territoires (GDD de la conquête, étape 6 ; Kevin : « le village et ses lieux-dits, avec des routes plus sûres
 * entre eux ») : un village et les lieux-dits qu'il tient et garde forment son territoire, à moins de
 * {@value #HAMLET_RANGE} blocs d'un de ses lieux-dits gardés ou de {@value #VILLAGE_RANGE} blocs du village. Sur ses
 * routes, les embuscades sont deux fois plus rares ; les voyageurs d'un village rival du maître des lieux font
 * demi-tour au départ quand le milieu de leur route passe par ce territoire.
 */
public final class Territories {

    public static final int HAMLET_RANGE = 250;
    public static final int VILLAGE_RANGE = 200;

    private Territories() {
    }

    /** Le village maître du territoire en (x, z) : celui d'un lieu-dit gardé proche, ou null. */
    public static Village master(World world, double x, double z) {
        // Un fortin actif étend le territoire de son village (Infrastructures).
        Village fort = dev.nakasar.hytale.peuples.annex.Infrastructures.territory(world, x, z);
        if (fort != null) {
            return fort;
        }
        Village best = null;
        double bestD = (double) HAMLET_RANGE * HAMLET_RANGE;
        for (Hamlets.Place h : Hamlets.all(world)) {
            if (h.stage() != Hamlets.BUILT) {
                continue;
            }
            double d = (h.x() - x) * (h.x() - x) + (h.z() - z) * (h.z() - z);
            if (d > bestD) {
                continue;
            }
            Village owner = Allegiance.owner(world, h);
            if (owner != null && Garrisons.count(world, h) > 0) {
                best = owner;
                bestD = d;
            }
        }
        if (best != null) {
            return best;
        }
        // Près d'un village qui tient au moins un lieu-dit gardé : son territoire aussi.
        for (Village v : Villages.registry(world).all()) {
            if (v.horizontalDistanceSquared(x, z) <= (double) VILLAGE_RANGE * VILLAGE_RANGE) {
                for (Hamlets.Place h : Allegiance.holdings(world, v)) {
                    if (Garrisons.count(world, h) > 0) {
                        return v;
                    }
                }
            }
        }
        return null;
    }

    /** Vrai si une embuscade à cet endroit est évitée (une sur deux en territoire gardé). */
    static boolean spared(World world, double[] here) {
        if (here != null && dev.nakasar.hytale.peuples.annex.Infrastructures.spares(world, here[0], here[1])) {
            return true; // poste routier proche, ou tour de garde une fois sur deux
        }
        return here != null && master(world, here[0], here[1]) != null && java.util.concurrent.ThreadLocalRandom.current().nextBoolean();
    }

    /** Vrai si un voyageur de `from` vers `to` doit renoncer : le milieu de sa route est le territoire d'un rival. */
    static boolean turnedBack(World world, Village from, Village to) {
        Routes.Path path = Links.path(world, from, to);
        if (path == null) {
            return false;
        }
        double[] mid = path.point(path.length() / 2);
        Village master = master(world, mid[0], mid[1]);
        return master != null && !master.id().equals(from.id()) && Relations.value(world, master, from) <= Relations.RIVAL;
    }
}
