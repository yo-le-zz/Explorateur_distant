# config.py
import json
from get_data import *
import os, sys
import tkinter as tk
from tkinter import simpledialog, messagebox

def reset_and_restart():
    """Supprime data.bin et informe l'utilisateur de relancer le script."""
    if os.path.exists(CONFIG_FILE):
        try:
            os.remove(CONFIG_FILE)
            print("Config supprimée : data.bin")
        except Exception as e:
            print(f"Impossible de supprimer data.bin : {e}")

    # Message à l'utilisateur
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Redémarrage nécessaire",
            "La configuration a été réinitialisée.\nVeuillez relancer manuellement le script."
        )
        root.destroy()
    except Exception as e:
        print(f"Impossible d'afficher la boîte d'information : {e}")

    sys.exit(0)


def get_path(name: str):
    """Retourne le chemin correct, compatible PyInstaller."""
    # ici on force dossier courant
    base_path = os.getcwd()
    return os.path.join(base_path, name)

# DATA BIN toujours dans le dossier courant
CONFIG_FILE = get_path("data.bin")

def get_data(root):
    """Charge ou demande la config SSH, renvoie un dictionnaire CONFIG."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            encrypted_data = f.read()
    else:
        # --- Saisie utilisateur ---
        user_serveur = simpledialog.askstring("Utilisateur serveur distant",
                                              "Utilisateur serveur distant",
                                              parent=root)
        if user_serveur is None: exit()

        user_host = simpledialog.askstring("Adresse serveur distant",
                                           "Adresse serveur distant",
                                           parent=root)
        if user_host is None: exit()

        # Forcer un port valide
        while True:
            user_port = simpledialog.askstring("Port serveur distant",
                                               "Port serveur distant (default 22)",
                                               parent=root)
            if user_port is None:
                exit()
            if user_port.isdigit() and int(user_port) > 0:
                break
            messagebox.showwarning("Port invalide", "Le port doit être un entier positif.")
        user_start_path = simpledialog.askstring("Chemin de démarrage",
                                                "Chemin de démarrage",
                                                parent=root)
        if user_start_path is None: exit()

        use_key = messagebox.askyesno("Authentification",
                                      "Utiliser une clé SSH ? (Non = mot de passe)",
                                      parent=root)

        key_path = None
        password = None

        if use_key:
            key_path = simpledialog.askstring("Clé SSH", "Chemin vers la clé SSH", parent=root)
            if key_path is None: exit()
        else:
            password = simpledialog.askstring("Mot de passe SSH",
                                              "Mot de passe SSH",
                                              show="*",
                                              parent=root)
            if password is None: exit()

        save = messagebox.askyesno("Confirmation",
                                   "Veux-tu sauvegarder ces informations ?",
                                   parent=root)

        data_dict = {
            "user_serveur": user_serveur,
            "user_host": user_host,
            "user_port": user_port,
            "user_start_path": user_start_path,
            "key_path": key_path,
            "password": password
        }

        encrypted = encrypt(source_type="content", data=json.dumps(data_dict), is_binary=False, bits=True)
        if save:
            with open(CONFIG_FILE, "w") as f:
                f.write(encrypted.decode())
        encrypted_data = encrypted.decode()

    # --- Décryptage ---
    decrypted = decrypt(source_type="content", data=encrypted_data, is_binary=False, bits=True)
    decrypted_dict = json.loads(decrypted.decode())

    # --- Auth SSH ---
    if decrypted_dict.get("key_path"):
        auth = {"type": "key", "key_path": decrypted_dict["key_path"]}
    else:
        auth = {"type": "password", "password": decrypted_dict["password"]}

    # --- Port sécurisé ---
    try:
        port = int(decrypted_dict.get("user_port", 22))
    except (ValueError, TypeError):
        port = 22

    CONFIG = {
        "host": decrypted_dict["user_host"],
        "port": port,
        "username": decrypted_dict["user_serveur"],
        "auth": auth,
        "start_path": decrypted_dict["user_start_path"]
    }

    return CONFIG
