# delete.py
import os, tempfile, shutil

def clean_temp():
    temp_dir = tempfile.gettempdir()
    for f in os.listdir(temp_dir):
        path = os.path.join(temp_dir, f)
        try:
            if f.endswith(".tmp") or f.startswith("tmp"):
                if os.path.isfile(path):
                    os.remove(path)
                elif os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
        except:
            pass
