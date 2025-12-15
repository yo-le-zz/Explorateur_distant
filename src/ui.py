# ui.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import os
import posixpath
import tempfile
from logic import SSHClient

# CHANGEMENT IMPORTANT : ExplorerUI hérite de tk.Toplevel pour être une fenêtre secondaire.
class ExplorerUI(tk.Toplevel):
    def __init__(self, parent, ssh_client, start_path="/", config_callback=None):
        super().__init__(parent) # PASSAGE DU PARENT
        self.ssh = ssh_client
        self.current = start_path or "/"
        self.config_callback = config_callback

        self.title("Explorateur distant")
        self.geometry("1200x700")
        self.configure(bg="#0A3D62")

        # Configuration de l'icône et autres initialisations
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "app.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self._build_ui()
        self.refresh()

    # ===================== UI =====================

    def _build_ui(self):
        nav = tk.Frame(self, bg="#0A3D62")
        nav.pack(fill="x", padx=5, pady=5)

        tk.Button(nav, text="← Parent", bg="#0E4F95", fg="white",
                  command=self.go_parent).pack(side="left")

        tk.Button(nav, text="Modifier infos", bg="#0E4F95", fg="white",
              command=self.change_config).pack(side="right")

        path_frame = tk.Frame(self, bg="#0A3D62")
        path_frame.pack(fill="x", padx=5)

        self.path_edit = tk.Entry(path_frame, bg="#333333", fg="#A1D6E2")
        self.path_edit.pack(side="left", fill="x", expand=True)
        self.path_edit.insert(0, self.current)

        tk.Button(path_frame, text="Refresh", bg="#0E4F95", fg="white",
                  command=self.refresh).pack(side="left")

        style = ttk.Style(self)
        style.configure("Treeview", background="#333333", foreground="#A1D6E2")
        style.map("Treeview", background=[("selected", "#0E4F95")])

        self.tree = ttk.Treeview(self, columns=("type", "size"))
        self.tree.heading("#0", text="Nom")
        self.tree.heading("type", text="Type")
        self.tree.heading("size", text="Taille")
        self.tree.column("#0", width=600)

        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree.bind("<Double-1>", lambda e: self.on_double_click())
        self.tree.bind("<Button-3>", self.show_menu)

    # ===================== REFRESH =====================

    def refresh(self):
        self.current = self.path_edit.get().strip() or "/"
        threading.Thread(target=self.refresh_worker, daemon=True).start()

    def refresh_worker(self):
        # Correction: Toutes les interactions GUI (populate et messagebox)
        # sont maintenant appelées via self.after(0, ...)
        try:
            rows = []
            for item in self.ssh.listdir_attr(self.current):
                typ = "Dossier" if self.ssh.is_dir_attr(item) else "Fichier"
                size = "" if typ == "Dossier" else str(item.st_size)
                rows.append((item.filename, typ, size))
            self.after(0, lambda: self.populate(rows))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda msg=error_msg: messagebox.showerror("Erreur SSH", msg, parent=self))

    def populate(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", text=r[0], values=r[1:])

    # ===================== NAV =====================

    def go_parent(self):
        if self.current != "/":
            self.current = posixpath.dirname(self.current)
            self.path_edit.delete(0, "end")
            self.path_edit.insert(0, self.current)
            self.refresh()

    def on_double_click(self):
        item = self.tree.selection()
        if not item:
            return
        name = self.tree.item(item, "text")
        typ = self.tree.item(item, "values")[0]
        if typ == "Dossier":
            self.current = posixpath.join(self.current, name)
            self.path_edit.delete(0, "end")
            self.path_edit.insert(0, self.current)
            self.refresh()
        else:
            self.open_item(name)

    # ===================== FILE OPS =====================

    def open_item(self, name):
        path = posixpath.join(self.current, name)
        try:
            data = self.ssh.open_file_readbytes(path)
            if b"\x00" in data:
                messagebox.showwarning("Binaire", "Fichier binaire non affichable", parent=self)
                return

            dlg = tk.Toplevel(self)
            dlg.title(name)
            dlg.geometry("700x500")

            text = tk.Text(dlg, bg="#333333", fg="#A1D6E2")
            text.insert("1.0", data.decode(errors="ignore"))
            text.pack(fill="both", expand=True)

            tk.Button(
                dlg, text="Enregistrer", bg="#0E4F95", fg="white",
                command=lambda: self.save_file(path, text.get("1.0", "end"))
            ).pack(pady=5)

        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)

    def save_file(self, path, content):
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(content.encode())
                tmp_path = tmp.name
            self.ssh.upload_from(tmp_path, path)
            os.unlink(tmp_path)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)

    # ===================== CONTEXT MENU =====================

    def show_menu(self, event):
        iid = self.tree.identify_row(event.y)
        menu = tk.Menu(self, tearoff=0)

        if iid:
            name = self.tree.item(iid, "text")
            typ = self.tree.item(iid, "values")[0]
            menu.add_command(label="Ouvrir", command=lambda: self.open_item(name))
            menu.add_command(label="Supprimer", command=lambda: self.delete_item(name, typ))
            menu.add_command(label="Renommer", command=lambda: self.rename_item(name))

        menu.add_separator()
        menu.add_command(label="Créer dossier", command=self.create_folder)
        menu.add_command(label="Créer fichier", command=self.create_file)
        menu.add_command(label="Uploader", command=self.upload)

        if iid and typ == "Fichier":
            menu.add_command(label="Télécharger", command=lambda: self.download_item(name))

        menu.post(event.x_root, event.y_root)

    # ===================== CRUD =====================

    def delete_item(self, name, typ):
        path = posixpath.join(self.current, name)
        try:
            if typ == "Dossier":
                self.ssh.remove_dir(path)
            else:
                self.ssh.remove_file(path)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)

    def rename_item(self, name):
        new = simpledialog.askstring("Renommer", "Nouveau nom:", parent=self)
        if new:
            try:
                self.ssh.rename(
                    posixpath.join(self.current, name),
                    posixpath.join(self.current, new)
                )
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e), parent=self)

    def create_folder(self):
        name = simpledialog.askstring("Créer dossier", "Nom:", parent=self)
        if name:
            try:
                self.ssh.mkdir(posixpath.join(self.current, name))
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e), parent=self)

    def create_file(self):
        name = simpledialog.askstring("Créer fichier", "Nom:", parent=self)
        if name:
            try:
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    tmp_path = tmp.name
                self.ssh.upload_from(tmp_path, posixpath.join(self.current, name))
                os.unlink(tmp_path)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e), parent=self)

    def upload(self):
        file_path = filedialog.askopenfilename(parent=self)
        if file_path:
            try:
                self.ssh.upload_from(
                    file_path,
                    posixpath.join(self.current, os.path.basename(file_path))
                )
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e), parent=self)

    def download_item(self, name):
        dest = filedialog.asksaveasfilename(initialfile=name, parent=self)
        if dest:
            try:
                self.ssh.download_to(posixpath.join(self.current, name), dest)
            except Exception as e:
                messagebox.showerror("Erreur", str(e), parent=self)

    # ===================== CONFIG =====================

    def change_config(self):
        if self.config_callback:
            self.config_callback()

    def reset_config(self):
        from config import reset_and_restart
        reset_and_restart()


class ServerManagerUI(tk.Tk):
    """UI pour gérer et se connecter à plusieurs serveurs."""
    
    def __init__(self):
        super().__init__()
        self.title("Gestionnaire de serveurs")
        self.geometry("600x400")
        self.configure(bg="#0A3D62")
        
        self.explorers = {}  # {server_name: explorer_window}
        
        self._build_ui()
        self.refresh_list()
        
    def _build_ui(self):
        # Titre
        tk.Label(self, text="Serveurs disponibles:", bg="#0A3D62", fg="#A1D6E2", 
                 font=("Arial", 12, "bold")).pack(fill="x", padx=8, pady=6)
        
        # Listbox
        self.lb = tk.Listbox(self, bg="#333333", fg="#A1D6E2", height=15)
        self.lb.pack(fill="both", expand=True, padx=8, pady=6)
        
        # Double-clic pour connecter
        self.lb.bind("<Double-1>", lambda e: self.connect_server())
        
        # Buttons
        btn_frame = tk.Frame(self, bg="#0A3D62")
        btn_frame.pack(fill="x", padx=8, pady=6)
        
        tk.Button(btn_frame, text="Connecter", bg="#0E4F95", fg="white",
                  command=self.connect_server).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Ajouter", bg="#0E4F95", fg="white",
                  command=self.add_server).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Supprimer", bg="#0E4F95", fg="white",
                  command=self.delete_server).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Fermer", bg="#8B0000", fg="white",
                  command=self.on_close).pack(side="right", padx=4)
    
    def refresh_list(self):
        """Recharge la liste des serveurs."""
        from config import load_entries
        self.entries = load_entries()
        self.lb.delete(0, "end")
        for e in self.entries:
            display = f"{e.get('user_serveur')}@{e.get('user_host')} -> {e.get('user_start_path')}"
            self.lb.insert("end", display)
    
    def connect_server(self):
        """Lance la connexion dans un thread séparé."""
        cur = self.lb.curselection()
        if not cur:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un serveur.", parent=self)
            return
        
        idx = cur[0]
        entry = self.entries[idx]
        server_name = f"{entry.get('user_serveur')}@{entry.get('user_host')}"
        
        # Convertir l'entrée en CONFIG SSH
        try:
            port = int(entry.get("user_port", 22))
        except (ValueError, TypeError):
            port = 22
        
        if entry.get("key_path"):
            auth = {"type": "key", "key_path": entry.get("key_path")}
        else:
            auth = {"type": "password", "password": entry.get("password")}
        
        cfg = {
            "host": entry.get("user_host"),
            "port": port,
            "username": entry.get("user_serveur"),
            "auth": auth,
            "start_path": entry.get("user_start_path")
        }
        
        ssh = SSHClient(cfg)
        
        # Définir le worker de connexion
        def connection_worker():
            try:
                ssh.connect()
                # Ouvre l'explorateur sur le thread principal
                self.after(0, lambda: self._open_explorer_ui(ssh, cfg, server_name))
            except Exception as e:
                # Affiche l'erreur sur le thread principal
                self.after(0, lambda msg=str(e): messagebox.showerror("Erreur SSH", f"Impossible de connecter à {server_name}: {msg}", parent=self))

        # Lancer le thread de connexion
        threading.Thread(target=connection_worker, daemon=True).start()

    def _open_explorer_ui(self, ssh, cfg, server_name):
        """Méthode helper pour créer l'UI de l'explorateur sur le thread principal."""
        
        # Callback pour modifier la configuration (doit être définie)
        def edit_config():
            # Dans le mode multi-fenêtres, la modification de la config est plus complexe
            # car elle devrait affecter l'entrée dans data.bin.
            messagebox.showwarning("Fonctionnalité non implémentée", "La modification de la config n'est pas encore disponible directement depuis l'explorateur en mode multi-fenêtres.", parent=self)
            return
            
        # Création de l'ExplorerUI comme Toplevel
        explorer = ExplorerUI(parent=self, # Passage du parent self (ServerManagerUI)
                             ssh_client=ssh,
                             start_path=cfg.get("start_path", "/"),
                             config_callback=edit_config)
                             
        self.explorers[server_name] = explorer
        
        # Mettre à jour le titre
        explorer.title(f"Explorateur distant - {server_name}")
        
    def add_server(self):
        """Ajoute un nouveau serveur."""
        from config import prompt_new_server, save_entries
        result = prompt_new_server(self)
        if not result:
            return
        new_entry, save_flag = result
        self.entries.append(new_entry)
        if save_flag:
            save_entries(self.entries)
        self.refresh_list()
        messagebox.showinfo("Succès", "Serveur ajouté avec succès.", parent=self)
    
    def delete_server(self):
        """Supprime le serveur sélectionné."""
        cur = self.lb.curselection()
        if not cur:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un serveur.", parent=self)
            return
        
        idx = cur[0]
        if messagebox.askyesno("Supprimer", "Êtes-vous sûr de vouloir supprimer ce serveur ?", parent=self):
            from config import save_entries
            self.entries.pop(idx)
            save_entries(self.entries)
            self.refresh_list()
            messagebox.showinfo("Succès", "Serveur supprimé.", parent=self)
    
    def on_close(self):
        """Ferme l'application."""
        self.destroy()