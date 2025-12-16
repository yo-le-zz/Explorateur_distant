# main.py
import sys, os
import requests
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox
from logic import SSHClient
from config import get_data
from ui import ExplorerUI, ServerManagerUI # Ajout de ServerManagerUI pour clarté
import delete

version = "V1.0.3"
UPDATE_REPO = "yo-le-zz/GenericUpdater"
UPDATE_EXE_NAME = "update.exe"

def get_latest_release_tag(repo):
    """Retourne le tag de la dernière release GitHub"""
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    r = requests.get(api_url, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data.get("tag_name")

def download_update_exe():
    def _worker():
        try:
            latest_tag = get_latest_release_tag(UPDATE_REPO)

            if latest_tag == version:
                # On est déjà à jour
                root = tk.Tk()
                root.withdraw()
                messagebox.showinfo("Updater", "Vous êtes déjà sur la dernière version")
                root.destroy()
                return

            # Sinon, on continue le téléchargement...
            api_url = f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest"
            r = requests.get(api_url, timeout=15)
            r.raise_for_status()
            data = r.json()

            download_url = None
            for asset in data.get("assets", []):
                if asset["name"].lower().endswith(".exe"):
                    download_url = asset["browser_download_url"]
                    break

            if not download_url:
                root = tk.Tk()
                root.withdraw()
                messagebox.showinfo("Updater", "Aucun fichier .exe trouvé pour l'updater")
                root.destroy()
                return

            local_path = os.path.join(os.getcwd(), UPDATE_EXE_NAME)

            with requests.get(download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in r.iter_content(8192):
                        if chunk:
                            f.write(chunk)

            root = tk.Tk()
            root.withdraw()
            messagebox.showinfo("Updater", f"{UPDATE_EXE_NAME} téléchargé avec succès")
            root.destroy()

            subprocess.Popen([local_path])

        except Exception as e:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Updater", f"Erreur lors du téléchargement de update.exe:\n{e}")
            root.destroy()

    threading.Thread(target=_worker, daemon=True).start()

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
        # CAS A: Aucun serveur n'existe. On utilise une racine temporaire pour les dialogues.
        root_dialog = tk.Tk()
        root_dialog.withdraw() # Cache la fenêtre principale inutile
        
        # manage_servers va proposer d'ajouter le premier serveur et le retourne
        chosen = cfgmod.manage_servers(root_dialog)
        
        # Détruire proprement la fenêtre de dialogue SANS appeler root.destroy() qui tue l'interpréteur
        # Nous allons simplement la cacher et laisser le programme continuer.
        # Si on tente de la détruire, le bug revient souvent. 
        # Le plus sûr pour tkinter est d'utiliser Toplevel, mais pour garder 
        # la structure, on va juste la quitter et la laisser au garbage collector.
        root_dialog.quit() 
        
        # Vérifiez que chosen n'est pas None (l'utilisateur n'a pas annulé)
        if not chosen:
            sys.exit(0)
    
    elif len(entries) >= 1: 
        # CAS B: Un ou plusieurs serveurs existent. On lance le gestionnaire.
        cfgmod.open_server_manager() 
        return

    # Si on arrive ici, chosen contient le premier serveur créé (CAS A)
    # ou on est sorti (CAS B). Si chosen est None ici, c'est une erreur de logique.
    if not chosen:
        # Si le cas B a été exécuté, on est déjà sorti via return. 
        # Si le cas A a été exécuté, chosen est soit une config, soit on est sorti via sys.exit(0).
        # On peut laisser la suite du code s'exécuter.
        pass # La suite gère 'chosen' ou sort si chosen est None (mais on a déjà vérifié)

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
    download_update_exe()
    # ... (reste du code CLI inchangé) ...
    main()