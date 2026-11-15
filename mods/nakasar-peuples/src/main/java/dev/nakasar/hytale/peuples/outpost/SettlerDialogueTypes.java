package dev.nakasar.hytale.peuples.outpost;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import dev.nakasar.hytale.peuples.dialogue.DialogueCondition;
import dev.nakasar.hytale.peuples.dialogue.DialogueContext;
import dev.nakasar.hytale.peuples.dialogue.DialogueEffect;
import dev.nakasar.hytale.peuples.zone.SiteRules;

/** Conditions et effets du dialogue du colon ({@link Settlers}), enregistrés à part des types de base. */
public final class SettlerDialogueTypes {

    private SettlerDialogueTypes() {
    }

    public static void register() {
        DialogueCondition.CODEC.register("SettlerSite", SiteCondition.class, SiteCondition.CODEC);
        DialogueEffect.CODEC.register("SettlerFollow", FollowEffect.class, FollowEffect.CODEC);
        DialogueEffect.CODEC.register("SettlerFound", FoundEffect.class, FoundEffect.CODEC);
        DialogueEffect.CODEC.register("SettlerHome", HomeEffect.class, HomeEffect.CODEC);
    }

    /**
     * {@code {"Type": "SettlerSite", "Reason": "OK"}} : le colon suit le joueur et l'examen de l'endroit a donné cette
     * raison ({@link SiteRules.Reason}). Sans raison : le colon suit le joueur, quel que soit l'examen.
     */
    public static final class SiteCondition extends DialogueCondition {
        public static final BuilderCodec<SiteCondition> CODEC = BuilderCodec.builder(SiteCondition.class, SiteCondition::new)
                .append(new KeyedCodec<>("Reason", Codec.STRING), (c, v) -> c.reason = v, c -> c.reason)
                .documentation("Raison de l'examen du site : OK, TOO_CLOSE_SAME, TOO_CLOSE_OTHER, PLANNED, OUT_OF_ZONE, SHORE, WATER, GROUND, RELIEF, UNLOADED.")
                .add()
                .build();

        String reason;

        @Override
        public boolean test(DialogueContext context) {
            SiteRules.Reason last = Settlers.lastReason(context.playerRef().getUuid());
            return last != null && (reason == null || last.name().equalsIgnoreCase(reason));
        }
    }

    /** {@code {"Type": "SettlerFollow"}} : le colon suit le joueur. */
    public static final class FollowEffect extends DialogueEffect {
        public static final BuilderCodec<FollowEffect> CODEC = BuilderCodec.builder(FollowEffect.class, FollowEffect::new).build();

        @Override
        public boolean apply(DialogueContext context) {
            return Settlers.accept(context.world(), context.store(), context.playerRef());
        }
    }

    /** {@code {"Type": "SettlerFound"}} : fonder le village ici (nouvel examen, colons au matin). */
    public static final class FoundEffect extends DialogueEffect {
        public static final BuilderCodec<FoundEffect> CODEC = BuilderCodec.builder(FoundEffect.class, FoundEffect::new).build();

        @Override
        public boolean apply(DialogueContext context) {
            return Settlers.found(context.world(), context.store(), context.ref(), context.playerRef());
        }
    }

    /** {@code {"Type": "SettlerHome"}} : le colon rentre attendre à son village. */
    public static final class HomeEffect extends DialogueEffect {
        public static final BuilderCodec<HomeEffect> CODEC = BuilderCodec.builder(HomeEffect.class, HomeEffect::new).build();

        @Override
        public boolean apply(DialogueContext context) {
            return Settlers.sendHome(context.world(), context.store(), context.playerRef());
        }
    }
}
