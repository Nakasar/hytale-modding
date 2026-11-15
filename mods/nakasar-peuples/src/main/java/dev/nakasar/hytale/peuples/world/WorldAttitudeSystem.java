package dev.nakasar.hytale.peuples.world;

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
import com.hypixel.hytale.server.npc.systems.BlackboardSystems;

import java.util.Set;

/**
 * Camps des combats du monde vivant ({@link WorldLife#side}) : deux PNJ de la même clé (une embuscade, une
 * escarmouche, l'attaque d'un campement) et d'équipes différentes sont hostiles l'un à l'autre, de la même équipe amis.
 * Priorité {@value #PRIORITY}, juste avant les raids ({@code RaidAttitudeSystem}, 80) : les pillards d'une embuscade
 * attaquent une caravane de n'importe quel peuple, et les gardes de deux villages rivaux se battent entre eux.
 */
public final class WorldAttitudeSystem extends StoreSystem<EntityStore> {

    public static final int PRIORITY = 79;

    private static final Set<Dependency<EntityStore>> DEPENDENCIES =
            Set.of(new SystemDependency<>(Order.AFTER, BlackboardSystems.InitSystem.class));

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

    @Override
    public void onSystemAddedToStore(Store<EntityStore> store) {
        AttitudeView view = store.getResource(Blackboard.getResourceType()).getView(AttitudeView.class, 0L);
        view.registerProvider(PRIORITY, (IAttitudeProvider) (ref, roleIndex, target, accessor) -> attitude(ref, target));
    }

    @Override
    public void onSystemRemovedFromStore(Store<EntityStore> store) {
    }

    private static Attitude attitude(Ref<EntityStore> ref, Ref<EntityStore> target) {
        WorldLife.Side a = WorldLife.sideOf(ref);
        WorldLife.Side b = a == null ? null : WorldLife.sideOf(target);
        if (b == null || !a.key().equals(b.key())) {
            return null;
        }
        return a.team() == b.team() ? Attitude.FRIENDLY : Attitude.HOSTILE;
    }
}
