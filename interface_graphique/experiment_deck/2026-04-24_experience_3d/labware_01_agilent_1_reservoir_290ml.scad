// ─── Placement Jubilee ──────────────────────────────────────
// coordinates (JSON) : (120.21, 58.79, 3.00) mm
// Rotation : 0°   Labware dims : xDim=127.76, yDim=85.57
// Mode : simplifié (boîte)

translate([120.215, 58.787, 3.000])
rotate([0, 0, 0.0])
{
    // Agilent 1 Well Reservoir 290 mL (simplified — outer body only)
    $fn = 64;
    cube([127.76, 85.57, 44.04]);

}
