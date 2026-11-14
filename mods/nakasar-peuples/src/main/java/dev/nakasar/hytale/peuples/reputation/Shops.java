package dev.nakasar.hytale.peuples.reputation;

import com.hypixel.hytale.builtin.adventure.shop.barter.BarterPage;
import com.hypixel.hytale.builtin.adventure.shop.barter.BarterShopAsset;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.Message;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;
import dev.nakasar.hytale.peuples.village.Village;

/**
 * Les échoppes de troc du village (GDD, Récompenses, Par rang ; étape 4) : des boutiques de troc vanilla
 * ({@code Server/BarterShops/Nakasar_Peuples_<Peuple>_<Rang>.json}, payées en faveurs du peuple), ouvertes dans la page
 * vanilla {@link BarterPage} comme le fait l'action PNJ {@code OpenBarterShop} du marchand kweebec. Une échoppe par
 * rang : toléré (troc de base), ami (échoppe avancée), hôte (réserve de l'hôte). Le stock de chacune est partagé par
 * le monde et se renouvelle tous les 3 jours, comme celui du marchand vanilla.
 */
public final class Shops {

    private Shops() {
    }

    /** Rang minimal de l'échoppe `shopId` du village, ou null si ce n'est pas une échoppe de son peuple. */
    public static Rank rankOf(Village village, String shopId) {
        for (Rank rank : Rank.values()) {
            if (shopId != null && shopId.equals(village.people().shop(rank))) {
                return rank;
            }
        }
        return null;
    }

    /** Meilleure échoppe ouverte au rang `rank` dans le village, ou null (étranger, honni). */
    public static String best(Village village, Rank rank) {
        String best = null;
        for (Rank r : Rank.values()) {
            String shop = village.people().shop(r);
            if (shop != null && rank.atLeast(r)) {
                best = shop;
            }
        }
        return best;
    }

    /**
     * Ouvre l'échoppe `shopId` au joueur s'il a le rang voulu dans le village ; sinon lui dit quel rang il faut.
     * Rend vrai si la page s'ouvre. Thread du monde.
     */
    public static boolean open(Store<EntityStore> store, Ref<EntityStore> ref, PlayerRef playerRef, Village village, String shopId) {
        Player player = ref != null && ref.isValid() ? store.getComponent(ref, Player.getComponentType()) : null;
        if (player == null) {
            return false;
        }
        if (shopId == null) {
            playerRef.sendMessage(Message.translation(Reputations.KEYS + "shopClosed")
                    .param("people", Message.translation(village.people().nameKey()))
                    .param("rank", Message.translation(Rank.TOLERE.nameKey())));
            return false;
        }
        Rank needed = rankOf(village, shopId);
        if (needed != null && !Reputations.rank(store, ref, village).atLeast(needed)) {
            playerRef.sendMessage(Message.translation(Reputations.KEYS + "shopClosed")
                    .param("people", Message.translation(village.people().nameKey()))
                    .param("rank", Message.translation(needed.nameKey())));
            return false;
        }
        if (BarterShopAsset.getAssetMap().getAsset(shopId) == null) {
            playerRef.sendMessage(Message.translation(Reputations.KEYS + "shopMissing").param("shop", shopId));
            return false;
        }
        player.getPageManager().openCustomPage(ref, store, new BarterPage(playerRef, shopId));
        return true;
    }
}
