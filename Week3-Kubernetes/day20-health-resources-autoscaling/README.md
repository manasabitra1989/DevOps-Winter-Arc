# Day 20 — Kubernetes Health Checks, Resources & Autoscaling

## 🎯 Objective

Learn how to make Kubernetes applications:

- **Self-checking** using startup, readiness, and liveness probes.
- **Resource-aware** using CPU and memory requests and limits.
- **Efficiently scheduled** using Kubernetes QoS classes.
- **Automatically scalable** using the Horizontal Pod Autoscaler (HPA).

The goal is to deploy an application that can check its own health, use resources responsibly, and scale from **1 to 5 Pods** under load.

---

## 🧰 Prerequisites

- Docker Desktop with Kubernetes running.
- `kubectl` configured and connected to the cluster.
- Basic understanding of Deployments, Pods, and Services.
- Metrics Server installed and working.

Check the current Kubernetes context:

```bash
kubectl config current-context
```

Check the cluster:

```bash
kubectl get nodes
```

**Why?** These commands verify which cluster you're connected to and whether its nodes are available.

---

## 📁 Project Structure

```text
day20-health-resources-autoscaling/
├── README.md
└── deployment.yaml
```

---

# Task A — Install and Verify Metrics Server

## 1. Check node and Pod metrics

```bash
kubectl get nodes
kubectl top nodes
kubectl top pods -A
```

**What these commands do:**

- `kubectl get nodes` — lists the cluster's nodes.
- `kubectl top nodes` — displays current CPU and memory usage for nodes.
- `kubectl top pods -A` — displays CPU and memory usage for Pods across all namespaces.

If `kubectl top` reports `Metrics API not available`, Metrics Server may be missing or not functioning.

## 2. Install Metrics Server

Apply the official Metrics Server manifest:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

Check the Deployment:

```bash
kubectl get deployment metrics-server -n kube-system
kubectl get pods -n kube-system | grep metrics-server
```

Wait for the rollout:

```bash
kubectl rollout status deployment/metrics-server -n kube-system --timeout=120s
```

## 3. Fix the local lab's kubelet certificate issue

On this Docker Desktop/Kubernetes lab cluster, Metrics Server may fail to verify the kubelet's certificate.

If the logs show a TLS certificate verification error, apply this **lab-only workaround**:

```bash
kubectl patch deployment metrics-server -n kube-system --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'
```

Wait for Metrics Server to restart:

```bash
kubectl rollout status deployment/metrics-server -n kube-system --timeout=120s
```

**Security note:** `--kubelet-insecure-tls` disables kubelet certificate verification. Use it only when appropriate for this local lab, not as a general production configuration.

## 4. Verify metrics

```bash
kubectl top nodes
kubectl top pods -A
```

**Expected result:** CPU and memory values appear instead of a Metrics API error.

**Why this matters:** HPA needs resource metrics to calculate whether more or fewer replicas are required.

---

# Task B — Deploy an Application with Probes and Resource Limits

## 1. Create the namespace

```bash
kubectl create namespace day20-health
```

If the namespace already exists, continue without recreating it.

**Why?** Namespaces keep this day's resources separate from the other labs.

## 2. Create `deployment.yaml`

```bash
nano deployment.yaml
```

Paste the following configuration:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: php-apache
  namespace: day20-health
spec:
  replicas: 1
  selector:
    matchLabels:
      app: php-apache
  template:
    metadata:
      labels:
        app: php-apache
    spec:
      containers:
        - name: php-apache
          image: registry.k8s.io/hpa-example
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 200m
              memory: 64Mi
            limits:
              cpu: 500m
              memory: 128Mi
          startupProbe:
            httpGet:
              path: /
              port: 80
            failureThreshold: 30
            periodSeconds: 2
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 15
            periodSeconds: 10
```

Save with `Ctrl+O`, press `Enter`, then exit with `Ctrl+X`.

## 3. Understand the configuration

### Deployment

| Field | Purpose |
|---|---|
| `name: php-apache` | Names the Deployment. |
| `namespace: day20-health` | Places it in the lab namespace. |
| `replicas: 1` | Starts with one Pod. |
| `selector.matchLabels` | Identifies the Pods managed by the Deployment. |
| `template.metadata.labels` | Adds the matching label to created Pods. |
| `containerPort: 80` | Documents the container's HTTP port. |

### CPU and memory requests and limits

```yaml
resources:
  requests:
    cpu: 200m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 128Mi
```

- **Requests** describe the resources Kubernetes uses when scheduling the Pod and calculating resource-relative metrics.
- **Limits** cap resource consumption. A CPU limit throttles CPU usage; exceeding a memory limit can result in the container being terminated with `OOMKilled`.

Unit meanings:

- `200m` CPU = 0.2 of one CPU core.
- `500m` CPU = 0.5 of one CPU core.
- `64Mi` memory = 64 mebibytes.
- `128Mi` memory = 128 mebibytes.

### Startup probe

```yaml
startupProbe:
  httpGet:
    path: /
    port: 80
  failureThreshold: 30
  periodSeconds: 2
```

Checks whether the application has started successfully.

With a failure threshold of 30 and a period of 2 seconds, Kubernetes allows roughly 60 seconds of repeated probe failures before treating startup as failed.

While a startup probe has not succeeded, Kubernetes does not run the liveness and readiness probes.

### Readiness probe

```yaml
readinessProbe:
  httpGet:
    path: /
    port: 80
  initialDelaySeconds: 5
  periodSeconds: 5
```

Checks whether the application is ready to receive traffic. An unready Pod is excluded from normal Service traffic.

### Liveness probe

```yaml
livenessProbe:
  httpGet:
    path: /
    port: 80
  initialDelaySeconds: 15
  periodSeconds: 10
```

Checks whether the application is alive. Repeated failures can cause Kubernetes to restart the container.

**Remember:**

- Startup = Has the application started?
- Readiness = Can it receive traffic?
- Liveness = Should Kubernetes restart it?

## 4. Apply the Deployment

```bash
kubectl apply -f deployment.yaml
```

Wait for the Deployment:

```bash
kubectl rollout status deployment/php-apache -n day20-health --timeout=120s
```

Check the Pod:

```bash
kubectl get pods -n day20-health
```

Inspect its events, probes, and resource configuration:

```bash
kubectl describe pod -n day20-health -l app=php-apache
```

**Expected result:** The Pod is `Running` and shows `1/1` in the `READY` column.

---

# Task C — Inspect QoS and Resource Usage

## 1. Check the Pod's QoS class

```bash
kubectl get pod -n day20-health -l app=php-apache \
  -o jsonpath='{.items[0].status.qosClass}'; echo
```

**Expected result:**

```text
Burstable
```

### Why is the Pod Burstable?

The Pod has CPU and memory requests that are lower than their corresponding limits.

Kubernetes defines three QoS classes:

| QoS class | General rule |
|---|---|
| `Guaranteed` | Every container has CPU and memory requests equal to their limits, with the required settings for all containers. |
| `Burstable` | The Pod does not meet Guaranteed requirements but has resource requests or limits configured. |
| `BestEffort` | No container in the Pod has CPU or memory requests or limits configured. |

QoS class can affect eviction priority under node resource pressure.

## 2. Inspect resource settings

```bash
kubectl describe pod -n day20-health -l app=php-apache
```

Look for the `Requests`, `Limits`, `Liveness`, `Readiness`, `Startup`, and `QoS Class` sections.

## 3. View live resource usage

```bash
kubectl top pods -n day20-health
```

**Why?** This shows measured CPU and memory usage, which can be compared with the resource requests and limits.

---

# Task D — Configure Horizontal Pod Autoscaling

## 1. Create the HPA

```bash
kubectl autoscale deployment php-apache -n day20-health \
  --cpu-percent=50 \
  --min=1 \
  --max=5
```

This creates a Horizontal Pod Autoscaler targeting the `php-apache` Deployment.

| Option | Meaning |
|---|---|
| `--cpu-percent=50` | Target average CPU utilization of 50% of the Pods' CPU requests. |
| `--min=1` | Minimum replica count. |
| `--max=5` | Maximum replica count. |

Since each Pod requests `200m` CPU, a 50% utilization target corresponds to approximately `100m` CPU per Pod on average.

## 2. Verify the HPA

```bash
kubectl get hpa -n day20-health
```

Inspect its configuration and events:

```bash
kubectl describe hpa php-apache -n day20-health
```

Check the current Deployment and Pod count:

```bash
kubectl get deployments,pods -n day20-health
```

**Note:** The CPU target may briefly show `<unknown>` while metrics become available. If it persists, check Metrics Server, HPA events, and the Pods' resource requests.

---

# Task E — Generate Load and Observe Autoscaling

## 1. Start a load generator

Run this command in Terminal 1:

```bash
kubectl run load-generator -n day20-health \
  --image=busybox:1.36 \
  --restart=Never \
  -it --rm -- \
  /bin/sh -c 'while true; do wget -q -O- http://php-apache.day20-health.svc.cluster.local >/dev/null; done'
```

This creates a temporary BusyBox Pod that continuously sends HTTP requests to the application through its Kubernetes Service DNS name.

- `--restart=Never` creates a standalone Pod.
- `-it` attaches an interactive terminal.
- `--rm` removes the temporary Pod when the command exits.
- `wget` sends requests to the application.
- `>/dev/null` discards the response body while requests continue.

Keep this terminal running to maintain the load.

## 2. Watch the HPA in Terminal 2

```bash
kubectl get hpa -n day20-health -w
```

In another command, inspect the Deployment and Pods:

```bash
kubectl get deployments,pods -n day20-health
```

Monitor resource usage:

```bash
kubectl top pods -n day20-health
```

## 3. Understand the results

Under sufficient CPU load, the HPA should increase the replica count above 1, up to the configured maximum of 5.

The exact number of replicas and the time required to scale depend on measured CPU utilization, metrics collection, and HPA timing.

When finished, stop the load generator with `Ctrl+C`.

Then check the replica count again:

```bash
kubectl get hpa -n day20-health
kubectl get deployment php-apache -n day20-health
```

After the load stops, the HPA may reduce the number of replicas, but it will not go below 1.

**Success criteria:**

- HPA exists and reports metrics.
- Replica count increases under sufficient load.
- Replica count never exceeds 5.
- Replica count can decrease after the load stops.

---

# Task F — Test Readiness Probe Failure

This is a temporary test to demonstrate how readiness probes affect Pod availability.

**Important:** Change only the readiness probe path. Do not break the liveness probe.

## 1. Back up the Deployment file

From this directory:

```bash
cp deployment.yaml deployment.yaml.backup
```

## 2. Temporarily change the readiness path

Open the file:

```bash
nano deployment.yaml
```

Under `readinessProbe`, change:

```yaml
readinessProbe:
  httpGet:
    path: /
    port: 80
```

to:

```yaml
readinessProbe:
  httpGet:
    path: /does-not-exist
    port: 80
```

Make sure you change the path under `readinessProbe` only. Leave the startup and liveness paths as `/`.

Save the file and apply it:

```bash
kubectl apply -f deployment.yaml
```

## 3. Inspect the effect

```bash
kubectl get pods -n day20-health
kubectl describe pods -n day20-health
kubectl get events -n day20-health --sort-by=.metadata.creationTimestamp
```

The readiness probe should fail because the application does not serve the requested path successfully. Affected Pods may show `0/1` ready and will not receive normal Service traffic.

Because this is a Deployment template change, Kubernetes may create replacement Pods. Do not leave the broken readiness path in place.

## 4. Restore the correct readiness path

Restore `path: /` under `readinessProbe` in `deployment.yaml`, then apply:

```bash
kubectl apply -f deployment.yaml
kubectl rollout status deployment/php-apache -n day20-health --timeout=120s
kubectl get pods -n day20-health
```

Verify that the Pods become ready again.

If you need to restore the exact original file instead, and you have not made other changes you want to keep:

```bash
cp deployment.yaml.backup deployment.yaml
kubectl apply -f deployment.yaml
kubectl rollout status deployment/php-apache -n day20-health --timeout=120s
```

---

# Troubleshooting

## `Metrics API not available`

Check Metrics Server:

```bash
kubectl get pods -n kube-system | grep metrics-server
kubectl logs deployment/metrics-server -n kube-system
kubectl top nodes
```

If the Deployment is not ready, inspect its logs and events before applying a workaround.

## HPA shows `<unknown>` CPU

```bash
kubectl top pods -n day20-health
kubectl describe hpa php-apache -n day20-health
kubectl get events -n day20-health --sort-by=.metadata.creationTimestamp
```

Confirm that Metrics Server is healthy and that the application containers have CPU requests configured.

## Pod is not ready

```bash
kubectl get pods -n day20-health
kubectl describe pod -n day20-health -l app=php-apache
kubectl logs -n day20-health deployment/php-apache
```

Check image pulls, probe failures, and events.

## Container shows `OOMKilled`

Inspect the Pod:

```bash
kubectl describe pod -n day20-health -l app=php-apache
```

`OOMKilled` usually indicates that a container exceeded the memory available to it, often its configured memory limit. Review memory usage and whether the limit is appropriate.

## HPA does not scale up

```bash
kubectl get hpa -n day20-health
kubectl describe hpa php-apache -n day20-health
kubectl top pods -n day20-health
```

Check whether CPU utilization is above the target, metrics are available, and the replica count has not already reached the maximum.

---

# Interview Questions and Answers

### 1. What is the difference between startup, readiness, and liveness probes?

- **Startup probe:** Determines whether the application has started.
- **Readiness probe:** Determines whether the Pod should receive traffic.
- **Liveness probe:** Determines whether the container should be restarted because it appears unhealthy.

### 2. What is the difference between requests and limits?

Requests help Kubernetes schedule Pods and provide the baseline used for resource-relative utilization calculations. Limits cap container resource consumption.

### 3. What does `OOMKilled` mean?

The container was terminated after running out of available memory, commonly because it exceeded its memory limit.

### 4. What is HPA?

The Horizontal Pod Autoscaler adjusts the number of Pod replicas according to observed metrics and configured targets.

### 5. Why does HPA need Metrics Server?

Metrics Server supplies resource usage metrics, such as CPU and memory, that HPA can use for resource-based scaling.

### 6. What are the three Kubernetes QoS classes?

`Guaranteed`, `Burstable`, and `BestEffort`.

### 7. What is the approximate HPA replica calculation?

For CPU utilization-based scaling, a useful simplified formula is:

```text
desired replicas ≈
current replicas × (current average CPU utilization / target CPU utilization)
```

For example, if there are 2 replicas, average CPU utilization is 100%, and the target is 50%:

```text
desired replicas ≈ 2 × (100 / 50)
                 ≈ 4
```

This is a simplified estimate. Kubernetes also considers metrics availability, scaling behavior, and replica bounds.

### 8. Can HPA scale based on memory?

Yes, if configured with suitable resource metrics and targets. HPA can also use other supported metrics, depending on the cluster and configuration.

### 9. Does HPA guarantee immediate scaling?

No. Metrics collection and control loops introduce delays. Scaling can also be affected by replica bounds, missing metrics, and scaling behavior settings.

### 10. Why should the liveness probe not be confused with readiness?

A failed readiness probe removes a Pod from normal Service traffic without necessarily restarting it. A failed liveness probe can trigger a container restart.

---

# 🧹 Cleanup

Once you have captured any evidence you need, remove the lab namespace:

```bash
kubectl delete namespace day20-health
```

This removes the namespace and its namespaced resources, including the Deployment, HPA, and remaining Pods.

**Do not remove Metrics Server just to clean up this lab.** It is a shared cluster component that may be useful for future labs. If you use this cluster for production or other workloads, review any TLS workaround separately.

Verify cleanup:

```bash
kubectl get namespace day20-health
```

The namespace should no longer exist once deletion has completed.

---

# ✅ Day 20 Completion Checklist

- [ ] Checked node and Pod resource metrics.
- [ ] Installed and verified Metrics Server.
- [ ] Created the `day20-health` namespace.
- [ ] Deployed `php-apache`.
- [ ] Configured startup, readiness, and liveness probes.
- [ ] Configured CPU and memory requests and limits.
- [ ] Verified the Pod's QoS class is `Burstable`.
- [ ] Checked live Pod resource usage.
- [ ] Created and inspected the HPA.
- [ ] Generated load and observed autoscaling.
- [ ] Temporarily tested readiness probe failure.
- [ ] Restored the correct readiness probe.
- [ ] Cleaned up the lab namespace.

## 🎓 What I Learned

This lab demonstrated how Kubernetes monitors application health, allocates resources, classifies Pods by QoS, and adjusts replica counts using metrics. I also learned how to inspect failures through Pod descriptions, events, and resource metrics, and why health probes must be configured carefully.

**Day 20 complete — Health Checks, Resource Management & Autoscaling.**
