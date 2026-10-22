package dev.nakasar.hytale.fractals.boss;

import com.hypixel.hytale.component.ArchetypeChunk;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.component.system.tick.TickingSystem;
import com.hypixel.hytale.protocol.packets.interface_.UpdateBossBar;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.modules.entity.component.TransformComponent;
import com.hypixel.hytale.server.core.modules.entity.damage.DeathComponent;
import com.hypixel.hytale.server.core.modules.entity.tracker.NetworkId;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatMap;
import com.hypixel.hytale.server.core.modules.entitystats.EntityStatValue;
import com.hypixel.hytale.server.core.modules.entitystats.asset.DefaultEntityStatTypes;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import com.hypixel.hytale.server.npc.entities.NPCEntity;
import com.hypixel.hytale.server.npc.role.support.StateSupport;
import org.joml.Vector3d;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.WeakHashMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiConsumer;
import java.util.function.Function;

/**
 * Barre de vie des boss de fractales, comme celle du donjon gobelin (Deepworks). Copie du mod Vampires.
 *
 * <p>Le donjon vanilla passe par un gestionnaire de rencontre (encounter, action PNJ {@code SetEncounterBossBar}) qui
 * envoie le paquet {@link UpdateBossBar} aux joueurs de la rencontre ; le client y lit ensuite la vie de l'entité
 * désignée par son id réseau. Nos élites n'ont pas de rencontre : on envoie le même paquet nous-mêmes.
 *
 * <p>Une élite est « engagée » quand elle est en combat (état {@code Combat}) ou blessée ; chaque joueur à moins de
 * {@value #RANGE} blocs d'une élite engagée voit la barre de la plus proche. Elle disparaît quand l'élite meurt, se
 * calme (retour au calme et vie regagnée), ou quand le joueur s'éloigne ou change de monde.
 */
public final class BossBarSystem extends TickingSystem<EntityStore> {

    /** Rôles qui ont une barre de boss ({@link #register}, rempli par le plugin fractale par fractale). */
    private static final Set<String> ELITES = ConcurrentHashMap.newKeySet();
    /** Texte ajouté au nom de la barre, par rôle (barre de défiance) ; null : rien. Lu à chaque passage. */
    private static final Map<String, Function<Ref<EntityStore>, String>> LABELS = new ConcurrentHashMap<>();

    private static final double RANGE = 40;
    private static final float INTERVAL = 0.25f;

    /** Barre affichée par joueur : monde et id réseau de l'élite. */
    private static final Map<UUID, Shown> SHOWN = new ConcurrentHashMap<>();

    /** Système partagé par les mondes, chacun sur son thread : un compte à rebours par monde. */
    private final Map<World, Float> wait = Collections.synchronizedMap(new WeakHashMap<>());

    /** {@code player} : la session qui a reçu la barre ; une reconnexion crée un autre PlayerRef. */
    private record Shown(World world, int networkId, PlayerRef player, String label) {
    }

    private record Elite(int networkId, Vector3d position, String nameKey, String label) {
    }

    /** Donne une barre de boss au rôle `role`. */
    public static void register(String role) {
        ELITES.add(role);
    }

    /** Ajoute au nom de la barre du rôle `role` le texte rendu par `label` (null : rien) ; la barre est renvoyée quand il change. */
    public static void label(String role, Function<Ref<EntityStore>, String> label) {
        LABELS.put(role, label);
    }

    @Override
    public void tick(float dt, int systemIndex, Store<EntityStore> store) {
        World world = store.getExternalData().getWorld();
        float left = wait.getOrDefault(world, 0f) - dt;
        if (left > 0f) {
            wait.put(world, left);
            return;
        }
        wait.put(world, INTERVAL);

        List<PlayerRef> players = new ArrayList<>(world.getPlayerRefs());
        Set<UUID> present = new HashSet<>();
        for (PlayerRef player : players) {
            present.add(player.getUuid());
        }
        // Joueurs partis de ce monde (déconnexion, changement de monde) : on oublie leur barre.
        SHOWN.entrySet().removeIf(entry -> entry.getValue().world() == world && !present.contains(entry.getKey()));
        if (players.isEmpty()) {
            return;
        }

        List<Elite> engaged = new ArrayList<>();
        BiConsumer<ArchetypeChunk<EntityStore>, CommandBuffer<EntityStore>> collector = (chunk, buffer) -> collect(chunk, store, engaged);
        store.forEachChunk(NPCEntity.getComponentType(), collector);

        for (PlayerRef player : players) {
            Ref<EntityStore> ref = player.getReference();
            TransformComponent transform = ref == null || !ref.isValid() ? null
                    : store.getComponent(ref, TransformComponent.getComponentType());
            Elite nearest = null;
            if (transform != null) {
                double best = RANGE * RANGE;
                for (Elite elite : engaged) {
                    double distance = elite.position().distanceSquared(transform.getPosition());
                    if (distance <= best) {
                        best = distance;
                        nearest = elite;
                    }
                }
            }
            show(player, world, nearest);
        }
    }

    private static void collect(ArchetypeChunk<EntityStore> chunk, Store<EntityStore> store, List<Elite> engaged) {
        for (int i = 0; i < chunk.size(); i++) {
            NPCEntity npc = chunk.getComponent(i, NPCEntity.getComponentType());
            String role = npc == null ? null : npc.getRoleName();
            if (role == null || !ELITES.contains(role)) {
                continue;
            }
            Ref<EntityStore> ref = chunk.getReferenceTo(i);
            NetworkId networkId = chunk.getComponent(i, NetworkId.getComponentType());
            TransformComponent transform = chunk.getComponent(i, TransformComponent.getComponentType());
            if (networkId == null || transform == null || chunk.getComponent(i, DeathComponent.getComponentType()) != null
                    || !isEngaged(ref, store, chunk.getComponent(i, EntityStatMap.getComponentType()))) {
                continue;
            }
            String nameKey = npc.getRole() == null ? null : npc.getRole().getNameTranslationKey();
            Function<Ref<EntityStore>, String> labeler = LABELS.get(role);
            engaged.add(new Elite(networkId.getId(), new Vector3d(transform.getPosition()),
                    nameKey != null ? nameKey : role, labeler == null ? null : labeler.apply(ref)));
        }
    }

    private static boolean isEngaged(Ref<EntityStore> ref, Store<EntityStore> store, EntityStatMap stats) {
        EntityStatValue health = stats == null ? null : stats.get(DefaultEntityStatTypes.getHealth());
        if (health != null && health.get() <= 0f) {
            return false;
        }
        StateSupport state = StateSupport.get(ref, store);
        String name = state == null ? null : state.getStateName();
        if (name != null && name.startsWith("Combat")) {
            return true;
        }
        return health != null && health.get() < health.getMax() - 0.5f;
    }

    /** Envoie au joueur la barre de l'élite (null : aucune), seulement si elle change. */
    private static void show(PlayerRef player, World world, Elite elite) {
        UUID uuid = player.getUuid();
        Shown before = SHOWN.get(uuid);
        if (before != null && before.player() != player) {
            // Nouvelle session du même joueur : son client n'a aucune barre.
            SHOWN.remove(uuid);
            before = null;
        }
        if (before != null && elite != null && before.world() == world && before.networkId() == elite.networkId()
                && Objects.equals(before.label(), elite.label())) {
            return;
        }
        if (before != null) {
            player.getPacketHandler().writeNoCache(new UpdateBossBar(before.networkId(), null, true, false));
            SHOWN.remove(uuid);
        }
        if (elite != null) {
            Message name = Message.translation(elite.nameKey());
            if (elite.label() != null) {
                name = Message.join(name, Message.raw("  " + elite.label()));
            }
            player.getPacketHandler().writeNoCache(new UpdateBossBar(elite.networkId(), name.getFormattedMessage(), false, false));
            SHOWN.put(uuid, new Shown(world, elite.networkId(), player, elite.label()));
        }
    }

    public static void clearAll() {
        SHOWN.clear();
    }
}
