# Day 10 — Docker Multi-Stage Builds

## Objective

Learn how to build Docker images using single-stage and multi-stage builds, reduce image size, run containers as a non-root user, and compare different runtime images.

## Project Structure

```text
day10-multistage/
├── main.go
├── go.mod
├── Dockerfile.single
├── Dockerfile
├── Dockerfile.scratch
├── README.md
└── evidence/
```

| File | Purpose |
|---|---|
| `main.go` | Go application with HTTP endpoints |
| `go.mod` | Defines the Go module and Go version |
| `Dockerfile.single` | Builds the application in a single image |
| `Dockerfile` | Uses multi-stage build and a non-root runtime user |
| `Dockerfile.scratch` | Optional minimal image using an empty base |
| `evidence/` | Stores screenshots and test results |
| `README.md` | Documents tasks, results, and concepts |

---

## Task 1 — Create the Project

```bash
mkdir -p ~/DevOps-Winter-Arc/Week2-Docker/day10-multistage/evidence
cd ~/DevOps-Winter-Arc/Week2-Docker/day10-multistage
```

**Explanation:**
- `mkdir -p` creates the project and evidence directories.
- `cd` moves into the project directory.
- `evidence/` stores screenshots and proof of completed tasks.

## Task 2 — Create the Go Application

Create `main.go`:

```go
package main

import (
    "fmt"
    "net/http"
)

func main() {
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintln(w, "Hello from a multi-stage build!")
    })

    http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprint(w, "ok")
    })

    http.ListenAndServe(":8080", nil)
}
```

**Code explanation:**
- `package main` defines an executable Go program.
- `fmt` writes text responses.
- `net/http` provides the HTTP server.
- `http.HandleFunc("/", ...)` handles requests to the root endpoint.
- `http.HandleFunc("/health", ...)` provides a health-check endpoint.
- `http.ListenAndServe(":8080", nil)` starts the server on port `8080`.

**Expected responses:**

| Endpoint | Response |
|---|---|
| `/` | `Hello from a multi-stage build!` |
| `/health` | `ok` |

Create `go.mod`:

```go
module demo

go 1.22
```

**Explanation:**
- `module demo` names the Go module.
- `go 1.22` declares the Go language version for the module.

## Task 3 — Build a Single-Stage Image

Create `Dockerfile.single`:

```dockerfile
FROM golang:1.22
WORKDIR /src
COPY . .
RUN go build -o /app/server .
EXPOSE 8080
CMD ["/app/server"]
```

**Line-by-line explanation:**
- `FROM golang:1.22` uses an image containing the Go compiler and tools.
- `WORKDIR /src` sets the working directory inside the image.
- `COPY . .` copies the project files into the image.
- `RUN go build -o /app/server .` compiles the Go application into a binary.
- `EXPOSE 8080` documents the port used by the application.
- `CMD ["/app/server"]` specifies the default command when the container starts.

Build the image:

```bash
docker build -f Dockerfile.single -t demo:single .
```

Check the image:

```bash
docker images demo
```

**Key concept:** A single-stage image keeps the Go build environment in the same image as the application, making the final image larger than necessary for this application.

## Task 4 — Build a Multi-Stage Image

Create `Dockerfile`:

```dockerfile
# Stage 1: Build
FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /out/server .

# Stage 2: Runtime
FROM alpine:3.20
RUN addgroup -S app && adduser -S -G app app
WORKDIR /app
COPY --from=builder --chown=app:app /out/server /app/server
USER app
EXPOSE 8080
CMD ["/app/server"]
```

**Code explanation:**

**Build stage**
- `FROM golang:1.22-alpine AS builder` creates a build environment with Go and names the stage `builder`.
- `WORKDIR /src` sets the working directory.
- `COPY go.mod ./` copies the dependency manifest first.
- `RUN go mod download` downloads module dependencies. This app has no third-party dependencies, but the command demonstrates a common build pattern.
- `COPY . .` copies the remaining project files.
- `CGO_ENABLED=0` builds without CGO, helping produce a standalone binary for this app.
- `-ldflags="-s -w"` removes symbol and debug information to reduce binary size.
- `-o /out/server` writes the compiled binary to `/out/server`.

**Runtime stage**
- `FROM alpine:3.20` starts a fresh, smaller runtime image.
- `addgroup` and `adduser` create an unprivileged application user.
- `WORKDIR /app` sets the runtime working directory.
- `COPY --from=builder` copies only the compiled binary from the build stage.
- `--chown=app:app` assigns ownership to the application user and group.
- `USER app` runs the application as a non-root user.
- `EXPOSE 8080` documents the application port.
- `CMD ["/app/server"]` starts the application.

Build and inspect:

```bash
docker build -f Dockerfile -t demo:multi .
docker images demo
```

**Key concept:** Multi-stage builds separate compilation from runtime. The final image does not need the Go compiler or the source code.

## Task 5 — Compare Image Sizes

```bash
docker images demo
```

Record the actual sizes shown on your machine.

| Image | Size |
|---|---|
| `demo:single` | Fill in measured size |
| `demo:multi` | Fill in measured size |
| `demo:scratch` (optional) | Fill in measured size |

Calculate the percentage reduction:

```text
Reduction (%) = ((Single-stage size - Multi-stage size)
                 / Single-stage size) × 100
```

**Example:** If the single-stage image is 850 MB and the multi-stage image is 20 MB:

```text
((850 - 20) / 850) × 100 = 97.65%
```

These example sizes are illustrative. Use your actual image sizes in the final report.

**Why reduce image size?**
- Less data to store and transfer.
- Faster image pulls and deployments.
- Fewer unnecessary components in the runtime image.

## Task 6 — Run and Test the Multi-Stage Image

If a container named `demo` already exists, remove it only if it belongs to this lab:

```bash
docker rm -f demo
```

Run the application:

```bash
docker run -d --name demo -p 8080:8080 demo:multi
```

Test both endpoints:

```bash
curl http://localhost:8080/
curl http://localhost:8080/health
```

Expected output:

```text
Hello from a multi-stage build!
ok
```

Check the running container:

```bash
docker ps
docker logs demo
docker port demo
```

**Explanation:**
- `-d` runs the container in the background.
- `--name demo` assigns a name to the container.
- `-p 8080:8080` maps host port `8080` to container port `8080`.
- `docker logs` displays application output.
- `docker port` displays published port mappings.

Verify the runtime user:

```bash
docker exec demo id
```

The output should show a non-zero UID, rather than `uid=0(root)`. This confirms the process runs as a non-root user.

Inspect image details:

```bash
docker history demo:multi
docker image inspect demo:multi
```

- `docker history` displays image layers and build instructions.
- `docker image inspect` displays image configuration and metadata.

## Task 7 — Build Only the Builder Stage

```bash
docker build --target builder -t demo:build -f Dockerfile .
```

**Explanation:**
- `--target builder` stops the build at the stage named `builder`.
- `-t demo:build` tags the resulting image.
- `-f Dockerfile` specifies the Dockerfile to use.

**Why this matters:** You can build or inspect an intermediate stage without building the final runtime image.

## Task 8 — Optional: Build a Scratch Image

Create `Dockerfile.scratch`:

```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /src
COPY go.mod ./
COPY main.go ./
RUN CGO_ENABLED=0 go build -ldflags="-s -w" -o /server .

FROM scratch
COPY --from=builder /server /server
EXPOSE 8080
ENTRYPOINT ["/server"]
```

**Code explanation:**
- The first stage compiles the application.
- `FROM scratch` starts with an empty base image.
- `COPY --from=builder` copies only the compiled binary.
- `EXPOSE 8080` documents the application port.
- `ENTRYPOINT ["/server"]` runs the binary when the container starts.

Build and run:

```bash
docker build -f Dockerfile.scratch -t demo:scratch .
docker run -d --name demo-scratch -p 8081:8080 demo:scratch
```

Test:

```bash
curl http://localhost:8081/
curl http://localhost:8081/health
docker images demo
```

**Important:** A `scratch` image has no shell or standard debugging utilities. Commands such as `docker exec demo-scratch sh` will fail. Check logs using:

```bash
docker logs demo-scratch
```

**Key concept:** `scratch` can produce an extremely minimal image, but it requires a suitable standalone executable and provides fewer tools for debugging.

## Task 9 — Troubleshooting

| Problem | Check | Possible fix |
|---|---|---|
| Image is still large | `docker images demo` and `docker history demo:multi` | Ensure the final stage uses a runtime image and copies only the binary |
| Port already allocated | `docker ps` | Stop or remove the lab container using that host port, or choose another host port |
| Container exits | `docker ps -a` and `docker logs demo` | Inspect startup errors and the build |
| Endpoint unavailable | `docker port demo` and `curl -v http://localhost:8080/health` | Verify the container is running and the port mapping is correct |
| Permission issue | `docker exec demo id` | Verify `USER app` and file ownership in the runtime stage |
| Builder target fails | `docker build --progress=plain --target builder -t demo:build -f Dockerfile .` | Check the `AS builder` name and build instructions |
| Cannot open a shell in scratch | `docker exec demo-scratch sh` | Expected: scratch has no shell; use logs or rebuild with a debugging-friendly image |

For troubleshooting notes, use this format:

```text
Problem:
Evidence:
Root Cause:
Fix:
Verification:
```

## Task 10 — Results and Evidence

Save relevant screenshots or command output in `evidence/`.

- [ ] Single-stage image built successfully.
- [ ] Multi-stage image built successfully.
- [ ] Actual image sizes recorded and reduction calculated.
- [ ] `/` endpoint returns the greeting.
- [ ] `/health` endpoint returns `ok`.
- [ ] `docker exec demo id` confirms a non-root UID.
- [ ] Builder target builds successfully.
- [ ] Optional scratch image built and tested.
- [ ] Troubleshooting notes completed.

Complete this results table with your actual results:

| Check | Result |
|---|---|
| Single-stage size | ___ |
| Multi-stage size | ___ |
| Size reduction | ___% |
| Root endpoint | Pass / Fail |
| Health endpoint | Pass / Fail |
| Non-root user | Pass / Fail |
| Builder target | Pass / Fail |
| Scratch image (optional) | Pass / Fail |

## Task 11 — Interview Questions and Answers

**1. What is a multi-stage Docker build?**

A build process using multiple `FROM` stages. Build tools and source code can stay in an earlier stage while only required artifacts are copied into the final image.

**2. What does `COPY --from=builder` do?**

It copies files from a previous build stage named `builder` into the current stage.

**3. Why should containers run as non-root?**

It reduces the impact of a compromised application by limiting its privileges inside the container.

**4. What are `scratch` and distroless images?**

- `scratch` is an empty base image.
- Distroless images provide selected runtime components without a typical shell and package manager.

Both can reduce unnecessary runtime components, but debugging may be harder.

**5. How would you reduce a 1 GB Node.js image?**

Use a multi-stage build, a suitable smaller runtime image, production-only dependencies, and a `.dockerignore` file. Copy only the files needed at runtime.

**6. How do you debug a failing build stage?**

Build the target stage explicitly and use plain build output:

```bash
docker build --progress=plain --target builder -t demo:build -f Dockerfile .
```

For runtime failures, check `docker logs`, container status, and configuration.

**7. What is the difference between `RUN`, `CMD`, and `ENTRYPOINT`?**

- `RUN` executes a command during image building.
- `CMD` supplies the default command or arguments when a container starts.
- `ENTRYPOINT` defines the main executable for the container.

**8. Why use `CGO_ENABLED=0`?**

It disables CGO during compilation. For this simple Go application, that helps produce a standalone binary suitable for minimal runtime images.

**9. What does `EXPOSE 8080` do?**

It documents the port the application listens on. It does not publish the port to the host; `-p` does that.

**10. Why does image size matter?**

Smaller images generally use less storage and bandwidth and can be pulled faster. Minimal runtime images can also reduce unnecessary components.

## Task 12 — Cleanup and Git

Remove only the containers created for this lab:

```bash
docker rm -f demo demo-scratch
```

If a container does not exist, Docker may report an error; that is okay. Avoid deleting unrelated containers.

Check your project:

```bash
git status
```

Stage and commit the lab files:

```bash
git add main.go go.mod Dockerfile.single Dockerfile README.md evidence/
```

If you created `Dockerfile.scratch`, stage it too:

```bash
git add Dockerfile.scratch
```

Commit and push:

```bash
git commit -m "Complete Day 10 Docker multi-stage builds"
git push
```

## Final Summary

- **Single-stage build:** Builds and runs the app in one image, which also retains the build environment.
- **Multi-stage build:** Separates building from running and copies only the compiled artifact into the final stage.
- **Non-root user:** Reduces unnecessary privileges.
- **Scratch image:** Can minimize the runtime image but makes interactive debugging harder.
- **Image comparison:** Use measured local image sizes rather than assumed values.

**Main takeaway:** A production-oriented container image should include the application and only the runtime components it needs, and should run with the least privilege practical.
