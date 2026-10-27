# Day 23 --- AWS IAM & Access Management

## Objective

Learn how AWS controls who can do what, secure the account, and design
least-privilege access for a small team.

**Level:** Beginner\
**Estimated time:** 2--3 hours (flexible)\
**Cost goal:** `$0` planned AWS resource spend

This lab focuses on IAM and access management only. It does not repeat
Day 22's AWS overview/account setup or earlier Linux, Docker, and
Kubernetes tasks.

> **Safety first:** IAM itself is generally not the expensive part of
> AWS, but permissions can allow someone to create chargeable resources.
> Keep billing budgets and alerts enabled, enable MFA, never share
> credentials, and do not create access keys for practice users. Budget
> alerts are not a hard spending cap.

## Part 1 --- IAM Concepts

  -----------------------------------------------------------------------
  Concept                             Explanation
  ----------------------------------- -----------------------------------
  IAM user                            An identity for a person or
                                      workload; it may have long-term
                                      credentials.

  Group                               A collection of IAM users. Attach
                                      common permissions to a group
                                      instead of managing each user
                                      separately.

  Role                                An identity that is assumed to
                                      obtain temporary credentials;
                                      commonly used by AWS services and
                                      cross-account access.

  Policy                              A JSON permissions document
                                      describing `Effect`, `Action`,
                                      `Resource`, and optionally
                                      `Condition`.

  Least privilege                     Grant only the minimum permissions
                                      required for a task.

  MFA                                 Multi-factor authentication adds
                                      another verification step.

  Default deny                        A request is denied unless an
                                      applicable Allow exists. An
                                      explicit Deny overrides an Allow.

  Trust policy                        Defines who is allowed to assume a
                                      role.
  -----------------------------------------------------------------------

### User vs Group vs Role

-   **User:** represents an identity that may use long-term credentials.
-   **Group:** makes it easier to assign common permissions to multiple
    users.
-   **Role:** is assumed by a trusted principal and provides temporary
    credentials.

For AWS services, prefer an appropriate IAM role and temporary
credentials over long-lived access keys stored on a server.

### Policy evaluation basics

AWS access is not granted merely because a policy exists. The request
must be allowed by applicable permissions, and an explicit Deny
overrides an Allow.

A policy should be scoped to the required actions and resources instead
of using broad permissions such as `Action: "*"` and `Resource: "*"`
without a justified need.

## Part 2 --- Secure the AWS Account

1.  Sign in as the root user only when needed to secure the account.
2.  Enable root MFA if it is not already enabled.
3.  Do not use root for everyday work.
4.  Use a separate, appropriately permissioned identity for routine
    administration.
5.  Confirm that Day 22 billing budgets and alerts remain configured.
6.  Do not launch EC2, RDS, NAT Gateway, EKS, load balancers, or other
    chargeable resources for this assignment.
7.  Do not share screenshots containing account IDs, email addresses,
    MFA QR codes, recovery details, secret keys, or passwords.

Root is the highest-privilege account identity. Protecting it with MFA
and avoiding routine root use reduces account risk.

## Part 3 --- Explore IAM in the Console (Read Only)

Open the AWS IAM console and inspect these sections without attaching
broad permissions to your everyday identity:

-   Users
-   User groups
-   Roles
-   Policies
-   Account settings

Tasks: 1. Find where MFA status is shown. 2. Inspect the difference
between AWS-managed and customer-managed policies. 3. Open an example
policy and identify `Effect`, `Action`, and `Resource`. 4. Open a role
and locate its trust relationship/trust policy.

### AWS-managed vs customer-managed policies

-   **AWS-managed policy:** created and maintained by AWS.
-   **Customer-managed policy:** created and maintained in your AWS
    account, allowing your organization to define permissions for its
    needs.

Read policy details carefully. A policy name alone does not tell you its
full scope.

## Part 4 --- Practical Lab: Design Access for a Small Team

### Scenario

A small company has three teams: Admins, Developers, and Auditors.
Design their permissions. You may complete the design on paper or as
JSON first. Create IAM objects only if your account is authorized for
the lab and you understand the permissions.

  -----------------------------------------------------------------------
  Group                   Intended access         Design note
  ----------------------- ----------------------- -----------------------
  Admins                  Administrative access   Limit membership; never
                          for a designated admin  use root for daily
                          identity                work.

  Developers              Read-only baseline plus The custom policy
                          read/write access to    should target only that
                          one lab S3 bucket in a  bucket; no account-wide
                          later lab               admin rights.

  Auditors                Read-only access        Inspect resources
                                                  without modifying them.
  -----------------------------------------------------------------------

### Task A --- Permission matrix

Use this matrix as a starting point and explain any permissions you add.

  -----------------------------------------------------------------------
  Action            Admins            Developers        Auditors
  ----------------- ----------------- ----------------- -----------------
  Perform approved  Yes, for          No, unless        No
  administration    designated admins specifically      
                                      required          

  Read relevant     Yes               Yes, within       Yes, within audit
  resource                            assigned scope    scope
  information                                           

  Read objects in   As needed         Yes, for the      If required for
  the lab bucket                      designated bucket audit

  Upload/update     As needed         Yes, for the      No
  objects in the                      designated bucket 
  lab bucket                                            

  Delete resources  Only when         No by default     No
  or objects        required and                        
                    authorized                          

  Change IAM        Only designated   No                No
  permissions       authorized admins                   
  -----------------------------------------------------------------------

This is a design exercise, not a universal AWS policy. Actual access
should be adjusted to business requirements and approved
responsibilities.

**Why should Developers not receive `AdministratorAccess`?** It grants
much broader permissions than the described task requires. A developer
who only needs to work with one lab bucket should not automatically be
able to modify IAM, networking, billing-related resources, or unrelated
workloads.

### Task B --- Understand the sample S3 policy

The PDF provides this example:

``` json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:GetObject", "s3:PutObject"],
    "Resource": "arn:aws:s3:::YOUR-LAB-BUCKET/*"
  }]
}
```

#### Explain every field

-   `Version`: the policy language version. `2012-10-17` is the standard
    policy version used in this example.
-   `Statement`: contains one or more permission statements.
-   `Effect: Allow`: grants the listed actions when the statement
    matches.
-   `Action`: lists the allowed S3 operations.
-   `s3:GetObject`: allows reading objects.
-   `s3:PutObject`: allows uploading or writing objects.
-   `Resource`: identifies the objects to which these permissions apply.
-   `arn:aws:s3:::YOUR-LAB-BUCKET/*`: the object ARN pattern for objects
    inside the named bucket. Replace `YOUR-LAB-BUCKET` with the actual
    lab bucket name before use.

**Important:** This object policy does not grant permission to list the
bucket. `s3:ListBucket` applies to the bucket ARN itself, such as
`arn:aws:s3:::YOUR-LAB-BUCKET`, without `/*`. Do not attach this sample
policy until you understand its scope, and never use real or production
data in a practice bucket.

### Task C --- Role vs User: EC2 example

**Question:** When should an EC2 instance use a role instead of storing
access keys on the server?

**Answer:** When an application on EC2 needs to call AWS services,
attach an appropriate IAM role to the instance. The application can
obtain temporary credentials through the AWS-provided credential
mechanism. This avoids storing long-lived access keys in files or
application code.

## Part 5 --- Optional AWS CLI Identity Check

Only perform this section if AWS CLI is already installed and configured
with an appropriately permissioned, non-root identity.

**Do not create root access keys to make these commands work.** If the
CLI is not installed or configured, skip this section.

### 1. Check the AWS CLI version

``` bash
aws --version
```

Shows whether the AWS CLI is installed and reports its version.

### 2. Check the active identity

``` bash
aws sts get-caller-identity
```

Shows the identity and account context being used by the CLI.

Verify that the identity belongs to the intended account. Redact the
account ID before sharing output.

### 3. Inspect CLI configuration

``` bash
aws configure list
```

Shows the active profile, Region, and credential source. Do not share
the output publicly if it reveals sensitive context.

### 4. Inspect IAM account summary

``` bash
aws iam get-account-summary
```

Reports selected IAM account statistics, subject to the permissions of
the current identity.

If a command returns `AccessDenied`, the identity may lack the required
permission. Do not work around the error by using root access keys or
attaching broad permissions without approval.

## Part 6 --- Troubleshooting Mini-Challenge

  -------------------------------------------------------------------------------
  Problem                 Evidence / likely cause Next step
  ----------------------- ----------------------- -------------------------------
  You can open IAM but    The identity may lack   Ask the account owner/admin to
  cannot create a user    required IAM            review the required
                          permissions; inspect    permissions.
                          `AccessDenied`          

  A Developer can read an `s3:GetObject` applies  Review the actions and resource
  object but cannot list  to object ARNs; listing ARNs in the policy.
  the bucket              needs `s3:ListBucket`   
                          on the bucket ARN       

  A role cannot be        Trust policy, caller    Inspect the trust relationship
  assumed                 permissions, target     and relevant permission
                          role ARN, or an         policies.
                          explicit Deny may be    
                          responsible             

  A policy contains       The scope is            Narrow actions and resources to
  `Action: "*"` and       excessively broad for   the actual requirement.
  `Resource: "*"`         most tasks              

  An EC2 server stores    Credentials may be      Prefer an attached IAM role
  long-lived access keys  exposed through files,  with temporary credentials.
                          logs, or backups        

  CLI identity is         The CLI may be using a  Check `aws configure list` and
  unexpected              different profile or    `aws sts get-caller-identity`
                          credential source       before further commands.
  -------------------------------------------------------------------------------

### Required diagnosis format

For any issue you investigate, write:

**Problem → Evidence → Root Cause → Fix → Verification**

Do not claim that you observed an error unless it actually occurred in
your account.

## Interview Questions and Answers

### 1. What is the difference between an IAM user and an IAM role?

A user is an identity that may have long-term credentials. A role is
assumed by a trusted principal and provides temporary credentials.

### 2. What is least privilege?

Granting only the permissions required for a task, limited to the
necessary actions and resources.

### 3. How are IAM permissions evaluated?

Requests are denied by default unless an applicable Allow grants access.
An explicit Deny overrides an Allow.

### 4. Why use IAM groups?

Groups allow common permissions to be managed consistently for multiple
users rather than assigning the same permissions individually.

### 5. What is a trust policy?

A trust policy defines which principals are allowed to assume a role.

### 6. Why enable MFA on the root user?

MFA adds another verification step and makes account takeover more
difficult.

### 7. What is the difference between a permissions policy and a trust policy?

A permissions policy defines what actions an identity may perform. A
role trust policy defines who is allowed to assume the role.

### 8. Why should Developers not have AdministratorAccess by default?

It grants permissions beyond the described development task and
increases the impact of mistakes or compromised credentials.

### 9. Why can a user read an S3 object but not list the bucket?

Object reading uses `s3:GetObject` on object ARNs. Listing requires
`s3:ListBucket` on the bucket ARN.

### 10. Why should EC2 use an IAM role instead of stored access keys?

An attached role provides temporary credentials through the AWS
credential mechanism, avoiding long-lived access keys stored on the
server.

### 11. What is the difference between AWS-managed and customer-managed policies?

AWS manages AWS-managed policies. Customer-managed policies are created
and maintained in your account for your own permission requirements.

### 12. What should you do if IAM returns `AccessDenied`?

Read the error, identify the denied action and resource, check the
relevant policies and trust relationship, and ask an authorized account
administrator if needed. Do not bypass the restriction with root
credentials.

### 13. What does `aws sts get-caller-identity` do?

It identifies the AWS identity and account context currently used by the
CLI.

### 14. Why is `Action: "*"` with `Resource: "*"` risky?

It grants an extremely broad scope that can permit unrelated actions on
unrelated resources. Use the minimum required actions and resources
instead.

## Evidence / Proof of Work

No GitHub submission is required by the Day 23 PDF.

Capture only useful evidence, and hide personal/account information:

-   [ ] IAM dashboard or MFA status
-   [ ] The sample policy JSON in your editor or your written permission
    matrix
-   [ ] If configured, successful `aws sts get-caller-identity` output
    with the account ID redacted

Never share account IDs, email addresses, MFA QR codes, recovery
details, access keys, secret keys, or passwords.

## Completion Checklist

### Account security

-   [ ] Root MFA is enabled if available.
-   [ ] Root is not used for daily work.
-   [ ] Billing budget and alerts from Day 22 remain configured.
-   [ ] No root access keys were created.
-   [ ] No chargeable resources were launched for this assignment.

### IAM concepts and console

-   [ ] I can explain users, groups, roles, policies, MFA, least
    privilege, and default deny.
-   [ ] I inspected Users, Groups, Roles, Policies, and account
    settings.
-   [ ] I located MFA status.
-   [ ] I compared AWS-managed and customer-managed policies.
-   [ ] I identified `Effect`, `Action`, and `Resource` in a policy.
-   [ ] I found the role trust policy area.

### Access design and CLI

-   [ ] I designed permissions for Admins, Developers, and Auditors.
-   [ ] I explained why Developers should not receive
    AdministratorAccess.
-   [ ] I understand why object access and bucket listing require
    different S3 permissions.
-   [ ] I can explain why AWS services should use roles instead of
    long-lived access keys.
-   [ ] If AWS CLI was already configured, I checked the active identity
    safely; otherwise, I skipped the optional section.

## Cleanup

This lab is primarily an account review and access-design exercise. No
chargeable infrastructure or IAM objects need to be created to complete
the paper/design portion.

-   Do not delete existing users, roles, policies, MFA settings, or
    budgets as generic cleanup.
-   If you created optional lab-only IAM objects, inspect them and
    remove them only if you are authorized and certain they are not used
    elsewhere.
-   Keep MFA and useful billing alerts enabled.
-   Never delete or expose credentials as part of cleanup.

## Final Learning Summary

Day 23 teaches how AWS controls access through identities, groups,
roles, policies, and trust relationships.

-   Users represent identities; groups simplify shared permissions.
-   Roles provide temporary credentials when assumed by a trusted
    principal.
-   Policies define allowed actions and resources.
-   Least privilege reduces the impact of mistakes and compromised
    identities.
-   MFA adds protection to the root account.
-   S3 object permissions and bucket-listing permissions apply to
    different resource ARNs.
-   EC2 applications should use IAM roles rather than stored long-lived
    access keys.

**Main takeaway:** Give each identity only the access it needs, verify
which identity is active, and protect account credentials.
