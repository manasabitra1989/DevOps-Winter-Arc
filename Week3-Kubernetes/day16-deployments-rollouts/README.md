# Day 16 - Kubernetes Deployments & Rollouts

## Objective

The objective of Day 16 is to understand how Kubernetes Deployments manage application releases, perform rolling updates, maintain revision history, detect failed updates, and roll back to a previously working version.

This lab builds on Day 15, where Nginx was deployed using a Kubernetes Deployment and exposed through a Service.

### Tasks covered

- Inspect an existing Kubernetes Deployment.
- Understand Deployment replicas and ReplicaSets.
- Perform a rolling update by changing the Nginx image.
- Monitor the rollout and inspect revision history.
- Configure and understand rolling-update settings.
- Introduce an invalid image tag to simulate a failed rollout.
- Diagnose the failure using Pods, events, and resource descriptions.
- Roll back to the last known-good Deployment revision.
- Verify recovery and collect evidence.
- Clean up the lab resources.

### Technologies used

| Technology | Purpose |
|---|---|
| Kubernetes | Orchestrates containerized workloads |
| Docker Desktop / kind | Provides a local Kubernetes cluster |
| kubectl | Manages and inspects Kubernetes resources |
| Deployment | Manages replicated Pods and application updates |
| ReplicaSet | Maintains the desired number of matching Pods |
| Nginx | Application used to practise release management |
| YAML | Defines Kubernetes resources declaratively |
| Git and GitHub | Version control and submission |

## Architecture and key concepts

### 1. What is a Kubernetes Deployment?

A Deployment is a Kubernetes resource that manages replicated Pods and supports controlled application updates.

Instead of manually deleting old Pods and creating new ones, you update the Deployment's desired configuration. Kubernetes controllers work to bring the running workload toward that desired state.

For example, changing the container image from `nginx:1.27` to `nginx:1.28` updates the Deployment's Pod template and normally creates a new ReplicaSet.

### 2. Deployment, ReplicaSet, and Pod

```text
Kubernetes Cluster
       |
       v
Deployment: nginx-deployment
       |
       +---- ReplicaSet for old version
       |          |
       |          +---- Old Nginx Pods
       |
       +---- ReplicaSet for new version
                  |
                  +---- New Nginx Pods
```

**Deployment:** Manages application releases, desired replicas, and rollout history.

**ReplicaSet:** Maintains the requested number of matching Pods. A Deployment normally creates a new ReplicaSet when its Pod template changes.

**Pod:** Runs the application container. A Pod may be replaced during updates or recovery.

A Deployment can retain older ReplicaSets to support rollback, subject to its revision-history settings and pruning.

### 3. What is a rolling update?

A rolling update gradually replaces Pods running the old version with Pods running the new version.

For example, if the Deployment requests three replicas:

```text
Before update:
nginx:1.27  nginx:1.27  nginx:1.27

During update:
nginx:1.27  nginx:1.28  nginx:1.28  (progress depends on strategy)

After successful update:
nginx:1.28  nginx:1.28  nginx:1.28
```

The exact sequence depends on the rollout strategy, readiness, scheduling, and available resources.

Rolling updates reduce the need for an all-at-once replacement, but they do not guarantee zero downtime for every application or configuration.

### 4. `maxSurge` and `maxUnavailable`

These settings control how a Deployment replaces Pods during a rolling update.

- **`maxSurge`** specifies how many additional Pods may be created above the desired replica count during an update.
- **`maxUnavailable`** specifies how many desired Pods may be unavailable during the update.

Example:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

With three desired replicas, this strategy permits one additional Pod and aims to keep all three desired replicas available during the update.

Actual availability still depends on readiness, scheduling, capacity, and application behaviour.

### 5. What is rollout history?

Kubernetes records Deployment revisions when relevant Pod-template changes occur.

Rollout history lets you inspect past revisions and helps identify a previous configuration to restore.

Useful commands:

```bash
kubectl rollout history deployment/nginx-deployment
kubectl rollout history deployment/nginx-deployment --revision=2
```

The revision number is an example. Use a revision number that actually exists in your cluster.

### 6. What is a failed rollout?

A rollout may fail to complete if the new Pods cannot become ready.

Common causes include:

- An invalid container image name or tag.
- An image registry that cannot be reached.
- Failed application startup.
- Incorrect configuration.
- Failed readiness checks.
- Insufficient cluster resources.

In this lab, an invalid Nginx image tag is used to practise diagnosis and recovery.

### 7. What is rollback?

Rollback restores an earlier Deployment revision.

```bash
kubectl rollout undo deployment/nginx-deployment
```

This changes the Deployment back to a previous Pod-template configuration. Kubernetes then works to reconcile the workload.

Rollback does not reverse every possible external side effect, such as database migrations or data changes. Those require a separate recovery plan.

## Cluster setup

### 1. Prerequisites

- A running local Kubernetes cluster.
- `kubectl` installed and configured.
- The Day 15 Nginx Deployment, or a separate Deployment created for this lab.
- Internet access if the Nginx image must be pulled.

The commands in this README assume:

- Deployment name: `nginx-deployment`
- Container name: `nginx`
- Initial image: `nginx:1.27`
- Update image: `nginx:1.28`
- Intentionally invalid image: `nginx:1.99-broken`

Use the actual names and image values shown by your cluster if they differ.

### 2. Verify the cluster

```bash
kubectl config current-context
kubectl get nodes
kubectl get deployments
kubectl get pods
kubectl get rs
```

**Explanation**

- `kubectl config current-context` identifies the selected cluster context.
- `kubectl get nodes` checks node status.
- `kubectl get deployments` lists Deployments.
- `kubectl get pods` lists running and pending Pods.
- `kubectl get rs` lists ReplicaSets associated with Deployments.

If `nginx-deployment` does not exist, inspect your resources before continuing. Do not change an unrelated Deployment.

### 3. Inspect the current Deployment

```bash
kubectl describe deployment nginx-deployment
kubectl get deployment nginx-deployment -o yaml
```

Check the image, replica count, strategy, selector, Pod template, and Deployment conditions.

Record the currently working image before changing it.

### 4. Record the starting image

```bash
kubectl get deployment nginx-deployment \
  -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
```

This command reads the container image configured in the Deployment's Pod template.

Record the output in your notes so you can confirm the image after rollback.

## Deploy and scale Nginx

### 1. Add a release description

```bash
kubectl annotate deployment/nginx-deployment \
  kubernetes.io/change-cause="Day 16: update Nginx for rollout practice" \
  --overwrite
```

This adds a human-readable change description to the Deployment. It is useful for recording why the release was made.

The annotation alone does not create a new Pod-template revision.

### 2. Perform the rolling update

```bash
kubectl set image deployment/nginx-deployment \
  nginx=nginx:1.28
```

This changes the image for the `nginx` container in the Deployment's Pod template.

Monitor the update:

```bash
kubectl rollout status deployment/nginx-deployment
```

Inspect the resulting resources:

```bash
kubectl get deployment nginx-deployment
kubectl get rs
kubectl get pods -o wide
kubectl rollout history deployment/nginx-deployment
```

**Expected result**

- The Deployment requests the configured number of replicas.
- The new Pods use `nginx:1.28`.
- The new Pods become ready.
- A new ReplicaSet is normally created for the changed Pod template.
- Rollout history shows the available Deployment revisions.

If the rollout does not complete, inspect the Deployment, Pods, and events before continuing.

### 3. Inspect the revision history

```bash
kubectl rollout history deployment/nginx-deployment
```

For a particular revision:

```bash
kubectl rollout history deployment/nginx-deployment --revision=2
```

Replace `2` with an actual revision number listed by your cluster.

Revision numbers can differ between environments. Do not assume that a specific revision number always represents a particular image.

### 4. Configure a rolling-update strategy

To explicitly configure the rolling-update strategy, edit the Deployment:

```bash
kubectl edit deployment nginx-deployment
```

Under `spec`, ensure the strategy is configured as follows:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

Save and exit the editor.

Alternatively, place the strategy under `spec` in a YAML manifest and apply it.

Inspect the configuration:

```bash
kubectl get deployment nginx-deployment -o yaml
kubectl describe deployment nginx-deployment
```

**Important:** If you edit the Deployment, only change the intended fields and preserve the existing selector and Pod-template configuration.

### 5. Prepare for the failure test

Before introducing the invalid image, record the working image and history:

```bash
kubectl get deployment nginx-deployment \
  -o jsonpath='{.spec.template.spec.containers[0].image}'; echo

kubectl rollout history deployment/nginx-deployment
kubectl get pods
```

Make sure you have captured evidence of the successful update. This is your known-good state.

### 6. Introduce an invalid image tag

This is an intentional failure for the lab.

```bash
kubectl set image deployment/nginx-deployment \
  nginx=nginx:1.99-broken
```

Inspect the rollout:

```bash
kubectl rollout status deployment/nginx-deployment --timeout=60s
kubectl get pods
kubectl get rs
```

The status command may time out because the new Pods cannot become ready. That is expected during this failure exercise.

The invalid tag should produce an image-pull failure when Kubernetes tries to retrieve it.

Existing healthy Pods may remain available while the failed rollout is pending.

### 7. Diagnose the failed rollout

List the Pods:

```bash
kubectl get pods
```

Find a Pod belonging to the failed ReplicaSet, then inspect it:

```bash
kubectl describe pod POD_NAME
```

Replace `POD_NAME` with the actual failing Pod name.

Inspect recent events:

```bash
kubectl get events --sort-by=.metadata.creationTimestamp
```

Inspect the Deployment and ReplicaSets:

```bash
kubectl describe deployment nginx-deployment
kubectl get rs,pods -o wide
kubectl rollout history deployment/nginx-deployment
```

Look for messages such as:

- `ErrImagePull`
- `ImagePullBackOff`
- Image not found
- Failed image pull

These messages help distinguish an image-pull problem from a container startup problem.

Capture the failing Pod and its Events for your evidence folder.

### 8. Roll back the Deployment

Return to the last known-good revision:

```bash
kubectl rollout undo deployment/nginx-deployment
```

Monitor recovery:

```bash
kubectl rollout status deployment/nginx-deployment --timeout=120s
```

Inspect the final state:

```bash
kubectl get deployment nginx-deployment -o wide
kubectl get rs
kubectl get pods
kubectl rollout history deployment/nginx-deployment
```

Confirm the restored image:

```bash
kubectl get deployment nginx-deployment \
  -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
```

The restored image should match the known-good version you recorded before the failure.

### 9. Roll back to a specific revision (optional)

List revisions first:

```bash
kubectl rollout history deployment/nginx-deployment
```

Then restore a specific revision:

```bash
kubectl rollout undo deployment/nginx-deployment \
  --to-revision=REVISION
```

Replace `REVISION` with a valid revision number.

Always verify the resulting image and Pod health after rollback.

### 10. Verify the final state

```bash
kubectl get deployments
kubectl get pods -o wide
kubectl get rs
kubectl rollout status deployment/nginx-deployment
```

The final Deployment should use the known-good image, and the desired replicas should be ready.

If your Day 15 Service is still present, it can continue selecting the Nginx Pods as long as the Pod labels still match its selector.

## Commands and evidence

### 1. Command reference

| Command | Purpose |
|---|---|
| `kubectl get deployments` | Lists Deployments and replica status. |
| `kubectl get pods -o wide` | Lists Pods with additional placement details. |
| `kubectl get rs` | Lists ReplicaSets. |
| `kubectl describe deployment NAME` | Shows Deployment configuration, status, and events. |
| `kubectl set image deployment/NAME CONTAINER=IMAGE` | Updates a container image in a Deployment. |
| `kubectl rollout status deployment/NAME` | Monitors rollout completion. |
| `kubectl rollout history deployment/NAME` | Displays Deployment revision history. |
| `kubectl rollout history deployment/NAME --revision=N` | Displays details for a particular revision. |
| `kubectl rollout undo deployment/NAME` | Rolls back to the previous revision. |
| `kubectl scale deployment NAME --replicas=N` | Changes the desired replica count. |
| `kubectl describe pod POD_NAME` | Shows Pod details and events. |
| `kubectl get events --sort-by=.metadata.creationTimestamp` | Lists recent events in chronological order. |
| `kubectl get deployment NAME -o yaml` | Displays the Deployment's YAML representation. |

### 2. Evidence checklist

Capture actual terminal output or screenshots for these stages:

- [ ] Kubernetes node is `Ready`.
- [ ] Initial Deployment and Pods are healthy.
- [ ] New Nginx image is deployed successfully.
- [ ] Rollout status reports success.
- [ ] Revision history shows the available revisions.
- [ ] Invalid image causes a failed rollout.
- [ ] `kubectl describe pod` or events show the image-pull failure.
- [ ] Rollback is completed.
- [ ] The restored image matches the known-good version.
- [ ] Final Pods are healthy.

### 3. Suggested evidence filenames

```text
evidence/
├── 01-initial-deployment.png
├── 02-successful-rolling-update.png
├── 03-rollout-history.png
├── 04-failed-rollout.png
├── 05-image-pull-events.png
└── 06-rollback-verified.png
```

These filenames are suggestions. Create the screenshots from your actual environment.

### 4. Submission structure

```text
day16-deployments-rollouts/
├── README.md
└── evidence/
    ├── 01-initial-deployment.png
    ├── 02-successful-rolling-update.png
    ├── 03-rollout-history.png
    ├── 04-failed-rollout.png
    ├── 05-image-pull-events.png
    └── 06-rollback-verified.png
```

Include YAML manifests if the assignment requires you to submit the Deployment and Service definitions. If the lab uses an existing Day 15 manifest, consider copying the relevant manifest into the Day 16 folder so the project is reproducible.

Do not commit kubeconfig files, credentials, or other sensitive configuration.

## Troubleshooting / lessons learned

### 1. Deployment does not exist

Check:

```bash
kubectl get deployments
kubectl get all
```

Use the actual resource name. If the Day 15 Deployment was deleted during cleanup, recreate the required Deployment before attempting rollout commands.

### 2. Rollout does not complete

Run:

```bash
kubectl rollout status deployment/nginx-deployment
kubectl describe deployment nginx-deployment
kubectl get pods
kubectl get events --sort-by=.metadata.creationTimestamp
```

Check whether the new Pods are scheduled, whether the image can be pulled, and whether the Pods become ready.

### 3. ImagePullBackOff

Run:

```bash
kubectl get pods
kubectl describe pod POD_NAME
```

Check the image name and tag, registry connectivity, and Pod events.

In this lab, `nginx:1.99-broken` is deliberately invalid. Roll back after collecting the evidence.

### 4. Rollback does not appear to restore the expected version

Inspect the current image:

```bash
kubectl get deployment nginx-deployment \
  -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
```

Inspect the history:

```bash
kubectl rollout history deployment/nginx-deployment
```

Choose a valid known-good revision if necessary. Do not assume revision numbers are identical across different clusters.

### 5. Old ReplicaSets remain after rollback

Kubernetes may retain older ReplicaSets so that earlier revisions can be inspected or restored. Their presence does not necessarily mean cleanup failed.

Check:

```bash
kubectl get rs
kubectl rollout history deployment/nginx-deployment
```

The Deployment's revision-history settings influence how many old ReplicaSets are retained.

### 6. Pods are not immediately ready

Run:

```bash
kubectl get pods -w
```

Wait for the rollout to settle, then inspect Pod details and events if readiness does not improve.

### 7. Lessons learned

- A Deployment manages the desired state of replicated Pods.
- Changing the Pod template normally creates a new Deployment revision.
- Rolling updates replace application versions gradually.
- `maxSurge` and `maxUnavailable` control update behaviour.
- ReplicaSets help manage the old and new Pod sets.
- Invalid images can prevent a rollout from completing.
- Events and resource descriptions help diagnose failures.
- Rollback restores an earlier Pod-template configuration.
- Always verify the restored image and Pod health after rollback.
- A successful rollback does not automatically reverse external side effects such as database changes.

## Cleanup

### 1. Save evidence before cleanup

Ensure all screenshots and notes are saved before deleting the lab resources.

### 2. Remove the Deployment

If you want to remove the Day 16 Nginx workload:

```bash
kubectl delete deployment nginx-deployment
```

Kubernetes normally removes the Deployment's managed Pods and ReplicaSets as part of deleting the Deployment.

If the Day 15 Service remains and is no longer needed:

```bash
kubectl delete service nginx-service
```

Only delete the Service if it belongs to this lab and you no longer need it.

### 3. Verify cleanup

```bash
kubectl get deployments
kubectl get pods
kubectl get rs
kubectl get services
```

The built-in `kubernetes` Service should remain. Do not delete it.

If you want to keep the Day 15 Nginx application for later labs, do not delete its Deployment or Service.

### 4. Keep or delete the cluster

Keep the local Kubernetes cluster running if you plan to use it for Day 17 or later tasks.

If you created a dedicated kind cluster exclusively for this lab and no longer need it, you can delete that cluster:

```bash
kind delete cluster --name winter-arc
```

Do not run this against a cluster you want to keep. Docker Desktop's shared Kubernetes cluster should not be deleted merely to clean up this lab.

## Interview Questions and Answers

### Q1. What is a Kubernetes Deployment?

A Deployment manages replicated Pods and supports controlled application updates and rollbacks.

### Q2. What is a rolling update?

A rolling update gradually replaces old Pods with Pods using the new Pod template.

### Q3. What is a ReplicaSet?

A ReplicaSet maintains the requested number of matching Pods. Deployments normally manage ReplicaSets to implement updates.

### Q4. What happens when you change the image in a Deployment?

The Pod template changes. Kubernetes normally creates a new ReplicaSet and begins a rollout.

### Q5. What does `kubectl rollout status` do?

It monitors whether a Deployment rollout has completed successfully or is still progressing or failing.

### Q6. What does `kubectl rollout history` show?

It lists the recorded revisions of a Deployment and can show details for a specific revision.

### Q7. How do you roll back a Deployment?

Use `kubectl rollout undo deployment/DEPLOYMENT_NAME` to restore the previous revision, or specify a valid revision with `--to-revision`.

### Q8. What is `maxSurge`?

It controls the maximum number of extra Pods allowed above the desired replica count during a rolling update.

### Q9. What is `maxUnavailable`?

It controls how many desired Pods may be unavailable during a rolling update.

### Q10. What does ImagePullBackOff mean?

Kubernetes is unable to retrieve the requested image after retrying. The image name, tag, registry connectivity, and Pod events should be checked.

### Q11. Why might a rollout remain incomplete?

The new Pods may fail to start, fail readiness checks, be unable to pull an image, or remain unscheduled because of resource constraints.

### Q12. How can you investigate a failed rollout?

Use `kubectl get pods`, `kubectl describe pod`, `kubectl describe deployment`, `kubectl get events`, and `kubectl rollout history`.

### Q13. Does rollback delete every old ReplicaSet?

Not necessarily. Kubernetes can retain older ReplicaSets for revision history and future rollbacks.

### Q14. Does rollback reverse a database migration?

No. Deployment rollback restores the Pod-template configuration. External data changes and database migrations require their own recovery strategy.

### Q15. Why record the working image before a failure test?

It gives you a known-good reference to compare against after rollback.

### Q16. Is a rolling update always zero-downtime?

No. Availability depends on readiness, update settings, capacity, application behaviour, and other dependencies.

### Q17. What is the purpose of a Deployment's change-cause annotation?

It records a human-readable explanation of a change, helping people understand the purpose of a release.

### Q18. Why should you verify the image after rollback?

The rollback command may target a different revision than expected. Checking the actual image confirms which version the Deployment is configured to run.

## Final Completion Checklist

- [ ] Kubernetes cluster is running.
- [ ] Existing Deployment and Pod status were inspected.
- [ ] The starting image was recorded.
- [ ] A rolling update was completed successfully.
- [ ] Rollout status and revision history were inspected.
- [ ] `maxSurge` and `maxUnavailable` were understood or configured.
- [ ] An invalid image tag was used to simulate a failed rollout.
- [ ] The failure was diagnosed using Pod details and events.
- [ ] Rollback restored the known-good configuration.
- [ ] Final image and Pod health were verified.
- [ ] Evidence screenshots were saved.
- [ ] README documents the actual commands and results.
- [ ] Lab resources were cleaned up or intentionally retained.

**Final result:** A Kubernetes Deployment was updated, its rollout history inspected, a failed image update diagnosed, and the workload restored to a known-good revision using rollback.
