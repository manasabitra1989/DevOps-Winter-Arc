# Day 24 --- AWS S3 + CloudFront with Floci (WSL2)

> **DevOps Winter Arc · 90 Days Challenge · Week 4 --- AWS · Day 24**
>
> This README records the lab performed in WSL2 Ubuntu using Floci, a
> local AWS emulator. It includes the concepts, setup steps, commands,
> JSON configuration files, verification results, troubleshooting notes,
> and interview questions.

## 1. Lab goals

By completing this lab, I practised:

-   Creating an S3 bucket and uploading static website files.
-   Enabling S3 Block Public Access and bucket versioning.
-   Understanding object keys, metadata, object versions, and downloads.
-   Creating a CloudFront Origin Access Control (OAC).
-   Creating a CloudFront distribution with `index.html` as its default
    root object.
-   Configuring an S3 bucket policy for a specific CloudFront
    distribution.
-   Testing the local CloudFront-style endpoint provided by Floci.
-   Capturing evidence and cleaning up local emulator resources.

## 2. What is Floci?

**Floci** is a local emulator for AWS and other cloud service APIs. It
runs locally (in this lab, through Docker) and lets tools such as the
AWS CLI send requests to a local endpoint instead of a real AWS account.

In this lab, the endpoint was:

``` text
http://localhost.floci.io:4566
```

Floci is useful for learning commands and testing workflows without
creating normal billable AWS resources. However, it is not the same as
real AWS. Some service behaviours, DNS, TLS, IAM/policy enforcement,
caching, and API operations may differ from production AWS. A successful
local test must not be presented as proof that every production AWS
behaviour has been tested.

### Floci vs. real AWS

  -----------------------------------------------------------------------
  Area                    Floci lab               Real AWS
  ----------------------- ----------------------- -----------------------
  S3 bucket               Simulated local         Real AWS resource; may
                          resource                incur charges

  CloudFront distribution Simulated distribution  Global CDN
                                                  distribution; may incur
                                                  charges

  CloudFront hostname     Local routing may be    Public AWS-managed
                          needed                  distribution hostname

  DNS/TLS/edge caching    Emulator-dependent      Real managed service
                                                  behaviour

  Cost                    No normal AWS resource  Charges may apply for
                          charges for simulated   storage, requests,
                          services; local machine transfer,
                          uses resources          distributions, and
                                                  invalidations

  Best use                Learning commands, API  Production validation
                          flows, basic            and real-world
                          configuration           behaviour
  -----------------------------------------------------------------------

## 3. Architecture and key concepts

``` text
Visitor
   |
   | HTTPS (intended production architecture)
   v
CloudFront (CDN)
   |
   | Signed origin request using OAC
   v
Private S3 bucket
   |
   +-- index.html
   +-- error.html

S3 Block Public Access: ON
```

### S3 bucket

An S3 bucket is a named container for objects. Bucket names in real AWS
must be globally unique. This lab used `uploads` in Floci.

### Object and object key

An **object** is the stored file and its metadata. An **object key** is
its name/path within a bucket, such as `index.html` or `error.html`.

### Block Public Access (BPA)

S3 provides four controls that help prevent accidental public access:

-   `BlockPublicAcls`
-   `IgnorePublicAcls`
-   `BlockPublicPolicy`
-   `RestrictPublicBuckets`

All four were set to `true` in this lab. Keep these enabled unless you
have a deliberate, reviewed reason to change them.

### Versioning

Versioning lets a bucket retain multiple versions of an object when it
is overwritten or deleted. The lab enabled versioning and uploaded a
changed `index.html`. The emulator returned a `VersionId` from
`head-object`.

**Known lab limitation:** `aws s3api list-object-versions` and even
`list-objects-v2` returned `badly formed help string` in this AWS
CLI/Python 3.14.4 environment. Therefore, the current object's
`VersionId` was observed, but the complete version history could not be
verified using that listing command.

### CloudFront

CloudFront is a Content Delivery Network (CDN). It can cache content at
edge locations closer to viewers, reducing latency and origin requests.
It can serve content over HTTPS.

### Origin Access Control (OAC)

OAC allows CloudFront to sign requests to a private S3 origin. In real
AWS, the bucket policy must permit the intended CloudFront distribution
to read the objects. OAC attachment alone does not prove the bucket
policy is correct or enforced.

### Caching and invalidation

CloudFront caches responses based on its cache behaviour and TTLs. An
**invalidation** requests that cached objects be removed before their
normal expiry. Invalidation can incur charges beyond applicable
allowances. It was not required for this lab.

## 4. Environment used

-   OS: Ubuntu under WSL2
-   AWS CLI: `aws-cli/2.31.35`
-   Python reported by AWS CLI: `3.14.4`
-   Floci CLI: `0.4.0`
-   Floci server: `2.3.0 (floci-always-free)`
-   Local endpoint configured by Floci: `http://localhost.floci.io:4566`
-   Project directory:
    `~/DevOps-Winter-Arc/Week4-AWS/day24-S3-Cloudfront`

## 5. Install and start Floci

### 5.1 Check the environment

``` bash
cat /etc/os-release
docker --version
docker info
aws --version
```

`docker info` checks that Docker is reachable, not merely installed.

### 5.2 Download and inspect the installer

``` bash
curl -fsSL https://floci.io/install.sh -o /tmp/install-floci.sh
less /tmp/install-floci.sh
```

Press `q` to exit `less`. After reviewing the installer, install it:

``` bash
sh /tmp/install-floci.sh
floci --help
```

The installer reported Floci CLI `0.4.0` installed to
`/usr/local/bin/floci`.

### 5.3 Start the emulator and load its environment

``` bash
floci start
eval "$(floci env)"
```

`floci start` launches the local emulator. `eval "$(floci env)"` applies
the environment variables printed by Floci to the current shell. In this
session the values included:

``` text
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_ENDPOINT_URL=http://localhost.floci.io:4566
```

These were local emulator values, not real AWS credentials. Run
`eval "$(floci env)"` again in a new terminal when needed.

Verify:

``` bash
floci status
floci version
floci services
env | grep -E '^(AWS_ENDPOINT_URL|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY|AWS_DEFAULT_REGION|AWS_REGION)='
```

**Safety note:** before running AWS CLI commands, verify the endpoint.
If it points to real AWS rather than Floci, resource-creation commands
may create real resources and incur charges.

## 6. Website files

The project contained:

``` text
day24-S3-Cloudfront/
├── index.html
├── error.html
├── oac-config.json
├── distribution-config.json
├── bucket-policy.json
└── evidence/
```

The local website homepage displayed "Hello from AWS Week - Version 2"
and a short note that it was the Day 24 DevOps Winter Arc project.

Example simple `index.html` (the actual file may include slightly
different whitespace or wording):

``` html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AWS Week - My Website</title>
</head>
<body>
    <h1>Hello from AWS Week - Version 2</h1>
    <p>My Day 24 DevOps Winter Arc project.</p>
    <p>Learning Amazon S3 and CloudFront.</p>
</body>
</html>
```

`error.html` was also present and uploaded. It is a simple
page-not-found page.

Useful local checks:

``` bash
pwd
ls -lh
cat index.html
cat error.html
```

## 7. Create and secure the S3 bucket

### 7.1 Confirm the CLI is connected to Floci

``` bash
aws s3 ls
```

The initial bucket listing was empty before creating `uploads`.

### 7.2 Create the bucket

``` bash
aws s3 mb s3://uploads
aws s3 ls
```

The output confirmed that `uploads` was created. In this lab, we reused
the bucket name `uploads`; in real AWS, bucket naming and uniqueness
rules apply globally.

Set variables for later commands:

``` bash
export BUCKET=uploads
export AWS_DEFAULT_REGION=us-east-1
```

### 7.3 Enable all four Block Public Access controls

``` bash
aws s3api put-public-access-block \
  --bucket "$BUCKET" \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

Verify:

``` bash
aws s3api get-public-access-block --bucket "$BUCKET"
```

Observed result: all four values were `true`.

### 7.4 Enable versioning

``` bash
aws s3api put-bucket-versioning \
  --bucket "$BUCKET" \
  --versioning-configuration Status=Enabled
```

Verify:

``` bash
aws s3api get-bucket-versioning --bucket "$BUCKET"
```

Observed result:

``` json
{
    "Status": "Enabled"
}
```

## 8. Upload and test the website files

From the project directory:

``` bash
cd ~/DevOps-Winter-Arc/Week4-AWS/day24-S3-Cloudfront
aws s3 sync . "s3://$BUCKET"
aws s3 ls "s3://$BUCKET"
```

`aws s3 sync` compares local files with the destination and uploads new
or changed files. Because `.` means the current directory, use it only
from the intended project directory; it can upload other files in that
directory too.

Check object metadata:

``` bash
aws s3api head-object --bucket "$BUCKET" --key index.html
aws s3api head-object --bucket "$BUCKET" --key error.html
```

Download the object and compare it with the local copy:

``` bash
aws s3 cp "s3://$BUCKET/index.html" /tmp/day24-index-download.html
diff -u index.html /tmp/day24-index-download.html
```

No output from `diff` means the downloaded copy matches the local file.

### Demonstrate an overwrite

Edit `index.html`, change the heading to Version 2, save, then upload
it:

``` bash
nano index.html
aws s3 cp index.html "s3://$BUCKET/index.html"
aws s3api head-object --bucket "$BUCKET" --key index.html
```

The `head-object` response included a `VersionId`, which confirmed that
the emulator returned version metadata.

### Version listing issue observed

These commands both returned `badly formed help string`:

``` bash
aws s3api list-object-versions --bucket "$BUCKET"
aws s3api list-objects-v2 --bucket "$BUCKET" --no-cli-pager
```

Adding `--endpoint-url "$AWS_ENDPOINT_URL"` and `--no-cli-pager` did not
resolve the issue. Environment observed: AWS CLI `2.31.35` with Python
`3.14.4`. Record this as a CLI/emulator environment limitation; do not
claim that all object versions were listed and verified.

## 9. Read the object using the AWS CLI

``` bash
aws s3api get-object \
  --bucket "$BUCKET" \
  --key index.html \
  /tmp/day24-private-test.html
```

This authenticated CLI request succeeded. It demonstrates that the CLI
can retrieve the object; it does **not** demonstrate that anonymous
users can access it.

## 10. Create an Origin Access Control

### 10.1 `oac-config.json`

This was the OAC configuration used:

``` json
{
  "Name": "day24-s3-oac",
  "Description": "Day 24 local Floci lab",
  "SigningProtocol": "sigv4",
  "SigningBehavior": "always",
  "OriginAccessControlOriginType": "s3"
}
```

Field explanation:

-   `Name`: readable name for the OAC.
-   `Description`: explains that it belongs to the local Day 24 lab.
-   `SigningProtocol: sigv4`: uses AWS Signature Version 4.
-   `SigningBehavior: always`: sign origin requests.
-   `OriginAccessControlOriginType: s3`: the origin is S3.

Create and verify it:

``` bash
aws cloudfront create-origin-access-control \
  --origin-access-control-config file://oac-config.json \
  --no-cli-pager

export OAC_ID="587b650b-917e-476f-91cc-133a500dbc66"

aws cloudfront list-origin-access-controls --no-cli-pager
```

OAC ID returned by this Floci session:

``` text
587b650b-917e-476f-91cc-133a500dbc66
```

IDs are specific to this emulator state and may differ if the lab is
recreated.

## 11. Create the CloudFront distribution

### 11.1 `distribution-config.json`

The distribution configuration used in the lab was:

``` json
{
  "CallerReference": "day24-1793080273",
  "Comment": "Day 24 local Floci S3 website",
  "Enabled": true,
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 1,
    "Items": [
      {
        "Id": "uploads-s3-origin",
        "DomainName": "uploads.s3.amazonaws.com",
        "S3OriginConfig": {
          "OriginAccessIdentity": ""
        },
        "OriginAccessControlId": "587b650b-917e-476f-91cc-133a500dbc66"
      }
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "uploads-s3-origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {
      "Quantity": 2,
      "Items": ["GET", "HEAD"],
      "CachedMethods": {
        "Quantity": 2,
        "Items": ["GET", "HEAD"]
      }
    },
    "ForwardedValues": {
      "QueryString": false,
      "Cookies": {
        "Forward": "none"
      }
    },
    "MinTTL": 0,
    "DefaultTTL": 60,
    "MaxTTL": 300,
    "Compress": true
  }
}
```

Explanation:

-   `CallerReference`: a unique creation reference to avoid duplicate
    creation requests.
-   `Origins`: identifies the S3 origin and attaches the OAC.
-   `DefaultRootObject`: makes `/` use `index.html`.
-   `ViewerProtocolPolicy`: requests that viewers use HTTPS.
-   `AllowedMethods`: permits read-only `GET` and `HEAD` requests.
-   `ForwardedValues`: does not forward query strings or cookies.
-   `DefaultTTL`, `MinTTL`, `MaxTTL`: define caching duration bounds.
-   `Compress`: enables compression where supported.

Create the distribution:

``` bash
aws cloudfront create-distribution \
  --distribution-config file://distribution-config.json \
  --no-cli-pager
```

Returned values in this session:

``` bash
export DIST_ID="EK68WXSB87MFYY"
export DIST_DOMAIN="ek68wxsb87mfyy.cloudfront.net"
```

The create response reported `Status: Deployed`, default root object
`index.html`, and viewer policy `redirect-to-https`.

Verify:

``` bash
aws cloudfront list-distributions --no-cli-pager
aws cloudfront get-distribution --id "$DIST_ID" --no-cli-pager
```

The simulated `*.cloudfront.net` hostname did not resolve from WSL2.
Floci's local hostname worked instead.

## 12. Bucket policy for CloudFront

### 12.1 `bucket-policy.json`

The policy applied in Floci was:

``` json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowCloudFrontReadForDay24Distribution",
      "Effect": "Allow",
      "Principal": {
        "Service": "cloudfront.amazonaws.com"
      },
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::uploads/*",
      "Condition": {
        "StringEquals": {
          "AWS:SourceArn": "arn:aws:cloudfront::000000000000:distribution/EK68WXSB87MFYY"
        }
      }
    }
  ]
}
```

Explanation:

-   `Principal`: CloudFront service principal.
-   `Action`: read objects using `s3:GetObject`.
-   `Resource`: all objects in the `uploads` bucket.
-   `AWS:SourceArn`: restricts the statement to this distribution ARN.
-   `000000000000`: simulated account ID returned by Floci, not a real
    AWS account ID.

Apply and verify:

``` bash
aws s3api put-bucket-policy \
  --bucket "$BUCKET" \
  --policy file://bucket-policy.json

aws s3api get-bucket-policy --bucket "$BUCKET"
aws s3api get-public-access-block --bucket "$BUCKET"
```

Floci accepted and returned the policy. All four Block Public Access
controls remained `true`.

**Production note:** never copy a simulated account ID or guessed policy
blindly into a real AWS account. For real AWS, use the exact
distribution ARN/account context and AWS-generated/recommended policy.
Also verify the real bucket policy and actual access behaviour.

## 13. Test the local CloudFront-style route

The real-looking `cloudfront.net` hostname did not resolve locally. This
local Floci hostname did work:

``` bash
export LOCAL_CF_HOST="ek68wxsb87mfyy.cloudfront.localhost.floci.io"

curl -i --max-time 10 "http://$LOCAL_CF_HOST:4566/"
```

Observed result: `HTTP/1.1 200 OK`, `Content-Type: text/html`, and the
page content showing:

``` html
<h1>Hello from AWS Week - Version 2</h1>
```

This demonstrates that the local Floci route returned the website
content.

### What was not proven

-   The HTTP test returned `200 OK`, so the local HTTP-to-HTTPS redirect
    was not demonstrated.
-   The direct S3 URL returning `403 Access Denied` was not confirmed.
-   The response alone does not prove that OAC and the `AWS:SourceArn`
    condition are enforced exactly as real AWS enforces them.
-   The version-listing command failed, so all historical versions and
    delete markers were not enumerated.

Accurate documentation should distinguish "configured" from "verified".

## 14. Useful command reference

``` bash
# Floci lifecycle
floci start
eval "$(floci env)"
floci status
floci version
floci services
floci stop

# S3 bucket and objects
aws s3 mb "s3://$BUCKET"
aws s3 ls
aws s3 ls "s3://$BUCKET"
aws s3 sync . "s3://$BUCKET"
aws s3 cp index.html "s3://$BUCKET/index.html"
aws s3 cp "s3://$BUCKET/index.html" /tmp/day24-index-download.html

# S3 security and metadata
aws s3api get-public-access-block --bucket "$BUCKET"
aws s3api get-bucket-versioning --bucket "$BUCKET"
aws s3api head-object --bucket "$BUCKET" --key index.html
aws s3api get-object --bucket "$BUCKET" --key index.html /tmp/day24-private-test.html
aws s3api get-bucket-policy --bucket "$BUCKET"

# CloudFront and OAC
aws cloudfront list-distributions --no-cli-pager
aws cloudfront get-distribution --id "$DIST_ID" --no-cli-pager
aws cloudfront list-origin-access-controls --no-cli-pager
```

## 15. Cleanup notes

For this lab, cleanup should be done only after saving screenshots and
evidence.

### Simplest local-only cleanup

`floci reset` clears **all simulated resources** in the running Floci
AWS emulator, not just Day 24. Use it only if there are no other Floci
resources you want to keep:

``` bash
floci reset
floci stop
floci status
```

This reset does not remove local project files such as HTML, JSON,
README, or evidence files. They remain on the WSL filesystem.

### Targeted cleanup

If other Floci experiments must be preserved, do not use `floci reset`.
Delete only the Day 24 distribution, OAC, bucket policy, and bucket
using the emulator's supported API workflow. CloudFront deletion
generally requires disabling a distribution first and using its current
ETag. A versioned S3 bucket requires removing every object version and
delete marker, not just current objects.

The lab's `list-object-versions` command failed with
`badly formed help string`, so do not assume the versioned bucket is
safe to delete based only on `aws s3 rm --recursive`. If targeted
cleanup is necessary, first troubleshoot version enumeration or use a
verified emulator-supported cleanup method.

## 16. Interview questions and answers from the Day 24 PDF

### 1. What is S3?

Amazon S3 is object storage for files and data, organised as objects
inside buckets.

### 2. What does versioning do?

It keeps multiple versions of an object to help recover from overwrites
or deletes.

### 3. Why keep Block Public Access on?

It reduces the risk of accidentally exposing bucket content.

### 4. What is CloudFront?

CloudFront is a CDN that caches content at edge locations and can serve
it over HTTPS.

### 5. What is OAC?

Origin Access Control lets a CloudFront distribution access a private S3
origin.

### 6. Why should direct S3 return 403?

The bucket is private; the site is intended to be accessed through
CloudFront. A 403 is expected for an unauthorised direct request when
the private-origin setup is correct.

### 7. What is invalidation?

An invalidation asks CloudFront to remove cached content before it
naturally expires.

### 8. What must be removed from a versioned bucket?

All object versions and delete markers, not just the current objects.

## 17. Additional commonly asked interview questions

### 9. What is the difference between a bucket and an object?

A bucket is a container. An object is the data stored in it, together
with metadata and a key.

### 10. What is an S3 object key?

It is the unique name used to identify an object inside a bucket, such
as `images/logo.png`. Slashes in keys create a folder-like naming
convention; S3 is fundamentally object storage.

### 11. What is the difference between `aws s3 sync` and `aws s3 cp`?

`cp` copies a specified file or set of files. `sync` compares source and
destination and transfers new or changed files. Be careful with
`--delete`, which can remove destination objects that aren't in the
source.

### 12. What is the difference between S3 Block Public Access and a bucket policy?

Block Public Access is a set of safeguards against public exposure. A
bucket policy is a resource-based JSON policy that grants or denies
actions to principals. Both matter to the final access decision.

### 13. Does enabling versioning mean files can never be deleted?

No. Versioning preserves prior versions, but delete markers and
permanent deletion of specific versions are still possible. Permissions
and retention controls are important.

### 14. What is an S3 delete marker?

In a versioned bucket, a normal delete commonly adds a delete marker as
the current version. Older object versions may still exist and continue
to consume storage.

### 15. What is an S3 lifecycle rule?

A lifecycle rule automatically transitions or expires objects according
to configured conditions. For versioned buckets, rules can also manage
noncurrent versions and expired delete markers.

### 16. What is the difference between an S3 REST endpoint and an S3 website endpoint?

A REST endpoint accesses the S3 API and supports private-origin patterns
such as OAC. An S3 static website endpoint serves website content with
website-style behaviour, but it is not the same origin type and does not
support OAC in the same way.

### 17. Why use CloudFront in front of S3?

CloudFront can reduce latency through edge caching, provide HTTPS, apply
viewer-facing controls, and reduce repeated requests to the origin.

### 18. What is an origin in CloudFront?

The origin is the backend source from which CloudFront retrieves
content, such as an S3 bucket or an application server.

### 19. What is the difference between OAC and OAI?

OAC is the newer recommended mechanism for signing requests to supported
origins such as private S3 buckets. OAI is the older CloudFront identity
mechanism historically used for S3 access.

### 20. What is a TTL in caching?

Time to Live is the duration a response may remain cached before it
needs to be refreshed, subject to cache policy and origin headers.

### 21. What happens when a user requests a cached object?

If a valid cached response is available at the serving edge, CloudFront
can return it without fetching the object from the origin. On a cache
miss or expired entry, CloudFront may request it from the origin.

### 22. Is invalidation always required after uploading a changed file?

No. The object may update after its TTL expires. Invalidation can be
used when the change must appear sooner, but it may have cost
implications.

### 23. What is the difference between `403 Forbidden` and `404 Not Found`?

`403` means the request is not allowed (or access is intentionally
concealed). `404` means the requested resource was not found, although
services may use either status in some configurations to avoid revealing
resource existence.

### 24. Why should we avoid putting AWS access keys in source control?

Keys can be stolen and misused to access resources or incur charges. Use
short-lived credentials or an appropriate identity/role mechanism, and
never commit secrets.

### 25. What does Infrastructure as Code mean?

Infrastructure as Code (IaC) defines infrastructure through
version-controlled files and repeatable tools, enabling consistent
review, deployment, and change management. JSON configuration used in
this lab is configuration input; by itself, it is not a complete IaC
workflow.

### 26. What is the difference between local emulation and cloud testing?

Local emulation is useful for fast, repeatable development without
creating real cloud resources. Cloud testing is still needed to validate
real IAM, service integrations, DNS, TLS, regional/global behaviour,
billing, and production-specific constraints.

### 27. Does a successful Floci test guarantee the same result in AWS?

No. Floci implements selected API behaviour locally, but the exact
behaviour may differ. Validate production-sensitive permissions,
networking, HTTPS, caching, and cleanup in the actual target environment
before deployment.

## 18. Day 24 completion summary

### Successfully demonstrated in Floci

-   Installed Floci CLI and started the local AWS emulator.
-   Created the `uploads` S3 bucket.
-   Enabled all four Block Public Access settings.
-   Enabled bucket versioning.
-   Uploaded `index.html` and `error.html`.
-   Downloaded `index.html` and confirmed it matched the local file.
-   Retrieved object metadata including a `VersionId`.
-   Created an OAC and a CloudFront distribution.
-   Saved a distribution-specific bucket policy.
-   Received `HTTP 200 OK` and website HTML from the local
    CloudFront-style hostname.
-   Saved configuration and verification evidence.

### Known limitations to document honestly

-   `list-object-versions` and `list-objects-v2` returned
    `badly formed help string` with the installed CLI/Python
    environment.
-   The simulated public `cloudfront.net` hostname did not resolve in
    WSL2; the Floci local hostname worked.
-   The local HTTP request returned `200 OK`; HTTPS redirection was
    configured but not verified.
-   Anonymous direct S3 denial and exact OAC enforcement were not
    conclusively verified.
-   Floci behaviour is not proof of production AWS behaviour.

The Day 24 PDF says no GitHub submission is required. Keep screenshots
focused on relevant proof and hide account identifiers, emails,
credentials, and private content before sharing publicly.
