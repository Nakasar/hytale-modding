package dev.nakasar.hytale.peuples.klops;

import com.hypixel.hytale.codec.builder.BuilderCodec;
import dev.nakasar.hytale.peuples.dialogue.DialogueContext;
import dev.nakasar.hytale.peuples.dialogue.DialogueEffect;

/** Effets de dialogue du Klops errant (étape 7), enregistrés à part des effets de base ({@code DialogueTypes}). */
public final class KlopsDialogueTypes {

    private KlopsDialogueTypes() {
    }

    public static void register() {
        DialogueEffect.CODEC.register("KlopsParcel", ParcelEffect.class, ParcelEffect.CODEC);
        DialogueEffect.CODEC.register("KlopsRoute", RouteEffect.class, RouteEffect.CODEC);
    }

    /** {@code {"Type": "KlopsParcel"}} : le Klops confie un colis pour un autre village. */
    public static final class ParcelEffect extends DialogueEffect {
        public static final BuilderCodec<ParcelEffect> CODEC = BuilderCodec.builder(ParcelEffect.class, ParcelEffect::new).build();

        @Override
        public boolean apply(DialogueContext context) {
            return Klops.giveParcel(context.world(), context.store(), context.ref(), context.playerRef(), context.village());
        }
    }

    /** {@code {"Type": "KlopsRoute"}} : dit où le Klops est aujourd'hui et où il sera demain. */
    public static final class RouteEffect extends DialogueEffect {
        public static final BuilderCodec<RouteEffect> CODEC = BuilderCodec.builder(RouteEffect.class, RouteEffect::new).build();

        @Override
        public boolean apply(DialogueContext context) {
            context.playerRef().sendMessage(Klops.route(context.world(), context.store(), context.ref()));
            return true;
        }
    }
}
