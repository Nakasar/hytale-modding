package dev.nakasar.hytale.peuples.village;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Le chantier de chaque peuple, selon ses techniques (retours de Kevin du 15 novembre 2026 : les échafaudages étaient
 * provisoires). Autour de l'emprise d'un grand bâtiment en travaux, un anneau d'un bloc évolue en {@value #PHASES}
 * phases sur la durée du chantier (préparation, montée, charpente, finitions) :
 * <ul>
 *   <li>Kweebecs : on fait pousser la maison. Un jardin se sème, des troncs de chêne couverts de lierre montent aux
 *   angles, une guirlande de feuillage les relie et des lianes en pendent, puis des lanternes à des cordes.</li>
 *   <li>Trorks : une palissade de rondins de hêtre, des auvents de cuir aux angles, des os, des crânes et des torches.</li>
 *   <li>Feran : des briques de grès sèchent au soleil puis montent en murets, des toiles de peau tendues sur des
 *   poteaux de bois sec font de l'ombre aux angles.</li>
 *   <li>Renoncés : un vrai échafaudage d'Outlanders, poteaux de sapin et deux passerelles de bois mort, chaînes, cairns
 *   de schiste.</li>
 *   <li>Slothians : de hautes cannes de bambou qui dépassent le toit, un plancher de bois tropical à mi-hauteur, mousse
 *   et lianes.</li>
 * </ul>
 * Tout est en blocs vanilla, repris des prefabs vanilla de chaque peuple (Npc/Kweebec, Npc/Trork, Npc/Feran,
 * Npc/Outlander, Npc/Slothian dans Assets.zip 0.7.2). Le plan est une fonction pure de l'emprise et de la phase : on
 * peut le reposer après un redémarrage, et l'enlever en ne retirant que nos propres blocs.
 */
public final class SiteStyle {

    /** Nombre de phases d'un chantier. */
    public static final int PHASES = 4;
    /** Hauteur de référence des chantiers (bornée, comme l'ancien échafaudage). */
    static final int MIN_HEIGHT = 5;
    static final int MAX_HEIGHT = 12;

    private SiteStyle() {
    }

    /** Un bloc du plan : id, rotation (quart de lacet, voir hytale-prefab-rotations) et s'il lui faut un sol plein. */
    public record Placement(String block, int rotation, boolean grounded) {
    }

    /** Clé d'une position du monde dans un plan. */
    public static long key(int x, int y, int z) {
        return ((long) (x & 0x3FFFFFF) << 38) | ((long) (z & 0x3FFFFFF) << 12) | (y & 0xFFF);
    }

    public static int keyX(long key) {
        return (int) (key >> 38) << 6 >> 6;
    }

    public static int keyZ(long key) {
        return (int) ((key >> 12) & 0x3FFFFFF) << 6 >> 6;
    }

    public static int keyY(long key) {
        return (int) (key & 0xFFF);
    }

    /** Hauteur de référence d'un chantier pour un bâtiment de hauteur `height`. */
    static int fullHeight(int height) {
        return Math.max(MIN_HEIGHT, Math.min(MAX_HEIGHT, height));
    }

    /** Tous les blocs vanilla que les chantiers posent (vérifiés par validateAssets via {@link Burning#REQUIRED_BLOCKS}). */
    public static List<String> allBlocks() {
        Set<String> out = new LinkedHashSet<>();
        for (People people : People.values()) {
            for (int p = 1; p <= PHASES; p++) {
                for (Placement placement : plan(people, 0, 10, 0, 8, 0, 12, p).values()) {
                    out.add(placement.block());
                }
            }
        }
        return List.copyOf(out);
    }

    /**
     * Pour chaque position touchée par un chantier, à n'importe quelle phase, les ids que nous y posons : seuls ces
     * blocs-là sont remplacés ou retirés ensuite (jamais ceux d'un joueur ni le relief).
     */
    public static Map<Long, Set<String>> ours(People people, int x0, int x1, int z0, int z1, int h, int height) {
        Map<Long, Set<String>> out = new HashMap<>();
        for (int p = 1; p <= PHASES; p++) {
            for (Map.Entry<Long, Placement> e : plan(people, x0, x1, z0, z1, h, height, p).entrySet()) {
                out.computeIfAbsent(e.getKey(), k -> new HashSet<>()).add(e.getValue().block());
            }
        }
        return out;
    }

    /**
     * Plan d'un chantier à la phase `phase` (1 à {@value #PHASES} ; 0 ou moins = rien) : positions du monde → bloc.
     * L'anneau entoure d'un bloc l'emprise [x0, x1] x [z0, z1] ; `h` est le sol de la parcelle.
     */
    public static Map<Long, Placement> plan(People people, int x0, int x1, int z0, int z1, int h, int height, int phase) {
        Plan plan = new Plan(x0 - 1, x1 + 1, z0 - 1, z1 + 1, h, fullHeight(height), (x0 + x1) / 2, (z0 + z1) / 2);
        if (phase > 0) {
            switch (people == null ? People.KWEEBEC : people) {
                case TRORK -> trork(plan, phase);
                case FERAN -> feran(plan, phase);
                case RENONCE -> renonce(plan, phase);
                case SLOTHIAN -> slothian(plan, phase);
                default -> kweebec(plan, phase);
            }
        }
        return plan.out;
    }

    // ------------------------------------------------------------------------------------------------ Kweebecs

    private static final String[] KWEEBEC_GARDEN = {"Plant_Flower_Common_Yellow", "Plant_Fern_Forest", "Plant_Flower_Common_Pink",
            "Plant_Moss_Rug_Green", "Plant_Flower_Bushy_Blue", "Plant_Grass_Lush_Tall", "Plant_Moss_Rug_Green", "Plant_Fern_Forest"};
    private static final String[] KWEEBEC_BLOOM = {"Plant_Flower_Tall_Yellow", "Plant_Flower_Tall_Pink", "Plant_Flower_Tall_Blue"};

    /**
     * Kweebecs : 1 semis (fleurs, fougères, mousse sur l'anneau, buissons aux angles) ; 2 troncs de chêne à mi-hauteur
     * aux angles, couverts de lierre, buissons au milieu des côtés ; 3 troncs à pleine hauteur, guirlande de feuillage
     * sur les côtés et touffes aux angles, lianes qui pendent ; 4 grandes fleurs, lanternes kweebec suspendues à des
     * cordes au milieu des côtés (comme dans les prefabs vanilla des villages kweebecs).
     */
    private static void kweebec(Plan p, int phase) {
        int top = p.h + p.full;
        List<int[]> ring = p.ring();
        for (int i = 0; i < ring.size(); i++) {
            int x = ring.get(i)[0];
            int z = ring.get(i)[1];
            if (p.corner(x, z)) {
                if (phase == 1) {
                    p.ground(x, z, "Plant_Bush_Lush");
                } else {
                    int trunk = phase == 2 ? p.full / 2 : p.full;
                    p.column(x, z, p.h + 1, p.h + trunk, "Wood_Oak_Trunk_Full");
                    // Lierre sur les deux faces extérieures du tronc (support « nord » tourné vers le tronc).
                    int[] ox = p.outX(x);
                    int[] oz = p.outZ(z);
                    for (int y = p.h + 1; y < p.h + trunk; y++) {
                        p.put(x + ox[0], y, z, "Plant_Vine", ox[1], false);
                        p.put(x, y, z + oz[0], "Plant_Vine", oz[1], false);
                    }
                }
            } else if (phase >= 2 && p.midSide(x, z)) {
                p.ground(x, z, phase >= 4 ? KWEEBEC_BLOOM[i % KWEEBEC_BLOOM.length] : "Plant_Bush_Lush");
            } else {
                p.ground(x, z, KWEEBEC_GARDEN[i % KWEEBEC_GARDEN.length]);
            }
            if (phase >= 3) {
                if (!p.corner(x, z)) {
                    p.put(x, top, z, "Plant_Leaves_Oak", 0, false);
                    if (i % 2 == 1 && !p.midSide(x, z)) {
                        p.hang(x, top - 1, z, "Plant_Vine_Hanging", "Plant_Vine_Hanging", "Plant_Vine_Hanging");
                    }
                }
                if (p.corner(x, z)) {
                    p.put(x, top + 1, z, "Plant_Leaves_Oak", 0, false);
                    for (int[] d : new int[][] {{1, 0}, {-1, 0}, {0, 1}, {0, -1}}) {
                        p.put(x + d[0], top + 1, z + d[1], "Plant_Leaves_Oak", 0, false);
                    }
                    if (phase >= 4) {
                        p.put(x, top + 2, z, "Plant_Leaves_Oak", 0, false);
                    }
                }
            }
            if (phase >= 4 && p.midSide(x, z)) {
                p.hang(x, top - 1, z, "Deco_Rope", "Furniture_Kweebec_Lantern");
            }
        }
        // Pépinière au centre : de jeunes buissons, épuisés à la fin.
        if (phase <= 3) {
            p.ground(p.cx, p.cz, "Plant_Bush_Green");
            p.ground(p.cx + 1, p.cz, phase <= 2 ? "Plant_Bush_Green" : null);
            p.ground(p.cx, p.cz + 1, phase <= 2 ? "Plant_Flower_Tall_Yellow" : null);
        }
    }

    // ------------------------------------------------------------------------------------------------ Trorks

    /**
     * Trorks : 1 pieux d'os aux angles, tas d'os et de côtes, rondins entassés au centre ; 2 palissade de rondins de
     * hêtre (deux de haut, une ouverture au milieu de chaque côté), angles plus hauts ; 3 angles à mi-hauteur et
     * auvents de cuir tendus de chaque côté des angles, cordes ; 4 crânes sur la palissade, torches grossières aux
     * angles, le tas de rondins est épuisé.
     */
    private static void trork(Plan p, int phase) {
        int cornerH = phase >= 3 ? Math.max(4, p.full / 2 + 1) : 3;
        int awning = p.h + cornerH;
        List<int[]> ring = p.ring();
        for (int i = 0; i < ring.size(); i++) {
            int x = ring.get(i)[0];
            int z = ring.get(i)[1];
            boolean corner = p.corner(x, z);
            boolean gate = p.midSide(x, z);
            if (phase == 1) {
                if (corner) {
                    p.ground(x, z, "Deco_Bone_Spike_Large");
                } else if (i % 3 == 0) {
                    p.ground(x, z, i % 2 == 0 ? "Deco_Bone_Pile" : "Deco_Bone_Ribs_Long");
                }
                continue;
            }
            if (corner) {
                p.column(x, z, p.h + 1, p.h + cornerH, "Wood_Beech_Trunk_Full");
                if (phase >= 4) {
                    p.put(x, p.h + cornerH + 1, z, "Furniture_Crude_Torch", 0, false);
                }
            } else if (!gate) {
                p.column(x, z, p.h + 1, p.h + 2, "Wood_Beech_Trunk");
                if (phase >= 4 && i % 4 == 2) {
                    p.put(x, p.h + 3, z, "Deco_Bone_Skulls", 0, false);
                }
            } else if (phase >= 4) {
                p.ground(x, z, "Deco_Bone_Spike");
            }
            if (phase >= 3 && !corner && p.nearCorner(x, z, 2)) {
                p.put(x, awning, z, "Cloth_Roof_Leather_Flat", 0, false);
                if (p.nearCorner(x, z, 1)) {
                    p.put(x, awning - 1, z, "Deco_Rope", 0, false);
                }
            }
        }
        if (phase <= 3) {
            p.pile(phase <= 2 ? 2 : 1, phase <= 2, "Wood_Beech_Trunk", "Wood_Beech_Trunk");
            if (phase <= 2) {
                p.ground(p.cx - 1, p.cz, "Furniture_Village_Crate");
            }
        }
    }

    // ------------------------------------------------------------------------------------------------ Feran

    /**
     * Feran : 1 briques de grès qui sèchent au sol, poteries aux angles, argile entassée au centre ; 2 premier rang de
     * briques (ouverture au milieu de chaque côté), poteaux de bois sec aux angles ; 3 deuxième rang en demi-briques,
     * poteaux plus hauts et toiles de peau tendues en ombrière sur les angles, cordes ; 4 torches feran de part et
     * d'autre des ouvertures, poteries, l'argile est épuisée.
     */
    private static void feran(Plan p, int phase) {
        int postH = phase >= 3 ? Math.max(4, p.full / 2 + 1) : 3;
        int shade = p.h + postH + 1;
        List<int[]> ring = p.ring();
        for (int i = 0; i < ring.size(); i++) {
            int x = ring.get(i)[0];
            int z = ring.get(i)[1];
            boolean corner = p.corner(x, z);
            boolean gate = p.midSide(x, z);
            if (phase == 1) {
                p.ground(x, z, corner ? "Furniture_Village_Pot" : i % 2 == 0 ? "Rock_Sandstone_Brick_Half" : null);
                continue;
            }
            if (corner) {
                p.column(x, z, p.h + 1, p.h + postH, "Wood_Dry_Trunk");
            } else if (!gate) {
                p.put(x, p.h + 1, z, "Rock_Sandstone_Brick", 0, false);
                if (phase >= 4 && p.besideGate(x, z)) {
                    p.put(x, p.h + 2, z, "Furniture_Feran_Torch", 0, false);
                } else if (phase >= 3) {
                    p.put(x, p.h + 2, z, "Rock_Sandstone_Brick_Half", 0, false);
                }
            } else if (phase >= 4) {
                p.ground(x, z, "Furniture_Feran_Pot_Secondary");
            }
            if (phase >= 3 && p.nearCorner(x, z, 2)) {
                p.put(x, shade, z, "Cloth_Roof_Hide_Flat", 0, false);
                if (!corner && p.nearCorner(x, z, 1)) {
                    p.put(x, shade - 1, z, "Deco_Rope", 0, false);
                }
            }
        }
        if (phase <= 3) {
            p.pile(phase <= 2 ? 2 : 1, phase <= 2, "Soil_Clay", "Rock_Sandstone_Brick");
            if (phase <= 2) {
                p.ground(p.cx - 1, p.cz, "Furniture_Village_Pot");
            }
        }
    }

    // ------------------------------------------------------------------------------------------------ Renoncés

    /**
     * Renoncés : 1 cairns de schiste aux angles, demi-pavés de schiste, rondins de sapin et caisse au centre ; 2
     * poteaux de sapin tous les 4 blocs à mi-hauteur et première passerelle de planches de bois mort ; 3 poteaux à
     * pleine hauteur, seconde passerelle, chaînes qui pendent ; 4 torches aux angles de la passerelle haute, le bois
     * est épuisé.
     */
    private static void renonce(Plan p, int phase) {
        int low = p.h + Math.max(3, p.full / 2);
        int high = p.h + p.full;
        List<int[]> ring = p.ring();
        for (int i = 0; i < ring.size(); i++) {
            int x = ring.get(i)[0];
            int z = ring.get(i)[1];
            boolean corner = p.corner(x, z);
            boolean post = p.post(x, z, 4);
            if (phase == 1) {
                if (corner) {
                    p.column(x, z, p.h + 1, p.h + 2, "Rock_Shale_Cobble");
                } else if (i % 3 == 0) {
                    p.ground(x, z, "Rock_Shale_Cobble_Half");
                }
                continue;
            }
            if (post) {
                p.column(x, z, p.h + 1, phase >= 3 ? high - 1 : low - 1, "Wood_Fir_Trunk");
            } else if (i % 3 == 0) {
                p.ground(x, z, "Rock_Shale_Cobble_Half");
            }
            p.put(x, low, z, "Wood_Deadwood_Planks_Half", 0, false);
            if (phase >= 3) {
                p.put(x, high, z, "Wood_Deadwood_Planks_Half", 0, false);
                if (!post && i % 3 == 1) {
                    p.hang(x, high - 1, z, "Deco_Iron_Chain_Small", "Deco_Iron_Chain_Small");
                }
            }
            if (phase >= 4 && corner) {
                p.put(x, high + 1, z, "Furniture_Human_Ruins_Torch", 0, false);
            }
        }
        if (phase <= 3) {
            p.pile(phase <= 2 ? 2 : 1, phase <= 2, "Wood_Fir_Trunk", "Wood_Fir_Trunk");
            if (phase <= 2) {
                p.ground(p.cx - 1, p.cz, "Furniture_Village_Crate");
            }
        }
    }

    // ------------------------------------------------------------------------------------------------ Slothians

    /**
     * Slothians : 1 mousse et fougères de jungle, jeunes cannes de bambou aux angles, bambous entassés au centre ; 2
     * cannes de bambou aux angles et au milieu des côtés, à mi-hauteur ; 3 cannes plus hautes que le toit, plancher de
     * bois tropical à mi-hauteur, lianes qui en pendent ; 4 torches de jungle au sommet des cannes d'angle.
     */
    private static void slothian(Plan p, int phase) {
        int deck = p.h + Math.max(3, p.full / 2);
        int poleTop = phase >= 3 ? p.h + p.full + 2 : deck - 1;
        List<int[]> ring = p.ring();
        for (int i = 0; i < ring.size(); i++) {
            int x = ring.get(i)[0];
            int z = ring.get(i)[1];
            boolean corner = p.corner(x, z);
            boolean pole = corner || p.midSide(x, z);
            if (phase == 1) {
                if (corner) {
                    p.column(x, z, p.h + 1, p.h + 2, "Wood_Bamboo_Trunk_Deco");
                } else {
                    p.ground(x, z, i % 2 == 0 ? "Plant_Moss_Rug_Green" : i % 4 == 1 ? "Plant_Fern_Jungle" : null);
                }
                continue;
            }
            if (pole) {
                p.column(x, z, p.h + 1, poleTop, "Wood_Bamboo_Trunk_Deco");
                if (phase >= 4 && corner) {
                    p.put(x, poleTop + 1, z, "Furniture_Jungle_Torch", 0, false);
                }
            } else {
                p.ground(x, z, i % 2 == 0 ? "Plant_Moss_Rug_Green" : i % 4 == 1 ? "Plant_Fern_Jungle" : null);
            }
            if (phase >= 3) {
                if (!pole) {
                    p.put(x, deck, z, "Wood_Tropicalwood_Planks_Half", 0, false);
                    if (i % 3 == 1) {
                        p.hang(x, deck - 1, z, "Plant_Vine_Hanging", "Plant_Vine_Hanging");
                    }
                }
            }
        }
        if (phase <= 3) {
            p.pile(phase <= 2 ? 2 : 1, phase <= 2, "Wood_Bamboo_Trunk", "Wood_Bamboo_Trunk");
        }
    }

    // ------------------------------------------------------------------------------------------------ Outils

    /** Un plan en cours de construction : l'anneau [rx0, rx1] x [rz0, rz1], le sol `h`, la hauteur de référence. */
    private static final class Plan {
        final int rx0;
        final int rx1;
        final int rz0;
        final int rz1;
        final int h;
        final int full;
        final int cx;
        final int cz;
        final Map<Long, Placement> out = new LinkedHashMap<>();

        Plan(int rx0, int rx1, int rz0, int rz1, int h, int full, int cx, int cz) {
            this.rx0 = rx0;
            this.rx1 = rx1;
            this.rz0 = rz0;
            this.rz1 = rz1;
            this.h = h;
            this.full = full;
            this.cx = cx;
            this.cz = cz;
        }

        void put(int x, int y, int z, String block, int rotation, boolean grounded) {
            if (block != null) {
                out.put(key(x, y, z), new Placement(block, rotation, grounded));
            }
        }

        /** Posé au sol (il lui faut un bloc plein dessous). */
        void ground(int x, int z, String block) {
            put(x, h + 1, z, block, 0, true);
        }

        void column(int x, int z, int from, int to, String block) {
            for (int y = from; y <= to; y++) {
                put(x, y, z, block, 0, false);
            }
        }

        /** Ce qui pend de `y` vers le bas, sans descendre à moins de 2 blocs du sol. */
        void hang(int x, int y, int z, String... chain) {
            for (int k = 0; k < chain.length && y - k > h + 2; k++) {
                put(x, y - k, z, chain[k], 0, false);
            }
        }

        /** Tas au centre : `spots` piles de `layers` (1 ou 2), de bas en haut. */
        void pile(int spots, boolean full, String bottom, String topBlock) {
            int[][] at = {{0, 0}, {1, 0}, {0, 1}};
            for (int k = 0; k < Math.min(spots + (full ? 1 : 0), at.length); k++) {
                put(cx + at[k][0], h + 1, cz + at[k][1], bottom, 0, true);
                if (full && k == 0) {
                    put(cx + at[k][0], h + 2, cz + at[k][1], topBlock, 0, false);
                }
            }
        }

        /** Positions de l'anneau, dans l'ordre (côté nord, est, sud, ouest), sans doublon. */
        List<int[]> ring() {
            List<int[]> list = new ArrayList<>();
            for (int x = rx0; x <= rx1; x++) {
                list.add(new int[] {x, rz0});
            }
            for (int z = rz0 + 1; z <= rz1; z++) {
                list.add(new int[] {rx1, z});
            }
            for (int x = rx1 - 1; x >= rx0; x--) {
                list.add(new int[] {x, rz1});
            }
            for (int z = rz1 - 1; z > rz0; z--) {
                list.add(new int[] {rx0, z});
            }
            return list;
        }

        boolean corner(int x, int z) {
            return (x == rx0 || x == rx1) && (z == rz0 || z == rz1);
        }

        /** Poteau tous les `step` blocs le long de l'anneau (et aux angles). */
        boolean post(int x, int z, int step) {
            return ((x == rx0 || x == rx1) && ((z - rz0) % step == 0 || z == rz1))
                    || ((z == rz0 || z == rz1) && ((x - rx0) % step == 0 || x == rx1));
        }

        /** Milieu d'un côté (ouvertures, lanternes, cannes). */
        boolean midSide(int x, int z) {
            int mx = (rx0 + rx1) / 2;
            int mz = (rz0 + rz1) / 2;
            return ((z == rz0 || z == rz1) && x == mx) || ((x == rx0 || x == rx1) && z == mz);
        }

        /** Juste à côté d'une ouverture, sur le même côté. */
        boolean besideGate(int x, int z) {
            int mx = (rx0 + rx1) / 2;
            int mz = (rz0 + rz1) / 2;
            return ((z == rz0 || z == rz1) && Math.abs(x - mx) == 1) || ((x == rx0 || x == rx1) && Math.abs(z - mz) == 1);
        }

        /** À au plus `d` blocs d'un angle, le long de l'anneau. */
        boolean nearCorner(int x, int z, int d) {
            boolean ex = x == rx0 || x == rx1;
            boolean ez = z == rz0 || z == rz1;
            int dx = Math.min(x - rx0, rx1 - x);
            int dz = Math.min(z - rz0, rz1 - z);
            return (ez && dx <= d) || (ex && dz <= d);
        }

        /** Décalage vers l'extérieur sur x d'un bloc d'angle, et rotation d'un bloc mural tourné vers lui (+x : 3, -x : 1). */
        int[] outX(int x) {
            return x == rx0 ? new int[] {-1, 3} : new int[] {1, 1};
        }

        /** Décalage vers l'extérieur sur z, et rotation (0 → -z, 2 → +z). */
        int[] outZ(int z) {
            return z == rz0 ? new int[] {-1, 2} : new int[] {1, 0};
        }
    }
}
