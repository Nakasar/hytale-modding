package dev.nakasar.hytale.vampires.pumpkin;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.vampires.allegiance.AllegianceDamageFilter;

import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Bouclier de la citrouille géante ({@value #ROLE}) : tant qu'une de ses vrilles combattantes est vivante, aucun coup
 * ne la blesse ; le joueur qui frappe est prévenu (au plus une fois toutes les {@value #WARN_SECONDS} s). Il faut
 * détruire la vague pour l'atteindre, jusqu'à la vague suivante (son IA, 10 à 12 s plus tard).
 *
 * <p>Si elle prend un coup alors qu'elle n'a pas de vrilles et n'a lancé aucune invocation depuis
 * {@value #FIRST_WAVE_SECONDS} s (début du combat : son IA n'a pas encore pu lancer la sienne), la première vague
 * sort tout de suite. Ce coup-là porte encore.
 *
 * <p>Filtre de dégâts, après celui des camps (un coup déjà annulé reste annulé).
 */
public final class PumpkinShieldSystem extends DamageEventSystem {

    public static final String ROLE = "Nakasar_Giant_Pumpkin";
    private static final double FIRST_WAVE_SECONDS = 20;
    private static final long WARN_SECONDS = 4;

    private static final Set<Dependency<EntityStore>> DEPENDENCIES =
            Set.of(new SystemDependency<>(Order.AFTER, AllegianceDamageFilter.class));

    /** Dernier avertissement par joueur (System.nanoTime). */
    private static final Map<UUID, Long> WARNED = new ConcurrentHashMap<>();

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return DamageModule.get().getFilterDamageGroup();
    }

    @Override
    public Set<Dependency<EntityStore>> getDependencies() {
        return DEPENDENCIES;
    }

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        if (damage.isCancelled()) {
            return;
        }
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        if (npc == null || !ROLE.equals(npc.getRoleName())) {
            return;
        }
        Ref<EntityStore> pumpkin = chunk.getReferenceTo(index);
        if (SummonVinesInteraction.hasLivingVines(pumpkin, store)) {
            damage.setCancelled(true);
            warn(damage, buffer);
            return;
        }
        TransformComponent transform = chunk.getComponent(index, TransformComponent.getComponentType());
        if (transform != null) {
            SummonVinesInteraction.summonWave(store.getExternalData().getWorld(), pumpkin, transform.getPosition(),
                    FIRST_WAVE_SECONDS);
        }
    }

    private static void warn(Damage damage, CommandBuffer<EntityStore> buffer) {
        if (!(damage.getSource() instanceof Damage.EntitySource source) || source.getRef() == null || !source.getRef().isValid()) {
            return;
        }
        PlayerRef player = buffer.getComponent(source.getRef(), PlayerRef.getComponentType());
        if (player == null) {
            return;
        }
        long now = System.nanoTime();
        Long last = WARNED.get(player.getUuid());
        if (last == null || now - last > WARN_SECONDS * 1_000_000_000L) {
            WARNED.put(player.getUuid(), now);
            player.sendMessage(Message.translation("nakasar_mobs.npc.Giant_Pumpkin.shielded"));
        }
    }

    public static void clearAll() {
        WARNED.clear();
    }
}
