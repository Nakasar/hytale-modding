package dev.nakasar.hytale.peuples.reputation;

import com.hypixel.hytale.builtin.adventure.reputation.ReputationGroupComponent;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathSystems;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.peuples.village.People;
import dev.nakasar.hytale.peuples.village.Village;
import dev.nakasar.hytale.peuples.village.Villages;
import org.joml.Vector3d;

/**
 * Ce qui fait baisser la réputation quand on s'en prend aux villageois (GDD, Jauges : « frapper un villageois ») :
 * un PNJ d'un peuple du mod (groupe de réputation {@code Nakasar_Peuples_<Peuple>}, donc tout Kweebec vanilla et les
 * PNJ du mod) frappé ou tué par un joueur. Près d'un village du peuple (à moins de
 * {@value Reputations#ATTITUDE_RADIUS} blocs), la perte va au village (et un tiers au peuple) ; ailleurs, au peuple
 * seulement.
 */
public final class VillagerHarmSystems {

    /** Perte par coup porté à un villageois. */
    public static final int HIT = -5;
    /** Perte quand un villageois meurt de la main du joueur (en plus du coup). */
    public static final int KILL = -40;

    private VillagerHarmSystems() {
    }

    /** Joueur attaquant de `damage`, ou null. */
    public static Ref<EntityStore> attacker(Damage damage) {
        return damage != null && damage.getSource() instanceof Damage.EntitySource source ? source.getRef() : null;
    }

    /** Étape 7 : bandes des demandes et pillards des raids ne sont pas des villageois (leur groupe vanilla Trork compte sinon). */
    static boolean exempt(Ref<EntityStore> npc) {
        if (npc == null) {
            return false;
        }
        var owner = dev.nakasar.hytale.peuples.request.RequestSpawns.owner(npc);
        return owner != null && (owner.kind() == dev.nakasar.hytale.peuples.request.RequestSpawns.Kind.FOE
                || owner.kind() == dev.nakasar.hytale.peuples.request.RequestSpawns.Kind.GUARD)
                || dev.nakasar.hytale.peuples.raid.Raids.kind(npc) == dev.nakasar.hytale.peuples.raid.Raids.Kind.RAIDER;
    }

    static void punish(World world, PlayerRef player, People people, Vector3d where, int amount, String reasonKey) {
        world.execute(() -> {
            Store<EntityStore> store = world.getEntityStore().getStore();
            Ref<EntityStore> ref = player.getReference();
            if (ref == null || !ref.isValid()) {
                return;
            }
            Village village = Villages.registry(world).nearestOf(people, where.x(), where.z(), Reputations.ATTITUDE_RADIUS);
            if (village != null) {
                Reputations.change(world, store, ref, player, village, amount, reasonKey);
            } else if (people != People.TRORK) {
                // Étape 7 : hors d'un camp, les Trorks sauvages sont des ennemis (chasses kweebecs) : pas de perte.
                Reputations.changePeople(store, ref, people, amount);
            }
        });
    }

    /** Coup porté par un joueur à un villageois (dégâts déjà calculés, non annulés). */
    public static final class Hit extends DamageEventSystem {

        @Override
        public SystemGroup<EntityStore> getGroup() {
            return DamageModule.get().getInspectDamageGroup();
        }

        @Override
        public Query<EntityStore> getQuery() {
            return Query.and(NPCEntity.getComponentType(), ReputationGroupComponent.getComponentType());
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, Damage damage) {
            if (damage.isCancelled() || damage.getAmount() <= 0f) {
                return;
            }
            Ref<EntityStore> source = attacker(damage);
            PlayerRef player = source == null || !source.isValid() ? null : buffer.getComponent(source, PlayerRef.getComponentType());
            if (player == null) {
                return;
            }
            ReputationGroupComponent group = chunk.getComponent(index, ReputationGroupComponent.getComponentType());
            People people = group == null ? null : Reputations.peopleOfGroup(group.getReputationGroupId());
            TransformComponent transform = chunk.getComponent(index, TransformComponent.getComponentType());
            if (people == null || transform == null || exempt(chunk.getReferenceTo(index))) {
                return;
            }
            punish(store.getExternalData().getWorld(), player, people, new Vector3d(transform.getPosition()), HIT,
                    Reputations.KEYS + "reason.hit");
        }
    }

    /** Villageois tué par un joueur. */
    public static final class Kill extends DeathSystems.OnDeathSystem {

        @Override
        public Query<EntityStore> getQuery() {
            return Query.and(NPCEntity.getComponentType(), ReputationGroupComponent.getComponentType());
        }

        @Override
        public void onComponentAdded(Ref<EntityStore> ref, DeathComponent death, Store<EntityStore> store, CommandBuffer<EntityStore> buffer) {
            Ref<EntityStore> source = attacker(death.getDeathInfo());
            PlayerRef player = source == null || !source.isValid() ? null : buffer.getComponent(source, PlayerRef.getComponentType());
            if (player == null) {
                return;
            }
            ReputationGroupComponent group = buffer.getComponent(ref, ReputationGroupComponent.getComponentType());
            People people = group == null ? null : Reputations.peopleOfGroup(group.getReputationGroupId());
            TransformComponent transform = buffer.getComponent(ref, TransformComponent.getComponentType());
            if (people == null || transform == null || exempt(ref)) {
                return;
            }
            punish(store.getExternalData().getWorld(), player, people, new Vector3d(transform.getPosition()), KILL,
                    Reputations.KEYS + "reason.kill");
        }
    }
}
