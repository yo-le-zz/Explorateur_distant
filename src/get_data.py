# The get data script allows you to encrypt and decrypt via the server; for this, you just need to fill in your server's HMAC key and the Ngrok link.

import os, sys
import uuid
import datetime
import hmac
import hashlib
import json
import requests

def get_path(name: str):
    """Retourne le chemin correct, compatible PyInstaller."""
    if getattr(sys, 'frozen', False):
        # PyInstaller mode bundle
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, name)

# =========================
# CONFIG
# =========================
SERVER_URL = "https://stannic-uncomprehended-cornelius.ngrok-free.dev/activate"
HMAC_SECRET = b"\xd8\xa1\x88\xe2\xf4\x9b\x17m\x9f#\xe5\xfa\xbd\xfc\xee\xeb\x96\xca@\x03\xc5\x0cn\x85\xeak4\x9frm)I"

LICENSE_PATH = get_path("license.txt")
MACHINE_ID_PATH = get_path("machine_id.txt")

# =========================
# UTILS
# =========================
def get_local_path(name: str):
    """Retourne le chemin correct, compatible PyInstaller."""
    if getattr(sys, 'frozen', False):
        # PyInstaller mode bundle
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, name)

def load_license():
    path = get_local_path(LICENSE_PATH)
    if not os.path.exists(path):
        key = input("Licence : ").strip()
        with open(path, "w") as f:
            f.write(key)
        return key
    return open(path).read().strip()

def get_machine_id():
    path = get_local_path(MACHINE_ID_PATH)
    if os.path.exists(path):
        return open(path).read().strip()
    mid = str(uuid.uuid4())
    with open(path, "w") as f:
        f.write(mid)
    return mid

def generate_signature(machine_id, timestamp):
    msg = f"{machine_id}:{timestamp}".encode()
    return hmac.new(HMAC_SECRET, msg, hashlib.sha256).hexdigest()

def bits_to_bytes(bits: str) -> bytes:
    if len(bits) % 8 != 0:
        raise ValueError("Bits invalides")
    return bytes(int(bits[i:i+8], 2) for i in range(0, len(bits), 8))

def bytes_to_bits(data: bytes) -> str:
    return ''.join(format(b, "08b") for b in data)

# =========================
# CORE GATEWAY
# =========================
def process_with_server(
    *,
    action: str,
    source_type: str,
    data,
    is_binary: bool,
    bits_representation=False
):
    # Normalisation des données
    if source_type == "file":
        with open(data, "rb") as f:
            payload_data = f.read()
    elif source_type == "content":
        payload_data = data.encode() if not is_binary else data
    else:
        raise ValueError("source_type invalide")

    # Si bits=True
    if bits_representation:
        if action == "decrypt":
            bits_str = payload_data.decode() if isinstance(payload_data, bytes) else payload_data
            bits_str = bits_str.replace(" ", "").replace("\n", "")
            if len(bits_str) % 8 != 0:
                bits_str += "0" * (8 - len(bits_str) % 8)
            payload_data = bits_to_bytes(bits_str)
        # encrypt : conversion bits se fera après

    # Payload serveur
    license_key = load_license()
    machine_id = get_machine_id()
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    signature = generate_signature(machine_id, timestamp)

    payload = {
        "license_key": license_key,
        "machine_id": machine_id,
        "timestamp": timestamp,
        "signature": signature,
        "action": action
    }

    if action == "decrypt":
        payload["ciphertext"] = payload_data.decode("latin1") if isinstance(payload_data, bytes) else payload_data
    elif action == "encrypt":
        payload["plaintext"] = payload_data.decode("latin1") if isinstance(payload_data, bytes) else payload_data
    else:
        raise ValueError("Action invalide")

    r = requests.post(SERVER_URL, json=payload)
    if r.status_code != 200:
        raise Exception(r.text)

    resp_json = r.json()

    # Récupération adaptée au serveur
    if action == "encrypt" and "ciphertext" in resp_json:
        result_bytes = resp_json["ciphertext"].encode("latin1")
        if bits_representation:
            result_bits = bytes_to_bits(result_bytes)
            return result_bits.encode()
        return result_bytes
    elif action == "decrypt" and "decrypted" in resp_json:
        decrypted_json = resp_json["decrypted"]
        result_bytes = json.dumps(decrypted_json).encode("utf-8")
        return result_bytes
    else:
        raise Exception(f"Réponse inattendue du serveur : {resp_json}")


# =========================
# API SIMPLIFIÉE
# =========================
def encrypt(*, source_type, data, is_binary=True, bits=False):
    return process_with_server(
        action="encrypt",
        source_type=source_type,
        data=data,
        is_binary=is_binary,
        bits_representation=bits
    )

def decrypt(*, source_type, data, is_binary=True, bits=False):
    return process_with_server(
        action="decrypt",
        source_type=source_type,
        data=data,
        is_binary=is_binary,
        bits_representation=bits
    )