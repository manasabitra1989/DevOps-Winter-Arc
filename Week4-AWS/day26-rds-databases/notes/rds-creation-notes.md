# Day 26 — RDS Creation Notes

## Goal
Create a private Amazon RDS for PostgreSQL database reachable from the EC2 application instance only, test SQL, then snapshot and restore.

## Before creating resources
- [ ] Confirm AWS account and Region.
- [ ] Review current RDS, storage, backup/snapshot, public IPv4, and networking costs.
- [ ] Confirm the budget allows the lab.
- [ ] Identify the EC2 instance, VPC ID, and EC2 application Security Group ID.
- [ ] Confirm suitable subnets exist in at least two Availability Zones for the DB subnet group.
- [ ] Never put passwords or AWS credentials in this file, scripts, screenshots, or Git.

## Console creation steps
1. Open **RDS → Databases → Create database**.
2. Choose **PostgreSQL** and a suitable development/test configuration after checking pricing.
3. Set a unique DB identifier (example: `day26-postgres`).
4. Choose a database username. Set a strong password and store it securely; do not record it here.
5. Select the intended VPC and a DB subnet group with suitable subnets in at least two Availability Zones.
6. Set **Public access** to **No**.
7. Attach a DB Security Group (example: `day26-db-sg`).
8. In that Security Group, allow inbound **PostgreSQL / TCP 5432** from the **EC2 application Security Group only**. Never use `0.0.0.0/0`.
9. Configure automated backup retention to 7 days if supported.
10. Avoid Multi-AZ and NAT Gateway for this cost-conscious lab unless specifically needed and priced.
11. Review the final configuration and estimate, then create the database.
12. Wait for status **Available**. Record the endpoint if needed, but never record the password here.

## Connect and test from EC2
1. Ensure EC2 is running and reachable by the approved method (SSH restricted to your IP or configured Systems Manager Session Manager).
2. On Ubuntu EC2, install the client if needed: `sudo apt-get update && sudo apt-get install -y postgresql-client`
3. Copy the RDS endpoint from **RDS → Databases → Connectivity & security**.
4. From EC2, connect using an interactive password prompt:
   `psql "host=YOUR_RDS_ENDPOINT port=5432 dbname=postgres user=YOUR_DB_USER sslmode=require" -W`
5. Run the SQL in `lab.sql`.
6. For a timeout, check the VPC, database status, DB Security Group TCP 5432 source, routes, and Network ACLs. Do not make RDS public to work around the problem.

## Snapshot and restore
1. Select the original DB in **RDS → Databases → Actions → Take snapshot**.
2. Name it `day26-before-restore` and wait for **Available**.
3. Insert a second test row into the original DB after the snapshot.
4. Restore the snapshot to a separate DB, e.g. `day26-postgres-restored`.
5. Keep it private and attach the correct DB Security Group.
6. Wait for **Available** and connect using the restored instance's new endpoint.
7. Query `lab_notes`: the original row should exist; the row inserted after the snapshot should not.

## Cleanup
1. Save evidence without exposing credentials.
2. Delete the original and restored RDS instances. Review final-snapshot options carefully to avoid unintentionally creating extra snapshots.
3. Delete the manual snapshot after evidence is saved and it is no longer needed.
4. Check **RDS → Databases** and **RDS → Snapshots** for remaining lab resources.
5. Remove the lab DB Security Group and DB subnet group only if no remaining resources use them.
6. Do not delete shared VPCs, EC2 instances, IAM roles, or Security Groups from earlier days unless certain they are lab-only and unused.
7. Review billing later; charges can appear after deletion.

## Lab status — update after verification
- Original RDS instance deleted: [ ] Yes [ ] No [ ] Not created
- Restored RDS instance deleted: [ ] Yes [ ] No [ ] Not created
- Manual snapshot deleted: [ ] Yes [ ] No [ ] Not created
- Leftover resources checked: [ ] Yes [ ] No
- Billing reviewed: [ ] Yes [ ] No
