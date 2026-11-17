package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.server.core.inventory.container.ItemContainer;
import com.hypixel.hytale.server.core.universe.world.World;
import dev.nakasar.hytale.peuples.request.Requests;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * L'accès d'un village à une ressource (routes commerciales, Kevin, 16 novembre 2026) : chaque livraison d'une caravane
 * ouvre l'accès à ses marchandises pour {@value #DELIVERY_DAYS} jours. Un luxe posé au dépôt par un joueur (ou resté
 * d'une livraison) entretient l'accès : quand il ne reste qu'un jour, le village en consomme {@value #CONSUME} et gagne
 * {@value #CONSUME_DAYS} jours.
 *
 * <p>Les luxes comptent pour la croissance : luxes en accès plus celui du terroir du peuple dès le palier 2 (Kevin :
 * le terroir compte). Il en faut {@value #TIER2} pour le chantier du palier 2, {@value #TIER3} pour celui du palier 3,
 * {@value #SETTLER} pour faire venir un colon ; chaque luxe en plus de ce que demande le palier donne
 * {@value #BONUS_STEP} % d'essor (au plus {@value #BONUS_MAX} %). Un village ne perd jamais son palier faute de luxes.
 *
 * <p>État sauvé ({@link WorldLifeRegistry.Part#TRADE_ACCESS}) : {@code village|objet = dernier jour d'accès}.
 */
public final class TradeAccess {

    public static final int DELIVERY_DAYS = 7;
    public static final int CONSUME = 2;
    public static final int CONSUME_DAYS = 3;
    public static final int TIER2 = 1;
    public static final int TIER3 = 3;
    public static final int SETTLER = 4;
    public static final int BONUS_STEP = 5;
    public static final int BONUS_MAX = 25;
    /** Marque des demandes « Luxe d'ailleurs » (ids {@code <Peuple>_Luxe_<luxe>}, tools/generate_trade.py). */
    public static final String REQUEST_MARK = "_Luxe_";

    /** Bonus d'essor (%) par village, recalculé chaque matin et à chaque livraison. */
    private static final Map<String, Integer> BONUS = new ConcurrentHashMap<>();
    /** Reste fractionnaire du bonus d'essor par village (centièmes). */
    private static final Map<String, Integer> CARRY = new ConcurrentHashMap<>();

    private TradeAccess() {
    }

    private static Map<String, String> part(World world) {
        return WorldLife.registry(world).part(WorldLifeRegistry.Part.TRADE_ACCESS);
    }

    /** Ouvre (ou prolonge) l'accès du village à l'objet jusqu'au jour `until` inclus ; `day` : aujourd'hui (bonus recalculé). */
    public static void grant(World world, Village v, String item, long until, long day) {
        String key = v.id() + "|" + item;
        long was = WorldLife.registry(world).getLong(WorldLifeRegistry.Part.TRADE_ACCESS, key, Long.MIN_VALUE);
        if (until > was) {
            part(world).put(key, Long.toString(until));
        }
        refresh(world, v, day);
    }

    /** Dernier jour d'accès (ou {@code Long.MIN_VALUE}). */
    public static long until(World world, Village v, String item) {
        return WorldLife.registry(world).getLong(WorldLifeRegistry.Part.TRADE_ACCESS, v.id() + "|" + item, Long.MIN_VALUE);
    }

    public static boolean has(World world, Village v, String item, long day) {
        return until(world, v, item) >= day;
    }

    /** Objets en accès ce jour (objet → dernier jour), dans l'ordre d'arrivée. */
    public static Map<String, Long> items(World world, Village v, long day) {
        Map<String, Long> out = new LinkedHashMap<>();
        String prefix = v.id() + "|";
        for (Map.Entry<String, String> e : part(world).entrySet()) {
            if (!e.getKey().startsWith(prefix)) {
                continue;
            }
            try {
                long until = Long.parseLong(e.getValue());
                if (until >= day) {
                    out.put(e.getKey().substring(prefix.length()), until);
                }
            } catch (NumberFormatException ignored) {
                // entrée abîmée : oubliée au matin
            }
        }
        return out;
    }

    /** Les luxes qui comptent pour le village ce jour : en accès, plus son terroir dès le palier 2. */
    public static List<TradeGoods.Luxury> luxuries(World world, Village v, long day) {
        List<TradeGoods.Luxury> out = new ArrayList<>();
        TradeGoods.Luxury own = TradeGoods.terroir(v.people());
        for (TradeGoods.Luxury l : TradeGoods.LUXURIES) {
            if ((l == own && v.tier() >= 2) || has(world, v, l.item(), day)) {
                out.add(l);
            }
        }
        return out;
    }

    public static int count(World world, Village v, long day) {
        return luxuries(world, v, day).size();
    }

    /** Le village voudrait ce luxe (demande « Luxe d'ailleurs ») : ni en accès, ni de son terroir. */
    public static boolean wanted(World world, Village v, String item, long day) {
        TradeGoods.Luxury own = TradeGoods.terroir(v.people());
        return item != null && (own == null || !own.item().equals(item)) && !has(world, v, item, day + 1);
    }

    /** Luxes que demande le palier atteint (0, 1 au palier 2, 3 au palier 3). */
    public static int needAt(int tier) {
        return tier >= 3 ? TIER3 : tier >= 2 ? TIER2 : 0;
    }

    /** Luxes qui manquent pour le chantier du palier `target` (0 : rien ne manque). */
    public static int missingFor(World world, Village v, int target, long day) {
        if (v.isHamlet()) {
            return 0;
        }
        return Math.max(0, needAt(target) - count(world, v, day));
    }

    /** Luxes qui manquent pour faire venir un colon. */
    public static int missingForSettler(World world, Village v, long day) {
        return v.isHamlet() ? 0 : Math.max(0, SETTLER - count(world, v, day));
    }

    /** Bonus d'essor (%) du village (cache du matin). */
    public static int bonus(Village v) {
        return BONUS.getOrDefault(v.id(), 0);
    }

    static void refresh(World world, Village v, long day) {
        if (v.isHamlet()) {
            return;
        }
        int extra = count(world, v, day) - needAt(v.tier());
        int bonus = Math.min(BONUS_MAX, Math.max(0, extra) * BONUS_STEP);
        if (bonus > 0) {
            BONUS.put(v.id(), bonus);
        } else {
            BONUS.remove(v.id());
        }
    }

    /** Essor en plus pour un gain de `amount` (bonus des luxes, avec reste fractionnaire). Appelé par {@link Villages#addEssor}. */
    public static int extraEssor(Village v, int amount) {
        int bonus = bonus(v);
        if (bonus <= 0 || amount <= 0) {
            return 0;
        }
        int hundredths = amount * bonus + CARRY.getOrDefault(v.id(), 0);
        CARRY.put(v.id(), hundredths % 100);
        return hundredths / 100;
    }

    /**
     * Le matin : accès échus effacés ; luxes du dépôt consommés pour prolonger un accès qui finit (le dépôt doit être
     * chargé) ; bonus recalculés.
     */
    static void morning(World world, long day) {
        part(world).entrySet().removeIf(e -> {
            try {
                return Long.parseLong(e.getValue()) < day - 1;
            } catch (NumberFormatException ex) {
                return true;
            }
        });
        for (Village v : Villages.registry(world).all()) {
            ItemContainer chest = Villages.depositChest(world, v);
            if (chest != null) {
                for (TradeGoods.Luxury l : TradeGoods.LUXURIES) {
                    if (until(world, v, l.item()) <= day && TradeGoods.stock(chest, l.item()) >= CONSUME) {
                        Requests.take(chest, l.item(), CONSUME);
                        grant(world, v, l.item(), Math.max(day, until(world, v, l.item())) + CONSUME_DAYS, day);
                    }
                }
            }
            refresh(world, v, day);
        }
    }

    /** Admin : ouvre l'accès à un objet (commande). */
    public static void force(World world, Village v, String item, long day, int days) {
        grant(world, v, item, day + days, day);
    }

    public static void clearAll() {
        BONUS.clear();
        CARRY.clear();
    }
}
