# Day 15 - Kubernetes Fundamentals

## Objective

The objective of Day 15 is to understand the fundamentals of Kubernetes and deploy a containerized Nginx application to a local Kubernetes cluster using YAML manifests.

This lab covers Kubernetes architecture, Pods, Deployments, Services, scaling, networking, basic troubleshooting, and resource cleanup.

### Tasks completed in this lab

- Explain Kubernetes and the difference between Docker and Kubernetes.
- Understand clusters, control planes, nodes, Pods, Deployments, and Services.
- Set up and verify a local Kubernetes cluster.
- Create a Deployment using `deployment.yaml`.
- Create a NodePort Service using `service.yaml`.
- Deploy Nginx and inspect its Pods.
- Scale the Deployment from two to three replicas.
- Access Nginx through the Service or `kubectl port-forward`.
- Practice troubleshooting and optionally demonstrate self-healing.
- Save evidence and document the results.

### Technologies used

| Technology | Purpose |
|---|---|
| Kubernetes | Orchestrates containerized workloads |
| Docker Desktop | Provides a local environment for Kubernetes |
| kind | Alternative local Kubernetes cluster implementation |
| kubectl | Command-line interface for Kubernetes |
| Nginx | Web server used for the deployment exercise |
| YAML | Defines Kubernetes resources declaratively |
| Git and GitHub | Version control and project submission |
| curl | Tests HTTP access to Nginx |

## Architecture and key concepts

### 1. What is Kubernetes?

Kubernetes is a container orchestration platform. It helps deploy, manage, scale, and recover containerized applications across a cluster.

Instead of manually starting and managing every container, we declare the desired state in Kubernetes manifests. Kubernetes controllers then work to maintain that state.

### 2. Docker vs Kubernetes

| Docker | Kubernetes |
|---|---|
| Builds container images and runs containers. | Orchestrates containerized workloads across a cluster. |
| Provides commands such as `docker build` and `docker run`. | Provides commands such as `kubectl apply` and `kubectl scale`. |
| Manages individual containers and related resources. | Manages Pods, Deployments, Services, scheduling, and scaling. |
| Does not by itself provide Kubernetes-style Deployment reconciliation. | Controllers work to maintain the requested workload state. |

Docker and Kubernetes are complementary technologies, not direct replacements for each other.

### 3. Kubernetes architecture

A Kubernetes cluster consists of a control plane and one or more worker nodes. In a local learning cluster, these components may be hosted on the same computer.

**Control plane**

The control plane manages cluster-level decisions and the desired state of resources. Its components include the API server, scheduler, controller manager, and cluster data store.

**Worker node**

A node provides the environment where application Pods run. It uses components such as a container runtime and node agent to run and manage workloads.

**Pod**

A Pod is the smallest deployable Kubernetes unit. It contains one or more containers that share certain resources. In this lab, each Nginx Pod runs an Nginx container.

**Deployment**

A Deployment manages replicated Pods and helps maintain the desired number of replicas. It also supports controlled updates.

**Service**

A Service provides a stable endpoint for accessing a group of Pods. It uses label selectors to identify the Pods that receive traffic.

**Labels and selectors**

Labels are key-value pairs attached to Kubernetes resources. Selectors allow resources such as Deployments and Services to identify matching Pods.

### 4. Lab architecture

```text
Developer
   |
   | kubectl apply
   v
Local Kubernetes Cluster
   |
   v
Deployment: nginx-deployment
   |
   +---- Pod 1: Nginx
   |
   +---- Pod 2: Nginx
   |
   +---- Pod 3: Nginx (after scaling)
             |
             v
      Service: nginx-service
             |
             v
    NodePort: 30080
    or port-forward: localhost:8080
```

The Deployment initially requests two replicas. After scaling, it requests three. The Service selector `app: nginx` matches the labels on those Pods and routes traffic to the selected Pods.

### 5. NodePort vs port-forward

**NodePort** exposes a Service through a port on the cluster nodes. In this lab, the requested port is `30080`.

**Port-forwarding** creates a temporary local connection to a Kubernetes resource. The command `kubectl port-forward service/nginx-service 8080:80` forwards local port `8080` to Service port `80`.

Port-forwarding is a useful alternative when NodePort is not accessible through the local cluster environment.

## Cluster setup

### 1. Prerequisites

- Windows with Docker Desktop installed and running.
- Ubuntu/WSL terminal, if using WSL.
- `kubectl` installed.
- A working local Kubernetes cluster.
- Internet access to download the Nginx image.

This assignment is designed for a local cluster. A paid cloud cluster such as AWS EKS is not required.

### 2. Configure Docker Desktop Kubernetes

In Docker Desktop:

1. Open **Settings → Kubernetes**.
2. Select `kind` if using the Docker Desktop option shown in the setup screen.
3. Keep the default Kubernetes version unless you have a specific compatibility reason to change it.
4. Keep one node; it is sufficient for this exercise.
5. Leave **Show system containers (advanced)** unchecked.
6. Click **Apply** and wait for Kubernetes to start.

The exact interface may vary by Docker Desktop version.

If using a separate kind installation instead, create a cluster with:

```bash
kind create cluster --name winter-arc
```

Use one cluster setup method for this lab. Do not create another cluster if you already have a working one.

### 3. Verify the installation

Run these commands from Ubuntu/WSL or the terminal configured for your cluster:

```bash
docker --version
kubectl version --client
kubectl config current-context
kubectl cluster-info
kubectl get nodes
```

**Command explanations**

- `docker --version`: verifies the Docker CLI is installed.
- `kubectl version --client`: checks the installed Kubernetes client.
- `kubectl config current-context`: shows the selected Kubernetes context.
- `kubectl cluster-info`: checks access to the cluster's API endpoint.
- `kubectl get nodes`: lists cluster nodes and their status.

The cluster is ready when `kubectl get nodes` shows at least one node with status `Ready`.

Example output shape:

```text
NAME                 STATUS   ROLES           AGE   VERSION
<your-node-name>     Ready    <node-roles>    ...   v...
```

The actual node name, roles, age, and version depend on the local setup. Record your real output rather than copying this example as evidence.

### 4. Create the project directory

```bash
mkdir -p ~/DevOps-Winter-Arc/Week3-Kubernetes/day15-kubernetes/evidence
cd ~/DevOps-Winter-Arc/Week3-Kubernetes/day15-kubernetes
```

Project structure:

```text
day15-kubernetes/
├── deployment.yaml
├── service.yaml
├── README.md
└── evidence/
```

## Deploy and scale Nginx

### 1. Create `deployment.yaml`

Create the file:

```bash
nano deployment.yaml
```

Add:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
        - name: nginx
          image: nginx:1.27
          ports:
            - containerPort: 80
```

Save the file.

**Explanation**

- `apiVersion: apps/v1`: API version for a Deployment.
- `kind: Deployment`: declares the resource type.
- `metadata.name`: names the Deployment.
- `replicas: 2`: requests two Pod replicas.
- `selector.matchLabels`: selects Pods with the label `app: nginx`.
- `template`: defines the Pod that the Deployment creates.
- `image: nginx:1.27`: specifies the Nginx image.
- `containerPort: 80`: documents the port on which Nginx listens inside the container.

The Pod template's label must match the Deployment selector.

### 2. Create `service.yaml`

```bash
nano service.yaml
```

Add:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: nginx-service
spec:
  type: NodePort
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 80
      nodePort: 30080
```

Save the file.

**Explanation**

- `kind: Service`: declares a Service resource.
- `type: NodePort`: requests exposure through a node port.
- `selector: app: nginx`: selects the matching Nginx Pods.
- `port: 80`: the Service port.
- `targetPort: 80`: the destination port on the Pods.
- `nodePort: 30080`: the requested node port.

The Service does not create Pods. It selects existing Pods using labels.

### 3. Validate and apply the manifests

Validate the files before creating resources:

```bash
kubectl apply --dry-run=client -f deployment.yaml
kubectl apply --dry-run=client -f service.yaml
```

Apply them:

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

`kubectl apply` creates the resources if they do not exist and updates them when appropriate.

Inspect the resources:

```bash
kubectl get deployments
kubectl get pods -o wide
kubectl get services
```

Expected initial state:

- Deployment: `nginx-deployment`
- Desired replicas: 2
- Two Nginx Pods becoming `Running` and `Ready`
- Service: `nginx-service`
- Service type: `NodePort`
- Requested NodePort: `30080`

Wait for the Pods to become ready. Image download time and cluster resources affect how quickly this happens.

### 4. Inspect the Deployment and Service

```bash
kubectl describe deployment nginx-deployment
kubectl describe service nginx-service
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl get pods --show-labels
```

These commands help you inspect:

- Replica counts and Deployment conditions.
- Service selectors, ports, and endpoints.
- Recent cluster events.
- Pod labels and whether they match the Service selector.

To inspect Nginx logs:

```bash
kubectl get pods
kubectl logs POD_NAME
```

Replace `POD_NAME` with an actual Pod name from the output.

### 5. Scale Nginx to three replicas

```bash
kubectl scale deployment nginx-deployment --replicas=3
```

Verify the result:

```bash
kubectl get deployment nginx-deployment
kubectl get pods
```

Wait until the Deployment reports three ready replicas.

Scaling changes the Deployment's desired replica count. The Deployment controller works to create or remove Pods to match that count.

**Bonus challenge: scale to five**

```bash
kubectl scale deployment nginx-deployment --replicas=5
kubectl get pods
```

After verifying five Pods, return to three replicas:

```bash
kubectl scale deployment nginx-deployment --replicas=3
```

The Service continues routing to matching Pods because its selector uses the label `app: nginx`, rather than relying on fixed Pod names.

### 6. Test Nginx through NodePort

Try:

```bash
curl http://localhost:30080
```

If access works, the response should contain the Nginx welcome page HTML.

NodePort access through `localhost` depends on the local cluster and host networking setup. If it does not work, use port-forwarding.

### 7. Test with port-forwarding

Start the port-forward command:

```bash
kubectl port-forward service/nginx-service 8080:80
```

Leave this terminal running. In another terminal, run:

```bash
curl http://localhost:8080
```

You can also open this address in a browser:

```text
http://localhost:8080
```

Expected result: Nginx welcome page HTML.

Press `Ctrl+C` in the terminal running port-forwarding when finished.

### 8. Demonstrate self-healing (optional)

List the Pods:

```bash
kubectl get pods
```

Select one actual Pod name and delete it:

```bash
kubectl delete pod POD_NAME
```

Watch the Pod list:

```bash
kubectl get pods -w
```

Replace `POD_NAME` with the name of a real Pod. Press `Ctrl+C` to stop watching.

The Deployment should create a replacement Pod to restore the desired replica count. This demonstrates Kubernetes reconciliation and workload recovery.

## Commands and evidence

### 1. Command reference

| Command | Purpose |
|---|---|
| `kubectl get nodes` | Lists cluster nodes and their status. |
| `kubectl get pods` | Lists Pods in the current namespace. |
| `kubectl get pods -o wide` | Shows extra Pod details, including node placement. |
| `kubectl get deployments` | Lists Deployments and replica status. |
| `kubectl get services` | Lists Services and their types and ports. |
| `kubectl apply -f FILE` | Creates or updates resources from a manifest. |
| `kubectl describe deployment NAME` | Shows Deployment details, conditions, and events. |
| `kubectl describe service NAME` | Shows Service configuration and endpoints. |
| `kubectl logs POD_NAME` | Displays container logs for a Pod. |
| `kubectl scale deployment NAME --replicas=N` | Changes the desired replica count. |
| `kubectl get events --sort-by=.metadata.creationTimestamp` | Lists recent events in chronological order. |
| `kubectl get pods --show-labels` | Displays Pod labels for selector troubleshooting. |
| `kubectl port-forward service/NAME LOCAL:REMOTE` | Forwards a local port to a Service port. |
| `kubectl delete -f FILE` | Deletes resources defined in a manifest. |

### 2. Evidence checklist

Save screenshots or terminal output in the `evidence/` folder.

Recommended evidence:

- [ ] `kubectl get nodes` showing a `Ready` node.
- [ ] `kubectl get deployments` showing `nginx-deployment`.
- [ ] `kubectl get pods -o wide` showing the initial two Pods.
- [ ] `kubectl get services` showing `nginx-service` and NodePort `30080`.
- [ ] `kubectl get pods` showing three replicas after scaling.
- [ ] Successful Nginx access using NodePort or port-forwarding.
- [ ] One troubleshooting command and a short explanation of what it revealed.
- [ ] Optional: output showing a replacement Pod after deleting one managed Pod.

Use actual results from your own cluster. Do not fabricate command output or screenshots.

### 3. Suggested evidence filenames

```text
evidence/
├── 01-kubernetes-nodes.png
├── 02-deployment-and-pods.png
├── 03-service.png
├── 04-scaled-to-three.png
├── 05-nginx-access.png
└── 06-troubleshooting.png
```

These are suggested filenames only. Add each screenshot after you capture the corresponding result.

### 4. Submission deliverables

The completed folder should contain:

- `deployment.yaml`
- `service.yaml`
- `README.md`
- `evidence/` with real screenshots or evidence files

If submitting to GitHub, review the files before pushing. Never commit kubeconfig files, access tokens, cloud credentials, or other secrets.

## Troubleshooting / lessons learned

### 1. kubectl cannot connect to the server

Check:

```bash
kubectl config current-context
kubectl cluster-info
kubectl get nodes
```

**Possible causes**

- Docker Desktop or the local cluster is not running.
- Kubernetes has not finished starting.
- The selected context points to another cluster.
- The cluster configuration is unavailable.

**Lesson:** Installing `kubectl` is not the same as installing or starting a Kubernetes cluster.

### 2. Pod is Pending

Inspect the Pod:

```bash
kubectl get pods
kubectl describe pod POD_NAME
kubectl get events --sort-by=.metadata.creationTimestamp
```

Look for scheduling errors, insufficient resources, or node readiness issues.

### 3. Pod is ImagePullBackOff

Inspect:

```bash
kubectl describe pod POD_NAME
```

Check the image name, image tag, internet connectivity, and Pod events.

### 4. Pod is CrashLoopBackOff

Inspect:

```bash
kubectl logs POD_NAME
kubectl describe pod POD_NAME
```

Look for application startup errors, failed commands, or configuration problems.

### 5. Service has no endpoints

Check the Service and Pod labels:

```bash
kubectl describe service nginx-service
kubectl get pods --show-labels
kubectl get endpoints nginx-service
```

If the Service selector does not match the Pod labels, the Service cannot route traffic to those Pods.

On newer Kubernetes versions, EndpointSlices may be used as the primary endpoint representation:

```bash
kubectl get endpointslices
```

### 6. NodePort 30080 does not open

Try port-forwarding:

```bash
kubectl port-forward service/nginx-service 8080:80
```

Then test:

```bash
curl http://localhost:8080
```

**Lesson:** A NodePort Service and a local port-forward are different ways to reach the application. Port-forwarding is a useful fallback for local development.

### 7. Scaling does not immediately show three ready Pods

Run:

```bash
kubectl get deployment nginx-deployment
kubectl get pods
kubectl describe deployment nginx-deployment
```

Wait for image downloads and Pod startup. If the issue persists, inspect events and the status of the Pods.

### 8. Lessons learned

Record the lessons that apply to your actual run:

- Kubernetes resources are declared in YAML manifests.
- Deployments manage replicas and work to restore the desired state.
- Labels and selectors connect Services to matching Pods.
- Services provide a stable access point while Pod instances can change.
- Scaling changes the desired replica count.
- Troubleshooting is easier when checking resource status, events, descriptions, and logs.
- A local Kubernetes cluster is sufficient for this lab; a paid cloud cluster is unnecessary.

## Cleanup

After collecting the required evidence, remove the lab resources.

Delete the Service:

```bash
kubectl delete -f service.yaml
```

Delete the Deployment:

```bash
kubectl delete -f deployment.yaml
```

Verify:

```bash
kubectl get deployments
kubectl get pods
kubectl get services
```

Other resources in the current namespace may still exist, so do not expect these commands to remove unrelated workloads.

If you created a dedicated kind cluster exclusively for this lab and no longer need it, delete it with:

```bash
kind delete cluster --name winter-arc
```

Do not run this command against a cluster you intend to keep. If you used Docker Desktop Kubernetes, you can leave the cluster running for future Week 3 labs.

## Interview Questions and Answers

### Q1. What is Kubernetes?

Kubernetes is a container orchestration platform that manages the deployment, scaling, networking, and recovery of containerized workloads.

### Q2. How is Docker different from Kubernetes?

Docker builds and runs containers. Kubernetes orchestrates containerized workloads across a cluster and manages desired state, scheduling, scaling, and service discovery.

### Q3. What is a Kubernetes cluster?

A cluster is the complete Kubernetes environment containing the control plane and the nodes that run workloads.

### Q4. What is the control plane?

The control plane manages cluster-level operations and coordinates the desired state of resources.

### Q5. What is a node?

A node is a machine in the cluster that provides the environment for running Pods.

### Q6. What is a Pod?

A Pod is the smallest deployable Kubernetes unit and can contain one or more containers.

### Q7. Why use a Deployment?

A Deployment manages replicated Pods and helps maintain the requested replica count. It also supports controlled updates.

### Q8. What does `replicas: 3` mean?

It declares that the desired number of Pod replicas is three. Kubernetes works to maintain that count.

### Q9. What happens if a Pod managed by a Deployment is deleted?

The Deployment's controller normally creates a replacement Pod to restore the desired replica count.

### Q10. What is a Kubernetes Service?

A Service provides a stable endpoint to access a group of Pods selected by labels.

### Q11. What is a label selector?

A selector matches resources based on labels. In this lab, the Service selector `app: nginx` matches the Nginx Pod labels.

### Q12. What is a NodePort Service?

A NodePort Service exposes a Service through a port on cluster nodes, subject to the cluster's networking setup.

### Q13. What is the difference between `port` and `targetPort`?

`port` is the Service's port. `targetPort` is the port on the destination Pod to which traffic is forwarded.

### Q14. What does `kubectl apply -f deployment.yaml` do?

It creates or updates the Kubernetes resources described by the YAML file.

### Q15. What does `kubectl scale` do?

It changes the desired replica count for a scalable resource such as a Deployment.

### Q16. Why must Deployment selectors and Pod labels match?

The Deployment uses its selector to identify the Pods it manages. A mismatch prevents the selector from matching the intended Pods.

### Q17. Why is a Service useful when Pods can be replaced?

Pod instances and their IP addresses can change. A Service provides a stable access point and selects the current matching Pods.

### Q18. What is the difference between NodePort and port-forwarding?

NodePort exposes the Service through a node port. Port-forwarding temporarily forwards a local port to a Kubernetes resource and is useful for local testing.

### Q19. What is `kubectl describe` used for?

It shows detailed resource information, conditions, and events that help diagnose issues.

### Q20. What is the difference between `kubectl logs` and `kubectl describe`?

`kubectl logs` displays container output. `kubectl describe` displays resource details and events, which may reveal scheduling or configuration problems.

### Q21. What does ImagePullBackOff mean?

Kubernetes is unable to pull the requested container image after retrying. Check the image name, tag, registry access, and Pod events.

### Q22. What does CrashLoopBackOff mean?

A container is repeatedly failing and restarting. Inspect its logs, startup command, configuration, and Pod events.

### Q23. What is Kubernetes self-healing?

Kubernetes controllers work to restore the desired state. For example, a Deployment normally creates a replacement when one of its managed Pods is deleted.

### Q24. Is installing kubectl enough to run Kubernetes?

No. `kubectl` is the client. It must be configured to communicate with a running Kubernetes cluster.

### Q25. Why use YAML manifests?

YAML manifests describe the desired configuration declaratively, making resources repeatable, reviewable, and suitable for version control.

### Q26. Why does the Service still work after scaling from two to three Pods?

The Service selects Pods by labels, not by a fixed list of Pod names. Newly created matching Pods can therefore become Service endpoints.

### Q27. Do three replicas mean three Kubernetes nodes are required?

No. Multiple Pod replicas can run on a single node if resources are available and scheduling permits it.

### Q28. Why should kubeconfig files and credentials not be committed to GitHub?

They may contain credentials or access information that could allow unauthorized access to a cluster. Keep sensitive configuration out of version control.

## Final Completion Checklist

- [ ] Local Kubernetes cluster is running.
- [ ] At least one node reports `Ready`.
- [ ] `deployment.yaml` exists and applies successfully.
- [ ] `service.yaml` exists and applies successfully.
- [ ] Two initial Nginx replicas become ready.
- [ ] Deployment is scaled to three ready replicas.
- [ ] Nginx is accessible through NodePort or port-forwarding.
- [ ] A troubleshooting command was run and explained.
- [ ] Evidence screenshots were saved.
- [ ] README documents the actual results.
- [ ] Cleanup was completed or the cluster was intentionally retained for future labs.
- [ ] No credentials or kubeconfig files were committed.

**Final result:** A local Kubernetes deployment of Nginx managed by a Deployment, exposed through a NodePort Service, scaled to three replicas, tested, documented, and ready for GitHub submission.
