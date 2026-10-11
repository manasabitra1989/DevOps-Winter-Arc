# Task 2 — Dockerfile Deep Dive

## Objective

Learn essential Dockerfile instructions, containerize a Python application, pass environment variables, and understand Docker layer caching.

## Project Structure

```text
Task2-Dockerfile_Deep_Dive/
├── app/
│   └── app.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── README.md
└── evidence/
```

| File | Purpose |
|---|---|
| `app/app.py` | Python HTTP application with root and health endpoints |
| `requirements.txt` | Lists Python dependencies |
| `Dockerfile` | Defines how to build the application image |
| `.dockerignore` | Excludes unnecessary files from the build context |
| `README.md` | Documents the lab and results |
| `evidence/` | Stores screenshots and test evidence |

## Task 1 — Create the Python Application

File: `app/app.py`

```python
import os
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

APP_ENV = os.getenv("APP_ENV", "development")
APP_VERSION = os.getenv("APP_VERSION", "1.0")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            response = {"status": "ok"}
        else:
            response = {
                "message": "Hello from Docker!",
                "environment": APP_ENV,
                "version": APP_VERSION
            }

        body = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

HTTPServer(("0.0.0.0", 5000), Handler).serve_forever()
```

**Code explanation:**
- `os.getenv()` reads environment variables and provides defaults.
- `BaseHTTPRequestHandler` handles HTTP requests.
- `do_GET()` handles GET requests.
- `/health` returns the application's health status.
- `json.dumps()` converts a Python dictionary into JSON.
- `HTTPServer()` starts the server on port `5000`.
- `0.0.0.0` allows the server to accept connections through the container's network interface.

## Task 2 — Configure Dependencies

File: `requirements.txt`

This file lists external Python packages required by the application. This lab uses only Python's standard library, so the file can remain empty.

## Task 3 — Create the Dockerfile

File: `Dockerfile`

```dockerfile
FROM python:3.12-slim

ARG APP_BUILD=local

WORKDIR /app

ENV APP_ENV=production
ENV APP_VERSION=1.0
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 5000

CMD ["python", "app/app.py"]
```

### Dockerfile instructions explained

| Instruction | Purpose |
|---|---|
| `FROM` | Selects the base image. |
| `ARG` | Defines a build-time variable. |
| `WORKDIR` | Sets the working directory inside the image. |
| `ENV` | Sets environment variables available at runtime by default. |
| `COPY` | Copies files into the image. |
| `RUN` | Executes commands during image building. |
| `EXPOSE` | Documents the application's listening port. |
| `CMD` | Specifies the default command when a container starts. |

Additional details:
- `python:3.12-slim` is a smaller Python base image.
- `APP_BUILD` demonstrates a build argument; the application does not use it.
- `PYTHONDONTWRITEBYTECODE=1` prevents Python from writing bytecode files.
- `PYTHONUNBUFFERED=1` makes Python output available promptly in container logs.
- `pip install --no-cache-dir` installs dependencies without retaining pip's download cache.
- Copying `requirements.txt` before application code helps preserve the dependency-installation cache when only source code changes.

## Task 4 — Create `.dockerignore`

File: `.dockerignore`

```text
.git
.gitignore
__pycache__/
*.pyc
.env
.venv/
venv/
```

**Purpose:** Excludes unnecessary files from the Docker build context. This can reduce build overhead and helps prevent local environment files from being copied into the image.

Do not store secrets in the Dockerfile or bake them into the image.

## Task 5 — Build the Docker Image

```bash
docker build --build-arg APP_BUILD=task2 -t task2-python:v1 .
```

Verify:

```bash
docker images task2-python
docker image inspect task2-python:v1
```

**Command explanation:**
- `docker build` builds the image.
- `--build-arg` supplies a build-time argument.
- `-t task2-python:v1` assigns the image name and tag.
- `.` uses the current directory as the build context.
- `docker image inspect` displays image configuration and metadata.

## Task 6 — Run and Test the Container

```bash
docker run -d \
  --name task2-app \
  -p 5000:5000 \
  task2-python:v1
```

Test the root endpoint:

```bash
curl http://localhost:5000/
```

Expected response:

```json
{
  "message": "Hello from Docker!",
  "environment": "production",
  "version": "1.0"
}
```

Test the health endpoint:

```bash
curl http://localhost:5000/health
```

Expected response:

```json
{
  "status": "ok"
}
```

Check the container:

```bash
docker ps
docker logs task2-app
docker port task2-app
```

**Explanation:** `-d` runs the container in the background, while `-p 5000:5000` maps host port `5000` to container port `5000`.

## Task 7 — Pass Environment Variables

Remove the existing lab container before recreating it:

```bash
docker rm -f task2-app
```

Run it with custom environment variables:

```bash
docker run -d \
  --name task2-app \
  -p 5000:5000 \
  -e APP_ENV=testing \
  -e APP_VERSION=2.0 \
  task2-python:v1
```

Test the application:

```bash
curl http://localhost:5000/
```

The response should contain:

```json
{
  "message": "Hello from Docker!",
  "environment": "testing",
  "version": "2.0"
}
```

Verify the variables:

```bash
docker exec task2-app printenv APP_ENV
docker exec task2-app printenv APP_VERSION
```

**Key difference:**
- `ARG` is used during the image build.
- `ENV` defines default environment variables in the image.
- `docker run -e` sets or overrides environment variables for a container.

## Task 8 — Demonstrate Docker Layer Caching

Build the image again without changing any files:

```bash
docker build --progress=plain -t task2-python:v1 .
```

Look for `CACHED` messages in the build output.

Next, change the application's greeting in `app/app.py` and build a new tag:

```bash
docker build --progress=plain -t task2-python:v2 .
```

Observe which steps are cached and which are rebuilt.

**Why does the Dockerfile copy dependencies first?**

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
```

When application source changes but `requirements.txt` and the preceding build inputs remain unchanged, Docker can reuse the dependency-installation layer.

## Task 9 — Understand `ADD` vs `COPY`

`COPY` copies local files and directories into the image.

`ADD` supports additional behavior, including automatic extraction of supported local tar archives.

For normal application files, prefer:

```dockerfile
COPY app/ ./app/
```

Use `ADD` only when you need its additional features.

## Task 10 — Understand `CMD` vs `ENTRYPOINT`

The Dockerfile uses:

```dockerfile
CMD ["python", "app/app.py"]
```

- `CMD` defines the default command or arguments.
- `ENTRYPOINT` defines the main executable for the container.

An alternative is:

```dockerfile
ENTRYPOINT ["python", "app/app.py"]
```

Keep the original `CMD` for this lab.

## Task 11 — Troubleshooting

| Problem | Diagnostic command |
|---|---|
| Port is already in use | `docker ps` |
| Container exits | `docker ps -a` |
| Application fails | `docker logs task2-app` |
| Environment variable is incorrect | `docker exec task2-app printenv APP_ENV` |
| Build caching is unclear | `docker build --progress=plain -t task2-python:v1 .` |
| Unnecessary files enter the build context | Review `.dockerignore` |

If port `5000` is occupied, you can use another host port:

```bash
docker run -d \
  --name task2-app-alt \
  -p 5001:5000 \
  task2-python:v1
```

Test with:

```bash
curl http://localhost:5001/
```

## Task 12 — Evidence and Results

Save screenshots or command output in `evidence/`.

- [ ] Docker image built successfully.
- [ ] Root endpoint returns JSON.
- [ ] Health endpoint returns `ok`.
- [ ] Runtime environment variables override the defaults.
- [ ] Image configuration inspected successfully.
- [ ] Docker layer caching demonstrated.
- [ ] `.dockerignore` created and reviewed.
- [ ] Troubleshooting results recorded.

| Test | Result |
|---|---|
| Image build | Pass / Fail |
| Root endpoint | Pass / Fail |
| Health endpoint | Pass / Fail |
| Environment variables | Pass / Fail |
| Layer caching | Pass / Fail |
| `.dockerignore` | Pass / Fail |

## Interview Questions

**1. What is a Dockerfile?**

A text file containing instructions to build a Docker image.

**2. What is the difference between `RUN` and `CMD`?**

`RUN` executes during image building; `CMD` specifies the default command when a container starts.

**3. What is the difference between `ARG` and `ENV`?**

`ARG` provides build-time variables, while `ENV` defines environment variables available in the image and at runtime by default.

**4. What is the difference between `COPY` and `ADD`?**

Both copy files, but `ADD` has additional behaviors. `COPY` is preferred for ordinary local files.

**5. What does `WORKDIR` do?**

Sets the working directory for subsequent instructions and the container's default working directory.

**6. Does `EXPOSE` publish a port?**

No. It documents the intended port. Use `-p` to publish a port to the host.

**7. What is Docker layer caching?**

Docker reuses eligible build layers when instructions and their inputs have not changed.

**8. Why copy the dependency manifest before the source code?**

It allows dependency-installation layers to be reused when only application source code changes.

**9. What is `.dockerignore`?**

A file that excludes matching files from the Docker build context.

**10. What is the difference between an image and a container?**

An image is the packaged template; a container is an instance created from that image.

## Cleanup and Git

Remove only the containers created for this lab:

```bash
docker rm -f task2-app task2-app-alt
```

Check your Git changes:

```bash
git status
```

Stage and commit:

```bash
git add app/app.py requirements.txt Dockerfile .dockerignore README.md evidence/
git commit -m "Complete Task 2 Dockerfile deep dive"
git push
```

## Final Summary

In this lab, you created a Python application and packaged it into a Docker image. You practiced the essential Dockerfile instructions, passed runtime environment variables, used `.dockerignore`, and observed Docker layer caching.

**Key takeaway:** A reusable Dockerfile should be clear, configurable, efficient to rebuild, and easy to maintain.
