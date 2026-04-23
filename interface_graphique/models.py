"""
=========================================================================================
Projet      : Science-Jubilee
Fichier     : model.py
Auteur      : [SABATIÉ Léo / Projet industriel ROB4]
Date        : 10 Avril 2026
Description : Gestion des objets interactifs (Labware) sur le plateau.
              Inclut le chargement dynamique des dimensions depuis les définitions JSON
              et la gestion des événements de drag-and-drop et rotation.
=========================================================================================
"""

import json
import os

import app_paths
from constants import MM_TO_PIX

def load_labware_dims(json_filename):
    """
    Localise et charge les dimensions réelles d'un labware.

    Args:
        json_filename (str): Chemin absolu (cache Opentrons) ou nom de fichier
                             de la banque locale (ex: 'greiner_24_wellplate.json').

    Returns:
        dict | None: Contenu du JSON, ou None si introuvable / illisible.
    """
    full_path = app_paths.resolve_labware_json(json_filename)
    if full_path is None:
        print(f"⚠️  Labware introuvable : {json_filename}")
        return None
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  Impossible de charger {full_path} : {e}")
        return None


class DraggableObject:
    """
    Représente un labware interactif sur le canvas.
    Gère les collisions, le déplacement à la souris et la rotation à 90°.
    """

    def __init__(self, canvas, x, y, json_name, color, name, check_collision_callback, check_inside_callback):
        """
        Initialise l'objet graphique et charge ses propriétés physiques.
        
        Args:
            canvas (tk.Canvas): Support de dessin.
            x, y (int): Coordonnées initiales en pixels.
            json_name (str): Clé pour le fichier de définition.
            color (str): Couleur de remplissage.
            name (str): Label affiché sur l'objet.
            check_collision_callback (func): Fonction de validation des collisions.
            check_inside_callback (func): Fonction de validation des limites du plateau.
        """
        self.canvas = canvas
        self.name = name
        self.angle = 0 # État initial de la rotation
        self.json_name = json_name  # Conservé pour les exports 3D (SCAD/STL)
        
        # 1. Chargement des données techniques
        self.data = load_labware_dims(json_name)
        
        if self.data:
            # Récupération des dimensions réelles (mm)
            self.w_mm = self.data["dimensions"]["xDimension"]
            self.h_mm = self.data["dimensions"]["yDimension"]
        else:
            # Valeurs par défaut si le fichier est introuvable
            self.w_mm, self.h_mm = 50, 50 
            
        # 2. Conversion pour l'affichage (Inversion Axe X/Y pour correspondre au rendu Jubilee)
        # Note : Jubilee utilise X pour la longueur et Y pour la largeur.
        w_px = self.h_mm * MM_TO_PIX 
        h_px = self.w_mm * MM_TO_PIX

        # 3. Création des composants graphiques
        self.id = canvas.create_rectangle(x, y, x + w_px, y + h_px, 
                                          fill=color, outline="white", width=2)
        
        self.text = canvas.create_text(x + w_px/2, y + h_px/2, 
                                       text=name, fill="white", font=("Arial", 10))
        
        self.items = [self.id, self.text]

        # 4. Callbacks de validation
        self.check_collision = check_collision_callback
        self.check_inside = check_inside_callback

        # 5. Liaison des événements (Binding)
        for item in self.items:
            canvas.tag_bind(item, "<Button-1>", self.start_drag)
            canvas.tag_bind(item, "<B1-Motion>", self.do_drag)
            canvas.tag_bind(item, "<Button-3>", self.rotate)

    def start_drag(self, event):
        """Mémorise la position initiale du clic pour le calcul du delta."""
        self.start_x = event.x
        self.start_y = event.y

    def do_drag(self, event):
        """Calcule le déplacement et applique le mouvement si validé par les contraintes."""
        dx = event.x - self.start_x
        dy = event.y - self.start_y
        
        # Coordonnées actuelles de la bounding box
        x1, y1, x2, y2 = self.canvas.coords(self.id)
        w, h = x2 - x1, y2 - y1

        # Validation du mouvement (Limites plateau ET collisions avec autres objets)
        if self.check_inside(x1 + dx, y1 + dy, w, h) and \
           self.check_collision(x1 + dx, y1 + dy, w, h, ignore_id=self.id):
            
            for item in self.items:
                self.canvas.move(item, dx, dy)
                
            self.start_x = event.x
            self.start_y = event.y

    def rotate(self, event):
        """
        Bascule l'orientation de l'objet (90°). 
        Met à jour la géométrie sur le canvas et les métadonnées physiques.
        """
        x1, y1, x2, y2 = self.canvas.coords(self.id)
        w, h = x2 - x1, y2 - y1
        
        # Calcul du centre pour une rotation fixe
        cx, cy = x1 + w/2, y1 + h/2
        
        # Mise à jour graphique : inversion largeur/hauteur
        self.canvas.coords(self.id, cx - h/2, cy - w/2, cx + h/2, cy + w/2)
        self.canvas.coords(self.text, cx, cy)
        
        # Mise à jour de l'état logique
        self.angle = (self.angle + 90) % 360
        
        # Échange des dimensions physiques pour la cohérence lors de l'export
        self.w_mm, self.h_mm = self.h_mm, self.w_mm
