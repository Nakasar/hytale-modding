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
            .append(new KeyedCodec<>("Prepared", Codec.BOOLEAN), (r, v) -> r.prepared = v != null && v, r -> r.prepared)
            .documentation("Vrai quand le lieu de la demande a été préparé (bosquet brûlé d'une plantation).")
            .add()
            .append(new KeyedCodec<>("Target", Codec.STRING), (r, v) -> r.target = v, r -> r.target)
            .documentation("Caravane : id du village où mener la caravane.")
            .add()
            .append(new KeyedCodec<>("Stage", Codec.INTEGER), (r, v) -> r.stage = v == null ? 0 : v, r -> r.stage)
            .documentation("Caravane : embuscades passées ; récolte escortée : 0 aller, 1 récolte, 2 retour ; destruction : blocs posés.")
            .add()
            .append(new KeyedCodec<>("Count", Codec.INTEGER), (r, v) -> r.count = v == null ? -1 : v, r -> r.count)
            .documentation("Caravane, récolte : PNJ escortés encore en vie (-1 : pas encore partis) ; boss : vie en millièmes.")
            .add()
            .append(new KeyedCodec<>("Timer", Codec.INTEGER), (r, v) -> r.timer = v == null ? 0 : v, r -> r.timer)
            .documentation("Récolte escortée : secondes de récolte écoulées.")
            .add()
            .append(new KeyedCodec<>("WavesDone", Codec.INTEGER), (r, v) -> r.wavesDone = v == null ? 0 : v, r -> r.wavesDone)
            .documentation("Caravane, récolte escortée : embuscades déjà lancées.")
            .add()
            .append(new KeyedCodec<>("Marks", Codec.STRING), (r, v) -> r.marks = v, r -> r.marks)
            .documentation("Destruction : blocs posés au lieu, « x,y,z;x,y,z ».")
            .add()
            .append(new KeyedCodec<>("PosX", Codec.INTEGER), (r, v) -> r.posX = v == null ? 0 : v, r -> r.posX).add()
            .append(new KeyedCodec<>("PosY", Codec.INTEGER), (r, v) -> r.posY = v == null ? NO_Y : v, r -> r.posY).add()
            .append(new KeyedCodec<>("PosZ", Codec.INTEGER), (r, v) -> r.posZ = v == null ? 0 : v, r -> r.posZ).add()
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
    boolean prepared;
    String target;
    int stage;
    int count = -1;
    int timer;
    int wavesDone;
    String marks;
    int posX;
    int posY = NO_Y;
    int posZ;

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

    public boolean prepared() {
        return prepared;
    }

    public void setPrepared(boolean value) {
        prepared = value;
    }

    public boolean complete() {
        return progress >= needed();
    }

    /** Caravane : village de destination, ou null. */
    public String target() {
        return target;
    }

    void setTarget(String value) {
        target = value;
    }

    public int stage() {
        return stage;
    }

    void setStage(int value) {
        stage = value;
    }

    public int count() {
        return count;
    }

    void setCount(int value) {
        count = value;
    }

    public int timer() {
        return timer;
    }

    void setTimer(int value) {
        timer = value;
    }

    /** Destruction : positions des blocs posés (x, y, z). */
    public java.util.List<int[]> marks() {
        java.util.List<int[]> out = new java.util.ArrayList<>();
        if (marks == null || marks.isBlank()) {
            return out;
        }
        for (String part : marks.split(";")) {
            String[] c = part.split(",");
            if (c.length == 3) {
                try {
                    out.add(new int[] {Integer.parseInt(c[0].trim()), Integer.parseInt(c[1].trim()), Integer.parseInt(c[2].trim())});
                } catch (NumberFormatException ignored) {
                    // entrée abîmée : ignorée
                }
            }
        }
        return out;
    }

    void addMark(int x, int y, int z) {
        String m = x + "," + y + "," + z;
        marks = marks == null || marks.isBlank() ? m : marks + ";" + m;
    }

    public int wavesDone() {
        return wavesDone;
    }

    void setWavesDone(int value) {
        wavesDone = value;
    }

    /** Dernière position connue du groupe escorté, ou null. */
    public int[] position() {
        return posY == NO_Y ? null : new int[] {posX, posY, posZ};
    }

    void setPosition(int x, int y, int z) {
        posX = x;
        posY = y;
        posZ = z;
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
        c.prepared = prepared;
        c.target = target;
        c.stage = stage;
        c.count = count;
        c.timer = timer;
        c.wavesDone = wavesDone;
        c.marks = marks;
        c.posX = posX;
        c.posY = posY;
        c.posZ = posZ;
        return c;
    }
}
