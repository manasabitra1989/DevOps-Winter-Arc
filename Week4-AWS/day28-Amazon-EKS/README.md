# Day 28/90 — Amazon EKS

**Challenge:** DevOps Winter Arc — AWS Week, Day 6  
**Project:** `day28-Amazon-EKS/`  
**Source:** `DevOps_Winter_Arc_Day28_AWS_EKS.pdf`

> **Cost warning:** EKS control plane, EC2 worker nodes, load balancers, storage, NAT Gateways, public IPv4 addresses and data transfer may incur charges. A Free Tier account or budget alert does not guarantee all resources are free or stop charges automatically. If you cannot risk any charge, complete the design/documentation path and use Floci/local Kubernetes only.

## 1. Goal

Understand how Amazon EKS runs Kubernetes on AWS; create a cluster and worker capacity where cost permits; configure `kubectl`; deploy a small Nginx app; learn IAM, IRSA, storage and autoscaling; troubleshoot one issue; and clean up lab resources.

## 2. Architecture

### Real AWS architecture

```text
Developer / kubectl
        |
        v
Amazon EKS control plane (AWS-managed)
        |
        v
Managed node group (EC2 worker nodes)
        |
        v
Kubernetes Deployment
        |
        v
Two Nginx Pods
        |
        v
ClusterIP Service (internal)
        |
        +---- Optional AWS Load Balancer -> users
              (may incur additional charges)
```

The control plane coordinates the cluster; worker nodes provide compute capacity for Pods. An `Active` cluster does not guarantee the app is reachable: nodes, Pods, Services, routes, load balancer health and security rules must also be correct.

### Floci learning architecture

```text
AWS CLI -> Floci local AWS-compatible endpoint
                    |
                    +--> EKS API emulation (supported operations only)
                    |
                    +--> Real mode may start local Kubernetes (k3s)
                              |
                              +--> kubectl -> Pods / Services
```

**Important:** Floci is an emulator, not an actual AWS-managed EKS control plane. API support depends on the installed Floci version and mode. A cluster or node-group metadata record does not prove the Kubernetes API or worker nodes are working. Verify with `kubectl get nodes`; never assume every EKS API is implemented.

## 3. Key concepts

| Concept | Explanation |
|---|---|
| Amazon EKS | AWS-managed Kubernetes service. AWS manages the control plane; you manage workloads and worker capacity. |
| Control plane | Kubernetes API and coordination components managed by EKS. |
| Worker node | Compute machine, often EC2, where Pods run. |
| Managed node group | Group of EC2 worker nodes integrated with EKS management. |
| `kubectl` | CLI used to inspect and manage Kubernetes resources. |
| Pod | Smallest standard deployable Kubernetes unit; contains one or more containers. |
| Deployment | Maintains the desired replica count and replaces failed Pods. |
| Service | Stable network endpoint for selected Pods. |
| IAM access | Controls which identities can access/administer the cluster and what permissions they receive. |
| IRSA | IAM Roles for Service Accounts; gives a workload scoped AWS permissions through a Kubernetes service account and IAM role. |
| AWS Load Balancer Controller | Integrates supported Kubernetes resources with AWS load-balancing infrastructure. |
| EBS / EFS | AWS persistent-storage options; EBS is block storage, EFS is managed network file storage. |
| Pod autoscaling | Changes the number of application replicas. |
| Node autoscaling | Changes available worker compute capacity. |

## 4. Project files

```text
day28-Amazon-EKS/
├── README.md
├── deployment.yaml
└── notes/
    ├── troubleshooting.md
    └── cost-note.md
```

## 5. Task A — Prepare safely

### Option 1: Floci (local emulator)

```bash
mkdir -p ~/DevOps-Winter-Arc/Week4-AWS/day28-Amazon-EKS/notes
cd ~/DevOps-Winter-Arc/Week4-AWS/day28-Amazon-EKS

floci --version
floci status
docker --version
docker info
aws --version
kubectl version --client
```

Start Floci if needed, using commands supported by your installed version:

```bash
floci start
floci status
```

Set the local endpoint for this shell (adjust only if your setup uses another endpoint):

```bash
export AWS_ENDPOINT_URL=http://localhost:4566
export AWS_DEFAULT_REGION=us-east-1
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
```

Check EKS API support:

```bash
aws --endpoint-url "$AWS_ENDPOINT_URL" eks list-clusters
aws --endpoint-url "$AWS_ENDPOINT_URL" eks help
```

If your installed Floci version supports EKS real mode, follow its version-specific setup for the local Kubernetes engine and authentication. Verify the AWS API and Kubernetes layer separately:

```bash
aws --endpoint-url "$AWS_ENDPOINT_URL" eks describe-cluster \
  --name day28-eks-lab --region us-east-1
kubectl config current-context
kubectl get nodes
kubectl get namespaces
```

**Do not assume these commands work merely because `aws eks list-clusters` returns a name.** Floci may support cluster metadata while Kubernetes authentication or worker joining requires additional setup. Avoid `floci reset` because it can remove other simulated labs.

### Option 2: Local Kubernetes fallback

If Floci cannot emulate the required EKS operations, `kind` can teach Kubernetes Deployment, Pod, Service and `kubectl` concepts. It is not EKS and does not satisfy real EKS control-plane/node-group tasks.

```bash
kind create cluster --name day28-eks-lab
kubectl config current-context
kubectl get nodes
```

## 6. Task B — Real EKS through the AWS website (optional, potentially paid)

Proceed only after checking pricing and accepting possible charges. Offers vary; do not assume all components are free.

### B1. Region and cost
1. Sign in to the [AWS Console](https://console.aws.amazon.com/).
2. Choose one region and use it consistently; examples below use `us-east-1`.
3. Review [Amazon EKS pricing](https://aws.amazon.com/eks/pricing/), EC2 pricing and Billing/Free Tier usage.
4. Avoid NAT Gateways and load balancers unless necessary and cost-checked.

### B2. Create the cluster IAM role
1. IAM → Roles → Create role.
2. Select AWS service and the EKS cluster use case.
3. Attach the recommended EKS cluster policy if the wizard does not do so.
4. Name it `Day28-EKS-Cluster-Role` and create it.

### B3. Create the cluster
1. Open the [Amazon EKS Console](https://console.aws.amazon.com/eks/home).
2. Choose Create cluster; use custom configuration if available.
3. Name: `day28-eks-lab`.
4. Select a currently supported Kubernetes version.
5. Select `Day28-EKS-Cluster-Role`.
6. Configure a suitable VPC and subnets in at least two Availability Zones, following the wizard's requirements.
7. Choose endpoint access intentionally. Restrict public access where possible.
8. Review and create; wait for status `Active`.

### B4. Create the worker-node IAM role
1. IAM → Roles → Create role → AWS service → EC2.
2. Attach `AmazonEKSWorkerNodePolicy` and `AmazonEC2ContainerRegistryPullOnly`.
3. Name it `Day28-EKS-Node-Role`.
4. Create it. Do not reuse the cluster role as the node role.

### B5. Create a managed node group
1. EKS → `day28-eks-lab` → Compute → Add node group.
2. Name: `day28-workers`.
3. Select `Day28-EKS-Node-Role`.
4. Choose suitable cluster subnets and a compatible instance type after checking its price.
5. If supported by the configuration, set desired/min/max size to `1`.
6. Create it and wait for status `Active`.

One worker node may cost money. EKS control-plane charges are separate from EC2 charges.

### B6. Connect using AWS CloudShell
Open CloudShell in the same region:

```bash
aws sts get-caller-identity
aws eks update-kubeconfig --region us-east-1 --name day28-eks-lab
kubectl config current-context
kubectl get nodes
kubectl get namespaces
```

Expected: the context identifies the real cluster and a worker node eventually shows `Ready`. Never use Floci test credentials with real AWS.

## 7. Task C — Deploy Nginx

The PDF asks for a two-replica Deployment. This manifest uses `ClusterIP` to avoid intentionally provisioning a billable AWS load balancer. Save as `deployment.yaml`.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-demo
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nginx-demo
  template:
    metadata:
      labels:
        app: nginx-demo
    spec:
      containers:
        - name: nginx
          image: nginx:stable
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: nginx-demo
spec:
  type: ClusterIP
  selector:
    app: nginx-demo
  ports:
    - port: 80
      targetPort: 80
```

Run in the terminal connected to the intended cluster:

```bash
kubectl apply -f deployment.yaml
kubectl rollout status deployment/nginx-demo --timeout=300s
kubectl get deployments
kubectl get pods -o wide
kubectl get services
kubectl describe service nginx-demo
```

Expected: two Pods become Ready and the Deployment reports two available replicas.

### Test without a public load balancer

```bash
kubectl port-forward service/nginx-demo 8080:80
```

Keep this running; in a second terminal that can reach the forwarded port:

```bash
curl -I http://localhost:8080
```

A successful response usually includes `HTTP/1.1 200 OK`. Port forwarding does not create a public URL.

### Optional LoadBalancer Service
The PDF permits `type: LoadBalancer` if you intentionally want an AWS load balancer and have checked its cost. It is optional and may incur charges. Do not use it just to obtain a public address for this lab.

## 8. Concepts to explain

### IAM access vs workload permissions
IAM access governs identities accessing/administering the cluster. IRSA provides an application Pod scoped AWS permissions through its Kubernetes service account and IAM role. Grant least privilege; never bake long-lived AWS keys into images.

### EBS vs EFS
EBS is block storage; EFS is managed network file storage. Choose based on persistence and sharing/access needs. Real EKS storage integrations may require drivers and configuration; local emulation does not prove EBS/EFS behavior.

### Pod vs node autoscaling
Pod autoscaling changes replica count. Node autoscaling changes available worker capacity. More Pods may remain Pending if capacity or scheduling constraints prevent placement.

### AWS Load Balancer Controller
It integrates supported Kubernetes resources with AWS load balancers. IAM, subnet/network configuration, controller prerequisites and healthy Pods all matter. Load balancers may cost money.

## 9. Cleanup — mandatory

### Floci
1. Delete Kubernetes objects if `kubectl` is authenticated to the Floci cluster:
   ```bash
   kubectl delete -f deployment.yaml --ignore-not-found=true
   ```
2. Remove node-group and cluster resources using the deletion workflow supported by your installed Floci version.
3. Verify with the supported EKS list APIs.
4. Remove only test IAM identities created for this lab, if any.
5. Do not run `floci reset` unless you intend to clear all simulated resources, including other labs.

Floci routes and resource support vary by version; a failed delete call is not proof of cleanup.

### Real AWS
1. Delete Kubernetes workloads:
   ```bash
   kubectl delete -f deployment.yaml
   ```
2. In EKS → cluster → Compute, delete `day28-workers` and wait for completion.
3. Delete `day28-eks-lab`.
4. Inspect lab-created load balancers, target groups, NAT Gateways, Elastic IPs, EBS volumes and CloudFormation stacks. Delete only resources belonging to this lab.
5. Review billing later; usage data may be delayed.

Deleting only the Deployment is not enough. EKS, EC2 nodes and networking resources can continue to incur charges until removed.

## 10. Evidence and deliverables

Capture 3–5 screenshots if possible:
1. Cluster status (`Active`) — real AWS only if actually created.
2. `kubectl get nodes`.
3. Deployment and two Pods Ready.
4. Service and Nginx response, if tested.
5. Cleanup proof.

Hide account IDs and credentials. Never publish kubeconfig contents, tokens, access keys or secrets.

## 11. Interview Q&A

**Q1. What is Amazon EKS?**  
A managed Kubernetes service. AWS manages the control plane; you manage workloads and worker capacity.

**Q2. What is a managed node group?**  
A group of EC2 worker nodes integrated with EKS management.

**Q3. What is IRSA?**  
IAM Roles for Service Accounts lets Kubernetes workloads receive scoped AWS permissions through a service account and IAM role.

**Q4. What is the difference between a Pod and a node?**  
A Pod runs one or more containers; a node is the worker machine that runs Pods.

**Q5. Why might a Pod be Pending?**  
Insufficient resources, scheduling constraints, taints/tolerations, or storage/network requirements.

**Q6. Why use a load balancer?**  
It provides an entry point and routes traffic to an application. AWS load balancers may incur charges.

**Q7. Pod autoscaling vs node autoscaling?**  
Pod autoscaling changes replicas; node autoscaling changes available compute capacity.

**Q8. Why might `kubectl` fail to connect?**  
Wrong context/region/cluster, cluster not Active, IAM access problems, bad kubeconfig or endpoint/network issues.

**Q9. What does a ClusterIP Service do?**  
It provides an internal stable endpoint for selected Pods; it does not automatically expose the app to the internet.

**Q10. Why clean up EKS labs?**  
Control plane, nodes, load balancers, storage and networking resources can keep costing money.

## 12. Completion checklist

- [ ] Explain EKS control plane and worker nodes.
- [ ] Create or design a Deployment and Service.
- [ ] Verify two Nginx Pods Ready where Kubernetes is available.
- [ ] Explain IAM access, IRSA, EBS/EFS and autoscaling.
- [ ] Document one real or clearly labelled simulated troubleshooting case.
- [ ] Capture useful evidence without secrets.
- [ ] Delete lab resources and verify chargeable dependencies are removed.
