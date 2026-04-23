"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : theme.py
Description : Couleurs partagées entre les panneaux.
=========================================================================================
"""

CATEGORY_COLORS: dict[str, str] = {
    "wellPlate":     "#1565c0",
    "tubeRack":      "#6a1b9a",
    "reservoir":     "#00695c",
    "tipRack":       "#bf360c",
    "aluminumBlock": "#4e342e",
    "adapter":       "#37474f",
    "lid":           "#558b2f",
}

_DEFAULT_COLOR = "#1f6aa5"


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, _DEFAULT_COLOR)


def local_labware_color(name: str) -> str:
    if "Plaque" in name:
        return "#1f6aa5"
    if "eau" in name.lower():
        return "#2e7d32"
    return "#c2185b"
