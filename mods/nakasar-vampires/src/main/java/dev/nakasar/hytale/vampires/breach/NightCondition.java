package dev.nakasar.hytale.vampires.breach;

import com.hypixel.hytale.builtin.adventure.worldevents.condition.EventCondition;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.validation.Validators;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.modules.time.WorldTimeResource;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import javax.annotation.Nonnull;

/**
 * Condition d'évènement de monde {@value #ID} : se réalise quand il fait nuit dans le monde.
 *
 * <p>Le {@code TimeCondition} vanilla attend une heure précise et ne sait pas dire « entre le crépuscule et
 * l'aube » : une nuit qui passe minuit le ferait attendre le soir suivant. Celle-ci compare la progression du
 * jour ({@link WorldTimeResource#getDayProgress()}, 0 à minuit) à une plage qui peut passer minuit : par défaut
 * de 0,8 (19 h 12, coucher du soleil du jeu) à 0,15 (3 h 36, pour ne pas ouvrir une brèche juste avant l'aube).
 * Comme le {@code TimeCondition}, elle reste acquise jusqu'au redémarrage de son étape.
 */
public final class NightCondition implements EventCondition.Ticking {

    public static final String ID = "Nakasar_NightCondition";
    public static final EventCondition.Type TYPE = new EventCondition.Type(ID, 1.0F);

    /** État enregistré avec l'évènement : la nuit a-t-elle déjà été constatée. */
    public static final BuilderCodec<NightCondition> CODEC = BuilderCodec.builder(NightCondition.class, NightCondition::new)
            .append(new KeyedCodec<>("Complete", Codec.BOOLEAN), (self, value) -> self.complete = value, self -> self.complete)
            .add()
            .build();

    @Nonnull
    private Config config = Config.DEFAULT;
    private boolean complete;

    @Override
    public boolean test() {
        return complete;
    }

    @Override
    public void reset() {
        complete = false;
    }

    @Override
    public void tick(float dt, @Nonnull Store<EntityStore> store) {
        if (!complete) {
            complete = isWithin(store.getResource(WorldTimeResource.getResourceType()).getDayProgress(), config.start, config.end);
        }
    }

    @Override
    public void merge(@Nonnull EventCondition other) {
        if (other instanceof NightCondition night) {
            complete = night.complete;
        }
    }

    /** {@code progress} est-il dans [start, end), la plage passant minuit quand start > end. */
    static boolean isWithin(double progress, double start, double end) {
        return start <= end ? progress >= start && progress < end : progress >= start || progress < end;
    }

    public static final class Config implements EventCondition.Config {

        public static final BuilderCodec<Config> CODEC = BuilderCodec.builder(Config.class, Config::new)
                .documentation("Completes once the world is at night: the day progress (0 at midnight, 0.5 at noon) is between Start and End, the range wrapping past midnight when Start > End.")
                .<Double>append(new KeyedCodec<>("Start", Codec.DOUBLE), (self, value) -> self.start = value, self -> self.start)
                .documentation("Day progress at which the night starts (default 0.8, sunset).")
                .addValidator(Validators.range(0.0, 1.0))
                .add()
                .<Double>append(new KeyedCodec<>("End", Codec.DOUBLE), (self, value) -> self.end = value, self -> self.end)
                .documentation("Day progress after which the condition no longer completes (default 0.15).")
                .addValidator(Validators.range(0.0, 1.0))
                .add()
                .build();

        static final Config DEFAULT = new Config();

        private double start = 0.8;
        private double end = 0.15;

        @Nonnull
        @Override
        public EventCondition create() {
            NightCondition condition = new NightCondition();
            condition.config = this;
            return condition;
        }
    }
}
