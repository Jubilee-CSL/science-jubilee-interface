"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : led_tab.py
Description : Panneau de contrôle des 24 LEDs (PCA9685).
=========================================================================================
"""

from tkinter import messagebox

import customtkinter as ctk

import exporter
from constants import MAX_ILLUMINANCE

_NB_LEDS = 24
_COLS    = 6


class LedControlTab(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.light_values: dict[int, int] = {i: 0 for i in range(_NB_LEDS)}
        self._sliders: dict[int, ctk.CTkSlider] = {}
        self._entry_vars: dict[int, ctk.StringVar] = {}

        self._build_ui()

    def _build_ui(self):
        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(expand=True, fill="both", padx=10, pady=10)

        for i in range(_NB_LEDS):
            row, col = divmod(i, _COLS)
            self._build_led_card(grid, i).grid(
                row=row, column=col, padx=5, pady=5, sticky="nsew",
            )

        ctk.CTkButton(
            self, text="EXPORTER CONFIGURATION LED (ESP32)",
            fg_color="#2e7d32", height=40,
            font=("Arial", 14, "bold"),
            command=self._export_pattern,
        ).pack(pady=20)

    def _build_led_card(self, parent, idx: int) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, border_width=1, border_color="#444")
        ctk.CTkLabel(
            card, text=f"Puit {idx + 1}", font=("Arial", 12, "bold"),
        ).pack(pady=(5, 0))

        var = ctk.StringVar(value="0")
        self._entry_vars[idx] = var

        entry = ctk.CTkEntry(card, textvariable=var, width=60, justify="center")
        entry.pack(pady=2)
        entry.bind("<Return>", lambda _e, i=idx: self._sync_entry_to_slider(i))

        slider = ctk.CTkSlider(
            card, from_=0, to=MAX_ILLUMINANCE,
            number_of_steps=MAX_ILLUMINANCE, width=120,
            command=lambda val, i=idx: self._sync_slider_to_entry(i, val),
        )
        slider.set(0)
        slider.pack(pady=(0, 10), padx=5)
        self._sliders[idx] = slider
        return card

    def _sync_slider_to_entry(self, idx: int, val: float):
        value = int(val)
        self.light_values[idx] = value
        self._entry_vars[idx].set(str(value))

    def _sync_entry_to_slider(self, idx: int):
        try:
            val = int(self._entry_vars[idx].get())
        except ValueError:
            self._entry_vars[idx].set(str(int(self._sliders[idx].get())))
            return
        val = max(0, min(MAX_ILLUMINANCE, val))
        self.light_values[idx] = val
        self._sliders[idx].set(val)
        self._entry_vars[idx].set(str(val))

    def _export_pattern(self):
        exporter.export_led_pattern(self.light_values)
        messagebox.showinfo(
            "Exportation",
            "Le pattern LED a été exporté avec succès pour l'ESP32.",
        )
