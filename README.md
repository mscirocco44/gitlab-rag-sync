# gitlab-rag-sync

Automatically syncs a GitLab repository into an OpenWebUI knowledge base so you can chat with your codebase using a local LLM.

Every hour, it pulls all text-based files from your GitLab project and indexes them into OpenWebUI using your configured embedding model. Binary files are detected and skipped automatically.

## How it works

1. Pulls all files from a GitLab project via the API
2. Skips binary files (images, archives, compiled files, etc.)
3. Resets and re-indexes the OpenWebUI knowledge base
4. Repeats every hour

## Requirements

- Docker
- Ollama running with at least one model pulled
- OpenWebUI running and accessible
- A GitLab instance (self-hosted or remote)
- `nomic-embed-text` pulled in Ollama and set as the embedding model in OpenWebUI

To set the embedding model: **OpenWebUI → Admin Panel → Settings → Documents → Embedding Model → nomic-embed-text**

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/gitlab-rag-sync.git
```

### 2. Fill in the .env file

Copy the example and fill in your values:

```bash
cp .env.example .env
```

```
GITLAB_TOKEN=        # GitLab personal access token (read_api scope)
GITLAB_PROJECT_ID=   # Found under your project name in GitLab
GITLAB_BRANCH=main
OPENWEBUI_TOKEN=     # OpenWebUI API key (Settings → Account → API Keys)
KNOWLEDGE_NAME=gitlab-repo
```

### 3. Add to your docker-compose.yml

**If GitLab is running locally in Docker (same compose file):**

```yaml
  gitlab-rag-sync:
    build: gitlab-rag
    container_name: gitlab-rag-sync
    restart: always
    depends_on:
      open-webui:
        condition: service_healthy
      gitlab:
        condition: service_healthy
    env_file:
      - gitlab-rag/.env
    environment:
      GITLAB_URL: "http://gitlab"
      OPENWEBUI_URL: "http://open-webui:8080"
      SYNC_INTERVAL: "3600"
```

**If GitLab is hosted remotely:**

```yaml
  gitlab-rag-sync:
    build: gitlab-rag
    container_name: gitlab-rag-sync
    restart: always
    depends_on:
      open-webui:
        condition: service_healthy
    env_file:
      - gitlab-rag/.env
    environment:
      GITLAB_URL: "http://your-gitlab-host"
      OPENWEBUI_URL: "http://open-webui:8080"
      SYNC_INTERVAL: "3600"
```

> `OPENWEBUI_URL` uses the internal container port (8080), not the host-mapped port.

### 4. Start it

```bash
docker compose up -d --build gitlab-rag-sync
docker logs -f gitlab-rag-sync
```

## Usage

Once the first sync completes, open OpenWebUI and start a chat. Type `#` and select your knowledge base, then ask questions about your code:

```
#gitlab-repo do we have a script that handles authentication?
#gitlab-repo where are API calls being made?
#gitlab-repo explain the overall structure of this project
```

## Useful commands

```bash
# Force an immediate resync
docker restart gitlab-rag-sync

# Watch sync output
docker logs -f gitlab-rag-sync

# Update tokens without rebuilding
# Edit .env, then:
docker compose up -d gitlab-rag-sync
```

## Notes

- The knowledge base is fully reset on each sync to stay consistent with the repo
- Files over 500KB are skipped
- Any file that fails UTF-8 decoding is treated as binary and skipped
- Sync interval can be changed via the `SYNC_INTERVAL` environment variable (in seconds)
