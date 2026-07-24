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
import os


@dataclass
class SidebarCallbacks:
    save_all:     Callable[[], None]
    load_config:  Callable[[], None]
    clear_canvas: Callable[[], None]
    choose_gcode:  Callable[[], None]
    launch_twinsim: Callable[[], None]
    launch_raytracing: Callable[[], None]



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
        self._exp_entry.pack(fill="x", pady=(0, 4), padx=10)
        self._exp_entry.bind("<Return>", lambda _: self._confirm_experience_name())
        self._exp_entry.bind("<FocusOut>", lambda _: self._confirm_experience_name())
        ctk.CTkLabel(
            self,
            text="Tous les exports (JSON, DXF, G-code,\nSCAD, STL, .blend, LED) sont\nregroupés dans ce dossier.",
            font=("Arial", 9), text_color="gray",
            justify="left",
        ).pack(pady=(0, 6), padx=10, anchor="w")

        ctk.CTkLabel(self, text="--- Actions ---").pack(pady=(20, 5))

        ctk.CTkButton(
            self, text="💾  SAUVEGARDER",
            height=44, font=("Arial", 14, "bold"),
            fg_color="#1565c0", hover_color="#0d47a1",
            command=self._cb.save_all,
        ).pack(fill="x", pady=(4, 2), padx=10)
        ctk.CTkLabel(
            self,
            text="JSON • DXF • G-code • 3D (.blend)",
            font=("Arial", 9), text_color="gray",
        ).pack(pady=(0, 4), padx=10)

        ctk.CTkButton(
            self, text="Charger Configuration",
            command=self._cb.load_config,
        ).pack(fill="x", pady=4, padx=10)

        ctk.CTkButton(
            self, text="Vider plateau",
            fg_color="#c62828",
            command=self._cb.clear_canvas,
        ).pack(fill="x", pady=4, padx=10)

        self.folder = app_paths.gcode_log_dir()
        self.filelist = [fname for fname in os.listdir(self.folder)]

        ctk.CTkLabel(self, text="Choisir un gcode:").pack(pady=(0, 4), padx=10)
        initial_val = self.filelist[0] 
        self.gcode_filename = ctk.StringVar(value=initial_val)
        ctk.CTkOptionMenu(
            self, values=list(self.filelist),
            variable=self.gcode_filename,
            command=lambda choice: self._cb.choose_gcode(choice),
            width=150,anchor='n'
        ).pack(fill="x", pady=4, padx=10)

        ctk.CTkButton(
            self, text="Lancer Jumeau Numérique",
            command=self._cb.launch_twinsim,
        ).pack(fill="x", pady=4, padx=10)

        ctk.CTkButton(
            self, text="Lancer Raytracing",
            command=self._cb.launch_raytracing,
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

    def _confirm_experience_name(self):
        name = self._exp_var.get().strip() or "experience"
        self._exp_var.set(name)
        app_paths.set_experience_name(name)
