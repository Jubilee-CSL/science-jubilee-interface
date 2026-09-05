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

All exports write coordinates in the Jubilee machine convention.  Canvas
pixels are converted to machine millimetres in a single place: the helpers
in :mod:`jubilee_interface.coords`.  Historical ``experience.json`` files
saved before this refactor use a different (GUI-local) convention and will
not round-trip through :func:`export_layout` and
``workspace_tab.load_configuration``.
=========================================================================================
"""

import json
import os
import shutil
import subprocess
import sys
from tkinter import messagebox

import ezdxf

from jubilee_interface import app_paths
from jubilee_interface.app_paths import (
    gcode_log_dir,
    get_experience_name,
    jubilee_repo_root,
    twin_rep_dir,
)
from jubilee_interface.constants import (
    DIAMETRE_TROU,
    LABWARE,
    OFFSET_CONTOUR,
    OFFSET_TROU_LEFT_X,
    OFFSET_TROU_LEFT_Y,
    OFFSET_TROU_RIGHT_X,
    OFFSET_TROU_RIGHT_Y,
    PLATEAU_H_MM,
    PLATEAU_W_MM,
)
from jubilee_interface.coords import (
    MachineBBox,
    PlateauFrame,
    canvas_bbox_to_machine_mm,
    machine_point_to_dxf,
)


def _bbox_for(obj, canvas, frame: PlateauFrame) -> MachineBBox:
    """Return the machine-mm bbox of a placed labware."""
    return canvas_bbox_to_machine_mm(tuple(canvas.coords(obj.id)), frame)


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
    Coordonnées écrites dans le repère machine Jubilee (mm).

    Args:
        placed_objects (list): Objets labwares placés sur le canvas.
        slot_assignments (dict): Assignation des outils aux emplacements.
        canvas (tk.Canvas): Le canvas de l'interface graphique.
        canvas_plateau (int): L'ID du plateau sur le canvas.
        filename (str): Le nom du fichier d'export.
    """
    full_path = app_paths.resolve_deck_json(filename)
    frame = PlateauFrame.from_canvas(canvas, canvas_plateau)

    data = {
        "name": get_experience_name(),
        "type": "SLAS",
        "deck_offset": [0.0, 0.0],
        "slots": {},
        "tool_slots": {},
    }

    for idx, obj in enumerate(placed_objects):
        bbox = _bbox_for(obj, canvas, frame)
        data["slots"][str(idx)] = {
            "coordinates": [bbox.x_mm, bbox.y_mm],
            "shape": "rectangle",
            "length": bbox.length_mm,   # extent along machine X
            "width": bbox.width_mm,     # extent along machine Y
            "has_labware": True,
            "labware": LABWARE[obj.name]["json"] if obj.name in LABWARE else None,
        }

    for slot_id, tool in slot_assignments.items():
        if tool != "None":
            data["tool_slots"][str(slot_id - 1)] = tool  # 0-index for the Jubilee core

    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Export JSON réussi dans : {full_path}")


def export_deck_with_labware(placed_objects, canvas, canvas_plateau):
    """Copie les JSON labware dans le dossier expérience et génère deck.json."""
    out_dir = app_paths.experience_dir()
    frame = PlateauFrame.from_canvas(canvas, canvas_plateau)

    slots = {}
    for idx, obj in enumerate(placed_objects):
        bbox = _bbox_for(obj, canvas, frame)

        labware_filename = None
        if obj.json_name:
            src = app_paths.resolve_labware_json(obj.json_name)
            if src:
                labware_filename = os.path.basename(src)
                shutil.copy2(src, os.path.join(out_dir, labware_filename))

        slots[str(idx)] = {
            "offset": [bbox.x_mm, bbox.y_mm],
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
    """Génère les plans DXF à partir de la configuration JSON.

    Crée un plan complet et deux demi-plans optimisés pour la zone de travail
    d'une découpeuse laser.
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

    parties = [
        {"name": "plan_entier.dxf", "x_min": -OFFSET_CONTOUR, "x_max": PLATEAU_W_MM + 2 * OFFSET_CONTOUR, "off_x": -OFFSET_CONTOUR},
        {"name": "plan_left.dxf",   "x_min": -OFFSET_CONTOUR, "x_max": milieu_x_dxf,                     "off_x": -OFFSET_CONTOUR},
        {"name": "plan_right.dxf",  "x_min": milieu_x_dxf,    "x_max": PLATEAU_W_MM + 2 * OFFSET_CONTOUR, "off_x": milieu_x_dxf},
    ]

    slots = data.get("slots", {})

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
            (p["x_min"], PLATEAU_H_MM),
        ]
        final_plateau = [(px - off_x, py) for px, py in pts_plateau_dxf]
        msp.add_lwpolyline(final_plateau, close=True, dxfattribs={"layer": "plateau"})

        # --- 2) TROUS DE FIXATION ---
        r = DIAMETRE_TROU / 2
        trous_positions = [
            (-OFFSET_TROU_LEFT_X, OFFSET_TROU_LEFT_Y),
            (-OFFSET_TROU_LEFT_X, PLATEAU_H_MM - OFFSET_TROU_LEFT_Y),
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, OFFSET_TROU_RIGHT_Y),
            (PLATEAU_W_MM + OFFSET_TROU_RIGHT_X, PLATEAU_H_MM - OFFSET_TROU_RIGHT_Y),
        ]
        for txj, tyj in trous_positions:
            if p["x_min"] <= txj <= p["x_max"]:
                msp.add_circle(center=(txj - off_x, tyj), radius=r, dxfattribs={"layer": "fixation_holes"})

        # --- 3) LABWARES ---
        for slot in slots.values():
            if not slot.get("has_labware", False):
                continue

            cxj, cyj = slot["coordinates"]
            length_j = slot.get("length", 0)   # along machine X
            width_j  = slot.get("width", 0)    # along machine Y

            corners_machine = [
                (cxj - jeu,            cyj - jeu),
                (cxj + length_j + jeu, cyj - jeu),
                (cxj + length_j + jeu, cyj + width_j + jeu),
                (cxj - jeu,            cyj + width_j + jeu),
            ]
            pts_dxf = [machine_point_to_dxf(x, y) for x, y in corners_machine]

            x_min_dxf = min(pt[0] for pt in pts_dxf)
            x_max_dxf = max(pt[0] for pt in pts_dxf)

            if x_max_dxf > p["x_min"] and x_min_dxf < p["x_max"]:
                final_pts = [
                    (max(p["x_min"], min(px, p["x_max"])) - off_x, py)
                    for px, py in pts_dxf
                ]
                msp.add_lwpolyline(final_pts, close=True, dxfattribs={"layer": "labware"})

        out_path = app_paths.resolve_experience_file(p["name"])
        doc.saveas(out_path)
        print(f"✅ Fichier {out_path} généré avec succès.")


def json_to_gcode(json_file, gcode_file, z_up=10.0, z_down=0.0, feedrate=4000):
    """G-code de traçage des rectangles labware, dans le repère machine Jubilee."""
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
            # Machine convention: length along X, width along Y.
            x2 = x1 + slot.get("length", 0)
            y2 = y1 + slot.get("width", 0)
            pts = [(x1, y1), (x2, y1), (x2, y2), (x1, y2), (x1, y1)]

            # Start on a stable corner (min x then min y) for reproducibility.
            start_idx = min(range(len(pts) - 1), key=lambda i: (pts[i][0], pts[i][1]))
            path = pts[start_idx:-1] + pts[:start_idx]
            path.append(path[0])
            g.write(f"G0 X{path[0][0]:.3f} Y{path[0][1]:.3f} F{feedrate}\n")
            g.write(f"G1 Z{z_down} F800\n")
            for x, y in path[1:]:
                g.write(f"G1 X{x:.3f} Y{y:.3f}\n")
            g.write(f"G1 Z{z_up} F600\n\n")

    print(f"✅ G-code généré avec succès : {gcode_path}")


def testgcode_to_twin(gcode_file):
    twin_dir = twin_rep_dir()
    if twin_dir is None:
        messagebox.showerror(
            "Configuration Error",
            "jubilee-blender-twin n'est pas enregistré.\n"
            "Enregistrez le dépôt via un entry point 'jubilee.paths / twin_dir'."
        )
        return
    bat_path = os.path.join(twin_dir, "from_gcode", "run_latest_gcode_animation.bat")
    from jubilee_interface.deck_3d_exporter import find_blender
    blender_bin = find_blender()
    if blender_bin is None:
        messagebox.showerror(
            "Blender introuvable",
            "Aucun exécutable Blender trouvé dans le PATH.\n"
            "Installez Blender ou définissez constants.BLENDER_EXECUTABLE.",
        )
        return
    cmd = [
        "cmd.exe", "/c", bat_path,
        jubilee_repo_root(),
        twin_dir,
        blender_bin,
        gcode_file,
    ]
    try:
        env = os.environ.copy()
        py_paths = []
        for candidate in (
            twin_dir,
            os.path.join(twin_dir, "addons"),
            os.path.join(twin_dir, "scripts"),
            os.path.join(twin_dir, "blender_addons"),
            jubilee_repo_root(),
        ):
            if os.path.isdir(candidate):
                py_paths.append(candidate)

        if py_paths:
            existing = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = os.pathsep.join(py_paths + ([existing] if existing else []))

        # Aide Blender à découvrir les modules/add-ons du twin (dont `interface`).
        env.setdefault("BLENDER_USER_SCRIPTS", twin_dir)

        subprocess.Popen(cmd, cwd=twin_dir, env=env, shell=False)
    except Exception as e:
        messagebox.showerror("Execution Error", f"Impossible de lancer la simulation :\n{e}")


def launch_raytracing():
    twin_dir = twin_rep_dir()
    if twin_dir is None:
        messagebox.showerror(
            "Configuration Error",
            "jubilee-blender-twin n'est pas enregistré."
        )
        return
    sys.path.append(twin_dir)
    from ray_tracing import ray_tracing_cd

    ray_tracing_cd()
