# ui.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import os
import posixpath
import tempfile
from logic import SSHClient

# --- GESTION DRAG & DROP ---
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

class ExplorerUI(tk.Toplevel):
    def __init__(self, parent, ssh_client, start_path="/", config_callback=None):
        super().__init__(parent)
        self.ssh = ssh_client
        self.current = start_path or "/"
        self.config_callback = config_callback
        self.all_rows = []  # Cache pour le filtrage local

        self.title("Explorateur distant")
        self.geometry("1200x700")
        self.configure(bg="#0A3D62")

        self._build_ui()
        
        if HAS_DND:
            self.tree.drop_target_register(DND_FILES)
            self.tree.dnd_bind('<<Drop>>', self._on_drop)
            
        self.refresh()

    def _build_ui(self):
        # --- Barre de Navigation ---
        nav = tk.Frame(self, bg="#0A3D62")
        nav.pack(fill="x", padx=5, pady=5)
        
        tk.Button(nav, text="← Parent", bg="#0E4F95", fg="white", command=self.go_parent).pack(side="left", padx=2)
        tk.Button(nav, text="Modifier infos", bg="#0E4F95", fg="white", command=self.change_config).pack(side="right", padx=2)

        # --- Barre de Chemin ---
        path_frame = tk.Frame(self, bg="#0A3D62")
        path_frame.pack(fill="x", padx=5)
        
        self.path_edit = tk.Entry(path_frame, bg="#333333", fg="#A1D6E2")
        self.path_edit.pack(side="left", fill="x", expand=True)
        self.path_edit.insert(0, self.current)
        self.path_edit.bind("<Return>", lambda e: self.refresh())
        
        tk.Button(path_frame, text="Actualiser", bg="#0E4F95", fg="white", command=self.refresh).pack(side="left", padx=2)

        # --- Barre de Recherche (Filtre) ---
        search_frame = tk.Frame(self, bg="#0A3D62")
        search_frame.pack(fill="x", padx=5, pady=2)
        
        tk.Label(search_frame, text="🔍 Filtrer:", fg="white", bg="#0A3D62").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._filter_tree())
        tk.Entry(search_frame, textvariable=self.search_var, bg="#333333", fg="white").pack(side="left", fill="x", expand=True)

        # --- Treeview Style ---
        style = ttk.Style(self)
        style.configure("Treeview", background="#333333", foreground="#A1D6E2", fieldbackground="#333333")
        style.map("Treeview", background=[("selected", "#0E4F95")])

        # --- Treeview ---
        self.tree = ttk.Treeview(self, columns=("type", "size"), selectmode="browse")
        self.tree.heading("#0", text="Nom")
        self.tree.heading("type", text="Type")
        self.tree.heading("size", text="Taille")
        self.tree.column("#0", width=600)
        self.tree.column("type", width=100)
        self.tree.column("size", width=100)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree.bind("<Double-1>", lambda e: self.on_double_click())
        self.tree.bind("<Button-3>", self.show_menu)

        # --- Barre de Progrès ---
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", side="bottom", padx=5, pady=2)

    # ===================== LOGIQUE DE FILTRE =====================
    def _filter_tree(self):
        query = self.search_var.get().lower()
        self.tree.delete(*self.tree.get_children())
        for r in self.all_rows:
            if query in r[0].lower():
                self.tree.insert("", "end", text=r[0], values=r[1:])

    # ===================== DRAG & DROP =====================
    def _on_drop(self, event):
        files = self.tk.splitlist(event.data)
        for f in files:
            dest_path = posixpath.join(self.current, os.path.basename(f))
            threading.Thread(target=self._upload_worker, args=(f, dest_path), daemon=True).start()

    def _upload_worker(self, local_path, remote_path):
        try:
            self.ssh.upload_from(local_path, remote_path)
            self.after(0, self.refresh)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erreur Upload", str(e)))

    # ===================== REFRESH & POPULATE =====================
    def refresh(self):
        self.current = self.path_edit.get().strip() or "/"
        threading.Thread(target=self.refresh_worker, daemon=True).start()

    def refresh_worker(self):
        try:
            rows = []
            for item in self.ssh.listdir_attr(self.current):
                typ = "Dossier" if self.ssh.is_dir_attr(item) else "Fichier"
                size = "" if typ == "Dossier" else f"{item.st_size / 1024:.1f} KB"
                rows.append((item.filename, typ, size))
            
            # Trier par type (dossiers d'abord) puis nom
            rows.sort(key=lambda x: (x[1] != "Dossier", x[0].lower()))
            
            self.all_rows = rows # Mise à jour du cache
            self.after(0, lambda: self.populate(rows))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erreur SSH", str(e), parent=self))

    def populate(self, rows):
        self.tree.delete(*self.tree.get_children())
        # On applique le filtre actuel s'il y en a un
        query = self.search_var.get().lower()
        for r in rows:
            if query in r[0].lower():
                self.tree.insert("", "end", text=r[0], values=r[1:])

    # ===================== NAVIGATION =====================
    def go_parent(self):
        if self.current != "/":
            self.current = posixpath.dirname(self.current)
            self.path_edit.delete(0, "end")
            self.path_edit.insert(0, self.current)
            self.refresh()

    def on_double_click(self):
        item = self.tree.selection()
        if not item: return
        name = self.tree.item(item, "text")
        typ = self.tree.item(item, "values")[0]
        
        if typ == "Dossier":
            self.current = posixpath.join(self.current, name)
            self.path_edit.delete(0, "end")
            self.path_edit.insert(0, self.current)
            self.refresh()
        else:
            self.open_item(name)

    # ===================== FILE OPERATIONS =====================
    def open_item(self, name):
        path = posixpath.join(self.current, name)
        try:
            data = self.ssh.open_file_readbytes(path)
            if b"\x00" in data:
                messagebox.showwarning("Binaire", "Fichier binaire non affichable", parent=self)
                return

            dlg = tk.Toplevel(self)
            dlg.title(f"Édition : {name}")
            dlg.geometry("800x600")

            text_area = tk.Text(dlg, bg="#333333", fg="#A1D6E2", insertbackground="white")
            text_area.insert("1.0", data.decode(errors="ignore"))
            text_area.pack(fill="both", expand=True)

            tk.Button(dlg, text="💾 Enregistrer", bg="#0E4F95", fg="white",
                      command=lambda: self.save_file(path, text_area.get("1.0", "end-1c"), dlg)).pack(pady=5)
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=self)

    def save_file(self, path, content, window):
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(content.encode("utf-8"))
                tmp_path = tmp.name
            self.ssh.upload_from(tmp_path, path)
            os.unlink(tmp_path)
            messagebox.showinfo("Succès", "Fichier enregistré.", parent=window)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Erreur", str(e), parent=window)

    def show_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
            name = self.tree.item(iid, "text")
            typ = self.tree.item(iid, "values")[0]
            
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Ouvrir", command=lambda: self.open_item(name))
            menu.add_command(label="Renommer", command=lambda: self.rename_item(name))
            menu.add_command(label="Supprimer", command=lambda: self.delete_item(name, typ))
            if typ == "Fichier":
                menu.add_command(label="Télécharger", command=lambda: self.download_item(name))
            
            menu.add_separator()
            menu.add_command(label="Nouveau Dossier", command=self.create_folder)
            menu.add_command(label="Nouveau Fichier", command=self.create_file)
            menu.add_command(label="Uploader...", command=self.upload)
            menu.post(event.x_root, event.y_root)

    # ... [Reste des méthodes CRUD identiques à votre logique] ...
    def delete_item(self, name, typ):
        if messagebox.askyesno("Confirmation", f"Supprimer {name} ?"):
            path = posixpath.join(self.current, name)
            try:
                if typ == "Dossier": self.ssh.remove_dir(path)
                else: self.ssh.remove_file(path)
                self.refresh()
            except Exception as e: messagebox.showerror("Erreur", str(e))

    def rename_item(self, name):
        new = simpledialog.askstring("Renommer", "Nouveau nom:", initialvalue=name, parent=self)
        if new:
            try:
                self.ssh.rename(posixpath.join(self.current, name), posixpath.join(self.current, new))
                self.refresh()
            except Exception as e: messagebox.showerror("Erreur", str(e))

    def create_folder(self):
        name = simpledialog.askstring("Nouveau dossier", "Nom:", parent=self)
        if name:
            try:
                self.ssh.mkdir(posixpath.join(self.current, name))
                self.refresh()
            except Exception as e: messagebox.showerror("Erreur", str(e))

    def create_file(self):
        name = simpledialog.askstring("Nouveau fichier", "Nom:", parent=self)
        if name:
            try:
                # Créer un fichier vide localement puis l'uploader
                fd, path = tempfile.mkstemp()
                os.close(fd)
                self.ssh.upload_from(path, posixpath.join(self.current, name))
                os.remove(path)
                self.refresh()
            except Exception as e: messagebox.showerror("Erreur", str(e))

    def upload(self):
        f = filedialog.askopenfilename(parent=self)
        if f: self._upload_worker(f, posixpath.join(self.current, os.path.basename(f)))

    def download_item(self, name):
        dest = filedialog.asksaveasfilename(initialfile=name, parent=self)
        if dest:
            threading.Thread(target=lambda: self.ssh.download_to(posixpath.join(self.current, name), dest), daemon=True).start()

    def change_config(self):
        if self.config_callback: self.config_callback()

# =================================================================
# SERVER MANAGER UI
# =================================================================

class ServerManagerUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestionnaire de serveurs SSH")
        self.geometry("650x450")
        self.configure(bg="#0A3D62")
        self.explorers = {}
        self._build_ui()
        self.refresh_list()

    def _build_ui(self):
        # Titre
        tk.Label(self, text="Mes Serveurs", bg="#0A3D62", fg="#A1D6E2", 
                 font=("Arial", 12, "bold")).pack(pady=10)
        
        # --- RÉAJOUT DE LA LISTBOX (L'élément manquant) ---
        # C'est cet élément que self.refresh_list() cherche à modifier
        self.lb = tk.Listbox(self, bg="#333333", fg="#A1D6E2", 
                             font=("Consolas", 10), selectbackground="#0E4F95")
        self.lb.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Bindings pour la listbox
        self.lb.bind("<Double-1>", lambda e: self.connect_server())
        self.lb.bind("<Button-3>", self.show_context_menu)

        # --- Barre de boutons ---
        btn_frame = tk.Frame(self, bg="#0A3D62")
        btn_frame.pack(fill="x", padx=10, pady=15) 
        
        # Bouton Connecter
        tk.Button(btn_frame, text="🚀 Connecter", command=self.connect_server, 
                  bg="#27ae60", fg="white", width=12, height=1).pack(side="left", padx=5)
        
        # Bouton Ajouter
        tk.Button(btn_frame, text="➕ Ajouter", command=self.add_server, 
                  bg="#0E4F95", fg="white", width=10, height=1).pack(side="left", padx=5)
        
        # --- BOUTON SUPPRIMER (VERSION AJUSTÉE) ---
        tk.Button(btn_frame, 
                  text="🗑️ SUPPRIMER", 
                  command=self.delete_server, 
                  bg="#e74c3c", 
                  fg="white", 
                  font=("Arial", 9, "bold"), # Police un peu plus petite
                  width=14,                  # Largeur réduite (était à 18)
                  height=1,                  # Retour à la hauteur normale (était à 2)
                  relief="raised",
                  cursor="hand2"
                  ).pack(side="left", padx=10) # Espacement (padx) réduit à 10

    def show_context_menu(self, event):
        idx = self.lb.nearest(event.y)
        if idx >= 0:
            self.lb.selection_clear(0, "end")
            self.lb.selection_set(idx)
            
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Connecter", command=self.connect_server)
            menu.add_command(label="Modifier", command=self.edit_server)
            menu.add_command(label="Infos détaillées", command=self.show_info)
            menu.add_separator()
            menu.add_command(label="Supprimer", command=self.delete_server)
            menu.post(event.x_root, event.y_root)

    def refresh_list(self):
        from config import load_entries
        self.entries = load_entries()
        self.lb.delete(0, "end")
        for e in self.entries:
            self.lb.insert("end", f" {e.get('user_serveur')}@{e.get('user_host')}  ({e.get('user_start_path', '/')})")

    def connect_server(self):
        cur = self.lb.curselection()
        if not cur: return
        
        entry = self.entries[cur[0]]
        server_display = f"{entry.get('user_serveur')}@{entry.get('user_host')}"
        
        # Préparation config pour SSHClient
        try:
            port = int(entry.get("user_port", 22))
            auth = {"type": "key", "key_path": entry["key_path"]} if entry.get("key_path") else {"type": "password", "password": entry.get("password")}
            
            cfg = {
                "host": entry["user_host"],
                "port": port,
                "username": entry["user_serveur"],
                "auth": auth,
                "start_path": entry.get("user_start_path", "/")
            }
            
            ssh = SSHClient(cfg)
            threading.Thread(target=self._connection_worker, args=(ssh, cfg, server_display), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Erreur", f"Config invalide : {e}")

    def _connection_worker(self, ssh, cfg, name):
        try:
            ssh.connect()
            self.after(0, lambda: self._open_explorer(ssh, cfg, name))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Echec Connexion", str(e)))

    def _open_explorer(self, ssh, cfg, name):
        explorer = ExplorerUI(self, ssh, cfg.get("start_path", "/"))
        explorer.title(f"SSH: {name}")
        self.explorers[name] = explorer

    def add_server(self):
        from config import prompt_new_server, save_entries
        res = prompt_new_server(self)
        if res:
            self.entries.append(res[0])
            save_entries(self.entries)
            self.refresh_list()

    def edit_server(self):
        cur = self.lb.curselection()
        if not cur: return
        from config import prompt_new_server, save_entries
        res = prompt_new_server(self, entry_to_edit=self.entries[cur[0]])
        if res:
            self.entries[cur[0]] = res[0]
            save_entries(self.entries)
            self.refresh_list()

    def delete_server(self):
        cur = self.lb.curselection()
        if cur and messagebox.askyesno("Supprimer", "Supprimer ce serveur de la liste ?"):
            from config import save_entries
            self.entries.pop(cur[0])
            save_entries(self.entries)
            self.refresh_list()

    def show_info(self):
        cur = self.lb.curselection()
        if not cur: return
        e = self.entries[cur[0]]
        txt = f"Utilisateur: {e.get('user_serveur')}\nHôte: {e.get('user_host')}\nPort: {e.get('user_port', 22)}\nDépart: {e.get('user_start_path')}"
        messagebox.showinfo("Détails Serveur", txt)