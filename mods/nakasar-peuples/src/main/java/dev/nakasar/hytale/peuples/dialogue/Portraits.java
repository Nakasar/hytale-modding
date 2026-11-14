package dev.nakasar.hytale.peuples.dialogue;

import com.hypixel.hytale.component.Ref;
import com.hypixel.hytale.component.Store;
import com.hypixel.hytale.server.core.modules.entity.component.ModelComponent;
import com.hypixel.hytale.server.core.universe.world.storage.EntityStore;

import java.util.Set;

/**
 * Portrait du PNJ dans la fenêtre de dialogue : tête et buste recadrés dans le rendu vanilla de son modèle
 * (Common/Icons/ModelsGenerated, celui des Souvenirs), livrés par le pack sous {@value #DIR} par
 * tools/generate_portraits.py. Une variante sans rendu vanilla (Kweebec_Sapling_Pink) prend celui du plus long préfixe
 * connu (Kweebec_Sapling) ; un modèle sans aucun rendu (Klops_Merchant) n'a pas de portrait.
 */
public final class Portraits {

    /** Chemin des portraits pour un AssetImage (.AssetPath), relatif à Common/ comme celui de la page des Souvenirs. */
    public static final String DIR = "Icons/Nakasar/Peuples/Portraits/";

    private static final Set<String> KNOWN = Set.of(
        // GENERATED BEGIN (tools/generate_portraits.py)
            "Feran_Burrower",
            "Feran_Civilian",
            "Feran_Cub",
            "Feran_Longtooth",
            "Feran_Sharptooth",
            "Feran_Windwalker",
            "Goblin_Burner",
            "Goblin_Duke",
            "Goblin_Feastmaster",
            "Goblin_Glutton",
            "Goblin_Gobliterator",
            "Goblin_Guardian",
            "Goblin_Lobber",
            "Goblin_Miner",
            "Goblin_Scientist",
            "Goblin_Scrapper",
            "Goblin_Thief",
            "Goblin_Turret",
            "Kweebec_Rootling",
            "Kweebec_Sapling",
            "Kweebec_Seedling",
            "Kweebec_Sproutling",
            "Outlander_Berserker",
            "Outlander_Brute",
            "Outlander_Cultist",
            "Outlander_Hunter",
            "Outlander_Marauder",
            "Outlander_Peon",
            "Outlander_Priest",
            "Outlander_Sorcerer",
            "Outlander_Stalker",
            "Scarak_Broodmother",
            "Scarak_Broodmother_Young",
            "Scarak_Defender",
            "Scarak_Fighter",
            "Scarak_Louse",
            "Scarak_Seeker",
            "Trork_Brawler",
            "Trork_Chieftain",
            "Trork_Doctor_Witch",
            "Trork_Guard",
            "Trork_Hunter",
            "Trork_Mauler",
            "Trork_Sentry",
            "Trork_Shaman",
            "Trork_Warrior"
        // GENERATED END
    );

    private Portraits() {
    }

    /** Portrait du modèle `modelId` (ou de son plus long préfixe connu, coupé aux « _ »), null s'il n'y en a pas. */
    public static String forModel(String modelId) {
        String id = modelId;
        while (id != null && !id.isEmpty()) {
            if (KNOWN.contains(id)) {
                return DIR + id + ".png";
            }
            int cut = id.lastIndexOf('_');
            id = cut <= 0 ? null : id.substring(0, cut);
        }
        return null;
    }

    /** Portrait de l'entité `npc` d'après son modèle, null si elle n'en a pas (ou plus). */
    public static String of(Store<EntityStore> store, Ref<EntityStore> npc) {
        if (npc == null || !npc.isValid()) {
            return null;
        }
        ModelComponent model = store.getComponent(npc, ModelComponent.getComponentType());
        return model == null || model.getModel() == null ? null : forModel(model.getModel().getModelAssetId());
    }
}
