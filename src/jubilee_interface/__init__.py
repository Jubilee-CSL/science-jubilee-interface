from pathlib import Path

# For an editable install (`pip install -e .`) this file is at:
#   <workspace>/src/jubilee_interface/__init__.py
# so the experiment output dir resolves to the workspace's interface_graphique/experiment_deck/
_EXPERIMENT_DECK_DIR: Path = (
    Path(__file__).resolve().parent.parent.parent
    / "interface_graphique"
    / "experiment_deck"
)


def get_experiment_deck_dir() -> str:
    """Return the root directory where the interface writes experiment outputs."""
    return str(_EXPERIMENT_DECK_DIR)
