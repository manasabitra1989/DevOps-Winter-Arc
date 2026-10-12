# Docker Day 11 — Persistent PostgreSQL + Connected App

## 1. Objective

The goal of this hands-on lab is to understand how Docker handles persistent storage and container networking by running PostgreSQL and connecting a separate client container to it.

By completing this task, you will learn how to:

- Create and manage Docker networks and named volumes.
- Run PostgreSQL with persistent storage.
- Insert data and prove it survives container deletion.
- Connect separate containers using Docker's built-in DNS.
- Understand why containers on different networks cannot automatically resolve each other's names.
- Troubleshoot host-port conflicts.
- Back up a Docker volume to a compressed archive.
- Restore a volume into a new volume and verify the database.
- Understand volumes, bind mounts, tmpfs, and network drivers.
- Use common Docker troubleshooting and inspection commands.
- Answer Docker networking and storage interview questions.

## 2. Prerequisites

- Docker installed and running.
- Ubuntu or another Linux terminal.
- Docker Desktop with WSL2 integration if working on Windows.
- Basic familiarity with `docker run`, `docker exec`, and `docker ps`.

Verify Docker:

```bash
docker --version
docker info
docker ps
```

If `docker info` fails, start Docker Desktop and check WSL integration, if applicable.

## 3. Architecture

We will create a PostgreSQL container named `db`, attach it to a custom network named `app-net`, and store its database files in a named volume called `pgdata`.

```text
                  Docker network: app-net
        +-----------------------------------------+
        |                                         |
        |  +----------------+   PostgreSQL 5432   |
        |  | Client         | ----------------->  |
        |  | psql container |    hostname: db     |
        |  +----------------+                     |
        |                             +-----------+
        |                             | db        |
        |                             | PostgreSQL|
        |                             +-----+-----+
        |                                   |
        +-----------------------------------|-----+
                                            |
                                     Named volume
                                        pgdata
                                            |
                                  Persistent database
```

In this lab, we will use a `psql` client container as the second container instead of building a separate application. The same networking principles apply to an API or web application.

### Important concepts

- **Container:** runs the PostgreSQL process.
- **Volume:** stores the database files outside the container's writable layer.
- **Network:** connects the database and client containers.
- **DNS:** lets the client resolve the database container using the name `db`.
- **Backup:** creates an archive of the database volume.
- **Port mapping:** publishes a container port on the host.

## 4. Create the project directory

```bash
mkdir -p ~/DevOps-Winter-Arc/Week2-Docker/Day11-Persistent-PostgreSQL/evidence

cd ~/DevOps-Winter-Arc/Week2-Docker/Day11-Persistent-PostgreSQL
```

This directory will contain the README, backup archive, and any evidence you save from the exercise.

## 5. Task 1 — Create the network and volume

### Create a custom network

```bash
docker network create app-net
```

This creates a user-defined Docker bridge network named `app-net`.

Containers attached to this network can communicate with each other using their container names.

### Create a named volume

```bash
docker volume create pgdata
```

This creates a Docker-managed volume named `pgdata`.

The volume will hold PostgreSQL's database files and survive container deletion.

### Verify both resources

```bash
docker network ls
docker volume ls
docker network inspect app-net
docker volume inspect pgdata
```

**What you should understand:** networks and volumes are separate Docker resources. Removing a container does not automatically remove either one.

If either resource already exists, inspect it and reuse it for this lab rather than creating a differently named duplicate.

## 6. Task 2 — Run PostgreSQL with persistent storage

Start PostgreSQL:

```bash
docker run -d \
  --name db \
  --network app-net \
  -e POSTGRES_PASSWORD=changeme \
  -e POSTGRES_DB=shop \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16-alpine
```

### Explanation

| Option | Purpose |
|---|---|
| `docker run` | Creates and starts a container. |
| `-d` | Runs the container in the background. |
| `--name db` | Gives the container the name `db`. |
| `--network app-net` | Connects the container to our custom network. |
| `-e POSTGRES_PASSWORD=changeme` | Supplies the initial PostgreSQL password. |
| `-e POSTGRES_DB=shop` | Requests creation of the `shop` database during initialization. |
| `-v pgdata:/var/lib/postgresql/data` | Mounts the named volume at PostgreSQL's data directory. |
| `postgres:16-alpine` | Uses the PostgreSQL 16 Alpine image. |

### Security note

`changeme` is a lab-only password. Do not use it in production.

Environment variables are useful for this exercise, but they can be exposed through container inspection. Production deployments should use an appropriate secrets-management mechanism.

### Check the container

```bash
docker ps
docker logs db
docker inspect db
docker inspect db --format '{{json .Mounts}}'
```

The mount information should show `pgdata` mounted at `/var/lib/postgresql/data`.

### Wait for PostgreSQL

```bash
docker exec db pg_isready -U postgres
```

Expected output indicates that the server is accepting connections.

If PostgreSQL is still starting, wait a few seconds and retry. Check `docker logs db` if it does not become ready.

### Why is the mount path important?

PostgreSQL must write its database files into the mounted volume. If the volume is mounted at the wrong location, database data might be written to the container's writable layer instead, which would not provide the expected persistence.

## 7. Task 3 — Create a table and insert data

Run:

```bash
docker exec db psql -U postgres -d shop -c \
  "CREATE TABLE notes(id serial, msg text); INSERT INTO notes(msg) VALUES ('I survive!');"
```

### Understand the command

- `docker exec db` runs a command inside the existing container.
- `psql` is PostgreSQL's command-line client.
- `-U postgres` specifies the database user.
- `-d shop` selects the database.
- `-c` executes the SQL statement.

The SQL creates a table:

```sql
CREATE TABLE notes (
    id serial,
    msg text
);
```

- `id serial` creates an integer column with automatically generated sequence values.
- `msg text` stores a message.

Then it inserts a row:

```sql
INSERT INTO notes(msg) VALUES ('I survive!');
```

### Verify the row

```bash
docker exec db psql -U postgres -d shop -c "SELECT * FROM notes;"
```

Expected result includes:

```text
 id |    msg
----+-----------
  1 | I survive!
```

The ID can differ if the table already has rows.

## 8. Task 4 — Delete and recreate the database container

This step proves that a named volume preserves data.

### Remove the container

```bash
docker rm -f db
```

This force-stops and removes the container. It does not delete the named volume `pgdata`.

Verify:

```bash
docker ps -a
docker volume ls
```

The container should be gone, but `pgdata` should still exist.

### Recreate PostgreSQL with the same volume

```bash
docker run -d \
  --name db \
  --network app-net \
  -e POSTGRES_PASSWORD=changeme \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16-alpine
```

We do not need to reinitialize `shop`. Its existing database files are in `pgdata`.

The PostgreSQL initialization environment variables apply when initializing an empty data directory. Changing them later does not automatically reconfigure an existing database.

### Wait and query the data

```bash
docker exec db pg_isready -U postgres
```

Then:

```bash
docker exec db psql -U postgres -d shop -c "SELECT * FROM notes;"
```

The original `I survive!` row should still exist.

**Success condition:** the database container was deleted and recreated, but the data survived because both containers used the same named volume.

## 9. Task 5 — Connect a second container to PostgreSQL

Run a temporary PostgreSQL client on `app-net`:

```bash
docker run --rm \
  --network app-net \
  -e PGPASSWORD=changeme \
  postgres:16-alpine \
  psql -h db -U postgres -d shop -c "SELECT count(*) FROM notes;"
```

### Explanation

| Part | Purpose |
|---|---|
| `--rm` | Removes the temporary client container after it exits. |
| `--network app-net` | Connects the client to the same network as the database. |
| `-e PGPASSWORD=changeme` | Supplies the client's database password. |
| `postgres:16-alpine` | Provides the `psql` client. |
| `-h db` | Connects to the hostname `db`. |
| `-U postgres` | Uses the PostgreSQL user. |
| `-d shop` | Selects the database. |
| `SELECT count(*) FROM notes` | Counts the rows in the table. |

Expected result:

```text
 count
-------
     1
```

The count may differ if you inserted more rows.

### Why does `db` resolve?

Docker's user-defined network provides DNS resolution for container names. Because the database and client are attached to `app-net`, the client can find the database using the hostname `db`.

PostgreSQL uses port `5432` internally. We do not need to publish that port on the host for containers on the same network to communicate.

## 10. Task 6 — Test network-scoped DNS

### Test from the default bridge network

```bash
docker run --rm alpine ping -c 1 db
```

This should fail to resolve `db` because the temporary Alpine container is not connected to `app-net`.

### Test from the custom network

```bash
docker run --rm --network app-net alpine ping -c 1 db
```

This should resolve the hostname and attempt to ping the database container.

**Note:** ping can fail even when DNS works because ICMP responses may not be available. If necessary, verify connectivity using the `psql` client command from the previous section.

### The lesson

Containers must share an appropriate network to resolve each other's names through Docker's user-defined network DNS.

The default bridge does not provide the same automatic container-name DNS behavior.

## 11. Task 7 — Back up the volume

A raw archive of a PostgreSQL data directory should be created while the database is stopped to avoid capturing files while PostgreSQL is changing them.

### Stop PostgreSQL

```bash
docker stop db
```

### Create a compressed archive

Run this from the directory where you want to save the backup:

```bash
docker run --rm \
  -v pgdata:/data:ro \
  -v "$(pwd)":/backup \
  alpine \
  tar czf /backup/pgdata-backup.tgz -C /data .
```

### Explanation

| Part | Purpose |
|---|---|
| `--rm` | Removes the temporary backup container after it exits. |
| `-v pgdata:/data:ro` | Mounts the database volume read-only at `/data`. |
| `-v "$(pwd)":/backup` | Mounts the current host directory at `/backup`. |
| `alpine` | Supplies the `tar` utility. |
| `tar czf` | Creates a gzip-compressed tar archive. |
| `/backup/pgdata-backup.tgz` | Specifies the backup destination. |
| `-C /data .` | Archives the contents of the mounted volume. |

### Verify the backup

```bash
ls -lh pgdata-backup.tgz
```

List the archive contents:

```bash
docker run --rm \
  -v "$(pwd)":/backup:ro \
  alpine \
  tar tzf /backup/pgdata-backup.tgz | head
```

The archive should contain PostgreSQL data-directory files.

### Restart PostgreSQL

```bash
docker start db
docker exec db pg_isready -U postgres
```

Verify the data again:

```bash
docker exec db psql -U postgres -d shop -c "SELECT * FROM notes;"
```

### Backup best practice

For important databases, consider a PostgreSQL-aware logical backup using `pg_dump`. A raw volume archive requires correct database shutdown, compatible restoration conditions, and preservation of file ownership and permissions.

## 12. Task 8 — Restore the backup into a new volume

This test verifies that the archive contains recoverable data without overwriting the original volume.

### Create the new volume

```bash
docker volume create pgdata2
```

### Extract the archive

```bash
docker run --rm \
  -v pgdata2:/data \
  -v "$(pwd)":/backup:ro \
  alpine \
  tar xzf /backup/pgdata-backup.tgz -C /data
```

### Start a test PostgreSQL container

```bash
docker run -d \
  --name db-restore-test \
  --network app-net \
  -e POSTGRES_PASSWORD=changeme \
  -v pgdata2:/var/lib/postgresql/data \
  postgres:16-alpine
```

Wait for the server:

```bash
docker logs db-restore-test
docker exec db-restore-test pg_isready -U postgres
```

Query the restored database:

```bash
docker exec db-restore-test psql -U postgres -d shop -c "SELECT * FROM notes;"
```

The original row should be present.

If the test container fails, inspect the logs. File ownership, permissions, PostgreSQL version compatibility, and backup consistency can affect recovery.

Remove the temporary test container after verification:

```bash
docker rm -f db-restore-test
```

Keep `pgdata2` until you no longer need the restored copy.

## 13. Task 9 — Port-conflict drill

### Start the first Nginx container

```bash
docker run -d --name w1 -p 8080:80 nginx:1.27-alpine
```

Test:

```bash
curl http://localhost:8080
```

### Try to reuse the same host port

```bash
docker run -d --name w2 -p 8080:80 nginx:1.27-alpine
```

This should fail because host port `8080` is already allocated by the first container.

Inspect the containers:

```bash
docker ps
docker ps -a
```

### Fix the conflict

Remove any failed container with that name and use another host port:

```bash
docker rm -f w2
docker run -d --name w2 -p 8081:80 nginx:1.27-alpine
```

Verify both:

```bash
curl http://localhost:8080
curl http://localhost:8081
```

### Find the port owner

```bash
ss -tulpn | grep ':8080'
docker ps
docker port w1
```

On Docker Desktop with WSL2, the host networking implementation can differ from native Linux. If `ss` does not identify the owner, use `docker ps` and `docker port` to inspect published container ports.

### Understand the mapping

- `-p 8080:80` means host port `8080` forwards to container port `80`.
- The host ports must be different when both containers publish on the same host address.
- Containers can listen on the same internal port because each has its own network namespace.

## 14. Key Concepts — The 30%

### 14.1 Containers are disposable

Everything written inside a container's writable layer is tied to that container's lifecycle. Removing the container removes that writable layer.

A database running without persistent storage can lose its data when the container is removed.

Use volumes for data that must survive container replacement.

### 14.2 Volume

A Docker-managed volume stores data separately from the container.

- Survives container deletion.
- Suitable for databases, uploads, and persistent application data.
- Managed through Docker volume commands.
- Commonly used for production data.

Useful commands:

```bash
docker volume create pgdata
docker volume ls
docker volume inspect pgdata
```

### 14.3 Bind mount

A bind mount maps a specific host path into a container.

It is useful for development because edits made on the host can be visible in the container immediately.

Example:

```bash
docker run --rm \
  -v "$(pwd)/html:/usr/share/nginx/html:ro" \
  nginx:alpine
```

The `:ro` suffix makes the mount read-only from the container's perspective.

Bind mounts depend on host paths and their permissions.

### 14.4 tmpfs

A tmpfs mount stores temporary files in memory rather than in a persistent Docker volume.

Example:

```bash
docker run --rm --tmpfs /tmp alpine
```

When the container stops and is removed, the tmpfs data does not persist.

tmpfs is useful for temporary scratch data. Although it can be useful for sensitive temporary files, it should not automatically be treated as a complete secrets-management solution.

## 15. Volume vs Bind Mount vs tmpfs

| Property | Named volume | Bind mount | tmpfs |
|---|---|---|---|
| Where stored | Docker-managed storage area | A host path you choose | Memory |
| Managed by | Docker | You and the host OS | Kernel |
| Survives container removal | Yes | Yes, because host files remain | No |
| Best for | Databases, uploads, persistent data | Development code and configuration | Temporary scratch files |
| Example | `-v pgdata:/var/lib/postgresql/data` | `-v "$(pwd)/html:/usr/share/nginx/html"` | `--tmpfs /tmp` |

Named volumes are generally the best starting point for persistent database storage.

## 16. Network Drivers

| Driver | What it does | Typical use |
|---|---|---|
| `bridge` (default) | Provides a network on one Docker host; the default bridge does not provide the same automatic container-name DNS as a user-defined bridge. | Quick, single-host tests |
| User-defined `bridge` | Provides container networking, automatic name resolution, and application-level isolation. | Most single-host multi-container applications |
| `host` | Shares the host network stack; port publishing is generally unnecessary. | Specialized Linux networking or performance needs |
| `none` | Disables normal container networking. | Isolated batch jobs |
| `overlay` | Connects services across multiple Docker hosts in supported Swarm deployments. | Multi-host Docker Swarm applications |

Inspect available networks:

```bash
docker network ls
docker network inspect app-net
```

Create a network:

```bash
docker network create app-net
```

Attach an existing container:

```bash
docker network connect app-net web
```

Detach it:

```bash
docker network disconnect app-net web
```

Remove an unused network:

```bash
docker network rm app-net
```

A network generally cannot be removed while containers remain attached.

## 17. How Containers Communicate

Consider a typical web application:

```text
Browser
   |
   | host port 8080
   v
API container
   |
   | custom network: app-net
   | hostname: db
   v
PostgreSQL container
   |
   v
Named volume: pgdata
```

Only the API needs to be published to the host in a typical deployment. PostgreSQL can remain reachable only over the internal application network.

For example, an API might connect using a database connection string like:

```text
postgresql://postgres:<password>@db:5432/shop
```

Replace the password placeholder with a securely supplied credential. Do not use this example password or store real credentials in source control.

### Typical network mistakes

- **Using `localhost` inside a container:** `localhost` refers to that same container, not the database container or your host.
- **Containers on different networks:** they cannot automatically resolve each other's container names through Docker's user-defined network DNS.
- **Database port published unnecessarily:** publishing `5432` can expose PostgreSQL to host interfaces and potentially other machines, depending on the binding and firewall. Keep it internal unless external access is required and secured.
- **Service not ready:** a running container does not necessarily mean its application is ready to accept connections.
- **Application listening on the wrong interface:** a service intended to accept container-network traffic generally needs to listen on `0.0.0.0`, not only `127.0.0.1`.

## 18. Command Reference — Volumes

| Command | What it does | DevOps use case |
|---|---|---|
| `docker volume create pgdata` | Creates a named volume | Prepare storage for a database |
| `docker volume ls` | Lists volumes | See available Docker-managed storage |
| `docker volume inspect pgdata` | Shows volume details and mountpoint | Inspect storage configuration |
| `docker volume rm pgdata` | Deletes a volume | Cleanup when data is no longer needed |
| `docker volume prune` | Removes unused volumes, subject to the command's scope and options | Reclaim storage after reviewing impact |
| `docker run -v pgdata:/data alpine` | Mounts a named volume | Access persistent files |
| `docker run -v "$(pwd):/app" node:20-alpine` | Bind-mounts the current directory | Development workflows |
| `docker run -v "$(pwd)/conf:/etc/app:ro" alpine` | Mounts a host directory read-only | Supply configuration |

**Warning:** `docker volume rm` and volume-pruning commands can permanently remove data. Review the target volumes before running them, especially on servers.

## 19. Command Reference — Networks

| Command | What it does | DevOps use case |
|---|---|---|
| `docker network ls` | Lists networks | See available networks |
| `docker network create app-net` | Creates a user-defined bridge network | Isolate one application |
| `docker network inspect app-net` | Shows network details and attached containers | Diagnose connectivity |
| `docker run --network app-net --name db ...` | Starts a container on a network | Connect application components |
| `docker network connect app-net web` | Attaches an existing container | Add a running container to a network |
| `docker network disconnect app-net web` | Detaches a container | Isolate a container |
| `docker port web` | Shows published port mappings | Verify host-to-container ports |
| `docker network rm app-net` | Removes a network when unused | Cleanup |

## 20. Troubleshooting Connectivity

| Command | What it does | DevOps use case |
|---|---|---|
| `ss -tulpn \| grep 8080` | Looks for a listener using port 8080 | Investigate a port conflict |
| `docker network inspect app-net` | Shows network membership and addresses | Check whether containers share a network |
| `docker exec db pg_isready -U postgres` | Checks whether PostgreSQL accepts connections | Database readiness check |
| `docker logs db --tail 30` | Displays recent database logs | Find startup and authentication errors |
| `docker port web` | Displays published ports | Confirm port mapping |
| `docker ps -a` | Shows running and stopped containers | Find failed containers or name conflicts |

If your container includes `curl`, `ping`, or `nslookup`, those utilities can help test DNS and connectivity. Minimal images may not contain them. For this lab, a temporary PostgreSQL client container is a reliable way to test database connectivity.

Example database connection test:

```bash
docker run --rm \
  --network app-net \
  -e PGPASSWORD=changeme \
  postgres:16-alpine \
  psql -h db -U postgres -d shop -c "SELECT 1;"
```

## 21. Troubleshooting Guide

### PostgreSQL connection refused

Wait for PostgreSQL:

```bash
docker exec db pg_isready -U postgres
docker logs db --tail 30
```

A running container can still be initializing the database.

### Could not translate host name `db`

Check that the client uses `--network app-net` and that the database is attached to the same network:

```bash
docker network inspect app-net
```

### Password authentication failed

Check the username, password, and database name. Remember that PostgreSQL's initialization environment variables do not reset credentials in an already-initialized volume.

### Database does not exist

Check whether the data directory was initialized with the expected database:

```bash
docker exec db psql -U postgres -l
```

The `POSTGRES_DB` variable is applied during initial initialization of an empty data directory.

### Data disappeared after container deletion

Check whether the volume was mounted at the correct data directory:

```bash
docker inspect db --format '{{json .Mounts}}'
docker volume inspect pgdata
```

If PostgreSQL was writing to the container layer rather than the intended volume, data may have been lost with the container.

### Port already allocated

Check:

```bash
docker ps
docker ps -a
docker port w1
ss -tulpn | grep ':8080'
```

Remove a failed container if necessary, then select another unused host port.

### Restore container fails to start

Inspect the logs:

```bash
docker logs db-restore-test
```

Possible causes include inconsistent backup files, incompatible PostgreSQL versions, and file ownership or permission problems.

## 22. Day 11 Interview Questions

### Q1. What is the difference between a container and a volume?

A container provides the application runtime and a writable layer. A volume stores data independently of the container and can be reused by replacement containers.

### Q2. What is the difference between a volume and a bind mount?

A named volume is managed by Docker. A bind mount maps a specific host path into the container and is useful for development files and configuration.

### Q3. Why did the PostgreSQL data survive `docker rm -f db`?

The database files were stored in the named volume `pgdata`, which was not deleted with the container.

### Q4. Why can containers resolve names on a custom bridge network but not the default bridge?

User-defined bridge networks provide automatic DNS resolution by container name. The default bridge does not provide the same name-resolution behavior.

### Q5. What does `-p 8080:80` do?

It publishes host port `8080` and forwards traffic to port `80` in the container. Docker configures the networking rules needed for the mapping.

### Q6. What happens when a container using a named volume is removed?

The container is removed, but the volume and its data remain until the volume itself is deleted.

### Q7. How do you troubleshoot `port is already allocated`?

Inspect `docker ps`, `docker port`, and, where applicable, `ss -tulpn`. Stop or remove the conflicting workload, or use another host port.

### Q8. Two containers cannot communicate. What do you check?

Check that both containers share a suitable network, use the correct service name instead of `localhost`, that the application is listening on the right interface and port, and that the service is ready. Review network inspection output and logs.

### Q9. What is a tmpfs mount?

A temporary filesystem backed by memory. Its contents do not persist after the container stops and is removed.

### Q10. Why should a PostgreSQL volume backup be made while the database is stopped?

Copying a live database directory can capture inconsistent files while PostgreSQL is modifying them. A clean shutdown provides a more consistent raw-file backup.

### Q11. Why is a successful DNS lookup not enough to prove an application works?

DNS only resolves the name. The target application may still be stopped, listening on a different port, or refusing connections.

### Q12. Why should PostgreSQL normally remain unpublished to the host in this lab?

The client can reach PostgreSQL over the internal Docker network. Avoiding unnecessary host publication reduces exposure.

### Q13. Why don't PostgreSQL initialization variables reset the database on container recreation?

The official image uses those variables during initialization of an empty data directory. Existing database files and credentials remain in the mounted volume.

### Q14. What is the difference between a logical backup and a volume archive?

A logical backup such as `pg_dump` exports database objects and data in a PostgreSQL-aware format. A volume archive copies physical database files and depends on correct consistency, permissions, and restoration conditions.

## Conclusion

This lab demonstrates three essential Docker concepts:

1. **Persistence:** named volumes preserve database data when containers are replaced.
2. **Networking:** user-defined bridge networks provide container-name DNS and communication between application components.
3. **Recovery and troubleshooting:** backups must be verified, and network and port problems should be diagnosed systematically.

The most important lesson is that **containers are disposable, but persistent data and application networking must be designed deliberately**.
