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
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.core.util.NotificationUtil;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.combat.Foes;
import dev.nakasar.hytale.fractals.combat.Telegraphs;

import java.util.Collections;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Charge Brise-sceau du marteau du culte ({@link Hammer}) : un ennemi des fractales ({@link Foes}) frappé avec le
 * marteau en main, qui meurt dans les {@value Hammer#CREDIT_SECONDS} s (même d'une chute, loin de lui), charge le
 * marteau de ce joueur. Rien d'autre ne charge (retour de Kevin du 2026-10-24 : ni le coup lui-même, ni une mort à
 * côté d'un porteur qui n'a pas frappé). Les sceaux ne comptent pas (leurs coups sont annulés avant).
 *
 * <p>Groupe d'inspection : il passe après {@code DamageSystems.ApplyDamage}, la vie lue est donc déjà diminuée du coup.
 */
public final class HammerDamageSystem extends DamageEventSystem {

    /** Préfixe des sceaux, intacts ou fissurés. */
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
        if (npc == null || npc.getRoleName() != null && npc.getRoleName().startsWith(SEAL_ROLE) || !Foes.inGroup(victim, buffer)) {
            return;
        }
        if (damage.getSource() instanceof Damage.EntitySource source && source.getRef() != null && source.getRef().isValid()) {
            PlayerRef attacker = buffer.getComponent(source.getRef(), PlayerRef.getComponentType());
            Hammer.Carrier carrier = attacker == null ? null : Hammer.CARRIERS.get(attacker.getUuid());
            if (carrier != null && carrier.carrying && Hammer.holds(buffer, source.getRef())) {
                CREDITS.put(victim, new Credit(attacker, System.nanoTime()));
            }
        }
        EntityStatMap stats = chunk.getComponent(index, EntityStatMap.getComponentType());
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health == null || health.get() > health.getMin()) {
            return;
        }
        Credit credit = CREDITS.remove(victim);
        FractalsPlugin.get().getLogger().atInfo().log("Nakasar_Fractal_Hammer : mort de %s (crédit %s)", npc.getRoleName(),
                credit == null ? "aucun" : credit.player().getUsername());
        if (credit != null && System.nanoTime() - credit.at() <= Telegraphs.seconds(Hammer.CREDIT_SECONDS)) {
            charge(credit.player());
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
