"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : app_paths.py
Description : Point central de résolution des chemins du projet.
              (Nommé app_paths pour éviter toute collision avec le paquet PyPI 'paths'.)
=========================================================================================
"""

import os

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))


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


def resolve_deck_json(filename: str) -> str:
    target = deck_definition_dir()
    os.makedirs(target, exist_ok=True)
    return os.path.join(target, filename)


def resolve_labware_json(filename: str):
    if os.path.isabs(filename):
        return filename if os.path.exists(filename) else None
    candidate = os.path.join(labware_definition_dir(), filename)
    return candidate if os.path.exists(candidate) else None
