package dev.nakasar.hytale.peuples.player;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;
import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.request.PlayerRequest;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * Ce que le mod retient d'un joueur, sauvegardé avec lui (id {@value #ID}) : les drapeaux posés par les dialogues
 * (« a rencontré l'Ancien », « a reçu le cadeau »), et depuis l'étape 3 ses demandes en cours, les demandes déjà
 * remplies (pour ne pas reprendre deux fois la même) et le nombre de demandes remplies par village (base de la
 * réputation de village de l'étape 4). Depuis l'étape 4 : sa réputation dans chaque village et le dernier jour qu'il
 * y a passé. L'étape de la chaîne de chaque peuple (étape 6) s'y ajoutera. La réputation de peuple, elle, reste au
 * ReputationPlugin vanilla.
 */
public final class PeuplesPlayer implements Component<EntityStore> {

    public static final String ID = "Nakasar_Peuples_Player";

    public static final BuilderCodec<PeuplesPlayer> CODEC = BuilderCodec.builder(PeuplesPlayer.class, PeuplesPlayer::new)
            .append(new KeyedCodec<>("Flags", Codec.STRING), (p, v) -> p.setFlags(v), p -> String.join(",", p.flags))
            .documentation("Drapeaux posés par les dialogues, séparés par des virgules.")
            .add()
            .append(new KeyedCodec<>("Requests", new ArrayCodec<>(PlayerRequest.CODEC, PlayerRequest[]::new)),
                    (p, v) -> p.setRequests(v), p -> p.requests.toArray(PlayerRequest[]::new))
            .documentation("Demandes du tableau en cours.")
            .add()
            .append(new KeyedCodec<>("DoneRequests", Codec.STRING), (p, v) -> p.setDone(v), p -> String.join(",", p.done))
            .documentation("Ids des dernières demandes remplies, séparés par des virgules.")
            .add()
            .append(new KeyedCodec<>("Helped", Codec.STRING), (p, v) -> p.setHelped(v), p -> p.helpedString())
            .documentation("Demandes remplies par village : id=nombre, séparés par des virgules.")
            .add()
            .append(new KeyedCodec<>("Reputation", Codec.STRING), (p, v) -> readMap(v, p.reputation), p -> writeMap(p.reputation))
            .documentation("Réputation de village (étape 4) : id=valeur, séparés par des virgules.")
            .add()
            .append(new KeyedCodec<>("Visits", Codec.STRING), (p, v) -> readMap(v, p.visits), p -> writeMap(p.visits))
            .documentation("Dernier jour de jeu passé dans chaque village : id=jour (déclin de la réputation après une longue absence).")
            .add()
            .build();

    /** On garde les ids des dernières demandes remplies (assez pour couvrir plusieurs jours de tableau). */
    private static final int DONE_MEMORY = 40;

    private static ComponentType<EntityStore, PeuplesPlayer> componentType;

    private final Set<String> flags = new TreeSet<>();
    private final List<PlayerRequest> requests = new ArrayList<>();
    private final LinkedHashSet<String> done = new LinkedHashSet<>();
    private final Map<String, Integer> helped = new TreeMap<>();
    private final Map<String, Long> reputation = new TreeMap<>();
    private final Map<String, Long> visits = new TreeMap<>();

    public static void setComponentType(ComponentType<EntityStore, PeuplesPlayer> type) {
        componentType = type;
    }

    public static ComponentType<EntityStore, PeuplesPlayer> getComponentType() {
        return componentType;
    }

    /** État du joueur, ou null s'il n'en a pas encore. */
    public static PeuplesPlayer get(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> player) {
        return player == null || !player.isValid() ? null : accessor.getComponent(player, componentType);
    }

    /** État du joueur, créé au besoin. */
    public static PeuplesPlayer ensure(ComponentAccessor<EntityStore> accessor, Ref<EntityStore> player) {
        return accessor.ensureAndGetComponent(player, componentType);
    }

    public boolean hasFlag(String flag) {
        return flags.contains(flag);
    }

    public void setFlag(String flag, boolean value) {
        if (flag == null || flag.isBlank() || flag.contains(",")) {
            return;
        }
        if (value) {
            flags.add(flag);
        } else {
            flags.remove(flag);
        }
    }

    public Set<String> flags() {
        return Set.copyOf(flags);
    }

    public void clearFlags() {
        flags.clear();
    }

    private void setFlags(String value) {
        flags.clear();
        if (value != null && !value.isBlank()) {
            Arrays.stream(value.split(",")).map(String::trim).filter(s -> !s.isEmpty()).forEach(flags::add);
        }
    }

    /** Demandes en cours (lecture seule). */
    public List<PlayerRequest> requests() {
        return Collections.unmodifiableList(requests);
    }

    public PlayerRequest request(String requestId) {
        for (PlayerRequest r : requests) {
            if (r.id().equals(requestId)) {
                return r;
            }
        }
        return null;
    }

    public void addRequest(PlayerRequest request) {
        requests.add(request);
    }

    public boolean removeRequest(PlayerRequest request) {
        return requests.remove(request);
    }

    /** Vrai si le joueur a déjà rempli la demande d'id `requestId`. */
    public boolean hasDone(String requestId) {
        return done.contains(requestId);
    }

    /** Note une demande remplie dans le village `villageId`. */
    public void markDone(String requestId, String villageId) {
        done.remove(requestId);
        done.add(requestId);
        while (done.size() > DONE_MEMORY) {
            done.remove(done.iterator().next());
        }
        if (villageId != null && !villageId.isBlank() && !villageId.contains(",") && !villageId.contains("=")) {
            helped.merge(villageId, 1, Integer::sum);
        }
    }

    /** Nombre de demandes remplies par ce joueur pour le village `villageId`. */
    public int helped(String villageId) {
        return helped.getOrDefault(villageId, 0);
    }

    /** Réputation du joueur dans le village `villageId` (0 s'il n'y a jamais rien fait). */
    public int villageReputation(String villageId) {
        return reputation.getOrDefault(villageId, 0L).intValue();
    }

    /** Réputation du joueur dans le village `villageId`, ou `initial` s'il n'y a jamais rien fait (étape 7 : camp trork). */
    public int villageReputation(String villageId, int initial) {
        Long value = reputation.get(villageId);
        return value == null ? initial : value.intValue();
    }

    public void setVillageReputation(String villageId, int value) {
        if (validKey(villageId)) {
            reputation.put(villageId, (long) value);
        }
    }

    /** Dernier jour de jeu passé dans le village, ou null. */
    public Long lastVisit(String villageId) {
        return visits.get(villageId);
    }

    public void setLastVisit(String villageId, long day) {
        if (validKey(villageId)) {
            visits.put(villageId, day);
        }
    }

    /** Oublie la réputation de tous les villages (commande d'essai). */
    public void clearVillageReputation() {
        reputation.clear();
        visits.clear();
    }

    private static boolean validKey(String key) {
        return key != null && !key.isBlank() && !key.contains(",") && !key.contains("=");
    }

    private static void readMap(String value, Map<String, Long> into) {
        into.clear();
        if (value == null || value.isBlank()) {
            return;
        }
        for (String part : value.split(",")) {
            int eq = part.indexOf('=');
            if (eq > 0) {
                try {
                    into.put(part.substring(0, eq).trim(), Long.parseLong(part.substring(eq + 1).trim()));
                } catch (NumberFormatException ignored) {
                    // Entrée abîmée : ignorée.
                }
            }
        }
    }

    private static String writeMap(Map<String, Long> map) {
        List<String> parts = new ArrayList<>();
        map.forEach((k, v) -> parts.add(k + "=" + v));
        return String.join(",", parts);
    }

    private void setRequests(PlayerRequest[] value) {
        requests.clear();
        if (value != null) {
            for (PlayerRequest r : value) {
                if (r != null) {
                    requests.add(r);
                }
            }
        }
    }

    private void setDone(String value) {
        done.clear();
        if (value != null && !value.isBlank()) {
            Arrays.stream(value.split(",")).map(String::trim).filter(s -> !s.isEmpty()).forEach(done::add);
        }
    }

    private void setHelped(String value) {
        helped.clear();
        if (value == null || value.isBlank()) {
            return;
        }
        for (String part : value.split(",")) {
            int eq = part.indexOf('=');
            if (eq > 0) {
                try {
                    helped.put(part.substring(0, eq).trim(), Integer.parseInt(part.substring(eq + 1).trim()));
                } catch (NumberFormatException ignored) {
                    // Entrée abîmée : ignorée.
                }
            }
        }
    }

    private String helpedString() {
        List<String> parts = new ArrayList<>();
        helped.forEach((k, v) -> parts.add(k + "=" + v));
        return String.join(",", parts);
    }

    @Override
    public Component<EntityStore> clone() {
        PeuplesPlayer copy = new PeuplesPlayer();
        copy.flags.addAll(flags);
        for (PlayerRequest r : requests) {
            copy.requests.add(r.copy());
        }
        copy.done.addAll(done);
        copy.helped.putAll(helped);
        copy.reputation.putAll(reputation);
        copy.visits.putAll(visits);
        return copy;
    }
}
