package dev.nakasar.hytale.vampires.allegiance;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.system.StoreSystem;
import com.hypixel.hytale.server.core.asset.type.attitude.Attitude;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.blackboard.Blackboard;
import com.hypixel.hytale.server.npc.blackboard.view.attitude.AttitudeView;
import com.hypixel.hytale.server.npc.blackboard.view.attitude.IAttitudeProvider;
import com.hypixel.hytale.server.npc.systems.BlackboardSystems;

import java.util.Set;

/**
 * Branche les camps de {@link Allegiances} sur le calcul d'attitude des PNJ (filtres {@code Attitude} des capteurs),
 * comme le fait le module de réputation du jeu. L'{@link AttitudeView} interroge ses fournisseurs par priorité
 * croissante : 0 = attitudes imposées par les rôles ({@code OverrideAttitude}), 100 = même lignée d'apparition,
 * 200 = groupes d'attitude des rôles, puis attitudes par défaut du rôle.
 * <ul>
 *   <li>priorité -10 : changement de camp par la Domination, avant tout le reste ;</li>
 *   <li>priorité 150 : deux mobs du fragment sont amis, sauf si un rôle a imposé autre chose.</li>
 * </ul>
 * Les PNJ gardent leurs attitudes en cache 0,1 s : un changement de camp est vu presque aussitôt.
 */
public final class AllegianceAttitudeSystem extends StoreSystem<EntityStore> {

    // L'AttitudeView d'un monde est créée par l'initialisation du Blackboard.
    private static final Set<Dependency<EntityStore>> DEPENDENCIES =
            Set.of(new SystemDependency<>(Order.AFTER, BlackboardSystems.InitSystem.class));

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

    @Override
    public void onSystemAddedToStore(Store<EntityStore> store) {
        AttitudeView view = store.getResource(Blackboard.getResourceType()).getView(AttitudeView.class, 0L);
        view.registerProvider(-10, (IAttitudeProvider) (ref, roleIndex, target, accessor) ->
                Allegiances.dominationAttitude(ref, target, accessor));
        view.registerProvider(150, (IAttitudeProvider) (ref, roleIndex, target, accessor) ->
                Allegiances.bothInFaction(ref, target, accessor) ? Attitude.FRIENDLY : null);
    }

    @Override
    public void onSystemRemovedFromStore(Store<EntityStore> store) {
    }
}
