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

from jubilee_interface.constants import EXPERIMENT_OUTPUT_DIR


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

# Cache de résolution : au premier appel de experience_dir() pour un nom donné,
# le dossier daté est calculé et créé. Les appels suivants (dans la même session
# GUI) réutilisent le même chemin pour que tous les artefacts d'un même
# "Save All" atterrissent dans le même dossier.
_ACTIVE_EXPERIENCE_DIRS: dict[str, str] = {}


def set_experience_name(name: str) -> None:
    """Change le nom de l'expérience active."""
    global _EXPERIENCE_NAME
    _EXPERIENCE_NAME = name.strip() or "experience"


def get_experience_name() -> str:
    return _EXPERIENCE_NAME


def reset_experience_session() -> None:
    """Vide le cache des dossiers d'expérience — le prochain appel de
    :func:`experience_dir` recalcule un chemin (avec suffixe ``_2``, ``_3``,
    etc. si un dossier du même jour existe déjà)."""
    _ACTIVE_EXPERIENCE_DIRS.clear()


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
    ep = _load_entry_point("jubilee.paths", "gcode_logs_dir")
    if ep is None:
        raise RuntimeError(
            "science-jubilee is not installed (no gcode_logs_dir entry point)."
        )
    path = str(ep())
    os.makedirs(path, exist_ok=True)
    return path


def twin_rep_dir() -> str | None:
    """Path to the jubilee-blender-twin install, or None if not registered."""
    ep = _load_entry_point("jubilee.paths", "twin_dir")
    return str(ep()) if ep is not None else None


def _pick_unique_dir(name: str) -> str:
    """Return a fresh ``<date>_<name>[_N]/`` folder path and create it on disk.

    If ``<date>_<name>`` already exists (for instance from an earlier run today
    where the user forgot to change the experiment name), suffixes ``_2``,
    ``_3``, ... are tried until an unused name is found.
    """
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    base = os.path.join(experiment_root(), f"{date_prefix}_{name}")
    target = base
    suffix = 2
    while os.path.exists(target):
        target = f"{base}_{suffix}"
        suffix += 1
    os.makedirs(target, exist_ok=True)
    return target


def experience_dir(experience_name: str | None = None) -> str:
    """
    Retourne (et crée) le dossier de sortie de l'expérience active.

    Format : ``<EXPERIMENT_OUTPUT_DIR>/<YYYY-MM-DD>_<name>[_N]/``

    Le nom est lu en direct depuis ``_EXPERIENCE_NAME`` à chaque appel.
    Si un dossier du même jour existe déjà pour ce nom (par exemple parce que
    l'utilisateur relance une expérience sans changer le nom), un suffixe
    numérique ``_2``, ``_3``, ... est appliqué pour éviter d'écraser les
    exports précédents.  Le premier appel pour un nom donné mémorise le
    chemin résolu ; tous les appels suivants (dans la même session Python)
    renvoient exactement le même dossier — c'est ce qui garantit que tous les
    artefacts d'un même « Save All » atterrissent au même endroit.
    """
    name = experience_name or _EXPERIENCE_NAME
    cached = _ACTIVE_EXPERIENCE_DIRS.get(name)
    if cached and os.path.isdir(cached):
        return cached
    fresh = _pick_unique_dir(name)
    _ACTIVE_EXPERIENCE_DIRS[name] = fresh
    return fresh


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
