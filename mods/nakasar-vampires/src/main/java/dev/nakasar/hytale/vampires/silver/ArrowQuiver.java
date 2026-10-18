package dev.nakasar.hytale.vampires.silver;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.ArrayDeque;
import java.util.Deque;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Les flèches encochées ou chargées par chaque tireur, dans l'ordre : vrai pour une flèche en argent.
 *
 * <p>{@link TakeArrowInteraction} en ajoute une, le tir ({@link SilverProjectileSystems.Launch}) consomme la plus
 * ancienne, {@link ReturnArrowInteraction} rend la plus récente (arc relâché sans tirer, arbalète déchargée). Une
 * arbalète chargée avant un redémarrage du serveur a perdu sa liste : ses carreaux comptent comme simples.
 */
public final class ArrowQuiver {

    public static final String SILVER_ARROW = "Weapon_Nakasar_Arrow_Silver";
    public static final String CRUDE_ARROW = "Weapon_Arrow_Crude";

    /** Au-delà, les plus anciennes sont oubliées (une liste qui ne se vide plus après un tir perdu). */
    private static final int MAX_LOADED = 16;

    private static final Map<Ref<EntityStore>, Deque<Boolean>> LOADED = new ConcurrentHashMap<>();

    private ArrowQuiver() {
    }

    static void load(Ref<EntityStore> shooter, boolean silver) {
        LOADED.keySet().removeIf(ref -> !ref.isValid());
        Deque<Boolean> arrows = LOADED.computeIfAbsent(shooter, ref -> new ArrayDeque<>());
        synchronized (arrows) {
            arrows.addLast(silver);
            while (arrows.size() > MAX_LOADED) {
                arrows.removeFirst();
            }
        }
    }

    /** La plus ancienne flèche chargée part : vrai si elle est en argent (faux s'il n'y en a pas). */
    static boolean fire(Ref<EntityStore> shooter) {
        Deque<Boolean> arrows = LOADED.get(shooter);
        if (arrows == null) {
            return false;
        }
        synchronized (arrows) {
            Boolean silver = arrows.pollFirst();
            return silver != null && silver;
        }
    }

    /** La dernière flèche chargée revient : vrai si elle est en argent (faux s'il n'y en a pas). */
    static boolean unload(Ref<EntityStore> shooter) {
        Deque<Boolean> arrows = LOADED.get(shooter);
        if (arrows == null) {
            return false;
        }
        synchronized (arrows) {
            Boolean silver = arrows.pollLast();
            return silver != null && silver;
        }
    }

    public static void clearAll() {
        LOADED.clear();
    }
}
