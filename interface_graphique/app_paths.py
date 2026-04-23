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

from constants import EXPERIMENT_OUTPUT_DIR

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))

# Nom de l'expérience courante — tous les exports (JSON, DXF, G-code, SCAD,
# STL, .blend, pattern LED) sont regroupés dans un unique dossier daté.
# Peut être modifié à l'exécution via set_experience_name().
_EXPERIENCE_NAME: str = "experience"

# Le dossier daté est figé au premier appel à experience_dir() pour que tous
# les exports d'une même session atterrissent au même endroit, même si minuit
# passe entre deux clics. Reset via reset_experience_session().
_SESSION_DIR: str | None = None


def set_experience_name(name: str) -> None:
    """Change le nom de l'expérience. Réinitialise le dossier de session."""
    global _EXPERIENCE_NAME, _SESSION_DIR
    _EXPERIENCE_NAME = name or "experience"
    _SESSION_DIR = None  # sera recalculé au prochain export


def get_experience_name() -> str:
    return _EXPERIENCE_NAME


def reset_experience_session() -> None:
    """Force le recalcul du dossier daté (utile pour démarrer une nouvelle session)."""
    global _SESSION_DIR
    _SESSION_DIR = None


def deck_definition_dir() -> str:
    return os.path.join(
        PROJECT_ROOT, "src", "science_jubilee", "decks", "deck_definition"
    )


def labware_definition_dir() -> str:
    return os.path.join(
        PROJECT_ROOT, "src", "science_jubilee", "labware", "labware_definition"
    )


def labware_cache_dir() -> str:
    return os.path.join(_THIS_DIR, "labware_cache")


def experiment_root() -> str:
    """Racine (configurable) où sont stockés tous les exports d'expérience."""
    return EXPERIMENT_OUTPUT_DIR


def experience_dir(experience_name: str | None = None) -> str:
    """
    Retourne (et crée) le dossier unique de sortie de l'expérience active.
    Format : <EXPERIMENT_OUTPUT_DIR>/<YYYY-MM-DD>_<nom_experience>/
    Le chemin est mis en cache pour la session courante.
    """
    global _SESSION_DIR
    if experience_name is not None:
        # Appel avec un nom explicite → pas de cache
        name = experience_name
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        target = os.path.join(experiment_root(), f"{date_prefix}_{name}")
        os.makedirs(target, exist_ok=True)
        return target

    if _SESSION_DIR is None:
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        _SESSION_DIR = os.path.join(
            experiment_root(), f"{date_prefix}_{_EXPERIENCE_NAME}"
        )
    os.makedirs(_SESSION_DIR, exist_ok=True)
    return _SESSION_DIR


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
    candidate = os.path.join(labware_definition_dir(), filename)
    return candidate if os.path.exists(candidate) else None
