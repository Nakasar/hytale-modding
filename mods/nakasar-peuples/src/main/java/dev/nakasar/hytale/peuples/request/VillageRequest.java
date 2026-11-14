package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;

/**
 * Une demande affichée au tableau d'un village (une des trois du jour), sauvegardée avec le village. Les joueurs qui la
 * prennent en gardent chacun une copie ({@link PlayerRequest}) ; la première copie remplie donne l'essor au village et
 * libère la place pour une nouvelle demande (GDD : « renouvelées chaque matin ou quand l'une est remplie »).
 */
public final class VillageRequest {

    public static final BuilderCodec<VillageRequest> CODEC = BuilderCodec.builder(VillageRequest.class, VillageRequest::new)
            .append(new KeyedCodec<>("Id", Codec.STRING), (r, v) -> r.id = v, r -> r.id)
            .documentation("Identifiant unique de la demande (repris par les copies des joueurs).")
            .add()
            .append(new KeyedCodec<>("Template", Codec.STRING), (r, v) -> r.template = v, r -> r.template)
            .documentation("Modèle de demande (RequestTemplate).")
            .add()
            .append(new KeyedCodec<>("Day", Codec.LONG), (r, v) -> r.day = v == null ? 0L : v, r -> r.day)
            .documentation("Jour de jeu du tirage (GameClock.day).")
            .add()
            .build();

    String id = "";
    String template = "";
    long day;

    VillageRequest() {
    }

    public VillageRequest(String id, String template, long day) {
        this.id = id;
        this.template = template;
        this.day = day;
    }

    public String id() {
        return id;
    }

    public String templateId() {
        return template;
    }

    /** Modèle de la demande, ou null s'il a disparu des assets. */
    public RequestTemplate template() {
        return RequestTemplate.get(template);
    }

    public long day() {
        return day;
    }

    public VillageRequest copy() {
        return new VillageRequest(id, template, day);
    }
}
