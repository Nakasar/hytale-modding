package dev.nakasar.hytale.vampires.elite;

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
import com.hypixel.hytale.server.npc.role.support.StateSupport;
import dev.nakasar.hytale.vampires.allegiance.AllegianceDamageFilter;
import org.joml.Vector3d;

import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Bouclier des élites qui se cachent derrière leurs serviteurs ({@link #SHIELDS}) : tant qu'un de leurs serviteurs
 * ({@link SummonMinionsInteraction}) est vivant, aucun coup ne les blesse ; le joueur qui frappe est prévenu (au plus
 * une fois toutes les {@value #WARN_SECONDS} s). Il faut détruire la vague pour les atteindre, jusqu'à la suivante.
 * <ul>
 *   <li>citrouille géante : ses vrilles combattantes (son IA fait sortir la vague suivante 10 à 12 s après) ;</li>
 *   <li>Spectre : ses fantômes invoqués.</li>
 * </ul>
 *
 * <p>Seuls les coups d'une entité (arme, projectile, effet qu'elle a posé) sont bloqués : le vide, l'environnement et
 * les commandes les blessent toujours.
 *
 * <p>Première vague (citrouille seulement, qui ne bouge pas et peut être frappée avant d'avoir vu qui que ce soit) :
 * si une entité à moins de {@value #LEASH} blocs (sa laisse) la frappe alors qu'aucune vague n'est encore sortie
 * depuis son dernier retour au calme, la vague sort tout de suite. Ce coup-là porte encore. Une fois le combat lancé,
 * seule son IA invoque les vagues suivantes : le répit après chaque vague détruite est garanti.
 *
 * <p>Filtre de dégâts, après celui des camps (un coup déjà annulé reste annulé).
 */
public final class MinionShieldSystem extends DamageEventSystem {

    /** Message d'avertissement et vague du premier coup (null : seule l'IA invoque), par rôle protégé. */
    private record Shield(String warnKey, SummonMinionsInteraction firstWave) {
    }

    /** Élites protégées par leurs serviteurs. La vague du premier coup reprend Nakasar_NPC_Pumpkin_Summon. */
    static final Map<String, Shield> SHIELDS = Map.of(
            "Nakasar_Giant_Pumpkin", new Shield("nakasar_mobs.npc.Giant_Pumpkin.shielded",
                    SummonMinionsInteraction.preset("Nakasar_Pumpkin_Vine", 5, 5, 3f, 7f, 2.5f)),
            "Nakasar_Spectre", new Shield("nakasar_mobs.npc.Spectre.shielded", null));

    private static final double LEASH = 20;
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
        Shield shield = npc == null ? null : SHIELDS.get(npc.getRoleName());
        if (shield == null) {
            return;
        }
        if (!(damage.getSource() instanceof Damage.EntitySource source)) {
            return;
        }
        Ref<EntityStore> elite = chunk.getReferenceTo(index);
        if (SummonMinionsInteraction.hasLivingMinions(elite, store)) {
            damage.setCancelled(true);
            warn(source, buffer, shield.warnKey());
            return;
        }
        if (shield.firstWave() == null) {
            return;
        }
        StateSupport state = StateSupport.get(elite, store);
        String name = state == null ? null : state.getStateName();
        if (name == null || !name.startsWith("Combat")) {
            // Au calme : le prochain combat repart de zéro.
            SummonMinionsInteraction.forgetCalls(elite);
        }
        TransformComponent transform = chunk.getComponent(index, TransformComponent.getComponentType());
        if (transform != null && inLeash(source, buffer, transform.getPosition())) {
            SummonMinionsInteraction.summonFirstWave(shield.firstWave(), store.getExternalData().getWorld(), elite, transform.getPosition());
        }
    }

    private static boolean inLeash(Damage.EntitySource source, CommandBuffer<EntityStore> buffer, Vector3d at) {
        Ref<EntityStore> attacker = source.getRef();
        if (attacker == null || !attacker.isValid()) {
            return false;
        }
        TransformComponent transform = buffer.getComponent(attacker, TransformComponent.getComponentType());
        return transform != null && transform.getPosition().distanceSquared(at) <= LEASH * LEASH;
    }

    private static void warn(Damage.EntitySource source, CommandBuffer<EntityStore> buffer, String key) {
        if (source.getRef() == null || !source.getRef().isValid()) {
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
            player.sendMessage(Message.translation(key));
        }
    }

    public static void clearAll() {
        WARNED.clear();
    }
}
