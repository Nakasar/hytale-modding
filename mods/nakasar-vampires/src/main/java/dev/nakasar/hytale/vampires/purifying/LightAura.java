package dev.nakasar.hytale.vampires.purifying;

import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.protocol.ColorLight;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * Aura de lumière active sur une entité (rune Aura de lumière, {@link LightAuraInteraction}). Composant sans codec :
 * il n'est jamais sauvegardé, et {@link LightAuraSystem.Unload} rend sa lumière d'origine à une entité déchargée en
 * pleine aura.
 */
public final class LightAura implements Component<EntityStore> {

    private static ComponentType<EntityStore, LightAura> componentType;

    /** Secondes restantes. */
    float remaining;
    /** Vrai si c'est l'aura qui a posé la lumière dynamique de l'entité (et doit donc la retirer ou la rendre). */
    boolean lightByUs;
    /** Lumière dynamique que l'entité portait avant l'aura, rendue à la fin ; {@code null} s'il n'y en avait pas. */
    ColorLight previousLight;

    public static ComponentType<EntityStore, LightAura> getComponentType() {
        return componentType;
    }

    public static void setComponentType(ComponentType<EntityStore, LightAura> type) {
        componentType = type;
    }

    /** Oublie la lumière d'avant l'aura si c'est {@code light} : l'aura l'éteindra au lieu de la rendre. */
    public void forgetPreviousLight(ColorLight light) {
        if (light != null && light.equals(previousLight)) {
            previousLight = null;
        }
    }

    @Override
    public LightAura clone() {
        LightAura copy = new LightAura();
        copy.remaining = remaining;
        copy.lightByUs = lightByUs;
        copy.previousLight = previousLight == null ? null : new ColorLight(previousLight);
        return copy;
    }
}
