# Docker Week 2 — Task 5: Docker Compose Full-Stack Application

## 1. Project Overview

### Objective

Build and run a multi-container application using **Docker Compose** with a single command.

The application contains three services:

- **Flask:** Provides the web application and HTTP endpoints.
- **PostgreSQL:** Stores persistent visit records.
- **Redis:** Maintains an in-memory counter for HTTP requests.

Docker Compose manages the containers, networking, environment variables, health checks, startup dependencies, restart policies, and persistent storage.

### Learning objectives

By completing this lab, I will learn how to:

1. Define multiple services in `compose.yaml`.
2. Build a custom application image using a Dockerfile.
3. Connect containers using Compose service names.
4. Configure applications through environment variables.
5. Configure health checks and service dependencies.
6. Persist PostgreSQL data with a named volume.
7. Test container failure and restart behavior.
8. Protect secrets using `.env` and `.gitignore`.
9. Troubleshoot container, network, and database problems.

---

## 2. Application Architecture

```text
                  Browser / curl
                        |
                        | HTTP :5000
                        v
               +-------------------+
               |    Flask: web     |
               |    Port 5000      |
               +-------------------+
                     |        |
                     |        |
              Redis counter   PostgreSQL records
                     |        |
                     v        v
                +--------+  +----------+
                | Redis  |  | Postgres |
                | redis  |  |    db    |
                +--------+  +----------+
                                 |
                                 v
                           +-----------+
                           | pgdata    |
                           | Named     |
                           | volume    |
                           +-----------+
```

### How it works

1. A user sends an HTTP request to `http://localhost:5000`.
2. Docker forwards the host's port `5000` to the Flask container's port `5000`.
3. Flask increments the Redis request counter.
4. Flask inserts a visit record into PostgreSQL and retrieves the total.
5. Flask returns both counts in the HTTP response.
6. PostgreSQL stores its data in the named volume `pgdata`, allowing it to survive container replacement.

Only Flask publishes a host port. PostgreSQL and Redis communicate with Flask through the private Compose network.

---

## 3. Project Directory Structure

```text
Task5-Compose-Full-Stack/
├── app/
│   ├── app.py
│   ├── requirements.txt
│   └── Dockerfile
├── compose.yaml
├── .env
├── .env.example
├── .gitignore
└── README.md
```

| File | Purpose |
|---|---|
| `app/app.py` | Flask application, Redis counter, and PostgreSQL queries |
| `app/requirements.txt` | Python package dependencies |
| `app/Dockerfile` | Instructions to build the Flask image |
| `compose.yaml` | Defines the web, database, and Redis services |
| `.env` | Local database configuration and password |
| `.env.example` | Safe template for environment configuration |
| `.gitignore` | Prevents secrets and temporary files from being committed |
| `README.md` | Project documentation |

---

## 4. Step 1 — Create the Project

Open Ubuntu/WSL and run:

```bash
mkdir -p ~/DevOps-Winter-Arc/Week2-Docker/Task5-Compose-Full-Stack/app

cd ~/DevOps-Winter-Arc/Week2-Docker/Task5-Compose-Full-Stack
```

Verify the directory:

```bash
pwd
ls -la
```

- `mkdir -p` creates the directories, including parent directories when needed.
- `cd` changes the current working directory.
- `pwd` displays the current path.
- `ls -la` displays files, including hidden files.

---

## 5. Step 2 — Create the Flask Application

Create `app/requirements.txt`:

```text
flask==3.0.3
redis==5.0.8
psycopg2-binary==2.9.9
```

### Dependency explanations

- `flask`: Provides the HTTP web framework.
- `redis`: Provides the Python Redis client.
- `psycopg2-binary`: Allows Python to connect to PostgreSQL.

Create `app/app.py`:

```python
import os
import time

import psycopg2
import redis
from flask import Flask

app = Flask(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
DB_HOST = os.getenv("DB_HOST", "db")

POSTGRES_DB = os.getenv("POSTGRES_DB", "visits")
POSTGRES_USER = os.getenv("POSTGRES_USER", "appuser")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")


def get_redis():
    return redis.Redis(
        host=REDIS_HOST,
        port=6379,
        decode_responses=True,
        socket_connect_timeout=3,
    )


def get_db():
    return psycopg2.connect(
        host=DB_HOST,
        port=5432,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=3,
    )


def wait_for_db():
    for attempt in range(20):
        try:
            conn = get_db()
            conn.close()
            print("PostgreSQL connection successful")
            return
        except psycopg2.OperationalError:
            print(f"Waiting for PostgreSQL ({attempt + 1}/20)")
            time.sleep(2)

    raise RuntimeError("PostgreSQL did not become available")


@app.route("/")
def home():
    r = get_redis()
    hits = r.incr("hits")

    conn = get_db()

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS visits (
                        id SERIAL PRIMARY KEY,
                        visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cur.execute("INSERT INTO visits DEFAULT VALUES")
                cur.execute("SELECT COUNT(*) FROM visits")

                visits = cur.fetchone()[0]
    finally:
        conn.close()

    return f"Redis hits: {hits} | PostgreSQL visits: {visits}\n"


@app.route("/health")
def health():
    return "ok\n", 200


if __name__ == "__main__":
    wait_for_db()
    app.run(host="0.0.0.0", port=5000)
```

### Explanation of important code

**`os.getenv()`**

Reads environment variables supplied by Docker Compose. This lets the same application run with different configuration without changing the source code.

**`get_redis()`**

Connects to Redis using hostname `redis` and port `6379`.

**`get_db()`**

Connects to PostgreSQL using the hostname `db` and the configured credentials.

**`wait_for_db()`**

Retries the PostgreSQL connection while the database starts. This adds application-level retry behavior in addition to Compose startup dependencies.

**`r.incr("hits")`**

Increments a Redis integer counter named `hits`.

**`CREATE TABLE IF NOT EXISTS`**

Creates the PostgreSQL table if it does not already exist.

**`INSERT INTO visits DEFAULT VALUES`**

Adds one row for each successful request to `/`.

**`SELECT COUNT(*) FROM visits`**

Retrieves the total number of visit records.

**`@app.route("/health")`**

Defines a health endpoint that returns `ok`.

This is a basic application-response check. It does not independently test database or Redis connectivity.

**`host="0.0.0.0"`**

Allows Flask to accept connections through the container's network interface instead of listening only on its loopback interface.

---

## 6. Step 3 — Create the Dockerfile

Create `app/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN useradd --system appuser

USER appuser

EXPOSE 5000

CMD ["python", "app.py"]
```

### Dockerfile instruction explanations

| Instruction | Explanation |
|---|---|
| `FROM` | Selects the base image |
| `WORKDIR` | Sets the working directory inside the image |
| `ENV` | Sets environment variables |
| `COPY` | Copies files into the image |
| `RUN` | Executes commands during image building |
| `USER` | Sets the user used to run subsequent instructions and the application |
| `EXPOSE` | Documents the port used by the application |
| `CMD` | Defines the default startup command |

### Why copy `requirements.txt` first?

Docker can cache the dependency-installation layer. If only `app.py` changes, Docker may reuse the dependency layer rather than reinstalling packages.

### Why run as a non-root user?

Running the application as `appuser` follows the principle of least privilege and reduces the permissions available to the application.

### Does `EXPOSE 5000` publish the port?

No. The Compose configuration must publish the port using:

```yaml
ports:
  - "5000:5000"
```

The first port is the host port; the second is the container port.

---

## 7. Step 4 — Configure Environment Variables

Create `.env`:

```dotenv
POSTGRES_DB=visits
POSTGRES_USER=appuser
POSTGRES_PASSWORD=change-me-local-only
```

Create `.env.example`:

```dotenv
POSTGRES_DB=visits
POSTGRES_USER=appuser
POSTGRES_PASSWORD=replace-with-your-own-password
```

Create `.gitignore`:

```gitignore
.env
__pycache__/
*.pyc
.venv/
```

### Why use `.env`?

Environment variables keep configuration separate from application source code and make it easier to change database settings.

### Why use `.env.example`?

It documents the required variables without sharing the actual local password.

### Security warning

The password shown here is for a local lab only. Do not use it in production. Environment variables are convenient for learning but are not a complete production secret-management solution.

Also, PostgreSQL initialization variables such as `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` are applied when the database data directory is initialized. Changing `.env` later does not automatically update credentials in an existing database.

---

## 8. Step 5 — Create `compose.yaml`

Create `compose.yaml` in the project root:

```yaml
services:
  web:
    build: ./app
    ports:
      - "5000:5000"
    env_file:
      - .env
    environment:
      DB_HOST: db
      REDIS_HOST: redis
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:16-alpine
    env_file:
      - .env
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test:
        - CMD-SHELL
        - pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped

volumes:
  pgdata:
```

### Explanation of the Compose configuration

#### `services`

Defines the containers that make up the application.

#### `web`

Builds the Flask image using the Dockerfile in `app/` and publishes host port `5000`.

#### `env_file`

Loads variables from `.env` into the service's container environment.

#### `environment`

Sets the database and Redis hostnames used by Flask.

```yaml
DB_HOST: db
REDIS_HOST: redis
```

Docker Compose provides service-name DNS on its project network. Flask can therefore reach the database at `db:5432` and Redis at `redis:6379`.

Do not use `localhost` for these services from inside the Flask container. Inside a container, `localhost` refers to that same container.

#### `depends_on`

```yaml
depends_on:
  db:
    condition: service_healthy
  redis:
    condition: service_healthy
```

This tells Compose to wait for the configured health checks to pass before starting the dependent web service.

It helps with startup ordering but does not guarantee that dependencies will remain healthy forever. Applications should still handle connection failures.

#### PostgreSQL health check

```yaml
test:
  - CMD-SHELL
  - pg_isready -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"
```

`pg_isready` checks whether PostgreSQL is accepting connections. The doubled dollar signs allow the variables to be expanded inside the container rather than prematurely by Compose.

#### Redis health check

```yaml
test: ["CMD", "redis-cli", "ping"]
```

This runs the Redis CLI ping command. A responding Redis server normally returns `PONG`.

#### `restart: unless-stopped`

Configures Docker to restart the service after many exits unless the container has been explicitly stopped. Verify the actual behavior during failure tests rather than assuming every manual stop or kill will trigger a restart.

#### Named volume

```yaml
volumes:
  pgdata:
```

The volume stores PostgreSQL data outside the container's writable layer.

The mapping:

```yaml
- pgdata:/var/lib/postgresql/data
```

mounts that storage at PostgreSQL's data directory.

---

## 9. Step 6 — Validate the Configuration

Navigate to the project root:

```bash
cd ~/DevOps-Winter-Arc/Week2-Docker/Task5-Compose-Full-Stack
```

Validate the Compose file:

```bash
docker compose config
```

Check the installed tools:

```bash
docker --version
docker compose version
```

`docker compose config` renders the resolved configuration and helps catch YAML or configuration errors. Be careful when sharing its output if it contains sensitive values.

---

## 10. Step 7 — Start the Full Stack With One Command

Run:

```bash
docker compose up -d --build
```

This command:

1. Builds the Flask image.
2. Pulls the PostgreSQL and Redis images if required.
3. Creates the project network and named volume.
4. Creates the containers.
5. Starts the services in the background.

The `-d` flag means detached mode, so the terminal returns to the prompt.

The `--build` flag requests image building before startup.

Check service status:

```bash
docker compose ps
```

Wait for PostgreSQL and Redis to become healthy. Flask may take additional time while it retries its database connection.

Check logs:

```bash
docker compose logs --tail=50
```

Check only Flask:

```bash
docker compose logs --tail=50 web
```

Follow Flask logs live:

```bash
docker compose logs -f web
```

Press `Ctrl+C` to stop following the logs. This does not normally stop the containers.

---

## 11. Step 8 — Test the Application

### Test the health endpoint

```bash
curl http://localhost:5000/health
```

Expected response:

```text
ok
```

### Test the main endpoint

```bash
curl http://localhost:5000/
```

Example:

```text
Redis hits: 1 | PostgreSQL visits: 1
```

Make several requests:

```bash
curl http://localhost:5000/
curl http://localhost:5000/
curl http://localhost:5000/
```

The counts depend on earlier requests and whether existing data is present.

### Understand the two counters

**Redis hits**

Redis stores the in-memory counter. Because this Compose file does not configure a persistent Redis volume, the counter may reset when the Redis container is recreated.

**PostgreSQL visits**

Each successful request inserts a database row. The count is stored in PostgreSQL's data directory, which is mounted to the named volume.

---

## 12. Step 9 — Verify PostgreSQL Persistence

First, generate a few visits:

```bash
curl http://localhost:5000/
curl http://localhost:5000/
```

Record the PostgreSQL count.

Stop and remove the containers:

```bash
docker compose down
```

Start the application again:

```bash
docker compose up -d
```

Wait for the database and Redis health checks to pass. Then run:

```bash
curl http://localhost:5000/
```

### Expected result

The PostgreSQL visit count should continue from its previous value because the `pgdata` named volume survives ordinary `docker compose down`.

The Redis counter may reset because Redis has no persistent volume configured.

### Why is the named volume important?

Containers are replaceable. Data stored only in a container's writable layer is not a reliable persistence strategy.

A named volume keeps database files separate from the database container's lifecycle.

**Important:** Do not run `docker compose down -v` during this test. The `-v` option removes Compose-managed named volumes and can delete the database data.

---

## 13. Step 10 — Test Container Recovery

Check running services:

```bash
docker compose ps
```

Get the web container ID:

```bash
docker compose ps -q web
```

For the failure experiment, kill the web container:

```bash
docker kill "$(docker compose ps -q web)"
```

Inspect all containers, including stopped ones:

```bash
docker compose ps -a
```

Inspect logs:

```bash
docker compose logs --tail=50 web
```

### Interpret the result

Exit code `137` commonly indicates termination by `SIGKILL`, which is consistent with the `docker kill` command.

The restart policy is intended to handle many unexpected exits, but a manually issued kill can leave the container stopped. A manual kill is therefore not sufficient by itself to prove the restart policy is broken or working.

Restore the service:

```bash
docker compose up -d web
```

Verify it:

```bash
docker compose ps
curl http://localhost:5000/health
```

Expected:

```text
ok
```

Record the forced-kill result separately from the recovery result.

---

## 14. Step 11 — Inspect Docker Resources

### List running containers

```bash
docker compose ps
```

### List all project containers

```bash
docker compose ps -a
```

### List images

```bash
docker images
```

### List Docker volumes

```bash
docker volume ls
```

### Inspect networks

```bash
docker network ls
```

### Inspect the Compose volume

Compose typically prefixes the volume name with the project name. Find its exact name using `docker volume ls`, then run:

```bash
docker volume inspect <actual-volume-name>
```

Replace `<actual-volume-name>` with the real volume name. Do not type the angle brackets.

---

## 15. Step 12 — Git and Secret Protection

Check the repository status:

```bash
git status --short
```

Check whether `.env` is ignored:

```bash
git check-ignore -v .env
```

If this directory is inside your Git repository, stage the project files:

```bash
git add app compose.yaml .env.example .gitignore README.md
```

Check staged changes:

```bash
git status --short
```

Commit:

```bash
git commit -m "Complete Docker Compose Task 5"
```

Do not stage `.env`.

If a secret was already committed, adding it to `.gitignore` is not enough to remove it from Git history. Remove it from tracking and rotate the exposed credential.

---

## 16. Troubleshooting Guide

### Problem 1: Port 5000 is already allocated

Inspect running containers:

```bash
docker ps
```

If host port `5000` is occupied, change the web port mapping in `compose.yaml`:

```yaml
ports:
  - "5001:5000"
```

Apply the change:

```bash
docker compose up -d --build
```

Test:

```bash
curl http://localhost:5001/health
```

### Problem 2: Flask cannot connect to PostgreSQL

Check status and logs:

```bash
docker compose ps
docker compose logs --tail=100 db
docker compose logs --tail=100 web
```

Verify the Flask environment uses `DB_HOST=db` and that the database credentials match the initialized database.

### Problem 3: Flask cannot connect to Redis

Check Redis logs:

```bash
docker compose logs --tail=100 redis
```

Verify that Flask uses:

```text
REDIS_HOST=redis
```

Remember that `localhost` inside the web container means the web container itself.

### Problem 4: The web container is stopped

Use:

```bash
docker compose ps -a
docker compose logs --tail=100 web
```

Restart or reconcile the service:

```bash
docker compose up -d web
```

### Problem 5: PostgreSQL data appears missing

Check the volume list:

```bash
docker volume ls
```

Verify that the Compose file still maps `pgdata` to `/var/lib/postgresql/data`.

Check whether `docker compose down -v` was run. That command can remove the database volume.

Do not delete volumes as an initial troubleshooting step.

---

## 17. Docker Compose Command Reference

| Command | Purpose |
|---|---|
| `docker compose config` | Validate and render Compose configuration |
| `docker compose up -d --build` | Build and start the full stack |
| `docker compose up -d` | Create/start services without explicitly requesting a build |
| `docker compose ps` | Show running project containers |
| `docker compose ps -a` | Show running and stopped project containers |
| `docker compose logs` | View service logs |
| `docker compose logs -f web` | Follow Flask logs |
| `docker compose restart web` | Restart the existing web container |
| `docker compose down` | Remove project containers and network |
| `docker compose down -v` | Also remove Compose-managed named volumes |
| `docker volume ls` | List Docker volumes |
| `docker network ls` | List Docker networks |
| `docker images` | List local images |

### `restart` versus `up`

`docker compose restart web` restarts the existing container; it does not rebuild the image or apply changed Compose configuration.

`docker compose up -d --build web` builds the image when requested and reconciles the service configuration before starting it.

---

## 18. Interview Questions and Answers

### Q1. What is Docker Compose?

Docker Compose is a tool for defining and managing multi-container applications through a YAML configuration file.

### Q2. Why use Docker Compose instead of running containers individually?

Compose keeps service definitions, networking, environment variables, volumes, and health checks in one place. It simplifies repeatable application startup and management.

### Q3. What does `docker compose up -d --build` do?

It builds the required images, creates or updates the services, and starts the containers in detached mode.

### Q4. What is the role of `compose.yaml`?

It defines the services and their configuration, including images or build instructions, ports, environment variables, dependencies, health checks, restart policies, and volumes.

### Q5. What is the difference between a Docker image and a container?

An image is a template containing the application and its dependencies. A container is a running or stopped instance created from an image.

### Q6. How do the Flask, PostgreSQL, and Redis containers communicate?

They communicate over the Compose-created network. Docker's service-name DNS lets Flask connect to `db` and `redis` without fixed container IP addresses.

### Q7. Why is `DB_HOST=db` used instead of `localhost`?

Inside the Flask container, `localhost` refers to that same container. `db` resolves to the PostgreSQL service through Docker DNS.

### Q8. What does `depends_on` do?

It defines startup dependencies. With `condition: service_healthy`, Compose waits for the configured dependency health checks before starting the dependent service.

### Q9. Does `depends_on` guarantee that PostgreSQL will never fail after Flask starts?

No. It helps with startup ordering and readiness. The application must still handle later database failures and reconnections.

### Q10. What is a health check?

A health check runs a command to assess whether a service is responding as expected. Health status is separate from whether the container process is running.

### Q11. What is the difference between a running container and a healthy container?

Running means the container's main process is running. Healthy means the configured health check is passing. A container can be running but unhealthy.

### Q12. What is a named volume?

A Docker-managed storage resource that can exist independently of a container and preserve data across container replacement.

### Q13. Why does PostgreSQL data survive `docker compose down`?

Because PostgreSQL's data directory is stored in the named volume `pgdata`, and ordinary `down` does not remove that volume.

### Q14. What is the difference between `docker compose down` and `docker compose down -v`?

`down` removes project containers and the network. `down -v` also removes Compose-managed named volumes, potentially deleting persistent database data.

### Q15. Why might Redis's counter reset after restarting the stack?

This configuration does not mount a persistent volume for Redis. Its in-memory counter can be lost when the Redis container is recreated.

### Q16. What does `restart: unless-stopped` mean?

Docker attempts to restart the container after many exits unless it has been explicitly stopped. The exact behavior should be verified during testing.

### Q17. What does `5000:5000` mean?

The first port is the host port; the second is the container port. Requests to host port `5000` are forwarded to port `5000` inside the web container.

### Q18. What is the purpose of `.env`?

It supplies local configuration values to containers without hardcoding them into application source code.

### Q19. Why commit `.env.example` but ignore `.env`?

The example file documents required variables without revealing the real local credentials. The `.env` file may contain secrets and should not be committed.

### Q20. Does `.gitignore` protect secrets that have already been committed?

No. Previously committed secrets may remain in Git history. They should be removed from tracking and rotated.

### Q21. Why run the Flask application as a non-root user?

It follows the principle of least privilege and reduces the permissions available to the application.

### Q22. What does exit code 137 commonly indicate?

It commonly indicates termination by `SIGKILL`. In this lab, it is consistent with the deliberate `docker kill` experiment.

### Q23. How would you troubleshoot a web container that is not responding?

Check `docker compose ps -a`, inspect web logs, verify the port mapping, check dependency health, and test the health endpoint after fixing the problem.

### Q24. What is the difference between `docker compose restart web` and `docker compose up -d --build web`?

The first restarts the existing container. The second can rebuild the image and reconcile the service configuration before starting it.

---

## 19. Evidence and Completion Checklist

- [ ] Project files created in the correct directory.
- [ ] `docker compose config` succeeds.
- [ ] `docker compose up -d --build` starts the full stack.
- [ ] `web`, `db`, and `redis` are running.
- [ ] PostgreSQL and Redis health checks pass.
- [ ] `/health` returns `ok`.
- [ ] `/` returns Redis hits and PostgreSQL visits.
- [ ] Multiple requests increase the counters.
- [ ] PostgreSQL data persists after `down` and `up`.
- [ ] Container failure and recovery behavior is documented.
- [ ] `.env` is ignored by Git.
- [ ] `.env.example` is included.
- [ ] README and terminal evidence are ready for submission.

---

## 20. Cleanup

Stop and remove the project containers:

```bash
docker compose down
```

This preserves the named PostgreSQL volume.

Only if you intentionally want to delete the database data should you run:

```bash
docker compose down -v
```

**Warning:** The second command deletes Compose-managed named volumes and can permanently remove the lab's PostgreSQL data.

---

## 21. Final Summary

In this task, I used Docker Compose to define a Flask application, PostgreSQL database, and Redis service in one configuration file. I configured service discovery, environment variables, health checks, startup dependencies, restart policies, and persistent storage.

I tested the HTTP endpoints, verified PostgreSQL persistence across container replacement, investigated container failure behavior, and checked that local credentials were excluded from Git.

**Key takeaway:** Docker Compose makes it possible to define, launch, inspect, and manage an entire multi-container application using a consistent configuration and a single startup command.
