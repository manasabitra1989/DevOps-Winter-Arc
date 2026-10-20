# Day 19 — Kubernetes Storage & StatefulSets

## 🎯 Objective

Learn how Kubernetes manages persistent storage and StatefulSets by deploying a PostgreSQL database and verifying that its data survives Pod deletion.

By the end of this lab, I will understand:

- PersistentVolumes (PV) and PersistentVolumeClaims (PVC)
- StorageClasses and dynamic volume provisioning
- Headless Services
- StatefulSets and stable Pod identities
- How to store database credentials using a Kubernetes Secret
- How to verify that database records survive Pod recreation
- How to inspect and troubleshoot persistent storage

---

## 🧰 Prerequisites

- Kubernetes cluster is running.
- `kubectl` is installed and configured.
- A suitable StorageClass is available, or the cluster's storage configuration has been reviewed.
- The working directory is:

```bash
cd ~/DevOps-Winter-Arc/Week3-Kubernetes/day19-storage-statefulsets
```

Check the cluster connection:

```bash
kubectl cluster-info
kubectl get nodes
```

**Why?** Before deploying resources, I verify that `kubectl` can communicate with my Kubernetes cluster.

---

# Task A — Inspect Kubernetes Storage

## Step 1: List StorageClasses

```bash
kubectl get storageclass
```

A StorageClass describes how Kubernetes can provision storage volumes.

Example output might contain a class named `standard`. The actual name depends on the cluster.

## Step 2: Inspect PersistentVolumes

```bash
kubectl get pv
```

A PersistentVolume (PV) represents storage made available to the cluster.

## Step 3: Inspect PersistentVolumeClaims

```bash
kubectl get pvc -A
```

A PersistentVolumeClaim (PVC) is a request for storage made by a workload.

The `-A` flag lists PVCs from all namespaces.

## Step 4: Describe the StorageClass

If the StorageClass is named `standard`:

```bash
kubectl describe storageclass standard
```

If the cluster uses a different name, replace `standard` with the actual name.

### Key concepts

| Resource | Purpose |
|---|---|
| StorageClass | Defines how storage can be provisioned |
| PV | Represents a storage volume |
| PVC | Requests storage for a workload |
| StatefulSet | Manages Pods with stable identities and storage associations |

**Important:** The `storageClassName` in the StatefulSet manifest must match a StorageClass that is appropriate for the cluster. Do not assume every Kubernetes cluster has a class named `standard`.

---

# Task B — Create a Namespace and Secret

## Step 1: Create the namespace

```bash
kubectl create namespace day19-storage
```

Verify:

```bash
kubectl get namespace day19-storage
```

**Why?** A dedicated namespace keeps this lab's resources separate from resources in other namespaces.

## Step 2: Create the PostgreSQL Secret

```bash
kubectl create secret generic pg-secret \
  --from-literal=POSTGRES_PASSWORD='WinterArcLab123!' \
  -n day19-storage
```

Verify that the Secret exists without printing its value:

```bash
kubectl get secret pg-secret -n day19-storage
```

**Why?** The PostgreSQL password is stored in a Kubernetes Secret instead of being written directly into the StatefulSet manifest.

**Security note:** This password is only for the disposable lab. Do not use it for a real database. Kubernetes Secrets are not automatically encrypted just because their values are stored in a Secret object. Base64 encoding is not encryption. Do not commit real credentials to Git.

---

# Task C — Create a Headless Service

Create a file named `pg-headless.yaml`.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: pg-headless
  namespace: day19-storage
spec:
  clusterIP: None
  selector:
    app: pg
  ports:
    - name: postgres
      port: 5432
      targetPort: 5432
```

## Apply the manifest

```bash
kubectl apply -f pg-headless.yaml
```

Verify:

```bash
kubectl get service pg-headless -n day19-storage
kubectl describe service pg-headless -n day19-storage
```

### Why use a Headless Service?

The setting `clusterIP: None` makes this a headless Service. Instead of providing a normal virtual ClusterIP, it supports DNS-based discovery of the matching Pods.

The StatefulSet will reference this Service through its `serviceName` field.

**Important:** The Service selector `app: pg` must match the labels on the PostgreSQL Pod template.

---

# Task D — Deploy PostgreSQL with a StatefulSet

Create a file named `postgres-statefulset.yaml`.

> Before applying this file, confirm the correct StorageClass name from Task A. The example below uses `standard`; replace it if necessary.

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: pg
  namespace: day19-storage
spec:
  serviceName: pg-headless
  replicas: 1
  selector:
    matchLabels:
      app: pg
  template:
    metadata:
      labels:
        app: pg
    spec:
      containers:
        - name: postgres
          image: postgres:16-alpine
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: winterarc
            - name: POSTGRES_USER
              value: appuser
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: pg-secret
                  key: POSTGRES_PASSWORD
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes:
          - ReadWriteOnce
        storageClassName: standard
        resources:
          requests:
            storage: 1Gi
```

## Understand the important fields

- `serviceName`: Associates the StatefulSet with the headless Service.
- `replicas: 1`: Runs one PostgreSQL Pod for this lab.
- `app: pg`: Connects the Pod labels to the StatefulSet selector and Service selector.
- `POSTGRES_DB`: Creates the database named `winterarc` when PostgreSQL initializes a new data directory.
- `POSTGRES_USER`: Sets the database user to `appuser`.
- `secretKeyRef`: Reads the database password from the `pg-secret` Secret.
- `volumeMounts`: Mounts persistent storage at PostgreSQL's data directory.
- `volumeClaimTemplates`: Tells the StatefulSet to create a PVC for its Pod.
- `storage: 1Gi`: Requests 1 GiB of storage.
- `ReadWriteOnce`: Requests a volume that can be mounted read-write by one node at a time, depending on the storage driver. It does not necessarily mean only one Pod can use the volume.

## Apply the StatefulSet

```bash
kubectl apply -f postgres-statefulset.yaml
```

Check the resources:

```bash
kubectl get statefulset -n day19-storage
kubectl get pods -n day19-storage
kubectl get pvc -n day19-storage
```

You can watch each resource separately:

```bash
kubectl get statefulset -n day19-storage -w
```

In another terminal:

```bash
kubectl get pods -n day19-storage -w
```

And, if needed, in another terminal:

```bash
kubectl get pvc -n day19-storage -w
```

Press `Ctrl+C` to stop watching.

**Note:** Some `kubectl` versions do not support combining several resource types with `-w`. Running separate watch commands avoids that issue.

## Expected state

Before continuing, verify:

- StatefulSet `pg` has one desired replica and eventually one ready replica.
- Pod `pg-0` reaches `Running` and `Ready`.
- PVC `data-pg-0` reaches `Bound`.

The exact PV name and storage details depend on the cluster.

**Do not continue to the database test while the PVC is Pending or the Pod is not Ready.** Check the troubleshooting section below first.

---

# Task E — Create Data and Prove Persistence

This is the main experiment of the lab.

## Step 1: Connect to PostgreSQL

After `pg-0` is Ready:

```bash
kubectl exec -it -n day19-storage pg-0 -- \
  psql -U appuser -d winterarc
```

This opens the PostgreSQL interactive terminal inside the container.

## Step 2: Create a table and insert a record

Run these SQL statements inside `psql`:

```sql
CREATE TABLE lab_notes (
    id INT PRIMARY KEY,
    note TEXT
);

INSERT INTO lab_notes
VALUES (1, 'data-survives-pod-delete');

SELECT * FROM lab_notes;
```

Expected query result:

```text
 id |           note
----+---------------------------
  1 | data-survives-pod-delete
```

Exit PostgreSQL:

```sql
\q
```

## Step 3: Confirm the PVC exists

```bash
kubectl get pvc -n day19-storage
```

The claim should remain `Bound`.

## Step 4: Delete the PostgreSQL Pod

```bash
kubectl delete pod pg-0 -n day19-storage
```

**Why delete the Pod?** This simulates losing a Pod. The StatefulSet controller should create a replacement Pod with the same stable name, `pg-0`.

Watch for the replacement:

```bash
kubectl get pods -n day19-storage -w
```

Wait until `pg-0` is Ready, then press `Ctrl+C`.

Check the PVC again:

```bash
kubectl get pvc -n day19-storage
```

The claim `data-pg-0` should still be present and Bound.

## Step 5: Verify the original record survived

Run:

```bash
kubectl exec -n day19-storage pg-0 -- \
  psql -U appuser -d winterarc -c \
  "SELECT * FROM lab_notes;"
```

Expected result:

```text
 id |           note
----+---------------------------
  1 | data-survives-pod-delete
```

### What did this prove?

The Pod was deleted and recreated, but the database record remained because PostgreSQL's data directory was stored on the persistent volume associated with its PVC.

This is the central lesson:

**Deleting a Pod is not the same as deleting its persistent data.**

A StatefulSet provides stable Pod identity and works with persistent volume claims. The storage backend and its lifecycle determine what happens to the underlying data when other resources are deleted.

---

# Task F — Inspect the Storage Resources

Run:

```bash
kubectl get statefulset,pods,pvc -n day19-storage
```

Inspect the PVC:

```bash
kubectl describe pvc data-pg-0 -n day19-storage
```

List PVs:

```bash
kubectl get pv
```

Inspect recent namespace events:

```bash
kubectl get events -n day19-storage --sort-by=.lastTimestamp
```

### Understand the storage relationship

The storage chain looks like this:

```text
StatefulSet: pg
      |
      v
Pod: pg-0
      |
      v
PVC: data-pg-0
      |
      v
PV: provisioned volume
      |
      v
Storage backend
```

The StatefulSet creates a PVC from `volumeClaimTemplates`. Kubernetes then binds that claim to a suitable PV, which represents the storage provided by the cluster.

The actual provisioning mechanism and backing storage location vary by environment.

---

# Troubleshooting

## 1. PVC remains Pending

Check:

```bash
kubectl get storageclass
kubectl describe pvc data-pg-0 -n day19-storage
kubectl get events -n day19-storage --sort-by=.lastTimestamp
```

Possible causes:

- The manifest specifies a StorageClass that does not exist.
- The StorageClass has no functioning provisioner.
- The storage backend cannot satisfy the requested volume.
- Storage provisioning or binding has failed.

**Next step:** Read the PVC events first. Fix the specific reported problem instead of changing the storage configuration blindly.

## 2. Pod is Pending or not Ready

Check:

```bash
kubectl describe pod pg-0 -n day19-storage
kubectl get events -n day19-storage --sort-by=.lastTimestamp
kubectl get pvc -n day19-storage
```

These commands help distinguish scheduling issues, image-pull failures, volume-mount problems, and container startup errors.

If the container has started but PostgreSQL is failing, inspect its logs:

```bash
kubectl logs -n day19-storage pg-0
```

## 3. Database connection fails

Confirm the Pod is Ready:

```bash
kubectl get pod pg-0 -n day19-storage
```

Check the container logs:

```bash
kubectl logs -n day19-storage pg-0
```

Ensure the database name and username match the manifest:

- Database: `winterarc`
- User: `appuser`

## 4. Record does not survive Pod deletion

Check that the PVC still exists:

```bash
kubectl get pvc -n day19-storage
```

Check the volume mount and StatefulSet configuration:

```bash
kubectl describe pod pg-0 -n day19-storage
kubectl describe pvc data-pg-0 -n day19-storage
```

Possible causes include the database writing to a different directory, an incorrect volume mount, or an incorrectly configured storage claim.

Do not delete the PVC while troubleshooting: it may contain the only copy of the lab data.

---

# Interview Questions and Answers

## 1. What is the difference between a PV and a PVC?

A PV represents storage made available to the cluster. A PVC is a request for storage from a workload. Kubernetes binds a suitable PV to a PVC.

## 2. Why is a container's writable layer not enough for database storage?

The writable layer belongs to the container and is not intended to provide durable database storage across container replacement. Persistent volumes provide storage independent of an individual container's writable layer.

## 3. What is a StorageClass?

A StorageClass describes a type of storage and how it can be provisioned. It allows workloads to request storage without manually creating every PV in advance when dynamic provisioning is supported.

## 4. What does `volumeClaimTemplates` do?

It lets a StatefulSet create a PVC for each Pod identity that requires storage.

## 5. Why did the record survive Pod deletion?

The database stored its data in a persistent volume mounted through the Pod's PVC. The StatefulSet recreated `pg-0`, and the replacement Pod reused its associated claim.

## 6. How is a StatefulSet different from a Deployment?

A Deployment is commonly used for interchangeable, stateless replicas. A StatefulSet is designed for workloads that benefit from stable Pod identities and persistent storage associations.

## 7. What is a headless Service?

A Service configured with `clusterIP: None`. It supports DNS-based discovery of matching Pods rather than providing a normal virtual ClusterIP.

## 8. What can cause a PVC to remain Pending?

Examples include a missing StorageClass, a broken or unavailable provisioner, storage capacity or topology constraints, and other provisioning or binding failures.

## 9. Does deleting a PVC always delete the underlying storage?

Not necessarily. The fate of the PV and backing storage depends on the PV's reclaim policy, provisioner, and storage system. Always inspect those settings before deleting a claim.

## 10. Does persistent storage replace backups?

No. Persistent storage helps data survive certain Pod or container failures. It does not protect against every failure, accidental deletion, corruption, or loss of the storage backend. Backups are still necessary for important data.

## 11. Does `ReadWriteOnce` mean only one Pod can mount a volume?

Not exactly. It generally means the volume can be mounted read-write by one node at a time. The exact behavior and additional restrictions depend on the storage implementation.

---

# Evidence and Submission

Before cleaning up, save screenshots or terminal output showing:

- [ ] StorageClasses and existing storage resources
- [ ] `pg-headless` Service
- [ ] StatefulSet `pg` and Ready Pod `pg-0`
- [ ] PVC `data-pg-0` in `Bound` state
- [ ] The record returned before Pod deletion
- [ ] The record returned after Pod deletion and Pod recreation
- [ ] The final StatefulSet, Pod, PVC, and PV inspection

Suggested folder structure:

```text
day19-storage-statefulsets/
├── README.md
├── pg-headless.yaml
├── postgres-statefulset.yaml
└── evidence/
    ├── storage-inspection.png
    ├── postgres-running.png
    ├── record-before-delete.png
    └── record-after-recreation.png
```

Create the evidence directory if needed:

```bash
mkdir -p evidence
```

Keep screenshots free of real credentials and sensitive information.

---

# Cleanup

**Only run the following cleanup after saving your evidence and confirming that the namespace contains only disposable lab resources.**

Inspect the namespace:

```bash
kubectl get all -n day19-storage
kubectl get pvc -n day19-storage
kubectl get pv
```

Delete the lab namespace:

```bash
kubectl delete namespace day19-storage
```

Check the PVs afterward:

```bash
kubectl get pv
```

**Important:** Namespace deletion removes namespaced resources, including the StatefulSet, Service, Secret, and PVC. The fate of the underlying storage depends on the PV reclaim policy and provisioner. Inspect those settings before assuming the data has been deleted or retained.

---

# Final Learning Summary

In Day 19, I learned how Kubernetes storage supports stateful applications.

- A StorageClass defines how storage can be provisioned.
- A PV represents storage available to the cluster.
- A PVC requests storage for a workload.
- A headless Service supports Pod discovery through DNS.
- A StatefulSet provides stable Pod identities and persistent storage associations.
- A Secret can supply database credentials to a container.
- Deleting a Pod does not necessarily delete its persistent data.
- Persistent storage is not a substitute for backups.

**Main takeaway:** Kubernetes can recreate a database Pod while preserving its data through persistent storage, provided the storage and claim lifecycle are configured correctly.
