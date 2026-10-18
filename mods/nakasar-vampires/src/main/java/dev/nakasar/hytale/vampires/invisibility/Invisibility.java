package dev.nakasar.hytale.vampires.invisibility;

import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

/**
 * Invisibilité active (rune Invisibilité, {@link InvisibilityInteraction}) : le porteur reste caché tant qu'il ne
 * bouge pas de son point d'ancrage. Composant sans codec : jamais sauvegardé ; {@link InvisibilitySystem.Unload}
 * défait ses effets (intangibilité, joueurs aveuglés) si le porteur quitte le monde en pleine invisibilité.
 */
public final class Invisibility implements Component<EntityStore> {

    private static ComponentType<EntityStore, Invisibility> componentType;

    /** Secondes restantes avant la fin forcée. */
    float remaining;
    /** Temps pendant lequel l'ancrage suit encore le porteur (il finit son pas au lancer). */
    float settle;
    double anchorX;
    double anchorY;
    double anchorZ;
    /** Vrai si c'est l'invisibilité qui a rendu le porteur intangible (et doit donc le rendre tangible). */
    boolean intangibleByUs;
    /** Effet de statut posé (retiré à la fin), ou {@code null}. */
    String effectId;
    /** Identifiant du porteur s'il est joueur (pour le cacher aux autres), sinon {@code null}. */
    UUID self;
    /** Joueurs à qui le porteur est caché. */
    final Set<UUID> hiddenFrom = new HashSet<>();

    public static ComponentType<EntityStore, Invisibility> getComponentType() {
        return componentType;
    }

    public static void setComponentType(ComponentType<EntityStore, Invisibility> type) {
        componentType = type;
    }

    @Override
    public Invisibility clone() {
        Invisibility copy = new Invisibility();
        copy.remaining = remaining;
        copy.settle = settle;
        copy.anchorX = anchorX;
        copy.anchorY = anchorY;
        copy.anchorZ = anchorZ;
        copy.intangibleByUs = intangibleByUs;
        copy.effectId = effectId;
        copy.self = self;
        copy.hiddenFrom.addAll(hiddenFrom);
        return copy;
    }
}
