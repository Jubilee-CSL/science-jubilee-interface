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

from constants import EXPERIMENT_OUTPUT_DIR, LABWARE_REPO_PATH

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


def deck_definition_dir() -> str:
    return os.path.join(
        PROJECT_ROOT, "src", "science_jubilee", "decks", "deck_definition"
    )


def labware_collection_dir() -> str:
    """Dossier racine des labwares pré-téléchargés (sous-dossier par labware)."""
    return os.path.join(LABWARE_REPO_PATH, "labware_definition")


def labware_definition_dir() -> str:
    """Alias — retourne le même dossier que labware_collection_dir."""
    return labware_collection_dir()


def labware_cache_dir() -> str:
    """Conservé pour compatibilité — redirige vers labware_collection_dir."""
    return labware_collection_dir()


def experiment_root() -> str:
    """Racine (configurable) où sont stockés tous les exports d'expérience."""
    return EXPERIMENT_OUTPUT_DIR


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
