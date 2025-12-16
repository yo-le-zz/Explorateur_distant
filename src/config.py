# config.py
import json
from get_data import *
import os, sys
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog

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


def prompt_new_server(parent, entry_to_edit=None):
    """Dialogue pour ajouter ou éditer un serveur.
    
    Retourne (entry_dict, save_flag) ou None si annulé.
    """
    
    # [NOUVELLE CORRECTION] Démasquer le parent s'il est caché, pour éviter le blocage.
    is_parent_hidden = False
    try:
        # Si 'parent' est une fenêtre Tkinter et est retirée
        if isinstance(parent, tk.Tk) and parent.state() == 'withdrawn':
            parent.deiconify()
            is_parent_hidden = True
    except Exception:
        pass
    # ----------------------------------------------------------------------
    
    dlg = tk.Toplevel(parent)
    is_editing = entry_to_edit is not None
    dlg.title("Modifier un serveur" if is_editing else "Ajouter un nouveau serveur")
    dlg.geometry("500x350")
    dlg.configure(bg="#0A3D62")
    # Rendre la fenêtre modale
    dlg.transient(parent)
    dlg.grab_set()

    # Variables de retour
    result = {'entry': None, 'save': False}
    
    # Récupérer les valeurs par défaut
    defaults = entry_to_edit if is_editing else {}

    # Initialisation des variables Tkinter avec les valeurs existantes (pour l'édition)
    user_var = tk.StringVar(value=defaults.get('user_serveur', ''))
    host_var = tk.StringVar(value=defaults.get('user_host', ''))
    port_var = tk.StringVar(value=defaults.get('user_port', '22'))
    path_var = tk.StringVar(value=defaults.get('user_start_path', '/'))
    pwd_var = tk.StringVar(value=defaults.get('password', ''))
    key_path_var = tk.StringVar(value=defaults.get('key_path', ''))
    
    # Authentification: 'key' si key_path est présent, sinon 'password'
    initial_auth_mode = "key" if defaults.get('key_path') else "password"
    auth_mode = tk.StringVar(value=initial_auth_mode)


    # --- Widgets ---
    # Layout Frame
    main_frame = tk.Frame(dlg, bg="#0A3D62")
    main_frame.pack(padx=10, pady=10, fill="both", expand=True)

    def create_row(row, label_text, var, show=None, command_btn=None):
        tk.Label(main_frame, text=label_text, bg="#0A3D62", fg="#A1D6E2", anchor="w").grid(row=row, column=0, padx=5, pady=2, sticky="w")
        entry = tk.Entry(main_frame, textvariable=var, show=show, bg="#333333", fg="#A1D6E2", insertbackground="#A1D6E2")
        entry.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
        if command_btn:
            tk.Button(main_frame, text="...", command=command_btn, bg="#0E4F95", fg="white").grid(row=row, column=2, padx=5, pady=2)
        else:
            # Colonne vide pour l'alignement
            main_frame.grid_columnconfigure(2, weight=0)
        return entry

    # Champs de saisie
    create_row(0, "Utilisateur SSH:", user_var)
    create_row(1, "Hôte (IP/Domaine):", host_var)
    create_row(2, "Port (défaut 22):", port_var)
    create_row(3, "Chemin de démarrage:", path_var)
    
    # --- Authentification ---
    tk.Label(main_frame, text="--- Authentification ---", bg="#0A3D62", fg="#A1D6E2", font=("Arial", 10, "bold")).grid(row=4, column=0, columnspan=3, pady=(10, 5))

    auth_frame = tk.Frame(main_frame, bg="#0A3D62")
    auth_frame.grid(row=5, column=0, columnspan=3, sticky="ew")
    tk.Radiobutton(auth_frame, text="Mot de passe", variable=auth_mode, value="password", bg="#0A3D62", fg="#A1D6E2", selectcolor="#0A3D62").pack(side="left", padx=5)
    tk.Radiobutton(auth_frame, text="Clé SSH", variable=auth_mode, value="key", bg="#0A3D62", fg="#A1D6E2", selectcolor="#0A3D62").pack(side="left", padx=5)
    
    # Conteneur pour le champ clé/mot de passe
    pwd_frame = tk.Frame(main_frame, bg="#0A3D62")
    pwd_frame.grid(row=6, column=0, columnspan=3, sticky="ew")
    
    pwd_entry = tk.Entry(pwd_frame, textvariable=pwd_var, show="*", bg="#333333", fg="#A1D6E2", insertbackground="#A1D6E2")
    key_entry = tk.Entry(pwd_frame, textvariable=key_path_var, bg="#333333", fg="#A1D6E2", insertbackground="#A1D6E2")
    
    def browse_key():
        path = filedialog.askopenfilename(parent=dlg, title="Sélectionner la clé SSH privée")
        if path:
            key_path_var.set(path)

    key_browse_btn = tk.Button(pwd_frame, text="...", command=browse_key, bg="#0E4F95", fg="white")

    def update_auth_fields(*args):
        # Masquer et montrer les champs selon le mode
        for w in pwd_frame.winfo_children():
            w.pack_forget()

        if auth_mode.get() == "password":
            pwd_entry.pack(fill="x", expand=True, padx=5, pady=2)
        else: # key mode
            key_browse_btn.pack(side="right", padx=(0, 5), pady=2)
            key_entry.pack(side="left", fill="x", expand=True, padx=(5, 0), pady=2)

    auth_mode.trace_add("write", update_auth_fields)
    update_auth_fields() # Appel initial

    # Fonctions de validation et fermeture
    def on_ok():
        # Validation
        if not user_var.get() or not host_var.get():
            messagebox.showerror("Erreur", "Veuillez remplir le nom d'utilisateur et l'hôte.", parent=dlg)
            return

        try:
            port = int(port_var.get())
            if port <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Erreur", "Le port doit être un entier positif.", parent=dlg)
            return
            
        save_conf = messagebox.askyesno("Confirmation",
                                       "Veux-tu sauvegarder ces informations ?",
                                       parent=dlg)

        # Construction de l'entrée mise à jour
        new_entry_data = {
            "user_serveur": user_var.get(),
            "user_host": host_var.get(),
            "user_port": port_var.get(),
            "user_start_path": path_var.get(),
            "password": "", 
            "key_path": "", 
        }

        if auth_mode.get() == "password":
            new_entry_data["password"] = pwd_var.get()
        else:
            new_entry_data["key_path"] = key_path_var.get()
            
        # Fusion avec l'entrée existante si édition
        if is_editing:
            final_entry = entry_to_edit.copy()
            final_entry.update(new_entry_data)
            result['entry'] = final_entry
        else:
            result['entry'] = new_entry_data

        result['save'] = save_conf
        dlg.destroy()

    def on_cancel():
        dlg.destroy()

    # Boutons OK/Annuler
    btn_frame = tk.Frame(dlg, bg="#0A3D62")
    btn_frame.pack(fill="x", pady=10)
    
    tk.Button(btn_frame, text="Sauvegarder", command=on_ok, bg="#0E4F95", fg="white").pack(side="left", fill="x", expand=True, padx=(10, 5))
    tk.Button(btn_frame, text="Annuler", command=on_cancel, bg="#8B0000", fg="white").pack(side="left", fill="x", expand=True, padx=(5, 10))

    # Configuration pour étendre la colonne 1
    main_frame.grid_columnconfigure(1, weight=1)

    # Attendre la fermeture du dialogue
    dlg.wait_window(dlg)
    
    # [NOUVELLE CORRECTION] Si on a démasqué le parent, le masquer à nouveau.
    if is_parent_hidden:
        parent.withdraw()
    # ----------------------------------------------------------------------
    
    if result['entry'] and result['save']:
        return (result['entry'], result['save'])
    
    return None


def manage_servers(root):
    """Ouvre une interface simple pour choisir/ajouter/supprimer des serveurs.

    Retourne une entrée (dict) sélectionnée ou None si annulé.
    """
    entries = load_entries()

    # Si aucun serveur n'existe, proposer d'en créer un automatiquement
    if not entries:
        # NOTE : Cette messagebox utilise 'root' comme parent, mais elle est généralement 
        # affichée depuis 'main.py' où 'root' est le Toplevel principal.
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
        # Ceci appelle la fonction globale prompt_new_server corrigée.
        result = prompt_new_server(root)
        if not result:
            exit()
        new_entry, save_flag = result
        entries.append(new_entry)
        if save_flag:
            encrypted = encrypt(source_type="content", data=json.dumps(entries), is_binary=False, bits=True)
            with open(CONFIG_FILE, "w") as f:
                f.write(encrypted.decode())

        # Retourner les données brutes attendues par main.py
        return new_entry, entries

    # Si plusieurs, afficher un petit menu de sélection
    if len(entries) > 1:
        sel = {'index': None}

        # NOTE: Pas besoin de correction ici car 'root' n'est masqué que si le programme 
        # vient de démarrer sans config, et c'est géré dans prompt_new_server.
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
            # Ceci appelle la fonction globale prompt_new_server corrigée.
            res = prompt_new_server(dlg) # Le parent est ici le dlg visible, donc pas de problème.
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