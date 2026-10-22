package dev.nakasar.hytale.fractals.combat;

import com.hypixel.hytale.builtin.tagset.config.NPCGroup;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.WorldSupport;

/**
 * Le camp des fractales : tous les PNJ des fractales (boss, adds, serviteurs) sont membres du groupe
 * {@value #GROUP} et ne se blessent pas entre eux avec les attaques de zone du mod ({@link TelegraphInteraction}).
 * Pas de Domination ni de chasseurs ici, contrairement au mod Vampires : un seul camp, face aux joueurs.
 */
public final class Foes {

    public static final String GROUP = "Nakasar_Fractal_Foes";

    private Foes() {
    }

    /** Vrai si les deux entités sont des PNJ du groupe {@value #GROUP}. */
    public static boolean allies(Ref<EntityStore> a, Ref<EntityStore> b, ComponentAccessor<EntityStore> accessor) {
        return inGroup(a, accessor) && inGroup(b, accessor);
    }

    /** Vrai si l'entité est un PNJ du groupe {@value #GROUP} (faux si le groupe n'est pas chargé). */
    public static boolean inGroup(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        if (ref == null || !ref.isValid() || accessor.getComponent(ref, NPCEntity.getComponentType()) == null) {
            return false;
        }
        int group = NPCGroup.getAssetMap().getIndexOrDefault(GROUP, Integer.MIN_VALUE);
        return group != Integer.MIN_VALUE && WorldSupport.isGroupMember(Integer.MIN_VALUE, ref, group, accessor);
    }
}
