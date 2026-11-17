package dev.nakasar.hytale.peuples.population;

import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;

/**
 * Une ligne de la chronique du village : un jour, une sorte (clé de langue {@code population.chron.<kind>}), l'habitant
 * concerné, un second habitant (parent, maître, successeur) et un détail (poste, bâtiment, village d'origine).
 */
public final class ChronicleEntry {

    public static final BuilderCodec<ChronicleEntry> CODEC = BuilderCodec.builder(ChronicleEntry.class, ChronicleEntry::new)
            .append(new KeyedCodec<>("Day", Codec.LONG), (e, l) -> e.day = l == null ? 0L : l, e -> e.day).add()
            .append(new KeyedCodec<>("Kind", Codec.STRING), (e, s) -> e.kind = s, e -> e.kind).add()
            .append(new KeyedCodec<>("Who", Codec.STRING), (e, s) -> e.who = s, e -> e.who).add()
            .append(new KeyedCodec<>("Other", Codec.STRING), (e, s) -> e.other = s, e -> e.other).add()
            .append(new KeyedCodec<>("Detail", Codec.STRING), (e, s) -> e.detail = s, e -> e.detail).add()
            .build();

    long day;
    String kind = "";
    String who;
    String other;
    String detail;

    ChronicleEntry() {
    }

    ChronicleEntry(long day, String kind, String who, String other, String detail) {
        this.day = day;
        this.kind = kind;
        this.who = who;
        this.other = other;
        this.detail = detail;
    }

    ChronicleEntry copy() {
        return new ChronicleEntry(day, kind, who, other, detail);
    }

    public long day() {
        return day;
    }

    public String kind() {
        return kind;
    }

    public String who() {
        return who;
    }

    public String other() {
        return other;
    }

    public String detail() {
        return detail;
    }
}
