package dev.nakasar.hytale.peuples.player;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Component;
import com.hypixel.hytale.component.ComponentAccessor;
import com.hypixel.hytale.component.ComponentType;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Arrays;
import java.util.Set;
import java.util.TreeSet;

/**
 * Ce que le mod retient d'un joueur, sauvegardé avec lui (id {@value #ID}) : pour l'instant les drapeaux posés par
 * les dialogues (« a rencontré l'Ancien », « a reçu le cadeau ») ; la réputation de village (étape 4) et l'étape de la
 * chaîne de chaque peuple (étape 6) s'y ajouteront. La réputation de peuple, elle, reste au ReputationPlugin vanilla.
 */
public final class PeuplesPlayer implements Component<EntityStore> {

    public static final String ID = "Nakasar_Peuples_Player";

    public static final BuilderCodec<PeuplesPlayer> CODEC = BuilderCodec.builder(PeuplesPlayer.class, PeuplesPlayer::new)
            .append(new KeyedCodec<>("Flags", Codec.STRING), (p, v) -> p.setFlags(v), p -> String.join(",", p.flags))
            .documentation("Drapeaux posés par les dialogues, séparés par des virgules.")
            .add()
            .build();

    private static ComponentType<EntityStore, PeuplesPlayer> componentType;

    private final Set<String> flags = new TreeSet<>();

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

    @Override
    public Component<EntityStore> clone() {
        PeuplesPlayer copy = new PeuplesPlayer();
        copy.flags.addAll(flags);
        return copy;
    }
}
