package dev.nakasar.hytale.fractals.support;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.SystemGroup;
import com.hypixel.hytale.component.query.Query;
import com.hypixel.hytale.server.core.inventory.InventoryComponent;
import com.hypixel.hytale.server.core.inventory.ItemStack;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageEventSystem;
import com.hypixel.hytale.server.core.modules.entity.damage.DamageModule;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Effets au coup des trois armes de soutien (attaque principale vanilla de leur arme de base) :
 * <ul>
 *   <li>Bâton de guérison des Brumes : chaque coup soigne de {@value #STAFF_HEAL} PV le joueur le plus blessé à
 *   {@value #STAFF_RADIUS} blocs du porteur (lui compris), au plus toutes les {@value #STAFF_EVERY} s ;</li>
 *   <li>Grimoire de givre des Brumes : chaque coup ajoute une pile de lenteur ({@value #GRIMOIRE_STACK} par pile,
 *   {@value #GRIMOIRE_MAX} piles, {@value #GRIMOIRE_SECONDS} s) ;</li>
 *   <li>Baguette des racines des Brumes : un coup enracine {@value #WAND_ROOT} s, une fois toutes les
 *   {@value #WAND_EVERY} s par cible (un boss ne prend que la défiance du coup lui-même).</li>
 * </ul>
 */
public final class SupportHitSystem extends DamageEventSystem {

    public static final String STAFF = "Weapon_Nakasar_Fractal_Mending_Staff";
    public static final String GRIMOIRE = "Weapon_Nakasar_Fractal_Frost_Grimoire";
    public static final String WAND = "Weapon_Nakasar_Fractal_Root_Wand";

    static final float STAFF_HEAL = 6f;
    static final double STAFF_RADIUS = 8;
    static final float STAFF_EVERY = 0.5f;
    static final float GRIMOIRE_STACK = 0.10f;
    static final int GRIMOIRE_MAX = 5;
    static final float GRIMOIRE_SECONDS = 4f;
    static final float WAND_ROOT = 2f;
    static final float WAND_EVERY = 8f;

    private static final Map<UUID, Long> STAFF_NEXT = new ConcurrentHashMap<>();
    private static final Map<Ref<EntityStore>, long[]> FROST = new ConcurrentHashMap<>();
    private static final Map<Ref<EntityStore>, Long> ROOT_NEXT = new ConcurrentHashMap<>();

    @Override
    public SystemGroup<EntityStore> getGroup() {
        return DamageModule.get().getInspectDamageGroup();
    }

    @Override
    public Query<EntityStore> getQuery() {
        return NPCEntity.getComponentType();
    }

    @Override
    @SuppressWarnings("deprecation")
    public void handle(int index, ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store,
                       CommandBuffer<EntityStore> buffer, Damage damage) {
        if (damage.isCancelled() || damage.getAmount() <= 0f || !(damage.getSource() instanceof Damage.EntitySource source)) {
            return;
        }
        if (damage.getCause() != null && Support.CAUSE.equals(damage.getCause().getId())) {
            return;
        }
        Ref<EntityStore> attacker = source.getRef();
        PlayerRef player = attacker == null || !attacker.isValid() ? null
                : buffer.getComponent(attacker, PlayerRef.getComponentType());
        ItemStack held = player == null ? null : InventoryComponent.getItemInHand(buffer, attacker);
        String id = held == null ? null : held.getItemId();
        if (id == null || !(STAFF.equals(id) || GRIMOIRE.equals(id) || WAND.equals(id))) {
            return;
        }
        Ref<EntityStore> victim = chunk.getReferenceTo(index);
        World world = store.getExternalData().getWorld();
        long now = System.nanoTime();
        if (STAFF.equals(id)) {
            Long next = STAFF_NEXT.get(player.getUuid());
            if (next != null && now < next) {
                return;
            }
            STAFF_NEXT.put(player.getUuid(), now + Telegraphs.seconds(STAFF_EVERY));
            world.execute(() -> mend(world, attacker));
        } else if (GRIMOIRE.equals(id)) {
            long[] stack = FROST.compute(victim, (r, old) ->
                    old == null || now >= old[1] ? new long[]{1, 0} : new long[]{Math.min(GRIMOIRE_MAX, old[0] + 1), 0});
            stack[1] = now + Telegraphs.seconds(GRIMOIRE_SECONDS);
            float part = GRIMOIRE_STACK * stack[0];
            world.execute(() -> {
                if (victim.isValid()) {
                    Skills.slowFoe(world.getEntityStore().getStore(), victim, "Grimoire", part, GRIMOIRE_SECONDS);
                }
            });
        } else {
            Long next = ROOT_NEXT.get(victim);
            if (next != null && now < next) {
                return;
            }
            ROOT_NEXT.put(victim, now + Telegraphs.seconds(WAND_EVERY));
            world.execute(() -> {
                Store<EntityStore> s = world.getEntityStore().getStore();
                if (victim.isValid() && !Support.immune(s, victim)) {
                    Support.stun(world, s, victim, WAND_ROOT, 0);
                    Vector3d at = Telegraphs.position(s, victim);
                    if (at != null) {
                        Telegraphs.particle(s, Skills.FX_ROOTS, at, 1f);
                    }
                }
            });
        }
        if (FROST.size() + ROOT_NEXT.size() > 512) {
            FROST.keySet().removeIf(r -> !r.isValid());
            ROOT_NEXT.keySet().removeIf(r -> !r.isValid());
        }
    }

    /** Soigne le joueur le plus blessé (en part de sa vie) près du porteur du bâton. */
    private static void mend(World world, Ref<EntityStore> holder) {
        Store<EntityStore> store = world.getEntityStore().getStore();
        Vector3d at = Telegraphs.position(store, holder);
        if (at == null) {
            return;
        }
        Ref<EntityStore> best = null;
        float lowest = 1f;
        for (Ref<EntityStore> p : Support.playersNear(world, store, at, STAFF_RADIUS)) {
            EntityStatMap stats = store.getComponent(p, EntityStatMap.getComponentType());
            EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
            if (health != null && health.getMax() > 0 && health.get() / health.getMax() < lowest) {
                lowest = health.get() / health.getMax();
                best = p;
            }
        }
        if (best != null) {
            Support.heal(store, best, STAFF_HEAL);
            Vector3d p = Telegraphs.position(store, best);
            Telegraphs.particle(store, Skills.FX_HEAL, new Vector3d(p).add(0, 1, 0), 0.8f);
        }
    }

    public static void clearAll() {
        STAFF_NEXT.clear();
        FROST.clear();
        ROOT_NEXT.clear();
    }
}
