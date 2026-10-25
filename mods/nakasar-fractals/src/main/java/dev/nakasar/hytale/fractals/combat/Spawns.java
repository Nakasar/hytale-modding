package dev.nakasar.hytale.fractals.combat;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.RemoveReason;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.math.vector.Rotation3f;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.npc.INonPlayerCharacter;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.NPCPlugin;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.FractalsPlugin;
import dev.nakasar.hytale.fractals.arena.Box;
import dev.nakasar.hytale.fractals.boss.GroupHealth;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import it.unimi.dsi.fastutil.Pair;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * Apparitions et outils communs aux déroulés des fractales (Falaise, Inclassable, Volcanique) : PNJ non sauvegardés,
 * vie des ennemis selon le groupe et le niveau, joueurs vivants, zones.
 */
public final class Spawns {

    public static final String SCALE_MODIFIER = "Nakasar_Fractal_Scale";
    public static final String BOSS_SCALE_MODIFIER = "Nakasar_Fractal_Boss_Scale";

    private Spawns() {
    }

    /** Pose le PNJ `role` (non sauvegardé), tourné de `yaw` ; null si le jeu refuse. */
    public static Ref<EntityStore> spawn(Store<EntityStore> store, String role, Vector3d at, float yaw) {
        Pair<Ref<EntityStore>, INonPlayerCharacter> spawned = NPCPlugin.get().spawnNPC(store, role, null, at, new Rotation3f(0f, yaw, 0f));
        if (spawned == null || spawned.first() == null) {
            FractalsPlugin.get().getLogger().atWarning().log("Fractale : impossible de faire apparaître '%s'", role);
            return null;
        }
        store.ensureAndGetComponent(spawned.first(), EntityStore.REGISTRY.getNonSerializedComponentType());
        return spawned.first();
    }

    /** Multiplicateur de vie d'un ennemi : × (1 + 25 % par joueur de plus) × (1 + niveau / 100). */
    public static float foeScale(World world) {
        return (1f + 0.25f * (FractalRuns.partySize(world) - 1)) * (1f + FractalRuns.level(world) / 100f);
    }

    /** Multiplicateur de vie d'un boss : {@link GroupHealth} × (1 + niveau / 100). */
    public static float bossScale(World world) {
        return GroupHealth.multiplier(FractalRuns.partySize(world)) * (1f + FractalRuns.level(world) / 100f);
    }

    /** Un ennemi des fractales en `at` (léger décalage au hasard), non sauvegardé, vie selon le groupe et le niveau. */
    public static Ref<EntityStore> spawnFoe(World world, Store<EntityStore> store, String role, double[] at) {
        ThreadLocalRandom random = ThreadLocalRandom.current();
        Vector3d where = new Vector3d(at[0] + random.nextDouble(-0.8, 0.8), at[1], at[2] + random.nextDouble(-0.8, 0.8));
        return spawnFoe(world, store, role, where, (float) random.nextDouble(-Math.PI, Math.PI));
    }

    public static Ref<EntityStore> spawnFoe(World world, Store<EntityStore> store, String role, Vector3d at, float yaw) {
        Ref<EntityStore> ref = spawn(store, role, at, yaw);
        if (ref != null) {
            GroupHealth.apply(store.getComponent(ref, EntityStatMap.getComponentType()), SCALE_MODIFIER, foeScale(world));
        }
        return ref;
    }

    /** Un boss : vie {@link #bossScale}. */
    public static Ref<EntityStore> spawnBoss(World world, Store<EntityStore> store, String role, Vector3d at, float yaw) {
        Ref<EntityStore> ref = spawn(store, role, at, yaw);
        if (ref != null) {
            GroupHealth.apply(store.getComponent(ref, EntityStatMap.getComponentType()), BOSS_SCALE_MODIFIER, bossScale(world));
        }
        return ref;
    }

    /**
     * Un ennemi qui revient en boucle (vagues, renforts réguliers) ne laisse pas tomber la liste de butin de son rôle :
     * seuls les ennemis présents de base ou apparus sur un événement en ont une (Kevin, 25 octobre 2026). Le rôle croit
     * avoir déjà lâché son butin ({@code NPCDamageSystems.DropDeathItems} ne le tire alors pas).
     */
    public static Ref<EntityStore> noLoot(Store<EntityStore> store, Ref<EntityStore> ref) {
        NPCEntity npc = ref == null || !ref.isValid() ? null : store.getComponent(ref, NPCEntity.getComponentType());
        if (npc != null && npc.getRole() != null) {
            npc.getRole().setDeathItemsDropped();
        }
        return ref;
    }

    public static Vector3d point(double[] at) {
        return new Vector3d(at[0], at[1], at[2]);
    }

    public static List<PlayerRef> alivePlayers(World world, Store<EntityStore> store) {
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef player : world.getPlayerRefs()) {
            Ref<EntityStore> ref = player.getReference();
            if (ref != null && ref.isValid() && store.getComponent(ref, DeathComponent.getComponentType()) == null) {
                out.add(player);
            }
        }
        return out;
    }

    public static boolean alive(Store<EntityStore> store, Ref<EntityStore> ref) {
        return Telegraphs.position(store, ref) != null;
    }

    public static String role(Store<EntityStore> store, Ref<EntityStore> ref) {
        NPCEntity npc = ref == null || !ref.isValid() ? null : store.getComponent(ref, NPCEntity.getComponentType());
        return npc == null ? null : npc.getRoleName();
    }

    public static void remove(Store<EntityStore> store, Ref<EntityStore> ref) {
        if (ref != null && ref.isValid()) {
            store.removeEntity(ref, RemoveReason.REMOVE);
        }
    }

    public static void removeAll(Store<EntityStore> store, Collection<Ref<EntityStore>> refs) {
        for (Ref<EntityStore> ref : refs) {
            remove(store, ref);
        }
        refs.clear();
    }

    public static boolean anyIn(Store<EntityStore> store, List<PlayerRef> players, Box box) {
        return !in(store, players, box).isEmpty();
    }

    /** Joueurs dont les pieds sont dans `box`. */
    public static List<PlayerRef> in(Store<EntityStore> store, List<PlayerRef> players, Box box) {
        List<PlayerRef> out = new ArrayList<>();
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null && box.contains(at.x(), at.y(), at.z())) {
                out.add(player);
            }
        }
        return out;
    }

    public static double nearest(Store<EntityStore> store, List<PlayerRef> players, Vector3d where) {
        double best = Double.MAX_VALUE;
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null) {
                best = Math.min(best, at.distance(where));
            }
        }
        return best;
    }

    /** Joueur vivant le plus proche de `where` (null s'il n'y en a pas). */
    public static PlayerRef nearestPlayer(Store<EntityStore> store, List<PlayerRef> players, Vector3d where) {
        PlayerRef best = null;
        double bestDistance = Double.MAX_VALUE;
        for (PlayerRef player : players) {
            Vector3d at = Telegraphs.position(store, player.getReference());
            if (at != null && at.distance(where) < bestDistance) {
                bestDistance = at.distance(where);
                best = player;
            }
        }
        return best;
    }

    /** `count` joueurs au hasard parmi `players`. */
    public static List<PlayerRef> pick(List<PlayerRef> players, int count) {
        List<PlayerRef> copy = new ArrayList<>(players);
        Collections.shuffle(copy);
        return copy.subList(0, Math.min(count, copy.size()));
    }

    public static void tellAll(World world, Message message) {
        for (PlayerRef player : world.getPlayerRefs()) {
            player.sendMessage(message);
        }
    }
}
