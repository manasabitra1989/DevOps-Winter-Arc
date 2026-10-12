# Docker Week 2 — Task 3: Multi-Stage Builds

## 1. Objective

The objective of this task is to understand Docker multi-stage builds and learn how to create production-style Docker images.

In this lab, we will:

- Understand build stages and runtime stages.
- Build a static website using Node.js.
- Create a single-stage Docker image.
- Create a multi-stage Docker image using Node.js and Nginx.
- Run and test both containers.
- Compare Docker image sizes.
- Understand `FROM`, `AS`, and `COPY --from`.
- Inspect images, containers, and logs.
- Learn why production images should avoid unnecessary build tools.
- Troubleshoot common Docker build and runtime problems.

## 2. Project Overview

We will create a simple static website with HTML and CSS.

The single-stage image uses Node.js to build and serve the website. The multi-stage image uses Node.js to build the website and Nginx to serve the generated files.

### Single-stage build

```text
Source Files
     |
     v
Node.js Image
     |
     v
Build Website
     |
     v
Node.js Serves Website
```

The image contains Node.js, application source files, the build script, and generated website files.

### Multi-stage build

```text
             BUILD STAGE
          Node.js Image
                |
                v
          Build Website
                |
                v
          Generated Files
                |
      COPY --from=builder
                |
                v
             RUNTIME STAGE
             Nginx Image
                |
                v
          Serve Static Website
```

The final image contains Nginx and the generated website files. The Node.js builder and source files are not copied into the final image.

**Expected result:** both containers serve the same website, but the multi-stage image should generally be smaller because it uses Nginx rather than Node.js as its runtime.

## 3. Prerequisites

- Docker installed and running.
- Ubuntu terminal through WSL2 or a Linux environment.
- Basic understanding of Docker images and containers.
- Familiarity with basic terminal commands.

Verify Docker:

```bash
docker --version
docker info
```

If `docker info` fails, check that Docker Desktop is running and that WSL integration is enabled, if applicable.

## 4. Create the Project Structure

Navigate to your Week 2 Docker directory:

```bash
cd ~/DevOps-Winter-Arc/Week2-Docker
```

Create the project:

```bash
mkdir -p Task3-Multi_Stage_Builds/src
mkdir -p Task3-Multi_Stage_Builds/evidence

cd Task3-Multi_Stage_Builds
```

Create the files:

```bash
touch package.json
touch build.js
touch server.js
touch src/index.html
touch src/styles.css
touch Dockerfile.single
touch Dockerfile
touch .dockerignore
touch README.md
```

Verify the structure:

```bash
find . -maxdepth 2 -type f | sort
```

Expected structure:

```text
Task3-Multi_Stage_Builds/
├── .dockerignore
├── Dockerfile
├── Dockerfile.single
├── README.md
├── build.js
├── package.json
├── server.js
├── src/
│   ├── index.html
│   └── styles.css
└── evidence/
```

## 5. Create the Application Files

### 5.1 `package.json`

This file defines basic project metadata and the build command.

```json
{
  "name": "task3-static-site",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "build": "node build.js"
  }
}
```

No third-party npm packages are required for this lab.

### 5.2 `src/index.html`

This is the main webpage.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Docker Multi-Stage Build</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <main class="container">
    <h1>Docker Multi-Stage Builds</h1>
    <p>This website was built using Node.js and served by Nginx.</p>
    <p class="success">Application status: Running</p>
    <p>Task: Docker Week 2 — Task 3</p>
  </main>
</body>
</html>
```

### 5.3 `src/styles.css`

This file styles the webpage.

```css
body {
  margin: 0;
  font-family: Arial, sans-serif;
  background: #f1f5f9;
  color: #1e293b;
}

.container {
  max-width: 700px;
  margin: 100px auto;
  padding: 32px;
  background: white;
  border-radius: 12px;
  text-align: center;
}

.success {
  color: #15803d;
  font-weight: bold;
}
```

### 5.4 `build.js`

This script copies the website source files into a `dist/` directory.

```javascript
const fs = require("fs");
const path = require("path");

const source = path.join(__dirname, "src");
const output = path.join(__dirname, "dist");

fs.rmSync(output, { recursive: true, force: true });
fs.mkdirSync(output, { recursive: true });
fs.cpSync(source, output, { recursive: true });

console.log("Build complete: website files copied to dist/");
```

**What happens when it runs?**

1. It locates the `src/` directory.
2. It creates a fresh `dist/` directory.
3. It copies the HTML and CSS files into `dist/`.
4. It prints a completion message.

The `dist/` directory represents the generated production website.

### 5.5 `server.js`

The single-stage image uses this small Node.js server to serve the generated website.

```javascript
const http = require("http");
const fs = require("fs");
const path = require("path");

const root = path.join(__dirname, "dist");

const types = {
  ".html": "text/html",
  ".css": "text/css"
};

http.createServer((req, res) => {
  const pathname = new URL(req.url, "http://localhost").pathname;
  const requested = pathname === "/" ? "index.html" : pathname.slice(1);
  const file = path.resolve(root, requested);

  if (file !== root && !file.startsWith(root + path.sep)) {
    res.writeHead(403);
    return res.end("Forbidden");
  }

  fs.readFile(file, (err, data) => {
    if (err) {
      res.writeHead(404);
      return res.end("Not Found");
    }

    res.writeHead(200, {
      "Content-Type": types[path.extname(file)] || "application/octet-stream"
    });
    res.end(data);
  });
}).listen(8080, "0.0.0.0", () => {
  console.log("Server listening on port 8080");
});
```

The server listens on port `8080` inside the container.

### 5.6 `.dockerignore`

This file prevents unnecessary local files from being sent in the Docker build context.

```text
.git
node_modules
dist
evidence
*.log
```

**Why exclude `dist/`?**

The image should generate the website during the Docker build. Excluding a local `dist/` directory avoids accidentally using stale output from an earlier build.

## 6. Task A — Build a Single-Stage Image

### 6.1 Create `Dockerfile.single`

```dockerfile
FROM node:22-alpine

WORKDIR /app

COPY package.json build.js server.js ./
COPY src/ ./src/

RUN npm run build

EXPOSE 8080

CMD ["node", "server.js"]
```

### 6.2 Understand each instruction

| Instruction | Purpose |
|---|---|
| `FROM node:22-alpine` | Uses a Node.js image based on Alpine Linux. |
| `WORKDIR /app` | Sets the working directory inside the image. |
| `COPY package.json build.js server.js ./` | Copies the project configuration and scripts. |
| `COPY src/ ./src/` | Copies the website source files. |
| `RUN npm run build` | Generates the production website during the image build. |
| `EXPOSE 8080` | Documents the port used by the Node.js server. |
| `CMD ["node", "server.js"]` | Starts the web server when a container starts. |

This is called a single-stage build because it uses one `FROM` instruction for the image's build and runtime environment.

### 6.3 Build the image

```bash
docker build -f Dockerfile.single -t task3-single:v1 .
```

Explanation:

- `-f Dockerfile.single` selects the single-stage Dockerfile.
- `-t task3-single:v1` names the image and gives it a tag.
- `.` uses the current directory as the build context.

Verify:

```bash
docker images
```

### 6.4 Run the container

```bash
docker run -d \
  --name task3-single \
  -p 8081:8080 \
  task3-single:v1
```

Port mapping:

- Host port: `8081`
- Container port: `8080`

Open this address in your browser:

`http://localhost:8081`

Or test from the terminal:

```bash
curl http://localhost:8081/
```

You should receive the HTML for the website.

### 6.5 Inspect the container

```bash
docker ps
docker logs task3-single
docker inspect task3-single
```

Check the running process:

```bash
docker top task3-single
```

You should see the Node.js server running inside the container.

## 7. Task B — Build a Multi-Stage Image

### 7.1 Create `Dockerfile`

```dockerfile
# Stage 1: Build the website
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json build.js ./
COPY src/ ./src/

RUN npm run build


# Stage 2: Serve the website
FROM nginx:alpine

COPY --from=builder /app/dist/ /usr/share/nginx/html/

EXPOSE 80
```

### 7.2 Understand the multi-stage instructions

#### `FROM node:22-alpine AS builder`

Starts the first stage and names it `builder`.

The stage has Node.js available to run the website build script.

#### `RUN npm run build`

Generates the production website in:

```text
/app/dist/
```

#### `FROM nginx:alpine`

Starts a fresh stage using the Nginx image.

The final image is based on Nginx, not on the Node.js builder image.

#### `COPY --from=builder`

```dockerfile
COPY --from=builder /app/dist/ /usr/share/nginx/html/
```

This copies the generated website from the builder stage into Nginx's default website directory.

Only the selected files are copied. The builder's Node.js installation and source files do not become part of the final image.

#### `EXPOSE 80`

Documents that Nginx serves HTTP on port `80` inside the container.

### 7.3 Build the multi-stage image

```bash
docker build -t task3-multi:v1 .
```

Docker executes the build stage and then creates the final Nginx-based image.

Verify:

```bash
docker images
```

### 7.4 Run the multi-stage container

```bash
docker run -d \
  --name task3-multi \
  -p 8082:80 \
  task3-multi:v1
```

Open:

`http://localhost:8082`

Test:

```bash
curl http://localhost:8082/
```

The multi-stage version should display the same webpage as the single-stage version.

### 7.5 Inspect the final files

```bash
docker exec task3-multi ls -l /usr/share/nginx/html
```

Expected files include:

```text
index.html
styles.css
```

The final image does not need `build.js`, `server.js`, or Node.js to serve this static website.

## 8. Task C — Compare Image Sizes

### 8.1 List both images

```bash
docker images task3-single task3-multi
```

### 8.2 Display the exact reported sizes in bytes

```bash
docker image inspect task3-single:v1 \
  --format='Single-stage: {{.Size}} bytes'

docker image inspect task3-multi:v1 \
  --format='Multi-stage: {{.Size}} bytes'
```

Record the results:

| Image | Measured size |
|---|---|
| `task3-single:v1` | Fill in your result |
| `task3-multi:v1` | Fill in your result |

Do not enter guessed sizes. Record the values returned by your own Docker installation.

### 8.3 Why can the multi-stage image be smaller?

The single-stage image uses Node.js as its runtime. The multi-stage image uses Nginx to serve the generated static files.

The final multi-stage image does not contain the Node.js builder environment.

For this specific lab, the comparison demonstrates both multi-stage copying and a change in runtime. It is not a perfectly controlled comparison of the same runtime image, because the single-stage and multi-stage images use different base images and servers.

**Production takeaway:** use multi-stage builds to keep build tools and other unnecessary files out of the final image. The actual size savings depend on the application, dependencies, base images, and runtime requirements.

## 9. Task D — Inspect the Images and Containers

### List running containers

```bash
docker ps
```

### List all containers, including stopped ones

```bash
docker ps -a
```

### Inspect image configuration

```bash
docker image inspect task3-single:v1
docker image inspect task3-multi:v1
```

### Inspect container logs

```bash
docker logs task3-single
docker logs task3-multi
```

Nginx normally writes access and error logs to its standard output and standard error, which Docker exposes through `docker logs`.

### Inspect container ports

```bash
docker port task3-single
docker port task3-multi
```

Expected mappings are equivalent to:

```text
task3-single: 8081 -> 8080
task3-multi:  8082 -> 80
```

The exact display format can vary.

## 10. Task E — Modify and Rebuild

### 10.1 Change the website

Edit `src/index.html` and change the heading to:

```html
<h1>My Production Website</h1>
```

Save the file.

### 10.2 Rebuild the multi-stage image

```bash
docker build -t task3-multi:v2 .
```

Docker creates a new image tag containing the updated website.

### 10.3 Replace the old container

```bash
docker rm -f task3-multi
```

Start a new container:

```bash
docker run -d \
  --name task3-multi \
  -p 8082:80 \
  task3-multi:v2
```

### 10.4 Verify the change

```bash
curl http://localhost:8082/
```

Confirm that the new heading appears in the returned HTML. Refresh the browser if necessary.

Remember: rebuilding an image does not automatically replace an existing container. Create a new container from the updated image.

## 11. Task F — Observe Docker Build Cache

Build the multi-stage image again without changing the source:

```bash
docker build --progress=plain -t task3-multi:v3 .
```

Inspect the build output. Docker may reuse cached layers when the relevant instructions and their inputs have not changed.

Now change `src/index.html` and build again:

```bash
docker build --progress=plain -t task3-multi:v4 .
```

Observe which steps run again.

The exact output depends on Docker's version, cache availability, and whether the relevant layers have changed.

**Important:** build cache improves rebuild speed; it does not mean Docker skips necessary work after relevant inputs change.

## 12. Troubleshooting

### Problem 1: Docker daemon is not running

**Possible error:**

```text
Cannot connect to the Docker daemon
```

**Solution:**

- If using Docker Desktop with WSL2, start Docker Desktop.
- Verify that WSL integration is enabled for your Ubuntu distribution.
- Run:

```bash
docker info
```

### Problem 2: Port is already allocated

**Possible error:**

```text
Bind for 0.0.0.0:8082 failed: port is already allocated
```

**Solution:** choose another unused host port:

```bash
docker run -d --name task3-multi \
  -p 8083:80 task3-multi:v1
```

Then test `http://localhost:8083`.

### Problem 3: Container name already exists

**Possible error:**

```text
The container name "/task3-multi" is already in use
```

**Solution:**

```bash
docker ps -a
docker rm -f task3-multi
```

Run the container again afterward.

### Problem 4: Website returns 404

Check that the builder creates `dist/index.html` and that the Dockerfile copies the directory to Nginx's document root.

```bash
docker exec task3-multi ls -l /usr/share/nginx/html
docker logs task3-multi
```

Rebuild if the output files are missing.

### Problem 5: The old website still appears

**Cause:** the existing container is still using the old image.

**Solution:**

```bash
docker build -t task3-multi:v2 .
docker rm -f task3-multi
docker run -d --name task3-multi \
  -p 8082:80 task3-multi:v2
```

Refresh the browser and test using `curl`.

### Problem 6: `COPY --from=builder` fails

Check:

- The first stage is named exactly `builder`.
- The build command generates `/app/dist/`.
- The source path in `COPY --from=builder` matches the generated directory.

Review the build output:

```bash
docker build --progress=plain -t task3-multi:v1 .
```

### Problem 7: `npm run build` fails

Check that `package.json` includes the `build` script and that `build.js` exists.

```bash
cat package.json
ls -l build.js src/
```

The app uses Node.js built-in modules, so no third-party npm installation is needed.

### Problem 8: Image size is not what you expected

Image sizes vary by platform, base-image version, and Docker's image reporting. Compare the actual values reported by `docker image inspect`, and make sure both images have finished building.

Do not assume that every multi-stage build will automatically produce a smaller image. Its benefit depends on what is excluded from the final stage.

### Problem 9: A container exits immediately

Check its status and logs:

```bash
docker ps -a
docker logs task3-single
docker logs task3-multi
```

The single-stage server should keep running, and Nginx should remain active in the multi-stage container. Read the logs for startup or configuration errors.

## 13. Important Docker Concepts

### Image vs container

- **Image:** a packaged template containing the filesystem and configuration used to create a container.
- **Container:** a running or stopped instance created from an image.

### Build stage vs runtime stage

- **Build stage:** contains the tools needed to create application output.
- **Runtime stage:** contains what is required to run or serve that output.

### `RUN` vs `CMD`

- `RUN` executes a command while building the image.
- `CMD` specifies the default command when a container starts.

In this lab, `RUN npm run build` generates the website during the build. Nginx starts when a container is launched from the final image.

### `EXPOSE` vs `-p`

- `EXPOSE` documents the port used by the application inside the container.
- `-p` publishes a container port on the host so it can be reached from outside the container.

### Why multi-stage builds matter

They let you use a convenient build environment without automatically including that environment in the final production image.

## 14. Interview Questions and Answers

### Q1. What is a Docker multi-stage build?

A multi-stage build uses multiple `FROM` instructions in one Dockerfile. Each stage can have a separate purpose, such as compiling or building an application and then preparing a smaller runtime image.

### Q2. What is the main advantage of multi-stage builds?

They help exclude unnecessary build tools, source files, and dependencies from the final image, which can reduce image size and simplify the runtime environment.

### Q3. What does `AS builder` mean?

It assigns the name `builder` to a build stage so later instructions can refer to that stage.

### Q4. What does `COPY --from=builder` do?

It copies selected files from the named build stage into the current stage.

### Q5. Why do we use Nginx in the final stage?

Nginx can serve static HTML and CSS files directly. The final image does not need Node.js just to deliver these files to a browser.

### Q6. Does the builder stage run when the container starts?

No. The builder stage runs as part of the image build. The container starts from the final image.

### Q7. Does Docker automatically remove the builder stage?

The intermediate stage is not included in the final image unless its files are copied into that image. Intermediate build cache may still be stored by Docker.

### Q8. What is the difference between `RUN` and `CMD`?

`RUN` executes during image building. `CMD` specifies the default command executed when a container starts.

### Q9. What is the difference between `EXPOSE` and `-p`?

`EXPOSE` documents the container port. `-p` publishes a port from the container to the host.

### Q10. Why is the final image different from the builder image?

The final stage starts from its own base image. Only the files explicitly copied into that stage are carried over from the builder.

### Q11. Will every multi-stage build produce a smaller image?

No. The result depends on the base images, the build output, the runtime, and what is excluded from the final stage.

### Q12. What happens if the source code changes?

Rebuild the image and create a new container from it. Existing containers do not automatically update when a new image is built.

### Q13. What is Docker build cache?

Docker can reuse previously built layers when the instructions and their inputs remain unchanged. This can make repeated builds faster.

### Q14. Why use `.dockerignore`?

It prevents unnecessary files from being sent to the Docker build context, helping reduce build overhead and avoiding accidental inclusion of local files.

### Q15. What is the difference between an image and a container?

An image is the packaged template. A container is an instance created from that template.

### Q16. Why should production images avoid unnecessary tools?

Extra tools and files increase the image's footprint and may increase the number of components that need maintenance or security updates.

### Q17. Can one Dockerfile have more than two stages?

Yes. A Dockerfile can have multiple stages for tasks such as testing, compiling, packaging, and creating a runtime image.

### Q18. How do you compare image sizes?

Use:

```bash
docker images
```

or:

```bash
docker image inspect task3-multi:v1 --format='{{.Size}}'
```

Compare images built on your own environment rather than relying on assumed sizes.

## 15. Evidence and Git

Capture screenshots or save notes showing:

1. The project structure.
2. Successful single-stage build.
3. Successful multi-stage build.
4. Both webpages running.
5. Output of the image-size comparison.
6. Files present in the final Nginx image.
7. Successful rebuild after changing the website.

Store evidence in the `evidence/` directory.

Review Git changes:

```bash
git status
```

From the repository root, stage and commit the task:

```bash
git add Week2-Docker/Task3-Multi_Stage_Builds
git commit -m "Complete Docker Week 2 Task 3 multi-stage builds"
```

Run these Git commands from the repository root, not from a directory outside the repository.

## 16. Cleanup

Stop and remove the lab containers:

```bash
docker rm -f task3-single task3-multi
```

Optionally remove the images created for this task:

```bash
docker rmi task3-single:v1 task3-multi:v1 task3-multi:v2 task3-multi:v3 task3-multi:v4
```

Docker may report that an image is missing if you did not create that optional tag. Remove only the lab images you no longer need.

## 17. Final Completion Checklist

- [ ] Created all application files.
- [ ] Understood the Node.js build script.
- [ ] Built the single-stage image.
- [ ] Ran and tested the single-stage container.
- [ ] Built the multi-stage image.
- [ ] Ran and tested the multi-stage container.
- [ ] Verified both versions serve the website.
- [ ] Compared and recorded actual image sizes.
- [ ] Inspected the final Nginx document root.
- [ ] Modified the website and rebuilt the image.
- [ ] Observed Docker build cache behavior.
- [ ] Reviewed the troubleshooting section.
- [ ] Practiced the interview questions.
- [ ] Saved evidence.
- [ ] Committed the task to Git.

## Conclusion

In this task, we used Node.js to build a static website and compared a single-stage Docker image with a multi-stage image using Nginx as the runtime.

The central lesson is that **the final production image should contain what is needed to run the application, not necessarily everything that was needed to build it**.
