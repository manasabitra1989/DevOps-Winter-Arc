
# Day 39 – AWS EKS: IAM, Cluster Access & IRSA

**DevOps Winter Arc – 90 Days Challenge**  
**Week 6 – AWS EKS**  
**Day 39 / 90**

---

## Overview

Day 39 focuses on identity, authentication, and authorization in Amazon Elastic Kubernetes Service (EKS).

In this task, we learn how IAM identities access an EKS cluster, how Kubernetes RBAC controls permissions inside the cluster, and how applications running inside Kubernetes can securely access AWS services using IAM Roles for Service Accounts (IRSA).

### Today's Topics

- IAM vs Kubernetes RBAC
- EKS cluster authentication
- EKS access entries
- Kubernetes ServiceAccounts
- OpenID Connect (OIDC)
- IAM Roles for Service Accounts (IRSA)
- Least-privilege permissions
- Secure application access to Amazon S3

### Environment Used

| Component | Purpose |
|---|---|
| Ubuntu WSL | Linux terminal |
| AWS CLI | AWS API commands |
| Floci | Local cloud emulation |
| kubectl | Kubernetes management |
| Minikube / local Kubernetes | Kubernetes RBAC practice |
| AWS Management Console | AWS IAM and EKS interface |

**Important:** Floci is used for local AWS API emulation. It is not a real AWS account or a real EKS cluster. Minikube is used for local Kubernetes exercises. Do not treat simulated AWS resources as actual AWS infrastructure.

---

# 1. Core Concepts

## 1.1 IAM – Identity and Access Management

AWS IAM controls access to AWS services and resources.

Examples:

- Allow an engineer to inspect an S3 bucket.
- Allow an application to download objects from S3.
- Allow an EKS cluster to use AWS services.
- Allow worker nodes to interact with AWS infrastructure.

IAM uses:

- Users
- Groups
- Roles
- Policies
- Trust policies

### Example

An application needs to read files from an S3 bucket.

Instead of storing AWS access keys inside the application, we can associate an IAM role with its Kubernetes ServiceAccount using IRSA.

## 1.2 Kubernetes RBAC

RBAC stands for Role-Based Access Control.

Kubernetes RBAC controls what authenticated users, groups, and ServiceAccounts can do inside a Kubernetes cluster.

Examples:

- Read Pods.
- List Deployments.
- Create Services.
- Delete resources.
- Access resources in a specific namespace.

Kubernetes RBAC uses four important objects:

| Object | Purpose |
|---|---|
| Role | Defines permissions inside a namespace |
| ClusterRole | Defines cluster-wide or reusable permissions |
| RoleBinding | Assigns a Role or ClusterRole to a subject |
| ClusterRoleBinding | Assigns permissions across the cluster |

### IAM vs Kubernetes RBAC

| IAM | Kubernetes RBAC |
|---|---|
| Controls AWS resource access | Controls Kubernetes API access |
| Uses IAM policies | Uses Roles and RoleBindings |
| Controls S3, EC2, EKS and other AWS services | Controls Pods, Services, Deployments and other Kubernetes resources |
| Works with AWS identities | Works with authenticated Kubernetes identities |

**Remember:** IAM authentication does not automatically grant Kubernetes permissions. The authenticated identity must also receive appropriate Kubernetes permissions.

## 1.3 EKS Access Entries

EKS access entries connect AWS IAM principals to Kubernetes cluster access.

An access entry identifies an IAM principal that is allowed to authenticate to an EKS cluster.

Access can be granted using:

- EKS access policies.
- Kubernetes groups that are mapped to RBAC permissions.

The cluster authentication mode determines which access-management mechanisms are available.

## 1.4 ServiceAccount

A Kubernetes ServiceAccount provides an identity to an application running inside a Pod.

For example:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader-sa
  namespace: dev
```

The application Pod uses this ServiceAccount rather than relying on a human user's identity.

## 1.5 OIDC

OIDC stands for OpenID Connect.

EKS uses an OIDC identity provider to establish trust between Kubernetes ServiceAccounts and AWS IAM roles.

OIDC provides an identity token that AWS STS can validate when the application requests temporary AWS credentials.

## 1.6 IRSA

IRSA stands for IAM Roles for Service Accounts.

It allows a Kubernetes ServiceAccount to assume a specific IAM role.

Benefits:

- No permanent AWS access keys inside application Pods.
- Temporary AWS credentials.
- Permissions can be scoped to a specific application.
- Different applications can use different IAM roles.
- Supports least-privilege security.

### IRSA Architecture

```text
                 Kubernetes Cluster
                         |
                         v
                 Application Pod
                         |
                         v
                 ServiceAccount
                    s3-reader-sa
                         |
                         v
                   OIDC Token
                         |
                         v
                 AWS STS Validation
                         |
                         v
                  IAM Role Assumed
                         |
                         v
                Temporary Credentials
                         |
                         v
                    Amazon S3
                  Read-only access
```

### Why not use the worker node IAM role?

A worker node IAM role is intended for node-level AWS operations.

Giving every application Pod broad access through the node role can expose unnecessary permissions.

IRSA allows each application to receive only the AWS permissions it needs.

---

# 2. Task A – Design IAM and Kubernetes Access

## Objective

Design access for two different identities:

1. An engineer who needs read-only access to Pods in the `dev` namespace.
2. An application Pod that needs read-only access to one S3 bucket.

These are separate access requirements.

## Part A – Engineer access to Pods

### Required access

The engineer should be able to:

- Get Pods.
- List Pods.
- Watch Pods.

The engineer should not be able to:

- Delete Pods.
- Create Pods.
- Modify workloads.

### Architecture

```text
Engineer IAM Identity
        |
        v
EKS Access Entry
        |
        v
Kubernetes Group
dev-pod-readers
        |
        v
RoleBinding
        |
        v
Role
dev-pod-reader
        |
        v
Read-only Pod access
in namespace dev
```

### Step 1 – Create the namespace

```bash
kubectl create namespace dev
```

Expected output:

```text
namespace/dev created
```

A namespace logically separates Kubernetes resources.

### Step 2 – Create a test Pod

```bash
kubectl run nginx-test \
  --image=nginx:stable \
  --namespace=dev
```

Expected output:

```text
pod/nginx-test created
```

Verify:

```bash
kubectl get pods -n dev
```

The Pod may initially show `ContainerCreating`. Wait for it to become `Running`.

### Step 3 – Create the Role

Create a file named:

`dev-pod-reader-role.yaml`

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: dev-pod-reader
  namespace: dev
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
```

Apply:

```bash
kubectl apply -f dev-pod-reader-role.yaml
```

Expected output:

```text
role.rbac.authorization.k8s.io/dev-pod-reader created
```

### Explanation

- `apiGroups: [""]` means the Kubernetes core API group.
- `resources: ["pods"]` restricts permissions to Pods.
- `get` allows reading an individual Pod.
- `list` allows listing Pods.
- `watch` allows watching Pod changes.

The Role does not grant permission to delete or modify Pods.

### Step 4 – Create the RoleBinding

Create:

`dev-pod-reader-binding.yaml`

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: dev-pod-reader-binding
  namespace: dev
subjects:
  - kind: Group
    name: dev-pod-readers
    apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: Role
  name: dev-pod-reader
  apiGroup: rbac.authorization.k8s.io
```

Apply:

```bash
kubectl apply -f dev-pod-reader-binding.yaml
```

Expected output:

```text
rolebinding.rbac.authorization.k8s.io/dev-pod-reader-binding created
```

### Explanation

The RoleBinding connects:

- Group: `dev-pod-readers`
- Role: `dev-pod-reader`

This means authenticated members of that group receive the permissions defined by the Role.

### Step 5 – Verify the Role and RoleBinding

```bash
kubectl describe role dev-pod-reader -n dev
```

```bash
kubectl describe rolebinding dev-pod-reader-binding -n dev
```

Check the group and role names.

### Step 6 – Test permissions

Initially, the following commands were used:

```bash
kubectl auth can-i get pods \
  --namespace dev \
  --as=dev-pod-readers
```

```bash
kubectl auth can-i list pods \
  --namespace dev \
  --as=dev-pod-readers
```

```bash
kubectl auth can-i delete pods \
  --namespace dev \
  --as=dev-pod-readers
```

These returned `no` because `--as` impersonates a username, not a group.

The RoleBinding refers to a Kubernetes group.

### Correct permission tests

Test the group using `--as-group`:

```bash
kubectl auth can-i get pods \
  --namespace dev \
  --as=test-engineer \
  --as-group=dev-pod-readers
```

Expected:

```text
yes
```

Test listing:

```bash
kubectl auth can-i list pods \
  --namespace dev \
  --as=test-engineer \
  --as-group=dev-pod-readers
```

Expected:

```text
yes
```

Test deleting:

```bash
kubectl auth can-i delete pods \
  --namespace dev \
  --as=test-engineer \
  --as-group=dev-pod-readers
```

Expected:

```text
no
```

### Important learning

`--as=test-engineer` represents a test username.

`--as-group=dev-pod-readers` adds the group to the impersonated identity.

This tests the Kubernetes RBAC mapping. It does not prove that a real AWS IAM identity has been mapped to the group through an EKS access entry.

---

## Part B – Application access to S3

### Requirement

An application running inside Kubernetes needs read-only access to one S3 bucket.

We design:

| Component | Name |
|---|---|
| Namespace | `dev` |
| ServiceAccount | `s3-reader-sa` |
| IAM role | `winter-arc-s3-reader-role` |
| Example S3 bucket | `winter-arc-day39-test-bucket` |
| Access | Read-only |

### Architecture

```text
Application Pod
      |
      v
ServiceAccount
s3-reader-sa
      |
      v
OIDC Identity
      |
      v
IAM Role
winter-arc-s3-reader-role
      |
      v
S3 Read-only Policy
      |
      v
Specific S3 Bucket
```

The application receives only the permissions required to read data from the selected bucket.

---

# 3. Task B – Read-only AWS Inspection

## Objective

Inspect the AWS identity, EKS clusters, cluster authentication mode, access entries, and Kubernetes ServiceAccounts.

No real AWS resources need to be created for these inspection commands.

### Step 1 – Check AWS identity

```bash
aws sts get-caller-identity
```

This identifies the AWS principal used by the AWS CLI.

It normally returns:

- Account ID.
- User ID.
- ARN.

For local Floci testing, use the Floci endpoint:

```bash
aws --endpoint-url http://localhost:4566 \
  sts get-caller-identity
```

### Step 2 – List EKS clusters

Real AWS:

```bash
aws eks list-clusters --region REGION
```

Floci:

```bash
aws --endpoint-url http://localhost:4566 \
  eks list-clusters \
  --region us-east-1
```

This lists clusters visible through the selected AWS API endpoint.

### Step 3 – Inspect authentication mode

```bash
aws eks describe-cluster \
  --name CLUSTER_NAME \
  --region REGION \
  --query "cluster.accessConfig.authenticationMode" \
  --output text
```

Floci example:

```bash
aws --endpoint-url http://localhost:4566 \
  eks describe-cluster \
  --name day39-eks \
  --region us-east-1 \
  --query "cluster.accessConfig.authenticationMode" \
  --output text
```

Authentication modes determine which EKS authentication mechanisms are enabled.

Common modes:

| Mode | Meaning |
|---|---|
| CONFIG_MAP | Uses the legacy `aws-auth` ConfigMap |
| API | Uses EKS access entries |
| API_AND_CONFIG_MAP | Supports both mechanisms |

Not every cluster supports every mode. Do not change the authentication mode just for this exercise.

### Step 4 – List EKS access entries

```bash
aws eks list-access-entries \
  --cluster-name CLUSTER_NAME \
  --region REGION
```

Floci example:

```bash
aws --endpoint-url http://localhost:4566 \
  eks list-access-entries \
  --cluster-name day39-eks \
  --region us-east-1
```

Access entries identify IAM principals associated with an EKS cluster.

### Step 5 – Inspect Kubernetes ServiceAccounts

```bash
kubectl get serviceaccounts -A
```

This displays ServiceAccounts across all namespaces.

Inspect the `dev` namespace:

```bash
kubectl get serviceaccounts -n dev
```

Inspect one ServiceAccount:

```bash
kubectl describe serviceaccount s3-reader-sa -n dev
```

**Note:** EKS access-entry API support in a local emulator does not automatically mean that access policies are enforced as Kubernetes permissions. Kubernetes RBAC was tested separately in Task A.

---

# 4. Task C – Understand the IRSA Authentication Flow

## Objective

Understand how an application Pod receives temporary AWS credentials without storing permanent access keys.

### IRSA flow

**Step 1 – Pod starts**

An application Pod runs in the Kubernetes cluster.

**Step 2 – Pod uses a ServiceAccount**

The Pod is configured with:

```yaml
serviceAccountName: s3-reader-sa
```

**Step 3 – Kubernetes provides an OIDC token**

The ServiceAccount identity is represented by a projected token.

**Step 4 – AWS STS validates the token**

The application requests credentials through:

`sts:AssumeRoleWithWebIdentity`

**Step 5 – IAM checks the trust policy**

The IAM role trust policy checks:

- The trusted OIDC provider.
- The token audience.
- The ServiceAccount subject.

**Step 6 – Temporary credentials are returned**

If the trust relationship and permissions are valid, AWS STS returns temporary credentials.

**Step 7 – Application accesses S3**

The application uses the temporary credentials to perform allowed S3 operations.

### Important OIDC trust policy conditions

Example subject:

```text
system:serviceaccount:dev:s3-reader-sa
```

Example audience:

```text
sts.amazonaws.com
```

The subject restricts role assumption to the intended namespace and ServiceAccount.

### Why temporary credentials?

Permanent access keys can be leaked, copied, or accidentally committed to source control.

Temporary credentials reduce the risk because they expire and are issued only after the identity is validated.

### Node IAM role vs IRSA

| Node IAM Role | IRSA |
|---|---|
| Assigned to worker nodes | Assigned through a Kubernetes ServiceAccount |
| Intended for node-level operations | Intended for application-specific AWS access |
| May be shared by workloads using node credentials | Can provide different permissions to different applications |
| Can expose broad permissions if misconfigured | Supports narrower permissions |

---

# 5. Task D – Optional IRSA Hands-on Lab

## Objective

Create a dedicated Kubernetes ServiceAccount and associate it with an IAM role that has read-only access to a specific S3 bucket.

**Important:** This is an optional lab. A complete IRSA test requires a real EKS OIDC integration or a local emulator that implements the complete OIDC and STS web-identity flow. A Minikube ServiceAccount annotation alone does not implement IRSA.

The commands below are organized into stages. Use Floci for supported local AWS API operations and use a real EKS environment only with explicit authorization and cost review.

## Step 1 – Confirm the Kubernetes context

```bash
kubectl config current-context
```

```bash
kubectl get nodes
```

This ensures you know which Kubernetes cluster receives your commands.

Do not assume the current context is EKS.

## Step 2 – Start Floci

Check Docker:

```bash
docker info
```

Start Floci:

```bash
floci start
```

Load the environment:

```bash
eval "$(floci env)"
```

Check the endpoint:

```bash
echo "$AWS_ENDPOINT_URL"
```

Expected local endpoint:

```text
http://localhost:4566
```

Use an explicit endpoint for local AWS CLI commands:

```bash
--endpoint-url http://localhost:4566
```

This prevents accidental calls to the real AWS account.

## Step 3 – Inspect the EKS OIDC issuer

```bash
aws --endpoint-url http://localhost:4566 \
  eks describe-cluster \
  --name day39-eks \
  --region us-east-1 \
  --query "cluster.identity.oidc.issuer" \
  --output text
```

Replace the cluster name if necessary.

An issuer URL is required for the OIDC trust relationship.

If the cluster does not exist or no issuer is returned, stop and investigate. Do not invent an issuer URL.

## Step 4 – Create the ServiceAccount

Check whether it already exists:

```bash
kubectl get serviceaccount s3-reader-sa -n dev
```

If it does not exist:

```bash
kubectl create serviceaccount s3-reader-sa -n dev
```

Verify:

```bash
kubectl get serviceaccount s3-reader-sa -n dev -o yaml
```

Expected identity:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: s3-reader-sa
  namespace: dev
```

## Step 5 – Prepare the IAM trust policy

Create:

`irsa-trust-policy.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::ACCOUNT_ID:oidc-provider/OIDC_PROVIDER_HOSTPATH"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "OIDC_PROVIDER_HOSTPATH:sub": "system:serviceaccount:dev:s3-reader-sa",
          "OIDC_PROVIDER_HOSTPATH:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

Replace:

- `ACCOUNT_ID` with the appropriate account ID.
- `OIDC_PROVIDER_HOSTPATH` with the exact host and path of the registered OIDC provider, without `https://`.

The provider ARN and condition-key prefix must match the actual registered provider.

This is a template, not a ready-to-run policy.

## Step 6 – Prepare the S3 read-only policy

Create:

`s3-readonly-policy.json`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::winter-arc-day39-test-bucket"
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::winter-arc-day39-test-bucket/*"
    }
  ]
}
```

### Explanation

` s3:ListBucket ` allows listing the contents of the bucket.

` s3:GetObject ` allows downloading objects from the bucket.

The policy does not grant:

- `s3:PutObject`
- `s3:DeleteObject`
- `s3:DeleteBucket`

The example bucket name must be replaced with the actual bucket used for testing.

## Step 7 – Create the IAM role in Floci

Only proceed after confirming the OIDC provider and trust policy are valid in the local environment.

```bash
aws --endpoint-url http://localhost:4566 \
  iam create-role \
  --role-name winter-arc-s3-reader-role \
  --assume-role-policy-document file://irsa-trust-policy.json
```

The response should include a role ARN.

Inspect the role:

```bash
aws --endpoint-url http://localhost:4566 \
  iam get-role \
  --role-name winter-arc-s3-reader-role
```

## Step 8 – Attach the S3 read-only policy

```bash
aws --endpoint-url http://localhost:4566 \
  iam put-role-policy \
  --role-name winter-arc-s3-reader-role \
  --policy-name S3ReadOnlyAccess \
  --policy-document file://s3-readonly-policy.json
```

Verify:

```bash
aws --endpoint-url http://localhost:4566 \
  iam get-role-policy \
  --role-name winter-arc-s3-reader-role \
  --policy-name S3ReadOnlyAccess
```

## Step 9 – Annotate the ServiceAccount

Use the actual IAM role ARN returned by the role creation command.

```bash
kubectl annotate serviceaccount s3-reader-sa \
  -n dev \
  eks.amazonaws.com/role-arn=YOUR_IAM_ROLE_ARN
```

Verify:

```bash
kubectl describe serviceaccount s3-reader-sa -n dev
```

Look for:

```text
eks.amazonaws.com/role-arn
```

**Important:** The annotation is an EKS IRSA convention. It does not independently configure a Kubernetes cluster or guarantee that temporary credentials can be obtained.

## Step 10 – Create a test Pod

Create:

`irsa-test-pod.yaml`

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: irsa-test-pod
  namespace: dev
spec:
  serviceAccountName: s3-reader-sa
  containers:
    - name: aws-cli
      image: amazon/aws-cli:latest
      command:
        - sleep
        - "3600"
```

Apply:

```bash
kubectl apply -f irsa-test-pod.yaml
```

Check:

```bash
kubectl get pod irsa-test-pod -n dev
```

Inspect the ServiceAccount assignment:

```bash
kubectl get pod irsa-test-pod -n dev \
  -o jsonpath='{.spec.serviceAccountName}{"\n"}'
```

Expected:

```text
s3-reader-sa
```

## Step 11 – Test AWS identity

Only after the environment supports the complete IRSA web-identity flow:

```bash
kubectl exec -it irsa-test-pod -n dev -- \
  aws sts get-caller-identity
```

The identity should represent an assumed IAM role.

## Step 12 – Test S3 read access

```bash
kubectl exec -it irsa-test-pod -n dev -- \
  aws s3 ls s3://winter-arc-day39-test-bucket
```

Expected: the bucket contents are listed, or no output if the bucket is empty.

A write operation should be denied by the read-only policy.

### Important limitation

Floci can emulate AWS APIs, but support for EKS metadata, IAM operations, OIDC provider registration, and complete STS web-identity credential exchange are separate capabilities.

A successful IAM role creation or ServiceAccount annotation does not prove end-to-end IRSA.

If the STS identity test fails because the token exchange is unsupported, document the limitation rather than adding permanent AWS keys to the Pod.

---

# 6. AWS Management Console – Where to Inspect

No real EKS cluster, VPC, or IAM role was assumed to exist for this exercise.

The following console walkthrough is for learning and inspection. Do not click Create or attach policies in a real account without authorization and review.

## 6.1 IAM Console

1. Open the AWS Management Console.
2. Search for IAM.
3. Open the IAM dashboard.
4. Explore Roles.
5. Open the role details page to understand permissions and trust relationships.
6. Locate the JSON policy editor.

For a real IRSA setup, the role trust policy must refer to the actual EKS OIDC provider.

Do not use the example account ID or placeholder provider from the local exercise.

## 6.2 EKS Console

1. Search for Amazon EKS.
2. Open the EKS dashboard.
3. Select Clusters.
4. Inspect the cluster overview if an authorized cluster exists.
5. Locate the Access tab.
6. Review access entries and authentication configuration.

No cluster needs to be created for the console walkthrough.

## 6.3 S3 Console

1. Search for S3.
2. Open the S3 dashboard.
3. Inspect the bucket list.
4. Open a bucket only if you are authorized.
5. Review permissions and bucket policies.

The exercise uses a read-only policy. Do not make a bucket public.

---

# 7. Troubleshooting

## Problem 1 – kubectl returns Forbidden

Possible reason:

The authenticated identity does not have the required Kubernetes RBAC permissions.

Check:

```bash
kubectl auth can-i get pods -n dev
```

For group testing:

```bash
kubectl auth can-i get pods \
  -n dev \
  --as=test-engineer \
  --as-group=dev-pod-readers
```

Inspect:

```bash
kubectl describe role dev-pod-reader -n dev
kubectl describe rolebinding dev-pod-reader-binding -n dev
```

## Problem 2 – All group permission tests return no

Possible reason:

The group was passed as a username using `--as`.

Incorrect:

```bash
kubectl auth can-i get pods \
  -n dev \
  --as=dev-pod-readers
```

Correct:

```bash
kubectl auth can-i get pods \
  -n dev \
  --as=test-engineer \
  --as-group=dev-pod-readers
```

## Problem 3 – ServiceAccount not found

Check:

```bash
kubectl get serviceaccounts -n dev
```

Create it if missing:

```bash
kubectl create serviceaccount s3-reader-sa -n dev
```

## Problem 4 – IAM AccessDenied

Possible reasons:

- Incorrect IAM role policy.
- Incorrect trust relationship.
- Wrong S3 bucket ARN.
- Missing S3 permissions.
- Wrong IAM principal.

Inspect the role:

```bash
aws --endpoint-url http://localhost:4566 \
  iam get-role \
  --role-name winter-arc-s3-reader-role
```

Inspect its inline policy:

```bash
aws --endpoint-url http://localhost:4566 \
  iam get-role-policy \
  --role-name winter-arc-s3-reader-role \
  --policy-name S3ReadOnlyAccess
```

## Problem 5 – Pod cannot assume IAM role

Possible reasons:

- OIDC provider is not registered.
- Trust policy uses the wrong provider ARN.
- Subject does not match the ServiceAccount.
- Audience does not match `sts.amazonaws.com`.
- The cluster does not support the complete IRSA integration.

Check the ServiceAccount:

```bash
kubectl describe serviceaccount s3-reader-sa -n dev
```

Check the cluster issuer:

```bash
aws --endpoint-url http://localhost:4566 \
  eks describe-cluster \
  --name day39-eks \
  --region us-east-1 \
  --query "cluster.identity.oidc.issuer" \
  --output text
```

Do not solve this problem by placing permanent AWS credentials inside the Pod.

## Problem 6 – Pod remains ContainerCreating

Inspect:

```bash
kubectl describe pod nginx-test -n dev
```

Check events:

```bash
kubectl get events -n dev --sort-by=.lastTimestamp
```

Possible causes include image-pull problems, network issues, or unavailable container runtime resources.

---

# 8. Complete Cleanup

Run cleanup against the same Kubernetes context and Floci environment where you created the resources.

## Step 1 – Check the current context

```bash
kubectl config current-context
```

## Step 2 – Delete the IRSA test Pod

```bash
kubectl delete pod irsa-test-pod \
  -n dev \
  --ignore-not-found
```

## Step 3 – Delete the Nginx test Pod

```bash
kubectl delete pod nginx-test \
  -n dev \
  --ignore-not-found
```

## Step 4 – Delete the IRSA ServiceAccount

```bash
kubectl delete serviceaccount s3-reader-sa \
  -n dev \
  --ignore-not-found
```

## Step 5 – Delete the RoleBinding

```bash
kubectl delete rolebinding dev-pod-reader-binding \
  -n dev \
  --ignore-not-found
```

## Step 6 – Delete the Role

```bash
kubectl delete role dev-pod-reader \
  -n dev \
  --ignore-not-found
```

## Step 7 – Delete the namespace

Only do this after all Day 39 work in the namespace is finished.

```bash
kubectl delete namespace dev
```

## Step 8 – Delete the Floci inline IAM policy

```bash
aws --endpoint-url http://localhost:4566 \
  iam delete-role-policy \
  --role-name winter-arc-s3-reader-role \
  --policy-name S3ReadOnlyAccess
```

## Step 9 – Delete the Floci IAM role

```bash
aws --endpoint-url http://localhost:4566 \
  iam delete-role \
  --role-name winter-arc-s3-reader-role
```

If the role or policy was never created, skip the corresponding deletion.

## Step 10 – Remove local Task D files

From the Day 39 directory:

```bash
rm -f irsa-trust-policy.json
rm -f s3-readonly-policy.json
rm -f irsa-test-pod.yaml
```

This removes only the three named files.

## Step 11 – Final verification

```bash
kubectl get namespaces
```

```bash
kubectl get pods -A
```

```bash
kubectl get roles,rolebindings -A
```

Check the Floci role:

```bash
aws --endpoint-url http://localhost:4566 \
  iam get-role \
  --role-name winter-arc-s3-reader-role
```

A `NoSuchEntity` response means the role no longer exists.

### Cleanup precautions

- Do not delete shared namespaces.
- Do not delete shared OIDC providers without checking dependencies.
- Do not delete shared S3 buckets.
- Do not delete a real AWS EKS cluster as part of this local cleanup.
- Floci and Docker do not need to be uninstalled.

---

# 9. Interview Questions and Answers

### 1. What is IAM?

IAM is AWS Identity and Access Management. It controls who can access AWS services and which actions they can perform.

### 2. What is Kubernetes RBAC?

RBAC is a Kubernetes authorization mechanism that grants permissions to users, groups, and ServiceAccounts through Roles and RoleBindings.

### 3. What is the difference between IAM and Kubernetes RBAC?

IAM controls access to AWS resources, while Kubernetes RBAC controls access to Kubernetes API resources.

### 4. What is an EKS access entry?

An EKS access entry associates an IAM principal with an EKS cluster and provides a mechanism for granting cluster access.

### 5. What is a Kubernetes ServiceAccount?

A ServiceAccount provides an identity to an application or process running inside a Kubernetes Pod.

### 6. What is IRSA?

IRSA stands for IAM Roles for Service Accounts. It allows Kubernetes ServiceAccounts to assume IAM roles and obtain temporary AWS credentials.

### 7. What is OIDC?

OIDC is an identity layer built on OAuth 2.0. In EKS IRSA, it allows AWS to validate Kubernetes ServiceAccount identity tokens.

### 8. What is AWS STS?

AWS Security Token Service provides temporary security credentials for authorized identities.

### 9. Why is IRSA better than storing AWS access keys in Pods?

IRSA avoids long-lived credentials inside applications and provides temporary, scoped credentials.

### 10. What is a trust policy?

A trust policy defines which principals are allowed to assume an IAM role.

### 11. What does `sts:AssumeRoleWithWebIdentity` do?

It allows an identity with a valid web identity token to request temporary credentials for an IAM role.

### 12. What does the OIDC subject represent?

The subject identifies the Kubernetes ServiceAccount, including its namespace and name.

Example:

```text
system:serviceaccount:dev:s3-reader-sa
```

### 13. Why should applications not use broad node IAM permissions?

A broad node role may expose unnecessary AWS permissions to workloads. IRSA allows application-specific permissions.

### 14. What is least privilege?

Least privilege means granting only the minimum permissions required to perform a task.

### 15. Why do we use `--as-group` during Kubernetes RBAC testing?

Because it tests a group identity. The `--as` option impersonates a username.

---

# 10. Completion Checklist

- [x] Understood IAM vs Kubernetes RBAC.
- [x] Designed engineer access to Pods in the `dev` namespace.
- [x] Created the `dev` namespace.
- [x] Created the `nginx-test` Pod.
- [x] Created the `dev-pod-reader` Role.
- [x] Created the `dev-pod-reader-binding` RoleBinding.
- [x] Identified why the initial `--as` permission tests returned `no`.
- [x] Prepared the corrected group-based permission tests.
- [x] Designed application access to a specific S3 bucket.
- [x] Studied the EKS access-entry and authentication-mode commands.
- [x] Learned the OIDC and IRSA authentication flow.
- [x] Prepared the IRSA trust policy template.
- [x] Prepared the S3 read-only policy.
- [x] Prepared the ServiceAccount and test Pod manifests.
- [x] Documented the complete cleanup commands.

**Note:** A checked item indicates that the task or its design/code was completed or prepared. It does not claim that a real AWS EKS cluster, real IAM role, OIDC provider, or successful end-to-end IRSA credential exchange was created or verified.

---

# Day 39 – Key Takeaways

1. IAM controls access to AWS services.
2. Kubernetes RBAC controls access to Kubernetes resources.
3. EKS access entries connect IAM principals with cluster access.
4. ServiceAccounts provide identities to Kubernetes applications.
5. OIDC enables identity verification for IRSA.
6. IRSA provides temporary AWS credentials to applications.
7. Least privilege reduces the impact of compromised workloads.
8. Application Pods should not depend on broad worker-node permissions.
9. Permanent AWS access keys should not be stored inside application Pods.
10. Local emulation and real AWS infrastructure must be clearly distinguished.

**Day 39 complete: You have practiced Kubernetes namespace-scoped RBAC, designed IAM-based cluster access, and learned how IRSA securely connects Kubernetes ServiceAccounts with AWS IAM roles.**
