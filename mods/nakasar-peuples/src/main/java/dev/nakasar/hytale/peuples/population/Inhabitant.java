package dev.nakasar.hytale.peuples.population;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.codec.codecs.array.ArrayCodec;
import com.hypixel.hytale.server.core.Message;

/**
 * Un habitant d'un village (générations de villageois, Kevin, 16 novembre 2026) : sa fiche est sauvegardée avec le
 * village ({@link PopulationState}) ; le PNJ qui le montre reste non sauvegardé et lit sa fiche pour savoir qui il est.
 * Un mort garde une fiche réduite (nom, dates, métier, cause, tombe) pour la chronique et le cimetière.
 */
public final class Inhabitant {

    public static final long NONE = Long.MIN_VALUE;

    public static final BuilderCodec<Inhabitant> CODEC = BuilderCodec.builder(Inhabitant.class, Inhabitant::new)
            .append(new KeyedCodec<>("Id", Codec.STRING), (h, s) -> h.id = s, h -> h.id).add()
            .append(new KeyedCodec<>("Given", Codec.STRING), (h, s) -> h.given = s == null ? "" : s, h -> h.given)
            .documentation("Prénom tiré de la réserve du peuple (Names), vide pour un fondateur nommé par NameKey.")
            .add()
            .append(new KeyedCodec<>("NameKey", Codec.STRING), (h, s) -> h.nameKey = s, h -> h.nameKey)
            .documentation("Clé de langue du prénom d'un fondateur (le nom du villageois à métier d'avant les générations).")
            .add()
            .append(new KeyedCodec<>("Family", Codec.STRING), (h, s) -> h.family = s == null ? "" : s, h -> h.family)
            .documentation("Nom de famille, pris à la naissance chez l'un des deux parents.")
            .add()
            .append(new KeyedCodec<>("Born", Codec.LONG), (h, l) -> h.born = l == null ? 0L : l, h -> h.born)
            .documentation("Jour de jeu de la naissance (GameClock.day), reculé pour un fondateur ou un arrivant adulte.")
            .add()
            .append(new KeyedCodec<>("Parents", new ArrayCodec<>(Codec.STRING, String[]::new)),
                    (h, a) -> h.parents = a == null ? new String[0] : a, h -> h.parents)
            .add()
            .append(new KeyedCodec<>("Home", Codec.STRING), (h, s) -> h.home = s == null ? "" : s, h -> h.home)
            .documentation("Bâtiment du plan où dort l'habitant (son foyer).")
            .add()
            .append(new KeyedCodec<>("Job", Codec.STRING), (h, s) -> h.job = s == null ? "" : s, h -> h.job)
            .documentation("Poste tenu (id VillageLayout.Job, ou @chief, @crier, @merchant), vide s'il n'en tient aucun.")
            .add()
            .append(new KeyedCodec<>("Vocation", Codec.STRING), (h, s) -> h.vocation = s == null ? "" : s, h -> h.vocation)
            .documentation("Métier appris par l'apprenti (id du poste de son maître).")
            .add()
            .append(new KeyedCodec<>("Trait", Codec.STRING), (h, s) -> h.trait = s == null ? Traits.WORKER : s, h -> h.trait).add()
            .append(new KeyedCodec<>("Wounded", Codec.LONG), (h, l) -> h.wounded = l == null ? NONE : l, h -> h.wounded)
            .documentation("Dernier jour de convalescence (blessé en défendant le village), NONE sinon.")
            .add()
            .append(new KeyedCodec<>("Died", Codec.LONG), (h, l) -> h.died = l == null ? NONE : l, h -> h.died)
            .documentation("Jour de la mort, NONE pour un vivant.")
            .add()
            .append(new KeyedCodec<>("Cause", Codec.STRING), (h, s) -> h.cause = s, h -> h.cause)
            .documentation("Cause de la mort : age (vieillesse) ou fire (bâtiment brûlé sur un raid perdu).")
            .add()
            .append(new KeyedCodec<>("DiedJob", Codec.STRING), (h, s) -> h.diedJob = s, h -> h.diedJob)
            .documentation("Dernier métier tenu, gardé pour l'épitaphe.")
            .add()
            .append(new KeyedCodec<>("Godparent", Codec.STRING), (h, s) -> h.godparent = s, h -> h.godparent)
            .documentation("UUID du joueur parrain (il a choisi le prénom), ou absent.")
            .add()
            .append(new KeyedCodec<>("GodparentName", Codec.STRING), (h, s) -> h.godparentName = s, h -> h.godparentName).add()
            .append(new KeyedCodec<>("From", Codec.STRING), (h, s) -> h.from = s, h -> h.from)
            .documentation("Village d'où vient un arrivant, ou absent.")
            .add()
            .append(new KeyedCodec<>("Founder", Codec.BOOLEAN), (h, b) -> h.founder = b != null && b, h -> h.founder).add()
            .append(new KeyedCodec<>("Tomb", new ArrayCodec<>(Codec.INTEGER, Integer[]::new)),
                    (h, a) -> h.tomb = a == null || a.length < 3 ? null : new int[] {a[0], a[1], a[2]},
                    h -> h.tomb == null ? null : new Integer[] {h.tomb[0], h.tomb[1], h.tomb[2]})
            .documentation("Position de la tombe posée au cimetière, absente tant qu'elle n'est pas posée.")
            .add()
            .build();

    String id = "";
    String given = "";
    String nameKey;
    String family = "";
    long born;
    String[] parents = new String[0];
    String home = "";
    String job = "";
    String vocation = "";
    String trait = Traits.WORKER;
    long wounded = NONE;
    long died = NONE;
    String cause;
    String diedJob;
    String godparent;
    String godparentName;
    String from;
    boolean founder;
    int[] tomb;

    Inhabitant() {
    }

    Inhabitant copy() {
        Inhabitant h = new Inhabitant();
        h.id = id;
        h.given = given;
        h.nameKey = nameKey;
        h.family = family;
        h.born = born;
        h.parents = parents.clone();
        h.home = home;
        h.job = job;
        h.vocation = vocation;
        h.trait = trait;
        h.wounded = wounded;
        h.died = died;
        h.cause = cause;
        h.diedJob = diedJob;
        h.godparent = godparent;
        h.godparentName = godparentName;
        h.from = from;
        h.founder = founder;
        h.tomb = tomb == null ? null : tomb.clone();
        return h;
    }

    public String id() {
        return id;
    }

    /** Prénom affiché (traduit pour un fondateur). */
    public Message given() {
        return nameKey != null ? Message.translation(nameKey) : Message.raw(given);
    }

    /** Prénom et nom de famille. */
    public Message fullName() {
        if (family == null || family.isEmpty()) {
            return given();
        }
        return Message.join(given(), Message.raw(" " + family));
    }

    public String family() {
        return family;
    }

    public long born() {
        return born;
    }

    /** Âge en jours de jeu. */
    public long age(long day) {
        return Math.max(0L, (alive() ? day : died) - born);
    }

    public Ages.Stage stage(long day) {
        return Ages.stage(age(day));
    }

    public String[] parents() {
        return parents;
    }

    public String home() {
        return home;
    }

    public String job() {
        return job;
    }

    public boolean hasJob() {
        return job != null && !job.isEmpty();
    }

    public String vocation() {
        return vocation;
    }

    public String trait() {
        return trait;
    }

    public boolean alive() {
        return died == NONE;
    }

    public long died() {
        return died;
    }

    public String cause() {
        return cause;
    }

    public String diedJob() {
        return diedJob;
    }

    /** Vrai le jour de sa blessure et le jour de convalescence qui suit. */
    public boolean convalescent(long day) {
        return wounded != NONE && day <= wounded;
    }

    public String godparent() {
        return godparent;
    }

    public String godparentName() {
        return godparentName;
    }

    public String from() {
        return from;
    }

    public boolean founder() {
        return founder;
    }

    public int[] tomb() {
        return tomb;
    }
}
