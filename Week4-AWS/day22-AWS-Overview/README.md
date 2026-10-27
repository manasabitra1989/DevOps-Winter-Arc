# Day 22 --- AWS Overview, Account Setup & Billing Safety

## Objective

Understand the basics of AWS, safely explore the AWS Console, and
configure billing awareness without launching chargeable infrastructure.

**Level:** Beginner\
**Estimated time:** 1.5--2 hours\
**Cost goal:** \$0 planned AWS resource spend

> **Safety warning:** A \$0 budget or billing alert is not a hard
> spending cap. Alerts can be delayed, and AWS can still charge for
> resources you create. Do not launch EC2 instances, RDS databases, NAT
> Gateways, load balancers, EKS clusters, or other chargeable
> infrastructure for this lab.

## Concepts and Key Terms

  -----------------------------------------------------------------------
  Concept                             Explanation
  ----------------------------------- -----------------------------------
  AWS                                 A cloud platform offering compute,
                                      storage, databases, networking,
                                      monitoring, and other services.

  Region                              A geographic area where AWS
                                      operates infrastructure.

  Availability Zone (AZ)              An isolated location within a
                                      Region. Using multiple AZs can
                                      improve availability.

  IAM                                 Identity and Access Management;
                                      controls who can access AWS and
                                      what they can do.

  EC2                                 A service for virtual servers in
                                      the cloud.

  S3                                  Object storage for files and data.

  VPC                                 A logically isolated network in
                                      AWS.

  CloudWatch                          A monitoring service for metrics,
                                      logs, and alarms.

  Billing & Cost Management           AWS console area for reviewing
                                      usage, charges, budgets, and cost
                                      trends.

  MFA                                 Multi-factor authentication; adds
                                      another verification step when
                                      signing in.

  AWS Free Tier                       Offers subject to eligibility,
                                      quotas, time limits, and
                                      service-specific pricing. It does
                                      not mean every service is free.

  Budget alert                        A notification about costs or
                                      forecasted costs; it does not
                                      automatically stop resources.
  -----------------------------------------------------------------------

### EC2 vs S3

-   **EC2:** provides compute capacity, such as a virtual server that
    runs an application.
-   **S3:** stores objects such as files, images, logs, and backups.

### Region vs Availability Zone

A Region is a geographic area. An Availability Zone is an isolated
location within a Region. Deploying across multiple AZs can improve
resilience, but may also affect cost.

## Part 1 --- Explain AWS in Your Own Words

Write 2--3 sentences explaining AWS. Then explain the difference between
EC2 and S3.

Example:

> AWS provides cloud services over the internet so teams can use
> computing, storage, networking, and other infrastructure without
> owning all the physical hardware. EC2 provides virtual servers, while
> S3 stores objects such as files and backups.

## Part 2 --- Create or Check an AWS Account Safely

1.  Open the official AWS website and review the current Free Tier terms
    before signing up.
2.  Use your own email address and accurate details. AWS may require
    payment-card and identity/phone verification.
3.  Use a strong, unique password.
4.  Enable MFA for the root user if available.
5.  Do **not** create access keys for the root user.
6.  If you already have an AWS account, do not create a duplicate for
    this challenge. Review the existing account's security and billing
    settings instead.
7.  Sign in and locate:
    -   Account menu
    -   Region selector
    -   Console search
    -   Help/support area

**Why this matters:** Account security is the foundation for all later
cloud work. Root has extensive privileges and should not be used for
routine tasks.

## Part 3 --- Billing Safety

Complete these checks before launching any AWS resources.

### Step 1: Review current charges and usage

Open **Billing and Cost Management** and review the current month's
charges and usage.

A zero total at the moment does not guarantee that future usage will be
free. Billing data may take time to appear.

### Step 2: Create or review a budget

1.  Open **AWS Budgets** from Billing and Cost Management.
2.  Create a monthly cost budget for `$0.00` if permitted, or the
    smallest available amount.
3.  Add actual-cost and forecasted-cost alert thresholds above `$0` if
    available.
4.  Add an email address you actively check.
5.  Confirm that the alert recipient is correct.

Console labels and available options may change; use console search if
necessary.

### Step 3: Review additional billing visibility

If available in your account, review: - Billing alerts or a CloudWatch
billing alarm - Free Tier usage - Current-month usage and cost trends

**Critical:** Budgets and alerts notify you; they are not a hard cap and
do not automatically stop resources. Alerts may be delayed. Never launch
resources merely to test an alert.

### Billing safety checklist

-   [ ] I know where to find current charges and usage.
-   [ ] I created or reviewed a budget.
-   [ ] I verified the alert recipient.
-   [ ] I understand that a `$0` budget is not a spending limit.
-   [ ] I will check pricing before future labs and remove resources
    when the lab says to do so.

## Part 4 --- AWS Console Exploration

Open service pages only. **Do not press Create, Launch, Deploy, or any
button that provisions resources.**

  -----------------------------------------------------------------------
  Area                    What to find            Do not do today
  ----------------------- ----------------------- -----------------------
  IAM                     Users, roles, policies, Do not create broad
                          MFA/security            permissions or root
                          recommendations         access keys.

  EC2                     Instance dashboard,     Do not launch an
                          instance types, pricing instance.
                          links                   

  S3                      What buckets and        Do not create a bucket
                          objects are; access and or upload sensitive
                          pricing notes           data.

  VPC                     VPCs, subnets, route    Do not create a NAT
                          tables, security groups Gateway or networking
                                                  resources.

  Billing                 Bills, budgets, Free    Do not assume a blank
                          Tier usage              chart means future
                                                  usage is free.
  -----------------------------------------------------------------------

The goal is to understand where services and settings live---not to
deploy infrastructure.

## Part 5 --- Troubleshooting and Lessons Learned

  -----------------------------------------------------------------------
  Situation                           What it means / what to do
  ----------------------------------- -----------------------------------
  Billing page shows `$0`             It reflects the data currently
                                      available; it does not guarantee
                                      future use will be free. Check
                                      usage again later.

  Budget alert is configured          It sends a notification when
                                      conditions are met; it does not
                                      automatically stop resources.

  Free Tier is available              Eligibility, quotas, time limits,
                                      and pricing differ by service. Read
                                      the current terms.

  You cannot find a console page      Use the AWS Console search. Labels
                                      and navigation may change.

  You already have an AWS account     Review and secure it; do not create
                                      a duplicate just for the challenge.

  You need to test a service          Do not provision resources during
                                      this orientation lab. Check pricing
                                      and the assignment first.
  -----------------------------------------------------------------------

## Interview Questions and Answers

### 1. What is cloud computing?

Using computing resources over the internet instead of owning and
maintaining all physical hardware yourself.

### 2. What is AWS?

A cloud platform that provides services such as compute, storage,
databases, networking, identity, and monitoring.

### 3. What is an AWS Region?

A geographic area containing AWS infrastructure.

### 4. What is an Availability Zone?

An isolated location within a Region. Multiple AZs can improve
availability and resilience.

### 5. What is the difference between EC2 and S3?

EC2 provides virtual compute servers. S3 stores objects such as files
and backups.

### 6. What does IAM do?

IAM controls identities and permissions for accessing AWS resources.

### 7. What is a VPC?

A logically isolated network in AWS where resources can be placed in
subnets and controlled with routing and security settings.

### 8. What is CloudWatch?

A service used to collect metrics and logs and create alarms for
monitoring.

### 9. Is every AWS service free with a Free Tier account?

No. Eligibility, quotas, time limits, and service-specific pricing
apply. Check the current terms.

### 10. Does a `$0` budget prevent AWS charges?

No. It sends alerts; it is not a hard spending cap, and billing data and
notifications may be delayed.

### 11. Why enable MFA?

It adds another verification step and makes account takeover harder.

### 12. What should you do after a future lab?

Review resources in the relevant Regions, delete resources the task says
to remove, and check billing and usage afterward.

## Evidence / Proof of Work

No GitHub project is required for Day 22. If you save screenshots or
share progress, hide personal and account information.

Suggested evidence: - \[ \] AWS Console home page with personal details
hidden - \[ \] Budget configuration showing the amount and alert
thresholds, with email/account identifiers hidden - \[ \] Billing or
Free Tier usage page, if available

Never share passwords, payment details, account identifiers, or other
sensitive information.

## Completion Checklist

-   [ ] I can explain AWS, Region, AZ, IAM, EC2, S3, VPC, and
    CloudWatch.
-   [ ] I created or checked my AWS account.
-   [ ] I enabled root MFA if available.
-   [ ] I reviewed billing and created or reviewed budget alerts.
-   [ ] I understand that alerts are not a hard spending cap.
-   [ ] I explored the Console without launching chargeable resources.
-   [ ] I did not create root access keys or expose credentials.

## Cleanup

This lab should not create infrastructure, so there should be no lab
servers or networking resources to remove.

-   Review relevant Regions if you previously created resources.
-   Check Billing and Cost Management for current usage.
-   Do not delete account security settings or budgets just to clean up
    the lab; keep useful alerts enabled.

## Final Learning Summary

Day 22 is about safe AWS orientation, account security, and billing
awareness---not deploying infrastructure.

**Main takeaway:** Learn the console and control costs before building
anything. A Free Tier label or `$0` budget does not guarantee a zero
bill.
