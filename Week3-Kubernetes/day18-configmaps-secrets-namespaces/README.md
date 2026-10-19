# Day 18 — ConfigMaps, Secrets & Namespaces

## 🎯 Objective

Learn how to manage application configuration in Kubernetes using:

- **Namespaces** to separate environments (`dev` and `prod`)
- **ConfigMaps** to store non-sensitive configuration and HTML content
- **Secrets** to store sensitive values such as passwords
- **Deployments** to run the same application configuration in different namespaces
- **Environment variables and mounted volumes** to provide configuration to containers

By the end of this lab, the same Nginx Deployment will serve different pages in `dev` and `prod`.

---

## 🧰 Prerequisites

- Kubernetes cluster running
- `kubectl` installed and configured
- `curl` installed
- A terminal with access to the cluster

Check your cluster:

```bash
kubectl config current-context
kubectl get nodes
kubectl get namespaces
```

**Why?** These commands confirm which cluster you're connected to, whether its nodes are available, and which namespaces already exist.

---

## 📁 Project Structure

Create the Day 18 folder:

```bash
cd ~/DevOps-Winter-Arc/Week3-Kubernetes

mkdir -p day18-configmaps-secrets-namespaces/evidence

cd day18-configmaps-secrets-namespaces
```

Your folder will look like this when completed:

```text
day18-configmaps-secrets-namespaces/
├── README.md
├── configmap-dev.yaml
├── configmap-prod.yaml
├── deployment.yaml
└── evidence/
    ├── dev-page.png
    ├── prod-page.png
    ├── environment-values.png
    └── config-update.png
```

The evidence images are examples of filenames to use. Capture and save your own screenshots during the lab.

---

## Step 1 — Create Namespaces

Create separate namespaces for development and production:

```bash
kubectl create namespace dev
kubectl create namespace prod
```

Verify:

```bash
kubectl get namespaces
```

Expected: both `dev` and `prod` appear in the namespace list.

**Why namespaces?**

Namespaces provide logical separation between Kubernetes resources. A Deployment, ConfigMap, or Secret created in `dev` is separate from a resource with the same name in `prod`.

If a namespace already exists, inspect it instead of deleting it:

```bash
kubectl get all -n dev
kubectl get all -n prod
```

---

## Step 2 — Create the Development ConfigMap

Create the file:

```bash
nano configmap-dev.yaml
```

Add:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: site
data:
  APP_ENV: dev
  index.html: |
    <h1>Hello from DEV</h1>
    <p>Winter Arc - Day 18</p>
```

Save and exit Nano using `Ctrl+O`, `Enter`, then `Ctrl+X`.

Apply the file:

```bash
kubectl apply -f configmap-dev.yaml -n dev
```

Inspect it:

```bash
kubectl get configmap site -n dev
kubectl describe configmap site -n dev
```

**What this does:**

- `APP_ENV` stores the environment name.
- `index.html` stores the HTML page Nginx will serve.
- `-n dev` creates or updates the ConfigMap in the development namespace.

A ConfigMap stores non-sensitive configuration separately from the container image.

---

## Step 3 — Create the Production ConfigMap

Create:

```bash
nano configmap-prod.yaml
```

Add:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: site
data:
  APP_ENV: prod
  index.html: |
    <h1>Hello from PROD</h1>
    <p>Winter Arc - Day 18</p>
```

Apply and inspect:

```bash
kubectl apply -f configmap-prod.yaml -n prod

kubectl get configmap site -n prod
kubectl describe configmap site -n prod
```

The ConfigMap is also named `site`, but its data differs from the development version because it exists in a different namespace.

Verify both:

```bash
kubectl get configmap site -n dev -o yaml
kubectl get configmap site -n prod -o yaml
```

Expected:
- `dev` has `APP_ENV: dev` and the DEV HTML page.
- `prod` has `APP_ENV: prod` and the PROD HTML page.

---

## Step 4 — Create Secrets

For this lab, use dummy passwords only.

Create a Secret in `dev`:

```bash
kubectl create secret generic db-secret \
  --from-literal=password=dev-pass \
  -n dev
```

Create a separate Secret in `prod`:

```bash
kubectl create secret generic db-secret \
  --from-literal=password=prod-pass \
  -n prod
```

Verify that both exist without displaying their values:

```bash
kubectl get secret db-secret -n dev
kubectl get secret db-secret -n prod
```

**Important security note:** Kubernetes Secret values are commonly represented as Base64-encoded data, which is not encryption by itself. Use dummy values for this exercise. Never commit real passwords, tokens, or production credentials to Git.

---

## Step 5 — Create the Deployment YAML

Create the shared Deployment manifest:

```bash
nano deployment.yaml
```

Add the following YAML:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          ports:
            - containerPort: 80
          env:
            - name: APP_ENV
              valueFrom:
                configMapKeyRef:
                  name: site
                  key: APP_ENV
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: db-secret
                  key: password
          volumeMounts:
            - name: html
              mountPath: /usr/share/nginx/html
      volumes:
        - name: html
          configMap:
            name: site
```

### Understand the important fields

| Field | Purpose |
|---|---|
| `replicas: 1` | Runs one Pod for this Deployment. |
| `image: nginx:1.27` | Uses the Nginx container image. |
| `configMapKeyRef` | Loads `APP_ENV` from the `site` ConfigMap. |
| `secretKeyRef` | Loads the Secret's `password` key into `DB_PASSWORD`. |
| `volumeMounts` | Mounts configuration files into the container. |
| `/usr/share/nginx/html` | Nginx's default directory for serving website files. |
| `volumes.configMap.name` | Uses the `site` ConfigMap as the volume source. |

**Important:** This manifest deliberately contains no namespace in its metadata. You will apply the same file separately to `dev` and `prod`, allowing Kubernetes to resolve each namespace's own `site` ConfigMap and `db-secret`.

---

## Step 6 — Deploy to Both Namespaces

Apply the same Deployment manifest to `dev`:

```bash
kubectl apply -f deployment.yaml -n dev
```

Apply it to `prod`:

```bash
kubectl apply -f deployment.yaml -n prod
```

Wait for both Deployments:

```bash
kubectl rollout status deployment/web -n dev --timeout=180s
kubectl rollout status deployment/web -n prod --timeout=180s
```

Inspect the Pods:

```bash
kubectl get pods -n dev
kubectl get pods -n prod
```

Expected: each namespace has one running Nginx Pod, assuming the image can be pulled and the cluster has sufficient resources.

---

## Step 7 — Test the Development Website

Open a terminal and run:

```bash
kubectl port-forward -n dev deployment/web 8081:80
```

Keep this terminal running. Open a second terminal and run:

```bash
curl http://localhost:8081
```

Expected HTML includes:

```html
<h1>Hello from DEV</h1>
<p>Winter Arc - Day 18</p>
```

The port-forward connects your local port `8081` to port `80` on the Deployment's Pod.

---

## Step 8 — Test the Production Website

Open another terminal and run:

```bash
kubectl port-forward -n prod deployment/web 8082:80
```

Keep that terminal running, then test from another terminal:

```bash
curl http://localhost:8082
```

Expected HTML includes:

```html
<h1>Hello from PROD</h1>
<p>Winter Arc - Day 18</p>
```

### Compare the two environments

| Local URL | Namespace | Expected page |
|---|---|---|
| `http://localhost:8081` | `dev` | Hello from DEV |
| `http://localhost:8082` | `prod` | Hello from PROD |

If you are using WSL, run `curl` in the same environment where your port-forward is running, unless you have confirmed that the forwarded port is reachable from another environment.

---

## Step 9 — Verify Environment Variables

Check the environment in `dev`:

```bash
kubectl exec -n dev deployment/web -- printenv APP_ENV
```

Expected:

```text
dev
```

Check `prod`:

```bash
kubectl exec -n prod deployment/web -- printenv APP_ENV
```

Expected:

```text
prod
```

### Verify that the Secret is available without printing it

```bash
kubectl exec -n dev deployment/web -- sh -c \
  'test -n "$DB_PASSWORD" && echo "DB_PASSWORD is set" || echo "DB_PASSWORD is missing"'
```

```bash
kubectl exec -n prod deployment/web -- sh -c \
  'test -n "$DB_PASSWORD" && echo "DB_PASSWORD is set" || echo "DB_PASSWORD is missing"'
```

Expected: `DB_PASSWORD is set` for both environments.

Do not use `printenv DB_PASSWORD` in screenshots or logs for this lab; the goal is to verify that the variable exists without exposing its value.

---

## Step 10 — Update the Development ConfigMap

Edit the development ConfigMap:

```bash
kubectl edit configmap site -n dev
```

Change `APP_ENV` from `dev` to:

```yaml
APP_ENV: dev-updated
```

Change the HTML to:

```yaml
index.html: |
  <h1>Hello from UPDATED DEV</h1>
  <p>Winter Arc - Day 18</p>
```

Save and exit the editor.

### Test the mounted HTML update

Wait briefly, then run:

```bash
curl http://localhost:8081
```

The HTML served by Nginx should eventually change to `Hello from UPDATED DEV`. ConfigMap volumes are updated asynchronously; the change may not appear immediately.

### Test the environment variable

Run:

```bash
kubectl exec -n dev deployment/web -- printenv APP_ENV
```

It will normally still show:

```text
dev
```

**Why?** Environment variables populated from a ConfigMap are read when the container starts. Updating the ConfigMap does not modify an already-running process's environment.

### Restart the Deployment

Apply a rollout restart:

```bash
kubectl rollout restart deployment/web -n dev
kubectl rollout status deployment/web -n dev
```

Check the value again:

```bash
kubectl exec -n dev deployment/web -- printenv APP_ENV
```

Expected:

```text
dev-updated
```

Test the page again:

```bash
curl http://localhost:8081
```

Expected: `Hello from UPDATED DEV`.

Finally, confirm that production remains unchanged:

```bash
kubectl exec -n prod deployment/web -- printenv APP_ENV
curl http://localhost:8082
```

Expected: `prod` and the original `Hello from PROD` page.

---

## Step 11 — Troubleshooting

### A. Pod shows `CreateContainerConfigError`

Inspect the Pod and its events:

```bash
kubectl get pods -n dev
kubectl describe pod <POD_NAME> -n dev
```

For production:

```bash
kubectl get pods -n prod
kubectl describe pod <POD_NAME> -n prod
```

Look for messages about missing ConfigMaps, missing Secrets, or missing keys.

Verify that the resources exist in the same namespace as the Deployment:

```bash
kubectl get configmap site -n dev
kubectl get secret db-secret -n dev

kubectl get configmap site -n prod
kubectl get secret db-secret -n prod
```

A missing referenced resource or key can prevent Kubernetes from starting the container.

### B. Pod is not running

```bash
kubectl get pods -n dev -o wide
kubectl describe deployment web -n dev
kubectl get events -n dev --sort-by=.metadata.creationTimestamp
```

Repeat with `-n prod` if the production Deployment has a problem.

Look for image-pull failures, scheduling problems, missing configuration, or container startup errors.

### C. Website displays the wrong page

Inspect the ConfigMaps:

```bash
kubectl get configmap site -n dev -o yaml
kubectl get configmap site -n prod -o yaml
```

Inspect the mounted HTML file:

```bash
kubectl exec -n dev deployment/web -- cat /usr/share/nginx/html/index.html
kubectl exec -n prod deployment/web -- cat /usr/share/nginx/html/index.html
```

Confirm you are using the correct local port and namespace.

### D. `APP_ENV` did not change

```bash
kubectl rollout restart deployment/web -n dev
kubectl rollout status deployment/web -n dev
kubectl exec -n dev deployment/web -- printenv APP_ENV
```

Environment variables are refreshed when the container starts again.

### E. Port-forward fails

Confirm that the Deployment and Pod are available:

```bash
kubectl get deployment web -n dev
kubectl get pods -n dev
```

Check whether another process is already using local port `8081` or `8082`. Stop an old port-forward with `Ctrl+C` before restarting it.

---

## Step 12 — Save Evidence

Capture screenshots that demonstrate:

1. `dev` website displaying `Hello from DEV`.
2. `prod` website displaying `Hello from PROD`.
3. Environment variables showing `dev` and `prod`.
4. Updated DEV page and `APP_ENV=dev-updated` after restarting the Deployment.
5. Both namespaces and their Deployments, if useful.

Save the screenshots inside the `evidence/` folder.

**Before submitting:** Make sure screenshots do not expose password values, tokens, or other credentials.

---

## Step 13 — Cleanup

Only perform cleanup **after saving your evidence** and confirming you have no other resources to preserve in these namespaces.

Inspect what will be removed:

```bash
kubectl get all -n dev
kubectl get all -n prod
kubectl get configmaps -n dev
kubectl get secrets -n dev
kubectl get configmaps -n prod
kubectl get secrets -n prod
```

If these namespaces are dedicated to this lab and contain no resources you need to keep, delete them:

```bash
kubectl delete namespace dev
kubectl delete namespace prod
```

**Warning:** Deleting a namespace deletes all resources inside it, not just the resources created for Day 18. Do not run these commands if either namespace contains unrelated work.

---

## 🧠 Interview Questions & Answers

### 1. What is a ConfigMap?

A ConfigMap stores non-sensitive configuration separately from an application image. It can provide values through environment variables or mounted files.

### 2. What is a Secret?

A Secret is a Kubernetes resource intended for sensitive values such as passwords and tokens. Access should be restricted, and appropriate encryption-at-rest and access controls should be configured.

### 3. Is Base64 encryption?

No. Base64 is an encoding format, not encryption. Anyone with access to the encoded value can decode it.

### 4. Why do we use namespaces?

Namespaces separate and organize Kubernetes resources. They allow resources with the same name to exist independently in different namespaces.

### 5. Why can `site` exist in both `dev` and `prod`?

Names are scoped to a namespace for namespaced resources. Each Deployment references the ConfigMap and Secret in its own namespace.

### 6. Why did the HTML update while `APP_ENV` did not?

The HTML is delivered through a ConfigMap volume, which Kubernetes updates asynchronously. Environment variables are set when a container starts and do not change inside an already-running container.

### 7. Why does a missing ConfigMap or Secret cause a startup problem?

The Deployment references those resources to build the container configuration. If a required resource or key is missing, Kubernetes may be unable to create the container configuration.

### 8. Do namespaces provide complete security isolation?

No. Namespaces provide logical separation, but they do not automatically isolate every resource or network connection. RBAC, NetworkPolicies, and appropriate cluster configuration may also be required.

### 9. What happens when a Deployment is restarted?

Kubernetes replaces the Deployment's Pods through a rollout. The new containers read their environment variables from the current ConfigMap and Secret data.

### 10. What is the difference between a ConfigMap and a Secret?

A ConfigMap is for non-sensitive configuration. A Secret is designed for sensitive data and supports tighter access controls, but safe use still requires proper RBAC, encryption-at-rest configuration, and careful handling.

---

## ✅ Day 18 Completion Checklist

- [ ] Created `dev` and `prod` namespaces.
- [ ] Created `site` ConfigMaps with different values and HTML pages.
- [ ] Created separate `db-secret` resources with dummy values.
- [ ] Created the shared `deployment.yaml`.
- [ ] Deployed Nginx in both namespaces.
- [ ] Confirmed both Pods are running.
- [ ] Verified the DEV and PROD websites using port-forward and `curl`.
- [ ] Verified `APP_ENV` in both containers.
- [ ] Verified `DB_PASSWORD` is set without exposing its value.
- [ ] Updated the DEV ConfigMap and tested the mounted HTML change.
- [ ] Restarted the DEV Deployment and verified the updated environment variable.
- [ ] Captured evidence screenshots.
- [ ] Cleaned up only after checking for unrelated resources.
- [ ] Saved all YAML files and this README in the Day 18 folder.

---

## 🎉 What I Learned

In this lab, I practiced separating application configuration from container images, managing development and production resources with namespaces, injecting configuration using ConfigMaps and Secrets, and understanding the difference between mounted files and environment variables.

These are important Kubernetes fundamentals for managing applications across multiple environments.
