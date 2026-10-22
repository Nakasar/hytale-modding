package dev.nakasar.hytale.fractals.minions;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.modules.entity.component.Invulnerable;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.StateSupport;
import org.joml.Vector3d;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Bouclier des boss qui se cachent derrière leurs serviteurs ({@link #register}) : tant qu'un de leurs serviteurs
 * ({@link SummonMinionsInteraction}) est vivant, aucun coup ne les blesse. Il faut détruire la vague pour les
 * atteindre, jusqu'à la suivante (transitions de l'Archidevin, par exemple). Copie du mod Vampires (citrouille géante,
 * Spectre).
 *
 * <p>Comme les boss du donjon Deepworks, l'élite protégée porte le composant vanilla {@link Invulnerable} pendant ce
 * temps (posé et retiré par {@link SummonMinionsInteraction}) : sa barre de boss passe en mode invulnérable et, comme
 * pour eux, plus aucun dégât ne la touche (vide et environnement compris). Aucun message n'explique quoi faire : les
 * joueurs le découvrent. Ce filtre annule en plus les coups d'entité tant que la vague vit, au cas où le composant
 * serait posé un instant trop tard, et lève une invulnérabilité restée sans vague vivante.
 *
 * <p>Première vague : si une entité à moins de {@value #LEASH} blocs frappe l'élite alors qu'aucune vague n'est encore
 * sortie depuis son dernier retour au calme, la vague sort tout de suite (la citrouille ne bouge pas et peut être
 * frappée avant d'avoir vu qui que ce soit). Ce coup-là porte
 * encore. Une fois le combat lancé, seule l'IA invoque les vagues suivantes : le répit après chaque vague détruite
 * est garanti.
 *
 * <p>Filtre de dégâts (un coup déjà annulé reste annulé).
 */
public final class MinionShieldSystem extends DamageEventSystem {

    /**
     * Boss protégés par leurs serviteurs, avec la vague du premier coup (même réglage que leur interaction
     * d'invocation). Rempli par le plugin, fractale par fractale.
     */
    static final Map<String, SummonMinionsInteraction> SHIELDS = new ConcurrentHashMap<>();

    private static final double LEASH = 20;

    /** Protège le rôle `role` par ses serviteurs ; `firstWave` sort dès le premier coup reçu au calme. */
    public static void register(String role, SummonMinionsInteraction firstWave) {
        SHIELDS.put(role, firstWave);
    }

    /** Vrai si l'entité est un boss protégé par ses serviteurs. */
    static boolean isShielded(Ref<EntityStore> ref, ComponentAccessor<EntityStore> accessor) {
        NPCEntity npc = accessor.getComponent(ref, NPCEntity.getComponentType());
        return npc != null && SHIELDS.containsKey(npc.getRoleName());
    }

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return DamageModule.get().getFilterDamageGroup();
    }

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        NPCEntity npc = chunk.getComponent(index, NPCEntity.getComponentType());
        SummonMinionsInteraction firstWave = npc == null ? null : SHIELDS.get(npc.getRoleName());
        if (firstWave == null) {
            return;
        }
        Ref<EntityStore> elite = chunk.getReferenceTo(index);
        boolean shielded = SummonMinionsInteraction.hasLivingMinions(elite, store);
        if (!shielded && chunk.getArchetype().contains(Invulnerable.getComponentType())) {
            // Invulnérabilité orpheline (sauvegarde en plein combat, plugin rechargé…) : sans vague vivante, on la
            // lève. Ce coup-ci a déjà pu être annulé par le filtre vanilla ; le suivant porte.
            buffer.tryRemoveComponent(elite, Invulnerable.getComponentType());
        }
        if (damage.isCancelled()) {
            return;
        }
        if (!(damage.getSource() instanceof Damage.EntitySource source)) {
            return;
        }
        if (shielded) {
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
