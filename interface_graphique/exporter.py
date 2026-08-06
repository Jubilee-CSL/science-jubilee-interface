
"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : exporter.py
Auteur      : [SABATIÉ Léo YAHIAOUI Rayan  / Projet industriel ROB4]
Date        : 10 Avril 2026
Description : Module de gestion des exports pour l'interface graphique.
              Gère la génération des fichiers de configuration (JSON), 
              des plans de découpe (DXF), et des parcours d'outils (G-code) 
              pour la configuration physique du plateau de la machine Jubilee.
=========================================================================================
"""

import json
import os
import shutil
import sys
import subprocess
from tkinter import messagebox

import ezdxf

import app_paths
from app_paths import get_experience_name
from constants import (
    DIAMETRE_TROU, LABWARE, OFFSET_CONTOUR,
    OFFSET_TROU_LEFT_X, OFFSET_TROU_LEFT_Y,
    OFFSET_TROU_RIGHT_X, OFFSET_TROU_RIGHT_Y,
    PLATEAU_H_MM, PLATEAU_W_MM,
    TWIN_REPO_PATH,JUBILEE_REPO_PATH,BLENDER_EXECUTABLE
)


def export_led_pattern(light_data, filename="pattern_lumiere.json"):
    """
    Exporte les 24 valeurs des LEDs vers un fichier JSON destiné à être lu par l'ESP32.
    
    Args:
        light_data (dict): Dictionnaire contenant l'état des LEDs.
        filename (str): Nom du fichier de destination.
    """
    pattern = {str(k): v for k, v in light_data.items()}
    data = {"pattern": pattern}

    full_path = app_paths.resolve_experience_file(filename)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print(f"✅ Pattern LED exporté -> {full_path}")


def export_layout(placed_objects, slot_assignments, canvas, canvas_plateau, filename="experience.json"):
    """
    Exporte la configuration du plateau (positions des labwares et outils) en format JSON.
    Garantit que le fichier est sauvegardé dans le répertoire 'deck_definition' du projet.
    
    Args:
        placed_objects (list): Objets labwares placés sur le canvas.
        slot_assignments (dict): Assignation des outils aux emplacements.
        canvas (tk.Canvas): Le canvas de l'interface graphique.
        canvas_plateau (int): L'ID du plateau sur le canvas.
        filename (str): Le nom du fichier d'export.
    """
    # 1. Résolution du chemin (crée l'arborescence si nécessaire)
    full_path = app_paths.resolve_deck_json(filename)

    # 3. Récupération des dimensions et calcul des échelles (Pixels -> Millimètres)
    x0_px, y0_px, x1_px, y1_px = canvas.coords(canvas_plateau)
    plateau_w_px = x1_px - x0_px
    plateau_h_px = y1_px - y0_px
    scale_x = PLATEAU_W_MM / plateau_w_px
    scale_y = PLATEAU_H_MM / plateau_h_px

    # Structure de base du fichier de configuration Jubilee
    data = {
        "name": get_experience_name(),
        "type": "SLAS", 
        "deck_offset": [0.0, 0.0],
        "slots": {}, 
        "tool_slots": {}
    }

    # Formatage des positions des labwares
    for idx, obj in enumerate(placed_objects):
        x1, y1, x2, y2 = canvas.coords(obj.id)
        
        # Conversion des coordonnées en millimètres
        y_mm = (x1 - x0_px) * scale_x
        x_mm = (y1 - y0_px) * scale_y
        w_mm = (x2 - x1) * scale_x
        h_mm = (y2 - y1) * scale_y

        data["slots"][str(idx)] = {
            "coordinates": [round(x_mm, 2), round(y_mm, 2)],
            "shape": "rectangle", 
            "width": round(w_mm, 2), 
            "length": round(h_mm, 2),
            "has_labware": True, 
            "labware": LABWARE[obj.name]["json"] if obj.name in LABWARE else None
        }

    # Formatage de l'assignation des outils
    for slot_id, tool in slot_assignments.items():
        if tool != "None": 
            data["tool_slots"][str(slot_id-1)] = tool  # Indexation à 0 pour le noyau Jubilee

    # 4. Écriture des données sur le disque
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Export JSON réussi dans : {full_path}")


def export_deck_with_labware(placed_objects, canvas, canvas_plateau):
    """Copie les JSON labware dans le dossier expérience et génère deck.json."""
    x0_px, y0_px, x1_px, y1_px = canvas.coords(canvas_plateau)
    scale_x = PLATEAU_W_MM / (x1_px - x0_px)
    scale_y = PLATEAU_H_MM / (y1_px - y0_px)
    out_dir = app_paths.experience_dir()

    slots = {}
    for idx, obj in enumerate(placed_objects):
        x1, y1, x2, y2 = canvas.coords(obj.id)
        x_mm = round((y1 - y0_px) * scale_y, 2)
        y_mm = round((x1 - x0_px) * scale_x, 2)

        labware_filename = None
        if obj.json_name:
            src = app_paths.resolve_labware_json(obj.json_name)
            if src:
                labware_filename = os.path.basename(src)
                shutil.copy2(src, os.path.join(out_dir, labware_filename))

        slots[str(idx)] = {
            "offset": [x_mm, y_mm],
            "has_labware": False,
            "labware": labware_filename,
        }

    data = {
        "deck_type": "Lab Automation Deck",
        "deck_slots": {"total": len(slots), "type": "SLAS Standard Labware"},
        "slots": slots,
        "offset_from": {"corner": "bottom_left"},
    }

    out_path = os.path.join(out_dir, "deck.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"✅ deck.json + labware JSON exportés dans : {out_dir}")


def export_to_dxf(json_file="experience.json"):
    """
    Génère les plans de découpe vectoriels (DXF) à partir de la configuration JSON.
    Crée un plan complet et deux demi-plans optimisés pour la zone de travail d'une découpeuse laser.
    
    Args:
        json_file (str): Le fichier JSON source contenant les coordonnées.
    """

    json_path = app_paths.resolve_deck_json(json_file)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Erreur lecture JSON: {e}")
        return

    milieu_x_dxf = PLATEAU_W_MM / 2
    jeu = 0.5 

    # Définition des fichiers (Le découpage se fait sur l'axe X du DXF, soit le Y Jubilee)
    parties = [
        {"name": "plan_entier.dxf", "x_min": -OFFSET_CONTOUR, "x_max": PLATEAU_W_MM + 2*OFFSET_CONTOUR, "off_x": -OFFSET_CONTOUR},
        {"name": "plan_left.dxf",  "x_min": -OFFSET_CONTOUR, "x_max": milieu_x_dxf, "off_x": -OFFSET_CONTOUR},
        {"name": "plan_right.dxf", "x_min": milieu_x_dxf, "x_max": PLATEAU_W_MM + 2*OFFSET_CONTOUR, "off_x": milieu_x_dxf}
    ]

    slots = data.get("slots", {})

    def transform_jubilee_to_dxf(x_jub, y_jub):
        """
        Transformation par matrice/logique :
        X_dxf = Y_jubilee (Axe vers la droite)
        Y_dxf = PLATEAU_H_MM - X_jubilee (Axe vers le bas inversé pour monter)
        """
        x_dxf = y_jub
        y_dxf = PLATEAU_H_MM - x_jub
        return x_dxf, y_dxf

    for p in parties:
        doc = ezdxf.new(dxfversion="R2010")
        doc.header["$INSUNITS"] = 4 
        msp = doc.modelspace()
        off_x = p["off_x"]

        # --- 1) CONTOUR DU PLATEAU ---
        pts_plateau_dxf = [
            (p["x_min"], 0),
            (p["x_max"], 0),
            (p["x_max"], PLATEAU_H_MM),
            (p["x_min"], PLATEAU_H_MM)
        ]
        
        # On applique l'offset de fichier sur le X final
        final_plateau = [(px - off_x, py) for px, py in pts_plateau_dxf]
        msp.add_lwpolyline(final_plateau, close=True, dxfattribs={"layer": "plateau"})


        # --- 2) TROUS DE FIXATION ---
        r = DIAMETRE_TROU / 2
        trous_positions = [
            (- OFFSET_TROU_LEFT_X, OFFSET_TROU_LEFT_Y),                          # Bas Gauche
            (- OFFSET_TROU_LEFT_X, PLATEAU_H_MM - OFFSET_TROU_LEFT_Y),           # Bas Droite
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, OFFSET_TROU_RIGHT_Y),         # Haut Gauche
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, PLATEAU_H_MM - OFFSET_TROU_RIGHT_Y) # Haut Droite
        ]
        for txj, tyj in trous_positions:
            if p["x_min"] <= txj <= p["x_max"]:
                msp.add_circle(center=(txj - off_x, tyj), radius=r, dxfattribs={"layer": "fixation_holes"})
    
        # --- 3) LABWARES ---
        for slot in slots.values():
            if not slot.get("has_labware", False): continue
            
            cxj, cyj = slot["coordinates"]
            wj, hj = slot.get("width", 0), slot.get("length", 0)
            # Calcul des 4 coins en Jubilee autour du centre (cxj, cyj)
            # wj est sur l'axe X (bas), hj sur l'axe Y (droite)
            corners_jub = [
                (cxj - jeu, cyj - jeu),
                (cxj + hj + jeu, cyj - jeu),
                (cxj + hj + jeu, cyj + wj + jeu),
                (cxj - jeu, cyj + wj + jeu)
            ]

            # Transformation de chaque coin
            pts_dxf = [transform_jubilee_to_dxf(xj, yj) for xj, yj in corners_jub]

            # Vérification du clipping sur le X du DXF
            x_min_dxf = min(pt[0] for pt in pts_dxf)
            x_max_dxf = max(pt[0] for pt in pts_dxf)

            if x_max_dxf > p["x_min"] and x_min_dxf < p["x_max"]:
                # CLIPPING STRICT : On borne les points X pour couper net au milieu
                final_pts = [
                    (max(p["x_min"], min(px, p["x_max"])) - off_x, py) 
                    for px, py in pts_dxf
                ]
                msp.add_lwpolyline(final_pts, close=True, dxfattribs={"layer": "labware"})
        
        out_path = app_paths.resolve_experience_file(p["name"])
        doc.saveas(out_path)
        print(f"✅ Fichier {out_path} généré avec succès.")


def json_to_gcode(json_file, gcode_file, z_up=10.0, z_down=0.0, feedrate=4000):
    json_path  = app_paths.resolve_deck_json(json_file)
    gcode_path = app_paths.resolve_deck_json(gcode_file)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Erreur lecture JSON ({json_path}): {e}")
        return

    with open(gcode_path, "w", encoding="utf-8") as g:
        g.write("G21 ; mm\nG90 ; absolu\n")
        g.write(f"G0 Z{z_up} F600\n\n")

        for slot in data.get("slots", {}).values():
            if not slot.get("has_labware", False):
                continue
            x1, y1 = slot["coordinates"]
            x2 = x1 + slot.get("length", 0)
            y2 = y1 + slot.get("width", 0)
            pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]
            g.write(f"G0 X{pts[0][0]:.3f} Y{pts[0][1]:.3f} F{feedrate}\n")
            g.write(f"G1 Z{z_down} F800\n")
            for x, y in pts[1:]:
                g.write(f"G1 X{x:.3f} Y{y:.3f}\n")
            g.write(f"G1 Z{z_up} F600\n\n")

    print(f"✅ G-code généré avec succès : {gcode_path}")

def testgcode_to_twin(gcode_file):
    
    bat_path = os.path.join(TWIN_REPO_PATH,"from_gcode", "run_latest_gcode_animation.bat") 

    cmd = [
        bat_path,
        JUBILEE_REPO_PATH,
        TWIN_REPO_PATH,
        BLENDER_EXECUTABLE,
        gcode_file
    ]

    try:
        subprocess.Popen(cmd, shell=True)
    except Exception as e:
        messagebox.showerror("Execution Error", f"Impossible de lancer la simulation :\n{e}")

def launch_raytracing():
    rt_path = os.path.join(TWIN_REPO_PATH, "ray_tracing.py") 
    sys.path.append(rt_path)
    from ray_tracing import ray_tracing_cd

    ray_tracing_cd()
    