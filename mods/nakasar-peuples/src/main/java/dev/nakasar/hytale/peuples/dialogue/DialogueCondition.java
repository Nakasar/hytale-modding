package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.codec.lookup.CodecMapCodec;

/**
 * Condition d'une réponse ou d'une entrée de dialogue (GDD, section Dialogue avec les PNJ). Le champ {@code "Type"}
 * choisit la classe ({@link DialogueTypes} enregistre celles du socle) ; les étapes suivantes en ajoutent (rang de
 * peuple via le ReputationPlugin vanilla, objectif en cours, étape de chaîne, heure...).
 */
public abstract class DialogueCondition {

    public static final CodecMapCodec<DialogueCondition> CODEC = new CodecMapCodec<>("Type");

    /** Vrai si la condition est remplie pour ce joueur. */
    public abstract boolean test(DialogueContext context);

    /** Toutes les conditions sont remplies (aucune condition : vrai). */
    public static boolean all(DialogueCondition[] conditions, DialogueContext context) {
        if (conditions != null) {
            for (DialogueCondition c : conditions) {
                if (c != null && !c.test(context)) {
                    return false;
                }
            }
        }
        return true;
    }
}
