"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : assemble_deck.py  (script Blender headless)
Description : Importe tous les fichiers STL d'un dossier, en conservant chacun comme
              un objet séparé avec ses coordonnées monde d'origine (déjà baked dans
              le SCAD via translate()+rotate()), puis sauvegarde le .blend résultant.

Utilisation (ne pas lancer directement — utilisé par deck_3d_exporter.py) :
    blender --background --python assemble_deck.py -- <output.blend> <stl_dir>
=========================================================================================
"""

import glob
import os
import sys

try:
    import bpy  # noqa: F401 — disponible uniquement dans Blender
except ImportError:  # pragma: no cover
    print("[assemble_deck] Ce script doit être lancé via Blender.", file=sys.stderr)
    sys.exit(1)


def parse_args() -> tuple[str, str]:
    """Récupère les arguments après `--`."""
    if "--" not in sys.argv:
        raise SystemExit("Usage: blender --background --python assemble_deck.py -- <out.blend> <stl_dir>")
    argv = sys.argv[sys.argv.index("--") + 1:]
    if len(argv) < 2:
        raise SystemExit("Arguments manquants: <out.blend> <stl_dir>")
    return argv[0], argv[1]


def reset_scene() -> None:
    """Vide la scène par défaut de Blender (cube/camera/light)."""
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def import_stl(path: str) -> None:
    """Importe un STL en conservant ses coordonnées monde (pas de recentrage)."""
    # Blender 4.x : op renommée. On tente les deux.
    try:
        bpy.ops.wm.stl_import(filepath=path)
    except AttributeError:
        bpy.ops.import_mesh.stl(filepath=path)  # Blender 3.x / legacy


def main() -> None:
    output_blend, stl_dir = parse_args()

    stl_files = sorted(glob.glob(os.path.join(stl_dir, "*.stl")))
    if not stl_files:
        raise SystemExit(f"Aucun STL trouvé dans : {stl_dir}")

    print(f"[assemble_deck] {len(stl_files)} STL à importer depuis {stl_dir}")
    reset_scene()

    for stl in stl_files:
        name = os.path.splitext(os.path.basename(stl))[0]
        print(f"[assemble_deck]   + {name}")
        import_stl(stl)
        # L'objet actif après import est celui qu'on vient de charger.
        if bpy.context.active_object is not None:
            bpy.context.active_object.name = name

    os.makedirs(os.path.dirname(os.path.abspath(output_blend)), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    print(f"[assemble_deck] Sauvegardé : {output_blend}")


if __name__ == "__main__":
    main()
