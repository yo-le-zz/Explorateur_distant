# main.py
import sys, os
import tkinter as tk
from logic import SSHClient
from config import get_data
from ui import ExplorerUI
import delete

def main():
    # Nettoyage fichiers temporaires
    delete.clean_temp()

    # Tk temporaire pour dialogues
    root = tk.Tk()
    root.withdraw()
    cfg = get_data(root)
    root.destroy()

    # SSH
    ssh = SSHClient(cfg)
    try:
        ssh.connect()
    except Exception as e:
        tk.messagebox.showerror("Erreur SSH", str(e))
        sys.exit(1)

    # Fonction pour modifier la config
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
            tk.messagebox.showerror("Erreur SSH", f"Impossible de reconnecter : {e}")

    # UI principale
    app = ExplorerUI(ssh_client=ssh,
                     start_path=cfg.get("start_path", "/"),
                     config_callback=edit_config)

    # Hook fermeture propre
    def on_close():
        try: ssh.close()
        except: pass
        try: app.destroy()
        except: pass
        sys.exit(0)

    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()

if __name__ == "__main__":
    main()
