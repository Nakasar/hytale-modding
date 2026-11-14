package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;

/**
 * Une réponse du joueur. Une réponse dont les conditions ne sont pas remplies reste visible mais grisée, avec sa
 * condition ({@code FailKey}) : rien n'est caché derrière un rang sans l'indiquer (GDD).
 */
public final class DialogueResponse {

    public static final BuilderCodec<DialogueResponse> CODEC = BuilderCodec.builder(DialogueResponse.class, DialogueResponse::new)
            .append(new KeyedCodec<>("TextKey", Codec.STRING), (r, v) -> r.textKey = v, r -> r.textKey)
            .documentation("Clé de traduction du texte du bouton.")
            .add()
            .append(new KeyedCodec<>("HintKey", Codec.STRING), (r, v) -> r.hintKey = v, r -> r.hintKey)
            .documentation("Ligne d'effet sous le bouton (« ouvre le tableau », « donne 3 graines »).")
            .add()
            .append(new KeyedCodec<>("Conditions", new ArrayCodec<>(DialogueCondition.CODEC, DialogueCondition[]::new)),
                    (r, v) -> r.conditions = v, r -> r.conditions)
            .documentation("Conditions de la réponse (toutes).")
            .add()
            .append(new KeyedCodec<>("FailKey", Codec.STRING), (r, v) -> r.failKey = v, r -> r.failKey)
            .documentation("Condition affichée quand elle n'est pas remplie (« Il faut 3 graines »).")
            .add()
            .append(new KeyedCodec<>("Effects", new ArrayCodec<>(DialogueEffect.CODEC, DialogueEffect[]::new)),
                    (r, v) -> r.effects = v, r -> r.effects)
            .documentation("Effets appliqués dans l'ordre quand le joueur choisit la réponse.")
            .add()
            .append(new KeyedCodec<>("Next", Codec.STRING), (r, v) -> r.next = v, r -> r.next)
            .documentation("Nœud suivant ; absent : la fenêtre se ferme.")
            .add()
            .build();

    String textKey;
    String hintKey;
    DialogueCondition[] conditions = new DialogueCondition[0];
    String failKey;
    DialogueEffect[] effects = new DialogueEffect[0];
    String next;

    public String textKey() {
        return textKey;
    }

    public String hintKey() {
        return hintKey;
    }

    public DialogueCondition[] conditions() {
        return conditions == null ? new DialogueCondition[0] : conditions;
    }

    public String failKey() {
        return failKey;
    }

    public DialogueEffect[] effects() {
        return effects == null ? new DialogueEffect[0] : effects;
    }

    public String next() {
        return next;
    }

    public boolean available(DialogueContext context) {
        return DialogueCondition.all(conditions, context);
    }
}
