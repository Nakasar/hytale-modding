package dev.nakasar.hytale.fractals.cliffside;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.AnimationSlot;
import com.hypixel.hytale.server.core.asset.type.itemanimation.config.ItemPlayerAnimations;
import com.hypixel.hytale.server.core.entity.AnimationUtils;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.FractalsPlugin;

/**
 * Gestes d'incantation d'un incantateur qui répare un sceau : coups de bâton alternés (jeu d'animations
 * {@value #ANIMATIONS}, celui de leurs attaques), joués depuis le Java pendant qu'il est figé devant le sceau.
 */
final class Chanting {

    static final String ANIMATIONS = "Staff";
    private static boolean warned;

    private Chanting() {
    }

    static void cast(Store<EntityStore> store, Ref<EntityStore> ref, boolean right) {
        if (ref == null || !ref.isValid()) {
            return;
        }
        try {
            ItemPlayerAnimations animations = ItemPlayerAnimations.getAssetMap().getAsset(ANIMATIONS);
            if (animations != null) {
                AnimationUtils.playAnimation(ref, AnimationSlot.Action, animations, right ? "SwingRight" : "SwingLeft", store);
            }
        } catch (RuntimeException e) {
            if (!warned) {
                warned = true;
                FractalsPlugin.get().getLogger().atWarning().log("Incantation : animation %s impossible (%s)", ANIMATIONS, e);
            }
        }
    }
}
