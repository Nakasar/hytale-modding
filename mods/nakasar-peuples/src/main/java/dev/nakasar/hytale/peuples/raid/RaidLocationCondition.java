package dev.nakasar.hytale.peuples.raid;

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
import java.util.UUID;

/**
 * Condition d'évènement de monde {@value #ID} : donne au raid son lieu, le camp trork choisi par le Java
 * ({@link Raids#location(UUID)}), sous la clé {@code LocationKey} (comme le {@code LocationCondition} vanilla qui
 * cherche un lieu sauvage près d'un joueur). Les actions vanilla qui suivent ({@code ShowEventTitleAction},
 * {@code EffectsAction}) jouent alors leur titre et leur son à cet endroit. Sans lieu connu (raid annulé entre-temps),
 * elle n'est jamais remplie et l'évènement s'arrête au bout de son autre branche.
 */
public final class RaidLocationCondition implements EventCondition.Ticking {

    public static final String ID = "Nakasar_Peuples_RaidLocation";
    public static final EventCondition.Type TYPE = new EventCondition.Type(ID, 1.0F);

    /** Aucun état à sauvegarder : le lieu est relu dans le Java. */
    public static final BuilderCodec<RaidLocationCondition> CODEC = BuilderCodec.builder(RaidLocationCondition.class, RaidLocationCondition::new)
            .build();

    @Nonnull
    private Config config = Config.DEFAULT;
    private UUID event;

    @Override
    public boolean test() {
        return event != null && Raids.location(event) != null;
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
        Vector3i at = Raids.location(worldEvent.uuid);
        if (config.locationKey == null || at == null) {
            return false;
        }
        worldEvent.context.put(config.locationKey, new LocationContext(new Vector3i(at)));
        return true;
    }

    public static final class Config implements EventCondition.Config {

        public static final BuilderCodec<Config> CODEC = BuilderCodec.builder(Config.class, Config::new)
                .documentation("Completes when the Peuples mod knows where the raid camp is; stores it under LocationKey.")
                .<ContextKey>append(new KeyedCodec<>("LocationKey", ContextKey.CODEC), (self, value) -> self.locationKey = value, self -> self.locationKey)
                .documentation("Context key receiving the raid camp location.")
                .add()
                .build();

        static final Config DEFAULT = new Config();

        private ContextKey locationKey;

        @Nonnull
        @Override
        public EventCondition create() {
            RaidLocationCondition condition = new RaidLocationCondition();
            condition.config = this;
            return condition;
        }

        @Override
        public void validate(@Nonnull Validator validator) {
            if (locationKey == null) {
                validator.addErrorMessage("RaidLocationCondition: LocationKey is missing");
            } else {
                validator.addDefinedKey(ID, "LocationKey", locationKey);
            }
        }
    }
}
