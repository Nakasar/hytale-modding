package dev.nakasar.hytale.vampires.invisibility;

import com.hypixel.hytale.component.AddReason;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Holder;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.component.system.HolderSystem;
import com.hypixel.hytale.component.system.tick.DelayedEntitySystem;
import com.hypixel.hytale.component.system.tick.EntityTickingSystem;
import com.hypixel.hytale.server.core.asset.type.entityeffect.config.EntityEffect;
import com.hypixel.hytale.server.core.entity.effect.EffectControllerComponent;
import com.hypixel.hytale.server.core.modules.entity.component.Intangible;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.Universe;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.MarkedEntitySupport;
import org.joml.Vector3d;

import java.util.UUID;

/**
 * Fait vivre l'invisibilité ({@link Invisibility}) : chaque tick, cache le porteur aux joueurs de son monde et la
 * termine s'il s'écarte de plus de {@value #TOLERANCE} bloc de son point d'ancrage (marche, saut, chute, poussée)
 * ou au bout de sa durée. Les classes internes la terminent aussi quand le porteur frappe ({@link BreakOnAttack}),
 * effacent le porteur des cibles des PNJ ({@link ForgetInvisible}) et la défont au déchargement ({@link Unload}).
 */
public final class InvisibilitySystem extends EntityTickingSystem<EntityStore> {

    /** Écart (blocs) au point d'ancrage qui rompt l'invisibilité. */
    static final double TOLERANCE = 0.3;
    /** Secondes après le lancer pendant lesquelles l'ancrage suit le porteur, le temps qu'il finisse son pas. */
    static final float SETTLE = 0.3f;

    @Override
    public Query<EntityStore> getQuery() {
        return Query.and(Invisibility.getComponentType(), TransformComponent.getComponentType());
    }

    @Override
    public boolean isParallel(int archetypeChunkSize, int taskCount) {
        return false; // modifie les listes de joueurs cachés
    }

    @Override
    public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                     CommandBuffer<EntityStore> buffer) {
        Ref<EntityStore> ref = chunk.getReferenceTo(index);
        Invisibility invisibility = chunk.getComponent(index, Invisibility.getComponentType());
        Vector3d position = chunk.getComponent(index, TransformComponent.getComponentType()).getPosition();
        invisibility.remaining -= dt;
        if (invisibility.settle > 0) {
            invisibility.settle -= dt;
            invisibility.anchorX = position.x;
            invisibility.anchorY = position.y;
            invisibility.anchorZ = position.z;
        }
        double dx = position.x - invisibility.anchorX;
        double dy = position.y - invisibility.anchorY;
        double dz = position.z - invisibility.anchorZ;
        if (invisibility.remaining <= 0 || dx * dx + dy * dy + dz * dz > TOLERANCE * TOLERANCE) {
            end(ref, invisibility, buffer);
            return;
        }
        if (invisibility.self == null) {
            PlayerRef self = buffer.getComponent(ref, PlayerRef.getComponentType());
            if (self == null) {
                return; // un PNJ : seuls les autres PNJ cessent de le voir
            }
            invisibility.self = self.getUuid();
        }
        // à chaque tick, pour les joueurs arrivés depuis le lancer
        for (PlayerRef viewer : buffer.getExternalData().getWorld().getPlayerRefs()) {
            UUID uuid = viewer.getUuid();
            if (!uuid.equals(invisibility.self) && invisibility.hiddenFrom.add(uuid)) {
                viewer.getHiddenPlayersManager().hidePlayer(invisibility.self);
            }
        }
    }

    /** Termine l'invisibilité du porteur : visible, tangible, effet de statut retiré. */
    static void end(Ref<EntityStore> ref, Invisibility invisibility, CommandBuffer<EntityStore> buffer) {
        reveal(invisibility);
        if (invisibility.intangibleByUs) {
            buffer.tryRemoveComponent(ref, Intangible.getComponentType());
        }
        if (invisibility.effectId != null) {
            EffectControllerComponent effects = buffer.getComponent(ref, EffectControllerComponent.getComponentType());
            int effect = EntityEffect.getAssetMap().getIndex(invisibility.effectId);
            if (effects != null && effect >= 0) {
                effects.removeEffect(ref, effect, buffer);
            }
        }
        buffer.tryRemoveComponent(ref, Invisibility.getComponentType());
    }

    /** Montre de nouveau le porteur aux joueurs à qui il était caché, où qu'ils soient. */
    private static void reveal(Invisibility invisibility) {
        if (invisibility.self == null) {
            return;
        }
        for (UUID uuid : invisibility.hiddenFrom) {
            PlayerRef viewer = Universe.get().getPlayer(uuid);
            if (viewer != null) {
                viewer.getHiddenPlayersManager().showPlayer(invisibility.self);
            }
        }
        invisibility.hiddenFrom.clear();
    }

    /** Le porteur qui inflige des dégâts (coup, projectile, sort) redevient visible. */
    public static final class BreakOnAttack extends DamageEventSystem {

        @Override
        public SystemGroup<EntityStore> getGroup() {
            return DamageModule.get().getInspectDamageGroup();
        }

        @Override
        public Query<EntityStore> getQuery() {
            return TransformComponent.getComponentType();
        }

        @Override
        public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                           CommandBuffer<EntityStore> buffer, Damage damage) {
            if (damage.isCancelled() || !(damage.getSource() instanceof Damage.EntitySource source)) {
                return;
            }
            Ref<EntityStore> attacker = source.getRef();
            if (attacker == null || !attacker.isValid()) {
                return;
            }
            Invisibility invisibility = buffer.getComponent(attacker, Invisibility.getComponentType());
            if (invisibility != null) {
                end(attacker, invisibility, buffer);
            }
        }
    }

    /**
     * Les PNJ oublient les cibles invisibles qu'ils suivaient déjà : leurs capteurs ignorent une entité intangible,
     * mais une cible verrouillée avant le lancer resterait sinon en mémoire.
     */
    public static final class ForgetInvisible extends DelayedEntitySystem<EntityStore> {

        public ForgetInvisible() {
            super(0.25f);
        }

        @Override
        public Query<EntityStore> getQuery() {
            return Query.and(NPCEntity.getComponentType(), MarkedEntitySupport.getComponentType());
        }

        @Override
        public void tick(float dt, int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                         CommandBuffer<EntityStore> buffer) {
            MarkedEntitySupport marked = chunk.getComponent(index, MarkedEntitySupport.getComponentType());
            for (int slot = 0; slot < marked.getMarkedEntitySlotCount(); slot++) {
                Ref<EntityStore> target = marked.getMarkedEntityRef(slot);
                if (target != null && target.isValid()
                        && buffer.getComponent(target, Invisibility.getComponentType()) != null) {
                    marked.clearMarkedEntity(slot);
                }
            }
        }
    }

    /** Porteur déchargé, déconnecté ou changeant de monde : on défait l'invisibilité avant la sauvegarde. */
    public static final class Unload extends HolderSystem<EntityStore> {

        @Override
        public Query<EntityStore> getQuery() {
            return Invisibility.getComponentType();
        }

        @Override
        public void onEntityAdd(Holder<EntityStore> holder, AddReason reason, Store<EntityStore> store) {
        }

        @Override
        public void onEntityRemoved(Holder<EntityStore> holder, RemoveReason reason, Store<EntityStore> store) {
            Invisibility invisibility = holder.getComponent(Invisibility.getComponentType());
            if (invisibility != null) {
                reveal(invisibility);
                if (invisibility.intangibleByUs) {
                    holder.tryRemoveComponent(Intangible.getComponentType());
                }
            }
            holder.tryRemoveComponent(Invisibility.getComponentType());
        }
    }
}
