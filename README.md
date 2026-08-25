# 🔬🧪 Science Jubilee Interface ⚡⚙️
### Design experimental deck layouts for the Jubilee lab robot — graphically

[![Twitter](https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter)](https://twitter.com/machine_agency)

> Drag-and-drop labware, assign tools, click **Save All**, and get every file
> the machine, the digital twin and the laser cutter need — in one folder.

<p align="center">
  <img src="https://github.com/user-attachments/assets/b9f23d3c-060a-4648-8b81-c446124a8f5e" width="900" alt="Jubilee Graphical Interface"/>
</p>

This repository is the **GUI companion** to [science-jubilee](https://github.com/machineagency/science-jubilee).
It lets you visually arrange labware on the 305 × 305 mm Jubilee deck, assign
tools to parking slots, and export everything needed to run an experiment —
without editing JSON by hand.

The GUI is a plugin in the Jubilee ecosystem: once installed, it registers a
`jubilee.paths / experiment_deck_dir` entry point that other packages (notably
[jubilee-blender-twin](https://github.com/Jubilee-CSL/jubilee-blender-twin))
consume to locate the latest experiment output.

---

## Table of Contents

1. [What you get](#what-you-get)
2. [Installation](#installation)
3. [Running the App](#running-the-app)
4. [Configuration](#configuration)
5. [Using the interface](#using-the-interface)
   - [Workspace tab](#workspace-tab)
   - [Labware browser tab](#labware-browser-tab)
   - [LED control tab](#led-control-tab)
   - [Sidebar](#sidebar)
6. [Save-All: what gets written and where](#save-all-what-gets-written-and-where)
7. [Coordinate convention](#coordinate-convention)
8. [Project structure](#project-structure)
9. [Development](#development)
10. [Troubleshooting](#troubleshooting)

---

## What you get

| Component | Description |
|---|---|
| **`jubilee-gui`** | Console-script that launches the GUI |
| **`python -m jubilee_interface`** | Same, without needing `pip install -e .` |
| **`experience.json`** | Deck layout in Jubilee machine coordinates |
| **`deck.json`** | science-jubilee deck definition (copied labware JSONs alongside) |
| **`pattern_lumiere.json`** | 24-channel LED pattern for the ESP32 driver |
| **DXF plans** | Full and split laser-cutter plates |
| **G-code trace** | Tool-tip trace of the deck (pen calibration) |
| **SCAD / STL / .blend** | 3-D assembly for the digital twin (optional) |

---

## Installation

**Python 3.10+** is required.

```bash
# 1. Clone the repository
git clone https://github.com/Jubilee-CSL/science-jubilee-interface.git
cd science-jubilee-interface

# 2. Install the interface package (registers the `jubilee-gui` command and
#    the `jubilee.paths` / `experiment_deck_dir` entry point)
pip install -e .

# 3. Install the local labware library so the labware browser works
pip install -e path/to/jubilee-labware

# 4. (Recommended) Install science-jubilee so the sidebar can find gcode_logs/
pip install -e path/to/science-jubilee
```

> **Optional 3-D export** — install [OpenSCAD](https://openscad.org/) and/or
> [Blender](https://www.blender.org/) to enable the SCAD → STL → .blend pipeline.
> Set their paths in `constants.py` (see [Configuration](#configuration)) or
> leave them on `PATH` for auto-detection.

Verify the entry points registered:

```bash
python -c "from importlib.metadata import entry_points; print([ep.name for ep in entry_points(group='jubilee.paths')])"
# → ['jubilee_dir', 'labware_dir', 'interface_dir', 'experiment_deck_dir', ...]
```

---

## Running the App

Once installed:

```bash
jubilee-gui
```

Or, without installing:

```bash
python -m jubilee_interface
```

Or from an IDE / notebook:

```python
from jubilee_interface.app import main
main()
```

The window title is **"Jubilee Bioreactor — Workspace & LED Control"**.

<!-- SCREENSHOT: launch view. Save as docs/screenshots/main_window.png -->
<!-- ![Main window](docs/screenshots/main_window.png) -->

---

## Configuration

Open [`src/jubilee_interface/constants.py`](src/jubilee_interface/constants.py) and adjust the paths for your machine:

```python
# Where dated experiment folders are created.  Defaults to
# <repo_root>/experiment_deck/ — override only if you want data somewhere
# else (e.g. a shared drive).
EXPERIMENT_OUTPUT_DIR = r"C:\path\to\your\experiment_deck"

# Optional overrides for OpenSCAD / Blender.  Leave `None` to auto-detect via PATH.
OPENSCAD_EXECUTABLE: str | None = r"C:\Program Files\OpenSCAD\openscad.exe"
BLENDER_EXECUTABLE:  str | None = None
```

The path to the local labware repository is discovered automatically via the
`jubilee.paths / labware_dir` entry point registered by `jubilee-labware` —
no manual configuration needed.

---

## Using the interface

### Workspace tab

Interactive to-scale canvas of the 305 × 305 mm Jubilee deck (rendered at
3 px/mm).

- **Left click** on the canvas after picking a labware from the library places it.
- **Left drag** on a placed labware moves it (blocked when it would overlap another item or leave the plateau).
- **Right click** on a placed labware rotates it 90°.
- **`Delete` key** removes the item under the cursor.
- **Tool slot column** (right of the plateau) — click a slot to assign one of the tools from the popup.

<!-- SCREENSHOT: workspace tab with a couple of plates placed. Save as docs/screenshots/workspace_tab.png -->
<!-- ![Workspace tab](docs/screenshots/workspace_tab.png) -->

### Labware browser tab

Browses the local labware repository (`jubilee-labware`).

- **Search** by display name, load name or brand.
- **Filter** by category (well plates, reservoirs, tube racks, tip racks, adapters, aluminium blocks, lids).
- Click **"↳ Placer sur le plateau"** on a card to arm the labware for placement, then click on the workspace tab to drop it.

<!-- SCREENSHOT: labware browser with filter applied. Save as docs/screenshots/labware_browser.png -->
<!-- ![Labware browser](docs/screenshots/labware_browser.png) -->

### LED control tab

Controls the 24 individual LEDs of the illumination panel (PCA9685 PWM
driver, 12-bit resolution, values 0–4095).

- Per-well slider **and** a text entry for precise values.
- **"EXPORTER CONFIGURATION LED (ESP32)"** writes `pattern_lumiere.json` in the current experiment folder.

<!-- SCREENSHOT: LED tab with a lighting pattern. Save as docs/screenshots/led_tab.png -->
<!-- ![LED tab](docs/screenshots/led_tab.png) -->

### Sidebar

- **Nom de l'expérience** — sets the dated output folder (`<EXPERIMENT_OUTPUT_DIR>/<YYYY-MM-DD>_<name>/`). Confirm with `Enter` or by losing focus.
- **💾 SAUVEGARDER** — triggers the full export pipeline in one click (see [Save-All](#save-all-what-gets-written-and-where)).
- **Charger Configuration** — reload a saved `experience.json` back onto the canvas.
- **Vider plateau** — clear the workspace.
- **Choisir un gcode** — pick one of the G-code files under `<science-jubilee>/gcode_logs/` to feed the digital twin.
- **Lancer Jumeau Numérique** — starts the [jubilee-blender-twin](https://github.com/Jubilee-CSL/jubilee-blender-twin) animation for the selected G-code.
- **Lancer Raytracing** — runs the collision-detection pass in the twin.

<!-- SCREENSHOT: sidebar. Save as docs/screenshots/sidebar.png -->
<!-- ![Sidebar](docs/screenshots/sidebar.png) -->

---

## Save-All: what gets written and where

Clicking **💾 SAUVEGARDER** in the sidebar runs the full export pipeline. Every
artefact for one experiment lands in a single folder:

```
<EXPERIMENT_OUTPUT_DIR>/<YYYY-MM-DD>_<experience_name>[_N]/
├── experience.json          # deck layout — labware positions + tool assignments
├── deck.json                # science-jubilee deck definition (same coords)
├── <copied labware JSONs>   # every labware used, copied from jubilee-labware
├── pattern_lumiere.json     # LED illumination pattern for the ESP32
├── plan_entier.dxf          # full DXF manufacturing plan
├── plan_left.dxf            # left half (fits smaller laser cutters)
├── plan_right.dxf           # right half
├── plan_jubilee.gcode       # G-code trace path for pen calibration
├── deck.scad                # OpenSCAD assembly file (requires OpenSCAD)
├── labware_<n>_<name>.scad  # per-labware SCAD files
├── *.stl                    # rendered STL meshes (requires OpenSCAD)
└── assembly.blend           # Blender scene (requires Blender)
```

### Never overwriting past exports

If the experiment name was not edited and the day's folder already exists (from
a previous run, or from an earlier session left over), the GUI **appends a
numeric suffix** — `_2`, then `_3`, and so on — so nothing is silently
overwritten:

```
experiment_deck/
├── 2026-08-14_experience/
├── 2026-08-14_experience_2/    ← second launch, same day, same name
└── 2026-08-14_experience_3/    ← third launch
```

Within a single Save-All (JSON + DXF + G-code + LED + optional 3-D) every
artefact goes into the **same** folder. If you change the experiment name in
the sidebar and click Save-All again, a fresh folder is picked for the new
name.

### `experience.json` — example

```json
{
  "name": "Experience1",
  "type": "SLAS",
  "deck_offset": [0.0, 0.0],
  "slots": {
    "0": {
      "coordinates": [16.12, 18.59],
      "shape": "rectangle",
      "length": 127.76,
      "width": 85.48,
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

`coordinates` is the min corner of the labware in Jubilee machine millimetres.
`length` is the extent along machine X; `width` is the extent along machine Y.

---

## Coordinate convention

All exports (`experience.json`, `deck.json`, DXF, G-code, SCAD) carry
**machine millimetres in the Jubilee frame** — origin at the bottom-left of
the plateau, +X vertical (upward on the canvas), +Y horizontal (rightward).
The canvas-pixel → machine-mm transform lives in a single tested module,
[`jubilee_interface.coords`](src/jubilee_interface/coords.py), and is
exercised by `tests/test_coords.py`.

Historical `experience.json` files saved before this refactor use a
different (GUI-local) convention and will not round-trip through the current
`Charger Configuration` action.

---

## Project structure

```
science-jubilee-interface/
├── README.md                         # ← you are here
├── pyproject.toml
├── setup.cfg
├── experiment_deck/                  # default output directory (created on first save)
├── docs/
│   └── screenshots/                  # drop UI screenshots here
├── src/
│   └── jubilee_interface/
│       ├── __init__.py               # entry-point providers
│       ├── __main__.py               # `python -m jubilee_interface`
│       ├── app.py                    # main window (was interface_graphique/main.py)
│       ├── workspace_tab.py          # deck canvas — placement, collision, slots
│       ├── labware_browser.py        # labware library browser (search / filter)
│       ├── led_tab.py                # 24-LED illumination panel
│       ├── sidebar.py                # sidebar — actions & experience name
│       ├── coords.py                 # canvas ↔ machine mm transforms
│       ├── exporter.py               # JSON / DXF / G-code exports
│       ├── deck_3d_exporter.py       # async 3-D pipeline: SCAD → STL → .blend
│       ├── labware_to_scad.py        # labware → OpenSCAD geometry
│       ├── assemble_deck.py          # Blender-headless STL importer
│       ├── models.py                 # DraggableObject + labware dim loader
│       ├── app_paths.py              # experiment folder / labware repo resolution
│       ├── constants.py              # physical, graphical, and path constants
│       └── theme.py                  # colour palette
├── tests/                            # pytest suite (no display required)
│   ├── conftest.py
│   ├── test_coords.py
│   ├── test_exporter.py
│   └── test_app_paths.py
└── archive/                          # historical prototypes (not installed)
```

---

## Development

```bash
pip install -e ".[testing]"
python -m pytest -v
```

The test suite runs without a display: canvases and file I/O are stubbed with
`unittest.mock` and `tmp_path`.

Every touched module compiles clean under `python -m py_compile`. The
`bpy` / `mathutils` imports in the digital-twin add-on remain intentionally
unresolvable outside Blender.

---

## Troubleshooting

**"jubilee-labware is not installed" when the Labware Browser opens**

Install the labware repo into the same virtual environment:

```bash
pip install -e path/to/jubilee-labware
```

**"jubilee-blender-twin n'est pas enregistré" when clicking *Lancer Jumeau Numérique***

Install the twin so its `jubilee.paths / twin_dir` entry point registers:

```bash
pip install -e path/to/jubilee-blender-twin
```

**Empty G-code dropdown in the sidebar**

The sidebar lists `.gcode` files from `<science-jubilee>/gcode_logs/`. Install
science-jubilee (`pip install -e path/to/science-jubilee`) and make sure at
least one recording exists.

**My old `experience.json` no longer loads correctly**

Files saved before the coordinate refactor use a different convention; delete
the old folder or re-place the labware and Save-All again.

---

## Ecosystem

| Package | Role |
|---|---|
| [science-jubilee](https://github.com/machineagency/science-jubilee) | Motion driver, deck / tool / labware classes, HAL |
| [jubilee-labware](https://github.com/Jubilee-CSL/labware) | Labware JSON + STL definitions |
| **science-jubilee-interface** *(this repo)* | GUI for deck design & experiment export |
| [jubilee-blender-twin](https://github.com/Jubilee-CSL/jubilee-blender-twin) | Digital twin in Blender — animation & collision detection |
