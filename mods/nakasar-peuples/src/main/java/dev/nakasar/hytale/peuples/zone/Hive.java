package dev.nakasar.hytale.peuples.zone;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import dev.nakasar.hytale.peuples.PeuplesPlugin;
import dev.nakasar.hytale.peuples.raid.Raids;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

/**
 * La ruche scarak de la zone 2 (GDD : « la ruche grossit si on ne la taille pas ; raids sur les Feran »). Une jauge par
 * monde, de 0 à {@value #MAX} points, un niveau tous les {@value #PER_LEVEL} : elle gagne {@value #GROWTH} points
 * chaque matin, et perd des points à chaque Scarak abattu par un joueur ({@link HiveDeathSystem}).
 *
 * <p>Ce que fait le niveau : il ajoute {@code niveau} Scaraks combattants à chaque vague d'un raid sur un village feran,
 * et {@code 5 % x niveau} à la chance d'un raid tiré au matin. Tailler la ruche d'un niveau la fâche (GDD, réputation
 * croisée « −− ») : un raid est prévu dès la nuit suivante sur le village feran le plus proche.
 */
public final class Hive {

    public static final String KEYS = "nakasar_peuples.hive.";
    public static final int MAX = 100;
    public static final int PER_LEVEL = 20;
    public static final int START = 20;
    public static final int GROWTH = 8;
    /** Points retirés par Scarak abattu, par la Broodmother, par un pillard scarak de raid. */
    public static final int KILL = 2;
    public static final int BROODMOTHER = 12;
    public static final int RAIDER = 1;
    public static final double CHANCE_PER_LEVEL = 0.05;

    private Hive() {
    }

    public static int level(int points) {
        return Math.max(0, Math.min(MAX, points)) / PER_LEVEL;
    }

    public static int level(World world) {
        ZoneRegistry r = ZoneRegistry.get(world);
        return r == null ? 0 : level(r.hive);
    }

    /** Scaraks combattants de plus dans chaque vague d'un raid sur ce village (0 hors Feran). */
    public static int extraRaiders(World world, Village village) {
        return village.people() == People.FERAN ? level(world) : 0;
    }

    /** Chance de raid au matin ajoutée par la ruche pour ce village (0 hors Feran). */
    public static double extraChance(World world, Village village) {
        return village.people() == People.FERAN ? level(world) * CHANCE_PER_LEVEL : 0.0;
    }

    /** Croissance du matin (une fois par jour de jeu). */
    static void morning(World world, Store<EntityStore> store) {
        ZoneRegistry r = ZoneRegistry.get(world);
        if (r == null) {
            return;
        }
        long day = GameClock.day(store);
        if (r.hiveDay == day) {
            return;
        }
        boolean first = r.hiveDay < 0;
        r.hiveDay = day;
        if (first) {
            return;
        }
        int before = level(r.hive);
        r.hive = Math.min(MAX, r.hive + GROWTH);
        int after = level(r.hive);
        if (after > before) {
            tell(world, Message.translation(KEYS + "grew").param("level", after), NotificationStyle.Warning);
        }
    }

    /** Fixe les points (commande d'essai). */
    public static void set(World world, int points) {
        ZoneRegistry r = ZoneRegistry.get(world);
        if (r != null) {
            r.hive = Math.max(0, Math.min(MAX, points));
        }
    }

    /** Un joueur a taillé la ruche de `points` ; un niveau perdu lance la riposte sur le village feran le plus proche. */
    static void cut(World world, Store<EntityStore> store, int points, double x, double z) {
        ZoneRegistry r = ZoneRegistry.get(world);
        if (r == null || points <= 0) {
            return;
        }
        int before = level(r.hive);
        r.hive = Math.max(0, r.hive - points);
        int after = level(r.hive);
        if (after >= before) {
            return;
        }
        Village village = Villages.registry(world).nearestOf(People.FERAN, x, z, Double.MAX_VALUE / 4);
        boolean revenge = village != null && Raids.schedule(village, Raids.nextNight(store, village), "Hive");
        PeuplesPlugin.get().getLogger().atInfo().log("Peuples : ruche taillée au niveau %d%s", after,
                revenge ? ", riposte prévue sur " + village.name() : "");
        tell(world, revenge
                ? Message.translation(KEYS + "cutRevenge").param("level", after).param("village", village.name())
                : Message.translation(KEYS + "cut").param("level", after), NotificationStyle.Warning);
    }

    /** Prévient les joueurs de la zone 2. */
    private static void tell(World world, Message message, NotificationStyle style) {
        for (PlayerRef p : world.getPlayerRefs()) {
            var at = p.getTransform().getPosition();
            if (Zones.at(world, at.x(), at.z()) == 2) {
                NotificationUtil.sendNotification(p.getPacketHandler(), message, style);
            }
        }
    }

    /** L'état de la ruche, en une ligne. */
    public static Message describe(World world) {
        ZoneRegistry r = ZoneRegistry.get(world);
        int points = r == null ? 0 : r.hive;
        return Message.translation(KEYS + "status").param("level", level(points)).param("points", points).param("max", MAX)
                .param("extra", level(points)).param("chance", (int) Math.round(level(points) * CHANCE_PER_LEVEL * 100));
    }
}
