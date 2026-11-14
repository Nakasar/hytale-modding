package dev.nakasar.hytale.peuples.raid;

import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.system.StoreSystem;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.blackboard.Blackboard;
import com.hypixel.hytale.server.npc.blackboard.view.attitude.AttitudeView;
import com.hypixel.hytale.server.npc.blackboard.view.attitude.IAttitudeProvider;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.systems.BlackboardSystems;

import java.util.Set;

/**
 * Pillards contre villageois : un pillard ({@value Raids#RAIDER_PREFIX}*) est hostile à tout PNJ kweebec (gardes du
 * raid, villageois des prefabs) et amical envers les autres pillards ; un Kweebec est hostile aux pillards. Priorité
 * {@value #PRIORITY}, avant le rang de village (90) : les groupes vanilla ne suffisent pas (les Razorleaf vanilla ne
 * voient que les joueurs).
 */
public final class RaidAttitudeSystem extends StoreSystem<EntityStore> {

    public static final int PRIORITY = 80;

    private static final Set<Dependency<EntityStore>> DEPENDENCIES =
            Set.of(new SystemDependency<>(Order.AFTER, BlackboardSystems.InitSystem.class));

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

    @Override
    public void onSystemAddedToStore(Store<EntityStore> store) {
        AttitudeView view = store.getResource(Blackboard.getResourceType()).getView(AttitudeView.class, 0L);
        view.registerProvider(PRIORITY, (IAttitudeProvider) (ref, roleIndex, target, accessor) -> attitude(ref, target, accessor));
    }

    @Override
    public void onSystemRemovedFromStore(Store<EntityStore> store) {
    }

    private static Attitude attitude(Ref<EntityStore> ref, Ref<EntityStore> target,
                                                                                         ComponentAccessor<EntityStore> accessor) {
        if (ref == null || target == null || !ref.isValid() || !target.isValid()) {
            return null;
        }
        String self = role(ref, accessor);
        String other = role(target, accessor);
        if (self == null || other == null) {
            return null;
        }
        boolean selfRaider = Raids.isRaiderRole(self);
        boolean otherRaider = Raids.isRaiderRole(other);
        if (selfRaider && otherRaider) {
            return Attitude.FRIENDLY;
        }
        if (selfRaider && other.contains("Kweebec") || otherRaider && self.contains("Kweebec")) {
            return Attitude.HOSTILE;
        }
        return null;
    }

    private static String role(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        NPCEntity npc = accessor.getComponent(ref, NPCEntity.getComponentType());
        return npc == null ? null : npc.getRoleName();
    }
}
