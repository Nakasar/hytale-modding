package dev.nakasar.hytale.fractals.observatory;

import com.hypixel.hytale.builtin.adventure.shop.barter.BarterPage;
import com.hypixel.hytale.codec.Codec;
import com.hypixel.hytale.codec.KeyedCodec;
import com.hypixel.hytale.codec.builder.BuilderCodec;
import com.hypixel.hytale.component.CommandBuffer;
import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.server.core.entity.entities.Player;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.SimpleInstantInteraction;
import com.hypixel.hytale.server.core.universe.PlayerRef;
import com.hypixel.hytale.server.core.universe.world.World;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

/**
 * {@code "Type": "Nakasar_Fractal_OpenShop"} : comptoir de l'Archiviste. Ouvre la boutique de troc {@code Shop}
 * ({@code Server/BarterShops}), comme lui parler (action de PNJ {@code OpenBarterShop}) : le comptoir reste utilisable
 * si le PNJ manque.
 */
public class OpenShopInteraction extends PlayerInteraction {

    public static final String TYPE_ID = "Nakasar_Fractal_OpenShop";

    public static final BuilderCodec<OpenShopInteraction> CODEC = BuilderCodec
            .builder(OpenShopInteraction.class, OpenShopInteraction::new, SimpleInstantInteraction.CODEC)
            .documentation("Ouvre une boutique de troc.")
            .append(new KeyedCodec<>("Shop", Codec.STRING), (i, v) -> i.shop = v, i -> i.shop)
            .documentation("Id de la boutique de troc (Server/BarterShops).")
            .add()
            .build();

    protected String shop;

    @Override
    protected void use(CommandBuffer<EntityStore> buffer, Ref<EntityStore> player, PlayerRef playerRef, World world) {
        if (shop == null) {
            return;
        }
        buffer.run(store -> {
            Player playerComponent = player.isValid() ? store.getComponent(player, Player.getComponentType()) : null;
            if (playerComponent != null) {
                playerComponent.getPageManager().openCustomPage(player, store, new BarterPage(playerRef, shop));
            }
        });
    }
}
