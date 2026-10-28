# Day 27 — VPC Build Plan (Public and Private Instances)

## 0. Safety and cost gate
- Review current regional pricing before launching EC2, allocating public IPv4 addresses, or creating NAT Gateway.
- NAT Gateway has hourly and data-processing charges. If cost is uncertain, use the design-only path.
- Choose one AWS Region and use it for every resource in this lab.
- Never delete shared resources from previous labs.

## 1. CIDR and subnet plan

| Resource | CIDR | Tier | AZ |
|---|---|---|---|
| VPC `day27-vpc` | `10.0.0.0/16` | VPC | Region |
| `day27-public-a` | `10.0.1.0/24` | Public | AZ A |
| `day27-public-b` | `10.0.2.0/24` | Public | AZ B |
| `day27-private-a` | `10.0.11.0/24` | Private | AZ A |
| `day27-private-b` | `10.0.12.0/24` | Private | AZ B |

Before creating, check that `10.0.0.0/16` does not overlap with existing VPC, VPN, office, home, or on-premises networks that need connectivity.

## 2. Console build order
1. Create VPC `day27-vpc` with `10.0.0.0/16`.
2. Create the four subnets above in two distinct Availability Zones.
3. Create `day27-igw` and attach it to `day27-vpc`.
4. Create `day27-public-rt`; add `0.0.0.0/0 → IGW`; associate public-a and public-b.
5. Create `day27-private-rt`; associate private-a and private-b. Keep the local route.
6. Optional paid path: create NAT Gateway in public-a, allocate Elastic IP, wait for Available, then add `0.0.0.0/0 → NAT Gateway` to the private route table.
7. Optional paid path: launch a public EC2 in public-a with public IPv4 enabled and a private EC2 in private-a with public IPv4 disabled.
8. Prefer Session Manager when configured. If SSH is necessary, allow TCP 22 only from your current public IP `/32`; never `0.0.0.0/0`.
9. Verify route tables, subnet associations, private instance public-IP field, and NAT egress if configured.
10. Save evidence, then clean up.

## 3. Route-table matrix

| Route table | Subnets | Destination | Target |
|---|---|---|---|
| Public RT | public-a, public-b | `10.0.0.0/16` | `local` |
| Public RT | public-a, public-b | `0.0.0.0/0` | IGW |
| Private RT | private-a, private-b | `10.0.0.0/16` | `local` |
| Private RT (NAT option) | private-a, private-b | `0.0.0.0/0` | NAT Gateway |

Without NAT or another suitable egress path, private subnets do not have general outbound IPv4 internet access.

## 4. Security plan
- Public EC2: allow only required inbound traffic. Prefer Session Manager; if SSH is required, source must be your current IP `/32`.
- Private EC2: no public IPv4; no public SSH rule. Session Manager requires a suitable IAM role, SSM Agent, and network access.
- NACLs are stateless: verify both directions and response/ephemeral ports if custom rules are used.
- Keep databases and private workloads off public ingress.

## 5. Verification
- Public RT has local route and default route to IGW.
- Private RT has local route; if NAT exists, default route targets NAT.
- Both public subnets are associated with public RT.
- Both private subnets are associated with private RT.
- NAT is Available, in a public subnet, has an Elastic IP, and public RT routes to IGW.
- Private EC2 has no public IPv4.
- From private EC2, if NAT is configured:
  `curl -s --max-time 10 https://checkip.amazonaws.com`
  Output should match the NAT Elastic IP.

## 6. Cleanup order
1. Terminate lab EC2 instances.
2. Delete NAT Gateway and wait for deletion.
3. Release NAT Elastic IP if unused.
4. Delete lab VPC endpoints if created.
5. Remove route-table associations, then custom route tables and subnets.
6. Detach/delete lab IGW.
7. Delete unused lab Security Groups.
8. Delete VPC only if created exclusively for this lab and all dependencies are removed.
9. Verify no lab EC2, NAT, or Elastic IP resources remain.
10. Review billing later; billing data may be delayed.
