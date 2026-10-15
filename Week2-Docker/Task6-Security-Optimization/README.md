# Task 6 — Docker Security & Optimization

## 1. Overview

### Objective

Build, scan, optimize, and harden a Docker image using practical security and optimization techniques commonly used in DevOps workflows.

This lab builds on the previous Docker security lab. Instead of repeating only basic image scanning and non-root execution, it introduces additional practices such as:

- Multi-stage Docker builds and image-layer analysis
- Software Bill of Materials (SBOM)
- Trusted base images and digest pinning
- Trivy vulnerability scanning as a release gate
- Runtime secret injection
- Resource limits and filesystem restrictions
- Image tagging and artifact identity
- Security evidence and release documentation

### Learning outcomes

By completing this task, you should be able to:

1. Build an optimized Python application image.
2. Explain why image layers and build cache matter.
3. Scan an image and generate an SBOM using Trivy.
4. Understand image tags, digests, and reproducible builds.
5. Run an application as a non-root user.
6. Provide configuration and secrets at runtime instead of embedding them in the image.
7. Apply CPU, memory, process, and filesystem restrictions.
8. Record scan results and compare image sizes.
9. Explain Docker security practices in an interview.

---

## 2. Project structure

Create the project:

```bash
mkdir -p ~/DevOps-Winter-Arc/Week2-Docker/Task6-Security-Optimization
cd ~/DevOps-Winter-Arc/Week2-Docker/Task6-Security-Optimization

mkdir -p app reports
```

Expected structure:

```text
Task6-Security-Optimization/
├── app/
│   ├── app.py
│   └── requirements.txt
├── Dockerfile
├── .dockerignore
├── .gitignore
├── runtime.env
└── reports/
    ├── image-sizes.txt
    ├── image-history.txt
    ├── scan.json
    ├── sbom.json
    ├── image-id.txt
    └── results.txt
```

The `runtime.env` file contains a fake training token and must not be committed to Git.

The `reports/` directory contains the evidence generated during the lab. Review your organization's rules before committing scan reports or other generated artifacts.

---

## 3. Create the Python application

Create `app/app.py`:

```bash
nano app/app.py
```

Paste:

```python
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify(
        message="Task 6 security lab",
        version=os.getenv("APP_VERSION", "dev")
    )

@app.get("/health")
def health():
    return jsonify(status="ok"), 200

@app.get("/config")
def config():
    # Report whether the token exists, never its value.
    return jsonify(
        api_token_configured=bool(os.getenv("API_TOKEN"))
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### Explanation

- `os.getenv()` reads configuration from environment variables.
- `/` returns application information.
- `/health` provides a simple health endpoint.
- `/config` verifies whether the API token was supplied without returning the token itself.
- `0.0.0.0` allows the application to accept connections through the container's network interface.

This is a learning application, not a production-ready Flask deployment. A production application would normally use a production WSGI server and appropriate application-level security controls.

Create `app/requirements.txt`:

```bash
nano app/requirements.txt
```

Paste:

```text
Flask==3.1.1
```

The dependency is explicitly versioned so the lab has a defined Flask version. Pinning a version does not guarantee that every transitive dependency or the entire image is vulnerability-free.

---

## 4. Configure runtime secrets

Create `runtime.env`:

```bash
nano runtime.env
```

Paste:

```dotenv
API_TOKEN=training-only-not-a-real-secret
APP_VERSION=1.0.0
```

This token is fake and only for the lab. Never use a real API key or production password in this exercise.

Restrict file permissions:

```bash
chmod 600 runtime.env
```

### Create `.gitignore`

```bash
nano .gitignore
```

Paste:

```gitignore
runtime.env
.env
*.env
__pycache__/
*.pyc
.venv/
reports/
```

### Create `.dockerignore`

```bash
nano .dockerignore
```

Paste:

```dockerignore
.git
.gitignore
runtime.env
.env
*.env
reports/
__pycache__/
*.pyc
.venv/
```

### Why do we need both files?

| File | Purpose |
|---|---|
| `.gitignore` | Prevents Git from tracking specified local files |
| `.dockerignore` | Excludes specified files from the Docker build context |
| `runtime.env` | Supplies local runtime configuration to the container |

**Important:** `.gitignore` does not remove a file that Git already tracks. If a real secret was committed, rotate it and remove it from the repository history as appropriate.

Never copy secrets into a Docker image or put them in Dockerfile `ARG` or `ENV` instructions. Runtime environment variables are suitable for this local exercise, but production secrets should preferably use an appropriate secrets manager or platform secret mechanism.

---

## 5. Build an optimized multi-stage Docker image

Create the `Dockerfile`:

```bash
nano Dockerfile
```

Paste:

```dockerfile
# syntax=docker/dockerfile:1

# Stage 1: install application dependencies.
FROM python:3.12-slim AS build

WORKDIR /build

COPY app/requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# Stage 2: runtime image.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=1.0.0

RUN useradd --system --uid 10001 --no-create-home appuser

WORKDIR /app

COPY --from=build /install /usr/local
COPY --chown=appuser:appuser app/ /app/

USER 10001:10001

EXPOSE 5000

CMD ["python", "app.py"]
```

Build the image:

```bash
docker build --pull -t task6-api:1.0.0 .
```

### Explanation of the Dockerfile

| Instruction | Purpose |
|---|---|
| `FROM python:3.12-slim AS build` | Defines the dependency-installation stage |
| `WORKDIR /build` | Sets the working directory |
| `COPY app/requirements.txt .` | Copies the dependency manifest first |
| `RUN pip install ...` | Installs Python dependencies |
| `FROM python:3.12-slim AS runtime` | Starts a separate final image stage |
| `useradd` | Creates a dedicated non-root account |
| `COPY --from=build` | Copies installed dependencies from the build stage |
| `COPY --chown` | Copies application files with the intended owner |
| `USER 10001:10001` | Runs the app as a non-root UID and GID |
| `EXPOSE 5000` | Documents the application's listening port |
| `CMD` | Defines the default command |

### Why use a multi-stage build?

The final image does not inherit every file from the build stage. Only the selected dependency files are copied into the runtime stage.

This approach can reduce unnecessary build artifacts and makes it easier to separate build tools from runtime content.

This particular application has few dependencies, so the size improvement may be modest. Measure the result rather than assuming that a multi-stage build is always smaller.

### Why copy the requirements file first?

Docker can reuse the dependency-installation layer when the requirements file has not changed.

If application source code changes but dependencies remain the same, Docker can often reuse that cached layer and rebuild only the later layers.

---

## 6. Inspect image size, layers, and configuration

Run:

```bash
docker images task6-api
```

This shows the image tag and reported image size.

Inspect the image history:

```bash
docker history task6-api:1.0.0
```

This helps you identify the instructions that created the image's layers.

Inspect the configured user:

```bash
docker image inspect task6-api:1.0.0 \
  --format 'User={{.Config.User}}'
```

Expected user:

```text
User=10001:10001
```

Save evidence:

```bash
docker images task6-api > reports/image-sizes.txt

docker history task6-api:1.0.0 \
  > reports/image-history.txt
```

### New concept: image size versus storage usage

These measurements are related but not identical:

- **Image size:** the size reported for the image by Docker.
- **Shared layers:** layers that multiple images can reuse.
- **Registry transfer size:** the compressed data transferred when pulling or pushing.
- **Container writable layer:** changes made by a running container that are not stored in a named volume or other mount.

A smaller image can improve transfer time and reduce unnecessary packages, but size alone does not determine security.

---

## 7. Scan the image with Trivy

Check that Trivy is available:

```bash
trivy --version
```

If it is not installed, install it using the official Trivy installation instructions for your operating system.

Scan for HIGH and CRITICAL vulnerabilities:

```bash
trivy image \
  --severity HIGH,CRITICAL \
  task6-api:1.0.0
```

Save a JSON report:

```bash
trivy image \
  --severity HIGH,CRITICAL \
  --format json \
  --output reports/scan.json \
  task6-api:1.0.0
```

Review the report:

```bash
ls -lh reports/scan.json
```

### What does Trivy examine?

Depending on the scan type and available detection data, Trivy can identify known vulnerabilities in operating-system packages and supported application dependencies. It can also scan configuration files and detect certain exposed secrets.

A scan result depends on the scanner version, vulnerability database, image contents, and scan options.

A clean result does not prove that an image is completely secure.

### Use Trivy as a release gate

```bash
trivy image \
  --exit-code 1 \
  --severity HIGH,CRITICAL \
  task6-api:1.0.0
```

With these options, findings matching the configured severity gate cause a non-zero exit code. This is useful in CI/CD pipelines because automation can stop a release when the security check fails.

A non-zero exit can also result from an operational or scan error, so inspect the output rather than assuming every failure is a vulnerability.

Optional: ignore unfixed vulnerabilities when reviewing what can currently be remediated:

```bash
trivy image \
  --ignore-unfixed \
  --severity HIGH,CRITICAL \
  task6-api:1.0.0
```

This changes which findings are displayed. It should not be used to hide risk without documenting the reason.

---

## 8. Generate a Software Bill of Materials (SBOM)

An SBOM is an inventory of software components contained in an artifact.

Generate one:

```bash
trivy image \
  --format cyclonedx \
  --output reports/sbom.json \
  task6-api:1.0.0
```

Check the generated file:

```bash
ls -lh reports/sbom.json
head -n 20 reports/sbom.json
```

### Why is an SBOM useful?

Suppose a new vulnerability is announced in a popular library. An SBOM can help your team identify which built images include an affected version.

An SBOM is not a vulnerability scan by itself. It provides component inventory information that can support vulnerability analysis and software supply-chain management.

---

## 9. Trusted base images and digest pinning

Compare these references:

| Reference | Meaning |
|---|---|
| `python:latest` | A floating tag that can change over time |
| `python:3.12-slim` | A more intentional version tag, but still mutable |
| `python:3.12-slim@sha256:...` | A digest-pinned image reference |

Use a base image from a trusted, maintained source. Review its update policy and vulnerability status.

Inspect the local image's repository digests:

```bash
docker image inspect python:3.12-slim \
  --format '{{json .RepoDigests}}'
```

A digest can help identify the exact image manifest or image index. For a stricter reproducibility exercise, use a verified digest in the Dockerfile's `FROM` reference.

Do not copy a digest from an unrelated example. Use the correct repository, platform, and digest for the image you intend to build.

### Important trade-off

Digest pinning improves reproducibility, but a pinned image does not automatically receive updates when new patches become available.

A good workflow deliberately reviews and updates base-image digests, rebuilds the application, and rescans the result.

---

## 10. Test runtime secret injection

Start the container:

```bash
docker run -d \
  --name task6-secure \
  --publish 127.0.0.1:5000:5000 \
  --env-file runtime.env \
  task6-api:1.0.0
```

Check the endpoints:

```bash
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/config
```

Expected behavior:

- `/` returns the application message and version.
- `/health` returns a successful response with `status: ok`.
- `/config` reports `api_token_configured: true` without revealing the token.

Inspect the container's user:

```bash
docker exec task6-secure id
```

Inspect the container configuration:

```bash
docker inspect task6-secure \
  --format 'Configured user={{.Config.User}}'
```

### Why publish on `127.0.0.1`?

The command publishes the container port on the host's loopback interface. This is appropriate for a local lab because the service does not need to be exposed on every host network interface.

### Important secret limitation

An environment file prevents the token from being baked into the image by this Dockerfile, but environment variables can still be visible to sufficiently privileged users through container inspection or process-related mechanisms.

For production deployments, use the secrets facility provided by your deployment platform or an external secrets manager.

---

## 11. Apply production-style runtime restrictions

Remove the previous test container:

```bash
docker rm -f task6-secure
```

Run it again with additional restrictions:

```bash
docker run -d \
  --name task6-secure \
  --publish 127.0.0.1:5000:5000 \
  --env-file runtime.env \
  --memory=128m \
  --cpus=0.5 \
  --pids-limit=100 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=16m \
  --cap-drop=ALL \
  --security-opt=no-new-privileges:true \
  task6-api:1.0.0
```

### Explanation of runtime options

| Option | Purpose |
|---|---|
| `--memory=128m` | Sets a memory limit |
| `--cpus=0.5` | Limits CPU availability to half a CPU's worth of quota |
| `--pids-limit=100` | Limits the number of processes and threads in the container's PID cgroup |
| `--read-only` | Makes the container's root filesystem read-only |
| `--tmpfs /tmp:...` | Provides temporary writable storage at `/tmp` |
| `--cap-drop=ALL` | Drops Linux capabilities from the container |
| `no-new-privileges:true` | Prevents processes from gaining additional privileges through mechanisms such as setuid |
| `127.0.0.1:5000:5000` | Publishes the app on the local host interface only |

Test the application again:

```bash
curl http://localhost:5000/
curl http://localhost:5000/health
curl http://localhost:5000/config
```

Inspect logs:

```bash
docker logs task6-secure
```

Inspect runtime settings:

```bash
docker inspect task6-secure \
  --format 'Memory={{.HostConfig.Memory}} CPUQuota={{.HostConfig.CpuQuota}} Readonly={{.HostConfig.ReadonlyRootfs}}'
```

Observe resource use:

```bash
docker stats task6-secure
```

### What did we learn?

Security hardening is a combination of image construction, identity, configuration, and runtime controls. Resource limits reduce the risk that a container consumes excessive host resources, but they do not replace vulnerability remediation or application security.

If an application fails under a read-only root filesystem, investigate which paths it needs to write to. Add only the required writable mounts instead of making the entire filesystem writable.

---

## 12. Image tagging and release identity

Create a second tag for the same local image:

```bash
docker tag task6-api:1.0.0 task6-api:1.0.1
```

Inspect the tags:

```bash
docker images task6-api
```

Record the image ID:

```bash
docker image inspect task6-api:1.0.1 \
  --format '{{.Id}}' \
  | tee reports/image-id.txt
```

A tag is a convenient name that can be moved to another image. An image ID identifies local image content, while a repository digest identifies content in a registry context.

A release workflow should build, test, scan, approve, and deploy the same artifact. Avoid rebuilding a supposedly approved release later from changed inputs without repeating the checks.

Optional advanced extension: use Docker Buildx to build with SBOM and provenance attestations, then verify that your chosen builder and image store retain the generated attestations. Availability and storage behavior depend on the Buildx driver and output method.

---

## 13. Compare the results

Use your actual results to complete this table.

| Metric | Baseline | Final image |
|---|---|---|
| Image tag | Record your baseline | `task6-api:1.0.0` |
| Image size | Measured size | Measured size |
| HIGH findings | Actual scan count | Actual scan count |
| CRITICAL findings | Actual scan count | Actual scan count |
| Runs as non-root | Yes/No | Yes/No |
| Secret baked into image | Yes/No | Yes/No |
| SBOM generated | Yes/No | Yes/No |
| Health endpoint works | Yes/No | Yes/No |
| Runtime restrictions tested | Yes/No | Yes/No |

Record the results:

```bash
{
  echo "=== IMAGE SIZE ==="
  docker images task6-api
  echo
  echo "=== IMAGE USER ==="
  docker image inspect task6-api:1.0.0 \
    --format '{{.Config.User}}'
  echo
  echo "=== HEALTH ENDPOINT ==="
  curl -sS http://localhost:5000/health
  echo
  echo "=== TOKEN CONFIGURATION ==="
  curl -sS http://localhost:5000/config
} | tee reports/results.txt
```

Do not claim that the image is smaller or has fewer vulnerabilities unless your measurements show that. Differences in scanner databases, base-image versions, and scan options can affect comparisons.

---

## 14. Troubleshooting

### Port 5000 is already in use

Check running and stopped containers:

```bash
docker ps
docker ps -a
```

Remove the old lab container if appropriate:

```bash
docker rm -f task6-secure
```

Alternatively, use another available host port, such as `127.0.0.1:5001:5000`.

### Trivy reports vulnerabilities

Review the affected packages and fixed versions. Update the relevant base image or dependency, rebuild, and rescan. Do not assume that changing a tag alone fixes every issue.

### The container fails with a read-only filesystem

Inspect the logs:

```bash
docker logs task6-secure
```

Identify the path the app needs to write to. Provide a narrowly scoped writable mount or tmpfs if required.

### The token is not configured

Verify the file exists:

```bash
ls -l runtime.env
```

Confirm that `--env-file runtime.env` was included in the `docker run` command.

### The image is not smaller

Inspect the image history and consider which files and packages remain in the final stage. Multi-stage builds do not automatically reduce every image's size.

### Trivy exits with a non-zero status

Read the output to determine whether the configured vulnerability gate failed or the scanner encountered an operational error.

---

## 15. Interview questions and answers

### Q1. What is a Docker image?

A Docker image is a packaged filesystem and configuration used to create containers. Images are built from layers and can be shared through registries.

### Q2. Why do we use multi-stage builds?

They separate build-time operations from the final runtime image. Only selected artifacts need to be copied into the final stage.

### Q3. What is the difference between a Docker image and a container?

An image is the packaged template. A container is a running or stopped instance created from an image.

### Q4. What does `docker history` show?

It displays the image's build history and layer-related information, helping identify which Dockerfile instructions contributed to the image.

### Q5. What is an SBOM?

A Software Bill of Materials is an inventory of the components in a software artifact. It helps teams investigate vulnerabilities and dependency exposure.

### Q6. Is an SBOM the same as a vulnerability scan?

No. An SBOM describes components. A vulnerability scanner evaluates components against available vulnerability information and detection rules.

### Q7. What is the difference between an image tag and a digest?

A tag is a human-readable reference that can change. A digest identifies specific content and helps ensure the intended artifact is selected.

### Q8. Why should we avoid floating tags such as `latest`?

They can point to different image content over time, making builds less predictable. Version tags or digest pinning make image selection more deliberate.

### Q9. Does digest pinning guarantee security?

No. It improves reproducibility, but the pinned image can still contain vulnerabilities. Updates and rescanning are still necessary.

### Q10. Why use a slim base image?

A slim base can contain fewer unnecessary packages, reducing image size and potentially reducing the attack surface. It does not guarantee that the image is secure.

### Q11. Why run containers as a non-root user?

It reduces the privileges available to the application if it is compromised. It is one layer of defense, not a complete security boundary.

### Q12. Why should secrets not be embedded in a Docker image?

Secrets in build instructions, image layers, or copied files may be exposed through image inspection, history, caches, or registries. Supply secrets through an appropriate runtime or build-secret mechanism.

### Q13. What is the difference between `.gitignore` and `.dockerignore`?

`.gitignore` controls which untracked files Git ignores. `.dockerignore` excludes files from the Docker build context. They serve different purposes.

### Q14. What does `--read-only` do?

It makes the container's root filesystem read-only. The application may still need explicitly mounted writable paths for temporary files or application data.

### Q15. What does `--cap-drop=ALL` do?

It removes Linux capabilities from the container. This reduces the privileges available to processes inside it, but the application must still be tested under the resulting restrictions.

### Q16. What is the purpose of `no-new-privileges`?

It prevents a process from gaining additional privileges through mechanisms such as setuid execution.

### Q17. What is the difference between `--memory` and `--cpus`?

`--memory` sets a memory limit. `--cpus` limits the CPU quota available to the container.

### Q18. What does `--pids-limit` control?

It limits the number of processes and threads in the container's PID cgroup, helping contain excessive process creation.

### Q19. What is a Trivy security gate?

It uses configured scan conditions and exit codes to make security findings capable of failing a build or release pipeline.

### Q20. Does a clean Trivy scan mean the image is completely secure?

No. A scan only identifies issues detectable by the scanner, its rules, and the available vulnerability data. Unknown vulnerabilities and application logic flaws may remain.

### Q21. Why does Dockerfile instruction order matter?

Docker caches layers. Copying dependency manifests before frequently changing source files can allow dependency-installation layers to be reused.

### Q22. What is image provenance?

Provenance records information about how an artifact was built, including relevant inputs and build details. It supports software supply-chain verification.

### Q23. Why should we deploy the same image that was scanned?

Rebuilding after a scan can produce different content if inputs have changed. Promoting the same verified artifact reduces the risk of deploying untested content.

### Q24. What should you do if a secret was already committed?

Treat it as exposed, revoke or rotate it, remove it from current code and relevant image layers, and review repository history and copies where appropriate. Deleting the visible line alone is insufficient.

---

## 16. Final submission checklist

- [ ] Application runs and `/health` returns a successful response.
- [ ] Docker image builds successfully.
- [ ] Image size and history have been recorded.
- [ ] Trivy image scan report is saved.
- [ ] SBOM has been generated.
- [ ] Application runs as a non-root user.
- [ ] Runtime token is not returned by the application.
- [ ] Local secret file is excluded from Git and the Docker build context.
- [ ] Resource limits and runtime restrictions have been tested.
- [ ] Actual image size and vulnerability results are documented.
- [ ] Image ID or digest information is recorded.
- [ ] Interview questions have been reviewed.

## 17. Cleanup

Stop and remove the container:

```bash
docker rm -f task6-secure
```

Remove only the lab images when you no longer need them:

```bash
docker image rm task6-api:1.0.0 task6-api:1.0.1
```

Keep the reports and notes for your submission. Do not use broad prune commands unless you understand which unrelated images, containers, networks, or volumes they may remove.

---

## Final outcome

At the end of Task 6, you should have more than a Docker image that merely builds. You should be able to explain what it contains, how it was scanned, how it was configured at runtime, which restrictions were applied, and what evidence supports your release decision.

The key DevOps lesson is that **image security and optimization are ongoing processes**: build deliberately, inspect, scan, test, record evidence, and update the image as its dependencies and base image evolve.
