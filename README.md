# gitlab-rag-sync

Automatically syncs one or more GitLab repositories into OpenWebUI knowledge bases so you can chat with your codebase using a local LLM.

Every sync interval (i.e., 1 hour), it pulls all text-based files from your GitLab project and indexes them into OpenWebUI using your configured embedding model. Binary files are detected and skipped automatically.

## How it works

1. Pulls all files from a GitLab project via the API
2. Skips binary files (images, archives, compiled files, etc.)
3. Resets and re-indexes the OpenWebUI custom knowledge base
4. Repeats every hour (or however long you configure it to repeat in the ENV settings)

## Requirements

- Docker
- Ollama running with at least one model pulled
- OpenWebUI running and accessible
- A GitLab instance (self-hosted or remote)
- `nomic-embed-text` pulled in Ollama and set as the embedding model in OpenWebUI

To set the embedding model: **OpenWebUI → Admin Panel → Settings → Documents → Embedding Model → nomic-embed-text**

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/mscirocco44/gitlab-rag-sync.git
```

### 2. Set up the directory structure

The `gitlab-rag` folder needs to sit alongside your `docker-compose.yml`. Copy it into the same directory as your compose file:

```bash
cp -r gitlab-rag/ /path/to/your/docker-compose-directory/
```

Your project layout should look like this:

```
your-project/
├── docker-compose.yml
├── gitlab-rag/
│   ├── sync.py
│   ├── Dockerfile
│   ├── .env
│   └── project-b.env    # only needed if syncing multiple repos
```

> The `build: gitlab-rag` line in the docker-compose service block tells Docker to look for a `Dockerfile` inside a folder called `gitlab-rag` relative to where `docker-compose.yml` lives. If the folder is placed elsewhere, update that path accordingly.

### 3. Create your .env file(s)

Copy the example and fill in your values. You need one `.env` file per GitLab project you want to index.

Ensure that your GitLab personal token has **read-only** permissions.

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

For multiple repos, create a separate env file for each with a unique `KNOWLEDGE_NAME`:

```bash
cp .env.example project-a.env
cp .env.example project-b.env
```

### 4. Add to your docker-compose.yml

See `example.docker-compose.yml` for a full reference. Below are the relevant service blocks.

> **Note on GITLAB_URL:**
> - If GitLab is running in Docker on the **same compose file**, use the container name as the hostname: `http://gitlab`. Docker's internal networking resolves container names automatically — no IP or port needed as long as GitLab is on port 80 inside the container (which it is by default).
> - If GitLab is on a **remote server**, use the actual IP or hostname with the port it is running on: `http://192.168.1.100:80`, `http://gitlab.company.com:8929`, or `https://gitlab.company.com`. If GitLab is on the default port (80 for HTTP, 443 for HTTPS), the port can be omitted.
>
> **Note on OPENWEBUI_URL:**
> - Always `http://open-webui:8080`. This is the internal Docker port for the OpenWebUI container and never changes, regardless of what port OpenWebUI is mapped to on your host machine.

---

#### Local GitLab (running in Docker) — single repo

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

#### Local GitLab (running in Docker) — multiple repos

Add one service block per project. Each needs a unique service name, container name, and env file:

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

#### Remote GitLab — single repo

Remove the `gitlab` depends_on condition since GitLab is not a local container. Set `GITLAB_URL` to your actual GitLab host and port:

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
      GITLAB_URL: "http://your-gitlab-host:port"
      OPENWEBUI_URL: "http://open-webui:8080"
      SYNC_INTERVAL: "3600"
```

If your remote GitLab runs on the default port 80 (or 443 for HTTPS), the port can be omitted:

```yaml
      GITLAB_URL: "http://your-gitlab-host"
      # or for HTTPS:
      GITLAB_URL: "https://your-gitlab-host"
```

#### Remote GitLab — multiple repos

Same as above but with one service block per project:

```yaml
  gitlab-rag-sync-project-a:
    build: gitlab-rag
    container_name: gitlab-rag-sync-project-a
    restart: always
    depends_on:
      open-webui:
        condition: service_healthy
    env_file:
      - gitlab-rag/project-a.env
    environment:
      GITLAB_URL: "http://your-gitlab-host:port"
      OPENWEBUI_URL: "http://open-webui:8080"
      SYNC_INTERVAL: "3600"

  gitlab-rag-sync-project-b:
    build: gitlab-rag
    container_name: gitlab-rag-sync-project-b
    restart: always
    depends_on:
      open-webui:
        condition: service_healthy
    env_file:
      - gitlab-rag/project-b.env
    environment:
      GITLAB_URL: "http://your-gitlab-host:port"
      OPENWEBUI_URL: "http://open-webui:8080"
      SYNC_INTERVAL: "3600"
```

### 5. Start it

```bash
docker compose up -d --build
docker logs -f gitlab-rag-sync
```

For multiple repos, all sync containers start together. You can tail a specific one:

```bash
docker logs -f gitlab-rag-sync-project-a
docker logs -f gitlab-rag-sync-project-b
```

---

## Full example docker-compose.yml

The assumed setup runs Ollama, OpenWebUI, and GitLab together in a single compose file. Here is what that looks like with `gitlab-rag-sync` included for a single local repo:

```yaml
services:

  ollama:
    image: ollama/ollama
    container_name: ollama
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    restart: unless-stopped

  open-webui:
    image: ghcr.io/open-webui/open-webui:v0.8.12
    container_name: open-webui
    depends_on:
      - ollama
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      - open_webui_data:/app/backend/data
    ports:
      - "3000:8080"
    restart: unless-stopped

  gitlab:
    image: gitlab/gitlab-ce:latest
    container_name: gitlab
    restart: always
    hostname: localhost
    environment:
      GITLAB_OMNIBUS_CONFIG: |
        external_url 'http://localhost'
        gitlab_rails['gitlab_shell_ssh_port'] = 2222
        puma['worker_processes'] = 2
        sidekiq['concurrency'] = 5
        prometheus_monitoring['enable'] = false
    ports:
      - "80:80"
      - "443:443"
      - "2222:22"
    volumes:
      - gitlab_config:/etc/gitlab
      - gitlab_logs:/var/log/gitlab
      - gitlab_data:/var/opt/gitlab
    shm_size: '256m'

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

volumes:
  ollama_data:
  open_webui_data:
  gitlab_config:
  gitlab_logs:
  gitlab_data:
```

> Remove `runtime: nvidia` from the ollama service if you do not have an NVIDIA GPU.
> See `example.docker-compose.yml` for multi-repo and remote GitLab variations.

---

## Usage

Once the first sync completes, open OpenWebUI and start a chat. Type `#` and select a knowledge base from the dropdown, then ask questions about your code:

```
#gitlab-repo do we have a script that handles authentication?
#project-a-repo where are API calls being made?
#project-b-repo explain the overall structure of this project
```

Each knowledge base corresponds to one GitLab project and is queryable independently.

---

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

---

## Notes

- The knowledge base is fully reset on each sync to stay consistent with the repo
- Files over 500KB are skipped
- Any file that fails UTF-8 decoding is treated as binary and skipped
- Sync interval can be changed via the `SYNC_INTERVAL` environment variable (in seconds)
- Each GitLab project requires its own service block and `.env` file with a unique `KNOWLEDGE_NAME`
