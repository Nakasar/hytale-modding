package dev.nakasar.hytale.vampires.lords;

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
 * Branche la colère des seigneurs vampires ({@link LordsWrath}) sur le calcul d'attitude des PNJ, en priorité -5 :
 * après la Domination (-10, voir {@code AllegianceAttitudeSystem}), avant tout le reste. Sans colère, le fournisseur
 * ne dit rien et l'attitude neutre du rôle s'applique.
 */
public final class LordsAttitudeSystem extends StoreSystem<EntityStore> {

    private static final Set<Dependency<EntityStore>> DEPENDENCIES =
            Set.of(new SystemDependency<>(Order.AFTER, BlackboardSystems.InitSystem.class));

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

    @Override
    public void onSystemAddedToStore(Store<EntityStore> store) {
        AttitudeView view = store.getResource(Blackboard.getResourceType()).getView(AttitudeView.class, 0L);
        view.registerProvider(-5, (IAttitudeProvider) (ref, roleIndex, target, accessor) ->
                LordsWrath.attitude(ref, target, accessor));
    }

    @Override
    public void onSystemRemovedFromStore(Store<EntityStore> store) {
    }
}
