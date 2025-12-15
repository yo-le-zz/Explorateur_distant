# main.py
import sys, os
import bcrypt
import tkinter as tk
from tkinter import messagebox
from logic import SSHClient
from config import get_data
from ui import ExplorerUI, ServerManagerUI # Ajout de ServerManagerUI pour clarté
import delete

# Nouvelle classe pour le mode 1-serveur
class MainExplorerUI(ExplorerUI):
    """ExplorerUI modifiée pour hériter de tk.Tk lorsque c'est la seule fenêtre principale."""
    def __init__(self, ssh_client, start_path="/", config_callback=None):
        # MainExplorerUI hérite directement de tk.Tk pour ce cas.
        tk.Tk.__init__(self) # Appel direct à l'init de Tk
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


def main():
    delete.clean_temp()

    import config as cfgmod

    chosen = None

    entries = cfgmod.load_entries()

    if not entries:
        # Aucun serveur -> création via UI
        root = tk.Tk()
        root.withdraw()
        chosen = cfgmod.manage_servers(root)
        root.destroy()
        
        if not chosen:
            sys.exit(0)
    
    # CORRECTION ICI: Si 1 ou plusieurs serveurs existent, on lance le gestionnaire.
    # Ceci correspond à la version corrigée que nous avions mise.
    elif len(entries) >= 1: # Si 1 ou plus, on ouvre le manager.
        cfgmod.open_server_manager() # Lance ServerManagerUI (qui hérite de tk.Tk) et appelle mainloop()
        return

    # Si on arrive ici, cela signifie qu'on a créé un nouveau serveur (cas `if not entries`)
    # et qu'il faut le lancer directement.
    if not chosen:
        sys.exit(0)

    # Construction config SSH
    try:
        port = int(chosen.get("user_port", 22))
    except (ValueError, TypeError):
        port = 22

    if chosen.get("key_path"):
        auth = {"type": "key", "key_path": chosen.get("key_path")}
    else:
        auth = {"type": "password", "password": chosen.get("password")}

    cfg = {
        "host": chosen.get("user_host"),
        "port": port,
        "username": chosen.get("user_serveur"),
        "auth": auth,
        "start_path": chosen.get("user_start_path", "/")
    }

    # Connexion SSH (dans le thread principal, car c'est la seule chose qui se passe)
    ssh = SSHClient(cfg)
    try:
        ssh.connect()
    except Exception as e:
        messagebox.showerror("Erreur SSH", str(e))
        sys.exit(1)

    # Callback pour éditer la configuration (uniquement dans le mode 1-serveur)
    def edit_config():
        temp_root = tk.Tk()
        temp_root.withdraw()
        new_cfg = get_data(temp_root)
        temp_root.destroy()

        try:
            ssh.close()
            new_ssh = SSHClient(new_cfg)
            new_ssh.connect()
            app.ssh = new_ssh
            app.current = new_cfg.get("start_path", "/")
            app.refresh()
        except Exception as e:
            messagebox.showerror("Erreur SSH", f"Impossible de reconnecter : {e}")

    # Lancement de l'Explorateur (utilise MainExplorerUI pour hériter de tk.Tk)
    app = MainExplorerUI(
        ssh_client=ssh,
        start_path=cfg.get("start_path", "/"),
        config_callback=edit_config
    )

    def on_close():
        try: ssh.close()
        except: pass
        try: app.destroy()
        except: pass
        sys.exit(0)

    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()

if __name__ == "__main__":
    # ... (reste du code CLI inchangé) ...
    main()