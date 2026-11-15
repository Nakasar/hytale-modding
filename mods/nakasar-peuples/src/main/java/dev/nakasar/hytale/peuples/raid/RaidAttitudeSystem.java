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
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.systems.BlackboardSystems;

import java.util.Set;

/**
 * Pillards contre villageois : un pillard ({@value Raids#RAIDER_PREFIX}*) est hostile aux PNJ du peuple qu'il attaque
 * ({@link Raids#preys} : Trorks contre Kweebecs, Scaraks contre Feran, culte contre Renoncés ; gardes du raid, villageois
 * des prefabs) et amical envers les autres pillards ; ses proies lui sont hostiles. Priorité
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
        // Demandes de caravane et de récolte escortée : les assaillants d'une embuscade et les PNJ escortés de la même
        // demande se battent, quel que soit le peuple (un clan trork rival attaque aussi une caravane trork).
        dev.nakasar.hytale.peuples.request.RequestSpawns.Owner so = dev.nakasar.hytale.peuples.request.RequestSpawns.owner(ref);
        dev.nakasar.hytale.peuples.request.RequestSpawns.Owner to = so == null ? null : dev.nakasar.hytale.peuples.request.RequestSpawns.owner(target);
        if (so != null && to != null && so.key().equals(to.key())) {
            boolean a = so.kind() == dev.nakasar.hytale.peuples.request.RequestSpawns.Kind.AMBUSH;
            boolean b = to.kind() == dev.nakasar.hytale.peuples.request.RequestSpawns.Kind.AMBUSH;
            boolean ea = so.kind() == dev.nakasar.hytale.peuples.request.RequestSpawns.Kind.ESCORTED;
            boolean eb = to.kind() == dev.nakasar.hytale.peuples.request.RequestSpawns.Kind.ESCORTED;
            if (a && eb || ea && b) {
                return Attitude.HOSTILE;
            }
            // Demande de chef : le chef et ses renforts sont du même camp, ils ne se battent jamais entre eux.
            if (bossSide(so.kind()) && bossSide(to.kind())) {
                return Attitude.FRIENDLY;
            }
        }
        String self = role(ref, accessor);
        if (self != null && Raids.isRaiderRole(self) && accessor.getComponent(target, Player.getComponentType()) != null) {
            // Étape 7 : le groupe vanilla Trork (*Trork*) donne aux pillards la réputation de peuple trork ; un raid reste
            // hostile à tout joueur, même ami du camp trork ou sous Peinture de guerre.
            return Attitude.HOSTILE;
        }
        String other = role(target, accessor);
        if (self == null || other == null) {
            return null;
        }
        boolean selfRaider = Raids.isRaiderRole(self);
        boolean otherRaider = Raids.isRaiderRole(other);
        if (selfRaider && otherRaider) {
            return Attitude.FRIENDLY;
        }
        if (selfRaider && Raids.preys(self, other) || otherRaider && Raids.preys(other, self)) {
            return Attitude.HOSTILE;
        }
        return null;
    }

    private static boolean bossSide(dev.nakasar.hytale.peuples.request.RequestSpawns.Kind kind) {
        return kind == dev.nakasar.hytale.peuples.request.RequestSpawns.Kind.BOSS
                || kind == dev.nakasar.hytale.peuples.request.RequestSpawns.Kind.ADD;
    }

    private static String role(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        NPCEntity npc = accessor.getComponent(ref, NPCEntity.getComponentType());
        return npc == null ? null : npc.getRoleName();
    }
}
