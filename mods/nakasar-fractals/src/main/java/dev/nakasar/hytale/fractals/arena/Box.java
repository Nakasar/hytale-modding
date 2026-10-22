package dev.nakasar.hytale.fractals.arena;

/** Boîte de blocs du monde, bornes comprises (zones des Layout écrits par les générateurs). */
public record Box(int x0, int x1, int y0, int y1, int z0, int z1) {

    public boolean contains(double x, double y, double z) {
        return x >= x0 && x < x1 + 1 && y >= y0 && y < y1 + 1 && z >= z0 && z < z1 + 1;
    }

    /** Vrai si (x, z) est dans l'emprise au sol de la boîte. */
    public boolean over(double x, double z) {
        return x >= x0 && x < x1 + 1 && z >= z0 && z < z1 + 1;
    }
}
