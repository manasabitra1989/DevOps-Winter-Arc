# Docker Week 2 — Task 4: Storage & Networking

## 1. Objective

Learn how Docker containers store data, communicate with other containers, and expose services to the host machine.

### Learning outcomes

By completing this lab, you will learn to:

- Create and inspect Docker volumes.
- Understand named volumes versus bind mounts.
- Create a user-defined bridge network.
- Run PostgreSQL with persistent storage.
- Connect a Node.js application to PostgreSQL in a separate container.
- Use Docker DNS to resolve a container by name.
- Publish container ports to the host.
- Troubleshoot network connectivity and port conflicts.
- Verify that database data survives container removal and recreation.

## 2. Architecture

```text
                    Browser / Host
                           |
                     localhost:3000
                           |
                    Port mapping
                     3000 -> 3000
                           |
                    +-------------+
                    | Node.js App |
                    | task4-app   |
                    +-------------+
                           |
                  Custom bridge network
                       task4-net
                           |
                    DNS hostname: db
                           |
                    +-------------+
                    | PostgreSQL  |
                    | task4-db    |
                    +-------------+
                           |
                  /var/lib/postgresql/data
                           |
                    +-------------+
                    | Named Volume|
                    | task4-pgdata|
                    +-------------+
```

### How communication works

1. The browser accesses the application through `localhost:3000`.
2. Docker forwards host port `3000` to port `3000` in the application container.
3. The application connects to PostgreSQL using hostname `db` and port `5432`.
4. Docker DNS resolves `db` to the PostgreSQL container's network address.
5. PostgreSQL stores database files in the `task4-pgdata` volume.

**Important:** PostgreSQL does not need a published host port for the application to reach it. Both containers communicate through `task4-net`.

## 3. Prerequisites

Verify that Docker is working:

```bash
docker --version
docker ps
docker network ls
docker volume ls
```

This lab uses Ubuntu on WSL2 with Docker Desktop or a Linux installation with Docker Engine.

Create the project directory:

```bash
mkdir -p ~/DevOps-Winter-Arc/Week2-Docker/Task4-Storage-Networking
cd ~/DevOps-Winter-Arc/Week2-Docker/Task4-Storage-Networking
```

## 4. Create a custom network and named volume

```bash
docker network create task4-net
docker volume create task4-pgdata
```

Inspect them:

```bash
docker network inspect task4-net
docker volume inspect task4-pgdata
```

### Explanation

- `docker network create task4-net` creates a user-defined bridge network.
- `docker volume create task4-pgdata` creates a Docker-managed volume.
- `docker network inspect` displays the network configuration and attached containers.
- `docker volume inspect` displays volume details, including its Docker-managed mount location.

A user-defined bridge network provides DNS-based service discovery between attached containers.

A named volume stores data independently of a container's lifecycle.

## 5. Run PostgreSQL with persistent storage

```bash
docker run -d \
  --name task4-db \
  --network task4-net \
  --network-alias db \
  -e POSTGRES_USER=appuser \
  -e POSTGRES_PASSWORD=devpass123 \
  -e POSTGRES_DB=appdb \
  -v task4-pgdata:/var/lib/postgresql/data \
  postgres:16-alpine
```

Check the container:

```bash
docker ps
docker logs task4-db
docker exec task4-db pg_isready -U appuser -d appdb
```

Wait until PostgreSQL reports that it is accepting connections.

### Explanation of important options

| Option | Explanation |
|---|---|
| `-d` | Runs the container in the background. |
| `--name task4-db` | Assigns a convenient container name. |
| `--network task4-net` | Connects the container to the custom network. |
| `--network-alias db` | Makes `db` an additional DNS name on that network. |
| `-e POSTGRES_USER=appuser` | Sets the initial database user. |
| `-e POSTGRES_PASSWORD=devpass123` | Sets the initial user's password. |
| `-e POSTGRES_DB=appdb` | Requests creation of the initial database. |
| `-v task4-pgdata:/var/lib/postgresql/data` | Mounts persistent storage at PostgreSQL's data directory. |
| `postgres:16-alpine` | Selects the PostgreSQL 16 image variant based on Alpine Linux. |

**Security note:** The credentials are for local practice only. Environment variables are convenient for a lab, but they are not a production secrets-management solution.

**Initialization note:** The PostgreSQL image's initialization variables apply when the data directory is first initialized. Changing these variables later does not automatically change credentials or recreate an existing database in a populated volume.

### Why is there no `-p 5432:5432`?

The app and database share `task4-net`. The app can connect directly to `db:5432` through the Docker network.

Publishing port `5432` would make the database port reachable through the host, which is unnecessary for this lab.

## 6. Create test data in PostgreSQL

Create a table:

```bash
docker exec task4-db \
  psql -U appuser -d appdb \
  -c "CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        message TEXT NOT NULL
      );"
```

Insert a row:

```bash
docker exec task4-db \
  psql -U appuser -d appdb \
  -c "INSERT INTO messages(message)
      VALUES ('Docker storage works!');"
```

Read the data:

```bash
docker exec task4-db \
  psql -U appuser -d appdb \
  -c "SELECT * FROM messages;"
```

### What does `docker exec` do?

`docker exec` runs a command inside an already-running container.

Here, `psql` is PostgreSQL's command-line client. The `-U` option specifies the database user, and `-d` specifies the database.

## 7. Build the Node.js application

Create the application directory:

```bash
mkdir -p app
```

Create `app/package.json`:

```json
{
  "name": "task4-storage-networking",
  "version": "1.0.0",
  "private": true,
  "main": "app.js",
  "scripts": {
    "start": "node app.js"
  },
  "dependencies": {
    "pg": "^8.13.0"
  }
}
```

Create `app/app.js`:

```javascript
const http = require("http");
const { Client } = require("pg");

const port = 3000;

async function queryDatabase() {
  const client = new Client({
    host: process.env.DB_HOST || "db",
    port: Number(process.env.DB_PORT || 5432),
    user: process.env.DB_USER || "appuser",
    password: process.env.DB_PASSWORD || "devpass123",
    database: process.env.DB_NAME || "appdb",
    connectionTimeoutMillis: 3000
  });

  await client.connect();

  try {
    const result = await client.query(
      "SELECT id, message FROM messages ORDER BY id DESC LIMIT 5"
    );
    return result.rows;
  } finally {
    await client.end();
  }
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.url === "/health") {
      await queryDatabase();

      res.writeHead(200, {
        "Content-Type": "application/json"
      });

      res.end(JSON.stringify({
        status: "ok",
        database: "connected"
      }));

      return;
    }

    if (req.url !== "/") {
      res.writeHead(404);
      res.end("Not found");
      return;
    }

    const rows = await queryDatabase();

    const items = rows.map(row => {
      const safeMessage = String(row.message)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");

      return `<li>${row.id}: ${safeMessage}</li>`;
    }).join("");

    res.writeHead(200, {
      "Content-Type": "text/html; charset=utf-8"
    });

    res.end(`
      <h1>Docker Task 4</h1>
      <p>Connected to PostgreSQL using Docker DNS hostname: db</p>
      <h2>Messages</h2>
      <ul>${items}</ul>
    `);
  } catch (error) {
    console.error(error);

    res.writeHead(503, {
      "Content-Type": "application/json"
    });

    res.end(JSON.stringify({
      error: "Database unavailable"
    }));
  }
});

server.listen(port, "0.0.0.0", () => {
  console.log(`App listening on port ${port}`);
});
```

Create `app/Dockerfile`:

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package.json ./
RUN npm install --omit=dev

COPY app.js ./

EXPOSE 3000

CMD ["npm", "start"]
```

Build the image:

```bash
docker build -t task4-app:v1 ./app
```

### Dockerfile concepts

- `FROM` selects the base image.
- `WORKDIR` sets the working directory for subsequent instructions.
- `COPY` copies files from the build context into the image.
- `RUN` executes a command during image construction.
- `EXPOSE` documents the port the application is intended to listen on.
- `CMD` defines the default command executed when a container starts.

`EXPOSE 3000` does not publish the port to the host. Host access is configured with `-p` when the container is run.

## 8. Run the app and connect it to PostgreSQL

```bash
docker run -d \
  --name task4-app \
  --network task4-net \
  -p 3000:3000 \
  -e DB_HOST=db \
  -e DB_PORT=5432 \
  -e DB_USER=appuser \
  -e DB_PASSWORD=devpass123 \
  -e DB_NAME=appdb \
  task4-app:v1
```

Inspect the containers and logs:

```bash
docker ps
docker logs task4-app
docker logs task4-db
```

Test the application:

```bash
curl http://localhost:3000/
curl http://localhost:3000/health
```

Expected health response:

```json
{"status":"ok","database":"connected"}
```

Open `http://localhost:3000/` in your browser. The page should display the saved database messages.

### Understand the connection settings

The application uses these settings:

| Setting | Value | Meaning |
|---|---|---|
| `DB_HOST` | `db` | Docker network alias for PostgreSQL |
| `DB_PORT` | `5432` | PostgreSQL's internal listening port |
| `DB_USER` | `appuser` | Database user |
| `DB_NAME` | `appdb` | Database name |
| `DB_PASSWORD` | Lab password | Authentication password |

**Important:** `localhost` inside the app container refers to the app container itself, not the PostgreSQL container. Containers should use the database's network name or alias.

## 9. Practise Docker DNS

Resolve the database alias from another container on the same network:

```bash
docker run --rm \
  --network task4-net \
  postgres:16-alpine \
  getent hosts db
```

The command should return the address associated with `db`.

Now test from the default bridge network:

```bash
docker run --rm \
  --network bridge \
  postgres:16-alpine \
  getent hosts db
```

The `db` alias should not resolve there because the temporary container is not connected to `task4-net`.

### Why does this happen?

Containers on a user-defined bridge network can use Docker's embedded DNS to resolve other containers by name or network alias. Containers on different networks cannot automatically resolve each other's network aliases.

DNS resolution and application connectivity are separate checks. A successful name lookup does not prove that the database is healthy or accepting connections.

## 10. Prove that the volume preserves data

First, check the table:

```bash
docker exec task4-db \
  psql -U appuser -d appdb \
  -c "SELECT * FROM messages;"
```

Remove the database container:

```bash
docker rm -f task4-db
```

Inspect the volume:

```bash
docker volume inspect task4-pgdata
```

The volume still exists because removing a container does not normally delete a separately managed named volume.

Recreate PostgreSQL with the same volume and network alias:

```bash
docker run -d \
  --name task4-db \
  --network task4-net \
  --network-alias db \
  -e POSTGRES_USER=appuser \
  -e POSTGRES_PASSWORD=devpass123 \
  -e POSTGRES_DB=appdb \
  -v task4-pgdata:/var/lib/postgresql/data \
  postgres:16-alpine
```

Wait for PostgreSQL to become ready:

```bash
docker exec task4-db pg_isready -U appuser -d appdb
```

Query the original row:

```bash
docker exec task4-db \
  psql -U appuser -d appdb \
  -c "SELECT * FROM messages;"
```

The original data should still be present.

Refresh the app at `http://localhost:3000/`. It should reconnect after PostgreSQL becomes ready.

### What did you prove?

- A container is disposable.
- A named volume has a lifecycle independent of its container.
- Reusing the same volume preserves database files.
- Reusing the same network alias allows the app to resolve the recreated database container.

Do not remove the volume until you are certain you no longer need its data.

## 11. Practise bind mounts

A bind mount shares a specific host path with a container.

Create a file on the host:

```bash
mkdir -p host-files
echo "Hello from the host" > host-files/message.txt
```

Read it from a temporary container:

```bash
docker run --rm \
  --mount type=bind,source="$(pwd)/host-files",target=/data,readonly \
  alpine \
  cat /data/message.txt
```

Expected output:

```text
Hello from the host
```

Update the host file:

```bash
echo "Updated on the host" > host-files/message.txt
```

Repeat the container command to see the updated text.

The container reads the host file directly. The `readonly` option prevents writes through that mount from the container.

## 12. Practise port mapping and port conflicts

The application already uses host port `3000`. Try publishing another container on the same port:

```bash
docker run -d \
  --name task4-conflict \
  -p 3000:80 \
  nginx:alpine
```

Docker should report that the host port is already allocated.

Inspect existing containers:

```bash
docker ps
docker ps -a
```

Remove a container left by the failed attempt, if present:

```bash
docker rm -f task4-conflict
```

Use another host port:

```bash
docker run -d \
  --name task4-nginx \
  -p 8080:80 \
  nginx:alpine
```

Test it:

```bash
curl -I http://localhost:8080
```

Remove the test container:

```bash
docker rm -f task4-nginx
```

### Understand `-p`

```text
-p HOST_PORT:CONTAINER_PORT
```

For example, `-p 8080:80` forwards traffic from host port `8080` to port `80` inside the container.

The host port must be available. The container port must match the port on which the application listens.

## 13. Volume vs bind mount vs tmpfs

| Type | Stored where? | Typical use |
|---|---|---|
| Named volume | Docker-managed storage | Database data and persistent application data |
| Bind mount | A specified host filesystem path | Source code, configuration files, development |
| `tmpfs` mount | Memory on the host | Temporary data that should not be written to a persistent filesystem |

Example `tmpfs` mount on a Linux Docker host:

```bash
docker run --rm \
  --tmpfs /tmp \
  alpine \
  sh -c "echo temporary-data > /tmp/example.txt && cat /tmp/example.txt"
```

The data in this `tmpfs` mount is temporary and is not preserved as a normal persistent volume.

## 14. Network driver overview

| Driver | Purpose |
|---|---|
| `bridge` | Connects containers on a single Docker host. |
| `host` | Uses the host's network namespace on supported Linux setups, reducing network isolation. |
| `none` | Provides no normal external container networking. |
| `overlay` | Connects services across multiple Docker hosts when supported by the deployment setup. |

For everyday single-host development, a **user-defined bridge network** is a common choice.

## 15. Troubleshooting reference

### View container state

```bash
docker ps
docker ps -a
docker inspect task4-app
```

`docker ps -a` includes stopped containers, which helps diagnose name conflicts after a failed run.

### View application and database logs

```bash
docker logs task4-app
docker logs task4-db
```

### Inspect networking

```bash
docker network inspect task4-net
docker port task4-app
```

### Inspect storage

```bash
docker volume ls
docker volume inspect task4-pgdata
```

### Common problems

**Problem: The app returns `503 Database unavailable`.**

Check:

1. Is PostgreSQL running?
2. Does `pg_isready` report that it is accepting connections?
3. Are the username, password and database correct?
4. Are both containers attached to `task4-net`?
5. Does PostgreSQL have the `db` network alias?

**Problem: `db` cannot be resolved.**

Verify the network:

```bash
docker network inspect task4-net
```

The app or test container must be attached to the same network as PostgreSQL.

**Problem: Port already allocated.**

Inspect running and stopped containers:

```bash
docker ps
docker ps -a
```

Choose an unused host port or stop/remove the container that owns the conflicting port.

**Problem: Database data disappeared.**

Check that the new database container mounted the original volume at the correct data directory:

```bash
docker inspect task4-db
docker volume inspect task4-pgdata
```

If you removed the volume itself, the original volume data may be lost.

## 16. Interview questions and answers

### Q1. What is a Docker volume?

A Docker volume is persistent storage managed by Docker. It can be mounted into a container and can outlive that container.

**Example:** PostgreSQL writes its database files into `task4-pgdata`, so recreating the container with the same volume preserves the data.

### Q2. What is the difference between a named volume and a bind mount?

A named volume is managed by Docker, while a bind mount maps a specific host path into a container.

Use volumes for persistent application data and bind mounts when you need to share particular host files or directories.

### Q3. What happens to volume data when a container is removed?

Normally, the volume remains. A separately managed named volume is not automatically deleted by ordinary container removal. Removing the volume itself is a different operation and can destroy the data.

### Q4. What is a Docker bridge network?

A bridge network connects containers on the same Docker host through a virtual network bridge. A user-defined bridge network also provides Docker DNS-based discovery between attached containers.

### Q5. What is the difference between the default bridge and a user-defined bridge?

A user-defined bridge supports automatic name-based discovery between attached containers and offers clearer network isolation. The default bridge does not provide the same automatic container-name DNS behavior for ordinary containers.

### Q6. Why can the app connect to `db` instead of an IP address?

`db` is a network alias assigned to PostgreSQL on `task4-net`. Docker's embedded DNS resolves that alias to the container's current network address.

### Q7. Why should an app use `db:5432` instead of `localhost:5432`?

Inside a container, `localhost` refers to that same container. Since PostgreSQL is in another container, the app must connect using the database's network name or alias.

### Q8. What does `-p 3000:3000` mean?

It publishes host port `3000` and forwards incoming traffic to port `3000` inside the container. The application must actually listen on that container port.

### Q9. What is the difference between `EXPOSE` and `-p`?

`EXPOSE` documents the intended container port in the image metadata. It does not publish the port. `-p` configures host-to-container port mapping when creating a container.

### Q10. Why doesn't PostgreSQL need a published port in this lab?

The app and database communicate over the same Docker network. Publishing port `5432` to the host is unnecessary for this container-to-container connection.

### Q11. Why did the port-conflict command fail?

Another container was already using the requested host port. A host port can generally be allocated to only one conflicting published endpoint at a time. Use a different host port or resolve the existing allocation.

### Q12. Does a container's IP address stay the same after recreation?

Not necessarily. A recreated container may receive a different IP address. Connecting through a stable network name or alias avoids hard-coding the address.

### Q13. What is a bind mount useful for?

It is useful for sharing host files with a container, such as application source code, configuration files or development assets.

### Q14. When would you use a `tmpfs` mount?

Use it for temporary data that should reside in memory rather than persistent container or host storage. Its availability and behavior depend on the host and Docker setup.

### Q15. What is the purpose of a custom Docker network in a multi-container application?

It provides a dedicated communication network and name-based discovery for services. For example, the app can connect to the PostgreSQL service by using `db`.

### Q16. What should you check when an app cannot connect to PostgreSQL?

Check database readiness, application logs, credentials, database name, network membership, DNS alias and listening port. Diagnose the connection in stages rather than assuming the problem is the volume.

### Q17. Is passing a database password with `-e` secure for production?

It is convenient for a local lab but should not be treated as production-grade secrets management. Use an appropriate secret-management approach for the deployment environment and avoid committing credentials to source control.

### Q18. What is the difference between removing a container and removing a volume?

Removing a container deletes that container instance. Removing a volume deletes the separately managed storage and can permanently remove persistent data.

## 17. Evidence and completion checklist

Capture evidence for your lab repository:

- [ ] `docker network ls` showing `task4-net`.
- [ ] `docker volume ls` showing `task4-pgdata`.
- [ ] PostgreSQL readiness check.
- [ ] SQL query showing the inserted message.
- [ ] Browser or `curl` output from the app.
- [ ] `/health` response confirming the database connection.
- [ ] DNS resolution of `db` on the custom network.
- [ ] The same SQL row after PostgreSQL container recreation.
- [ ] Bind-mount test output.
- [ ] Port-conflict error and successful alternative port test.

Create an evidence directory:

```bash
mkdir -p evidence
```

Save screenshots or terminal captures there if your training submission requires them.

## 18. Git commit

From your project directory:

```bash
git status
git add README.md app/
git commit -m "Complete Docker Task 4 storage and networking lab"
```

If your repository requires evidence files, add them separately after checking that they contain no credentials or sensitive information.

## 19. Cleanup

Remove the lab containers:

```bash
docker rm -f task4-app task4-db 2>/dev/null || true
```

Remove the network:

```bash
docker network rm task4-net
```

**Only if you no longer need the database data**, remove the volume:

```bash
docker volume rm task4-pgdata
```

Optionally remove the app image:

```bash
docker image rm task4-app:v1
```

Do not delete `task4-pgdata` before completing the persistence exercise.

## Final summary

This lab demonstrates four core Docker skills:

1. **Storage:** named volumes preserve data beyond a container's lifetime.
2. **Networking:** containers on a user-defined bridge network can communicate using DNS names.
3. **Port mapping:** `-p` publishes a container service through a host port.
4. **Troubleshooting:** logs, inspection, DNS tests and readiness checks help isolate connectivity failures.

The key production principle is to keep persistent data separate from disposable containers, connect services through deliberate networks, and publish only the ports that need to be accessible.
