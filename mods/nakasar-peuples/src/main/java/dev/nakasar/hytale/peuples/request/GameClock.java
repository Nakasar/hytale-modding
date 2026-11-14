package dev.nakasar.hytale.peuples.request;

import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.modules.time.WorldTimeResource;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.time.LocalDateTime;
import java.time.ZoneOffset;

/**
 * L'horloge de jeu vue par les demandes : le jour commence à {@value #MORNING} h (tirage des demandes du tableau), la
 * nuit va de {@value #DUSK} h à {@value #MORNING} h (défense du village).
 */
public final class GameClock {

    public static final int MORNING = 6;
    public static final int DUSK = 20;
    /** Une demande prise dure au moins ce nombre d'heures de jeu, puis jusqu'au matin suivant. */
    public static final int MIN_HOURS = 12;

    private GameClock() {
    }

    private static LocalDateTime now(Store<EntityStore> store) {
        WorldTimeResource time = store.getResource(WorldTimeResource.getResourceType());
        return time == null ? null : time.getGameDateTime();
    }

    /** Numéro du jour de jeu ; avant {@value #MORNING} h on est encore dans le jour précédent. */
    public static long day(Store<EntityStore> store) {
        LocalDateTime now = now(store);
        return now == null ? 0L : now.minusHours(MORNING).toLocalDate().toEpochDay();
    }

    /** Instant de jeu en secondes. */
    public static long seconds(Store<EntityStore> store) {
        LocalDateTime now = now(store);
        return now == null ? 0L : now.toEpochSecond(ZoneOffset.UTC);
    }

    public static boolean isNight(Store<EntityStore> store) {
        LocalDateTime now = now(store);
        if (now == null) {
            return false;
        }
        int hour = now.getHour();
        return hour >= DUSK || hour < MORNING;
    }

    /** Fin d'une demande prise maintenant : le premier matin au moins {@value #MIN_HOURS} heures plus tard. */
    public static long expiryFromNow(Store<EntityStore> store) {
        LocalDateTime now = now(store);
        if (now == null) {
            return Long.MAX_VALUE;
        }
        LocalDateTime earliest = now.plusHours(MIN_HOURS);
        LocalDateTime morning = earliest.toLocalDate().atTime(MORNING, 0);
        if (morning.isBefore(earliest)) {
            morning = morning.plusDays(1);
        }
        return morning.toEpochSecond(ZoneOffset.UTC);
    }
}
