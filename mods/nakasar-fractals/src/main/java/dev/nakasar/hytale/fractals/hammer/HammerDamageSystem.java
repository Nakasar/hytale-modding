package dev.nakasar.hytale.fractals.hammer;

import dev.nakasar.hytale.fractals.FractalsPlugin;
import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.protocol.packets.interface_.NotificationStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.combat.Foes;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Charge Brise-sceau du marteau du culte ({@link Hammer}) : un ennemi des fractales ({@link Foes}) frappé avec le
 * marteau en main charge le marteau ; à sa mort, un ennemi charge aussi le porteur qui l'a frappé dans les
 * {@value Hammer#CREDIT_SECONDS} s (même s'il meurt d'une chute, loin de lui) et les porteurs à moins de
 * {@value Hammer#CHARGE_RADIUS} blocs. Les sceaux ne comptent pas (leurs coups sont annulés avant).
 *
 * <p>Groupe d'inspection : il passe après {@code DamageSystems.ApplyDamage}, la vie lue est donc déjà diminuée du coup.
 */
public final class HammerDamageSystem extends DamageEventSystem {

    private static final String SEAL_ROLE = "Nakasar_Fractal_Seal";
    /** Dernier porteur du marteau à avoir frappé chaque ennemi, et quand (System.nanoTime). */
    private static final Map<Ref<EntityStore>, Credit> CREDITS = Collections.synchronizedMap(new WeakHashMap<>());

    private record Credit(PlayerRef player, long at) {
    }

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return DamageModule.get().getInspectDamageGroup();
    }

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        if (damage.isCancelled() || damage.getAmount() <= 0f || Hammer.CARRIERS.isEmpty()) {
            return;
        }
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        Ref<EntityStore> victim = chunk.getReferenceTo(index);
        if (npc == null || SEAL_ROLE.equals(npc.getRoleName()) || !Foes.inGroup(victim, buffer)) {
            return;
        }
        if (damage.getSource() instanceof Damage.EntitySource source && source.getRef() != null && source.getRef().isValid()) {
            PlayerRef attacker = buffer.getComponent(source.getRef(), PlayerRef.getComponentType());
            Hammer.Carrier carrier = attacker == null ? null : Hammer.CARRIERS.get(attacker.getUuid());
            if (carrier != null && carrier.carrying) {
                CREDITS.put(victim, new Credit(attacker, System.nanoTime()));
                if (Hammer.holds(buffer, source.getRef())) {
                    charge(attacker);
                }
            }
        }
        EntityStatMap stats = chunk.getComponent(index, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        TransformComponent transform = chunk.getComponent(index, TransformComponent.getComponentType());
        if (health == null || transform == null || health.get() > health.getMin()) {
            return;
        }
        Credit credit = CREDITS.remove(victim);
        FractalsPlugin.get().getLogger().atInfo().log("Nakasar_Fractal_Hammer : mort de %s (crédit %s)", npc.getRoleName(),
                credit == null ? "aucun" : credit.player().getUsername());
        if (credit != null && System.nanoTime() - credit.at() <= Telegraphs.seconds(Hammer.CREDIT_SECONDS)) {
            charge(credit.player());
        }
        Vector3d at = new Vector3d(transform.getPosition());
        World world = store.getExternalData().getWorld();
        for (PlayerRef player : world.getPlayerRefs()) {
            Hammer.Carrier carrier = Hammer.CARRIERS.get(player.getUuid());
            Vector3d where = carrier == null || !carrier.carrying ? null : Telegraphs.position(buffer, player.getReference());
            if (where != null && where.distance(at) <= Hammer.CHARGE_RADIUS) {
                charge(player);
            }
        }
    }

    private static void charge(PlayerRef player) {
        Hammer.Carrier carrier = Hammer.CARRIERS.get(player.getUuid());
        if (carrier == null || !carrier.carrying || carrier.charged) {
            return;
        }
        carrier.charged = true;
        FractalsPlugin.get().getLogger().atInfo().log("Nakasar_Fractal_Hammer : %s chargé", player.getUsername());
        // Bandeau en plus du chat : on ne doit pas pouvoir rater la charge.
        NotificationUtil.sendNotification(player.getPacketHandler(), Message.translation("nakasar_fractals_cliffside.hammer.charged"),
                NotificationStyle.Default);
    }
}
