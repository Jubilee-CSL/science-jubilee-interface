"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : labware_browser.py
Description : Navigateur visuel de la bibliothèque de labwares Opentrons
              (https://labware.opentrons.com/). Cache local + filtres + images.
=========================================================================================
"""

import customtkinter as ctk
import json
import os
import threading

import app_paths
import theme

try:
    import requests
    from PIL import Image
    from io import BytesIO
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

_GITHUB_DIR_URL = (
    "https://api.github.com/repos/Opentrons/opentrons/contents"
    "/shared-data/labware/definitions/2"
)
_RAW_BASE_URL = (
    "https://raw.githubusercontent.com/Opentrons/opentrons/edge"
    "/shared-data/labware/definitions/2"
)
_IMG_BASE_URL = "https://labware.opentrons.com/labware-images"

CACHE_DIR = app_paths.labware_cache_dir()

_CARDS_PER_ROW = 4
_IMG_W, _IMG_H = 140, 90

_CATEGORY_LABELS = {
    "Tous":            None,
    "Plaque de puits": "wellPlate",
    "Réservoir":       "reservoir",
    "Rack à tubes":    "tubeRack",
    "Bloc aluminium":  "aluminumBlock",
    "Rack à tips":     "tipRack",
    "Adaptateur":      "adapter",
    "Couvercle":       "lid",
}

_CATEGORY_COLORS = theme.CATEGORY_COLORS


class LabwareBrowserFrame(ctk.CTkFrame):
    def __init__(self, parent, on_select_callback, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_select_callback = on_select_callback
        self._all_cards: list[tuple[dict, ctk.CTkFrame]] = []
        self._images: dict[str, ctk.CTkImage] = {}

        os.makedirs(CACHE_DIR, exist_ok=True)
        self._build_ui()

        if not _DEPS_OK:
            self._status(
                "⚠  Modules manquants — installez : pip install requests Pillow",
                color="#e53935",
            )
            return

        threading.Thread(target=self._load_all_definitions, daemon=True).start()

    # ─── UI ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=12, pady=(10, 6))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filters())

        ctk.CTkLabel(toolbar, text="🔍", font=("Arial", 14)).pack(side="left")
        ctk.CTkEntry(
            toolbar, textvariable=self.search_var,
            placeholder_text="Rechercher par nom, marque ou API name…",
            width=300,
        ).pack(side="left", padx=(4, 16))

        ctk.CTkLabel(toolbar, text="Catégorie :").pack(side="left")
        self.cat_var = ctk.StringVar(value="Tous")
        ctk.CTkOptionMenu(
            toolbar, values=list(_CATEGORY_LABELS.keys()),
            variable=self.cat_var,
            command=lambda _: self._apply_filters(),
            width=180,
        ).pack(side="left", padx=(4, 0))

        self.status_lbl = ctk.CTkLabel(
            toolbar, text="En attente…", text_color="#888", font=("Arial", 11),
        )
        self.status_lbl.pack(side="right", padx=10)

        self.grid_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        for col in range(_CARDS_PER_ROW):
            self.grid_frame.columnconfigure(col, weight=1, uniform="col")

    def _status(self, text: str, color: str = "#888"):
        self.status_lbl.configure(text=text, text_color=color)

    # ─── Data fetching ───────────────────────────────────────────────────────

    def _load_all_definitions(self):
        try:
            resp = requests.get(_GITHUB_DIR_URL, timeout=12)
            resp.raise_for_status()
            entries = resp.json()
        except Exception as exc:
            self.after(0, lambda: self._status(f"Erreur réseau : {exc}", "#e53935"))
            return

        names = [e["name"] for e in entries if e["type"] == "dir"]
        total = len(names)
        metas: list[dict] = []

        for idx, name in enumerate(names):
            meta = self._fetch_meta(name)
            if meta:
                metas.append(meta)
            self.after(0, lambda n=idx + 1: self._status(f"Chargement… {n}/{total}"))

        self.after(0, lambda: self._populate_grid(metas))

    def _fetch_meta(self, load_name: str):
        meta_path = os.path.join(CACHE_DIR, f"{load_name}_meta.json")
        full_path = os.path.join(CACHE_DIR, f"{load_name}.json")

        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        for version in (3, 2, 1):
            url = f"{_RAW_BASE_URL}/{load_name}/{version}.json"
            try:
                r = requests.get(url, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    with open(full_path, "w", encoding="utf-8") as f:
                        json.dump(data, f)
                    meta = _extract_meta(data, load_name, full_path)
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta, f)
                    return meta
            except Exception:
                continue
        return None

    # ─── Grid ────────────────────────────────────────────────────────────────

    def _populate_grid(self, metas: list[dict]):
        self._all_cards.clear()
        for idx, meta in enumerate(sorted(metas, key=lambda m: m["displayName"].lower())):
            row, col = divmod(idx, _CARDS_PER_ROW)
            card = self._make_card(meta)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            self._all_cards.append((meta, card))

        self._status(f"✓  {len(metas)} labwares chargés", "#4caf50")
        threading.Thread(target=self._load_all_images, daemon=True).start()

    def _make_card(self, meta: dict) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self.grid_frame, fg_color="#1c1c1e",
            border_width=1, border_color="#2e2e30",
            corner_radius=10, cursor="hand2",
        )

        img_lbl = ctk.CTkLabel(
            card, text="⋯", width=_IMG_W, height=_IMG_H,
            fg_color="#111111", corner_radius=6,
            font=("Arial", 22), text_color="#444",
        )
        img_lbl.pack(padx=10, pady=(10, 4))
        card._img_label = img_lbl

        cat = meta.get("displayCategory", "")
        ctk.CTkLabel(
            card, text=cat or "—",
            fg_color=_CATEGORY_COLORS.get(cat, "#333"), corner_radius=4,
            font=("Arial", 9, "bold"), text_color="white", height=20,
        ).pack(padx=10, pady=(0, 2), anchor="w")

        if meta.get("brand"):
            ctk.CTkLabel(
                card, text=meta["brand"],
                font=("Arial", 9), text_color="#888",
            ).pack(padx=10, anchor="w")

        ctk.CTkLabel(
            card, text=meta["displayName"],
            font=("Arial", 11, "bold"),
            wraplength=170, justify="left",
        ).pack(padx=10, pady=(2, 0), anchor="w")

        stats_row = ctk.CTkFrame(card, fg_color="transparent")
        stats_row.pack(padx=10, pady=(4, 2), fill="x")
        if meta.get("wellCount"):
            ctk.CTkLabel(
                stats_row, text=f"⬡ {meta['wellCount']}",
                font=("Arial", 9), text_color="#aaa",
            ).pack(side="left")
        max_vol = meta.get("maxVolume", 0)
        if max_vol:
            vol_str = f"{max_vol} µL" if max_vol < 1000 else f"{max_vol / 1000:.1f} mL"
            ctk.CTkLabel(
                stats_row, text=f"  ▸ {vol_str}",
                font=("Arial", 9), text_color="#aaa",
            ).pack(side="left")

        x_dim = meta.get("xDimension", 0)
        y_dim = meta.get("yDimension", 0)
        if x_dim and y_dim:
            ctk.CTkLabel(
                card, text=f"{x_dim:.1f} × {y_dim:.1f} mm",
                font=("Arial", 9), text_color="#666",
            ).pack(padx=10, anchor="w")

        ctk.CTkLabel(
            card, text=meta["loadName"],
            font=("Courier New", 8), text_color="#555",
            wraplength=170, justify="left",
        ).pack(padx=10, pady=(0, 4), anchor="w")

        ctk.CTkButton(
            card, text="↳  Placer sur le plateau",
            height=30, font=("Arial", 11),
            command=lambda m=meta: self.on_select_callback(m),
        ).pack(padx=10, pady=(4, 10), fill="x")

        return card

    # ─── Images ──────────────────────────────────────────────────────────────

    def _load_all_images(self):
        for meta, card in self._all_cards:
            ctk_img = self._fetch_image(meta["loadName"])
            if ctk_img:
                self._images[meta["loadName"]] = ctk_img
                self.after(
                    0,
                    lambda c=card, i=ctk_img: c._img_label.configure(image=i, text=""),
                )

    def _fetch_image(self, load_name: str):
        for ext in (".jpg", ".png", ".gif"):
            cache_path = os.path.join(CACHE_DIR, f"{load_name}{ext}")
            if os.path.exists(cache_path):
                try:
                    pil = (
                        Image.open(cache_path).convert("RGBA")
                        .resize((_IMG_W, _IMG_H), Image.LANCZOS)
                    )
                    return ctk.CTkImage(light_image=pil, dark_image=pil,
                                        size=(_IMG_W, _IMG_H))
                except Exception:
                    continue

            url = f"{_IMG_BASE_URL}/{load_name}{ext}"
            try:
                r = requests.get(url, timeout=6)
                if r.status_code == 200:
                    with open(cache_path, "wb") as f:
                        f.write(r.content)
                    pil = (
                        Image.open(BytesIO(r.content)).convert("RGBA")
                        .resize((_IMG_W, _IMG_H), Image.LANCZOS)
                    )
                    return ctk.CTkImage(light_image=pil, dark_image=pil,
                                        size=(_IMG_W, _IMG_H))
            except Exception:
                continue
        return None

    # ─── Filter ──────────────────────────────────────────────────────────────

    def _apply_filters(self):
        query = self.search_var.get().lower()
        cat_filter = _CATEGORY_LABELS.get(self.cat_var.get())

        row = col = 0
        for meta, card in self._all_cards:
            matches_text = (
                query in meta["displayName"].lower()
                or query in meta["loadName"].lower()
                or query in meta.get("brand", "").lower()
            )
            matches_cat = cat_filter is None or meta.get("displayCategory") == cat_filter

            if matches_text and matches_cat:
                card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
                col += 1
                if col >= _CARDS_PER_ROW:
                    col = 0
                    row += 1
            else:
                card.grid_remove()


def _extract_meta(data: dict, load_name: str, full_json_path: str) -> dict:
    metadata   = data.get("metadata", {})
    wells      = data.get("wells", {})
    dimensions = data.get("dimensions", {})
    brand      = data.get("brand", {}).get("brand", "")

    max_vol = (
        max((w.get("totalLiquidVolume", 0) for w in wells.values()), default=0)
        if wells else 0
    )
    return {
        "loadName":        load_name,
        "displayName":     metadata.get("displayName", load_name),
        "displayCategory": metadata.get("displayCategory", ""),
        "brand":           brand,
        "wellCount":       len(wells),
        "maxVolume":       max_vol,
        "xDimension":      dimensions.get("xDimension", 127.76),
        "yDimension":      dimensions.get("yDimension", 85.48),
        "fullJsonPath":    full_json_path,
    }
