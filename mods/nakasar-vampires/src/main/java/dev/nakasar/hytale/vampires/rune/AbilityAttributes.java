package dev.nakasar.hytale.vampires.rune;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.entity.InteractionContext;
import com.hypixel.hytale.server.core.modules.projectile.component.ImpactModifiers;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/** Petits utilitaires partagés par les interactions du mod. */
public final class AbilityAttributes {

    private AbilityAttributes() {
    }

    /**
     * Résout une valeur authored, remplacée par l'attribut d'ability nommé quand le lancer en porte un.
     * Même sémantique que les clés {@code *Attribute} des interactions vanilla (remplacement, pas multiplication).
     */
    public static float resolve(InteractionContext context, Ref<EntityStore> acting,
                         ComponentAccessor<EntityStore> accessor, String attribute, float fallback) {
        if (attribute == null || attribute.isBlank() || acting == null || !acting.isValid()) {
            return fallback;
        }
        ImpactModifiers modifiers = ImpactModifiers.resolve(context, acting, accessor);
        if (modifiers == null) {
            return fallback;
        }
        return modifiers.getAttribute(attribute, fallback);
    }

    /** Le lanceur d'une chaîne : l'entité propriétaire quand il y en a une (projectile), sinon l'exécutant. */
    public static Ref<EntityStore> caster(InteractionContext context) {
        Ref<EntityStore> owner = context.getOwningEntity();
        if (owner != null && owner.isValid()) {
            return owner;
        }
        return context.getEntity();
    }
}
