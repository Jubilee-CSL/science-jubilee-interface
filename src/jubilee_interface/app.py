"""
=========================================================================================
Projet      : Jubilee Bioreactor GUI
Fichier     : main.py
Auteur      : [SABATIÉ Léo / Projet industriel ROB4]
Description : Point d'entrée de l'application.
              Orchestre la sidebar, les onglets et les callbacks inter-panneaux.
=========================================================================================
"""

import customtkinter as ctk

from jubilee_interface import app_paths, deck_3d_exporter, exporter
from jubilee_interface.constants import PLATEAU_H, PLATEAU_W
from jubilee_interface.labware_browser import LabwareBrowserFrame
from jubilee_interface.led_tab import LedControlTab
from jubilee_interface.sidebar import Sidebar, SidebarCallbacks
from jubilee_interface.workspace_tab import WorkspaceTab


class App(ctk.CTk):
    """Application principale — assemble les panneaux et relie les callbacks."""

    TAB_WORKSPACE = "Plan du Plateau"
    TAB_LED       = "Contrôle Lumineux"
    TAB_BROWSER   = "Bibliothèque Labware"

    def __init__(self):
        super().__init__()
        self.title("Jubilee Bioreactor — Workspace & LED Control")
        self.geometry(f"{PLATEAU_W + 400}x{PLATEAU_H + 150}")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.selected_gcode: str | None = None

        self._build_ui()
        self._bind_shortcuts()

    # ─── Construction UI ─────────────────────────────────────────────────────

    def _build_ui(self):
        # --- ONGLETS (créés avant la sidebar pour que les callbacks existent) --
        self.tabview = ctk.CTkTabview(self)

        tab_workspace = self.tabview.add(self.TAB_WORKSPACE)
        tab_led       = self.tabview.add(self.TAB_LED)
        tab_browser   = self.tabview.add(self.TAB_BROWSER)

        self.workspace = WorkspaceTab(
            tab_workspace,
            on_selection_change=self._on_selection_change,
        )
        self.workspace.pack(expand=True, fill="both")

        self.led_panel = LedControlTab(tab_led)
        self.led_panel.pack(expand=True, fill="both")

        LabwareBrowserFrame(
            tab_browser,
            on_select_callback=self._on_browser_select,
            fg_color="transparent",
        ).pack(fill="both", expand=True)

        # --- SIDEBAR ---------------------------------------------------------
        self.sidebar = Sidebar(self, self._build_sidebar_callbacks())
        self.sidebar.pack(side="left", fill="y", padx=12, pady=12)

        self.tabview.pack(side="right", expand=True, fill="both", padx=12, pady=12)

    def _build_sidebar_callbacks(self) -> SidebarCallbacks:
        return SidebarCallbacks(
            save_all=self._save_all,
            load_config=self.workspace.load_configuration,
            clear_canvas=self.workspace.clear_canvas,
            choose_gcode=self._choose_gcode,
            launch_twinsim=self._launch_twinsim,
            launch_raytracing=self._launch_raytracing,
        )

    def _bind_shortcuts(self):
        self.bind("<Delete>", self.workspace.delete_object_under_cursor)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _save_all(self):
        """Exporte tout en une seule action : JSON, DXF, G-code, LED, puis 3D async."""
        import os
        from tkinter import messagebox

        # 1. JSON (configuration du plateau)
        exporter.export_layout(
            self.workspace.placed_objects,
            self.workspace.slot_assignments,
            self.workspace.canvas,
            self.workspace.canvas_plateau,
        )

        # 2. deck.json + labware JSONs (format science_jubilee, chemins relatifs)
        exporter.export_deck_with_labware(
            self.workspace.placed_objects,
            self.workspace.canvas,
            self.workspace.canvas_plateau,
        )

        # 3. LED pattern
        exporter.export_led_pattern(self.led_panel.light_values)

        # 4. DXF
        exporter.export_to_dxf("experience.json")

        # 5. G-code
        exporter.json_to_gcode("experience.json", "plan_jubilee.gcode")

        folder = app_paths.experience_dir()

        # 5. 3D async (SCAD / STL / .blend) — single popup shown on completion
        if not self.workspace.placed_objects:
            if messagebox.askyesno(
                "Sauvegarde terminée",
                f"JSON, LED, DXF et G-code exportés.\n\n\U0001f4c1 {folder}\n\nOuvrir le dossier ?",
            ):
                os.startfile(folder)
            return

        def on_done(result: deck_3d_exporter.ExportResult):
            def _show():
                msg = (
                    f"JSON, LED, DXF, G-code exportés.\n"
                    f"SCAD : {len(result.scad_files)}  •  STL : {len(result.stl_files)}  •  "
                    f".blend : {'oui' if result.blend_file else 'non'}"
                )
                if result.warnings:
                    msg += "\n\n⚠ " + "\n⚠ ".join(result.warnings)
                msg += f"\n\n\U0001f4c1 {result.output_dir}"
                if messagebox.askyesno("Sauvegarde terminée", msg + "\n\nOuvrir le dossier ?"):
                    os.startfile(result.output_dir)
            self.after(0, _show)

        def on_error(exc: Exception):
            self.after(0, lambda: messagebox.showerror("Export 3D", str(exc)))

        deck_3d_exporter.export_deck_3d_async(
            placed_objects=list(self.workspace.placed_objects),
            canvas=self.workspace.canvas,
            canvas_plateau=self.workspace.canvas_plateau,
            on_done=on_done,
            on_error=on_error,
            on_progress=lambda step: print(f"[3D] {step}"),
        )

    def _notify_export(self, title: str, detail: str = ""):
        """Affiche le dossier de sortie après un export + bouton pour l'ouvrir."""
        import os
        from tkinter import messagebox
        folder = app_paths.experience_dir()
        msg = f"{detail}\n\n\U0001f4c1 {folder}" if detail else f"\U0001f4c1 {folder}"
        if messagebox.askyesno(title, msg + "\n\nOuvrir le dossier ?"):
            os.startfile(folder)

    def _choose_gcode(self,filename):
        self.selected_gcode = filename

    def _launch_twinsim(self):
        if not self.selected_gcode:
            return
        exporter.testgcode_to_twin(self.selected_gcode)

    def _launch_raytracing(self):
        exporter.launch_raytracing()

    # ─── Callbacks inter-panneaux ────────────────────────────────────────────

    def _on_browser_select(self, meta: dict):
        self.workspace.select_dynamic_labware(meta)
        self.tabview.set(self.TAB_WORKSPACE)

    def _on_selection_change(self, label: str):
        self.sidebar.set_selected_label(label)


def main() -> None:
    """Console-script entry point (`jubilee-gui`)."""
    App().mainloop()


if __name__ == "__main__":
    main()
