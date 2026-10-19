package dev.nakasar.hytale.vampires.lords;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.vampires.allegiance.Allegiances;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * La colère du Comte et de la Comtesse (groupe de PNJ {@value #LORDS_GROUP}).
 *
 * <p>Dans le Comté, les seigneurs vampires laissent passer les joueurs : leur rôle leur donne une attitude neutre.
 * Un joueur qui en frappe un le met en colère pour {@value #WRATH_SECONDS} s, et la colère vise <b>tous</b> les
 * joueurs, pas seulement l'attaquant : le groupe présent paie pour l'affront. Chaque coup échangé (reçu d'un joueur
 * ou porté à un joueur) relance le délai ; sans échange, le seigneur se calme, rentre à son trône et redevient
 * neutre.
 */
public final class LordsWrath {

    public static final String LORDS_GROUP = "Nakasar_Vampire_Lords";
    public static final float WRATH_SECONDS = 45f;

    private static final Map<Ref<EntityStore>, Long> WRATH_UNTIL = new ConcurrentHashMap<>();

    private LordsWrath() {
    }

    /** Met le seigneur en colère (ou prolonge sa colère). */
    public static void provoke(Ref<EntityStore> lord) {
        long now = System.nanoTime();
        WRATH_UNTIL.put(lord, now + (long) (WRATH_SECONDS * 1_000_000_000L));
        WRATH_UNTIL.entrySet().removeIf(e -> !e.getKey().isValid() || e.getValue() < now);
    }

    /** Vrai si ce seigneur est en colère. */
    public static boolean isEnraged(Ref<EntityStore> lord) {
        Long until = WRATH_UNTIL.get(lord);
        return until != null && lord.isValid() && until >= System.nanoTime();
    }

    /** Vrai si l'entité est le Comte ou la Comtesse. */
    public static boolean isLord(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        return Allegiances.inGroup(ref, LORDS_GROUP, accessor);
    }

    static boolean isPlayer(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        return ref != null && ref.isValid() && accessor.getComponent(ref, Player.getComponentType()) != null;
    }

    /**
     * Attitude d'un seigneur en colère envers un joueur : hostile ; {@code null} sinon (attitude neutre du rôle).
     */
    public static Attitude attitude(Ref<EntityStore> source, Ref<EntityStore> target,
                                    ComponentAccessor<EntityStore> accessor) {
        return isEnraged(source) && isPlayer(target, accessor) && isLord(source, accessor) ? Attitude.HOSTILE : null;
    }

    public static void clearAll() {
        WRATH_UNTIL.clear();
    }
}
