package dev.nakasar.hytale.peuples.reputation;

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
 * Branche le rang de village sur l'attitude des PNJ ({@link Reputations#villageAttitude}). L'{@link AttitudeView}
 * d'un monde interroge ses fournisseurs par priorité croissante (lu dans le mod Vampires et le serveur 0.7.7) :
 * 0 = attitudes imposées par les rôles ({@code OverrideAttitude} : un Kweebec frappé reste hostile), 100 = réputation
 * vanilla (ReputationPlugin, ici la réputation de peuple), 200 = groupes d'attitude des rôles, puis l'attitude par
 * défaut du rôle. Le rang de village passe en {@value #PRIORITY}, juste avant la réputation de peuple ; hors d'un
 * village, il ne répond rien et la réputation de peuple décide.
 *
 * <p>Ce que cela change chez les Kweebecs vanilla (rôles d'Assets.zip) : neutre, les gardes Razorleaf suivent le joueur
 * du regard (état Alerted) et les jeunes s'inquiètent de lui ; amical ou vénéré, ils l'ignorent tranquillement ;
 * hostile, les gardes l'attaquent et les jeunes fuient.
 */
public final class VillageAttitudeSystem extends StoreSystem<EntityStore> {

    public static final int PRIORITY = 90;

    private static final Set<Dependency<EntityStore>> DEPENDENCIES =
            Set.of(new SystemDependency<>(Order.AFTER, BlackboardSystems.InitSystem.class));

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

    @Override
    public void onSystemAddedToStore(Store<EntityStore> store) {
        AttitudeView view = store.getResource(Blackboard.getResourceType()).getView(AttitudeView.class, 0L);
        view.registerProvider(PRIORITY, (IAttitudeProvider) (ref, roleIndex, target, accessor) ->
                Reputations.villageAttitude(store, ref, target, accessor));
    }

    @Override
    public void onSystemRemovedFromStore(Store<EntityStore> store) {
    }
}
