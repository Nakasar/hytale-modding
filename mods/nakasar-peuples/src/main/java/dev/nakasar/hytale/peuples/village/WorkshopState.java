package dev.nakasar.hytale.peuples.village;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;
import dev.nakasar.hytale.peuples.request.VillageRequest;

/**
 * L'état d'un bâtiment de métier dans un village (GDD des bâtiments de métier), sauvegardé avec le village : niveau,
 * jauge de savoir-faire, spécialité, commandes du jour et place de son panneau. Comme {@link RaidRecord}, c'est l'objet
 * sauvegardé lui-même, modifiable sur le thread du monde ({@code dev.nakasar.hytale.peuples.workshop.Workshops}).
 */
public final class WorkshopState {

    public static final BuilderCodec<WorkshopState> CODEC = BuilderCodec.builder(WorkshopState.class, WorkshopState::new)
            .append(new KeyedCodec<>("Id", Codec.STRING), (w, v) -> w.id = v == null ? "" : v, w -> w.id)
            .documentation("Bâtiment de métier (asset Workshop).")
            .add()
            .append(new KeyedCodec<>("Level", Codec.INTEGER), (w, v) -> w.level = v == null ? 1 : Math.max(1, Math.min(3, v)), w -> w.level)
            .documentation("Niveau du bâtiment : 1 ouvert, 2 établi, 3 renommé.")
            .add()
            .append(new KeyedCodec<>("Knowledge", Codec.INTEGER), (w, v) -> w.knowledge = v == null ? 0 : Math.max(0, v), w -> w.knowledge)
            .documentation("Savoir-faire vers le niveau suivant, partagé par tous les joueurs.")
            .add()
            .append(new KeyedCodec<>("Specialty", Codec.STRING), (w, v) -> w.specialty = v == null || v.isBlank() ? null : v, w -> w.specialty)
            .documentation("Spécialité choisie au niveau II, ou absente.")
            .add()
            .append(new KeyedCodec<>("Requests", new ArrayCodec<>(VillageRequest.CODEC, VillageRequest[]::new)),
                    (w, a) -> w.requests = a == null ? new VillageRequest[0] : a, w -> w.requests)
            .documentation("Commandes du jour (2, 3 au niveau III).")
            .add()
            .append(new KeyedCodec<>("RequestDay", Codec.LONG), (w, l) -> w.requestDay = l == null ? Long.MIN_VALUE : l, w -> w.requestDay)
            .documentation("Jour de jeu du dernier tirage des commandes.")
            .add()
            .append(new KeyedCodec<>("Board", Codec.BOOLEAN), (w, b) -> w.board = b != null && b, w -> w.board)
            .documentation("Vrai si le panneau du bâtiment est posé en BoardX/Y/Z.")
            .add()
            .append(new KeyedCodec<>("BoardX", Codec.INTEGER), (w, i) -> w.boardX = i == null ? 0 : i, w -> w.boardX).add()
            .append(new KeyedCodec<>("BoardY", Codec.INTEGER), (w, i) -> w.boardY = i == null ? 0 : i, w -> w.boardY).add()
            .append(new KeyedCodec<>("BoardZ", Codec.INTEGER), (w, i) -> w.boardZ = i == null ? 0 : i, w -> w.boardZ).add()
            .append(new KeyedCodec<>("Master", Codec.BOOLEAN), (w, b) -> w.master = b != null && b, w -> w.master)
            .documentation("Vrai si la commande de maître du niveau en cours est remplie.")
            .add()
            .append(new KeyedCodec<>("UpgradeStart", Codec.LONG), (w, l) -> w.upgradeStart = l == null ? 0L : l, w -> w.upgradeStart)
            .documentation("Début du chantier d'amélioration (secondes de jeu, GameClock.seconds), 0 : aucun.")
            .add()
            .append(new KeyedCodec<>("UpgradeEnd", Codec.LONG), (w, l) -> w.upgradeEnd = l == null ? 0L : l, w -> w.upgradeEnd)
            .documentation("Fin du chantier d'amélioration (secondes de jeu), 0 : aucun.")
            .add()
            .append(new KeyedCodec<>("Reconverted", Codec.LONG), (w, l) -> w.reconverted = l == null ? Long.MIN_VALUE : l, w -> w.reconverted)
            .documentation("Jour de jeu du dernier choix ou changement de spécialité.")
            .add()
            .append(new KeyedCodec<>("Round", Codec.INTEGER), (w, i) -> w.round = i == null ? 0 : i, w -> w.round)
            .documentation("Nombre de reconversions : rend unique l'id de la commande de maître à refaire.")
            .add()
            .append(new KeyedCodec<>("ShareDay", Codec.LONG), (w, l) -> w.shareDay = l == null ? Long.MIN_VALUE : l, w -> w.shareDay)
            .documentation("Jour de jeu du lot de la Part de l'Hôte en cours.")
            .add()
            .append(new KeyedCodec<>("ShareTaken", Codec.STRING_ARRAY), (w, a) -> w.shareTaken = a == null ? new String[0] : a, w -> w.shareTaken)
            .documentation("Joueurs (UUID) qui ont déjà pris leur lot du jour.")
            .add()
            .build();

    String id = "";
    int level = 1;
    int knowledge;
    String specialty;
    VillageRequest[] requests = new VillageRequest[0];
    long requestDay = Long.MIN_VALUE;
    boolean board;
    int boardX;
    int boardY;
    int boardZ;
    boolean master;
    long upgradeStart;
    long upgradeEnd;
    long reconverted = Long.MIN_VALUE;
    int round;
    long shareDay = Long.MIN_VALUE;
    String[] shareTaken = new String[0];

    WorkshopState() {
    }

    WorkshopState(String id) {
        this.id = id;
    }

    WorkshopState copy() {
        WorkshopState w = new WorkshopState(id);
        w.level = level;
        w.knowledge = knowledge;
        w.specialty = specialty;
        w.requests = new VillageRequest[requests.length];
        for (int i = 0; i < requests.length; i++) {
            w.requests[i] = requests[i] == null ? null : requests[i].copy();
        }
        w.requestDay = requestDay;
        w.board = board;
        w.boardX = boardX;
        w.boardY = boardY;
        w.boardZ = boardZ;
        w.master = master;
        w.upgradeStart = upgradeStart;
        w.upgradeEnd = upgradeEnd;
        w.reconverted = reconverted;
        w.round = round;
        return w;
    }

    public String id() {
        return id;
    }

    public int level() {
        return level;
    }

    public void setLevel(int value) {
        level = Math.max(1, Math.min(3, value));
    }

    public int knowledge() {
        return knowledge;
    }

    public void setKnowledge(int value) {
        knowledge = Math.max(0, value);
    }

    /** Spécialité, ou null. */
    public String specialty() {
        return specialty;
    }

    public void setSpecialty(String value) {
        specialty = value == null || value.isBlank() ? null : value;
    }

    /** Commandes du jour (copie ; les cases vides sont null). */
    public VillageRequest[] requests() {
        return requests.clone();
    }

    public long requestDay() {
        return requestDay;
    }

    public void setRequests(VillageRequest[] value, long day) {
        requests = value == null ? new VillageRequest[0] : value.clone();
        requestDay = day;
    }

    public void setRequest(int slot, VillageRequest request) {
        if (slot >= 0 && slot < requests.length) {
            requests[slot] = request;
        }
    }

    /** Case de la commande `requestId`, ou -1. */
    public int slotOf(String requestId) {
        for (int i = 0; i < requests.length; i++) {
            if (requests[i] != null && requests[i].id().equals(requestId)) {
                return i;
            }
        }
        return -1;
    }

    public boolean hasBoard() {
        return board;
    }

    /** {@code [x, y, z]} du panneau. */
    public int[] board() {
        return new int[] {boardX, boardY, boardZ};
    }

    public boolean isBoard(int x, int y, int z) {
        return board && boardX == x && boardY == y && boardZ == z;
    }

    public void setBoard(int x, int y, int z) {
        board = true;
        boardX = x;
        boardY = y;
        boardZ = z;
    }

    public void clearBoard() {
        board = false;
    }

    /** La commande de maître du niveau en cours est remplie. */
    public boolean masterDone() {
        return master;
    }

    public void setMasterDone(boolean value) {
        master = value;
    }

    /** Vrai pendant le chantier d'amélioration. */
    public boolean upgrading() {
        // Les secondes de jeu (GameClock.seconds) sont NÉGATIVES : l'horloge vanilla part de l'an 1 (WorldTimeResource.ZERO_YEAR),
        // avant l'époque Unix. Seul 0 veut dire « aucun » (bug du 2026-11-15 : « > 0 » rendait tout chantier invisible).
        return upgradeEnd != 0L;
    }

    public long upgradeStart() {
        return upgradeStart;
    }

    public long upgradeEnd() {
        return upgradeEnd;
    }

    public void startUpgrade(long start, long end) {
        upgradeStart = start;
        upgradeEnd = end;
    }

    public void clearUpgrade() {
        upgradeStart = 0L;
        upgradeEnd = 0L;
    }

    /** Jour du dernier choix de spécialité (Long.MIN_VALUE : jamais). */
    public long reconverted() {
        return reconverted;
    }

    public void setReconverted(long day) {
        reconverted = day;
    }

    public int round() {
        return round;
    }

    public void nextRound() {
        round++;
    }

    /** Vrai si le joueur `uuid` a déjà pris le lot de la Part de l'Hôte du jour `day`. */
    public boolean shareTaken(long day, String uuid) {
        if (shareDay != day) {
            return false;
        }
        for (String t : shareTaken) {
            if (t.equals(uuid)) {
                return true;
            }
        }
        return false;
    }

    /** Le joueur `uuid` prend le lot du jour `day` (la liste repart à zéro chaque matin). */
    public void takeShare(long day, String uuid) {
        if (shareDay != day) {
            shareDay = day;
            shareTaken = new String[0];
        }
        String[] next = java.util.Arrays.copyOf(shareTaken, shareTaken.length + 1);
        next[shareTaken.length] = uuid;
        shareTaken = next;
    }
}
