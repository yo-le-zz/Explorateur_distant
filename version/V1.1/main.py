# main.py
import sys
import tkinter as tk
from logic import SSHClient
from config import get_data
from ui import ExplorerUI
import delete

def main():
    # Nettoyage des fichiers temporaires au démarrage
    delete.clean_temp()

    # Création de la fenêtre Tkinter principale
    root = tk.Tk()
    root.withdraw()  # Masquer la fenêtre principale pour les dialogues

    # Charger la configuration
    cfg = get_data(root)

    # Initialiser le client SSH
    ssh = SSHClient(cfg)
    try:
        ssh.connect()
    except Exception as e:
        tk.messagebox.showerror("Erreur SSH", str(e))
        sys.exit(1)

    # Créer et afficher l'interface principale
    app = ExplorerUI(ssh_client=ssh, start_path=cfg.get("start_path", "/"))
    app.mainloop()

if __name__ == "__main__":
    main()
