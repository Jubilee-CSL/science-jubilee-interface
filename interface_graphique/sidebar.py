"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : sidebar.py
Description : Barre latérale — navigation et actions globales.
=========================================================================================
"""

from dataclasses import dataclass
from typing import Callable

import customtkinter as ctk

import app_paths


@dataclass
class SidebarCallbacks:
    show_browser_tab:  Callable[[], None]
    show_led_tab:      Callable[[], None]
    save_config:       Callable[[], None]
    load_config:       Callable[[], None]
    export_dxf:        Callable[[], None]
    export_gcode:      Callable[[], None]
    export_3d:         Callable[[], None]
    clear_canvas:      Callable[[], None]


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, callbacks: SidebarCallbacks, **kwargs):
        super().__init__(parent, width=260, **kwargs)
        self._cb = callbacks
        self._build()

    def _build(self):
        ctk.CTkLabel(
            self, text="Jubilee", font=("Arial", 18, "bold"),
        ).pack(pady=(6, 12))

        self.lbl_selected = ctk.CTkLabel(
            self, text="Outil sélectionné:\nAucun", font=("Arial", 12),
        )
        self.lbl_selected.pack(pady=(12, 8))

        # ── Nom de l'expérience (dossier de sortie unique) ──────────────────
        ctk.CTkLabel(
            self, text="Nom de l'expérience :",
            font=("Arial", 11),
        ).pack(pady=(8, 2), padx=10, anchor="w")

        self._exp_var = ctk.StringVar(value=app_paths.get_experience_name())
        self._exp_entry = ctk.CTkEntry(
            self, textvariable=self._exp_var,
            placeholder_text="experience",
        )
        self._exp_entry.pack(fill="x", pady=(0, 2), padx=10)
        self._exp_var.trace_add(
            "write",
            lambda *_: app_paths.set_experience_name(self._exp_var.get().strip()),
        )
        ctk.CTkLabel(
            self,
            text="Tous les exports (JSON, DXF, G-code,\nSCAD, STL, .blend, LED) sont\nregroupés dans ce dossier.",
            font=("Arial", 9), text_color="gray",
            justify="left",
        ).pack(pady=(0, 6), padx=10, anchor="w")

        ctk.CTkLabel(self, text="--- Actions ---").pack(pady=(20, 5))

        ctk.CTkButton(
            self, text="BIBLIOTHÈQUE LABWARE",
            fg_color="#1565c0", hover_color="#0d47a1",
            font=("Arial", 13, "bold"),
            command=self._cb.show_browser_tab,
        ).pack(fill="x", pady=(4, 4), padx=10)

        ctk.CTkButton(
            self, text="PLATEAU LUMINEUX",
            fg_color="#2e7d32", hover_color="#1b5e20",
            font=("Arial", 13, "bold"),
            command=self._cb.show_led_tab,
        ).pack(fill="x", pady=(4, 10), padx=10)

        ctk.CTkButton(
            self, text="Exporter Configuration",
            fg_color="#1976d2",
            command=self._cb.save_config,
        ).pack(fill="x", pady=4, padx=10)

        ctk.CTkButton(
            self, text="Charger Configuration",
            command=self._cb.load_config,
        ).pack(fill="x", pady=4, padx=10)

        ctk.CTkButton(
            self, text="Plan Laser Cut (DXF)",
            command=self._cb.export_dxf,
        ).pack(fill="x", pady=4, padx=10)

        ctk.CTkButton(
            self, text="G-code Dessin (Stylo)",
            command=self._cb.export_gcode,
        ).pack(fill="x", pady=4, padx=10)

        ctk.CTkButton(
            self, text="Modèle 3D (SCAD / STL / .blend)",
            fg_color="#6a1b9a", hover_color="#4a148c",
            command=self._cb.export_3d,
        ).pack(fill="x", pady=4, padx=10)

        ctk.CTkButton(
            self, text="Vider plateau",
            fg_color="#c62828",
            command=self._cb.clear_canvas,
        ).pack(fill="x", pady=4, padx=10)

        ctk.CTkLabel(
            self,
            text=(
                "Raccourcis :\n"
                "- Clic gauche : Placer/Déplacer\n"
                "- Clic droit : Rotation 90°\n"
                "- Suppr : Supprimer l'objet"
            ),
            wraplength=220, justify="left",
            font=("Arial", 10), text_color="gray",
        ).pack(pady=20)

    def set_selected_label(self, name: str):
        self.lbl_selected.configure(text=f"Outil sélectionné:\n{name}")
