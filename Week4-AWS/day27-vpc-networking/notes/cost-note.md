# Day 27 — Cost and Cleanup Note

> Fill this out from the actual AWS Console. Do not mark resources deleted until you verify.

## Pre-build cost review
- Region:
- EC2 pricing reviewed: [ ] Yes [ ] No
- Public IPv4 pricing reviewed: [ ] Yes [ ] No
- NAT Gateway hourly/data-processing pricing reviewed: [ ] Yes [ ] No
- Elastic IP and VPC endpoint pricing reviewed where applicable: [ ] Yes [ ] No
- Budget/alerts reviewed: [ ] Yes [ ] No
- Chosen path: [ ] Design only [ ] VPC only [ ] VPC + NAT [ ] VPC + EC2 tests

## Lab resource inventory
- VPC ID:
- IGW ID:
- Public route table ID:
- Private route table ID:
- NAT Gateway ID, if created:
- NAT Elastic IP allocation, if created:
- Public EC2 instance ID, if created:
- Private EC2 instance ID, if created:
- VPC endpoint IDs, if created:

## Cleanup verification
- [ ] Lab EC2 instances terminated or not created
- [ ] NAT Gateway deleted or not created
- [ ] NAT Elastic IP released if unused or not allocated
- [ ] Lab VPC endpoints removed or not created
- [ ] Lab route tables/subnets removed if appropriate
- [ ] Lab IGW detached and deleted if appropriate
- [ ] Unused lab Security Groups removed
- [ ] Lab VPC deleted if created exclusively for this exercise
- [ ] No unintended shared resources deleted
- [ ] Billing reviewed after cleanup

## Notes
Write the actual resources removed and any costs/estimates checked. Billing data may be delayed. Do not include credentials or private keys.
