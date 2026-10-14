# Day 13 — Docker Security & Optimization

**DevOps Winter Arc | Week 2: Docker | Learn • Scan • Fix • Prove**

## 1. Objective

The goal of this lab is to take an intentionally insecure Docker image, improve its security and size, scan it using Trivy, and demonstrate that the final container runs with fewer privileges and restricted resources.

This lab covers:

- Identifying risks in an insecure Docker image.
- Scanning images and configuration files using Trivy.
- Understanding Docker image layers and build history.
- Replacing a floating base image with a more specific, slim base image.
- Separating build and runtime dependencies with a multi-stage Dockerfile.
- Running the application as a non-root user.
- Avoiding hard-coded secrets in Docker images.
- Comparing image sizes and HIGH/CRITICAL vulnerability findings.
- Applying CPU, memory, PID, filesystem, and capability restrictions.
- Documenting the results and evidence.

> **Safety note:** `Dockerfile.bad` deliberately contains a fake token for training. Never put real credentials in a Dockerfile, image, source code, or Git repository.

---

## 2. Project structure

Create the following structure:

```text
day6-security/
├── app.py
├── requirements.txt
├── Dockerfile.bad
├── Dockerfile.good
├── .dockerignore
├── token.txt
├── README.md
└── reports/
    ├── before.json
    └── after.json
```

- `Dockerfile.bad`: intentionally insecure image used as a baseline.
- `Dockerfile.good`: improved image used for the final version.
- `app.py`: small Flask application for testing.
- `requirements.txt`: Python application dependency.
- `.dockerignore`: prevents unnecessary files from entering the build context.
- `token.txt`: local-only fake token file for the exercise.
- `reports/before.json`: Trivy report for the insecure image.
- `reports/after.json`: Trivy report for the improved image.

Create the directory and enter it:

```bash
mkdir -p ~/DevOps-Winter-Arc/Week2-Docker/day6-security/reports
cd ~/DevOps-Winter-Arc/Week2-Docker/day6-security
```

### Why this structure?

Keeping the insecure and improved Dockerfiles separate allows us to compare them without losing the original example. The `reports` directory stores scan evidence that can be included in the project submission.

---

## 3. Create the application

### `requirements.txt`

```text
flask==3.0.3
```

**Explanation:**

- `flask` is the Python web framework used by the application.
- `==3.0.3` pins the dependency to a specific version, making the dependency choice more reproducible.
- A pinned version does not guarantee that the dependency is vulnerability-free. We still need to scan it and update it when appropriate.

### `app.py`

```python
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify(
        message="Docker security lab",
        environment=os.getenv("APP_ENV", "dev")
    )

@app.get("/health")
def health():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

### Code explanation

| Code | Purpose |
|---|---|
| `import os` | Reads environment variables. |
| `Flask` | Creates the web application. |
| `@app.get("/")` | Defines the root endpoint. |
| `os.getenv("APP_ENV", "dev")` | Reads `APP_ENV`; uses `dev` if it is not set. |
| `jsonify(...)` | Returns a JSON response. |
| `@app.get("/health")` | Defines the health-check endpoint. |
| `return "ok", 200` | Returns a simple response with HTTP status `200`. |
| `app.run(...)` | Starts the development server on port `5000`. |
| `host="0.0.0.0"` | Allows connections to the app through the container's network interface. |

The application is intentionally simple so that the exercise focuses on container security rather than application complexity.

### Test endpoints later

- `/` should return a JSON message and the environment.
- `/health` should return `ok` with HTTP status `200`.

---

## 4. Section 1 — Understand the security risks

The original image is intentionally insecure. Each problem below represents a real category of Docker security risk.

| Risk | Why it matters | Remediation |
|---|---|---|
| Floating base image | `python:latest` can point to different versions over time. | Use a specific maintained tag and update deliberately. |
| Root execution | A compromised application has unnecessary privileges. | Create a dedicated user and set `USER`. |
| Hard-coded secret | Secrets may be exposed in image configuration, layers, history, or registries. | Inject secrets securely at runtime. |
| Large base and extra packages | More software increases image size and potential attack surface. | Use a slim image and omit unnecessary packages. |
| Unscanned dependencies | Known vulnerabilities may go unnoticed. | Scan, review, fix, rebuild, and rescan. |
| Unrestricted runtime | The process may consume excessive resources or modify files. | Apply resource limits and runtime hardening. |

### Important concepts

**Attack surface:** The software, interfaces, permissions, and components that could potentially be exploited.

**Image layer:** A filesystem change recorded as part of an image. Removing a secret in a later layer does not necessarily remove it from earlier layers.

**Non-root user:** A user that does not have UID `0`. Running as non-root reduces unnecessary privileges but does not eliminate every security risk.

**Runtime hardening:** Restricting what a container can do after it starts, including limiting resources, dropping capabilities, and restricting filesystem writes.

---

## 5. Section 2 — Build and scan the insecure image

### Step 1: Create `Dockerfile.bad`

```dockerfile
FROM python:latest
ENV API_TOKEN=abc123-super-secret
RUN apt-get update && apt-get install -y build-essential git curl vim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD python app.py
```

### Line-by-line explanation

**`FROM python:latest`**

Uses a floating Python base image. Its contents can change over time, making builds less predictable.

**`ENV API_TOKEN=abc123-super-secret`**

Stores a fake token in the image's environment configuration. This demonstrates why secrets should not be baked into images.

**`RUN apt-get update && apt-get install -y ...`**

Installs build tools and utilities. They are unnecessary for this small application's runtime and increase the image's footprint.

**`WORKDIR /app`**

Sets `/app` as the working directory for subsequent instructions.

**`COPY . .`**

Copies the build context into the image. Without a suitable `.dockerignore`, unnecessary files could be copied too.

**`RUN pip install -r requirements.txt`**

Installs the Python dependencies.

**`CMD python app.py`**

Starts the application. This is shell-form `CMD`; the improved Dockerfile uses exec form instead.

### Step 2: Create `.dockerignore`

```text
.git
.env
token.txt
reports/
__pycache__/
*.pyc
.venv/
```

**Why use `.dockerignore`?**

It prevents matching files from being included in the Docker build context. This helps reduce unnecessary build data and avoids accidentally copying local files.

Important: `.dockerignore` does not make a secret safe if the Dockerfile explicitly writes it into the image. It also does not erase secrets from images already built.

### Step 3: Build the insecure image

```bash
docker build -f Dockerfile.bad -t my-app:bad .
```

Explanation:

- `docker build` builds an image.
- `-f Dockerfile.bad` selects the intentionally insecure Dockerfile.
- `-t my-app:bad` names and tags the image.
- `.` supplies the current directory as the build context.

### Step 4: Record the image size

```bash
docker images my-app
```

Record the size of `my-app:bad` in the comparison table later.

Image sizes vary by platform, base-image version, and image contents. Use your own output.

### Step 5: Inspect the image history

```bash
docker history --no-trunc my-app:bad
```

This displays image-layer history, including commands used to build the image. `--no-trunc` requests untruncated output.

Inspect the image configuration too:

```bash
docker image inspect my-app:bad --format '{{json .Config.Env}}'
```

The environment configuration can reveal the deliberately embedded fake token. This demonstrates why secrets must not be stored in image configuration.

### Step 6: Install and verify Trivy

Verify that Trivy is available:

```bash
trivy --version
```

Trivy is a security scanner that can identify known vulnerabilities in container images and check supported configuration files for misconfigurations.

If the command is not found, install Trivy using its official installation instructions for your operating system before continuing.

### Step 7: Scan and save the before report

```bash
mkdir -p reports

trivy image --severity HIGH,CRITICAL \
  -f json -o reports/before.json my-app:bad
```

Display the findings in the terminal:

```bash
trivy image --severity HIGH,CRITICAL my-app:bad
```

Scan supported configuration files:

```bash
trivy config .
```

#### What do these Trivy options mean?

| Option | Explanation |
|---|---|
| `image` | Scan a container image. |
| `--severity HIGH,CRITICAL` | Focus the displayed findings on these severities. |
| `-f json` | Select JSON output. |
| `-o reports/before.json` | Write the report to the specified file. |
| `config` | Scan supported configuration files for misconfigurations. |

The first scan may download vulnerability data and take some time.

A scan report is evidence, not a guarantee that the image is secure. Review findings, record the scan date and Trivy version, and document any accepted exceptions.

---

## 6. Section 3 — Fix, shrink, and rescan

### Step 8: Create `Dockerfile.good`

```dockerfile
FROM python:3.12-slim AS build

WORKDIR /w
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
RUN useradd -r -u 10001 app
WORKDIR /app
COPY --from=build /install /usr/local
COPY --chown=app:app app.py .
USER app
EXPOSE 5000
CMD ["python", "app.py"]
```

### Line-by-line explanation

**`FROM python:3.12-slim AS build`**

Starts the dependency-installation stage using a more specific, slim Python image. `AS build` gives the stage a name.

**`WORKDIR /w`**

Sets the working directory for the build stage.

**`COPY requirements.txt .`**

Copies only the dependency file first. This keeps the dependency-installation step independent of ordinary application source changes.

**`RUN pip install --no-cache-dir --prefix=/install -r requirements.txt`**

Installs dependencies under `/install`. The `--no-cache-dir` option avoids retaining pip's download cache.

**`FROM python:3.12-slim`**

Starts a fresh runtime stage. Files and tools from the build stage are not automatically included in this stage.

**`RUN useradd -r -u 10001 app`**

Creates a system user named `app` with UID `10001`.

**`WORKDIR /app`**

Sets the application's working directory.

**`COPY --from=build /install /usr/local`**

Copies the installed dependencies from the build stage into the runtime image.

**`COPY --chown=app:app app.py .`**

Copies the application file and assigns ownership to the `app` user and group.

**`USER app`**

Runs the application as the non-root user instead of root.

**`EXPOSE 5000`**

Documents the port used by the application. It does not publish that port on the host by itself.

**`CMD ["python", "app.py"]`**

Uses exec-form command syntax to run Python as the container's main process.

### What improved?

- Replaced the floating `python:latest` reference with `python:3.12-slim`.
- Separated dependency installation from the runtime stage.
- Left unnecessary build tools out of the runtime image.
- Created a dedicated non-root user.
- Removed the hard-coded token from the improved Dockerfile.
- Used exec-form `CMD`.
- Avoided retaining pip's download cache.

The exact image-size reduction depends on your environment; measure it rather than assuming a particular number.

### Step 9: Create a local fake token

```bash
printf '%s' 'training-token-only' > token.txt
chmod 600 token.txt
```

The first command creates a fake local token file. The second restricts access to the file's owner.

The `.dockerignore` file excludes `token.txt` from the build context. The improved Dockerfile does not copy or use this token.

**Real secret-handling rule:** Do not bake secrets into `ENV`, `ARG`, source code, or image layers. Supply runtime secrets through an appropriate secret mechanism. For production, use a secrets manager or platform-supported secret facility.

### Step 10: Build the improved image

```bash
docker build --pull --no-cache -f Dockerfile.good -t my-app:v2 .
```

- `--pull` checks for an updated base image.
- `--no-cache` rebuilds without using cached build layers.
- `-f Dockerfile.good` selects the improved Dockerfile.
- `-t my-app:v2` tags the image as version 2.

Inspect its size:

```bash
docker images my-app
```

Inspect the build history:

```bash
docker history --no-trunc my-app:v2
```

### Step 11: Scan the improved image

```bash
trivy image --severity HIGH,CRITICAL \
  -f json -o reports/after.json my-app:v2
```

Display the findings:

```bash
trivy image --severity HIGH,CRITICAL my-app:v2
```

Scan configuration files again:

```bash
trivy config .
```

Test the assignment's vulnerability policy:

```bash
trivy image --exit-code 1 --severity HIGH,CRITICAL \
  --ignore-unfixed my-app:v2
```

**Explanation:**

- `--exit-code 1` requests a non-zero exit status if findings match the selected policy.
- `--severity HIGH,CRITICAL` selects the severities being evaluated.
- `--ignore-unfixed` excludes findings for which Trivy reports no available fix.

If the command exits non-zero, review the findings and remediate what you can. Do not hide vulnerabilities just to make the scan appear successful.

### Step 12: Compare before and after

Fill in this table using your actual command output and reports.

| Measure | Before | After |
|---|---|---|
| Image tag | `my-app:bad` | `my-app:v2` |
| Base image | `python:latest` | `python:3.12-slim` |
| Image size | Record from Docker | Record from Docker |
| HIGH findings | Count from `before.json` | Count from `after.json` |
| CRITICAL findings | Count from `before.json` | Count from `after.json` |
| Runtime user | Inspect actual image | Verify UID `10001` |
| Hard-coded token | Present in bad image configuration | Removed from improved Dockerfile |
| Extra build tools | Installed in bad image | Not installed by the runtime stage |

The number of findings may not decrease to zero. A slim image can still contain vulnerable packages, and a specific version can still require updates. Explain remaining findings in your submission.

---

## 7. Section 4 — Run with restrictions

The objective is to prove that the improved image runs as a non-root user and under runtime restrictions.

### Step 13: Confirm non-root execution

Run the image's configured user command:

```bash
docker run --rm --entrypoint id my-app:v2
```

Inspect the configured image user:

```bash
docker image inspect my-app:v2 --format '{{.Config.User}}'
```

Expected: the process reports UID `10001`, and the configured user is `app`, rather than UID `0`.

### Step 14: Start the hardened container

Make sure host port `5000` is available, then run:

```bash
docker run -d \
  --name my-app-secure \
  -p 5000:5000 \
  -e APP_ENV=production \
  --memory=128m \
  --cpus=0.5 \
  --pids-limit=100 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop=ALL \
  --security-opt=no-new-privileges:true \
  my-app:v2
```

### Explanation of every important option

| Option | Meaning |
|---|---|
| `-d` | Runs the container in the background. |
| `--name my-app-secure` | Gives the container a recognizable name. |
| `-p 5000:5000` | Maps host port `5000` to container port `5000`. |
| `-e APP_ENV=production` | Supplies the environment setting at runtime. |
| `--memory=128m` | Sets a 128 MiB memory limit. |
| `--cpus=0.5` | Limits the container to approximately half a CPU. |
| `--pids-limit=100` | Limits the number of processes and threads. |
| `--read-only` | Makes the container's root filesystem read-only. |
| `--tmpfs /tmp:rw,noexec,nosuid,size=64m` | Provides temporary writable storage at `/tmp`, with execution and set-user-ID restrictions and a size limit. |
| `--cap-drop=ALL` | Drops Linux capabilities from the container. |
| `--security-opt=no-new-privileges:true` | Prevents processes from gaining additional privileges through supported privilege-escalation mechanisms. |
| `my-app:v2` | Selects the improved image to run. |

The application does not need to write to its root filesystem for this lab. If an application needs writable paths, provide narrowly scoped writable mounts rather than making the whole filesystem writable.

### Step 15: Test the application

```bash
docker ps
docker logs my-app-secure
curl http://localhost:5000/
curl http://localhost:5000/health
```

Expected results:

- The container is running.
- The root endpoint returns JSON containing the message and environment.
- The environment is `production`.
- `/health` returns `ok` with HTTP status `200`.

If port `5000` is already occupied, publish host port `5001` instead:

```bash
docker run -d \
  --name my-app-secure \
  -p 5001:5000 \
  -e APP_ENV=production \
  --memory=128m \
  --cpus=0.5 \
  --pids-limit=100 \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop=ALL \
  --security-opt=no-new-privileges:true \
  my-app:v2
```

Then test `http://localhost:5001/` and `http://localhost:5001/health`.

If you already created a failed container named `my-app-secure`, remove it before recreating it:

```bash
docker rm -f my-app-secure
```

Only do this if that container is the one from this lab.

### Step 16: Verify the runtime settings

```bash
docker inspect my-app-secure --format \
'User={{.Config.User}} ReadOnly={{.HostConfig.ReadonlyRootfs}} Memory={{.HostConfig.Memory}} NanoCPUs={{.HostConfig.NanoCpus}} PidsLimit={{.HostConfig.PidsLimit}}'
```

Check dropped capabilities and security options:

```bash
docker inspect my-app-secure --format \
'CapDrop={{json .HostConfig.CapDrop}} SecurityOpt={{json .HostConfig.SecurityOpt}}'
```

These commands inspect the configuration Docker applied to the running container. They provide evidence that restrictions were configured; they do not prove the application is completely secure.

### Step 17: Optional policy check in automation

The following command can be used in a script or CI pipeline:

```bash
trivy image --exit-code 1 --severity HIGH,CRITICAL \
  --ignore-unfixed my-app:v2
```

If the selected policy finds applicable issues, the non-zero exit status can stop a pipeline. A production pipeline should define its policy deliberately and review exceptions rather than blindly ignoring findings.

---

## 8. Troubleshooting

| Problem | What to check |
|---|---|
| `trivy: command not found` | Install Trivy and verify with `trivy --version`. |
| Docker image not found | Run `docker images my-app` and confirm the tag. |
| Build fails while installing dependencies | Inspect network access, Python version compatibility, and pip error messages. |
| Container exits immediately | Check `docker ps -a` and `docker logs my-app-secure`. |
| Port already allocated | Choose a different host port, such as `5001:5000`. |
| Permission denied | Verify the user and ownership of application files and writable directories. |
| Application is unreachable | Check container status, port mapping, and the app's `0.0.0.0` listener. |
| Scan reports vulnerabilities after remediation | Review package names, versions, available fixes, and whether the finding belongs to the base image or application dependency. |
| `after.json` is missing | Rerun the Trivy command and check the `reports` directory. |
| Read-only filesystem causes an error | Identify which path needs writing and provide only that path with a suitable writable mount. |

---

## 9. Important security lessons

### Why is `python:latest` risky?

Its tag can move to a different version over time. Builds may change unexpectedly, so a specific maintained tag gives more predictable results. For stronger reproducibility, production builds can pin an image digest and deliberately update it.

### Why use a multi-stage build?

The build stage installs dependencies, while the runtime stage starts from a clean base and copies only what is needed. This prevents unnecessary build-stage contents from being carried into the runtime image.

### Why is a non-root user important?

If an application is compromised, running without root privileges limits the privileges available to that process. Non-root execution is one layer of defense, not a replacement for other controls.

### Why should secrets not be in a Dockerfile?

Image configuration, build history, layers, caches, and registries can expose values. Removing a secret from the latest Dockerfile does not erase it from old images. Rotate any real exposed credential and rebuild cleanly.

### What does Trivy do?

Trivy identifies known vulnerabilities in container images and can inspect supported configuration files for misconfigurations. Results depend on the scanner database, image contents, and selected policy.

### Why use `--read-only` and `--cap-drop=ALL`?

A read-only root filesystem limits filesystem modifications. Dropping capabilities reduces the privileged operations available to a process. Add back only what the application genuinely requires.

### What do CPU and memory limits achieve?

They constrain resource consumption under the configured runtime. These limits can help prevent a container from consuming all host resources, but they are not a complete availability or security strategy.

---

## 10. Interview questions and answers

### Q1. How do you secure a Docker image?

Use a maintained and appropriately pinned base image, remove unnecessary packages, scan regularly, avoid embedded secrets, run as non-root, use multi-stage builds where appropriate, and apply runtime restrictions.

### Q2. What is the difference between an image and a container?

An image is the packaged template containing the application and its dependencies. A container is a running or stopped instance created from that image, with its own runtime state.

### Q3. What is a Docker image layer?

A layer represents filesystem changes recorded during image construction. Layers can be shared between images, and sensitive content in an earlier layer may remain accessible even if a later layer removes it.

### Q4. Why is `python:latest` discouraged for reproducible builds?

The tag can point to different image versions at different times. A specific maintained tag or digest makes the chosen base more predictable.

### Q5. What is a multi-stage Docker build?

A build that uses multiple `FROM` stages. The final stage can copy selected artifacts from earlier stages while leaving unnecessary build tools and files behind.

### Q6. What does `USER app` do?

It configures subsequent container instructions and the default runtime process to use the named user, rather than root.

### Q7. Why is running as root dangerous?

A compromised application may have more privileges than it needs. Non-root execution reduces those privileges and limits the potential impact of some attacks.

### Q8. What is the purpose of `.dockerignore`?

It excludes matching files from the Docker build context. This can reduce build overhead and prevent unwanted local files from being copied, but it cannot remove a secret that the Dockerfile explicitly embeds.

### Q9. How should secrets be handled in Docker?

Do not put them in Dockerfiles, source code, `ENV`, or image layers. Supply them through a suitable runtime secret mechanism or secrets manager. For build-time secrets, use a supported secret mechanism rather than baking values into layers.

### Q10. Why is deleting a secret from the current Dockerfile not enough?

The secret may remain in older image layers, image history, caches, or registries. If a real secret was exposed, rotate it and rebuild cleanly; also address any copies that were published.

### Q11. What does Trivy scan?

It can identify known vulnerabilities in container images and scan supported configuration files for misconfigurations.

### Q12. What do HIGH and CRITICAL mean in a Trivy command?

They are severity categories used to filter findings or apply a policy. A severity filter changes which findings are selected; it does not fix them.

### Q13. What does `--exit-code 1` do in a scan?

It requests a non-zero exit status when findings match the selected policy. This can be used to make a CI pipeline fail when its security criteria are not met.

### Q14. What does `--ignore-unfixed` do?

It excludes findings for which Trivy reports no available fix from that scan's selected results. It does not make those vulnerabilities harmless, so they should still be reviewed and documented.

### Q15. Why use a slim base image?

It generally reduces the number of installed packages and image size, which can reduce attack surface and patching burden. A slim image still needs regular updates and scanning.

### Q16. What does `--read-only` do?

It makes the container's root filesystem read-only. Applications that need temporary writes may require explicitly mounted writable paths.

### Q17. What does `--cap-drop=ALL` do?

It drops Linux capabilities from the container, reducing the privileged operations available to its processes. If an application needs a capability, assess and grant only the minimum required.

### Q18. What does `no-new-privileges` do?

It prevents processes from gaining additional privileges through supported privilege-escalation mechanisms. It complements, rather than replaces, other security controls.

### Q19. What do `--memory` and `--cpus` do?

They set memory and CPU limits for the container. These restrictions help control resource consumption, although actual enforcement and behavior depend on the container runtime and host configuration.

### Q20. What is the difference between `EXPOSE` and `-p`?

`EXPOSE` documents the application's container port in the image. `-p` publishes a port from the host to the container so that clients can reach the service through that mapping.

### Q21. Why use exec-form `CMD`?

Exec form runs the specified executable directly as the container's main process, helping signal handling and process behavior compared with shell-form commands.

### Q22. Does a clean Trivy scan guarantee a secure image?

No. It means the scan did not report findings matching that scan's database and policy. Undiscovered vulnerabilities, application logic flaws, configuration problems, and other risks can remain.

### Q23. Why might the improved image still have vulnerabilities?

The base image or pinned dependencies may still contain known issues. Review the report, update affected components when appropriate, rebuild, and scan again.

### Q24. Why is comparing image size useful?

It provides evidence of the optimization achieved. Smaller images often contain fewer unnecessary components, but image size alone does not establish that an image is secure.

---

## 11. Evidence and submission checklist

### Build and scan evidence

- [ ] `Dockerfile.bad` and `Dockerfile.good` are committed.
- [ ] `app.py` and `requirements.txt` are included.
- [ ] `reports/before.json` contains the before scan.
- [ ] `reports/after.json` contains the after scan.
- [ ] Actual image sizes are recorded.
- [ ] HIGH and CRITICAL counts are recorded from the reports.
- [ ] Remaining findings and accepted exceptions are explained.
- [ ] `docker history --no-trunc` has been reviewed.

### Runtime security evidence

- [ ] The improved image runs as UID `10001`.
- [ ] The hard-coded token is absent from the improved Dockerfile.
- [ ] The application responds at `/` and `/health`.
- [ ] The container uses a read-only root filesystem.
- [ ] CPU, memory, and PID limits are configured.
- [ ] Linux capabilities are dropped.
- [ ] `no-new-privileges` is configured.
- [ ] Runtime settings have been checked with `docker inspect`.

### Git hygiene

- [ ] `.dockerignore` is present.
- [ ] `.env` and other local secret files are excluded where applicable.
- [ ] The fake token is not committed.
- [ ] No real credentials have been placed in Dockerfiles, reports, or source code.
- [ ] The README explains the remediations and their purpose.

---

## 12. Cleanup

Stop and remove the test container:

```bash
docker rm -f my-app-secure
```

The `-f` option forces removal, including stopping the container if it is running.

Remove the lab images only if you no longer need them:

```bash
docker image rm my-app:bad my-app:v2
```

Keep the JSON reports and project files for your submission. Do not delete evidence you still need.

---

## 13. Final conclusion

In this lab, the insecure Docker image was used as a baseline. The improved image uses a more specific slim base, separates dependency installation from the runtime stage, runs as a non-root user, and removes the hard-coded token pattern. Trivy reports and Docker inspection commands provide evidence of the changes, while runtime options limit resources and privileges.

The final result should be evaluated using actual image sizes, scan reports, and runtime verification from your machine. A smaller image and fewer reported vulnerabilities are useful improvements, but neither alone proves complete security.
