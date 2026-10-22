# Day 21 — Kubernetes Security, RBAC & Troubleshooting

## 🎯 Objective

Learn how to secure Kubernetes workloads, implement least-privilege access, enforce Pod Security Standards, and troubleshoot broken Deployments.

This lab covers:

- Role-Based Access Control (RBAC)
- ServiceAccounts, Roles, and RoleBindings
- `kubectl auth can-i` permission verification
- Pod `securityContext` and non-root execution
- Pod Security Standards and restricted enforcement
- Troubleshooting `ImagePullBackOff`, `CrashLoopBackOff`, and `Pending` Pods
- Debugging with `kubectl get`, `describe`, `logs`, Events, and `exec`

**Main goal:** Work like an on-call DevOps engineer by gathering evidence before changing a resource and making the smallest safe fix.

---

## 📁 Project Structure

```text
day21-security-debug/
├── README.md
├── rbac.yaml
├── secure-pod.yaml
└── evidence/
    ├── rbac-permissions.png
    ├── restricted-policy.png
    ├── broken1-debug.png
    ├── broken2-debug.png
    ├── broken3-debug.png
    └── repaired-pods.png
```

The screenshot names are suggestions. Save your own evidence after completing each task.

---

## 🧰 Prerequisites

- Existing `kind` Kubernetes cluster
- `kubectl` installed and configured
- Ubuntu/WSL terminal access
- Basic familiarity with Kubernetes namespaces, Pods, and Deployments

Check the cluster:

```bash
kubectl config current-context
kubectl get nodes
kubectl get namespaces
```

**Explanation:**

- `kubectl config current-context` shows the active Kubernetes context.
- `kubectl get nodes` checks node readiness.
- `kubectl get namespaces` lists the cluster's namespaces.

The lab uses the existing cluster. Do not recreate or delete the shared `kind` cluster.

---

# Part 1 — Key Concepts

## 1. Role-Based Access Control (RBAC)

RBAC determines who can perform which actions on which Kubernetes resources.

| Resource | Purpose |
|---|---|
| ServiceAccount | Identity used by Pods or tools |
| Role | Grants permissions within a namespace |
| ClusterRole | Provides cluster-scoped or reusable permissions |
| RoleBinding | Connects a Role to a subject |
| ClusterRoleBinding | Grants ClusterRole permissions at cluster scope |

**Least privilege:** Grant only the permissions an identity needs. A read-only viewer should not be able to delete Pods.

RBAC does not grant permissions by default simply because an identity exists. Permissions must be granted through appropriate bindings.

## 2. Pod security

Important security settings:

| Setting | Purpose |
|---|---|
| `runAsNonRoot` | Requires a non-root user |
| `runAsUser` | Specifies the Linux user ID |
| `readOnlyRootFilesystem` | Makes the container root filesystem read-only |
| `allowPrivilegeEscalation: false` | Prevents privilege escalation through supported mechanisms |
| `capabilities.drop: ["ALL"]` | Removes Linux capabilities |
| `seccompProfile: RuntimeDefault` | Uses the runtime's default seccomp profile |

## 3. Pod Security Standards

Kubernetes defines three Pod Security Standard profiles:

- **Privileged:** least restrictive.
- **Baseline:** prevents many known privilege escalations.
- **Restricted:** strongest standard profile, intended for hardened workloads.

The `secure` namespace will enforce the restricted profile.

## 4. Troubleshooting routine

Remember:

**`get → describe → logs → events → exec`**

Start by identifying the affected resource. Inspect the Pod details and Events before guessing or changing configuration. Use `logs --previous` when a container has crashed.

---

# Part 2 — Hands-on Lab

## Task A — Create namespaces and a ServiceAccount

Create the namespaces:

```bash
kubectl create namespace secure
kubectl create namespace lab
```

The `secure` namespace is for RBAC and Pod security. The `lab` namespace is for intentionally broken Deployments.

If a namespace already exists, inspect it before continuing rather than deleting it.

Create the viewer ServiceAccount:

```bash
kubectl create serviceaccount viewer -n secure
```

A ServiceAccount provides an identity, but does not automatically grant the read permissions required by this exercise.

Verify:

```bash
kubectl get serviceaccount -n secure
```

---

## Task B — Configure RBAC

Create `rbac.yaml`:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: pod-reader
  namespace: secure
rules:
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: viewer-pods
  namespace: secure
subjects:
  - kind: ServiceAccount
    name: viewer
    namespace: secure
roleRef:
  kind: Role
  name: pod-reader
  apiGroup: rbac.authorization.k8s.io
```

### YAML explanation

- `kind: Role` defines namespace-scoped permissions.
- `resources` specifies Pods and Pod logs.
- `verbs` allows reading individual resources, listing resources, and watching changes.
- `kind: RoleBinding` connects the Role to the viewer ServiceAccount.
- `roleRef` identifies the Role being granted.

The Role does not include the `delete` verb.

Apply the configuration:

```bash
kubectl apply -f rbac.yaml
```

Verify:

```bash
kubectl get role,rolebinding -n secure
```

### Test the permissions

```bash
kubectl auth can-i get pods -n secure \
  --as=system:serviceaccount:secure:viewer
```

Expected:

```text
yes
```

Test deletion:

```bash
kubectl auth can-i delete pods -n secure \
  --as=system:serviceaccount:secure:viewer
```

Expected:

```text
no
```

`--as` asks Kubernetes to evaluate permissions as the specified identity. The current account must be authorized to impersonate that identity.

**Success criteria:** The viewer can read Pods but cannot delete them.

If the results differ, inspect the Role and RoleBinding:

```bash
kubectl describe role pod-reader -n secure
kubectl describe rolebinding viewer-pods -n secure
```

---

## Task C — Enforce restricted Pod Security

Label the namespace:

```bash
kubectl label namespace secure \
  pod-security.kubernetes.io/enforce=restricted
```

Verify:

```bash
kubectl get namespace secure --show-labels
```

The label enables restricted Pod Security enforcement for applicable Pod admissions in the namespace.

### Create the hardened Pod

Create `secure-pod.yaml`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
  namespace: secure
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 10001
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      image: busybox:1.36
      command: ["sleep", "3600"]
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: ["ALL"]
```

### Important YAML fields

- `runAsNonRoot: true`: requires non-root execution.
- `runAsUser: 10001`: sets the process user ID.
- `seccompProfile`: uses the runtime's default syscall filtering profile.
- `allowPrivilegeEscalation: false`: prevents supported privilege escalation.
- `readOnlyRootFilesystem: true`: blocks writes to the container's root filesystem.
- `capabilities.drop: ["ALL"]`: removes all Linux capabilities.
- `sleep 3600`: keeps the BusyBox container running for one hour.

Apply and inspect:

```bash
kubectl apply -f secure-pod.yaml
kubectl get pod secure-pod -n secure
kubectl describe pod secure-pod -n secure
```

Expected: the Pod is admitted and eventually reaches `Running`.

### Prove the policy rejects a root-based Pod

Run:

```bash
kubectl run root-pod --image=nginx:1.27 -n secure
```

The restricted policy should reject this Pod because it does not declare the required non-root security configuration.

Verify:

```bash
kubectl get pods -n secure
```

The `secure-pod` should run; the rejected `root-pod` should not be successfully created.

**Important:** Keep the restricted policy enabled. Do not weaken it just to admit the test Pod.

---

## Task D — Create three broken Deployments

The PDF deliberately introduces three failure types:

| Deployment | Expected symptom | Root cause |
|---|---|---|
| `broken1` | `ImagePullBackOff` | Invalid image tag |
| `broken2` | `CrashLoopBackOff` | Container command exits with code 1 |
| `broken3` | `Pending` | Memory request exceeds node capacity |

Create the first Deployment:

```bash
kubectl create deployment broken1 -n lab --image=nginx:1.99.99
```

Create the second:

```bash
kubectl create deployment broken2 -n lab --image=busybox:1.36 \
  -- sh -c "exit 1"
```

Create the third:

```bash
kubectl create deployment broken3 -n lab --image=nginx:1.27
```

Set an excessive memory request:

```bash
kubectl set resources deployment/broken3 -n lab \
  --requests=memory=64Gi
```

**Explanation:**

- `kubectl create deployment` creates a Deployment and its managed Pod.
- The invalid image tag causes an image-pull failure.
- `exit 1` immediately terminates the BusyBox process with an error status.
- `64Gi` requests 64 gibibytes of memory, which is too much for a typical local `kind` node.

Inspect the initial state:

```bash
kubectl get deployments,pods -n lab
```

---

# Part 3 — Diagnose and Repair the Deployments

## Debug routine

For each Deployment:

```bash
kubectl get pods -n lab
kubectl describe pod <POD_NAME> -n lab
kubectl logs <POD_NAME> -n lab --previous
kubectl get events -n lab --sort-by=.lastTimestamp
```

Replace `<POD_NAME>` with the actual Pod name.

Not every command will return useful output for every failure. For example, `--previous` is most useful when a container has terminated and a previous instance exists.

## Debug table

Use this table in your incident notes. Record what you actually observe in your cluster.

| Deployment | Symptom / evidence | Root cause | Fix / final status |
|---|---|---|---|
| `broken1` | `ImagePullBackOff`; Events report image-pull failure | Invalid image tag | Changed to `nginx:1.27`; verify Ready |
| `broken2` | `CrashLoopBackOff`; exit code 1 | Command exits immediately | Changed command to `sleep 3600`; verify Ready |
| `broken3` | `Pending`; Events report insufficient memory or unsatisfied scheduling | `64Gi` memory request too large | Reduced to `64Mi`; verify Ready |

### Repair `broken1`

Inspect the Pod and Events, then fix the image:

```bash
kubectl set image deployment/broken1 -n lab nginx=nginx:1.27
```

This changes the container image and triggers a Deployment rollout.

Verify:

```bash
kubectl rollout status deployment/broken1 -n lab
kubectl get pods -n lab
```

### Repair `broken2`

Inspect the Pod:

```bash
kubectl describe pod <POD_NAME> -n lab
kubectl logs <POD_NAME> -n lab --previous
```

Change the command to a long-running command:

```bash
kubectl patch deployment broken2 -n lab --type=strategic -p \
'{"spec":{"template":{"spec":{"containers":[{"name":"busybox","command":["sh","-c","sleep 3600"]}]}}}}'
```

The patch changes the container's command from an immediately exiting process to one that stays alive for the exercise.

Verify:

```bash
kubectl rollout status deployment/broken2 -n lab
kubectl get pods -n lab
```

### Repair `broken3`

Inspect the Pod and Events:

```bash
kubectl describe pod <POD_NAME> -n lab
kubectl get events -n lab --sort-by=.lastTimestamp
```

Reduce the memory request:

```bash
kubectl set resources deployment/broken3 -n lab \
  --requests=memory=64Mi
```

This requests 64 mebibytes instead of 64 gibibytes.

Verify:

```bash
kubectl rollout status deployment/broken3 -n lab
kubectl get pods -n lab
```

**Note:** The expected symptoms depend on cluster capacity, image availability, and runtime behavior. Use actual Events and logs to confirm the diagnosis before recording the result.

---

# Part 4 — Final Verification

Check all Deployments:

```bash
kubectl get deployments -n lab
kubectl get pods -n lab
```

Check each rollout:

```bash
kubectl rollout status deployment/broken1 -n lab
kubectl rollout status deployment/broken2 -n lab
kubectl rollout status deployment/broken3 -n lab
```

Expected: each Deployment has one available replica, and its Pod is running and ready.

Verify the RBAC checks again:

```bash
kubectl auth can-i get pods -n secure \
  --as=system:serviceaccount:secure:viewer

kubectl auth can-i delete pods -n secure \
  --as=system:serviceaccount:secure:viewer
```

Expected: `yes`, then `no`.

Inspect the security Pod:

```bash
kubectl get pod secure-pod -n secure
kubectl describe pod secure-pod -n secure
```

---

# Part 5 — Troubleshooting Reference

| Symptom | First checks | Common cause |
|---|---|---|
| `Pending` | `kubectl describe pod`; inspect Events | Insufficient resources, scheduling constraints, or storage issues |
| `ImagePullBackOff` | `kubectl describe pod`; inspect Events | Invalid image/tag, registry access, or image unavailable |
| `CrashLoopBackOff` | `kubectl logs --previous`; `kubectl describe pod` | Process exits, invalid command, or application configuration |
| `Running`, but not working | Inspect logs and object details | Application-level or configuration problem |
| RBAC returns unexpected result | Inspect Role, RoleBinding, and `can-i` output | Incorrect permissions, subject, namespace, or impersonation authorization |
| Pod rejected by policy | Inspect admission error and security settings | Pod violates the namespace's enforced Pod Security Standard |

### Repeatable debugging method

1. **Get:** Identify the failing resource and current status.
2. **Describe:** Inspect conditions and Events.
3. **Logs:** Read application output.
4. **Events:** Identify scheduling, image-pull, admission, or startup errors.
5. **Exec:** Inspect a running container when necessary.

Do not blindly restart a workload or change its configuration before gathering evidence.

---

# Part 6 — Evidence and GitHub Deliverables

Save evidence inside the `evidence/` folder.

Required evidence:

- [ ] `kubectl auth can-i` shows `yes` for reading Pods and `no` for deleting them.
- [ ] The restricted policy rejects `root-pod`.
- [ ] `secure-pod` runs with the hardened security settings.
- [ ] Evidence of the initial failure for each broken Deployment.
- [ ] All three repaired Pods reach `Running` and `Ready`.
- [ ] The debug table documents symptom, evidence, root cause, fix, and final status.

Suggested final structure:

```text
day21-security-debug/
├── README.md
├── rbac.yaml
├── secure-pod.yaml
└── evidence/
    ├── rbac-permissions.png
    ├── restricted-policy.png
    ├── broken1-debug.png
    ├── broken2-debug.png
    ├── broken3-debug.png
    └── repaired-pods.png
```

Check the files before submitting:

```bash
ls -R
git status --short
```

Only include screenshots and findings that you actually captured during the lab.

---

# Part 7 — Interview Questions and Answers

### 1. What is RBAC?

RBAC controls who can perform which actions on which Kubernetes resources and within what scope.

### 2. What is the difference between Role and ClusterRole?

A Role is namespace-scoped. A ClusterRole can provide cluster-scoped permissions or reusable permissions across namespaces.

### 3. What does a RoleBinding do?

It binds a Role to a subject, such as a user, group, or ServiceAccount, within a namespace.

### 4. How do you verify permissions in Kubernetes?

Use `kubectl auth can-i` with the action, resource, namespace, and optionally `--as` to test a particular identity.

### 5. Why should containers avoid running as root?

Non-root execution reduces the potential impact of a compromised or faulty container.

### 6. What is `securityContext`?

It configures Pod or container security settings, including user ID, privilege escalation, filesystem access, and Linux capabilities.

### 7. What does `readOnlyRootFilesystem` do?

It prevents writes to the container's root filesystem. Applications that need writable paths must use appropriate writable volumes or other supported storage.

### 8. What are Pod Security Standards?

They define the `privileged`, `baseline`, and `restricted` profiles for Pod security.

### 9. Why was `root-pod` rejected?

The namespace enforces the restricted profile, and Pod Security admission rejects Pods that violate its requirements.

### 10. What should you do first when a Pod is Pending?

Run `kubectl describe pod` and inspect Events for scheduling constraints, resource shortages, or other admission and placement problems.

### 11. What does `ImagePullBackOff` mean?

Kubernetes cannot successfully pull the container image. Check the image name, tag, registry access, and Events.

### 12. How do you debug `CrashLoopBackOff`?

Inspect `kubectl logs --previous` and `kubectl describe pod`, paying attention to exit codes, Events, and container startup configuration.

### 13. Why is least privilege important?

It limits accidental or malicious actions to only what an identity needs to perform its job.

### 14. What is the recommended debugging order?

`get → describe → logs → events → exec`. Inspect the current state and evidence before making changes.

---

# Part 8 — Completion Checklist

## Security and RBAC

- [ ] Confirmed the existing `kind` cluster is healthy.
- [ ] Created the `secure` and `lab` namespaces.
- [ ] Created the `viewer` ServiceAccount.
- [ ] Created `rbac.yaml` with a Role and RoleBinding.
- [ ] Verified that `viewer` can read Pods.
- [ ] Verified that `viewer` cannot delete Pods.

## Pod Security

- [ ] Enabled restricted Pod Security enforcement on `secure`.
- [ ] Created `secure-pod.yaml`.
- [ ] Confirmed `secure-pod` is admitted and runs as non-root.
- [ ] Confirmed the restricted policy rejects `root-pod`.
- [ ] Saved evidence of the policy rejection.

## Troubleshooting

- [ ] Created `broken1` with an invalid image tag.
- [ ] Recorded evidence of the image-pull failure.
- [ ] Fixed `broken1` and verified its rollout.
- [ ] Created `broken2` with a command that exits with code 1.
- [ ] Recorded evidence of the crash.
- [ ] Fixed `broken2` and verified its rollout.
- [ ] Created `broken3` with a `64Gi` memory request.
- [ ] Recorded evidence of the scheduling failure.
- [ ] Reduced its memory request and verified its rollout.
- [ ] Completed the debug table using actual observations.

## Submission

- [ ] Saved `rbac.yaml`.
- [ ] Saved `secure-pod.yaml`.
- [ ] Saved this `README.md`.
- [ ] Saved screenshots in `evidence/`.
- [ ] Reviewed the interview questions.
- [ ] Checked the Git working tree before submission.

---

# Part 9 — Cleanup

**Save your evidence and files before cleanup.** Inspect the namespaces first:

```bash
kubectl get all -n secure
kubectl get all -n lab
```

Only if both namespaces contain disposable resources from this lab, delete them:

```bash
kubectl delete namespace secure lab
```

This deletes resources inside those namespaces, including the lab Deployments, Pods, ServiceAccount, Role, RoleBinding, and security settings attached to the `secure` namespace.

Verify:

```bash
kubectl get namespaces
```

Do not delete the shared `kind` cluster if you still need it for other Winter Arc tasks.

---

# 🎓 Final Learning Summary

In Day 21, I practiced Kubernetes security and incident troubleshooting:

- RBAC provides scoped permissions for identities.
- ServiceAccounts represent identities used by workloads or tools.
- Roles and RoleBindings implement least-privilege access.
- Pod security settings reduce container privileges and restrict filesystem access.
- Pod Security Standards enforce security policies at admission.
- `kubectl describe`, logs, and Events help identify the root cause of failures.
- A broken Deployment should be repaired only after its symptom and cause are understood.

**Main takeaway:** Secure Kubernetes workloads by granting minimum permissions, enforcing hardened Pod settings, and fixing failures using evidence rather than guesswork.
