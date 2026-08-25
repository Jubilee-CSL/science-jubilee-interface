"""Jubilee GUI package — deck designer and experiment exporter."""

from pathlib import Path


def _repo_root() -> Path:
    """Repository root when installed editable; installed-package location otherwise."""
    # src/jubilee_interface/__init__.py → parents: [0] jubilee_interface, [1] src, [2] repo root
    return Path(__file__).resolve().parents[2]


_EXPERIMENT_DECK_DIR: Path = _repo_root() / "experiment_deck"


def get_experiment_deck_dir() -> str:
    """Root directory where the GUI writes ``YYYY-MM-DD_<name>/`` experiment folders."""
    return str(_EXPERIMENT_DECK_DIR)


def interface_dir() -> Path:
    """Return the science-jubilee-interface repo root (editable install)."""
    return _repo_root()


__all__ = ["get_experiment_deck_dir", "interface_dir"]
