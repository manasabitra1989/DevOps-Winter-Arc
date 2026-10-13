# Day 12 — Docker Compose: Multi-Container Application

## 1. Objective

Build and run a multi-container application using Docker Compose. The application consists of:

- **Flask:** Web application exposed on port `5000`
- **PostgreSQL:** Database that stores persistent visit counts
- **Redis:** In-memory store that tracks request hits
- **Docker Compose:** Defines and manages the services in one YAML file

### Learning goals

- Run multiple containers using one Compose file.
- Configure service-to-service communication.
- Use environment variables and `.env` files.
- Add health checks and startup dependencies.
- Persist PostgreSQL data with a named volume.
- Test container restart behavior.
- Protect environment secrets from Git.
- Inspect logs and troubleshoot failed services.

---

## 2. Architecture

```text
                 Browser / curl
                       |
                       | http://localhost:5000
                       v
              +------------------+
              |   Flask: web     |
              |   Port 5000      |
              +------------------+
                    |       |
          Redis hits |       | PostgreSQL visits
                    v       v
             +---------+  +---------+
             |  redis  |  |   db    |
             | 6379    |  | 5432    |
             +---------+  +---------+
                              |
                              v
                        +-----------+
                        | pgdata    |
                        | named     |
                        | volume    |
                        +-----------+
```

All three services communicate through the private network that Docker Compose creates automatically.

Only the web service publishes a port to the host. PostgreSQL and Redis are accessed by other containers through their service names, `db` and `redis`.

## 3. Project structure

```text
day12-Docker-Compose/
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

### What each file does

| File | Purpose |
|---|---|
| `app.py` | Flask routes and database/Redis logic |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Builds the web application image |
| `compose.yaml` | Defines all three services, health checks, networking, and storage |
| `.env` | Local configuration and database password |
| `.env.example` | Safe template for required environment variables |
| `.gitignore` | Prevents secrets and temporary files from being committed |
| `README.md` | Project documentation |

---

## 4. Step 1 — Navigate to the project

```bash
cd ~/DevOps-Winter-Arc/Week2-Docker/day12-Docker-Compose
```

Confirm the files exist:

```bash
ls -la
ls -la app
```

- `cd` changes the current directory.
- `ls -la` lists files, including hidden files such as `.env` and `.gitignore`.

## 5. Step 2 — Understand the Flask application

The application uses Flask to provide two endpoints.

### `GET /`

Each request:

1. Increments a counter in Redis.
2. Creates the PostgreSQL `visits` table if it does not exist.
3. Inserts a new visit record into PostgreSQL.
4. Returns both counts.

Example response:

```text
Redis hits: 1 | Postgres visits: 1
```

Repeated requests should increase both counts.

### `GET /health`

Returns:

```text
ok
```

This endpoint provides a simple check that the Flask application is responding.

### Dependencies

`app/requirements.txt`:

```text
flask==3.0.3
redis==5.0.8
psycopg2-binary==2.9.9
```

These packages provide the web framework, Redis client, and PostgreSQL client.

---

## 6. Step 3 — Understand the web Dockerfile

`app/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -r appuser
USER appuser

EXPOSE 5000

CMD ["python", "app.py"]
```

### Explanation

- `FROM python:3.12-slim`: starts from a smaller Python base image.
- `WORKDIR /app`: sets the working directory inside the image.
- `COPY requirements.txt .`: copies the dependency list first.
- `RUN pip install ...`: installs Python packages during the image build.
- `COPY . .`: copies the application files.
- `RUN useradd -r appuser`: creates a non-root user.
- `USER appuser`: runs the application without root privileges.
- `EXPOSE 5000`: documents the port used by Flask; it does not publish that port by itself.
- `CMD [...]`: defines the command that starts the application.

Copying the requirements file before the source code helps Docker reuse the dependency-installation layer when only application code changes.

---

## 7. Step 4 — Configure environment variables

### `.env`

```dotenv
POSTGRES_DB=visits
POSTGRES_USER=appuser
POSTGRES_PASSWORD=change-me-please
```

This file supplies configuration to the containers through Compose.

**Security:** `change-me-please` is a lab-only password. Do not use it in production.

### `.env.example`

```dotenv
POSTGRES_DB=visits
POSTGRES_USER=appuser
POSTGRES_PASSWORD=replace-with-a-local-password
```

This is a template that teammates can copy to create their own `.env` file.

### `.gitignore`

```gitignore
.env
__pycache__/
*.pyc
.venv/
```

The `.env` entry helps prevent accidentally committing the local password.

Verify the files:

```bash
cat .env.example
cat .gitignore
```

Avoid printing or sharing the real `.env` contents in public logs, screenshots, or repositories.

---

## 8. Step 5 — Understand `compose.yaml`

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
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
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

### Important Compose concepts

**`services`**

Defines the containers Compose manages: `web`, `db`, and `redis`.

**`build: ./app`**

Builds the web image using the Dockerfile in the `app` directory.

**`ports: "5000:5000"`**

Maps host port `5000` to container port `5000`. This makes Flask accessible at `http://localhost:5000`.

**`env_file: .env`**

Loads variables from `.env` into the container environment.

**`DB_HOST: db` and `REDIS_HOST: redis`**

Use Compose service names as hostnames. Containers on the Compose network can resolve these names through Docker's DNS.

Inside the web container, `localhost` refers to the web container itself—not PostgreSQL or Redis.

**`depends_on` with `service_healthy`**

Tells Compose to wait for the dependencies' health checks to pass before starting the web service.

**`healthcheck`**

- PostgreSQL uses `pg_isready` to check database readiness.
- Redis uses `redis-cli ping` to check whether Redis responds.

A healthy database means the readiness check succeeded; it does not guarantee that every application query will succeed.

**`restart: unless-stopped`**

Allows Docker to restart a container after many unexpected exits. Manual stopping and killing need to be interpreted carefully when testing this policy.

**`volumes: pgdata`**

Creates a named volume to store PostgreSQL data outside the database container's writable layer.

**`$${POSTGRES_USER}`**

The doubled dollar sign makes Compose pass the variable reference into the container command rather than substituting it prematurely.

---

## 9. Step 6 — Validate the Compose configuration

```bash
docker compose config
```

This renders the resolved Compose configuration and helps detect YAML or configuration problems.

Do not publish the output if it contains sensitive values.

Check that Docker is available:

```bash
docker --version
docker compose version
```

## 10. Step 7 — Build and start the application

```bash
docker compose up -d --build
```

Explanation:

- `up`: creates and starts the services.
- `-d`: runs them in the background.
- `--build`: builds or rebuilds images before starting.

Check the services:

```bash
docker compose ps
```

Expected: `web`, `db`, and `redis` should be running. PostgreSQL and Redis should become healthy. Allow a little time for health checks to run.

View startup logs:

```bash
docker compose logs --tail=50
```

View only web logs:

```bash
docker compose logs --tail=50 web
```

Follow logs live:

```bash
docker compose logs -f web
```

Press `Ctrl+C` to stop following logs. This does not normally stop the container.

## 11. Step 8 — Test the application

### Test the health endpoint

```bash
curl http://localhost:5000/health
```

Expected:

```text
ok
```

### Test the main endpoint

```bash
curl http://localhost:5000/
```

Run it several times:

```bash
curl http://localhost:5000/
curl http://localhost:5000/
curl http://localhost:5000/
```

Both counts should increase as requests are processed.

### What the counts mean

- **Redis hits:** an in-memory counter. In this configuration, it can reset when the Redis container is recreated because Redis has no persistent volume.
- **Postgres visits:** a database count stored in PostgreSQL. The named volume is intended to preserve these records across container replacement.

---

## 12. Step 9 — Verify PostgreSQL persistence

First, record the current visit count:

```bash
curl http://localhost:5000/
```

Stop and remove the Compose containers:

```bash
docker compose down
```

This removes the containers and Compose network, but normally preserves the named volume `pgdata`.

Start the application again:

```bash
docker compose up -d --build
```

Check service health:

```bash
docker compose ps
```

Wait for the services to become healthy, then request the application:

```bash
curl http://localhost:5000/
```

The PostgreSQL visit count should continue from its previous value. The Redis hit counter may restart from its initial value.

### Why does PostgreSQL data survive?

The database files are stored in the named volume mounted at:

```text
/var/lib/postgresql/data
```

Removing a container does not automatically delete this named volume.

**Important:** Do not run `docker compose down -v` during this test. The `-v` option removes Compose-managed named volumes and can permanently delete the lab database data.

---

## 13. Step 10 — Test container recovery

The assignment asks you to test what happens when the web container fails.

Check the current service:

```bash
docker compose ps
```

Get the web container ID:

```bash
docker compose ps -q web
```

Kill the web container:

```bash
docker kill "$(docker compose ps -q web)"
```

Check all containers, including stopped ones:

```bash
docker compose ps -a
```

Check its logs:

```bash
docker compose logs --tail=50 web
```

### Interpreting the result

In this lab, `docker kill` forcibly terminates the container's main process. Exit code `137` commonly indicates termination by `SIGKILL`, which is expected for this command.

The `restart: unless-stopped` policy is intended to restart a container after many unexpected exits. However, a manually issued `docker kill` can result in a stopped container rather than the automatic recovery you expected. Do not assume the policy worked just because it is configured—verify the actual state.

To restore the service:

```bash
docker compose up -d web
```

Then check:

```bash
docker compose ps
curl http://localhost:5000/health
```

Expected health response:

```text
ok
```

For your evidence, record both the result of the forced-kill test and the subsequent recovery command. They are two separate observations.

---

## 14. Step 11 — Inspect containers, images, and volumes

### List running containers

```bash
docker compose ps
```

### List all containers, including stopped ones

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

### Inspect the PostgreSQL volume

```bash
docker volume inspect day12-docker-compose_pgdata
```

Compose-generated volume names are typically prefixed by the project name. If the volume name differs, use the name shown by `docker volume ls`.

### Inspect the Compose network

```bash
docker network ls
```

Compose creates a project network so that the web service can resolve `db` and `redis` by service name.

---

## 15. Step 12 — Git and secret protection

Check the repository status:

```bash
git status --short
```

Confirm that `.env` is ignored:

```bash
git check-ignore -v .env
```

If the project is already inside a Git repository, stage the safe project files:

```bash
git add app compose.yaml .env.example .gitignore README.md
```

Check the staged files:

```bash
git status --short
```

Commit:

```bash
git commit -m "Complete Day 12 Docker Compose lab"
```

Do not add `.env` to Git. If a secret was committed previously, adding `.env` to `.gitignore` alone does not remove it from Git history. Remove it from tracking and rotate the exposed secret.

---

## 16. Common errors and fixes

### Error: `curl: (7) Failed to connect to localhost port 5000`

Check:

```bash
docker compose ps -a
docker compose logs --tail=100 web
```

Possible causes:

- The web container is stopped or restarting.
- The web application failed to start.
- Port `5000` is already being used by another process.
- The web container is still starting.

Start the service:

```bash
docker compose up -d web
```

### Error: port is already allocated

Another application or container may already be using host port `5000`.

Check running containers:

```bash
docker ps
```

If you need a different host port, change the Compose mapping to:

```yaml
ports:
  - "5001:5000"
```

Then recreate the service:

```bash
docker compose up -d --build
```

Open the app at `http://localhost:5001`.

### Error: web cannot connect to PostgreSQL

Check database health and logs:

```bash
docker compose ps
docker compose logs --tail=100 db
docker compose logs --tail=100 web
```

Verify the web environment uses:

```text
DB_HOST=db
```

Do not use `localhost` for the database host inside the web container.

### Error: web cannot connect to Redis

Verify Redis is running and healthy:

```bash
docker compose ps
docker compose logs --tail=100 redis
```

The web service should use:

```text
REDIS_HOST=redis
```

### Error: PostgreSQL credentials appear incorrect

Check the local `.env` values and the database logs.

PostgreSQL initialization variables such as `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` are applied when the data directory is initialized. Changing `.env` later does not automatically change credentials in an already-initialized database volume.

Avoid deleting the volume as a first troubleshooting step, because that can destroy persistent data.

### Error: a stopped container is missing from `docker compose ps`

Use:

```bash
docker compose ps -a
```

The default `docker compose ps` focuses on running containers; `-a` also shows stopped containers.

---

## 17. Important Docker Compose commands

| Command | Purpose |
|---|---|
| `docker compose config` | Validate and render Compose configuration |
| `docker compose up -d --build` | Build and start services |
| `docker compose ps` | Show running services |
| `docker compose ps -a` | Include stopped containers |
| `docker compose logs` | Display service logs |
| `docker compose logs -f web` | Follow web logs |
| `docker compose restart web` | Restart the existing web service container |
| `docker compose up -d web` | Ensure the web service is created and started |
| `docker compose down` | Remove containers and Compose network |
| `docker compose down -v` | Also remove Compose-managed named volumes; destructive to stored lab data |

### `restart` versus `up -d`

- `docker compose restart web` restarts the existing container. It does not rebuild the image or apply changed Compose configuration.
- `docker compose up -d --build web` can rebuild the image and reconcile the service configuration before starting it.

---

## 18. Interview questions and answers

### Q1. What is Docker Compose?

Docker Compose is a tool for defining and managing multi-container applications using a YAML configuration file.

### Q2. Why use Compose instead of running every container manually?

Compose keeps service configuration in one file and makes startup, networking, environment variables, volumes, and health checks easier to manage consistently.

### Q3. How do the web, PostgreSQL, and Redis containers communicate?

They share the Compose-created network. The web service connects to the hostnames `db` and `redis`, which Docker resolves to the appropriate containers.

### Q4. Why should the application use `DB_HOST=db` instead of `localhost`?

Inside a container, `localhost` points to that same container. `db` resolves to the PostgreSQL service on the shared Docker network.

### Q5. What is a named volume?

A named volume is Docker-managed storage that exists separately from a container's writable layer. It is useful for data that must survive container replacement.

### Q6. Why did PostgreSQL data survive `docker compose down`?

The database files were stored in the named volume `pgdata`. The ordinary `down` command removes containers and the network but preserves that volume.

### Q7. What is the difference between `docker compose down` and `docker compose down -v`?

`down` removes the Compose containers and network. `down -v` also removes Compose-managed named volumes, potentially deleting database data.

### Q8. What does `depends_on` do?

It defines startup dependencies. With `condition: service_healthy`, Compose waits for the specified dependency's health check to pass before starting the dependent service.

### Q9. Does `depends_on` guarantee that the application will never lose its database connection?

No. It helps with startup ordering and readiness. Applications should still handle connection failures and service restarts.

### Q10. What is a Docker health check?

A health check runs a command to assess whether a container's service is responding as expected. Its status is separate from whether the container process is running.

### Q11. What does `restart: unless-stopped` mean?

Docker attempts to restart the container after many exits unless it has been explicitly stopped. Always inspect the actual container state when testing failure recovery.

### Q12. Why might Redis data disappear after recreation?

This Compose configuration does not mount a persistent volume for Redis. Its in-memory data can be lost when the container is recreated.

### Q13. What is the purpose of `.env.example`?

It documents the required configuration variables without requiring the real local secrets to be committed.

### Q14. Does `.gitignore` protect secrets that were already committed?

No. It prevents matching untracked files from being added normally. Previously committed secrets need to be removed from tracking and rotated; they may remain in Git history.

### Q15. What does `5000:5000` mean?

The first port is the host port; the second is the container port. Requests to host port `5000` are forwarded to container port `5000`.

### Q16. Why use a non-root user in the web image?

It follows the principle of least privilege and reduces the potential impact of a compromised application.

### Q17. What does exit code 137 indicate?

It commonly indicates that the process was terminated by `SIGKILL`. In this exercise, it is consistent with the forced `docker kill` command.

### Q18. How would you troubleshoot a web service that is not responding?

Check `docker compose ps -a`, inspect web logs, verify the port mapping, confirm database and Redis health, and test the health endpoint after correcting the issue.

---

## 19. Evidence checklist

Capture screenshots or save terminal output demonstrating:

- [ ] `docker compose config` succeeds.
- [ ] `docker compose ps` shows all three services running.
- [ ] PostgreSQL and Redis reach healthy status.
- [ ] `/health` returns `ok`.
- [ ] `/` returns Redis hits and PostgreSQL visits.
- [ ] Multiple requests increment the counters.
- [ ] PostgreSQL visit count persists after `docker compose down` and `docker compose up -d`.
- [ ] Web-container kill behavior is recorded.
- [ ] Web service is restored and `/health` works again.
- [ ] `.env` is ignored by Git.
- [ ] `.env.example` is present in the project.

## 20. Cleanup

When you have finished collecting evidence, stop and remove the containers:

```bash
docker compose down
```

This preserves the named PostgreSQL volume.

Only if you intentionally want to delete the database data as well, use:

```bash
docker compose down -v
```

**Warning:** The second command is destructive to the Compose-managed database volume. Do not use it before verifying persistence and collecting evidence.

---

## 21. Final summary

In this lab, I used Docker Compose to define a Flask web application, PostgreSQL database, and Redis service in one YAML file. I configured service discovery, environment variables, health checks, startup dependencies, a named PostgreSQL volume, and a restart policy. I tested the endpoints, verified database persistence across container replacement, inspected container failure behavior, and checked that local environment secrets are excluded from Git.

**Key takeaway:** Containers can be recreated, but persistent application data should live in appropriately managed storage outside the container's writable layer.
