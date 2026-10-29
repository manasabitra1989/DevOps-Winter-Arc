# Day 28 — EKS Troubleshooting Guide

This guide follows the troubleshooting table and architecture in `DevOps_Winter_Arc_Day28_AWS_EKS.pdf`. It covers real AWS EKS and Floci.

> **Safety:** Confirm which environment you are using before running commands. Real AWS commands can affect billable resources. Never paste AWS keys, Kubernetes tokens, kubeconfig contents or secrets into public notes.

## 1. Identify the environment

### Floci

```bash
echo "$AWS_ENDPOINT_URL"
floci --version
floci status
aws --endpoint-url http://localhost:4566 eks list-clusters
```

Use the endpoint and credentials required by your installed Floci version. A cluster name returned by Floci does not prove the Kubernetes API is healthy.

### Real AWS

```bash
aws sts get-caller-identity
aws configure list
aws eks list-clusters --region us-east-1
aws eks describe-cluster \
  --name day28-eks-lab \
  --region us-east-1 \
  --query 'cluster.{status:status,endpoint:endpoint,version:version}'
```

Confirm account and region before making changes.

## 2. `kubectl` cannot connect or asks for credentials

**Symptoms**
- `You must be logged in to the server`
- `the server has asked for the client to provide credentials`
- `The connection to the server ... was refused`

**Checks**

```bash
kubectl config current-context
kubectl config get-contexts
kubectl cluster-info
```

For real AWS:

```bash
aws sts get-caller-identity
aws eks update-kubeconfig \
  --region us-east-1 \
  --name day28-eks-lab
kubectl get namespaces
```

If it persists, check cluster status, IAM access entries/permissions, endpoint access and network connectivity. The identity that created a cluster is not necessarily an administrator for every identity.

For Floci, check that `kubectl` points to the Floci Kubernetes API rather than a stale real AWS endpoint; confirm the installed Floci mode supports EKS real-mode Kubernetes; check its authentication requirements; and ensure Docker is running if the mode requires a local k3s container.

Do not fix emulator authentication by switching to real AWS credentials or creating a paid cluster.

## 3. Cluster is not `Active`

**Real AWS checks**

```bash
aws eks describe-cluster \
  --name day28-eks-lab \
  --region us-east-1 \
  --query 'cluster.{status:status,health:health}'
```

In the console, open EKS → Clusters → `day28-eks-lab`; inspect status and events. Check selected subnets, IAM role and reported configuration errors. Wait for provisioning; do not repeatedly create clusters with new names.

For Floci, use the supported `describe-cluster` API and Floci status/logging tools for that version. Emulator status is not proof of an AWS cluster.

## 4. Nodes are missing or `NotReady`

```bash
kubectl get nodes -o wide
kubectl describe nodes
kubectl get pods -A
kubectl get events -A --sort-by=.metadata.creationTimestamp
```

For real AWS:
1. EKS → cluster → Compute → node group; check node-group status.
2. Check EC2 instance state, node IAM role and cluster/node networking.
3. Verify node-group subnets are in the cluster VPC and meet EKS requirements.
4. Check instance type and capacity availability.

For Floci, distinguish a node-group metadata object from an actual Kubernetes node. A node group may exist in the emulator API while no node has joined the local Kubernetes engine.

## 5. Pod is `Pending`

**Common causes:** insufficient node capacity; scheduling constraints, node selectors or affinity; taints/tolerations mismatch; persistent volume or networking requirements.

```bash
kubectl get pods -o wide
kubectl describe pod POD_NAME
kubectl get nodes
kubectl get events --sort-by=.metadata.creationTimestamp
```

Replace `POD_NAME` with the real Pod name. Read the Events section at the bottom of `describe`; fix the cause rather than blindly increasing resources or creating nodes.

## 6. `ImagePullBackOff` / `ErrImagePull`

**Possible causes:** incorrect image name/tag, registry unavailable, authentication required, or node network/DNS issue.

```bash
kubectl describe pod POD_NAME
kubectl get events --sort-by=.metadata.creationTimestamp
```

Confirm the lab image is `nginx:stable`. In real AWS, check worker-node egress and registry access. Do not put registry passwords or AWS keys in a manifest.

## 7. Deployment does not reach two replicas

```bash
kubectl get deployments
kubectl describe deployment nginx-demo
kubectl get replicasets
kubectl get pods -l app=nginx-demo -o wide
kubectl rollout status deployment/nginx-demo --timeout=300s
```

Check desired/available replica counts, Pod events, image pull state and node capacity. The manifest should have `replicas: 2`; the selector must match the `app: nginx-demo` Pod labels.

## 8. Service has no endpoints

```bash
kubectl get services
kubectl describe service nginx-demo
kubectl get endpoints nginx-demo
kubectl get pods -l app=nginx-demo --show-labels
```

Check Service selector vs Pod labels, Pod readiness and whether `targetPort` matches the container's listening port. A Service with no ready matching Pods may have no usable endpoints.

## 9. LoadBalancer has no external address

This applies only if you intentionally created a `LoadBalancer` Service in real AWS.

```bash
kubectl get service nginx-demo
kubectl describe service nginx-demo
kubectl get events --sort-by=.metadata.creationTimestamp
```

Check subnet tagging/selection, networking, IAM permissions, controller prerequisites and Service events. Provisioning takes time and can incur charges. The cost-safe manifest uses `ClusterIP`, so no external address is expected.

## 10. Application times out

```bash
kubectl get pods -o wide
kubectl get services
kubectl get endpoints nginx-demo
kubectl describe service nginx-demo
kubectl logs deployment/nginx-demo
```

For port-forward testing:

```bash
kubectl port-forward service/nginx-demo 8080:80
```

Keep it running, then in another terminal:

```bash
curl -I --max-time 10 http://localhost:8080
```

For a real public load balancer, check target health, security rules, subnet routing and application port.

## 11. Floci-specific problems

### `aws eks list-clusters` works, but `kubectl get nodes` fails

The EKS API may return cluster metadata while Kubernetes authentication or the local API server is not ready.

1. Check `floci status` and Docker status.
2. Inspect the cluster using the supported Floci EKS API.
3. Check `kubectl config current-context`.
4. Confirm your Floci version supports EKS real mode and its documented authentication method.
5. Verify `kubectl get nodes` before deploying the app.

Do not infer a working cluster from `list-clusters` alone.

### Node-group creation succeeded but there are no nodes

A node-group record may not automatically create or join a worker in the emulator. Follow the exact worker-join/bootstrap workflow documented for your installed Floci version. Confirm with `kubectl get nodes`.

### Local endpoint unreachable

```bash
docker info
floci status
curl -i http://localhost:4566/
```

The root URL may not be a supported API path; an HTTP error from `/` alone does not prove every service is down. Verify the endpoint and health instructions for your Floci version.

## 12. Cleanup troubleshooting

### Kubernetes objects

```bash
kubectl delete -f deployment.yaml --ignore-not-found=true
```

### Real AWS cleanup order
1. Delete Kubernetes workloads.
2. Delete the EKS managed node group and wait for completion.
3. Delete the EKS cluster.
4. Inspect lab-created load balancers, target groups, NAT Gateways, Elastic IPs, EBS volumes and CloudFormation stacks.
5. Delete only resources belonging to this lab; preserve shared resources.
6. Review billing after cleanup because usage reporting can be delayed.

### Floci cleanup
Use the supported deletion workflow for the installed version. Verify with list APIs and Kubernetes state. Avoid `floci reset` unless you intend to clear all simulated resources, including other labs.

## 13. Example troubleshooting record

**Scenario:** `kubectl get nodes` returns `the server has asked for the client to provide credentials`.

**Status:** Mark *observed* only if it happened in your lab; otherwise label it *simulated*.

**Likely layer:** Kubernetes API authentication or kubeconfig/identity configuration.

**Investigation:**

```bash
kubectl config current-context
kubectl config get-contexts
kubectl cluster-info
```

For real AWS:

```bash
aws sts get-caller-identity
aws eks describe-cluster --name day28-eks-lab --region us-east-1
aws eks update-kubeconfig --region us-east-1 --name day28-eks-lab
```

For Floci, confirm local endpoint, version/mode and authentication workflow.

**Resolution principle:** fix the identity/context/authentication layer; do not recreate resources or switch to real AWS credentials without diagnosis.

## References

- `DevOps_Winter_Arc_Day28_AWS_EKS.pdf`, pages 1–3.
- [EKS troubleshooting](https://docs.aws.amazon.com/eks/latest/userguide/troubleshooting.html)
- [Connect kubectl to an EKS cluster](https://docs.aws.amazon.com/eks/latest/userguide/create-kubeconfig.html)
- [Amazon EKS pricing](https://aws.amazon.com/eks/pricing/)
