# ui_tk.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import os
import posixpath

class ExplorerUI(tk.Tk):
    def __init__(self, ssh_client, start_path="/", config_callback=None):
        super().__init__()
        self.ssh = ssh_client
        self.current = start_path or "/"   # chemin de base
        self.config_callback = config_callback

        self.history = [self.current]
        self.history_index = 0

        self.title("Explorateur distant")
        self.geometry("1200x700")
        self.configure(bg="#0A3D62")

        # Icône
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "app.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self._build_ui()
        self.refresh()

    def _build_ui(self):
        # Navigation
        nav_frame = tk.Frame(self, bg="#0A3D62")
        nav_frame.pack(fill="x", padx=5, pady=5)
        self.btn_prev = tk.Button(nav_frame, text="← Dossier parent", bg="#0E4F95", fg="white", command=self.go_parent)
        self.btn_prev.pack(side="left", padx=2)
        self.btn_next = tk.Button(nav_frame, text="→ Suivant", bg="#0E4F95", fg="white", command=self.go_next)
        self.btn_next.pack(side="left", padx=2)
        self.btn_config = tk.Button(nav_frame, text="Modifier infos", bg="#0E4F95", fg="white",
                                    command=self.change_config)
        self.btn_config.pack(side="right", padx=2)
        self.btn_create_file = tk.Button(nav_frame, text="Créer fichier", bg="#0E4F95", fg="white",
                                         command=self.create_file)
        self.btn_create_file.pack(side="right", padx=2)

        # Chemin + Refresh
        path_frame = tk.Frame(self, bg="#0A3D62")
        path_frame.pack(fill="x", padx=5, pady=5)
        self.path_edit = tk.Entry(path_frame, font=("Arial", 12))
        self.path_edit.pack(side="left", fill="x", expand=True, padx=2)
        self.path_edit.insert(0, self.current)
        refresh_btn = tk.Button(path_frame, text="Refresh", bg="#0E4F95", fg="white", command=self.refresh)
        refresh_btn.pack(side="left", padx=2)

        # Treeview
        style = ttk.Style(self)
        style.configure("Treeview",
                        background="#333333",
                        foreground="#A1D6E2",
                        fieldbackground="#333333")
        style.map("Treeview", background=[('selected', '#0E4F95')])
        self.tree = ttk.Treeview(self, columns=("type", "size"))
        self.tree.heading("#0", text="Nom")
        self.tree.heading("type", text="Type")
        self.tree.heading("size", text="Taille")
        self.tree.column("#0", width=500)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree.bind("<Double-1>", lambda e: self.on_double_click())
        self.tree.bind("<Button-3>", self.show_menu)

    # --- Navigation ---
    def refresh(self):
        path = self.path_edit.get().strip() or "/"
        if path != self.current:
            # ajouter historique
            self.history = self.history[:self.history_index+1]
            self.history.append(path)
            self.history_index += 1
            self.current = path
        threading.Thread(target=self.refresh_worker, daemon=True).start()

    def refresh_worker(self):
        try:
            entries = self.ssh.listdir_attr(self.current)
            rows = []
            for e in entries:
                item_type = "Dossier" if self.ssh.is_dir_attr(e) else "Fichier"
                size = str(e.st_size) if item_type == "Fichier" else ""
                rows.append((str(e.filename), item_type, size))
            self.after(0, lambda: self.populate(rows))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erreur SSH", str(e)))

    def populate(self, rows):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for name, typ, size in rows:
            self.tree.insert("", "end", text=name, values=(typ, size))

    def go_parent(self):
        if self.current != "/":
            self.current = posixpath.dirname(self.current)
            self.path_edit.delete(0, "end")
            self.path_edit.insert(0, self.current)
            self.refresh()

    def go_next(self):
        if self.history_index + 1 < len(self.history):
            self.history_index += 1
            self.current = self.history[self.history_index]
            self.path_edit.delete(0, "end")
            self.path_edit.insert(0, self.current)
            self.refresh()

    # --- Double click / open ---
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

    def open_item(self, name):
        path = posixpath.join(self.current, name)
        try:
            data = self.ssh.open_file_readbytes(path)
            dlg = tk.Toplevel(self)
            dlg.title(name)
            dlg.geometry("600x400")
            text = tk.Text(dlg, bg="#333333", fg="#A1D6E2")
            text.insert("1.0", data.decode(errors='ignore'))
            text.pack(fill="both", expand=True)
            save_btn = tk.Button(dlg, text="Enregistrer", bg="#0E4F95", fg="white",
                                 command=lambda: self.save_file(path, text.get("1.0","end")))
            save_btn.pack(pady=5)
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def save_file(self, path, content):
        try:
            local_path = os.path.join(os.path.expanduser("~"), "temp_edit_file")
            with open(local_path, "wb") as f:
                f.write(content.encode())
            self.ssh.upload_from(local_path, path)
            messagebox.showinfo("Succès", "Fichier sauvegardé !")
            self.refresh()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    # --- Context menu ---
    def show_menu(self, event):
        iid = self.tree.identify_row(event.y)
        menu = tk.Menu(self, tearoff=0)
        if iid:
            name = self.tree.item(iid, "text")
            typ = self.tree.item(iid, "values")[0]
            menu.add_command(label="Ouvrir", command=lambda: self.open_item(name))
            menu.add_command(label="Supprimer", command=lambda: self.delete_item(name, typ))
            menu.add_command(label="Renommer", command=lambda: self.rename_item(name))
        menu.add_command(label="Créer dossier", command=self.create_folder)
        menu.add_command(label="Créer fichier", command=self.create_file)
        menu.add_command(label="Uploader", command=self.upload)
        if iid and self.tree.item(iid, "values")[0] == "Fichier":
            menu.add_command(label="Télécharger", command=lambda: self.download_item(name))
        menu.post(event.x_root, event.y_root)

    # --- CRUD ---
    def delete_item(self, name, typ):
        path = posixpath.join(self.current, name)
        try:
            if typ == "Dossier":
                self.ssh.remove_dir(path)
            else:
                self.ssh.remove_file(path)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    def rename_item(self, name):
        new_name = simpledialog.askstring("Renommer", "Nouveau nom:", parent=self)
        if new_name:
            old_path = posixpath.join(self.current, name)
            new_path = posixpath.join(self.current, new_name)
            try:
                self.ssh.rename(old_path, new_path)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

    def create_folder(self):
        name = simpledialog.askstring("Créer dossier", "Nom du dossier:", parent=self)
        if name:
            path = posixpath.join(self.current, name)
            try:
                self.ssh.mkdir(path)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de créer : {e}")

    def create_file(self):
        name = simpledialog.askstring("Créer fichier", "Nom du fichier:", parent=self)
        if name:
            path = posixpath.join(self.current, name)
            try:
                # créer un fichier vide
                temp = os.path.join(os.path.expanduser("~"), "temp_new_file")
                with open(temp, "wb") as f:
                    f.write(b"")
                self.ssh.upload_from(temp, path)
                self.refresh()
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de créer : {e}")

    def upload(self):
        file_path = filedialog.askopenfilename(parent=self)
        if not file_path: return
        remote_path = posixpath.join(self.current, os.path.basename(file_path))
        try:
            self.ssh.upload_from(file_path, remote_path)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'uploader : {e}")

    def download_item(self, name):
        remote_path = posixpath.join(self.current, name)
        local_path = filedialog.asksaveasfilename(initialfile=name, parent=self)
        if not local_path: return
        try:
            self.ssh.download_to(remote_path, local_path)
            messagebox.showinfo("Succès", f"{name} téléchargé !")
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

    # --- Config ---
    def change_config(self):
        if self.config_callback:
            self.config_callback()
