# Day 27 — VPC Networking Troubleshooting Guide

Use this checklist from top to bottom. Do not make a private resource public as a shortcut.

## A. Public EC2 cannot be reached
1. Confirm instance state is Running and status checks passed.
2. Confirm the current public IPv4 address is assigned.
3. Check the subnet is associated with the public route table.
4. Confirm public route table has `0.0.0.0/0 → IGW`.
5. Confirm the IGW is attached to the correct VPC.
6. Check the Security Group allows only the required port from the correct source IP.
7. Check NACL inbound and outbound rules, including return/ephemeral ports.
8. Confirm the service is listening on the instance.

## B. Private EC2 cannot reach the internet
1. Confirm the instance is in the intended private subnet and has no public IPv4.
2. Check the private subnet is associated with `day27-private-rt`.
3. Confirm `0.0.0.0/0 → NAT Gateway` exists if NAT is the selected egress path.
4. Confirm NAT Gateway state is Available and it is in a public subnet.
5. Confirm NAT's public subnet route table has `0.0.0.0/0 → IGW`.
6. Confirm NAT has an Elastic IP.
7. Check instance outbound Security Group rules and NACL return traffic.
8. Check DNS resolution and test the destination.
9. If no NAT or other egress path was configured, internet failure is expected.

## C. NAT route exists but test still fails
- Confirm the private route table is associated with the subnet containing the instance.
- Confirm the NAT target ID is the correct NAT Gateway.
- Confirm NAT is Available and not in deletion state.
- Confirm the public route table used by NAT has the IGW default route.
- Confirm NACLs permit required traffic in both directions.
- Confirm DNS works.
- Run `curl -v --max-time 10 https://checkip.amazonaws.com` from the private instance if you have approved access.

## D. Session Manager does not connect
1. Confirm the instance has an IAM role with the required Systems Manager permissions.
2. Confirm SSM Agent is installed and running.
3. Confirm the instance can reach required Systems Manager endpoints.
4. For private instances, configure NAT or suitable interface endpoints such as `ssm` and `ssmmessages` (and `ec2messages` where applicable).
5. Check DNS and endpoint Security Groups.
6. Do not open SSH to all addresses as a workaround.

## E. NACL troubleshooting
- NACLs are stateless, unlike Security Groups.
- Confirm inbound and outbound rules independently.
- Check rule numbers and whether an earlier matching rule changes the result.
- Allow required ephemeral return ports where applicable.
- Avoid changing shared subnet NACLs during a lab.

## F. VPC peering does not work
- Confirm CIDR ranges do not overlap.
- Confirm peering connection is active.
- Add routes on both VPC sides for the peer CIDR.
- Check Security Groups and NACLs.
- Remember VPC peering is non-transitive.

## G. VPC deletion fails
1. Terminate lab instances and remove dependent network interfaces.
2. Delete NAT Gateway and wait until deletion finishes.
3. Release its Elastic IP when unused.
4. Delete lab VPC endpoints.
5. Remove subnet associations and custom route tables.
6. Detach and delete the IGW.
7. Delete subnets and unused lab Security Groups.
8. Delete the VPC only when it has no dependencies.
9. Never delete shared resources from another project.

## Record an actual incident
- Symptom:
- Evidence:
- Root cause (only after verified):
- Fix:
- Verification after fix:
