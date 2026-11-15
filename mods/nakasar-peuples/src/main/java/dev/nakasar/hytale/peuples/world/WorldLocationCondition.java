package dev.nakasar.hytale.peuples.world;

import com.hypixel.hytale.builtin.adventure.worldevents.condition.EventCondition;
import com.hypixel.hytale.builtin.adventure.worldevents.context.ContextKey;
import com.hypixel.hytale.builtin.adventure.worldevents.context.LocationContext;
import com.hypixel.hytale.builtin.adventure.worldevents.event.Validator;
import com.hypixel.hytale.builtin.adventure.worldevents.event.WorldEvent;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import org.joml.Vector3i;

import javax.annotation.Nonnull;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.UUID;

/**
 * Condition d'évènement de monde {@value #ID} : donne aux rendez-vous du monde vivant ({@link Calendar} : fête,
 * foire, migration) leur lieu, choisi par le Java, sous la clé {@code LocationKey} (comme
 * {@code raid/RaidLocationCondition} pour les raids). Sans lieu connu, elle n'est jamais remplie.
 */
public final class WorldLocationCondition implements EventCondition.Ticking {

    public static final String ID = "Nakasar_Peuples_WorldLocation";
    public static final EventCondition.Type TYPE = new EventCondition.Type(ID, 1.0F);

    private static final Map<UUID, Vector3i> LOCATIONS = new ConcurrentHashMap<>();

    static void put(UUID event, Vector3i at) {
        LOCATIONS.put(event, at);
    }

    static void remove(UUID event) {
        LOCATIONS.remove(event);
    }

    static Vector3i location(UUID event) {
        return event == null ? null : LOCATIONS.get(event);
    }

    /** Aucun état à sauvegarder : le lieu est relu dans le Java. */
    public static final BuilderCodec<WorldLocationCondition> CODEC = BuilderCodec.builder(WorldLocationCondition.class, WorldLocationCondition::new)
            .build();
    @Nonnull
    private Config config = Config.DEFAULT;
    private UUID event;

    @Override
    public boolean test() {
        return event != null && location(event) != null;
    }

    @Override
    public void reset() {
        event = null;
    }

    @Override
    public void tick(float dt, @Nonnull Store<EntityStore> store) {
    }

    @Override
    public boolean onStart(@Nonnull WorldEvent worldEvent) {
        event = worldEvent.uuid;
        if (config.locationKey != null) {
            worldEvent.context.remove(config.locationKey, LocationContext.class);
        }
        return true;
    }

    @Override
    public boolean onComplete(@Nonnull WorldEvent worldEvent) {
        Vector3i at = location(worldEvent.uuid);
        if (config.locationKey == null || at == null) {
            return false;
        }
        worldEvent.context.put(config.locationKey, new LocationContext(new Vector3i(at)));
        return true;
    }

    public static final class Config implements EventCondition.Config {

        public static final BuilderCodec<Config> CODEC = BuilderCodec.builder(Config.class, Config::new)
                .documentation("Completes when the Peuples mod knows where the gathering is; stores it under LocationKey.")
                .<ContextKey>append(new KeyedCodec<>("LocationKey", ContextKey.CODEC), (self, value) -> self.locationKey = value, self -> self.locationKey)
                .documentation("Context key receiving the gathering location.")
                .add()
                .build();

        static final Config DEFAULT = new Config();

        private ContextKey locationKey;

        @Nonnull
        @Override
        public EventCondition create() {
            WorldLocationCondition condition = new WorldLocationCondition();
            condition.config = this;
            return condition;
        }

        @Override
        public void validate(@Nonnull Validator validator) {
            if (locationKey == null) {
                validator.addErrorMessage("WorldLocationCondition: LocationKey is missing");
            } else {
                validator.addDefinedKey(ID, "LocationKey", locationKey);
            }
        }
    }
}
