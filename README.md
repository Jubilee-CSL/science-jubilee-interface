# 🔬🧪 Science Jubilee ⚡⚙️
### Controlling Jubilees for Science — with a Graphical Layout Designer

[![ReadTheDocs](https://readthedocs.org/projects/science-jubilee/badge/?version=latest)](https://science-jubilee.readthedocs.io/en/stable/)
[![PyPI-Server](https://img.shields.io/pypi/v/science-jubilee.svg)](https://pypi.org/project/science-jubilee/)
[![Monthly Downloads](https://pepy.tech/badge/science-jubilee/month)](https://pepy.tech/project/science-jubilee)
[![Twitter](https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter)](https://twitter.com/machine_agency)
[![Project generated with PyScaffold](https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold)](https://pyscaffold.org/)

> Use an open-source toolchanger to do science

<p align="center">
  <img src="https://github.com/user-attachments/assets/b9f23d3c-060a-4648-8b81-c446124a8f5e" width="900" alt="Jubilee Graphical Interface"/>
</p>

This repository extends [Science-Jubilee](https://science-jubilee.readthedocs.io/en/latest/index.html) with a **Graphical User Interface** to design, configure, and export experimental deck layouts for the Jubilee robotic platform. The GUI lets you visually arrange labware on the 305×305 mm Jubilee deck, assign tools to parking slots, and export everything needed to run an experiment — all without editing JSON by hand.

---

## Table of Contents

1. [Overview](#overview)
2. [GUI — Jubilee Layout Designer](#gui--jubilee-layout-designer)
   - [Features](#features)
   - [Installation](#installation)
   - [Configuration](#configuration)
   - [Running the App](#running-the-app)
   - [Export Outputs](#export-outputs)
   - [Module Architecture](#module-architecture)
3. [Core `science_jubilee` Library](#core-science_jubilee-library)
4. [Additional 2026 Extension Modules](#additional-2026-extension-modules)
5. [Project Structure](#project-structure)

---

## Overview

### Hardware
This project targets the [Jubilee](https://jubilee3d.com/index.php?title=Main_Page) platform: an open-source, extensible multi-tool motion system. You can think of it as a 3D printer that swaps its own tools mid-experiment. It is outfitted with a 305×305 mm laboratory deck that accommodates standard microplates.

### Software layers
| Layer | Description |
|---|---|
| `src/science_jubilee/` | Python library — machine driver, deck/tool/labware classes |
| `interface_graphique/` | CustomTkinter GUI — drag-and-drop deck designer + export pipeline |

---

## GUI — Jubilee Layout Designer

The graphical interface (`interface_graphique/main.py`) is a desktop application that provides a real-time, to-scale canvas of the Jubilee deck. It is the central design tool of the experiment workflow.

### Features

#### 1. Workspace Tab — Interactive Deck Canvas
- **Real-scale canvas** — 305×305 mm workspace rendered at 3 px/mm.
- **Drag-and-drop placement** of labware items from the built-in library.
- **90° rotation** with automatic dimension and coordinate updates.
- **Collision detection** — prevents overlapping objects with configurable safety margins.
- **Tool slot assignment** — link up to 4 tools to their physical parking slots at the back of the machine.

#### 2. Labware Browser Tab
- Browses a local labware repository (Opentrons V2-compatible JSON definitions).
- Filterable by **category** (well plates, reservoirs, tube racks, tip racks, …) and **keyword search**.
- Click a card to instantly load that labware onto the workspace canvas.

#### 3. LED Control Tab
- Controls **24 individual LEDs** (PCA9685 PWM driver, 12-bit resolution: 0–4095).
- Per-well slider + text entry for precise illumination values.
- Exports a `pattern_lumiere.json` file ready to be read by the ESP32 firmware.

#### 4. Sidebar
- **Experience name** — sets the dated output folder (`<EXPERIMENT_OUTPUT_DIR>/<YYYY-MM-DD>_<name>/`).
- **Save All** — triggers the full export pipeline in a single click.
- **Load / Clear** — reload a saved JSON configuration or reset the canvas.

---

### Installation

**Python 3.10+** is required.

```bash
# 1. Clone the repository
git clone https://github.com/leosabatie-eng/science-jubilee.git
cd science-jubilee

# 2. Install GUI dependencies
pip install customtkinter ezdxf Pillow

# 3. (Optional) Install the core science_jubilee library
pip install -e .
```

> **Optional 3D export** — install [OpenSCAD](https://openscad.org/) and/or [Blender](https://www.blender.org/) and configure their paths in `constants.py` (see below).

---

### Configuration

Open `interface_graphique/constants.py` and adjust the two path constants for your machine:

```python
# Absolute path where dated experiment folders are created
EXPERIMENT_OUTPUT_DIR = r"C:\path\to\your\experiment_deck"

# Absolute path to your local labware repository
# Expected structure: <LABWARE_REPO_PATH>/labware_definition/<labware_name>/<labware_name>.json
LABWARE_REPO_PATH = r"C:\path\to\your\labware"

# (Optional) Override auto-detected OpenSCAD / Blender executables
OPENSCAD_EXECUTABLE: str | None = r"C:\Program Files\OpenSCAD\openscad.exe"
BLENDER_EXECUTABLE:  str | None = None   # None = auto-detect via PATH
```

---

### Running the App

```bash
cd interface_graphique
python main.py
```

The window title is **"Jubilee Bioreactor — Workspace & LED Control"**.

Keyboard shortcut: `Delete` — removes the object currently under the cursor.

---

### Export Outputs

Clicking **Save All** in the sidebar triggers the full export pipeline. All files are written to:

```
<EXPERIMENT_OUTPUT_DIR>/<YYYY-MM-DD>_<experience_name>/
├── experience.json          # deck layout — labware positions + tool assignments
├── pattern_lumiere.json     # LED illumination pattern for the ESP32
├── plan_entier.dxf          # full DXF manufacturing plan (frame + labware cutouts)
├── plan_jubilee.txt         # G-code trace path for pen calibration on the machine
├── deck.scad                # OpenSCAD assembly file (requires OpenSCAD)
├── labware_<n>_<name>.scad  # per-labware SCAD files
├── *.stl                    # rendered STL meshes (requires OpenSCAD)
└── assembly.blend           # Blender scene (requires Blender)
```

#### `experience.json` — example

```json
{
  "name": "Experience1",
  "type": "SLAS",
  "deck_offset": [0.0, 0.0],
  "slots": {
    "0": {
      "coordinates": [16.12, 18.59],
      "shape": "rectangle",
      "width": 127.76,
      "length": 85.48,
      "has_labware": true,
      "labware": "greiner_24_wellplate_3300ul_orth.json"
    }
  },
  "tool_slots": {
    "0": "stylo",
    "2": "Inoculator",
    "3": "Pipette"
  }
}
```

#### DXF manufacturing plan

The exported DXF is ready for laser cutting or CNC milling:
- Outer frame with 4 corner M3 fixation holes.
- Accurate labware cutout contours.
- Units: millimeters (INSUNITS = 4).

---

### Module Architecture

```
interface_graphique/
├── main.py              # App entry-point — assembles tabs and sidebar
├── workspace_tab.py     # Interactive deck canvas (placement, collision, slots)
├── sidebar.py           # Sidebar — actions and experience name
├── labware_browser.py   # Labware library browser (local repo, search, filter)
├── led_tab.py           # LED illumination control panel (24 LEDs, PCA9685)
├── exporter.py          # JSON / DXF / G-code export logic
├── deck_3d_exporter.py  # Async 3D pipeline: SCAD → STL → .blend
├── labware_to_scad.py   # Labware → OpenSCAD geometry generator
├── models.py            # DraggableObject data class + labware dimension loader
├── app_paths.py         # Centralised path resolution (experience folders, labware repo)
├── constants.py         # All physical, graphical, and path constants
└── theme.py             # Colour palette for the UI
```

---

## Core `science_jubilee` Library

The `src/science_jubilee/` package provides the Python API to control Jubilee from scripts or Jupyter notebooks.

```
src/
└── science_jubilee/
    ├── Machine.py               # Jubilee machine driver
    ├── tools/
    │   ├── Tool.py              # Base tool class
    │   ├── configs/             # Tool configuration files
    │   └── ...                  # Pipette, Syringe, Camera, … modules
    ├── decks/
    │   ├── Deck.py              # Base deck class
    │   ├── deck_definition/     # Experiment JSON + 3D assets
    │   └── ...                  # LabAutomationDeck, … modules
    └── labware/
        ├── Labware.py           # Base labware class
        └── labware_definitions/ # Opentrons V2-compatible labware JSON files
```

**Quick start:**

```python
from science_jubilee.Machine import Machine
from science_jubilee.decks.LabAutomationDeck import LabAutomationDeck
from science_jubilee.tools.Pipette import Pipette

m = Machine()
deck = m.load_deck("deck_config_name")
tip_rack = deck.load_labware("opentrons_96_tiprack_300ul", 0)
pipette = Pipette(index, name, tip_rack, config_file)
m.load_tool(pipette)
```

---

## Additional 2026 Extension Modules

These companion repositories extend Science-Jubilee for specific experimental workflows:

| Module | Description | Repository |
|---|---|---|
| **Syringe Tool** | Precision liquid handling with customised syringe drivers | [Nicolas5u/Projet_industriel](https://github.com/Nicolas5u/Projet_industriel.git) |
| **LED Matrix Control** | ESP32/PCA9685 integration for per-well illumination | *(see LED tab in this GUI)* |
| **Duckweed Detection** | Computer vision pipeline for *Lemna minor* detection & counting | [Sworkyx/Jubilee_Camera_detection_lentille](https://github.com/Sworkyx/Jubilee_Camera_detection_lentille) |

---

## Project Structure

```
science-jubilee-interface/
├── README.md                    # ← you are here
├── interface_graphique/         # GUI application (CustomTkinter)
│   ├── main.py
│   ├── constants.py             # ← edit paths here before first run
│   └── experiment_deck/         # default output directory for exports
└── src/
    └── science_jubilee/
        ├── Machine.py
        ├── tools/
        ├── decks/
        └── labware/
```

---

## Note

This project has been set up using PyScaffold 4.5. For details and usage
information on PyScaffold see https://pyscaffold.org/.
