package dev.nakasar.hytale.fractals.snowblind;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.fractals.arena.Carried;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import org.joml.Vector3d;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Hypothermie, la règle de la Tempête de neige : loin d'un feu allumé, chaque joueur prend une pile toutes les
 * {@value #GAIN_EVERY} s ({@value #BLIZZARD_GAIN} s dans le blizzard, deux fois moins vite torche en main), jusqu'à
 * {@value #MAX}. Près d'un feu (Chaleur), il en perd une toutes les {@value #WARM_EVERY} s. Chaque seconde, le froid
 * retire {@value #PART_PER_STACK} des PV max par pile (cause {@code Nakasar_Fractal_Cold}). Au maximum, le joueur est
 * pris dans un éclat de glace que ses alliés doivent briser ; libéré, il garde {@value #FREED_STACKS} piles.
 */
final class Frost {

    static final int MAX = 10;
    static final float GAIN_EVERY = 5f;
    static final float BLIZZARD_GAIN = 2.5f;
    static final float TORCH_SLOWDOWN = 2f;
    static final float WARM_EVERY = 1.2f;
    static final float PART_PER_STACK = 0.003f;
    static final int FREED_STACKS = 6;
    static final String WARMTH = "Nakasar_Fractal_Warmth";
    static final String ENCASED = "Nakasar_Fractal_Encased";
    static final String TIER = "Nakasar_Fractal_Hypothermia_";
    static final String COLD = "Nakasar_Fractal_Cold";

    /** Une source de chaleur : feu de camp, foyer ou feu du village allumé. */
    record Heat(Vector3d at, double radius) {
    }

    private static final class Chill {
        int stacks;
        float gain;
        float warm;
        float tick;
        int tier;
        Ref<EntityStore> shard;
    }

    private final Map<UUID, Chill> chills = new HashMap<>();
    /** Éclat de glace → joueur qu'il enferme. */
    private final Map<Ref<EntityStore>, Ref<EntityStore>> prisoners = new HashMap<>();

    int stacks(PlayerRef player) {
        Chill c = chills.get(player.getUuid());
        return c == null ? 0 : c.stacks;
    }

    /** Ajoute `n` piles (coups d'épée du Chaman, pics du balcon). */
    void add(UUID player, int n) {
        Chill c = chills.computeIfAbsent(player, u -> new Chill());
        c.stacks = Math.min(MAX, c.stacks + n);
    }

    static boolean warm(Vector3d at, List<Heat> heats) {
        for (Heat h : heats) {
            if (Telegraphs.horizontal(at, h.at()) <= h.radius() && Math.abs(at.y() - h.at().y()) < 4) {
                return true;
            }
        }
        return false;
    }

    void step(World world, Store<EntityStore> store, List<PlayerRef> players, List<Heat> heats, boolean blizzard, float dt) {
        Set<UUID> alive = new HashSet<>();
        for (PlayerRef player : players) {
            alive.add(player.getUuid());
            Ref<EntityStore> ref = player.getReference();
            Vector3d at = Telegraphs.position(store, ref);
            if (at == null) {
                continue;
            }
            Chill c = chills.computeIfAbsent(player.getUuid(), u -> new Chill());
            if (c.shard != null) {
                encased(store, player, c);
                continue;
            }
            if (warm(at, heats)) {
                c.gain = 0f;
                c.warm += dt;
                if (c.warm >= WARM_EVERY && c.stacks > 0) {
                    c.warm = 0f;
                    c.stacks--;
                }
                if (c.tick == 0f) {
                    Hurt.effect(store, ref, WARMTH, 1.5f);
                }
            } else {
                c.warm = 0f;
                float every = (blizzard ? BLIZZARD_GAIN : GAIN_EVERY)
                        * (Carried.holds(store, ref, Snowblind.TORCH) ? TORCH_SLOWDOWN : 1f);
                c.gain += dt;
                if (c.gain >= every) {
                    c.gain = 0f;
                    c.stacks = Math.min(MAX, c.stacks + 1);
                }
            }
            if (c.stacks >= MAX) {
                encase(world, store, player, c, at);
                continue;
            }
            c.tick += dt;
            if (c.tick >= 1f) {
                c.tick = 0f;
                if (c.stacks > 0) {
                    Hurt.percent(store, ref, PART_PER_STACK * c.stacks, COLD);
                }
            }
            tier(store, ref, c, (c.stacks + 1) / 2);
        }
        // Morts ou partis : piles oubliées, éclat retiré.
        chills.entrySet().removeIf(e -> {
            if (alive.contains(e.getKey())) {
                return false;
            }
            if (e.getValue().shard != null) {
                prisoners.remove(e.getValue().shard);
                Spawns.remove(store, e.getValue().shard);
            }
            return true;
        });
    }

    /** Pose l'effet du palier (piles 1-2 : palier 1… 9-10 : palier 5), rafraîchi chaque seconde. */
    private static void tier(Store<EntityStore> store, Ref<EntityStore> ref, Chill c, int tier) {
        if (tier != c.tier && c.tier > 0) {
            Hurt.clear(store, ref, TIER + c.tier);
        }
        if (tier > 0 && (tier != c.tier || c.tick == 0f)) {
            Hurt.effect(store, ref, TIER + tier, 1.5f);
        }
        c.tier = tier;
    }

    private void encase(World world, Store<EntityStore> store, PlayerRef player, Chill c, Vector3d at) {
        Ref<EntityStore> ref = player.getReference();
        Ref<EntityStore> shard = Spawns.spawnFoe(world, store, Snowblind.SHARD, new Vector3d(at), 0f);
        if (shard == null) {
            c.stacks = MAX - 1;
            return;
        }
        c.shard = shard;
        prisoners.put(shard, ref);
        tier(store, ref, c, 0);
        Hurt.effect(store, ref, ENCASED, 1.5f);
        Telegraphs.particle(store, "Impact_Ice", at, 1.5f);
        Telegraphs.sound(store, "SFX_Ice_Break", at);
        player.sendMessage(Message.translation(Snowblind.MESSAGES + "cold.encased"));
        for (PlayerRef other : world.getPlayerRefs()) {
            if (!other.getUuid().equals(player.getUuid())) {
                other.sendMessage(Message.translation(Snowblind.MESSAGES + "cold.ally").param("name", player.getUsername()));
            }
        }
    }

    /** Pris dans la glace : immobile tant que l'éclat tient ; brisé, le joueur repart avec {@value #FREED_STACKS} piles. */
    private void encased(Store<EntityStore> store, PlayerRef player, Chill c) {
        Ref<EntityStore> ref = player.getReference();
        if (Spawns.alive(store, c.shard)) {
            Hurt.effect(store, ref, ENCASED, 1.5f);
            return;
        }
        prisoners.remove(c.shard);
        c.shard = null;
        c.stacks = FREED_STACKS;
        c.gain = 0f;
        c.tick = 0f;
        Hurt.clear(store, ref, ENCASED);
        Vector3d at = Telegraphs.position(store, ref);
        if (at != null) {
            Telegraphs.particle(store, "Nakasar_Fractal_Shard_Break", at, 1.2f);
        }
        player.sendMessage(Message.translation(Snowblind.MESSAGES + "cold.freed"));
    }

    /** Le joueur enfermé par cet éclat (null si ce n'est pas un éclat suivi). */
    Ref<EntityStore> prisoner(Ref<EntityStore> shard) {
        return prisoners.get(shard);
    }
}
