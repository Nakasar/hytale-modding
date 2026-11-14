package dev.nakasar.hytale.peuples;

import com.hypixel.hytale.assetstore.map.DefaultAssetMap;
import com.hypixel.hytale.server.core.asset.HytaleAssetStore;
import com.hypixel.hytale.server.core.modules.interaction.interaction.config.Interaction;
import com.hypixel.hytale.server.core.plugin.JavaPlugin;
import com.hypixel.hytale.server.core.plugin.JavaPluginInit;
import dev.nakasar.hytale.peuples.command.VillageCommand;
import dev.nakasar.hytale.peuples.dialogue.Dialogue;
import dev.nakasar.hytale.peuples.dialogue.Dialogues;
import dev.nakasar.hytale.peuples.player.PeuplesPlayer;
import dev.nakasar.hytale.peuples.village.OpenBoardInteraction;
import dev.nakasar.hytale.peuples.village.VillageEntrySystem;
import dev.nakasar.hytale.peuples.village.VillageLayout;
import dev.nakasar.hytale.peuples.village.VillageNoRegenSystem;
import dev.nakasar.hytale.peuples.village.VillageRegistry;
import dev.nakasar.hytale.peuples.village.VillageSeeder;
import dev.nakasar.hytale.peuples.village.Villages;

/**
 * Point d'entrée du mod « Peuples d'Orbis » : des villages vivants des peuples d'Orbis qui grandissent avec l'aide du
 * joueur (GDD : https://claude.ai/artifact/FJ15VjWp3pgnt9kmRWjfV7, résumé dans docs/peuples/gdd.md).
 *
 * <p>Étape 1, le socle :
 * <ul>
 *   <li>les villages d'un monde ({@link VillageRegistry}, ressource sauvegardée avec le monde), ancrés sur le bloc cœur
 *       invisible {@value Villages#HEART_BLOCK}, avec un dépôt (coffre vanilla du peuple) et un tableau (panneau vanilla
 *       du peuple, interaction {@value OpenBoardInteraction#TYPE_ID} qui ouvre la page vanilla BlockLore remplie par
 *       le Java) ;</li>
 *   <li>les dialogues, assets JSON {@code Server/}{@value Dialogue#PATH} (conditions et effets par codec), menés dans
 *       la fenêtre du mod ({@code DialoguePage}, mise en page .ui du pack) ou par le tchat ;</li>
 *   <li>l'état du joueur ({@link PeuplesPlayer} : drapeaux de dialogue), sauvegardé avec lui ;</li>
 *   <li>la commande de test {@code /village}.</li>
 * </ul>
 * Étape 2, le premier village :
 * <ul>
 *   <li>les plans de village, assets JSON {@code Server/}{@value VillageLayout#PATH} (prefabs vanilla autour du cœur,
 *       générés par {@code tools/generate_village_layouts.py}), bâtis par {@code VillageBuilder} ;</li>
 *   <li>{@link VillageSeeder} : un village kweebec posé tout seul près du point d'apparition du monde par défaut ;</li>
 *   <li>{@link VillageEntrySystem} : titre d'écran à l'entrée d'un village, bannière de carte révélée à l'approche ;</li>
 *   <li>{@link VillageNoRegenSystem} : les Kweebecs des prefabs ne se régénèrent pas (règle permanente, AGENTS.md).</li>
 * </ul>
 */
public final class PeuplesPlugin extends JavaPlugin {

    private static PeuplesPlugin instance;

    public PeuplesPlugin(JavaPluginInit init) {
        super(init);
        instance = this;
    }

    public static PeuplesPlugin get() {
        return instance;
    }

    @Override
    protected void setup() {
        // Les dialogues : un magasin d'assets comme les rangs de réputation vanilla (ReputationPlugin).
        getAssetRegistry().register(HytaleAssetStore.builder(Dialogue.class, new DefaultAssetMap<String, Dialogue>())
                .setPath(Dialogue.PATH)
                .setCodec(Dialogue.CODEC)
                .setKeyFunction(Dialogue::getId)
                .build());

        getAssetRegistry().register(HytaleAssetStore.builder(VillageLayout.class, new DefaultAssetMap<String, VillageLayout>())
                .setPath(VillageLayout.PATH)
                .setCodec(VillageLayout.CODEC)
                .setKeyFunction(VillageLayout::getId)
                .build());

        getCodecRegistry(Interaction.CODEC).register(OpenBoardInteraction.TYPE_ID, OpenBoardInteraction.class, OpenBoardInteraction.CODEC);

        var entities = getEntityStoreRegistry();
        Villages.setResourceType(entities.registerResource(VillageRegistry.class, VillageRegistry.ID, VillageRegistry.CODEC));
        PeuplesPlayer.setComponentType(entities.registerComponent(PeuplesPlayer.class, PeuplesPlayer.ID, PeuplesPlayer.CODEC));
        entities.registerSystem(new VillageSeeder());
        entities.registerSystem(new VillageEntrySystem());
        entities.registerSystem(new VillageNoRegenSystem());

        getCommandRegistry().registerCommand(new VillageCommand());

        getLogger().atInfo().log("Nakasar Peuples : villages (%s), plans (Server/%s), tableau (%s), dialogues (Server/%s), /village enregistrés",
                VillageRegistry.ID, VillageLayout.PATH, OpenBoardInteraction.TYPE_ID, Dialogue.PATH);
    }

    @Override
    protected void shutdown() {
        Dialogues.clearAll();
    }
}
