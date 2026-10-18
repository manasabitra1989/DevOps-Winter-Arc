# Day 17 — Kubernetes Services & Networking

## Objective

The objective of Day 17 is to understand how Kubernetes Services provide stable network access to Pods.

In this lab, I created a three-replica test workload, exposed it using a ClusterIP Service, tested Service DNS from a temporary Pod, observed backend endpoints, deleted a Pod to observe replacement, and intentionally broke and fixed the Service selector.

### Skills Practiced

- Kubernetes ClusterIP Services
- Service selectors and Pod labels
- Service DNS and CoreDNS
- Service `port` and `targetPort`
- EndpointSlices
- In-cluster HTTP requests
- Backend endpoint updates
- Service selector troubleshooting

---

## Architecture

The test application uses three backend Pods managed by a Deployment.

```text
                  Temporary Client Pod
                           |
                           | HTTP request
                           | http://hello/hostname
                           v
                     Kubernetes DNS
                        CoreDNS
                           |
                           | Resolves Service name
                           v
                   ClusterIP Service
                         hello
                       Port: 80
                           |
                           | targetPort: 8080
                           v
              +------------+------------+
              |            |            |
              v            v            v
           Pod 1         Pod 2         Pod 3
         app=hello     app=hello     app=hello
         Port 8080     Port 8080     Port 8080
```

### Key Concepts

**Service:** Provides a stable virtual IP and DNS name for accessing a group of matching Pods.

**ClusterIP:** Exposes a Service internally within the Kubernetes cluster.

**Selector:** Matches Pods using labels. The Service in this lab uses `app: hello`.

**EndpointSlice:** Stores backend endpoint information associated with a Service.

**CoreDNS:** Resolves Kubernetes Service DNS names.

**Port:** The port exposed by the Service to clients.

**TargetPort:** The port on which the backend application receives traffic.

**Service DNS:** Clients can access the Service using `hello` instead of hard-coding individual Pod IP addresses.

---

## Cluster Setup

I used the existing local Kubernetes cluster managed through Docker Desktop and kind.

Check the active context and cluster:

```bash
kubectl config current-context
kubectl get nodes
kubectl get deployments
kubectl get services
```

The cluster node should be Ready before starting the lab.

---

## Step 1 — Create a Three-Replica Deployment

Create the test application:

```bash
kubectl create deployment hello --replicas=3 \
  --image=registry.k8s.io/e2e-test-images/agnhost:2.39 \
  -- /agnhost netexec --http-port=8080
```

Check the Deployment and Pods:

```bash
kubectl get deployment hello
kubectl get pods -l app=hello --show-labels
kubectl rollout status deployment/hello --timeout=180s
```

### What I Learned

- A Deployment maintains the desired number of replicas.
- The Deployment creates and manages Pods through a ReplicaSet.
- Pod labels allow Services to identify the correct backend Pods.
- If a Pod is deleted, the Deployment attempts to create a replacement.

---

## Step 2 — Create a ClusterIP Service

Expose the Deployment internally:

```bash
kubectl expose deployment hello --name=hello \
  --type=ClusterIP --port=80 --target-port=8080
```

Inspect the Service:

```bash
kubectl get svc hello -o wide
kubectl describe svc hello
kubectl get endpointslices \
  -l kubernetes.io/service-name=hello -o wide
```

### Service Configuration

| Setting | Value |
|---|---|
| Service name | `hello` |
| Service type | ClusterIP |
| Selector | `app=hello` |
| Service port | `80` |
| Target port | `8080` |
| Expected replicas | `3` |

### Port vs. TargetPort

- `port: 80` is the port clients use when connecting to the Service.
- `targetPort: 8080` is the port used by the backend application.

The Service forwards traffic from port 80 to the application port 8080.

### Service Manifest

The equivalent reusable Service manifest is saved as `svc-clusterip.yaml`.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: hello
spec:
  type: ClusterIP
  selector:
    app: hello
  ports:
    - port: 80
      targetPort: 8080
```

The manifest can be applied with:

```bash
kubectl apply -f svc-clusterip.yaml
```

Use either `kubectl expose` or the manifest to create the Service, rather than trying to create the same Service twice.

---

## Step 3 — Test Service DNS

Start a temporary client Pod:

```bash
kubectl run tmp --rm -it \
  --image=busybox:1.36 \
  --restart=Never -- sh
```

Inside the temporary Pod, run:

```sh
nslookup hello
nslookup hello.default.svc.cluster.local
```

The full Service DNS name follows this pattern:

```text
service-name.namespace.svc.cluster.local
```

For this lab:

```text
hello.default.svc.cluster.local
```

A successful lookup returns the Service's ClusterIP.

Some shortened names tried during DNS search may return `NXDOMAIN`. The important check is that the intended Service name resolves successfully.

### Test HTTP Requests

Inside the temporary client Pod:

```sh
wget -qO- http://hello/hostname
```

Send repeated requests:

```sh
for i in 1 2 3 4 5 6; do
  wget -qO- http://hello/hostname
  echo
done
```

Exit the temporary Pod:

```sh
exit
```

### What I Learned

- CoreDNS resolves the Service name to its ClusterIP.
- Clients can communicate with a Service by name.
- The Service routes requests to eligible backend Pods.
- Repeated requests may return different backend hostnames.
- The exact order of backend responses is not guaranteed.

---

## Step 4 — Inspect EndpointSlices

Check the backend Pods:

```bash
kubectl get pods -l app=hello -o wide
```

Inspect the Service endpoints:

```bash
kubectl get endpointslices \
  -l kubernetes.io/service-name=hello -o wide
```

Describe the Service:

```bash
kubectl describe service hello
```

### What I Learned

EndpointSlices record the backend addresses and ports associated with a Service.

When the workload is healthy, I expect to see three backend addresses for the three ready replicas.

The Service object existing does not automatically mean it has working backends. The selector and endpoint information must also be checked.

---

## Step 5 — Delete a Pod and Observe Replacement

List the Pods:

```bash
kubectl get pods -l app=hello
```

Delete one actual Pod from the output:

```bash
kubectl delete pod POD_NAME
```

Replace `POD_NAME` with the real Pod name.

Watch the replacement:

```bash
kubectl get pods -l app=hello -w
```

Press `Ctrl+C` after observing the replacement.

Inspect the Pods and endpoints again:

```bash
kubectl get pods -l app=hello -o wide

kubectl get endpointslices \
  -l kubernetes.io/service-name=hello -o wide
```

### What I Learned

- Pods are replaceable and their IP addresses can change.
- The Deployment works to maintain the desired replica count.
- Kubernetes updates the Service's backend endpoint information as Pods change.
- Clients should use the Service name rather than depend on individual Pod IPs.

---

## Step 6 — Break the Service Selector

First inspect the correct labels and selector:

```bash
kubectl get pods -l app=hello --show-labels
kubectl describe service hello
```

Change the selector to an incorrect value:

```bash
kubectl patch service hello \
  -p '{"spec":{"selector":{"app":"hellow"}}}'
```

Inspect the result:

```bash
kubectl describe service hello

kubectl get endpointslices \
  -l kubernetes.io/service-name=hello -o wide
```

### Expected Result

The Service selector no longer matches the Pods labelled `app=hello`. As a result, the Service should have no usable backend endpoints.

The Service itself still exists, and its DNS name may still resolve. However, HTTP traffic cannot reach the intended application through this Service while it has no usable backends.

### Troubleshooting Lesson

A Service can exist and resolve through DNS but still fail to serve application traffic.

Always check:

- The Service selector
- The Pod labels
- The EndpointSlices
- Pod readiness
- The target port

---

## Step 7 — Fix the Service Selector

Restore the correct selector:

```bash
kubectl patch service hello \
  -p '{"spec":{"selector":{"app":"hello"}}}'
```

Check the restored endpoints:

```bash
kubectl get endpointslices \
  -l kubernetes.io/service-name=hello -o wide

kubectl describe service hello
```

Run the DNS and HTTP tests again from a temporary client Pod.

```bash
kubectl run tmp --rm -it \
  --image=busybox:1.36 \
  --restart=Never -- sh
```

Inside the shell:

```sh
nslookup hello

for i in 1 2 3 4 5 6; do
  wget -qO- http://hello/hostname
  echo
done

exit
```

### What I Learned

Restoring the correct selector allows the Service to discover the matching backend Pods again. Once the endpoints are available and the application is ready, requests should succeed.

---

## Troubleshooting

| Problem | Checks and Fixes |
|---|---|
| Service has no endpoints | Compare Service selector with Pod labels and check Pod readiness. |
| DNS lookup fails | Test from inside the cluster; check Service name, namespace and CoreDNS. |
| DNS works but HTTP fails | Inspect EndpointSlices, targetPort, readiness and the application port. |
| Only one backend appears | Verify all three Pods are Ready and repeat requests; traffic order is not guaranteed. |
| Replacement Pod takes time | Watch Pods and inspect events until the replacement is Ready. |
| ClusterIP cannot be accessed from the laptop | This is expected for an internal ClusterIP Service; test from a Pod. |

Useful diagnostic commands:

```bash
kubectl get pods -l app=hello --show-labels
kubectl describe service hello
kubectl get endpointslices \
  -l kubernetes.io/service-name=hello -o wide
kubectl get events --sort-by=.metadata.creationTimestamp
```

---

## Evidence

Save screenshots or terminal output in the `evidence/` directory.

Suggested files:

```text
evidence/
├── service-endpoints.png
├── dns-load-balancing.png
├── pod-replacement.png
└── selector-failure-fix.png
```

Evidence should demonstrate:

1. The ClusterIP Service configuration and backend endpoints.
2. Successful DNS lookup and repeated backend hostname requests.
3. Pod deletion, replacement and endpoint updates.
4. The broken selector and empty endpoints.
5. The corrected selector and restored HTTP requests.

Use evidence captured from my own Kubernetes cluster. Do not fabricate addresses, hostnames or successful test results.

---

## Cleanup

Delete only the resources created for this assignment:

```bash
kubectl delete service hello
kubectl delete deployment hello
```

Verify cleanup:

```bash
kubectl get deployments
kubectl get services
kubectl get pods
```

Do not delete the shared Kubernetes cluster or unrelated resources.

---

## Interview Questions and Answers

### 1. Why use a Service instead of a Pod IP?

Pod IPs can change when Pods are replaced. A Service provides a stable virtual IP and DNS name for clients.

### 2. What is a ClusterIP Service?

It is a Service type intended for internal communication within the Kubernetes cluster.

### 3. What is the difference between ClusterIP, NodePort and LoadBalancer?

- **ClusterIP:** Internal cluster access.
- **NodePort:** Exposes a Service through a port on each node.
- **LoadBalancer:** Requests an external load balancer where the environment supports it.

### 4. What is the difference between `port` and `targetPort`?

`port` is the Service-facing port. `targetPort` is the backend application port.

### 5. How does a Pod find a Service by name?

CoreDNS resolves the Service DNS name to its ClusterIP.

### 6. What is an EndpointSlice?

It is a Kubernetes resource that records network endpoints associated with a Service.

### 7. Why might a Service have no endpoints?

The selector may not match Pod labels, the Pods may not be ready, or the backend configuration may be incorrect.

### 8. Why can DNS work while HTTP fails?

The Service may exist and resolve successfully but have no usable backend endpoints or an incorrect target port.

### 9. Why should clients avoid hard-coded Pod IPs?

Pod IPs can change when Pods are replaced. A Service gives clients a stable way to reach the application.

---

## Completion Checklist

- [ ] Created the three-replica `hello` Deployment.
- [ ] Created the `hello` ClusterIP Service.
- [ ] Verified the Service selector and port mapping.
- [ ] Inspected EndpointSlices.
- [ ] Tested Service DNS from a temporary Pod.
- [ ] Sent repeated HTTP requests and inspected backend hostnames.
- [ ] Deleted a backend Pod and observed replacement.
- [ ] Confirmed endpoint updates.
- [ ] Broke the selector and observed the loss of usable endpoints.
- [ ] Fixed the selector and verified HTTP requests again.
- [ ] Saved the manifest, README, diagram and evidence.
- [ ] Cleaned up the assignment resources.

---

## Final Summary

In Day 17, I practiced Kubernetes Service networking by creating a ClusterIP Service in front of three backend Pods. I tested Service DNS and HTTP requests from inside the cluster, inspected EndpointSlices, observed Pod replacement, and diagnosed a Service failure caused by an incorrect selector.

The main lesson is that Kubernetes Services provide stable access to changing Pods, but successful traffic also depends on correct selectors, ready backends and port configuration.

**Status:** Update this README and mark the checklist only after verifying each task in the cluster.
