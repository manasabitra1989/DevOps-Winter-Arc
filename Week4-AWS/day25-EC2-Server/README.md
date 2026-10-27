# Day 25 --- AWS EC2 Server

**DevOps Winter Arc · 90 Days Challenge · AWS Week · Day 3**

> **Mission:** Launch and secure a Linux virtual server, bootstrap Nginx
> with User Data, connect to the instance, understand EBS storage, and
> clean up lab resources.

## Learning objectives

-   Explain EC2, AMIs, instance types, key pairs, Security Groups, User
    Data, EBS, and Systems Manager Session Manager.
-   Launch a Linux EC2 instance and configure network access safely.
-   Install and start Nginx automatically using User Data.
-   Verify the web server and diagnose public connectivity problems.
-   Terminate the instance and check for remaining billable resources.

## Cost and security warning

EC2, EBS, public IPv4 addresses, snapshots, data transfer, and related
resources may incur charges. A budget alert is **not** a hard spending
cap. Review current pricing and account eligibility before creating
resources.

-   Use one AWS Region consistently.
-   Never allow SSH (TCP 22) from `0.0.0.0/0`.
-   For this temporary public demo, allow HTTP (TCP 80) only as needed.
-   Keep private keys and AWS credentials outside Git repositories.
-   Terminate the instance when finished and check for leftover volumes,
    snapshots, and Elastic IPs.
-   Do not delete resources belonging to other projects.

## Key concepts

  -----------------------------------------------------------------------
  Concept                             Meaning
  ----------------------------------- -----------------------------------
  **EC2**                             AWS service providing virtual
                                      servers called instances.

  **AMI**                             Amazon Machine Image; a template
                                      used to launch an instance.

  **Instance type**                   Defines CPU, memory, networking,
                                      and other capacity characteristics.

  **Key pair**                        Public/private key pair used for
                                      supported SSH authentication. Keep
                                      the private key secret.

  **Security Group**                  Stateful virtual firewall
                                      associated with an instance's
                                      network interface.

  **User Data**                       Startup script commonly used to
                                      install packages and configure an
                                      instance during initial boot.

  **EBS**                             Persistent block storage for EC2;
                                      volumes and snapshots may incur
                                      charges.

  **Session Manager (SSM)**           Can provide access without inbound
                                      SSH when IAM role, agent, and
                                      network prerequisites are
                                      configured.

  **Network ACL**                     Stateless subnet-level network
                                      filter; return traffic must be
                                      permitted by rules.

  **IMDSv2**                          Instance metadata mode that
                                      requires a session token for
                                      metadata requests.
  -----------------------------------------------------------------------

## Architecture

``` text
Browser
   |
   | HTTP :80
   v
Public IPv4 address
   |
   v
EC2 instance / Security Group
   |
   v
Nginx web server
   |
   v
HTML page in the instance's web root
```

Direct public access requires a public IPv4 address, a suitable Security
Group rule, a subnet route to an Internet Gateway, and Network ACL rules
that permit traffic.

## Project setup

Recommended directory:

``` text
~/DevOps-Winter-Arc/Week4-AWS/day25-EC2-Server/
├── README.md
├── user-data.sh
├── notes/
└── screenshots/
```

``` bash
cd ~/DevOps-Winter-Arc/Week4-AWS/day25-EC2-Server
mkdir -p notes screenshots
bash -n user-data.sh
chmod +x user-data.sh
```

`bash -n` checks syntax without running the script. User Data is
intended to run on EC2, not directly on WSL.

## User Data script

``` bash
#!/bin/bash
set -eux

# Install Nginx using the package manager available on the AMI.
if command -v dnf >/dev/null 2>&1; then
    dnf install -y nginx
elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -y
    apt-get install -y nginx
else
    echo "No supported package manager found" >&2
    exit 1
fi

# Select the standard Nginx document root.
if [ -d /usr/share/nginx/html ]; then
    WEB_ROOT=/usr/share/nginx/html
else
    WEB_ROOT=/var/www/html
fi

cat > "$WEB_ROOT/index.html" <<'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Day 25 - AWS EC2</title>
</head>
<body>
    <h1>Hello from AWS EC2</h1>
    <p>Day 25 - DevOps Winter Arc</p>
</body>
</html>
EOF

systemctl enable --now nginx
```

### Script explanation

-   `#!/bin/bash` selects Bash.
-   `set -eux` exits on errors, prints commands, and treats unset
    variables as errors.
-   `command -v` detects whether `dnf` or `apt-get` is available.
-   `WEB_ROOT` selects the standard web directory for the image.
-   The quoted heredoc writes the HTML page.
-   `systemctl enable --now nginx` starts Nginx and enables it at boot.

User Data normally runs during initial launch. Editing it later does not
automatically rerun the script on an existing instance.

## Launch checklist

In the AWS Console:

1.  Open **EC2 → Instances → Launch instances**.
2.  Select a supported Amazon Linux or Ubuntu AMI.
3.  Choose a suitable small instance type after reviewing current
    pricing and eligibility.
4.  Create/select a key pair if SSH is required; store its private key
    securely outside the repository.
5.  Configure networking and a Security Group.
6.  Review root EBS volume size, type, and **Delete on termination**.
7.  Under **Advanced details → User data**, paste the script above.
8.  Review settings and launch.
9.  Wait for state `Running` and successful status checks.
10. Copy the current **Public IPv4 address** from instance details.

### Suggested inbound rules

  Type             Protocol     Port Source
  ---------------- ---------- ------ -------------------------------------------
  HTTP             TCP            80 `0.0.0.0/0` for the temporary public demo
  SSH (optional)   TCP            22 Your current public IP only

Do not expose SSH to all IPv4 addresses. If SSH is unnecessary, leave
port 22 closed and consider Session Manager after configuring its
prerequisites.

## Verify the website

In a browser, visit:

``` text
http://YOUR_PUBLIC_IPV4
```

Use `http://` unless TLS has been configured separately. Expected page:

**Hello from AWS EC2**\
Day 25 - DevOps Winter Arc

### Commands to run on EC2 over SSH

``` bash
sudo systemctl status nginx --no-pager
sudo journalctl -u nginx --no-pager -n 50
sudo ss -lntp | grep ':80'
curl -I http://127.0.0.1
curl -s http://127.0.0.1 | head -n 20
sudo cat /usr/share/nginx/html/index.html
sudo tail -n 100 /var/log/cloud-init-output.log
sudo tail -n 100 /var/log/cloud-init.log
```

These inspect Nginx status, listening sockets, local HTTP response, page
content, and cloud-init/User Data logs.

### Optional AWS CLI checks

First verify that the CLI is authenticated to the intended real AWS
account:

``` bash
aws configure list
aws sts get-caller-identity
```

Set the actual Region where the instance exists:

``` bash
export AWS_REGION="us-east-1"  # Replace with your instance's Region

aws ec2 describe-instances \
  --region "$AWS_REGION" \
  --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name,Type:InstanceType,PublicIP:PublicIpAddress}' \
  --output table
```

A Region is not an Availability Zone: `us-east-1` is a Region, while
`us-east-1c` is an Availability Zone. If `aws configure list` shows
environment credentials ending in `test`, or you ran
`eval "$(floci env)"`, the CLI may still be using Floci's simulated
credentials. Verify identity and endpoint configuration before managing
real AWS resources. Never paste credentials into notes or chat.

## Troubleshooting

  -----------------------------------------------------------------------
  Symptom                             Checks
  ----------------------------------- -----------------------------------
  Public website cannot be reached    Verify current public IPv4, inbound
                                      HTTP rule, subnet route to an
                                      attached Internet Gateway, and
                                      Network ACL rules.

  Nginx runs but site is unreachable  Run `curl -I http://127.0.0.1` on
                                      EC2. If local HTTP works,
                                      investigate networking before
                                      reinstalling Nginx.

  Local `curl` times out              Check public IP, route table,
                                      Security Group, Network ACL, and
                                      whether the subnet is public.

  Connection refused                  Verify Nginx is listening on port
                                      80 and confirm the IP is correct.

  User Data failed                    Inspect
                                      `/var/log/cloud-init-output.log`
                                      and `/var/log/cloud-init.log`.

  SSH timeout                         Check port 22 source restriction,
                                      public IP, subnet route, and status
                                      checks.

  SSH permission denied               Check private key, selected key
                                      pair, key file permissions, and AMI
                                      username.

  SSM unavailable                     Verify instance IAM role, SSM
                                      Agent, and network connectivity.

  Unexpected storage charges          Inspect EBS volumes, snapshots, and
                                      retained resources.
  -----------------------------------------------------------------------

Networking reminders:

-   A private IP such as `172.31.x.x` is not a public IPv4 address.
-   A public IP alone is insufficient without a valid Internet Gateway
    route and permissive network rules.
-   Security Groups are stateful; Network ACLs are stateless and need
    suitable return-traffic rules, including ephemeral ports where
    required.
-   Do not recreate the instance before checking logs and the network
    path.

## EBS storage notes

In **EC2 → Instances → Storage**, inspect the root volume ID, size,
type, and deletion setting.

-   **Stop:** instance stops; EBS generally persists and may still incur
    charges.
-   **Terminate:** instance is deleted; attached volumes are handled
    according to their deletion settings.
-   **Snapshot:** point-in-time backup of an EBS volume.
-   **AMI:** image used to launch instances; it may reference snapshots
    and other launch information.

If inspecting disks inside Linux, run `lsblk` first. Do not guess device
names or format the root disk during this lab.

## Cleanup --- do not skip

After capturing evidence:

1.  Open **EC2 → Instances**.
2.  Select only the instance created for this lab.
3.  Choose **Instance state → Terminate instance** and confirm.
4.  Wait for termination.
5.  Inspect **EC2 → Volumes** for leftover lab volumes.
6.  Inspect **Snapshots** for snapshots created during this lab.
7.  Inspect **Elastic IPs** and release lab allocations no longer
    needed.
8.  Review other lab-created resources and billing later; billing
    information can be delayed.

Do not delete resources from other projects. Stopping an instance is not
equivalent to terminating it.

Optional CLI checks:

``` bash
aws ec2 describe-instances \
  --region "$AWS_REGION" \
  --query 'Reservations[].Instances[].{ID:InstanceId,State:State.Name}' \
  --output table

aws ec2 describe-volumes \
  --region "$AWS_REGION" \
  --query 'Volumes[].{ID:VolumeId,State:State,Size:Size}' \
  --output table

aws ec2 describe-addresses \
  --region "$AWS_REGION" \
  --output table
```

These commands list resources; they do not clean them up automatically.
Review results before taking action.

## Proof of work

Save relevant screenshots in `screenshots/`:

-   [ ] Browser showing the Nginx page via public IPv4.
-   [ ] EC2 details showing `Running` and successful status checks.
-   [ ] EBS root volume details.
-   [ ] Final EC2 instance list after termination and cleanup.

Hide account IDs, email addresses, and private key material before
sharing screenshots publicly. No GitHub submission is required unless
the challenge instructions separately request it.

## Interview questions and answers

**1. What is EC2?**\
AWS compute service that provides virtual servers called instances.

**2. What is an AMI?**\
A template used to launch an instance, including operating-system and
image configuration.

**3. What is a Security Group?**\
A stateful virtual firewall associated with an instance's network
interface.

**4. Security Group vs. Network ACL?**\
A Security Group is stateful and operates at the
instance/network-interface level. A Network ACL is stateless and
operates at the subnet level.

**5. What is User Data?**\
Startup configuration commonly used to install software and bootstrap an
instance during initial launch.

**6. Stop vs. terminate?**\
Stopping generally preserves EBS storage. Termination deletes the
instance and handles attached volumes according to their deletion
settings.

**7. Snapshot vs. AMI?**\
A snapshot backs up an EBS volume. An AMI is used to launch instances
and may reference snapshots.

**8. How can you connect without port 22?**\
Use Systems Manager Session Manager if the required IAM role, agent, and
network prerequisites are configured.

**9. Why use IMDSv2?**\
It requires a session token for metadata requests and helps protect
against some metadata-access abuse scenarios.

## Completion checklist

-   [ ] I can explain EC2, AMIs, instance types, Security Groups, User
    Data, EBS, and Session Manager.
-   [ ] I reviewed cost and billing settings before launch.
-   [ ] I restricted SSH to my IP if SSH was needed.
-   [ ] Instance status checks passed.
-   [ ] Nginx was running and the page loaded using public IPv4.
-   [ ] I inspected the root EBS volume.
-   [ ] I captured proof-of-work screenshots.
-   [ ] I terminated the lab instance and checked for leftover volumes,
    snapshots, and Elastic IPs.
-   [ ] I kept credentials and private keys secure.

------------------------------------------------------------------------

**Day 25 status:** The Nginx Welcome Page was eventually visible through
the instance's public IP after troubleshooting. Complete and verify the
cleanup checklist before considering the lab fully closed.
