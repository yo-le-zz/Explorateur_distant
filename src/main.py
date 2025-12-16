# main.py
import sys, os
import bcrypt
import tkinter as tk
from tkinter import messagebox
from logic import SSHClient
from config import get_data
from ui import ExplorerUI, ServerManagerUI
import delete
import requests
import threading
import subprocess # Ajout nécessaire pour exécuter l'updater

version = "V1.0.3"
# Vos variables globales d'update
update_name = "update.exe"
update_url = "https://github.com/yo-le-zz/GenericUpdater/releases/latest/download/update.exe"
# programme_url pointe vers le répertoire des releases pour vérifier la dernière version
programme_url = "https://github.com/yo-le-zz/Explorateur_distant/releases/latest/" 
# Le nom de l'exécutable principal (à remplacer par le nom réel de votre .exe)
PROGRAM_NAME = "Explorateur_distant.exe" 
# Le repository pour l'updater
REPO_NAME = os.path.basename(os.path.dirname(__file__))


# Nouvelle classe pour le mode 1-serveur (inchangée)
class MainExplorerUI(ExplorerUI):
    """ExplorerUI modifiée pour hériter de tk.Tk lorsque c'est la seule fenêtre principale."""
    def __init__(self, ssh_client, start_path="/", config_callback=None):
        # ... (reste du code MainExplorerUI inchangé)
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
# Fin MainExplorerUI


def get_latest_version(url_latest_release):
    """Récupère la balise (tag) de la dernière release depuis l'URL."""
    try:
        # L'URL /latest/ fait une redirection vers la dernière release, le header 'Location' la contient.
        response = requests.head(url_latest_release, allow_redirects=True, timeout=5)
        
        # Exemple: https://github.com/yo-le-zz/Explorateur_distant/releases/tag/V1.0.4
        latest_tag = response.url.split("/")[-1]
        
        if latest_tag.startswith('V'):
            return latest_tag
        return None
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de la vérification de la version en ligne : {e}")
        return None

def version_is_newer(current_version, latest_version):
    """Compare deux versions au format V<major>.<minor>.<patch>."""
    try:
        # Nettoyer et convertir les parties de la version en entiers
        current_parts = [int(p) for p in current_version.lstrip('V').split('.')]
        latest_parts = [int(p) for p in latest_version.lstrip('V').split('.')]
        
        # Comparaison tuple par tuple
        return latest_parts > current_parts
    except Exception as e:
        print(f"Erreur lors de la comparaison des versions : {e}")
        return False

def run_updater(update_exe_path, program_name, repo_name):
    """Télécharge, exécute l'updater et quitte le programme principal."""
    try:
        print(f"Téléchargement de l'updater depuis {update_url}")
        # Télécharger l'updater (vous pourriez avoir besoin d'une fonction de téléchargement ici)
        # Par souci de simplicité, supposons que vous avez une fonction qui télécharge
        # requests.get et écriture dans update_exe_path
        
        updater_content = requests.get(update_url, timeout=10).content
        with open(update_exe_path, 'wb') as f:
            f.write(updater_content)

        # Lancement de l'updater avec le pattern demandé
        # update.exe --update "Explorateur_distant.exe" "yo-le-zz/Explorateur_distant"
        command = [
            update_exe_path, 
            "--update", 
            program_name, 
            repo_name
        ]
        
        # Lancer l'updater sans attendre sa fin et quitter le programme actuel
        subprocess.Popen(command, close_fds=True)
        print("Mise à jour lancée. Fermeture du programme actuel.")
        sys.exit(0)
        
    except Exception as e:
        messagebox.showerror("Erreur de Mise à Jour", f"Impossible d'exécuter la mise à jour : {e}")
        # On ne quitte pas si l'updater échoue, on continue avec l'ancienne version.

def check_for_updates():
    """Vérifie si une mise à jour est disponible et la lance si oui."""
    latest_version = get_latest_version(programme_url)

    if latest_version and version_is_newer(version, latest_version):
        # Une mise à jour est disponible
        root_dialog = tk.Tk()
        root_dialog.withdraw()

        if messagebox.askyesno(
            "Mise à Jour Disponible", 
            f"Une nouvelle version ({latest_version}) est disponible. Voulez-vous la télécharger et l'installer maintenant ? Votre version actuelle est {version}."
        ):
            root_dialog.destroy() # Détruire proprement la fenêtre de dialogue
            run_updater(update_name, PROGRAM_NAME, REPO_NAME)
        else:
            root_dialog.destroy() # Détruire proprement la fenêtre de dialogue
            print("Mise à jour refusée par l'utilisateur.")
    elif latest_version:
        print(f"Version actuelle ({version}) est à jour.")
    else:
        print("Impossible de vérifier la version en ligne.")


def main():
    delete.clean_temp()

    # **********************************************
    # AJOUTER LA VÉRIFICATION DE MISE À JOUR ICI
    check_for_updates()
    # **********************************************
    
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
    # ... (reste du code CLI inchangé) ...

    main()
