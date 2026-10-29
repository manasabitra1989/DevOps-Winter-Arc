# Day 28 — Cost Notes

- EKS control plane, EC2 worker nodes, load balancers, storage, NAT Gateways, public IPv4 addresses and data transfer may incur charges.
- Free Tier eligibility and credits depend on the account and current offer; do not assume every component is free.
- A budget alert is not a hard spending cap.
- Use Floci/local Kubernetes for supported learning exercises when avoiding AWS charges.
- Prefer `ClusterIP` and port-forwarding for Nginx testing; a `LoadBalancer` Service may provision billable infrastructure.
- If real AWS resources were created, delete workloads, node group, cluster and lab-created dependencies. Verify in the console and review billing later.
- Never delete shared resources from previous days.
