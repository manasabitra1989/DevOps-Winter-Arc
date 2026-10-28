# Day 26 --- AWS RDS & Databases

**DevOps Winter Arc · 90 Days Challenge · AWS Week · Day 4**

> **Mission:** Understand managed relational databases and, if account
> permissions and budget allow, create a private Amazon RDS for
> PostgreSQL database reachable from EC2 only. Run SQL, create a manual
> snapshot, restore it to a new database instance, verify the data, and
> clean up resources.

## Table of contents

-   [Objectives](#objectives)
-   [Architecture](#architecture)
-   [Key concepts](#key-concepts)
-   [Project structure](#project-structure)
-   [Cost and security precautions](#cost-and-security-precautions)
-   [AWS Console walkthrough](#aws-console-walkthrough)
-   [SQL lab](#sql-lab)
-   [Connect to RDS from EC2](#connect-to-rds-from-ec2)
-   [Snapshot, restore, and
    verification](#snapshot-restore-and-verification)
-   [Troubleshooting](#troubleshooting)
-   [Cleanup](#cleanup)
-   [Proof of work](#proof-of-work)
-   [Interview questions](#interview-questions)
-   [Completion checklist](#completion-checklist)

## Objectives

By completing this lab, I should be able to:

-   Explain Amazon RDS, PostgreSQL, DB subnet groups, DB Security
    Groups, backups, snapshots, Multi-AZ, and read replicas.
-   Explain why the database should remain private and why EC2 connects
    to it on TCP port `5432`.
-   Configure a DB Security Group that allows database traffic from the
    EC2 application's Security Group only.
-   Run SQL to create a table, insert a row, and query records.
-   Explain why restoring a snapshot creates a new RDS instance with a
    new endpoint.
-   Check AWS costs and clean up resources created for the lab.

## Architecture

The intended design is **EC2 → private RDS PostgreSQL**. The database
must not accept direct public internet connections.

![RDS Architecture](RDS%20Architecture.png)

> Keep `RDS Architecture.png` in the same directory as this README so
> the image renders on GitHub. The diagram should show the client
> reaching EC2 through the approved access method, EC2 connecting to
> private RDS over TCP 5432, and the database Security Group allowing
> the EC2 application Security Group as its source.

``` text
Laptop / Administrator
        |
        | SSH from approved IP or Systems Manager Session Manager
        v
EC2 Linux instance (app-sg)
        |
        | PostgreSQL TCP 5432
        v
Private RDS PostgreSQL (db-sg)
        |
        +-- Public access: No

Internet --------------------X----> Private RDS
```

### Required network rule

  Setting                     Required value
  --------------------------- -------------------------------------
  Database engine             PostgreSQL
  Protocol                    TCP
  Port                        `5432`
  Inbound source on `db-sg`   EC2 application's Security Group ID
  RDS Public access           `No`

Never open database port `5432` to `0.0.0.0/0`. A private RDS endpoint
resolving to an address such as `172.31.x.x` is normal; that private IP
is not directly reachable from an ordinary laptop over the public
internet.

## Key concepts

  -----------------------------------------------------------------------
  Concept                             Explanation
  ----------------------------------- -----------------------------------
  **Amazon RDS**                      Managed relational database
                                      service. AWS manages much of the
                                      infrastructure, patching, backup,
                                      monitoring, and recovery
                                      capability; the user manages
                                      schema, queries, data, and access.

  **PostgreSQL**                      Relational database engine
                                      supporting SQL, tables, joins, and
                                      transactions.

  **DB subnet group**                 Collection of subnets in multiple
                                      Availability Zones that tells RDS
                                      where it may place a database. This
                                      lab calls for suitable subnets in
                                      at least two Availability Zones.

  **DB Security Group**               Network rules controlling access to
                                      the database. For this lab, allow
                                      TCP 5432 only from the EC2
                                      application Security Group.

  **Automated backups**               Support point-in-time recovery
                                      within the configured retention
                                      period (1--35 days, subject to
                                      configuration and service details).

  **Manual snapshot**                 Saved database backup retained
                                      until deleted. Restoring it creates
                                      a separate DB instance.

  **Multi-AZ**                        Primarily provides high
                                      availability and automatic
                                      failover. The classic Multi-AZ
                                      standby does not serve read
                                      traffic.

  **Read replica**                    Asynchronous copy mainly used to
                                      scale reads; replication can lag.

  **DynamoDB**                        Managed NoSQL key-value/document
                                      database for predictable access
                                      patterns; not designed around
                                      relational joins.

  **Aurora**                          Cloud-optimized relational database
                                      compatible with MySQL/PostgreSQL,
                                      where the cost and features suit
                                      the workload.

  **ElastiCache**                     In-memory caching for frequently
                                      accessed data, sessions, and rate
                                      limiting.

  **Self-managed DB on EC2**          Offers OS-level control, but the
                                      operator is responsible for
                                      database patching, backups,
                                      monitoring, and operations.
  -----------------------------------------------------------------------

## Project structure

Recommended structure:

``` text
day26-rds-databases/
├── README.md
├── RDS Architecture.png
├── lab.sql
└── notes/
    ├── rds-creation-notes.md
    └── cost-note.md
```

If the SQL file is stored under `notes/` instead, adjust the path
accordingly. Never store passwords or AWS access keys in this
repository.

## Cost and security precautions

RDS instances, storage, automated backups, manual snapshots, data
transfer, public IPv4 addresses, and related networking may incur
charges. A budget alert is not a spending cap.

Before creating resources:

1.  Review current RDS PostgreSQL pricing for the chosen Region and
    configuration.
2.  Review storage, backup/snapshot, and related networking charges.
3.  Confirm the account's budget and permissions.
4.  Use one Region consistently.
5.  Avoid a NAT Gateway or Multi-AZ setup for this practice unless there
    is a specific need and the cost is understood.
6.  Keep RDS Public access set to `No`.
7.  Use a strong database password and store it securely. Prefer Secrets
    Manager or IAM database authentication where supported.
8.  Never put passwords in shell commands, shell history, scripts, Git,
    screenshots, or chat.

## AWS Console walkthrough

### 1. Identify the EC2 instance and VPC

In **EC2 → Instances**, select the Region used for this lab and record:

-   EC2 instance state and instance ID.
-   VPC ID.
-   EC2 application's Security Group ID (`app-sg`).
-   Subnet ID and Availability Zone.
-   Whether the EC2 instance is still running and reachable.

The Day 25 EC2 instance may have been terminated during cleanup. Do not
assume it still exists or recreate it without reviewing costs. If there
is no reachable EC2 instance, use the concept-only path until you decide
whether to create an appropriate instance.

### 2. Verify suitable subnets

In **VPC → Subnets**, confirm that the intended VPC has suitable subnets
in at least two Availability Zones for the DB subnet group. If suitable
subnets do not exist, the Day 26 guide recommends not creating RDS just
for this lab.

### 3. Create the DB Security Group

In **EC2 → Security Groups** or **VPC → Security Groups**:

1.  Create a Security Group named `day26-db-sg` (or record the actual
    name used).
2.  Select the same VPC as the EC2 application.
3.  Add one inbound rule:
    -   Type: PostgreSQL
    -   Protocol: TCP
    -   Port: `5432`
    -   Source: the EC2 application's Security Group ID
4.  Save the rule.
5.  Do not add a rule that exposes port 5432 to the public internet.

### 4. Create the RDS database

In **RDS → Databases → Create database**:

1.  Choose **PostgreSQL**.
2.  Choose a supported development/test configuration after reviewing
    its current cost.
3.  Set a unique DB identifier, for example `day26-postgres`.
4.  Choose a database username and create a strong password. Store the
    password securely; do not add it to notes.
5.  Select the intended VPC and DB subnet group.
6.  Set **Public access = No**.
7.  Attach `day26-db-sg`.
8.  Set automated backup retention to 7 days if supported by the
    selected configuration.
9.  Avoid Multi-AZ for this cost-conscious lab unless it is justified
    and priced.
10. Review the final configuration and costs, then create the database.
11. Wait for status **Available**.
12. Copy the RDS endpoint from **Connectivity & security**. The endpoint
    is not a password and can be recorded in a private note if needed.

### 5. Verify database security

On the database's **Connectivity & security** page, verify:

-   Public access is **No**.
-   The expected VPC and DB subnet group are selected.
-   `day26-db-sg` is attached.
-   The DB Security Group inbound rule allows TCP 5432 from the EC2
    application Security Group.
-   The database status is `Available`.

## SQL lab

The following statements are also provided in `lab.sql`.

``` sql
CREATE TABLE lab_notes (
    id SERIAL PRIMARY KEY,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO lab_notes (note)
VALUES ('Day 26 RDS connection test');

SELECT id, note, created_at
FROM lab_notes
ORDER BY id;
```

### What the SQL does

-   `CREATE TABLE` creates a table named `lab_notes`.
-   `id SERIAL PRIMARY KEY` creates an automatically generated integer
    identifier and makes it the primary key.
-   `note TEXT NOT NULL` stores text and requires a value.
-   `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` records the
    insertion time by default.
-   `INSERT` adds the test record.
-   `SELECT` retrieves the records ordered by ID.

## Connect to RDS from EC2

The RDS endpoint is private. Connect from the EC2 instance inside the
intended VPC; do not try to make the database public just to connect
from a laptop.

### 1. Connect to EC2

Use the configured approved access method: - SSH with the Security Group
restricted to your current public IP; or - Systems Manager Session
Manager, if the instance has the required IAM role, agent, and network
connectivity.

If SSH times out, check that the instance is running, the public IP/DNS
is current, inbound TCP 22 allows your IP, and the subnet has the
required route. A timeout occurs before database authentication and does
not indicate a wrong PostgreSQL password.

### 2. Install the PostgreSQL client on Ubuntu EC2

``` bash
sudo apt-get update
sudo apt-get install -y postgresql-client
```

`apt-get update` refreshes package metadata. `apt-get install` installs
`psql`, the PostgreSQL command-line client.

### 3. Connect using an interactive password prompt

Replace the endpoint and username with the actual values from RDS:

``` bash
psql "host=YOUR_RDS_ENDPOINT port=5432 dbname=postgres user=YOUR_DB_USER sslmode=require" -W
```

`-W` prompts for the password. Do not place the password directly in the
command, because command lines may be stored in shell history or exposed
through process inspection.

### 4. Run the SQL

At the `psql` prompt, run the SQL from `lab.sql`. Confirm the `SELECT`
returns the row:

`Day 26 RDS connection test`

Exit `psql` with:

``` sql
\q
```

## Snapshot, restore, and verification

### 1. Create a manual snapshot

In **RDS → Databases**, select the original DB and choose **Actions →
Take snapshot**. Use a name such as `day26-before-restore`. Wait for the
snapshot to become **Available**.

### 2. Add a row after the snapshot

Connect to the original database from EC2 and run:

``` sql
INSERT INTO lab_notes (note)
VALUES ('Added after snapshot');

SELECT id, note, created_at
FROM lab_notes
ORDER BY id;
```

The original database should now have the original test row plus the row
added after the snapshot.

### 3. Restore to a separate instance

In **RDS → Snapshots**:

1.  Select `day26-before-restore`.
2.  Choose **Restore snapshot**.
3.  Use a different identifier, for example `day26-postgres-restored`.
4.  Keep Public access set to **No**.
5.  Select the intended VPC/subnet group and attach the correct DB
    Security Group.
6.  Review cost settings and confirm the restore.
7.  Wait until the restored instance is **Available**.

Restore creates a new DB instance; it does not overwrite the original.
The restored instance has a different endpoint.

### 4. Verify the restored data

Connect from EC2 using the **restored instance's endpoint**:

``` bash
psql "host=YOUR_RESTORED_RDS_ENDPOINT port=5432 dbname=postgres user=YOUR_DB_USER sslmode=require" -W
```

Run:

``` sql
SELECT id, note, created_at
FROM lab_notes
ORDER BY id;
```

Expected result: - `Day 26 RDS connection test` should be present. -
`Added after snapshot` should not be present, because it was inserted
after the snapshot was taken.

This demonstrates snapshot-based recovery to a point in time.

## Troubleshooting

  -----------------------------------------------------------------------
  Symptom                             Likely checks
  ----------------------------------- -----------------------------------
  `psql` times out                    Ensure command is run from EC2 in
                                      the intended VPC; verify DB status,
                                      VPC, routes, DB subnet group, DB
                                      Security Group TCP 5432 source, and
                                      Network ACLs.

  Host resolves to `172.31.x.x`       That is a private address; it is
                                      expected for a private endpoint. It
                                      is not directly reachable from an
                                      ordinary laptop over the internet.

  SSH to EC2 times out                Check instance state, current
                                      public IP/DNS, inbound SSH source,
                                      subnet route to Internet Gateway,
                                      and Network ACLs.

  Password authentication failed      Network connectivity is working far
                                      enough to reach PostgreSQL; verify
                                      username and retrieve the current
                                      password securely.

  RDS is still creating               Wait until status is `Available`;
                                      provisioning can take several
                                      minutes or longer.

  Restored DB has a different         Expected. Use the new endpoint when
  endpoint                            reconnecting.

  EC2 cannot retrieve a secret        Check least-privilege IAM
                                      permissions and network access to
                                      Secrets Manager.

  Table does not exist                Verify the connected DB name, user,
                                      and whether the `CREATE TABLE`
                                      statement completed.
  -----------------------------------------------------------------------

Useful network test from EC2 (install `netcat-openbsd` on Ubuntu if
needed):

``` bash
getent hosts YOUR_RDS_ENDPOINT
nc -vz -w 5 YOUR_RDS_ENDPOINT 5432
```

Interpretation: - `succeeded`: TCP connectivity to port 5432 works. -
`timed out`: inspect networking and Security Group rules. -
`connection refused`: the destination is reachable but is not accepting
the connection.

## What happened during this lab

Record actual results honestly. Based on the troubleshooting observed
during this lab:

-   An attempt to run `psql` from the WSL terminal resolved the RDS
    endpoint to a private IP (`172.31.21.214`) and timed out on
    port 5432. This is consistent with attempting to reach a private RDS
    endpoint from outside its VPC.
-   An SSH attempt from Windows to the EC2 public DNS name also timed
    out on port 22.
-   These timeouts do **not** prove that the database password is wrong.
    The network path/access to EC2 and RDS must be verified first.
-   Do not mark SQL execution, snapshot/restore verification, or cleanup
    complete unless you actually performed and verified those steps.
-   Do not make RDS public as a workaround. If the Day 25 EC2 instance
    was terminated, decide whether to create a replacement only after
    checking cost and configuration.

## Cleanup --- do not skip

After capturing proof:

1.  Delete the original RDS instance created for the lab.
2.  Review final-snapshot options carefully to avoid creating unwanted
    extra snapshots.
3.  Delete the restored RDS instance.
4.  Delete the manual snapshot once evidence is saved and the snapshot
    is no longer needed.
5.  Check **RDS → Databases** and **RDS → Snapshots** for remaining lab
    resources.
6.  Remove `day26-db-sg` and the DB subnet group only if no remaining
    resources use them.
7.  Do not delete shared VPCs, EC2 instances, IAM roles, or Security
    Groups from earlier days unless you are certain they are lab-only
    and unused.
8.  Review billing later; charges can be finalized after deletion.

### Optional AWS CLI inventory commands

Run only after confirming that AWS CLI is authenticated to the intended
real AWS account and Region. Do not run these while unintentionally
using Floci credentials or endpoints.

``` bash
export AWS_REGION="us-east-1"  # Replace if your resources are in another Region

aws sts get-caller-identity

aws rds describe-db-instances \
  --region "$AWS_REGION" \
  --query 'DBInstances[].{ID:DBInstanceIdentifier,Status:DBInstanceStatus,Public:PubliclyAccessible,Endpoint:Endpoint.Address}' \
  --output table

aws rds describe-db-snapshots \
  --region "$AWS_REGION" \
  --query 'DBSnapshots[].{Snapshot:DBSnapshotIdentifier,Status:Status,DB:DBInstanceIdentifier}' \
  --output table
```

These commands list resources; they do not delete anything. Review
output before taking action.

## Proof of work

Save 3--5 useful screenshots in `screenshots/`:

-   [ ] RDS configuration showing **Public access = No**.
-   [ ] DB Security Group inbound rule showing the EC2 Security Group as
    source.
-   [ ] Successful SQL query from EC2.
-   [ ] Restore verification showing the original row and absence of the
    post-snapshot row.
-   [ ] Cleanup proof showing no lab databases or snapshots remain.

Hide account IDs and never show database passwords, AWS credentials,
session tokens, or private keys.

## Interview questions from the Day 26 PDF

**1. What does RDS manage?**\
AWS manages much of the database infrastructure, patching, backups,
monitoring, and recovery features. The user manages schema, queries,
data, and access.

**2. Multi-AZ vs. read replica?**\
Multi-AZ is mainly for high availability and automatic failover. A read
replica is asynchronous and scales read traffic; replication may lag.

**3. How do you keep RDS private?**\
Use private networking where appropriate, set Public access to No, and
allow the DB port only from the application Security Group.

**4. How do RDS backups work?**\
Automated backups support point-in-time recovery within retention.
Manual snapshots remain until deleted. Restoring a snapshot creates a
new instance.

**5. RDS vs. Aurora?**\
Both support relational workloads. Aurora is cloud-optimized and may
offer higher performance or faster failover, but can cost more.

**6. When choose DynamoDB over RDS?**\
Choose DynamoDB for high-scale key-value/document access with
predictable patterns and no relational joins. Choose RDS for SQL, joins,
and transactions.

**7. How should DB credentials be managed?**\
Use Secrets Manager with suitable rotation or IAM database
authentication where supported. Never hardcode credentials.

**8. How can you test a database change safely?**\
Take a snapshot, restore a separate test instance, verify the change,
then plan a controlled rollout.

## Additional commonly asked RDS / database interview questions

These questions expand beyond the supplied PDF for interview practice.

**9. What is a relational database?**\
A database that organizes data into tables with defined relationships
and commonly uses SQL to query and modify it.

**10. What is a primary key?**\
A column or set of columns that uniquely identifies each row in a table.
It must be unique and cannot be NULL.

**11. What is a foreign key?**\
A constraint that references a key in another table (or the same table)
to help enforce referential integrity.

**12. What is an index?**\
A data structure that can speed up selected queries, often at the cost
of additional storage and slower writes or index maintenance.

**13. What is a database transaction?**\
A group of operations treated as a unit. ACID describes atomicity,
consistency, isolation, and durability.

**14. What is the difference between a backup and a read replica?**\
A backup supports recovery from a past state. A read replica is a live
asynchronous copy mainly intended to scale reads; it is not a substitute
for backups.

**15. What does "private RDS" mean?**\
The DB is not directly exposed through a public endpoint for internet
clients. Network placement and access rules restrict which clients can
reach it.

**16. Why use a Security Group as the DB rule's source instead of an EC2
public IP?**\
It ties permission to the EC2 workload's Security Group membership
rather than depending on a potentially changing IP address.

**17. Why does a restored database have a new endpoint?**\
Restore creates a separate DB instance with its own network endpoint; it
does not overwrite the original instance.

**18. What should you check first when `psql` times out?**\
Confirm the command runs from a network location that can reach the
private endpoint, then check DB status, VPC/subnets, Security Group
source and port, routes, and Network ACLs. Password checks come after
TCP connectivity works.

**19. What is point-in-time recovery (PITR)?**\
A recovery option that restores a database to a specific supported time
within its automated backup retention window.

**20. Why should database passwords not be hardcoded?**\
Hardcoded credentials can leak through source control, logs, images, or
shell history. Use a managed secret or supported IAM authentication
instead.

## Completion checklist

-   [ ] I can explain RDS, PostgreSQL, DB subnet groups, and DB Security
    Groups.
-   [ ] I understand why RDS should not be publicly accessible for this
    lab.
-   [ ] I can explain Multi-AZ vs. read replicas.
-   [ ] I prepared the SQL file and architecture diagram.
-   [ ] If resources were created, I verified Public access = No and the
    TCP 5432 source rule.
-   [ ] If connectivity succeeded, I ran and verified the SQL test from
    EC2.
-   [ ] If a snapshot was created, I restored a separate instance and
    verified the expected row.
-   [ ] I recorded costs and saved evidence without secrets.
-   [ ] I verified cleanup of lab RDS instances and snapshots.

------------------------------------------------------------------------

**Day 26 status:** The private RDS endpoint was attempted from WSL and
timed out; SSH to the EC2 public hostname also timed out. Treat SQL
execution and snapshot/restore as **not yet verified** until access is
restored and the tests succeed. Keep the database private while
troubleshooting.
