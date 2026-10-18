package dev.nakasar.hytale.vampires.pumpkin;

import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Marque une victime du piège de vrilles ({@link RootTrapInteraction}) tant que sa vrille la retient. Composant
 * sans codec : il n'est jamais sauvegardé. {@link RootTrapUnloadSystem} s'en sert pour retirer le gel d'un PNJ
 * déchargé ou supprimé en plein piège, qui sinon resterait gelé au rechargement ({@code Frozen} est sauvegardé).
 */
public final class RootTrapped implements Component<EntityStore> {

    private static ComponentType<EntityStore, RootTrapped> componentType;

    /** Vrai si c'est le piège qui a posé {@code Frozen} sur ce PNJ (et doit donc le retirer). */
    boolean frozenByUs;

    public static ComponentType<EntityStore, RootTrapped> getComponentType() {
        return componentType;
    }

    public static void setComponentType(ComponentType<EntityStore, RootTrapped> type) {
        componentType = type;
    }

    @Override
    public RootTrapped clone() {
        RootTrapped copy = new RootTrapped();
        copy.frozenByUs = frozenByUs;
        return copy;
    }
}
