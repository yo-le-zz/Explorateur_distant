# logic.py
import paramiko
import stat
import warnings
import os

warnings.filterwarnings("ignore", category=DeprecationWarning)

class SSHClient:
    def __init__(self, config):
        if isinstance(config, str):
            import json
            with open(config, "r") as f:
                self.cfg = json.load(f)
        else:
            self.cfg = config

        self.ssh = None
        self.sftp = None

    # ===================== CONNECT =====================

    def connect(self):
        cfg = self.cfg

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            auth = cfg.get("auth", {})
            auth_type = auth.get("type")

            if auth_type == "key":
                self._connect_with_key(cfg, auth)
            elif auth_type == "password":
                self._connect_with_password(cfg, auth)
            else:
                raise RuntimeError("Type d'authentification inconnu")

            self.sftp = self.ssh.open_sftp()

        except Exception as e:
            self.close()
            raise RuntimeError(f"Connexion SSH échouée : {e}")

    # ===================== AUTH METHODS =====================

    def _connect_with_key(self, cfg, auth):
        key_path = os.path.expanduser(auth.get("key_path"))
        if not key_path or not os.path.exists(key_path):
            raise FileNotFoundError("Clé SSH introuvable")

        pkey = None
        errors = []

        for key_cls in (
            paramiko.Ed25519Key,
            paramiko.RSAKey,
            paramiko.ECDSAKey,
        ):
            try:
                pkey = key_cls.from_private_key_file(key_path)
                break
            except Exception as e:
                errors.append(str(e))

        if pkey:
            self.ssh.connect(
                hostname=cfg["host"],
                port=cfg.get("port", 22),
                username=cfg["username"],
                pkey=pkey,
                look_for_keys=False,
                allow_agent=False,
                timeout=10,
                banner_timeout=10,
                auth_timeout=10
            )
        else:
            # fallback agent
            self.ssh.connect(
                hostname=cfg["host"],
                port=cfg.get("port", 22),
                username=cfg["username"],
                look_for_keys=True,
                allow_agent=True,
                timeout=10,
                banner_timeout=10,
                auth_timeout=10
            )

    def _connect_with_password(self, cfg, auth):
        password = auth.get("password")
        if not password:
            raise ValueError("Mot de passe manquant")

        self.ssh.connect(
            hostname=cfg["host"],
            port=cfg.get("port", 22),
            username=cfg["username"],
            password=password,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
            banner_timeout=10,
            auth_timeout=10
        )

    # ===================== SFTP HELPERS =====================

    def listdir_attr(self, path):
        return self.sftp.listdir_attr(path)

    def is_dir_attr(self, attr):
        return stat.S_ISDIR(attr.st_mode)

    def stat(self, path):
        return self.sftp.stat(path)

    def mkdir(self, remote_path):
        self.sftp.mkdir(remote_path)

    def remove_file(self, remote_path):
        self.sftp.remove(remote_path)

    def remove_dir(self, remote_path):
        self.sftp.rmdir(remote_path)

    def rename(self, old, new):
        self.sftp.rename(old, new)

    def download_to(self, remote_path, local_path):
        self.sftp.get(remote_path, local_path)

    def upload_from(self, local_path, remote_path):
        self.sftp.put(local_path, remote_path)

    def open_file_readbytes(self, remote_path):
        with self.sftp.open(remote_path, "rb") as f:
            return f.read()

    # ===================== CLOSE =====================

    def close(self):
        try:
            if self.sftp:
                self.sftp.close()
        except Exception:
            pass
        try:
            if self.ssh:
                self.ssh.close()
        except Exception:
            pass