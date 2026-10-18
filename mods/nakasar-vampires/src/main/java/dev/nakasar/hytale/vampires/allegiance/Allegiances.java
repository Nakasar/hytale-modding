package dev.nakasar.hytale.vampires.allegiance;

import com.hypixel.hytale.builtin.tagset.config.NPCGroup;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.WorldSupport;
import dev.nakasar.hytale.vampires.domination.Dominations;

/**
 * Les camps des PNJ.
 *
 * <ul>
 *   <li>Les membres du groupe {@value #FACTION_GROUP} (les mobs du fragment Halloween) sont alliés entre eux :
 *       ils ne se ciblent pas et ne se blessent pas.</li>
 *   <li>Les chasseurs de vampires (groupe {@value #HUNTERS_GROUP}) et les mobs du fragment sont ennemis jurés :
 *       ils s'attaquent à vue.</li>
 *   <li>Un PNJ dominé change de camp le temps de la Domination : il est l'allié de son dominateur (et des autres
 *       PNJ du même dominateur) et l'ennemi de ses anciens alliés, qui le voient eux aussi comme un ennemi.</li>
 * </ul>
 * Anciens alliés : deux membres du groupe, ou deux PNJ dont le rôle se dit amical envers l'autre dans les groupes
 * d'attitude du jeu (mobs vanilla hors du fragment).
 */
public final class Allegiances {

    public static final String FACTION_GROUP = "Nakasar_Halloween_Faction";
    public static final String HUNTERS_GROUP = "Nakasar_Vampire_Hunters";

    private Allegiances() {
    }

    /**
     * Attitude imposée par un changement de camp, ou {@code null} si aucune domination ne concerne ces deux
     * entités ({@code source} est toujours un PNJ).
     */
    public static Attitude dominationAttitude(Ref<EntityStore> source, Ref<EntityStore> target,
                                              ComponentAccessor<EntityStore> accessor) {
        Ref<EntityStore> sourceMaster = Dominations.dominatorOf(source);
        Ref<EntityStore> targetMaster = Dominations.dominatorOf(target);
        if (sourceMaster == null && targetMaster == null) {
            return null;
        }
        if (sourceMaster != null && (target.equals(sourceMaster) || sourceMaster.equals(targetMaster))) {
            return Attitude.FRIENDLY;
        }
        if (sourceMaster != null && targetMaster != null) {
            return null; // chacun a changé de camp pour un maître différent
        }
        return wereAllies(source, target, accessor) ? Attitude.HOSTILE : null;
    }

    /** Vrai si les deux entités sont des PNJ du groupe {@value #FACTION_GROUP}. */
    public static boolean bothInFaction(Ref<EntityStore> a, Ref<EntityStore> b, ComponentAccessor<EntityStore> accessor) {
        return isNpc(a, accessor) && isNpc(b, accessor)
                && inGroup(a, FACTION_GROUP, accessor) && inGroup(b, FACTION_GROUP, accessor);
    }

    /** Vrai si l'un est un chasseur de vampires et l'autre un mob du fragment. */
    public static boolean huntersVsFaction(Ref<EntityStore> a, Ref<EntityStore> b, ComponentAccessor<EntityStore> accessor) {
        if (!isNpc(a, accessor) || !isNpc(b, accessor)) {
            return false;
        }
        return (inGroup(a, HUNTERS_GROUP, accessor) && inGroup(b, FACTION_GROUP, accessor))
                || (inGroup(a, FACTION_GROUP, accessor) && inGroup(b, HUNTERS_GROUP, accessor));
    }

    /** Vrai si l'entité est un PNJ du groupe de PNJ {@code groupId} (faux si le groupe n'est pas chargé). */
    public static boolean inGroup(Ref<EntityStore> ref, String groupId, ComponentAccessor<EntityStore> accessor) {
        int group = NPCGroup.getAssetMap().getIndexOrDefault(groupId, Integer.MIN_VALUE);
        return group != Integer.MIN_VALUE && isNpc(ref, accessor)
                && WorldSupport.isGroupMember(Integer.MIN_VALUE, ref, group, accessor);
    }

    /** Vrai si les deux PNJ étaient alliés, domination mise à part. */
    public static boolean wereAllies(Ref<EntityStore> a, Ref<EntityStore> b, ComponentAccessor<EntityStore> accessor) {
        return bothInFaction(a, b, accessor) || friendlyByRole(a, b, accessor) || friendlyByRole(b, a, accessor);
    }

    /** Attitude de base du rôle de {@code source} envers {@code target} (groupes d'attitude du jeu). */
    private static boolean friendlyByRole(Ref<EntityStore> source, Ref<EntityStore> target,
                                          ComponentAccessor<EntityStore> accessor) {
        NPCEntity npc = npc(source, accessor);
        if (npc == null || !isNpc(target, accessor)) {
            return false;
        }
        Attitude attitude = NPCPlugin.get().getAttitudeMap().getAttitude(source, npc.getRoleIndex(), target, accessor);
        return attitude == Attitude.FRIENDLY || attitude == Attitude.REVERED;
    }

    static boolean isNpc(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        return npc(ref, accessor) != null;
    }

    private static NPCEntity npc(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        return ref != null && ref.isValid() ? accessor.getComponent(ref, NPCEntity.getComponentType()) : null;
    }
}
