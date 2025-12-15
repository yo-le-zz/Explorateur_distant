# ui.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import threading
import os
import posixpath
import tempfile

class ExplorerUI(tk.Tk):
    def __init__(self, ssh_client, start_path="/", config_callback=None):
        super().__init__()
        self.ssh = ssh_client
        self.current = start_path or "/"
        self.config_callback = config_callback

        self.title("Explorateur distant")
        self.geometry("1200x700")
        self.configure(bg="#0A3D62")

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
                  command=self.reset_config).pack(side="right")

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
        try:
            rows = []
            for e in self.ssh.listdir_attr(self.current):
                typ = "Dossier" if self.ssh.is_dir_attr(e) else "Fichier"
                size = "" if typ == "Dossier" else str(e.st_size)
                rows.append((e.filename, typ, size))
            self.after(0, lambda: self.populate(rows))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erreur SSH", str(e)))

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
                messagebox.showwarning("Binaire", "Fichier binaire non affichable")
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
            messagebox.showerror("Erreur", str(e))

    def save_file(self, path, content):
        try:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(content.encode())
                tmp_path = tmp.name
            self.ssh.upload_from(tmp_path, path)
            os.unlink(tmp_path)
            self.refresh()
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

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
            messagebox.showerror("Erreur", str(e))

    def rename_item(self, name):
        new = simpledialog.askstring("Renommer", "Nouveau nom:", parent=self)
        if new:
            self.ssh.rename(
                posixpath.join(self.current, name),
                posixpath.join(self.current, new)
            )
            self.refresh()

    def create_folder(self):
        name = simpledialog.askstring("Créer dossier", "Nom:", parent=self)
        if name:
            self.ssh.mkdir(posixpath.join(self.current, name))
            self.refresh()

    def create_file(self):
        name = simpledialog.askstring("Créer fichier", "Nom:", parent=self)
        if name:
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp_path = tmp.name
            self.ssh.upload_from(tmp_path, posixpath.join(self.current, name))
            os.unlink(tmp_path)
            self.refresh()

    def upload(self):
        file_path = filedialog.askopenfilename(parent=self)
        if file_path:
            self.ssh.upload_from(
                file_path,
                posixpath.join(self.current, os.path.basename(file_path))
            )
            self.refresh()

    def download_item(self, name):
        dest = filedialog.asksaveasfilename(initialfile=name, parent=self)
        if dest:
            self.ssh.download_to(posixpath.join(self.current, name), dest)

    # ===================== CONFIG =====================

    def change_config(self):
        if self.config_callback:
            self.config_callback()

    def reset_config(self):
        from config import reset_and_restart
        reset_and_restart()
