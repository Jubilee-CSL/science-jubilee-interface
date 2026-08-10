"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : app_paths.py
Description : Point central de résolution des chemins du projet.
              (Nommé app_paths pour éviter toute collision avec le paquet PyPI 'paths'.)
=========================================================================================
"""

import os
from datetime import datetime
from pathlib import Path

from constants import EXPERIMENT_OUTPUT_DIR


def _load_entry_point(group: str, name: str):
    """Return the loaded value for the first matching entry point, or None."""
    from importlib.metadata import entry_points
    eps = [ep for ep in entry_points(group=group) if ep.name == name]
    return eps[0].load() if eps else None

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))

# Nom de l'expérience courante — tous les exports (JSON, DXF, G-code, SCAD,
# STL, .blend, pattern LED) sont regroupés dans un unique dossier daté.
# Peut être modifié à l'exécution via set_experience_name().
_EXPERIENCE_NAME: str = "experience"


def set_experience_name(name: str) -> None:
    """Change le nom de l'expérience active."""
    global _EXPERIENCE_NAME
    _EXPERIENCE_NAME = name.strip() or "experience"


def get_experience_name() -> str:
    return _EXPERIENCE_NAME


def reset_experience_session() -> None:
    """Conservé pour compatibilité — sans effet depuis la suppression du cache."""
    pass


def labware_collection_dir() -> str:
    """Labware JSON definitions bundled with the installed jubilee-labware package."""
    path = _load_entry_point("jubilee.paths", "labware_dir")
    if path is None:
        try:
            import jubilee_labware
            path = jubilee_labware.LABWARE_DEFINITION_DIR
        except ImportError:
            raise RuntimeError(
                "jubilee-labware is not installed. Run: pip install jubilee-labware"
            )
    return str(path)


def labware_definition_dir() -> str:
    """Alias — retourne le même dossier que labware_collection_dir."""
    return labware_collection_dir()


def labware_cache_dir() -> str:
    """Conservé pour compatibilité — redirige vers labware_collection_dir."""
    return labware_collection_dir()


def experiment_root() -> str:
    """Racine (configurable) où sont stockés tous les exports d'expérience."""
    return EXPERIMENT_OUTPUT_DIR

def jubilee_repo_root() -> str:
    """Root of the science-jubilee install (repo root for editable installs)."""
    ep = _load_entry_point("jubilee.paths", "jubilee_dir")
    if ep is not None:
        return str(ep())
    try:
        import science_jubilee
        return str(Path(science_jubilee.__file__).resolve().parent.parent)
    except ImportError:
        raise RuntimeError("science-jubilee is not installed.")


def gcode_log_dir() -> str:
    path = os.path.join(jubilee_repo_root(), "gcode_logs")
    os.makedirs(path, exist_ok=True)
    return path


def twin_rep_dir() -> str | None:
    """Path to the jubilee-blender-twin install, or None if not registered."""
    ep = _load_entry_point("jubilee.paths", "twin_dir")
    return str(ep()) if ep is not None else None


def experience_dir(experience_name: str | None = None) -> str:
    """
    Retourne (et crée) le dossier de sortie de l'expérience active.
    Format : <EXPERIMENT_OUTPUT_DIR>/<YYYY-MM-DD>_<nom_experience>/
    Le nom est lu en direct depuis _EXPERIENCE_NAME à chaque appel.
    """
    name = experience_name or _EXPERIENCE_NAME
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    target = os.path.join(experiment_root(), f"{date_prefix}_{name}")
    os.makedirs(target, exist_ok=True)
    return target


def resolve_experience_file(filename: str, experience_name: str | None = None) -> str:
    """
    Retourne le chemin absolu d'un fichier d'export dans le dossier de l'expérience.
    Si `filename` est déjà absolu, on le renvoie tel quel.
    """
    if os.path.isabs(filename):
        return filename
    return os.path.join(experience_dir(experience_name), filename)


# ─── Anciens helpers, conservés pour compatibilité ──────────────────────────

def resolve_deck_json(filename: str) -> str:
    """Alias historique — route désormais vers le dossier de l'expérience."""
    return resolve_experience_file(filename)


def resolve_3d_output_dir(experience_name: str | None = None) -> str:
    """Dossier de sortie des exports 3D (= dossier de l'expérience)."""
    return experience_dir(experience_name)


def resolve_labware_json(filename: str):
    if os.path.isabs(filename):
        return filename if os.path.exists(filename) else None
    # New structure: labware_definition/<load_name>/<load_name>.json
    load_name = os.path.splitext(os.path.basename(filename))[0]
    candidate = os.path.join(labware_collection_dir(), load_name, filename)
    if os.path.exists(candidate):
        return candidate
    return None
