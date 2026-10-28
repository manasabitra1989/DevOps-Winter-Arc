# Day 27 — AWS VPC Networking

**DevOps Winter Arc · AWS Week · Day 5**

> **Mission:** Design and, if budget allows, build a VPC with two public subnets and two private subnets. Configure route tables, an Internet Gateway (IGW), optionally a NAT Gateway, plan secure access, test traffic paths, troubleshoot, and clean up all lab resources.

## Table of contents
- [Objectives](#objectives)
- [Architecture diagram](#architecture-diagram)
- [Concepts](#concepts)
- [CIDR plan](#cidr-plan)
- [Route-table matrix](#route-table-matrix)
- [Security plan](#security-plan)
- [Public and private IP plan](#public-and-private-ip-plan)
- [Task 1: Prepare the project](#task-1-prepare-the-project)
- [Task 2: Create the VPC and subnets](#task-2-create-the-vpc-and-subnets)
- [Task 3: Attach the IGW](#task-3-attach-the-igw)
- [Task 4: Configure route tables](#task-4-configure-route-tables)
- [Task 5: Optional NAT Gateway](#task-5-optional-nat-gateway)
- [Task 6: Optional EC2 tests](#task-6-optional-ec2-tests)
- [Task 7: Verify traffic paths](#task-7-verify-traffic-paths)
- [Task 8: Troubleshooting](#task-8-troubleshooting)
- [Task 9: Cleanup](#task-9-cleanup)
- [Evidence and deliverables](#evidence-and-deliverables)
- [Interview questions](#interview-questions)
- [Completion checklist](#completion-checklist)

## Objectives

- Explain VPCs, CIDR ranges, subnets, route tables, IGWs, NAT Gateways, Security Groups, and Network ACLs.
- Plan two public and two private subnets across two Availability Zones.
- Make a route-table matrix with local and default routes.
- Restrict administration access and avoid exposing SSH to the world.
- Identify which resources need public IPs and which should remain private.
- Optionally test a public and private EC2 instance and verify NAT egress.
- Document troubleshooting and verify cleanup.

## Architecture diagram

![AWS VPC Architecture](AWS%20VPC%20Architecture.png)

Keep the file named exactly `AWS VPC Architecture.png` in the same directory as this README so GitHub can render it.

```text
                         AWS Region
        +------------------------------------------------+
        | VPC: 10.0.0.0/16                               |
        |                                                |
Internet+--> Internet Gateway (IGW)                     |
        |             ^                                  |
        |             | default route from public RT     |
        |   +---------+-----------+                      |
        |   |                     |                      |
        | Public subnet A      Public subnet B            |
        | 10.0.1.0/24          10.0.2.0/24                |
        | (optional public     (optional public           |
        |  EC2 / NAT GW)        EC2)                      |
        |       ^                                        |
        |       | NAT Gateway (optional, paid)            |
        |       |                                        |
        | Private subnet A     Private subnet B           |
        | 10.0.11.0/24         10.0.12.0/24               |
        | (private EC2)        (private EC2)              |
        |                                                |
        +------------------------------------------------+
```

The diagram represents the intended design, not proof that resources were created. A subnet is not public just because of its name: the route table, addressing, and security rules determine actual reachability.

## Concepts

| Concept | Explanation |
|---|---|
| VPC | Isolated virtual network in an AWS Region. |
| CIDR | Notation for an IP address range, e.g. `10.0.0.0/16`. |
| Subnet | A range inside a VPC associated with one Availability Zone. |
| Route table | Rules that determine where traffic is sent; the most-specific matching route wins. |
| `local` route | Automatically created route for traffic within the VPC CIDR. |
| Internet Gateway (IGW) | Enables internet connectivity for appropriately addressed resources in a VPC. |
| NAT Gateway | Allows private resources to initiate outbound IPv4 connections without accepting unsolicited inbound connections. |
| Security Group | Stateful, resource/network-interface-level firewall with allow rules. |
| Network ACL (NACL) | Stateless subnet-level filter with numbered allow and deny rules. |
| Session Manager | Administrative access method that can avoid inbound SSH when IAM, agent, and network prerequisites are met. |

## CIDR plan

| Resource | CIDR | Tier | Availability Zone |
|---|---|---|---|
| VPC | `10.0.0.0/16` | VPC range | Region-wide |
| `day27-public-a` | `10.0.1.0/24` | Public | AZ A |
| `day27-public-b` | `10.0.2.0/24` | Public | AZ B |
| `day27-private-a` | `10.0.11.0/24` | Private | AZ A |
| `day27-private-b` | `10.0.12.0/24` | Private | AZ B |

The four `/24` ranges are contained within `10.0.0.0/16` and do not overlap each other. Before creating them, check that the VPC range does not overlap existing VPCs, on-premises networks, VPNs, or other networks you may connect to. AWS reserves some IP addresses in each subnet, so not every address in a subnet is assignable.

## Route-table matrix

| Route table | Subnet association | Destination | Target |
|---|---|---|---|
| Public RT (`day27-public-rt`) | Public A and B | `10.0.0.0/16` | `local` |
| Public RT (`day27-public-rt`) | Public A and B | `0.0.0.0/0` | IGW |
| Private RT (`day27-private-rt`) | Private A and B | `10.0.0.0/16` | `local` |
| Private RT (optional NAT design) | Private A and B | `0.0.0.0/0` | NAT Gateway |

For the no-NAT/no-cost design, the private route table has only the local route unless another approved egress path is configured. Do not add a route to a NAT Gateway that does not exist.

## Security plan

### Security Groups

| Group | Inbound plan | Outbound plan |
|---|---|---|
| Public test EC2 SG | Prefer Session Manager; if SSH is necessary, TCP 22 from your current public IP `/32` only. Add HTTP 80 only if serving a demo page. | Restrict as appropriate for the test; default outbound may be used for a short lab only if understood. |
| Private test EC2 SG | No public SSH rule. Prefer Session Manager with correct IAM/network prerequisites. | Allow only required outbound traffic, including required egress to NAT or SSM endpoints. |

Never expose SSH to `0.0.0.0/0`. Do not create broad inbound rules just to make a test work.

### Network ACLs

NACLs are stateless. If you customize them, allow the necessary inbound and outbound traffic, including response/ephemeral ports where needed. Keep the default NACL unless you understand the custom rules and their effect.

## Public and private IP plan

- Public test EC2: a public IPv4 address is optional but needed for direct public IPv4 access; it must also have an IGW route and suitable security rules.
- Private test EC2: **no public IPv4 address**.
- NAT Gateway: placed in a public subnet and associated with an Elastic IP for public IPv4 egress.
- IGW: attached to the VPC; it is not assigned to an EC2 instance.
- RDS or other private services: keep private unless there is a reviewed, explicit reason otherwise.

## Cost and safety warning

EC2 instances, public IPv4 addresses, NAT Gateways, Elastic IPs, VPC endpoints, data transfer, and related resources may incur charges. NAT Gateway is optional and can charge while provisioned. Review current regional pricing and account budget before building. A budget alert is not a spending cap.

If cost is uncertain, complete the CIDR plan, route matrix, and console review without creating NAT or EC2 resources.

## Task 1: Prepare the project

```bash
cd ~/DevOps-Winter-Arc/Week4-AWS
mkdir -p day5-vpc/notes day5-vpc/screenshots
cd day5-vpc
```

Save the CIDR plan and route-table matrix in `vpc-plan.md`. Keep cost and troubleshooting notes in `notes/`. Do not save credentials or private keys in this project.

## Task 2: Create the VPC and subnets

In the AWS VPC Console, choose the intended Region.

1. Open **Your VPCs → Create VPC**.
2. Choose **VPC only**.
3. Name it `day27-vpc`; IPv4 CIDR: `10.0.0.0/16`.
4. Create four subnets in this VPC, selecting two distinct Availability Zones:
   - `day27-public-a`: `10.0.1.0/24`
   - `day27-public-b`: `10.0.2.0/24`
   - `day27-private-a`: `10.0.11.0/24`
   - `day27-private-b`: `10.0.12.0/24`
5. Verify each subnet's CIDR, VPC, and AZ.
6. Confirm the ranges do not overlap existing networks you need to connect.

## Task 3: Attach the IGW

1. Open **Internet Gateways → Create internet gateway**.
2. Name it `day27-igw`.
3. Create it, select it, and choose **Actions → Attach to a VPC**.
4. Attach it to `day27-vpc`.

## Task 4: Configure route tables

### Public route table

1. Create `day27-public-rt` in `day27-vpc`.
2. Open **Routes → Edit routes**.
3. Add `0.0.0.0/0` with target `day27-igw`.
4. Save.
5. Under **Subnet associations**, associate `day27-public-a` and `day27-public-b`.
6. Verify the local route and IGW default route.

### Private route table

1. Create `day27-private-rt` in `day27-vpc`.
2. Associate `day27-private-a` and `day27-private-b`.
3. Keep the local route.
4. If using the no-NAT path, stop here. Private subnets won't have general outbound IPv4 internet access without another egress path.

## Task 5: Optional NAT Gateway

Only do this after checking pricing and accepting the cost.

1. Open **NAT Gateways → Create NAT gateway**.
2. Select a public subnet such as `day27-public-a`.
3. Allocate/select an Elastic IP.
4. Create the NAT Gateway and wait for **Available**.
5. Add `0.0.0.0/0 → NAT Gateway` to `day27-private-rt`.
6. Confirm the public route table still has `0.0.0.0/0 → IGW`.

The NAT Gateway must be in a public subnet whose route table points to the IGW. The private subnet's default route points to NAT. NAT permits outbound connections initiated by private resources; it does not provide unsolicited inbound access.

## Task 6: Optional EC2 tests

Only create test instances after reviewing EC2 and public IPv4 pricing.

### Public test instance

1. Open **EC2 → Launch instances**.
2. Name it `day27-public-ec2`.
3. Select a suitable Linux AMI and small instance type after checking pricing.
4. Choose VPC `day27-vpc` and subnet `day27-public-a`.
5. Enable auto-assign public IP if direct public IPv4 access is required.
6. Use a restricted Security Group. Prefer Session Manager; if SSH is required, permit TCP 22 from your current IP `/32` only.
7. Launch and wait for successful status checks.

### Private test instance

1. Launch a second suitable Linux instance named `day27-private-ec2`.
2. Select VPC `day27-vpc` and subnet `day27-private-a`.
3. Disable auto-assign public IP.
4. Do not create a public SSH rule.
5. Prefer Session Manager if the instance role, SSM Agent, and network connectivity are configured.
6. Launch and confirm the public IPv4 field is blank.

Session Manager may require an instance IAM role and network access to Systems Manager endpoints. A private instance without NAT or suitable endpoints may not be able to use Session Manager.

## Task 7: Verify traffic paths

1. **Public routes:** in `day27-public-rt`, confirm `10.0.0.0/16 → local` and `0.0.0.0/0 → IGW`.
2. **Subnet associations:** confirm both public subnets are associated with the public route table.
3. **Private routes:** if NAT was created, confirm `10.0.0.0/16 → local` and `0.0.0.0/0 → NAT`.
4. **Private associations:** confirm both private subnets use the private route table.
5. **Private IP:** in EC2 instance details, confirm `day27-private-ec2` has no public IPv4 address.
6. **NAT status:** confirm NAT Gateway status is `Available`, it is in a public subnet, and it has an Elastic IP.
7. If accessible from the private instance, test outbound IP:

```bash
curl -s --max-time 10 https://checkip.amazonaws.com
```

The output should match the NAT Gateway's Elastic IP. Run this from the private EC2 instance, not your laptop. If NAT was not created, this outbound test may fail by design.

## Task 8: Troubleshooting

| Symptom | Checks |
|---|---|
| Private instance cannot reach internet | Private route points to NAT; NAT is Available; NAT subnet has route to IGW; outbound SG and NACL allow required traffic. |
| Public instance unreachable | Public IPv4, public route to IGW, correct SG rule, NACL rules, instance status checks. |
| NACL allows inbound but traffic fails | NACL is stateless; inspect outbound rules and return/ephemeral ports, often `1024–65535`. |
| Session Manager fails | Instance IAM role, SSM Agent, DNS/network connectivity, NAT or SSM interface endpoints (`ssm`, `ssmmessages`, and where required `ec2messages`). |
| VPC deletion fails | Remove dependent instances/ENIs, NAT, endpoints, subnet associations, custom route tables, IGW, subnets, and unused SGs in the correct order. |
| VPC peering fails | Check CIDR overlap, routes on both sides, SG/NACL rules; peering is non-transitive. |
| NAT route exists but egress fails | Check NAT status, public subnet route to IGW, Elastic IP, private route association, SG egress, NACL return traffic, and DNS. |

For a controlled failure test, only change a route created exclusively for this lab. Record the failure, restore the route, and confirm recovery. Never alter shared or production routing.

## Task 9: Cleanup — mandatory

Delete only resources created specifically for Day 27.

1. Terminate lab EC2 instances.
2. Delete the NAT Gateway, if created, and wait for deletion to finish.
3. Release its Elastic IP when no longer associated or needed.
4. Delete lab VPC endpoints, if created.
5. Remove route-table associations, then delete custom route tables and subnets.
6. Detach and delete the lab IGW.
7. Delete lab Security Groups when unused.
8. Delete `day27-vpc` only if created exclusively for this lab and all dependencies are gone.
9. Verify there are no lab instances, NAT Gateways, or Elastic IP allocations left.
10. Review billing later; charges can be delayed.

Do not delete shared resources from earlier labs.

## Evidence and deliverables

Recommended folder:

```text
day5-vpc/
├── README.md
├── AWS VPC Architecture.png
├── vpc-plan.md
├── notes/
│   ├── troubleshooting.md
│   └── cost-note.md
└── screenshots/
    ├── vpc-subnets.png
    ├── public-route-table.png
    ├── private-route-table.png
    ├── private-instance.png
    ├── nat-egress-proof.png
    └── cleanup-proof.png
```

Capture only evidence for work actually completed:
- VPC and subnet CIDRs.
- Public route table with IGW route.
- Private route table with NAT route, if created.
- Private EC2 showing no public IPv4.
- NAT egress output matching the NAT Elastic IP, if tested.
- Cleanup proof.

Hide account IDs and credentials. Do not invent evidence for resources you skipped.

## Interview questions

### Questions from the Day 27 task

**1. What makes a subnet public?**  
Its route table has a default route to an Internet Gateway. Actual internet access also requires appropriate addressing and security rules.

**2. NAT Gateway vs. Internet Gateway?**  
An IGW enables internet connectivity for appropriately addressed resources. NAT Gateway enables private resources to initiate outbound IPv4 connections without allowing unsolicited inbound connections.

**3. Security Group vs. NACL?**  
A Security Group is stateful, resource-level, and allow-only. A NACL is stateless, subnet-level, and supports numbered allow and deny rules.

**4. How can a private instance access S3 without internet routing?**  
Use an S3 Gateway VPC Endpoint associated with its route table, subject to endpoint and IAM policies.

**5. How do you troubleshoot connection failures?**  
Check routes, Security Groups, NACLs, and whether the destination service is listening. VPC Flow Logs and Reachability Analyzer can help when available.

**6. How do you connect VPCs?**  
Use VPC peering for direct non-transitive connectivity or Transit Gateway for connecting multiple networks. Peering requires non-overlapping CIDRs and routes.

**7. Why spread subnets across Availability Zones?**  
To support resilient designs and reduce dependence on a single Availability Zone.

### Additional commonly asked questions

**8. What does CIDR `/16` mean?**  
The first 16 bits identify the network prefix. `10.0.0.0/16` contains 65,536 IPv4 addresses before AWS subnet reservations and other practical constraints.

**9. Does naming a subnet “public” make it public?**  
No. Routing, public addressing, and security rules determine reachability.

**10. Does NAT allow inbound connections from the internet?**  
Not unsolicited inbound connections. NAT is used for connections initiated by private resources.

**11. What is the `local` route?**  
It routes traffic within the VPC's CIDR ranges, subject to security controls.

**12. Routing vs. Security Group?**  
Routing determines where packets can travel. Security Groups determine which traffic is allowed to or from the resource.

**13. What does non-transitive VPC peering mean?**  
If A peers with B and B peers with C, A cannot automatically reach C through B.

**14. Why do NACLs need ephemeral-port rules?**  
NACLs are stateless, so response traffic must be allowed by separate rules; return traffic commonly uses ephemeral ports.

**15. Why prefer Session Manager over public SSH?**  
It can avoid opening inbound port 22 and can provide centrally controlled access when IAM, agent, and network prerequisites are configured.

**16. Why can a private instance lack internet access even when its route table has a NAT route?**  
The NAT Gateway may not be Available, its public subnet may lack an IGW route, the route table may not be associated correctly, or security/NACL/DNS settings may block traffic.

## Completion checklist

- [ ] I understand VPC, CIDR, subnets, route tables, IGW, and NAT.
- [ ] I checked CIDR ranges for overlap with networks I need to connect.
- [ ] I documented the four subnets and route-table matrix.
- [ ] I planned restricted Security Group and NACL rules.
- [ ] I reviewed costs before deciding whether to create NAT/EC2.
- [ ] If built, the public route table points to the IGW.
- [ ] If NAT was created, the private route table points to NAT.
- [ ] If tested, the private EC2 has no public IPv4.
- [ ] I recorded troubleshooting and saved appropriate evidence.
- [ ] I verified cleanup and completed the cost note.

**Status note:** This README documents the intended lab. Mark the build, traffic tests, and cleanup as complete only after verifying the actual AWS resources.
