package dev.nakasar.hytale.fractals.instability;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.protocol.ChangeVelocityType;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.Damage;
import com.hypixel.hytale.server.core.modules.physics.component.Velocity;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import dev.nakasar.hytale.fractals.combat.Delayed;
import dev.nakasar.hytale.fractals.combat.Foes;
import dev.nakasar.hytale.fractals.combat.Hurt;
import dev.nakasar.hytale.fractals.combat.Spawns;
import dev.nakasar.hytale.fractals.combat.Telegraphs;
import dev.nakasar.hytale.fractals.observatory.Observatory;
import dev.nakasar.hytale.fractals.party.FractalRuns;
import org.joml.Vector3d;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.EnumSet;
import java.util.List;
import java.util.Random;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Le tirage quotidien des instabilités et leurs effets liés aux coups et aux morts (étape 5 du GDD). Les effets suivis
 * dans le temps (flaques, bombe de flux, nuées, malaise social) sont menés par {@link InstabilitySystem}.
 *
 * <p>Tirage : 0 instabilité en Initié, 1 en Adepte, 2 en Expert, 3 en Maître ; les mêmes pour tout le serveur, une
 * fois par jour et par fractale (graine = jour du serveur et fractale), les rangs hauts gardant celles des rangs bas.
 * Un joueur seul tire une autre instabilité à la place de celles qui demandent un groupe ; Malaise social et Restez
 * groupés ne tombent jamais ensemble.
 */
public final class Instabilities {

    public static final String CAUSE = "Nakasar_Fractal_Instability";
    public static final String VENGEANCE = "Nakasar_Fractal_Vengeance";
    public static final float LAST_LAUGH_RADIUS = 2.5f;
    public static final float LAST_LAUGH_SECONDS = 1.5f;
    public static final float LAST_LAUGH_PART = 0.20f;
    public static final double VENGEANCE_RADIUS = 10;
    public static final float VENGEANCE_SECONDS = 12f;
    public static final float VENGEANCE_FACTOR = 1.25f;
    public static final double TOGETHER_RADIUS = 6;
    public static final float TOGETHER_BONUS = 1.15f;
    public static final float ALONE_MALUS = 0.85f;
    public static final float SLIPPERY_PUSH = 8f;
    public static final float SLIPPERY_UP = 4.5f;

    /** Rôles qui ne comptent pas comme ennemis pour les instabilités (sceaux, tourelles, générateurs…). */
    private static final Set<String> EXEMPT = ConcurrentHashMap.newKeySet();

    private Instabilities() {
    }

    /** Ces rôles ne déclenchent ni Dernier rire ni Vengeance, et ne mettent pas « en combat » pour les nuées. */
    public static void exempt(String... roles) {
        EXEMPT.addAll(Arrays.asList(roles));
    }

    public static boolean isExempt(String role) {
        return role == null || EXEMPT.contains(role);
    }

    /** Nombre d'instabilités au niveau : une par rang au-delà d'Initié. */
    public static int count(int level) {
        return Math.min(3, Math.max(0, (Math.min(level, Observatory.MAX_LEVEL) - 1) / Observatory.RANK_SIZE));
    }

    /** Les instabilités du jour `day` pour `fractal` au niveau `level`, pour un groupe de `partySize`. */
    public static List<Instability> draw(String fractal, int level, int partySize, LocalDate day) {
        int count = count(level);
        if (count == 0) {
            return List.of();
        }
        List<Instability> order = new ArrayList<>(List.of(Instability.values()));
        Collections.shuffle(order, new Random(day.toEpochDay() * 31L + fractal.hashCode()));
        List<Instability> out = new ArrayList<>();
        for (Instability instability : order) {
            if (out.size() >= count) {
                break;
            }
            if (instability.groupOnly() && partySize <= 1) {
                continue;
            }
            boolean clash = (instability == Instability.SOCIAL_AWKWARDNESS && out.contains(Instability.STICK_TOGETHER))
                    || (instability == Instability.STICK_TOGETHER && out.contains(Instability.SOCIAL_AWKWARDNESS));
            if (!clash) {
                out.add(instability);
            }
        }
        return List.copyOf(out);
    }

    public static List<Instability> draw(String fractal, int level, int partySize) {
        return draw(fractal, level, partySize, LocalDate.now());
    }

    /** Instabilités de la partie jouée dans ce monde (aucune sans partie). */
    public static Set<Instability> of(World world) {
        FractalRuns.Run run = FractalRuns.of(world);
        return run == null || run.instabilities().isEmpty() ? Set.of() : EnumSet.copyOf(run.instabilities());
    }

    public static boolean active(World world, Instability instability) {
        FractalRuns.Run run = FractalRuns.of(world);
        return run != null && run.instabilities().contains(instability);
    }

    /** Liste à afficher : « aucune », ou une ligne par instabilité (nom en couleur, puis effet). */
    public static Message describe(List<Instability> list) {
        if (list.isEmpty()) {
            return Message.translation(Instability.LANG + "none");
        }
        Message out = Message.empty();
        for (int i = 0; i < list.size(); i++) {
            Instability instability = list.get(i);
            if (i > 0) {
                out.insert("\n");
            }
            out.insert(Message.raw("• ")).insert(instability.title().color("#e8a0ff").bold(true)).insert(Message.raw(" : "))
                    .insert(instability.description());
        }
        return out;
    }

    // --- coups -------------------------------------------------------------------------------------------

    /**
     * Coup dans une fractale (filtre commun, {@code stage.StageDamageFilter}) : Restez groupés, Vengeance, Pente
     * glissante.
     */
    public static void filter(World world, CommandBuffer<EntityStore> buffer, Ref<EntityStore> victim, boolean toPlayer,
                              Ref<EntityStore> attacker, boolean byPlayer, boolean byFoe, Damage damage) {
        FractalRuns.Run run = FractalRuns.of(world);
        if (run == null || run.instabilities().isEmpty() || attacker == null) {
            return;
        }
        List<Instability> active = run.instabilities();
        if (byPlayer && !toPlayer && active.contains(Instability.STICK_TOGETHER)) {
            damage.setAmount(damage.getAmount() * (hasAllyNear(world, buffer, attacker) ? TOGETHER_BONUS : ALONE_MALUS));
        }
        if (byFoe && active.contains(Instability.VENGEANCE) && Hurt.has(buffer, attacker, VENGEANCE)) {
            damage.setAmount(damage.getAmount() * VENGEANCE_FACTOR);
        }
        if (byFoe && toPlayer && active.contains(Instability.SLIPPERY_SLOPE)) {
            world.execute(() -> push(world.getEntityStore().getStore(), attacker, victim));
        }
    }

    static boolean hasAllyNear(World world, CommandBuffer<EntityStore> buffer, Ref<EntityStore> player) {
        Vector3d at = Telegraphs.position(buffer, player);
        if (at == null) {
            return false;
        }
        for (PlayerRef other : world.getPlayerRefs()) {
            Ref<EntityStore> ref = other.getReference();
            Vector3d there = ref == null || ref.equals(player) ? null : Telegraphs.position(buffer, ref);
            if (there != null && there.distance(at) <= TOGETHER_RADIUS) {
                return true;
            }
        }
        return false;
    }

    /** Pente glissante : le joueur touché part loin de l'ennemi qui l'a frappé. */
    private static void push(Store<EntityStore> store, Ref<EntityStore> attacker, Ref<EntityStore> victim) {
        Vector3d from = Telegraphs.position(store, attacker);
        Vector3d at = Telegraphs.position(store, victim);
        Velocity velocity = at == null ? null : store.getComponent(victim, Velocity.getComponentType());
        if (from == null || velocity == null) {
            return;
        }
        double a = Telegraphs.horizontal(at, from) > 0.1 ? Telegraphs.angle(from, at) : Math.random() * Math.PI * 2;
        velocity.addInstruction(new Vector3d(Math.cos(a) * SLIPPERY_PUSH, SLIPPERY_UP, Math.sin(a) * SLIPPERY_PUSH), null,
                ChangeVelocityType.Set);
    }

    // --- morts -------------------------------------------------------------------------------------------

    /** Un ennemi meurt en `at` (thread du monde) : Dernier rire et Vengeance. */
    public static void onFoeDeath(World world, Store<EntityStore> store, String role, Vector3d at) {
        FractalRuns.Run run = FractalRuns.of(world);
        if (run == null || run.instabilities().isEmpty() || isExempt(role)) {
            return;
        }
        if (run.instabilities().contains(Instability.LAST_LAUGH)) {
            lastLaugh(world, store, at);
        }
        if (run.instabilities().contains(Instability.VENGEANCE)) {
            vengeance(store, at);
        }
    }

    private static void lastLaugh(World world, Store<EntityStore> store, Vector3d at) {
        Vector3d center = new Vector3d(at);
        float seconds = LAST_LAUGH_SECONDS * FractalRuns.windupFactor(world);
        Telegraphs.circle(store, center, LAST_LAUGH_RADIUS, seconds);
        Telegraphs.particle(store, "Nakasar_Fractal_Last_Laugh", new Vector3d(center).add(0, 0.6, 0), 1f);
        Delayed.later(world, seconds, s -> {
            Telegraphs.particle(s, "Nakasar_Fractal_Bomb_Blast", new Vector3d(center).add(0, 0.3, 0), 1.3f);
            Telegraphs.sound(s, "SFX_Goblin_Lobber_Bomb_Death", center);
            for (PlayerRef player : world.getPlayerRefs()) {
                Ref<EntityStore> ref = player.getReference();
                Vector3d p = Telegraphs.position(s, ref);
                if (p != null && Telegraphs.horizontal(p, center) <= LAST_LAUGH_RADIUS + 0.3 && Math.abs(p.y() - center.y()) <= 3) {
                    Hurt.percent(s, ref, LAST_LAUGH_PART, CAUSE);
                }
            }
        });
    }

    private static void vengeance(Store<EntityStore> store, Vector3d at) {
        List<Ref<EntityStore>> near = new ArrayList<>();
        store.forEachChunk(NPCEntity.getComponentType(), (ArchetypeChunk<EntityStore> chunk, CommandBuffer<EntityStore> b) -> {
            for (int i = 0; i < chunk.size(); i++) {
                TransformComponent transform = chunk.getComponent(i, TransformComponent.getComponentType());
                NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
                if (transform != null && npc != null && !isExempt(npc.getRoleName())
                        && transform.getPosition().distance(at) <= VENGEANCE_RADIUS) {
                    near.add(chunk.getReferenceTo(i));
                }
            }
        });
        for (Ref<EntityStore> ref : near) {
            if (Spawns.alive(store, ref) && Foes.inGroup(ref, store)) {
                Hurt.effect(store, ref, VENGEANCE, VENGEANCE_SECONDS);
            }
        }
    }
}
