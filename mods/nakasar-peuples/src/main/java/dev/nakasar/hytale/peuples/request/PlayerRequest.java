package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;

import java.util.UUID;

/**
 * Une demande prise par un joueur, sauvegardée avec lui ({@code PeuplesPlayer}) : sa copie de la demande du tableau,
 * son avancement, et le lieu tiré pour elle (repaire de la chasse, guetteur de la livraison, captif de l'escorte).
 * Elle tient jusqu'au premier matin qui suit sa prise d'au moins {@value GameClock#MIN_HOURS} heures de jeu.
 */
public final class PlayerRequest {

    /** Hauteur du lieu pas encore connue (sa colonne n'était pas chargée au tirage). */
    public static final int NO_Y = Integer.MIN_VALUE;

    public static final BuilderCodec<PlayerRequest> CODEC = BuilderCodec.builder(PlayerRequest.class, PlayerRequest::new)
            .append(new KeyedCodec<>("Id", Codec.STRING), (r, v) -> r.id = v, r -> r.id)
            .documentation("Id de la demande du tableau.")
            .add()
            .append(new KeyedCodec<>("Village", Codec.STRING), (r, v) -> r.village = v, r -> r.village)
            .documentation("Id du village de la demande.")
            .add()
            .append(new KeyedCodec<>("Template", Codec.STRING), (r, v) -> r.template = v, r -> r.template)
            .documentation("Modèle de demande.")
            .add()
            .append(new KeyedCodec<>("Progress", Codec.INTEGER), (r, v) -> r.progress = v == null ? 0 : v, r -> r.progress)
            .documentation("Avancement (objets déposés, morts de la bande).")
            .add()
            .append(new KeyedCodec<>("Expires", Codec.LONG), (r, v) -> r.expires = v == null ? 0L : v, r -> r.expires)
            .documentation("Fin de la demande (secondes de jeu, GameClock.now).")
            .add()
            .append(new KeyedCodec<>("SiteX", Codec.INTEGER), (r, v) -> r.siteX = v == null ? 0 : v, r -> r.siteX).add()
            .append(new KeyedCodec<>("SiteY", Codec.INTEGER), (r, v) -> r.siteY = v == null ? NO_Y : v, r -> r.siteY).add()
            .append(new KeyedCodec<>("SiteZ", Codec.INTEGER), (r, v) -> r.siteZ = v == null ? 0 : v, r -> r.siteZ).add()
            .append(new KeyedCodec<>("Hud", Codec.STRING), (r, v) -> r.hud = v, r -> r.hud)
            .documentation("Id du suivi à l'écran (paquets d'objectif vanilla).")
            .add()
            .build();

    String id = "";
    String village = "";
    String template = "";
    int progress;
    long expires;
    int siteX;
    int siteY = NO_Y;
    int siteZ;
    String hud;

    PlayerRequest() {
    }

    PlayerRequest(String id, String village, String template, long expires) {
        this.id = id;
        this.village = village;
        this.template = template;
        this.expires = expires;
        this.hud = UUID.randomUUID().toString();
    }

    public String id() {
        return id;
    }

    public String villageId() {
        return village;
    }

    public String templateId() {
        return template;
    }

    public RequestTemplate template() {
        return RequestTemplate.get(template);
    }

    public int progress() {
        return progress;
    }

    void setProgress(int value) {
        progress = Math.max(0, value);
    }

    public long expires() {
        return expires;
    }

    public int[] site() {
        return new int[] {siteX, siteY, siteZ};
    }

    void setSite(int x, int y, int z) {
        siteX = x;
        siteY = y;
        siteZ = z;
    }

    public boolean siteHeightKnown() {
        return siteY != NO_Y;
    }

    /** Uuid du suivi à l'écran (créé au besoin pour une demande d'une ancienne sauvegarde). */
    public UUID hud() {
        if (hud == null) {
            hud = UUID.randomUUID().toString();
        }
        try {
            return UUID.fromString(hud);
        } catch (IllegalArgumentException e) {
            hud = UUID.randomUUID().toString();
            return UUID.fromString(hud);
        }
    }

    public int needed() {
        RequestTemplate t = template();
        return t == null ? 1 : t.needed();
    }

    public boolean complete() {
        return progress >= needed();
    }

    public PlayerRequest copy() {
        PlayerRequest c = new PlayerRequest();
        c.id = id;
        c.village = village;
        c.template = template;
        c.progress = progress;
        c.expires = expires;
        c.siteX = siteX;
        c.siteY = siteY;
        c.siteZ = siteZ;
        c.hud = hud;
        return c;
    }
}
