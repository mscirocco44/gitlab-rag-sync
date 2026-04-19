import os
import time
import urllib.parse
from pathlib import Path
import requests

GITLAB_URL        = os.environ['GITLAB_URL']
GITLAB_TOKEN      = os.environ['GITLAB_TOKEN']
GITLAB_PROJECT_ID = os.environ['GITLAB_PROJECT_ID']
GITLAB_BRANCH     = os.environ.get('GITLAB_BRANCH', 'main')
OPENWEBUI_URL     = os.environ['OPENWEBUI_URL']
OPENWEBUI_TOKEN   = os.environ['OPENWEBUI_TOKEN']
KNOWLEDGE_NAME    = os.environ.get('KNOWLEDGE_NAME', 'gitlab-repo')
SYNC_INTERVAL     = int(os.environ.get('SYNC_INTERVAL', 3600))

MAX_FILE_BYTES = 500_000  # skip files over 500KB

# Extensions that are always binary — skip these
SKIP_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.svg', '.webp',
    '.mp4', '.mp3', '.wav', '.avi', '.mov', '.mkv',
    '.zip', '.tar', '.gz', '.bz2', '.rar', '.7z',
    '.exe', '.dll', '.so', '.dylib', '.bin', '.obj', '.o', '.a',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.pyc', '.pyo', '.class', '.jar',
    '.ttf', '.otf', '.woff', '.woff2', '.eot',
    '.db', '.sqlite', '.sqlite3',
}


def gl_headers():
    return {'PRIVATE-TOKEN': GITLAB_TOKEN}

def ow_headers():
    return {'Authorization': f'Bearer {OPENWEBUI_TOKEN}'}


def get_all_files():
    files, page = [], 1
    while True:
        r = requests.get(
            f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/repository/tree",
            headers=gl_headers(),
            params={'recursive': 'true', 'per_page': 100, 'page': page, 'ref': GITLAB_BRANCH},
            timeout=30
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        files.extend(f['path'] for f in batch if f['type'] == 'blob')
        if len(batch) < 100:
            break
        page += 1
    return files


def is_text(content):
    """Return True if content appears to be text (not binary)."""
    try:
        content.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False


def should_skip(path):
    return Path(path).suffix.lower() in SKIP_EXTENSIONS


def fetch_file(path):
    encoded = urllib.parse.quote(path, safe='')
    r = requests.get(
        f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/repository/files/{encoded}/raw",
        headers=gl_headers(),
        params={'ref': GITLAB_BRANCH},
        timeout=30
    )
    if r.status_code == 200 and len(r.content) <= MAX_FILE_BYTES:
        return r.content
    return None


def get_or_create_knowledge():
    r = requests.get(f"{OPENWEBUI_URL}/api/v1/knowledge/", headers=ow_headers(), timeout=10)
    r.raise_for_status()
    for kb in r.json():
        if kb['name'] == KNOWLEDGE_NAME:
            return kb['id']
    r = requests.post(
        f"{OPENWEBUI_URL}/api/v1/knowledge/create",
        headers=ow_headers(),
        json={'name': KNOWLEDGE_NAME, 'description': f'Auto-synced from GitLab project {GITLAB_PROJECT_ID}'},
        timeout=10
    )
    r.raise_for_status()
    return r.json()['id']


def reset_knowledge(kb_id):
    requests.post(f"{OPENWEBUI_URL}/api/v1/knowledge/{kb_id}/reset", headers=ow_headers(), timeout=10)


def upload_and_index(kb_id, path, content):
    flat_name = path.replace('/', '__')
    labelled = f"# File: {path}\n\n".encode() + content

    r = requests.post(
        f"{OPENWEBUI_URL}/api/v1/files/",
        headers=ow_headers(),
        files={'file': (flat_name, labelled, 'text/plain')},
        timeout=30
    )
    if r.status_code != 200:
        return False

    file_id = r.json()['id']
    r = requests.post(
        f"{OPENWEBUI_URL}/api/v1/knowledge/{kb_id}/file/add",
        headers=ow_headers(),
        json={'file_id': file_id},
        timeout=10
    )
    return r.status_code == 200


def sync():
    print("=== Starting GitLab -> OpenWebUI sync ===")
    kb_id = get_or_create_knowledge()
    reset_knowledge(kb_id)
    print(f"Knowledge base '{KNOWLEDGE_NAME}' reset.")

    all_files = get_all_files()
    print(f"Repo has {len(all_files)} files. Scanning all...")

    ok, skipped = 0, 0
    for path in all_files:
        if should_skip(path):
            print(f"  SKIP  (binary ext) {path}")
            skipped += 1
            continue

        content = fetch_file(path)
        if content is None:
            print(f"  SKIP  (too large or fetch failed) {path}")
            skipped += 1
            continue

        if not is_text(content):
            print(f"  SKIP  (binary content) {path}")
            skipped += 1
            continue

        if upload_and_index(kb_id, path, content):
            print(f"  OK    {path}")
            ok += 1
        else:
            print(f"  FAIL  {path}")
            skipped += 1

    print(f"=== Done: {ok} indexed, {skipped} skipped. Next sync in {SYNC_INTERVAL}s ===\n")


if __name__ == '__main__':
    while True:
        try:
            sync()
            time.sleep(SYNC_INTERVAL)
        except Exception as e:
            print(f"ERROR: {e}")
            print("Retrying in 30 seconds...")
            time.sleep(30)

