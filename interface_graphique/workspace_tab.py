"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : workspace_tab.py
Description : Canvas interactif du plateau Jubilee (placement, collisions, slots).
=========================================================================================
"""

import json
import os
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import app_paths
import exporter
import theme
from constants import (
    LABWARE, MARGIN_BETWEEN_OBJECTS_PX, MARGIN_BORDER_PX, MM_TO_PIX,
    OUTIL_SLOTS, OUTILS_LISTE, PLATEAU_H, PLATEAU_H_MM, PLATEAU_W, PLATEAU_W_MM,
)
from models import DraggableObject, load_labware_dims

_SLOT_GAP     = 30   # px : distance entre le plateau et la colonne de slots
_SLOT_WIDTH   = 60
_SLOT_HEIGHT  = 90
_SLOT_V_GAP   = 20   # px : espace vertical entre deux slots


class WorkspaceTab(ctk.CTkFrame):
    def __init__(self, parent, on_selection_change, **kwargs):
        super().__init__(parent, **kwargs)
        self._notify_selection = on_selection_change

        self.selected_tool_name: str | None = None
        self.placed_objects: list[DraggableObject] = []
        self.slot_assignments: dict[int, str] = {sid: "None" for sid in OUTIL_SLOTS}
        self._browser_labware: dict[str, dict] = {}

        self._slot_rects: dict[int, int] = {}
        self._slot_text_ids: dict[int, int] = {}
        self._slot_windows: dict[int, ctk.CTkToplevel] = {}

        self._build_canvas()
        self._setup_tool_slots()

    # ─── Canvas ──────────────────────────────────────────────────────────────

    def _build_canvas(self):
        self.canvas = tk.Canvas(self, bg="#111213", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both")

        self.canvas_plateau = self.canvas.create_rectangle(
            0, 0, PLATEAU_W, PLATEAU_H,
            fill="white", outline="#888888", width=2, tags="__background__",
        )
        self.canvas_marge = self.canvas.create_rectangle(
            0, 0, 0, 0, fill="", outline="red",
            width=2, dash=(4, 4), tags="plateau_marge",
        )
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Configure>", self._draw_grid)

    def _setup_tool_slots(self):
        """Crée les rectangles des slots d'outils (positions fixées dans _reposition_tool_slots)."""
        for slot_id in OUTIL_SLOTS:
            tag = f"outil_{slot_id}"
            rect = self.canvas.create_rectangle(
                0, 0, _SLOT_WIDTH, _SLOT_HEIGHT,
                fill="#dddddd", outline="#888", width=2,
                tags=(tag, "slot_outil_rect"),
            )
            txt = self.canvas.create_text(
                _SLOT_WIDTH / 2, 25,
                text="None", fill="black", font=("Arial", 10, "bold"),
                tags=(f"slot_text_{slot_id}", "slot_outil_text"),
            )
            self._slot_rects[slot_id] = rect
            self._slot_text_ids[slot_id] = txt
            self.canvas.tag_bind(
                tag, "<Button-1>",
                lambda e, s=slot_id: self._open_slot_config(s),
            )

    def _reposition_tool_slots(self, plateau_x2: float, plateau_y1: float):
        """Place la colonne de slots immédiatement à droite du plateau."""
        x0 = plateau_x2 + _SLOT_GAP
        for idx, slot_id in enumerate(sorted(OUTIL_SLOTS.keys())):
            y0 = plateau_y1 + idx * (_SLOT_HEIGHT + _SLOT_V_GAP)
            self.canvas.coords(
                self._slot_rects[slot_id],
                x0, y0, x0 + _SLOT_WIDTH, y0 + _SLOT_HEIGHT,
            )
            self.canvas.coords(
                self._slot_text_ids[slot_id],
                x0 + _SLOT_WIDTH / 2, y0 + _SLOT_HEIGHT / 2,
            )

    # ─── Selection ───────────────────────────────────────────────────────────

    def select_local_labware(self, name: str):
        self.selected_tool_name = name
        self._notify_selection(name)

    def select_dynamic_labware(self, meta: dict):
        load_name = meta["loadName"]
        self._browser_labware[load_name] = meta
        self.selected_tool_name = load_name
        self._notify_selection(meta.get("displayName", load_name))

    def _reset_selection(self):
        self.selected_tool_name = None
        self._notify_selection("Aucun")

    # ─── Placement ───────────────────────────────────────────────────────────

    def _on_canvas_click(self, event):
        if self.selected_tool_name is None:
            return
        resolved = self._resolve_selected_labware()
        if resolved is None:
            return
        json_file, w_px, h_px, display_name, color = resolved

        x, y = event.x - w_px / 2, event.y - h_px / 2
        if not self._is_inside_plateau(x, y, w_px, h_px):
            return
        if not self._is_free_space(x, y, w_px, h_px):
            return

        obj = DraggableObject(
            self.canvas, x, y, json_file, color, display_name,
            self._is_free_space, self._is_inside_plateau,
        )
        self.placed_objects.append(obj)
        self._reset_selection()

    def _resolve_selected_labware(self):
        name = self.selected_tool_name
        if name in self._browser_labware:
            meta = self._browser_labware[name]
            return (
                meta.get("fullJsonPath", ""),
                meta["xDimension"] * MM_TO_PIX,
                meta["yDimension"] * MM_TO_PIX,
                meta.get("displayName", name),
                theme.category_color(meta.get("displayCategory", "")),
            )

        entry = LABWARE.get(name)
        if not entry:
            return None
        data = load_labware_dims(entry["json"])
        if not data:
            return None
        return (
            entry["json"],
            data["dimensions"]["xDimension"] * MM_TO_PIX,
            data["dimensions"]["yDimension"] * MM_TO_PIX,
            name,
            theme.local_labware_color(name),
        )

    # ─── Validation ──────────────────────────────────────────────────────────

    def _is_inside_plateau(self, x1, y1, w, h) -> bool:
        px1, py1, px2, py2 = self.canvas.coords(self.canvas_plateau)
        return (
            x1 >= px1 + MARGIN_BORDER_PX
            and y1 >= py1 + MARGIN_BORDER_PX
            and x1 + w <= px2 - MARGIN_BORDER_PX
            and y1 + h <= py2 - MARGIN_BORDER_PX
        )

    def _is_free_space(self, x1, y1, w, h, ignore_id=None) -> bool:
        m = MARGIN_BETWEEN_OBJECTS_PX
        for other in self.placed_objects:
            if other.id == ignore_id:
                continue
            ox1, oy1, ox2, oy2 = self.canvas.coords(other.id)
            if not (
                x1 + w < ox1 - m or x1 > ox2 + m
                or y1 + h < oy1 - m or y1 > oy2 + m
            ):
                return False
        return True

    # ─── Delete ──────────────────────────────────────────────────────────────

    def delete_object_under_cursor(self, event=None):
        x, y = self.winfo_pointerxy()
        cx = self.canvas.canvasx(x - self.canvas.winfo_rootx())
        cy = self.canvas.canvasy(y - self.canvas.winfo_rooty())
        items = self.canvas.find_overlapping(cx, cy, cx, cy)
        for obj in self.placed_objects:
            if obj.id in items:
                for item in obj.items:
                    self.canvas.delete(item)
                self.placed_objects.remove(obj)
                return

    # ─── Tool slots ──────────────────────────────────────────────────────────

    def _open_slot_config(self, slot_id: int):
        if slot_id in self._slot_windows:
            self._slot_windows[slot_id].lift()
            return

        win = ctk.CTkToplevel(self)
        win.title(f"Config Slot {slot_id}")
        win.geometry("240x160")
        self._slot_windows[slot_id] = win

        ctk.CTkLabel(win, text="Outil à charger :").pack(pady=(10, 0))
        combo = ctk.CTkComboBox(win, values=OUTILS_LISTE)
        combo.set(self.slot_assignments[slot_id])
        combo.pack(pady=10)

        def close():
            self._slot_windows.pop(slot_id, None)
            win.destroy()

        def validate():
            val = combo.get()
            self._update_slot_display(slot_id, val)
            close()

        ctk.CTkButton(win, text="Valider", command=validate).pack(pady=5)
        win.protocol("WM_DELETE_WINDOW", close)

    def _update_slot_display(self, slot_id: int, tool: str):
        self.slot_assignments[slot_id] = tool
        self.canvas.itemconfig(self._slot_text_ids[slot_id], text=tool)
        self.canvas.itemconfig(
            self._slot_rects[slot_id],
            fill="#aaffaa" if tool != "None" else "#dddddd",
        )

    # ─── Grid ────────────────────────────────────────────────────────────────

    def _draw_grid(self, event=None):
        self.canvas.delete("__grid__")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        # Décale le plateau à gauche pour réserver de la place pour la colonne de slots
        reserved_right = _SLOT_GAP + _SLOT_WIDTH + 20
        cx = max(PLATEAU_W / 2 + 20, (w - reserved_right) / 2)
        cy = h / 2
        x1, y1 = cx - PLATEAU_W / 2, cy - PLATEAU_H / 2
        x2, y2 = cx + PLATEAU_W / 2, cy + PLATEAU_H / 2

        self.canvas.coords(self.canvas_plateau, x1, y1, x2, y2)
        self.canvas.coords(
            self.canvas_marge,
            x1 + MARGIN_BORDER_PX, y1 + MARGIN_BORDER_PX,
            x2 - MARGIN_BORDER_PX, y2 - MARGIN_BORDER_PX,
        )

        # Replace les slots d'outils à droite du plateau
        self._reposition_tool_slots(x2, y1)

        for i in range(0, w, 20):
            self.canvas.create_line(i, 0, i, h, fill="#1b1b1b", tags="__grid__")
        for i in range(0, h, 20):
            self.canvas.create_line(0, i, w, i, fill="#1b1b1b", tags="__grid__")
        self.canvas.tag_lower("__grid__")
        self.canvas.tag_lower(self.canvas_plateau)

    # ─── Save / Load / Clear ─────────────────────────────────────────────────

    def clear_canvas(self, confirm: bool = True):
        if confirm and not messagebox.askyesno(
            "Confirmation", "Voulez-vous vraiment vider tout le plateau ?"
        ):
            return
        for obj in self.placed_objects:
            for item in obj.items:
                self.canvas.delete(item)
        self.placed_objects.clear()

    def save_configuration(self):
        exporter.export_layout(
            self.placed_objects, self.slot_assignments,
            self.canvas, self.canvas_plateau,
        )
        messagebox.showinfo("Exportation", "Configuration du deck sauvegardée.")

    def load_configuration(self, json_file: str = "experience.json"):
        json_path = app_paths.resolve_deck_json(json_file)
        if not os.path.exists(json_path):
            messagebox.showerror("Erreur", f"Fichier introuvable :\n{json_path}")
            return
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Erreur", f"Lecture JSON impossible :\n{e}")
            return

        self.clear_canvas(confirm=False)
        self._restore_labwares(data)
        self._restore_tool_slots(data)

    def _restore_labwares(self, data: dict):
        x0, y0, x1, y1 = self.canvas.coords(self.canvas_plateau)
        scale_h = (x1 - x0) / PLATEAU_W_MM
        scale_v = (y1 - y0) / PLATEAU_H_MM

        for slot in data.get("slots", {}).values():
            if not slot.get("has_labware"):
                continue
            x_px = x0 + slot["coordinates"][1] * scale_h
            y_px = y0 + slot["coordinates"][0] * scale_v
            name = next(
                (k for k, v in LABWARE.items() if v["json"] == slot["labware"]),
                "Labware",
            )
            obj = DraggableObject(
                self.canvas, x_px, y_px, slot["labware"], "#1f6aa5", name,
                self._is_free_space, self._is_inside_plateau,
            )
            self.placed_objects.append(obj)

    def _restore_tool_slots(self, data: dict):
        for sid_str, tool in data.get("tool_slots", {}).items():
            sid = int(sid_str) + 1
            if sid in self.slot_assignments:
                self._update_slot_display(sid, tool)
