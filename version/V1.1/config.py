# config.py
import json
import os
import sys
import tkinter as tk
from tkinter import simpledialog, messagebox

def get_data(root):
    if getattr(sys, 'frozen', False):
        # On est dans un exécutable PyInstaller
        BASE_DIR = os.path.dirname(sys.executable)
    else:
        # On est en script Python normal
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    CONFIG_FILE = os.path.join(BASE_DIR, "data.json")
    
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
    else:
        user_serveur = simpledialog.askstring("Utilisateur serveur distant", "Utilisateur serveur distant", parent=root)
        if user_serveur is None: exit()
        user_host = simpledialog.askstring("Adresse serveur distant", "Adresse serveur distant", parent=root)
        if user_host is None: exit()
        user_port = simpledialog.askstring("Port serveur distant", "Port serveur distant (default 22)", parent=root)
        if user_port is None: exit()
        user_start_path = simpledialog.askstring("Chemin de démarrage", "Chemin de démarrage", parent=root)
        if user_start_path is None: exit()
        key_path = simpledialog.askstring("Chemin clé SSH", "Chemin clé SSH", parent=root)
        if key_path is None: exit()

        save = messagebox.askyesno("Confirmation", "Veux-tu sauvegarder ces informations ?", parent=root)
        if save:
            data = {
                "user_serveur": user_serveur,
                "user_host": user_host,
                "user_port": user_port,
                "user_start_path": user_start_path,
                "key_path": key_path
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=4)

    CONFIG = {
        "host": data["user_host"],
        "port": int(data.get("user_port", 22)),
        "username": data["user_serveur"],
        "auth": {"type": "key", "key_path": data["key_path"]},
        "start_path": data["user_start_path"]
    }
    return CONFIG
