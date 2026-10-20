package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.protocol.packets.interface_.EventTitleStyle;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.util.EventTitleUtil;
import dev.nakasar.hytale.fractals.party.FractalCatalog;
import dev.nakasar.hytale.fractals.party.FractalRuns;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;

/**
 * État d'un Observatoire (une instance par Fragment des Brumes utilisé) : le meneur, le niveau choisi à l'Astrolabe et
 * le groupe debout sur le cercle d'harmonisation ({@link HarmonyCircleSystem}).
 *
 * <p>Le meneur est le premier joueur arrivé dans l'Observatoire ; s'il part, le suivant arrivé le remplace. Lui seul
 * règle le niveau et ouvre une arche. Tout est lu et modifié sur le thread du monde de l'Observatoire.
 */
public final class Observatory {

    public static final int MAX_GROUP = 5;
    public static final int MIN_LEVEL = 1;
    public static final int MAX_LEVEL = 100;
    /** Niveaux par rang (Initié 1-25, Adepte 26-50, Expert 51-75, Maître 76-100). */
    public static final int RANK_SIZE = 25;
    private static final String[] RANKS = {"Initiate", "Adept", "Expert", "Master"};
    static final String MESSAGES = "nakasar_fractals.observatory.";

    /** État d'un Observatoire. */
    public static final class State {
        /** Joueurs présents, dans l'ordre d'arrivée. */
        final Set<UUID> present = new LinkedHashSet<>();
        /** Joueurs sur le cercle, dans l'ordre où ils y sont montés (au plus {@value #MAX_GROUP}). */
        final Set<UUID> circle = new LinkedHashSet<>();
        /** Joueurs sur le cercle complet, déjà prévenus. */
        final Set<UUID> refused = new LinkedHashSet<>();
        UUID leader;
        int level = MIN_LEVEL;

        public int level() {
            return level;
        }
    }

    private static final Map<World, State> STATES = Collections.synchronizedMap(new WeakHashMap<>());

    private Observatory() {
    }

    public static State state(World world) {
        return STATES.computeIfAbsent(world, w -> new State());
    }

    public static Message rank(int level) {
        int rank = Math.min(RANKS.length - 1, (Math.max(MIN_LEVEL, level) - 1) / RANK_SIZE);
        return Message.translation("nakasar_fractals.rank." + RANKS[rank]);
    }

    /** Vrai si le joueur peut agir ici : dans un Observatoire et meneur ; sinon il est prévenu. */
    static boolean checkLeader(World world, PlayerRef player) {
        if (!FractalCatalog.isObservatory(world)) {
            player.sendMessage(Message.translation(MESSAGES + "notHere"));
            return false;
        }
        State state = state(world);
        if (state.leader == null) {
            state.leader = player.getUuid();   // premier tick pas encore passé : le premier qui agit mène
        }
        if (!state.leader.equals(player.getUuid())) {
            player.sendMessage(Message.translation(MESSAGES + "notLeader").param("name", nameOf(world, state.leader)));
            return false;
        }
        return true;
    }

    /** Règle le niveau (meneur seulement) et l'annonce à tout l'Observatoire. */
    public static void setLevel(World world, PlayerRef player, int level) {
        if (!checkLeader(world, player)) {
            return;
        }
        State state = state(world);
        int clamped = Math.max(MIN_LEVEL, Math.min(MAX_LEVEL, level));
        if (clamped == state.level) {
            player.sendMessage(Message.translation(MESSAGES + "level.same").param("level", clamped));
            return;
        }
        state.level = clamped;
        Message title = Message.translation(MESSAGES + "level.title").param("level", clamped);
        Message subtitle = Message.translation(MESSAGES + "level.rank").param("rank", rank(clamped));
        for (PlayerRef other : world.getPlayerRefs()) {
            EventTitleUtil.showEventTitleToPlayer(other, title, subtitle, EventTitleStyle.Default, null, 2f, 0.3f, 0.6f);
        }
    }

    /** Ouvre la fractale pour le cercle (meneur seulement ; il rejoint le groupe s'il reste une place). */
    public static void launch(World world, PlayerRef player, String fractalInput) {
        if (!checkLeader(world, player)) {
            return;
        }
        String fractal = FractalCatalog.resolve(fractalInput);
        if (fractal == null) {
            player.sendMessage(Message.translation(MESSAGES + "unknown").param("fractal", String.valueOf(fractalInput)));
            return;
        }
        if (!FractalCatalog.isOpen(fractal)) {
            player.sendMessage(Message.translation(MESSAGES + "soon").param("fractal", FractalCatalog.name(fractal)));
            return;
        }
        State state = state(world);
        List<PlayerRef> group = circlePlayers(world, state);
        if (group.isEmpty()) {
            player.sendMessage(Message.translation(MESSAGES + "emptyCircle"));
            return;
        }
        if (!state.circle.contains(player.getUuid()) && group.size() < MAX_GROUP) {
            group.add(player);
        }
        Message launch = Message.translation(MESSAGES + "launch").param("fractal", FractalCatalog.name(fractal))
                .param("level", state.level);
        group.forEach(member -> member.sendMessage(launch));
        int level = state.level;
        world.execute(() -> FractalRuns.launch(world, world.getEntityStore().getStore(), fractal, level, group));
    }

    /** Résumé du groupe pour {@code /fractale groupe}. */
    public static Message describe(World world) {
        State state = state(world);
        List<String> names = new ArrayList<>();
        for (PlayerRef member : circlePlayers(world, state)) {
            names.add(member.getUsername());
        }
        return Message.translation(MESSAGES + "group").param("count", names.size()).param("level", state.level)
                .param("leader", nameOf(world, state.leader)).param("names", names.isEmpty() ? "-" : String.join(", ", names));
    }

    /** Joueurs du cercle encore dans le monde, dans l'ordre où ils y sont montés. */
    static List<PlayerRef> circlePlayers(World world, State state) {
        List<PlayerRef> out = new ArrayList<>();
        for (UUID id : state.circle) {
            PlayerRef player = find(world, id);
            if (player != null) {
                out.add(player);
            }
        }
        return out;
    }

    static PlayerRef find(World world, UUID id) {
        if (id == null) {
            return null;
        }
        for (PlayerRef player : world.getPlayerRefs()) {
            if (id.equals(player.getUuid())) {
                return player;
            }
        }
        return null;
    }

    static String nameOf(World world, UUID id) {
        PlayerRef player = find(world, id);
        return player == null ? "-" : player.getUsername();
    }

    public static void clearAll() {
        STATES.clear();
    }
}
