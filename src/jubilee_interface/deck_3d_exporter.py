"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : deck_3d_exporter.py
Description : Export 3D du deck populé.
              Pipeline : placed_objects ─► SCAD ─► STL ─► .blend
              Chaque labware reste un fichier / objet Blender séparé, positionné
              en coordonnées monde absolues.
=========================================================================================
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable

from jubilee_interface import app_paths
from jubilee_interface import constants as C
from jubilee_interface.coords import (
    PlateauFrame,
    canvas_bbox_to_machine_mm,
)
from jubilee_interface.labware_to_scad import generate_scad_placed
from jubilee_interface.models import DraggableObject, load_labware_dims


# ═════════════════════════════════════════════════════════════════════════════
# Détection des exécutables externes
# ═════════════════════════════════════════════════════════════════════════════

def _first_existing(*paths: str | None) -> str | None:
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return None


def find_openscad() -> str | None:
    """Retourne le chemin vers openscad(.exe) existant, ou None si introuvable."""
    return _first_existing(C.OPENSCAD_EXECUTABLE, shutil.which("openscad"))


def find_blender() -> str | None:
    """Retourne le chemin vers blender(.exe) existant, ou None si introuvable."""
    return _first_existing(C.BLENDER_EXECUTABLE, shutil.which("blender"))


def _precomputed_stl(load_name: str) -> str | None:
    """Retourne le chemin du STL pré-calculé dans le dépôt local, ou None."""
    candidate = os.path.join(
        app_paths.labware_collection_dir(), load_name, f"{load_name}.stl"
    )
    return candidate if os.path.exists(candidate) else None


# ═════════════════════════════════════════════════════════════════════════════
# Génération SCAD
# ═════════════════════════════════════════════════════════════════════════════

def _sanitize_filename(name: str) -> str:
    """Remplace les caractères problématiques dans un nom de fichier."""
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "labware"


def _deck_plate_scad() -> str:
    """
    Génère le SCAD du plateau Jubilee dans le repère machine (Jubilee).
    Convention :
      - Jubilee-X = axe vertical (canvas Y)  → largeur SCAD = PLATEAU_H_MM
      - Jubilee-Y = axe horizontal (canvas X) → largeur SCAD = PLATEAU_W_MM
    C'est la même convention que exporter.export_layout() et que le digital twin.
    """
    sx, sy, t = C.PLATEAU_H_MM, C.PLATEAU_W_MM, C.DECK_THICKNESS_MM
    r = C.DIAMETRE_TROU / 2
    # Trous de fixation approximatifs aux 4 coins du plateau (aides visuelles)
    inset = max(C.OFFSET_TROU_LEFT_X, C.OFFSET_TROU_LEFT_Y, 5.0)
    holes = [
        (inset,       inset),
        (inset,       sy - inset),
        (sx - inset,  inset),
        (sx - inset,  sy - inset),
    ]
    hole_block = "\n".join(
        f"    translate([{hx:.3f}, {hy:.3f}, -0.5])\n"
        f"        cylinder(r={r}, h={t + 1}, $fn={C.OPENSCAD_FN});"
        for hx, hy in holes
    )
    return (
        "// ═══════════════════════════════════════════════════════════════════\n"
        "// Deck plate — repère Jubilee (X vertical, Y horizontal)\n"
        "// ═══════════════════════════════════════════════════════════════════\n"
        f"$fn = {C.OPENSCAD_FN};\n\n"
        "difference() {\n"
        f"    cube([{sx}, {sy}, {t}]);\n"
        f"{hole_block}\n"
        "}\n"
    )


def _canvas_to_jubilee_coords(
    obj: DraggableObject,
    canvas,
    canvas_plateau,
) -> tuple[float, float, float, float]:
    """
    Convertit les coordonnées canvas en coordonnées Jubilee (mm), strictement
    identiques à celles écrites dans experience.json par exporter.export_layout().

    Returns:
        (x_mm, y_mm, length_mm, width_mm) où :
          - (x_mm, y_mm) est le coin min-AABB de la bbox dans le repère machine
          - length_mm est l'extension selon la machine X
          - width_mm est l'extension selon la machine Y
    """
    frame = PlateauFrame.from_canvas(canvas, canvas_plateau)
    bbox = canvas_bbox_to_machine_mm(tuple(canvas.coords(obj.id)), frame)
    return bbox.x_mm, bbox.y_mm, bbox.length_mm, bbox.width_mm


@dataclass
class LabwarePart:
    """Représente un labware à exporter (source + destination)."""
    index:    int
    load_name: str        # ex: "nest_12_reservoir_15ml"
    scad_path: str
    stl_path:  str


def generate_all_scad(
    placed_objects: list[DraggableObject],
    canvas,
    canvas_plateau,
    output_dir: str,
) -> tuple[str, list[LabwarePart]]:
    """
    Génère tous les fichiers SCAD :
      - deck.scad
      - labware_NN_<loadName>.scad (un par labware)
      - assembly.scad (master file)

    Returns:
        (deck_scad_path, labware_parts).
    """
    os.makedirs(output_dir, exist_ok=True)

    # ── Plateau ──────────────────────────────────────────────────────────────
    deck_scad_path = os.path.join(output_dir, "deck.scad")
    with open(deck_scad_path, "w", encoding="utf-8") as f:
        f.write(_deck_plate_scad())

    # ── Labwares ─────────────────────────────────────────────────────────────
    parts: list[LabwarePart] = []
    for idx, obj in enumerate(placed_objects, start=1):
        x_mm, y_mm, _, _ = _canvas_to_jubilee_coords(obj, canvas, canvas_plateau)
        load_name = os.path.splitext(os.path.basename(obj.json_name or ""))[0]
        safe_name = _sanitize_filename(f"labware_{idx:02d}_{load_name}")
        scad_path = os.path.join(output_dir, f"{safe_name}.scad")
        stl_path  = os.path.join(output_dir, f"{safe_name}.stl")

        # Always load JSON data — needed for AABB correction and fallback generation
        data = load_labware_dims(obj.json_name) if obj.json_name else None
        if not data:
            print(f"⚠️  Labware {idx} ({obj.name}) ignoré — définition introuvable.")
            continue

        xdim = float(data["dimensions"]["xDimension"])
        ydim = float(data["dimensions"]["yDimension"])

        # AABB correction: same logic as generate_scad_placed.
        # After rotate([0,0,angle]), the body min-corner shifts; we compensate so
        # that the min-corner of the placed model lands exactly on (x_mm, y_mm),
        # matching the `coordinates` field written by exporter.export_layout().
        world_angle = (float(obj.angle) + 90.0) % 360.0
        rad = math.radians(world_angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        corners = [(0.0, 0.0), (xdim, 0.0), (xdim, ydim), (0.0, ydim)]
        rotated = [(cx * cos_a - cy * sin_a, cx * sin_a + cy * cos_a) for cx, cy in corners]
        tx = x_mm - min(p[0] for p in rotated)
        ty = y_mm - min(p[1] for p in rotated)

        # Prefer the pre-computed STL from the local labware repo
        src_stl = _precomputed_stl(load_name)
        if src_stl:
            # Reference the repo STL by absolute path so OpenSCAD applies
            # translate + rotate and produces a correctly positioned output STL.
            src_stl_fwd = src_stl.replace("\\", "/")
            scad = (
                f"// {obj.name} — positioned from pre-computed STL\n"
                f"// coordinates (JSON): ({x_mm:.2f}, {y_mm:.2f}) mm  rotation: {world_angle}°\n"
                f"translate([{tx:.3f}, {ty:.3f}, {C.DECK_THICKNESS_MM:.3f}])\n"
                f"rotate([0, 0, {world_angle}])\n"
                f"import(\"{src_stl_fwd}\");\n"
            )
        else:
            # Fallback: generate full SCAD from the JSON definition
            scad = generate_scad_placed(
                data=data,
                x_mm=x_mm,
                y_mm=y_mm,
                z_mm=C.DECK_THICKNESS_MM,
                rotation_deg=world_angle,
                fn=C.OPENSCAD_FN,
                simplified=False,
            )

        with open(scad_path, "w", encoding="utf-8") as f:
            f.write(scad)

        parts.append(LabwarePart(idx, load_name, scad_path, stl_path))

    # ── Assembly ─────────────────────────────────────────────────────────────
    assembly_path = os.path.join(output_dir, "assembly.scad")
    with open(assembly_path, "w", encoding="utf-8") as f:
        f.write("// Master assembly — previewable in OpenSCAD\n")
        f.write("include <deck.scad>;\n")
        for p in parts:
            f.write(f"include <{os.path.basename(p.scad_path)}>;\n")

    return deck_scad_path, parts


# ═════════════════════════════════════════════════════════════════════════════
# Conversion SCAD → STL via OpenSCAD CLI
# ═════════════════════════════════════════════════════════════════════════════

def run_openscad(
    scad_path: str,
    stl_path: str,
    openscad_bin: str,
) -> None:
    """Lance `openscad -o stl_path scad_path` en mode headless.

    Utilise le backend Manifold (10-100× plus rapide que CGAL) s'il est
    supporté par la version d'OpenSCAD installée (≥ 2024.01). Sinon on
    retombe sur le backend par défaut.
    """
    cmd = [
        openscad_bin,
        "--backend=manifold",
        "-o", stl_path,
        scad_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        # Ancienne version d'OpenSCAD : pas de --backend
        subprocess.run(
            [openscad_bin, "-o", stl_path, scad_path],
            check=True, capture_output=True,
        )


def convert_all_to_stl(
    deck_scad_path: str,
    parts: list[LabwarePart],
    output_dir: str,
    openscad_bin: str,
    progress: Callable[[str], None] | None = None,
) -> list[str]:
    """
    Convertit chaque .scad en .stl en parallèle (1 process OpenSCAD par labware).
    Retourne la liste des STL produits.
    """
    deck_stl = os.path.join(output_dir, "deck.stl")

    # All parts need OpenSCAD: pre-computed STLs use a wrapper SCAD
    # (translate+rotate+import) which is near-instant but produces positioned output.
    openscad_jobs: list[tuple[str, str, str]] = [
        ("deck", deck_scad_path, deck_stl),
    ] + [(p.load_name, p.scad_path, p.stl_path) for p in parts]

    produced: list[str] = []
    total = len(openscad_jobs)
    done = 0

    # max_workers = nb de CPU (OpenSCAD est déjà mono-thread par invocation)
    with ThreadPoolExecutor(max_workers=min(os.cpu_count() or 4, total)) as pool:
        future_map = {
            pool.submit(run_openscad, scad, stl, openscad_bin): (name, stl)
            for name, scad, stl in openscad_jobs
        }
        for fut in as_completed(future_map):
            name, stl = future_map[fut]
            fut.result()  # propage les exceptions
            produced.append(stl)
            done += 1
            if progress:
                progress(f"STL: {done}/{total} ({name})")

    return produced


# ═════════════════════════════════════════════════════════════════════════════
# Assemblage final via Blender headless
# ═════════════════════════════════════════════════════════════════════════════

def run_blender_assembly(
    stl_dir: str,
    output_blend: str,
    blender_bin: str,
    assemble_script: str,
) -> None:
    """
    Lance Blender en mode arrière-plan pour importer tous les STL et produire un .blend.
    Les arguments après `--` sont passés au script Python.
    """
    subprocess.run(
        [
            blender_bin, "--background",
            "--python", assemble_script,
            "--",
            output_blend, stl_dir,
        ],
        check=True,
        capture_output=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Orchestrateur (appelé par la GUI)
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class ExportResult:
    output_dir: str
    scad_files: list[str]
    stl_files:  list[str]
    blend_file: str | None
    warnings:   list[str]


def export_deck_3d(
    placed_objects: list[DraggableObject],
    canvas,
    canvas_plateau,
    experience_name: str | None = None,
    progress: Callable[[str], None] | None = None,
) -> ExportResult:
    """
    Pipeline complet :
      1. Génère les fichiers SCAD (toujours).
      2. Convertit en STL si OpenSCAD est disponible.
      3. Assemble en .blend si Blender est disponible.

    Produit ExportResult listant tous les fichiers créés et les avertissements
    (dépendances manquantes, labwares ignorés, etc.).
    """
    warnings: list[str] = []

    if not placed_objects:
        raise ValueError("Aucun labware à exporter — le plateau est vide.")

    output_dir = app_paths.resolve_3d_output_dir(experience_name)

    # ── 1. SCAD (toujours) ───────────────────────────────────────────────────
    if progress: progress("Génération des fichiers SCAD…")
    deck_scad, parts = generate_all_scad(
        placed_objects, canvas, canvas_plateau, output_dir,
    )
    scad_files = [deck_scad] + [p.scad_path for p in parts]
    scad_files.append(os.path.join(output_dir, "assembly.scad"))

    # ── 2. STL (optionnel — OpenSCAD requis) ─────────────────────────────────
    stl_files: list[str] = []
    openscad_bin = find_openscad()
    if openscad_bin:
        try:
            stl_files = convert_all_to_stl(
                deck_scad, parts, output_dir, openscad_bin, progress,
            )
        except subprocess.CalledProcessError as e:
            warnings.append(f"Conversion STL partielle : {e}")
        except OSError as e:
            warnings.append(
                f"OpenSCAD introuvable à « {openscad_bin} » — STL non générés ({e})."
            )
    else:
        warnings.append(
            "OpenSCAD introuvable — seuls les .scad ont été générés. "
            "Installez OpenSCAD pour obtenir les STL."
        )

    # ── 3. Blender (optionnel — Blender + STL requis) ────────────────────────
    blend_file: str | None = None
    blender_bin = find_blender()
    if stl_files and blender_bin:
        assemble_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "assemble_deck.py",
        )
        if os.path.exists(assemble_script):
            blend_path = os.path.join(output_dir, "deck.blend")
            try:
                if progress: progress("Assemblage Blender…")
                run_blender_assembly(
                    output_dir, blend_path, blender_bin, assemble_script,
                )
                blend_file = blend_path
            except subprocess.CalledProcessError as e:
                warnings.append(f"Échec assemblage Blender : {e}")
            except OSError as e:
                warnings.append(
                    f"Blender introuvable à « {blender_bin} » — étape .blend sautée ({e})."
                )
        else:
            warnings.append("Script assemble_deck.py introuvable.")
    elif stl_files and not blender_bin:
        warnings.append(
            "Blender introuvable — l'étape .blend a été sautée. "
            "Installez Blender pour obtenir le fichier d'assemblage."
        )

    if progress: progress("Terminé.")

    return ExportResult(
        output_dir=output_dir,
        scad_files=scad_files,
        stl_files=stl_files,
        blend_file=blend_file,
        warnings=warnings,
    )


# ═════════════════════════════════════════════════════════════════════════════
# Wrapper thread + callback GUI
# ═════════════════════════════════════════════════════════════════════════════

def export_deck_3d_async(
    placed_objects: list[DraggableObject],
    canvas,
    canvas_plateau,
    on_done:  Callable[[ExportResult], None],
    on_error: Callable[[Exception], None],
    on_progress: Callable[[str], None] | None = None,
) -> None:
    """Lance export_deck_3d() dans un thread daemon (non bloquant pour la GUI)."""

    def _worker():
        try:
            result = export_deck_3d(
                placed_objects, canvas, canvas_plateau,
                progress=on_progress,
            )
            on_done(result)
        except Exception as exc:  # noqa: BLE001 — intentionnellement large
            on_error(exc)

    threading.Thread(target=_worker, daemon=True).start()
