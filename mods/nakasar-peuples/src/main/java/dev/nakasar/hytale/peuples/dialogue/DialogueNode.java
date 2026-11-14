package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;

/** Un nœud de dialogue : la réplique du PNJ et ses réponses (quatre au plus). */
public final class DialogueNode {

    public static final BuilderCodec<DialogueNode> CODEC = BuilderCodec.builder(DialogueNode.class, DialogueNode::new)
            .append(new KeyedCodec<>("Id", Codec.STRING), (n, v) -> n.id = v, n -> n.id)
            .documentation("Identifiant du nœud dans le dialogue.")
            .add()
            .append(new KeyedCodec<>("TextKey", Codec.STRING), (n, v) -> n.textKey = v, n -> n.textKey)
            .documentation("Clé de traduction de la réplique.")
            .add()
            .append(new KeyedCodec<>("Responses", new ArrayCodec<>(DialogueResponse.CODEC, DialogueResponse[]::new)),
                    (n, v) -> n.responses = v, n -> n.responses)
            .documentation("Réponses du joueur (quatre au plus) ; aucune : seul « Partir » reste.")
            .add()
            .build();

    String id;
    String textKey;
    DialogueResponse[] responses = new DialogueResponse[0];

    public String id() {
        return id;
    }

    public String textKey() {
        return textKey;
    }

    public DialogueResponse[] responses() {
        return responses == null ? new DialogueResponse[0] : responses;
    }
}
