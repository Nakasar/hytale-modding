package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.reputation.Rank;
import dev.nakasar.hytale.peuples.reputation.Reputations;
import dev.nakasar.hytale.peuples.request.GameClock;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Village;

/**
 * Les blasons des villages (GDD de la conquête, « Bannières ») : une couleur parmi {@value #COLOUR_COUNT} et un
 * emblème parmi {@value #EMBLEM_COUNT} (trois par peuple, l'étoile pour tous), soit 128 bannières générées par
 * {@code tools/generate_conquest.py} sur le modèle vanilla de la bannière des ruines humaines, et un fanion par couleur.
 * Tiré au hasard (graine : l'id du village) la première fois qu'on le demande ; un joueur Hôte peut le changer au
 * tableau du village (onglet Domaine) pour {@value #CHANGE_BOLTS} rouleaux de tissu, une fois tous les
 * {@value #CHANGE_DAYS} jours.
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#HERALDRY}) : {@code village = couleur|emblème|jour du dernier changement}.
 */
public final class Heraldry {

    public static final String KEYS = "nakasar_peuples.conquest.";
    /** Ordre de tools/generate_conquest.py (COLOURS, EMBLEMS). */
    public static final String[] COLOURS = {"Red", "Blue", "Green", "Yellow", "White", "Black", "Purple", "Orange"};
    public static final String[] EMBLEMS = {"Leaf", "Acorn", "Mushroom", "Tusk", "Axe", "Skull", "Sun", "Feather", "Dune",
            "Snowflake", "Hammer", "Tower", "Flame", "Eye", "Lotus", "Star"};
    public static final int COLOUR_COUNT = 8;
    public static final int EMBLEM_COUNT = 16;
    /** Couleur de chaque tissu (liserés et rubans de l'interface). */
    public static final String[] COLOUR_HEX = {"#a8242a", "#284c9c", "#2e783e", "#deb034", "#e2ded0", "#4a4650", "#6a3084", "#d66e24"};
    public static final String STANDARD = "Nakasar_Peuples_Standard_";
    public static final String PENNANT = "Nakasar_Peuples_Pennant_";
    public static final String BLANK = STANDARD + "Blank";
    public static final int CHANGE_DAYS = 7;
    public static final int CHANGE_BOLTS = 4;
    private static final int STAR = 15;

    /** Un blason. `changed` : jour du dernier changement (Long.MIN_VALUE : jamais). */
    public record Arms(int colour, int emblem, long changed) {
        public String standard() {
            return STANDARD + COLOURS[colour] + "_" + EMBLEMS[emblem];
        }

        public String pennant() {
            return PENNANT + COLOURS[colour];
        }

        public String hex() {
            return COLOUR_HEX[colour];
        }

        public Message name() {
            return Message.translation(KEYS + "arms").param("colour", Message.translation(KEYS + "colour." + COLOURS[colour]))
                    .param("emblem", Message.translation(KEYS + "emblem." + EMBLEMS[emblem]));
        }
    }

    private Heraldry() {
    }

    /** Les emblèmes d'un peuple (indices d'{@link #EMBLEMS}) ; l'étoile en plus pour tous. */
    public static int[] emblemsOf(String peopleId) {
        return switch (peopleId == null ? "" : peopleId) {
            case "Kweebec" -> new int[] {0, 1, 2, STAR};
            case "Trork" -> new int[] {3, 4, 5, STAR};
            case "Feran" -> new int[] {6, 7, 8, STAR};
            case "Renonce" -> new int[] {9, 10, 11, STAR};
            case "Slothian" -> new int[] {12, 13, 14, STAR};
            default -> new int[] {STAR};
        };
    }

    /** Le blason du village (tiré la première fois). */
    public static Arms of(World world, Village v) {
        WorldLifeRegistry r = WorldLife.registry(world);
        String s = r.get(WorldLifeRegistry.Part.HERALDRY, v.id());
        Arms a = parse(s);
        if (a != null) {
            return a;
        }
        int h = v.id().hashCode() * 31 + 7;
        int[] own = emblemsOf(v.people().id());
        a = new Arms(Math.floorMod(h, COLOUR_COUNT), own[Math.floorMod(h >>> 4, Math.max(1, own.length - 1))], Long.MIN_VALUE);
        save(world, v, a);
        return a;
    }

    private static Arms parse(String s) {
        if (s == null) {
            return null;
        }
        String[] p = s.split("\\|", -1);
        try {
            int c = Integer.parseInt(p[0]);
            int e = Integer.parseInt(p[1]);
            long d = p.length > 2 && !p[2].isEmpty() ? Long.parseLong(p[2]) : Long.MIN_VALUE;
            if (c < 0 || c >= COLOUR_COUNT || e < 0 || e >= EMBLEM_COUNT) {
                return null;
            }
            return new Arms(c, e, d);
        } catch (RuntimeException ex) {
            return null;
        }
    }

    private static void save(World world, Village v, Arms a) {
        WorldLife.registry(world).put(WorldLifeRegistry.Part.HERALDRY, v.id(),
                a.colour() + "|" + a.emblem() + "|" + (a.changed() == Long.MIN_VALUE ? "" : Long.toString(a.changed())));
    }

    /** Vrai si `blockOrItem` est une bannière de village (pas la vierge). */
    public static boolean isStandard(String id) {
        return id != null && id.startsWith(STANDARD) && !id.equals(BLANK);
    }

    public static boolean isPennant(String id) {
        return id != null && id.startsWith(PENNANT);
    }

    /** Vrai pour un rouleau de tissu vanilla (Ingredient_Bolt_*). */
    public static boolean isBolt(String itemId) {
        return itemId != null && itemId.startsWith("Ingredient_Bolt_");
    }

    /** Jours avant le prochain changement possible (0 : possible). */
    public static long wait(World world, Village v, long day) {
        Arms a = of(world, v);
        return a.changed() == Long.MIN_VALUE ? 0 : Math.max(0, a.changed() + CHANGE_DAYS - day);
    }

    /**
     * Change le blason du village (joueur Hôte, {@value #CHANGE_BOLTS} rouleaux, une fois tous les {@value #CHANGE_DAYS}
     * jours) : bannières et fanions de ses lieux-dits repeints. Rend la raison du refus, ou null.
     */
    public static Message change(World world, Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef player, Village v, int colour,
                                 int emblem) {
        if (!Reputations.rank(store, ref, v).atLeast(Rank.HOTE)) {
            return Message.translation(KEYS + "arms.rank").param("village", v.name());
        }
        long day = GameClock.day(store);
        long wait = wait(world, v, day);
        if (wait > 0) {
            return Message.translation(KEYS + "arms.wait").param("days", wait);
        }
        Arms was = of(world, v);
        if (was.colour() == colour && was.emblem() == emblem) {
            return Message.translation(KEYS + "arms.same");
        }
        if (WorldLife.count(store, ref, Heraldry::isBolt) < CHANGE_BOLTS) {
            return Message.translation(KEYS + "arms.bolts").param("count", CHANGE_BOLTS);
        }
        WorldLife.take(store, ref, Heraldry::isBolt, CHANGE_BOLTS);
        Arms now = new Arms(Math.floorMod(colour, COLOUR_COUNT), Math.floorMod(emblem, EMBLEM_COUNT), day);
        save(world, v, now);
        Banners.repaint(world, v);
        dev.nakasar.hytale.peuples.village.Chantiers.announce(world, v, Message.translation(KEYS + "arms.changed")
                .param("village", v.name()).param("arms", now.name()), null,
                com.hypixel.hytale.protocol.packets.interface_.NotificationStyle.Success);
        return null;
    }

    /** Pose le blason de force (commande). */
    static void set(World world, Village v, int colour, int emblem) {
        save(world, v, new Arms(Math.floorMod(colour, COLOUR_COUNT), Math.floorMod(emblem, EMBLEM_COUNT), Long.MIN_VALUE));
        Banners.repaint(world, v);
    }

    /**
     * Brode le blason du village dont le joueur porte les couleurs sur toutes ses bannières vierges. Rend le nombre de
     * bannières brodées (0 : aucune vierge).
     */
    public static int embroider(World world, Store<EntityStore> store, Ref<EntityStore> ref, Village v) {
        int n = WorldLife.take(store, ref, BLANK::equals, 64);
        if (n > 0) {
            Requests.give(store, ref, new ItemStack(of(world, v).standard(), n));
        }
        return n;
    }
}
