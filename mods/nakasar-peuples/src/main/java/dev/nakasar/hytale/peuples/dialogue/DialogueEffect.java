package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.codec.lookup.CodecMapCodec;

/**
 * Effet d'une réponse de dialogue (donner, prendre, poser un drapeau, essor, ouvrir le tableau...). Le champ
 * {@code "Type"} choisit la classe ({@link DialogueTypes}). Les effets d'une réponse s'appliquent dans l'ordre, sur le
 * thread du monde, après le contrôle de ses conditions.
 */
public abstract class DialogueEffect {

    public static final CodecMapCodec<DialogueEffect> CODEC = new CodecMapCodec<>("Type");

    /**
     * Applique l'effet. Rend faux si l'effet n'a pas pu se faire (objet manquant, inventaire plein) : les effets
     * suivants de la réponse ne s'appliquent pas et le dialogue reste sur le nœud.
     */
    public abstract boolean apply(DialogueContext context);

    /** Vrai si l'effet ferme la fenêtre (ouverture d'une autre page). */
    public boolean closesDialogue() {
        return false;
    }
}
