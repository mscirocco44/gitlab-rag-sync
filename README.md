# gitlab-rag-sync

Automatically syncs one or more GitLab repositories into OpenWebUI knowledge bases so you can chat with your codebase using a local LLM.

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

### 2. Create your .env file(s)

Copy the example and fill in your values. You need one `.env` file per GitLab project you want to index.

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

For multiple repos, create a separate env file for each:

```bash
cp .env.example project-a.env
cp .env.example project-b.env
```

Each env file should have a unique `KNOWLEDGE_NAME` so they appear as separate knowledge bases in OpenWebUI.

### 3. Add to your docker-compose.yml

See `example.docker-compose.yml` for a full reference. Below are the relevant service blocks to copy in.

**Single repo — GitLab running locally in Docker:**

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

**Single repo — GitLab hosted remotely:**

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

**Multiple repos — add one service block per project:**

```yaml
  gitlab-rag-sync-project-a:
    build: gitlab-rag
    container_name: gitlab-rag-sync-project-a
    restart: always
    depends_on:
      open-webui:
        condition: service_healthy
      gitlab:
        condition: service_healthy
    env_file:
      - gitlab-rag/project-a.env
    environment:
      GITLAB_URL: "http://gitlab"
      OPENWEBUI_URL: "http://open-webui:8080"
      SYNC_INTERVAL: "3600"

  gitlab-rag-sync-project-b:
    build: gitlab-rag
    container_name: gitlab-rag-sync-project-b
    restart: always
    depends_on:
      open-webui:
        condition: service_healthy
      gitlab:
        condition: service_healthy
    env_file:
      - gitlab-rag/project-b.env
    environment:
      GITLAB_URL: "http://gitlab"
      OPENWEBUI_URL: "http://open-webui:8080"
      SYNC_INTERVAL: "3600"
```

> `OPENWEBUI_URL` uses the internal container port (8080), not the host-mapped port.
>
> Each service needs a unique `container_name` and a separate `.env` file with a unique `KNOWLEDGE_NAME`.

### 4. Start it

```bash
docker compose up -d --build
docker logs -f gitlab-rag-sync
```

For multiple repos, all sync containers start together. You can tail a specific one:

```bash
docker logs -f gitlab-rag-sync-project-a
docker logs -f gitlab-rag-sync-project-b
```

## Usage

Once the first sync completes, open OpenWebUI and start a chat. Type `#` and select a knowledge base from the dropdown, then ask questions about your code:

```
#gitlab-repo do we have a script that handles authentication?
#project-a-repo where are API calls being made?
#project-b-repo explain the overall structure of this project
```

Each knowledge base corresponds to one GitLab project and is queryable independently.

## Useful commands

```bash
# Force an immediate resync (single repo)
docker restart gitlab-rag-sync

# Force resync for a specific repo (multiple repos)
docker restart gitlab-rag-sync-project-a

# Watch sync output
docker logs -f gitlab-rag-sync

# Update tokens without rebuilding — edit the .env file, then:
docker compose up -d gitlab-rag-sync

# Rebuild after editing sync.py or Dockerfile
docker compose up -d --build gitlab-rag-sync
```

## Notes

- The knowledge base is fully reset on each sync to stay consistent with the repo
- Files over 500KB are skipped
- Any file that fails UTF-8 decoding is treated as binary and skipped
- Sync interval can be changed via the `SYNC_INTERVAL` environment variable (in seconds)
- Each GitLab project requires its own service block and `.env` file
