"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : constants.py
Auteur      : [SABATIÉ Léo / Projet industriel ROB4]
Date        : 10 Avril 2026
Description : Fichier centralisant les constantes physiques, logiques et graphiques.
              Toutes les dimensions sont exprimées soit en millimètres (MM), 
              soit en pixels (PX) pour l'interface Tkinter.
=========================================================================================
"""

# --- 1. DIMENSIONS PHYSIQUES ET CONVERSIONS ---
# Ratio utilisé pour le rendu graphique sur le canvas
MM_TO_PIX = 3 

# Dimensions utiles du plateau Jubilee (mm)
PLATEAU_W_MM = 305
PLATEAU_H_MM = 305

# Dimensions calculées pour l'interface graphique (px)
PLATEAU_W = PLATEAU_W_MM * MM_TO_PIX
PLATEAU_H = PLATEAU_H_MM * MM_TO_PIX


# --- 2. GÉOMÉTRIE DES FIXATIONS (PLATINE) ---
# Paramètres pour la génération des plans DXF et G-code
DIAMETRE_TROU = 3  # Diamètre des vis de fixation M3 (mm)

# Offsets pour les trous de fixation par rapport aux bords du plateau (mm)
OFFSET_TROU_RIGHT_Y = 15.39
OFFSET_TROU_RIGHT_X = 5
OFFSET_TROU_LEFT_Y  = 5
OFFSET_TROU_LEFT_X  = 1.5

# Marge de sécurité pour le tracé du contour extérieur
OFFSET_CONTOUR = 5


# --- 3. PARAMÈTRES ÉLECTRONIQUES (ESP32) ---
# Résolution PWM pour le contrôle de l'intensité lumineuse
MAX_ILLUMINANCE = 4095


# --- 3-BIS. EXPORT 3D (OpenSCAD + Blender) ---
# Épaisseur du plateau Jubilee utilisée pour le modèle 3D (mm)
DECK_THICKNESS_MM = 3.0

# Résolution des cercles/cylindres OpenSCAD
OPENSCAD_FN = 64

# Exécutables externes (None → auto-détection via PATH)
# Exemples d'override : r"C:\Program Files\OpenSCAD\openscad.exe"
OPENSCAD_EXECUTABLE: str | None = r"C:/Program Files/OpenSCAD/openscad.exe"
BLENDER_EXECUTABLE:  str | None = None


# --- 3-TER. DOSSIER DE SORTIE DES EXPÉRIENCES ---
# Racine absolue où sont enregistrés tous les exports (JSON, DXF, G-code,
# SCAD, STL, .blend, pattern LED). Un sous-dossier daté est créé automatiquement
# pour chaque expérience (ex. "2026-04-24_experience").
EXPERIMENT_OUTPUT_DIR = r"C:\Users\Alienor\Documents\Projects\Jubilee\science-jubilee-interface\interface_graphique\experiment_deck"


# --- 4. RÈGLES DE COLLISION ET PLACEMENT (Interface) ---
# Marges de sécurité pour éviter le chevauchement d'objets (mm)
MARGIN_BETWEEN_OBJECTS = 5 
MARGIN_BORDER          = 10 

# Conversion des marges en pixels pour la logique du Canvas
MARGIN_BORDER_PX          = MARGIN_BORDER * (PLATEAU_H / PLATEAU_H_MM)
MARGIN_BETWEEN_OBJECTS_PX = MARGIN_BETWEEN_OBJECTS * (PLATEAU_H / PLATEAU_H_MM)


# --- 5. GESTION DU CANVAS TKINTER ---
# Tags d'objets Canvas qui ne doivent pas être supprimés ou déplacés
TAGS_PROTEGES = {
    "__background__", "__grid__", "plateau_marge", "slot_text",
    "outil_1", "outil_2", "outil_3", "outil_4",
    "slot_text_1", "slot_text_2", "slot_text_3", "slot_text_4"
}


# --- 6. CONFIGURATION DES OUTILS (TOOL CHANGER) ---
# Emplacements physiques des slots d'outils sur le portique (coordonnées canvas)
OUTIL_SLOTS = {
    1: {"x": 200, "y": 700},
    2: {"x": 200, "y": 500},
    3: {"x": 200, "y": 300},
    4: {"x": 200, "y": 100},
}

# Liste exhaustive des outils supportés par la configuration actuelle
OUTILS_LISTE = ["None", "Pipette", "Inoculator", "Fluo", "stylo", "Other"]


# --- 7. DÉFINITIONS DU MATÉRIEL (LABWARE) ---
# Dépôt local des labwares pré-téléchargés (JSON, métadonnées, images, STL, SCAD).
# Chaque labware est dans un sous-dossier : labware_definition/<load_name>/
LABWARE_REPO_PATH = r"C:\Users\Alienor\Documents\Projects\Jubilee\labware"

# Base de données des labwares utilisables
# w_mm: largeur (axe Y machine), h_mm: longueur (axe X machine)
LABWARE = {
    "Plaque 24 puits": {
        "w_mm": 127.76, 
        "h_mm": 85.48, 
        "json": "greiner_24_wellplate_3300ul_orth.json"
    },
    "Réservoir eau": {
        "w_mm": 50, 
        "h_mm": 30, 
        "json": "pot_de_d'eau.json"
    },
    "Réservoir lentilles": {
        "w_mm": 80, 
        "h_mm": 80, 
        "json": "pot_duckweed.json"
    }
}
