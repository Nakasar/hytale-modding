package dev.nakasar.hytale.vampires.elite;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.dependency.Dependency;
import com.hypixel.hytale.component.dependency.Order;
import com.hypixel.hytale.component.dependency.SystemDependency;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.StateSupport;
import dev.nakasar.hytale.vampires.allegiance.AllegianceDamageFilter;
import org.joml.Vector3d;

import java.util.Map;
import java.util.Set;

/**
 * Bouclier des élites qui se cachent derrière leurs serviteurs ({@link #SHIELDS}) : tant qu'un de leurs serviteurs
 * ({@link SummonMinionsInteraction}) est vivant, aucun coup ne les blesse. Il faut détruire la vague pour les
 * atteindre, jusqu'à la suivante.
 * <ul>
 *   <li>citrouille géante : ses vrilles combattantes (son IA fait sortir la vague suivante 10 à 12 s après) ;</li>
 *   <li>Spectre : ses fantômes invoqués.</li>
 * </ul>
 *
 * <p>Comme les boss du donjon Deepworks, l'élite protégée porte le composant vanilla {@link Invulnerable} pendant ce
 * temps (posé et retiré par {@link SummonMinionsInteraction}) : sa barre de boss passe en mode invulnérable. Aucun
 * message n'explique quoi faire : les joueurs le découvrent. Ce filtre annule en plus les coups d'entité tant que
 * la vague vit, au cas où le composant serait posé un instant trop tard.
 *
 * <p>Première vague : si une entité à moins de {@value #LEASH} blocs frappe l'élite alors qu'aucune vague n'est encore
 * sortie depuis son dernier retour au calme, la vague sort tout de suite (la citrouille ne bouge pas et peut être
 * frappée avant d'avoir vu qui que ce soit ; le Spectre ne doit jamais se battre sans ses fantômes). Ce coup-là porte
 * encore. Une fois le combat lancé, seule l'IA invoque les vagues suivantes : le répit après chaque vague détruite
 * est garanti.
 *
 * <p>Filtre de dégâts, après celui des camps (un coup déjà annulé reste annulé).
 */
public final class MinionShieldSystem extends DamageEventSystem {

    /**
     * Élites protégées par leurs serviteurs, avec la vague du premier coup (même réglage que leur interaction
     * d'invocation : Nakasar_NPC_Pumpkin_Summon, Nakasar_NPC_Spectre_Summon).
     */
    static final Map<String, SummonMinionsInteraction> SHIELDS = Map.of(
            "Nakasar_Giant_Pumpkin", SummonMinionsInteraction.preset("Nakasar_Pumpkin_Vine", 5, 5, 3f, 7f, 2.5f),
            "Nakasar_Spectre", SummonMinionsInteraction.preset("Nakasar_Spectral_Ghost", 3, 3, 2.5f, 5f, 2f));

    private static final double LEASH = 20;

    private static final Set<Dependency<EntityStore>> DEPENDENCIES =
            Set.of(new SystemDependency<>(Order.AFTER, AllegianceDamageFilter.class));

    /** Vrai si l'entité est une élite protégée par ses serviteurs. */
    static boolean isShielded(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        NPCEntity npc = accessor.getComponent(ref, NPCEntity.getComponentType());
        return npc != null && SHIELDS.containsKey(npc.getRoleName());
    }

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
        SummonMinionsInteraction firstWave = npc == null ? null : SHIELDS.get(npc.getRoleName());
        if (firstWave == null) {
            return;
        }
        if (!(damage.getSource() instanceof Damage.EntitySource source)) {
            return;
        }
        Ref<EntityStore> elite = chunk.getReferenceTo(index);
        if (SummonMinionsInteraction.hasLivingMinions(elite, store)) {
            damage.setCancelled(true);
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
            SummonMinionsInteraction.summonFirstWave(firstWave, store.getExternalData().getWorld(), elite, transform.getPosition());
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
}
