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

import exporter
import deck_3d_exporter
from constants import PLATEAU_H, PLATEAU_W
from labware_browser import LabwareBrowserFrame
from led_tab import LedControlTab
from sidebar import Sidebar, SidebarCallbacks
from workspace_tab import WorkspaceTab


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
            show_browser_tab=lambda: self.tabview.set(self.TAB_BROWSER),
            show_led_tab=lambda: self.tabview.set(self.TAB_LED),
            save_config=self.workspace.save_configuration,
            load_config=self.workspace.load_configuration,
            export_dxf=lambda: exporter.export_to_dxf("experience.json"),
            export_gcode=lambda: exporter.json_to_gcode(
                "experience.json", "plan_jubilee.txt"
            ),
            export_3d=self._export_3d,
            clear_canvas=self.workspace.clear_canvas,
        )

    def _bind_shortcuts(self):
        self.bind("<Delete>", self.workspace.delete_object_under_cursor)

    # ─── Callbacks inter-panneaux ────────────────────────────────────────────

    def _on_browser_select(self, meta: dict):
        self.workspace.select_dynamic_labware(meta)
        self.tabview.set(self.TAB_WORKSPACE)

    def _on_selection_change(self, label: str):
        self.sidebar.set_selected_label(label)


    # ─── Export 3D ───────────────────────────────────────────────────────────

    def _export_3d(self):
        """Lance l'export 3D (SCAD → STL → .blend) en arrière-plan."""
        from tkinter import messagebox

        placed = list(self.workspace.placed_objects)
        if not placed:
            messagebox.showwarning(
                "Export 3D", "Aucun labware placé — ajoutez au moins un objet."
            )
            return

        def on_done(result: deck_3d_exporter.ExportResult):
            msg = (
                f"Export 3D terminé.\n\n"
                f"Dossier : {result.output_dir}\n"
                f"SCAD : {len(result.scad_files)} fichier(s)\n"
                f"STL  : {len(result.stl_files)} fichier(s)\n"
                f".blend : {'oui' if result.blend_file else 'non'}"
            )
            if result.warnings:
                msg += "\n\nAvertissements :\n- " + "\n- ".join(result.warnings)
            self.after(0, lambda: messagebox.showinfo("Export 3D", msg))

        def on_error(exc: Exception):
            self.after(0, lambda: messagebox.showerror("Export 3D", str(exc)))

        def on_progress(step: str):
            print(f"[3D] {step}")

        deck_3d_exporter.export_deck_3d_async(
            placed_objects=placed,
            canvas=self.workspace.canvas,
            canvas_plateau=self.workspace.canvas_plateau,
            on_done=on_done,
            on_error=on_error,
            on_progress=on_progress,
        )


if __name__ == "__main__":
    App().mainloop()
