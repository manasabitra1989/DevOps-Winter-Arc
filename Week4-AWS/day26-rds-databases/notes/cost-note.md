# Day 26 — Cost and Cleanup Note

> Complete this based on what you actually checked. Do not claim a resource was deleted unless you verified it in the AWS Console or CLI.

## Cost review
- AWS Region: `us-east-1` (confirm it matches your resources)
- RDS pricing for selected engine/class checked: [ ] Yes [ ] No
- Storage and automated backup pricing checked: [ ] Yes [ ] No
- Manual snapshot storage pricing checked: [ ] Yes [ ] No
- Related networking costs checked: [ ] Yes [ ] No
- Budget/alerts reviewed: [ ] Yes [ ] No
- Estimate or pricing notes: _Fill in the configuration and estimate you actually reviewed; do not guess._

## Resources created
- Original RDS DB identifier: `day26-postgres` (edit if different)
- Restored RDS DB identifier: `day26-postgres-restored` (if created)
- Manual snapshot: `day26-before-restore` (if created)
- DB Security Group: `day26-db-sg` (if created)
- DB subnet group: _Record actual name if created._

## Cleanup verification
- [ ] Original RDS instance deleted, or confirmed not created
- [ ] Restored RDS instance deleted, or confirmed not created
- [ ] Manual snapshot deleted, or confirmed not created
- [ ] RDS → Databases checked for remaining lab databases
- [ ] RDS → Snapshots checked for remaining lab snapshots
- [ ] Lab DB Security Group removed only if unused
- [ ] Lab DB subnet group removed only if unused
- [ ] Shared EC2/VPC/IAM resources were not deleted accidentally
- [ ] Billing reviewed after cleanup (billing data can be delayed)

## Final result
Status: **Not recorded yet — complete after verifying cleanup.**

Never include database passwords, access keys, session tokens, or other secrets in this note.
