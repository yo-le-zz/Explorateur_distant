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


def load_entries():
    """Retourne la liste d'entrées stockées (ou [] si aucune)."""
    if not os.path.exists(CONFIG_FILE):
        return []
    with open(CONFIG_FILE, "r") as f:
        encrypted_data = f.read()
    try:
        decrypted = decrypt(source_type="content", data=encrypted_data, is_binary=False, bits=True)
        loaded = json.loads(decrypted.decode())
    except Exception:
        return []
    if isinstance(loaded, dict):
        return [loaded]
    if isinstance(loaded, list):
        return loaded
    return []


def save_entries(entries):
    """Sauvegarde la liste d'entrées (écrase)."""
    encrypted = encrypt(source_type="content", data=json.dumps(entries), is_binary=False, bits=True)
    with open(CONFIG_FILE, "w") as f:
        f.write(encrypted.decode())


def save_config(entry: dict, append: bool = True):
    """Ajoute une entrée ou remplace la liste selon `append`.

    `entry` doit être un dictionnaire au format attendu par get_data.
    """
    if append:
        entries = load_entries()
        entries.append(entry)
        save_entries(entries)
    else:
        save_entries([entry])


def prompt_new_server(parent):
    """Dialogue pour créer un nouveau serveur.
    
    Retourne (entry_dict, save_flag) ou None si annulé.
    """
    user_serveur = simpledialog.askstring("Utilisateur serveur distant",
                                          "Utilisateur serveur distant",
                                          parent=parent)
    if user_serveur is None: 
        return None

    user_host = simpledialog.askstring("Adresse serveur distant",
                                       "Adresse serveur distant",
                                       parent=parent)
    if user_host is None: 
        return None

    # Forcer un port valide
    while True:
        user_port = simpledialog.askstring("Port serveur distant",
                                           "Port serveur distant (default 22)",
                                           parent=parent)
        if user_port is None:
            return None
        if user_port.isdigit() and int(user_port) > 0:
            break
        messagebox.showwarning("Port invalide", "Le port doit être un entier positif.", parent=parent)

    user_start_path = simpledialog.askstring("Chemin de démarrage",
                                            "Chemin de démarrage",
                                            parent=parent)
    if user_start_path is None: 
        return None

    use_key = messagebox.askyesno("Authentification",
                                  "Utiliser une clé SSH ? (Non = mot de passe)",
                                  parent=parent)

    key_path = None
    password = None

    if use_key:
        key_path = simpledialog.askstring("Clé SSH", "Chemin vers la clé SSH", parent=parent)
        if key_path is None: 
            return None
    else:
        password = simpledialog.askstring("Mot de passe SSH",
                                          "Mot de passe SSH",
                                          show="*",
                                          parent=parent)
        if password is None: 
            return None

    save = messagebox.askyesno("Confirmation",
                               "Veux-tu sauvegarder ces informations ?",
                               parent=parent)

    data_dict = {
        "user_serveur": user_serveur,
        "user_host": user_host,
        "user_port": user_port,
        "user_start_path": user_start_path,
        "key_path": key_path,
        "password": password
    }

    return data_dict, save



def manage_servers(root):
    """Ouvre une interface simple pour choisir/ajouter/supprimer des serveurs.

    Retourne une entrée (dict) sélectionnée ou None si annulé.
    """
    entries = load_entries()

    # Si aucun serveur n'existe, proposer d'en créer un automatiquement
    if not entries:
        choice = messagebox.askyesno("Aucun serveur", "Aucun serveur configuré. Veux-tu en ajouter un ?", parent=root)
        if not choice:
            return None
        # Ouvrir le dialogue de création de serveur
        result = prompt_new_server(root)
        if not result:
            return None
        new_entry, save_flag = result
        entries.append(new_entry)
        if save_flag:
            save_entries(entries)
        return new_entry

    # Retourner le premier serveur (s'il n'y en a qu'un) ou None pour afficher l'UI
    if len(entries) == 1:
        return entries[0]
    
    return None


def open_server_manager():
    """Ouvre une interface UI pour gérer les serveurs et se connecter à plusieurs."""
    from ui import ServerManagerUI
    manager = ServerManagerUI()
    manager.mainloop()


def get_data(root):
    """Charge ou demande la config SSH, renvoie un dictionnaire CONFIG."""
    # Si un fichier de config existe, on propose de choisir parmi plusieurs serveurs
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            encrypted_data = f.read()
    else:
        encrypted_data = None

    def prompt_new_server(parent):
        user_serveur = simpledialog.askstring("Utilisateur serveur distant",
                                              "Utilisateur serveur distant",
                                              parent=parent)
        if user_serveur is None: return None

        user_host = simpledialog.askstring("Adresse serveur distant",
                                           "Adresse serveur distant",
                                           parent=parent)
        if user_host is None: return None

        # Forcer un port valide
        while True:
            user_port = simpledialog.askstring("Port serveur distant",
                                               "Port serveur distant (default 22)",
                                               parent=parent)
            if user_port is None:
                return None
            if user_port.isdigit() and int(user_port) > 0:
                break
            messagebox.showwarning("Port invalide", "Le port doit être un entier positif.")

        user_start_path = simpledialog.askstring("Chemin de démarrage",
                                                "Chemin de démarrage",
                                                parent=parent)
        if user_start_path is None: return None

        use_key = messagebox.askyesno("Authentification",
                                      "Utiliser une clé SSH ? (Non = mot de passe)",
                                      parent=parent)

        key_path = None
        password = None

        if use_key:
            key_path = simpledialog.askstring("Clé SSH", "Chemin vers la clé SSH", parent=parent)
            if key_path is None: return None
        else:
            password = simpledialog.askstring("Mot de passe SSH",
                                              "Mot de passe SSH",
                                              show="*",
                                              parent=parent)
            if password is None: return None

        save = messagebox.askyesno("Confirmation",
                                   "Veux-tu sauvegarder ces informations ?",
                                   parent=parent)

        data_dict = {
            "user_serveur": user_serveur,
            "user_host": user_host,
            "user_port": user_port,
            "user_start_path": user_start_path,
            "key_path": key_path,
            "password": password
        }

        return data_dict, save

    # --- Décryptage / sélection multi-serveurs ---
    entries = []
    if encrypted_data:
        decrypted = decrypt(source_type="content", data=encrypted_data, is_binary=False, bits=True)
        try:
            loaded = json.loads(decrypted.decode())
        except Exception:
            loaded = None

        if isinstance(loaded, dict):
            entries = [loaded]
        elif isinstance(loaded, list):
            entries = loaded
        else:
            entries = []

    # Si pas d'entrée existante, on crée la première
    if not entries:
        result = prompt_new_server(root)
        if not result:
            exit()
        new_entry, save_flag = result
        entries.append(new_entry)
        if save_flag:
            encrypted = encrypt(source_type="content", data=json.dumps(entries), is_binary=False, bits=True)
            with open(CONFIG_FILE, "w") as f:
                f.write(encrypted.decode())

    # Si plusieurs, afficher un petit menu de sélection
    if len(entries) > 1:
        sel = {'index': None}

        dlg = tk.Toplevel(root)
        dlg.title("Choisir un serveur")
        dlg.geometry("480x320")
        dlg.transient(root)

        tk.Label(dlg, text="Choisissez un serveur existant ou créez-en un nouveau:", anchor="w").pack(fill="x", padx=8, pady=6)
        lb = tk.Listbox(dlg)
        for e in entries:
            display = f"{e.get('user_serveur')}@{e.get('user_host')} -> {e.get('user_start_path')}"
            lb.insert("end", display)
        lb.pack(fill="both", expand=True, padx=8, pady=6)

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(fill="x", pady=6)

        def do_select():
            cur = lb.curselection()
            if not cur:
                messagebox.showwarning("Sélection requise", "Veuillez sélectionner un serveur.", parent=dlg)
                return
            sel['index'] = cur[0]
            dlg.destroy()

        def do_new():
            res = prompt_new_server(dlg)
            if not res:
                return
            new_entry, save_flag = res
            entries.append(new_entry)
            # sauvegarde
            if save_flag:
                encrypted = encrypt(source_type="content", data=json.dumps(entries), is_binary=False, bits=True)
                with open(CONFIG_FILE, "w") as f:
                    f.write(encrypted.decode())
            lb.insert("end", f"{new_entry.get('user_serveur')}@{new_entry.get('user_host')} -> {new_entry.get('user_start_path')}")

        def do_delete():
            cur = lb.curselection()
            if not cur:
                return
            idx = cur[0]
            if messagebox.askyesno("Supprimer", "Supprimer cette entrée ?", parent=dlg):
                entries.pop(idx)
                lb.delete(idx)
                # réécrire le fichier
                encrypted = encrypt(source_type="content", data=json.dumps(entries), is_binary=False, bits=True)
                with open(CONFIG_FILE, "w") as f:
                    f.write(encrypted.decode())

        tk.Button(btn_frame, text="Sélectionner", command=do_select).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Nouveau", command=do_new).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Supprimer", command=do_delete).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Annuler", command=lambda: dlg.destroy()).pack(side="right", padx=6)

        # attendre la fermeture
        dlg.grab_set()
        root.wait_window(dlg)

        if sel['index'] is None:
            # Si l'utilisateur a fermé sans sélectionner, on prend la première
            chosen = entries[0]
        else:
            chosen = entries[sel['index']]

        decrypted_dict = chosen
    else:
        # une seule entrée
        decrypted_dict = entries[0]

    # --- Auth SSH ---
    if decrypted_dict.get("key_path"):
        auth = {"type": "key", "key_path": decrypted_dict["key_path"]}
    else:
        auth = {"type": "password", "password": decrypted_dict.get("password")}

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