# Host Control Plane — New Features (v0.2.1)

**Date:** 2026-05-05  
**Branch:** `claude/fix-t2-4-production-U2yIZ`  
**Commits:** `d9c20a9` (enable-shell), `f9361cc` (images), `b32f5a2` (route restructure + S3)

---

## 1. `--enable-shell` — Opt-in unrestricted shell on the sidecar

### Problem

`POST /host/shell/execute` is allowlist-gated by `Safe_Str__Shell__Command`. Only a small set
of read-only commands are permitted (`docker ps`, `docker logs`, `df -h`, `free -m`, etc.).
Commands like `docker images`, `docker exec`, and `docker rmi` are rejected with:

```
"command not in allowlist: 'docker images'"
```

### Solution

A new `--enable-shell` flag at **node creation time** disables the allowlist for that node by
injecting `-e SG_SHELL_UNRESTRICTED=1` into the sidecar's `docker run` command.
`Safe_Str__Shell__Command` skips the allowlist check when this env var is set.

The default remains **deny-all** — existing nodes are unaffected.

### Usage

```bash
# Docker spec
sg-compute spec docker create --registry $ECR --enable-shell

# Firefox spec
sg-compute spec firefox create --enable-shell

# Via API (Schema__Docker__Create__Request)
POST /api/nodes
{
  "spec_id": "docker",
  "registry": "...",
  "enable_shell": true
}
```

On a node launched with `--enable-shell`:

```bash
curl -d '{"command": "docker images"}' -H "X-API-Key: $KEY" $API/host/shell/execute
curl -d '{"command": "docker exec my-container ls /app"}' -H "X-API-Key: $KEY" $API/host/shell/execute
```

### Files changed

| File | Change |
|------|--------|
| `sg_compute/host_plane/shell/primitives/Safe_Str__Shell__Command.py` | Skip allowlist when `SG_SHELL_UNRESTRICTED=1` |
| `sg_compute/platforms/ec2/user_data/Section__Sidecar.py` | `enable_shell: bool = False` param; injects env var into `docker run` |
| `sg_compute_specs/docker/service/Docker__User_Data__Builder.py` | Thread `enable_shell` to `Section__Sidecar` |
| `sg_compute_specs/docker/schemas/Schema__Docker__Create__Request.py` | `enable_shell: bool = False` field |
| `sg_compute_specs/docker/service/Docker__Service.py` | Pass `enable_shell` to builder |
| `sg_compute_specs/docker/cli/Cli__Docker.py` | `--enable-shell` flag on `create` |
| `sg_compute_specs/firefox/service/Firefox__User_Data__Builder.py` | Thread `enable_shell` |
| `sg_compute_specs/firefox/schemas/Schema__Firefox__Stack__Create__Request.py` | `enable_shell: bool = False` field |
| `sg_compute_specs/firefox/service/Firefox__Service.py` | Pass `enable_shell` to builder |
| `sg_compute_specs/firefox/cli/Cli__Firefox.py` | `--enable-shell` flag on `create` |

---

## 2. `/images` — Docker image management endpoints

### Problem

Managing Docker images on a running node previously required either:
- `--enable-shell` + raw `docker images` / `docker load` / `docker rmi` via `/host/shell/execute`
- SSH or SSM Session Manager

Neither gives structured output or allows direct file upload from the client.

### Solution

A new `/images` resource group on the host control plane (`Routes__Host__Images`) exposes
six first-class endpoints backed by `Image__Runtime__Docker` (subprocess to `docker` binary,
no docker-py SDK — same pattern as `Pod__Runtime__Docker`).

### Endpoints

All endpoints require `X-API-Key` authentication.

---

#### `GET /images`

List all locally available Docker images.

**Response — `Schema__Image__List`**

```json
{
  "images": [
    {
      "id":         "a1b2c3d4e5f6",
      "tags":       ["my-app:latest", "my-app:v1.0.0"],
      "size_mb":    142.3,
      "created_at": "2026-05-05T10:00:00Z"
    }
  ],
  "count": 1
}
```

---

#### `GET /images/{name}`

Inspect a specific image by name or tag. Returns `404` if not found.

```bash
curl -H "X-API-Key: $KEY" $API/images/my-app:latest
```

**Response — `Schema__Image__Info`** (same shape as item in list above)

---

#### `POST /images/load/from/local-path`

Load a Docker image from a tar file that already exists on the host filesystem.

**Request body**

```json
{ "path": "/home/ssm-user/app/my-app.tar" }
```

**Response — `Schema__Image__Load__Response`**

```json
{ "loaded": true, "output": "Loaded image: my-app:latest", "error": "" }
```

Returns `422` if `path` is empty; `404` if the file does not exist on the host.

---

#### `POST /images/load/from/s3`

Download a tar from S3 and load it into Docker. Uses the node's IAM role — no
credentials in the request. The S3 bucket must be accessible from the instance role.

**Request body**

```json
{ "bucket": "my-artefacts", "key": "images/my-app.tar" }
```

**Response — `Schema__Image__Load__Response`**

```json
{ "loaded": true, "output": "Loaded image: my-app:latest", "error": "" }
```

Returns `422` if `bucket` or `key` is empty. Returns `loaded: false` + `error` if the
`aws s3 cp` download fails (wrong bucket, key, or missing IAM permissions).

---

#### `POST /images/load/from/upload`

Upload a Docker image tar directly via HTTP multipart — **no S3 or sgit relay needed**.
This is the primary workflow for pushing a locally built image to an EC2 node.

```bash
curl -F "file=@my-app.tar" \
     -H "X-API-Key: $KEY" \
     $API/images/load/from/upload
```

**Response — `Schema__Image__Upload__Response`**

```json
{
  "loaded":     true,
  "output":     "Loaded image: my-app:latest",
  "error":      "",
  "size_bytes": 52428800
}
```

Hard cap: 20 GiB (returns `413` if exceeded). The tar is written to a tmpfile, passed to
`docker load`, and deleted immediately after — no disk residue.

---

#### `DELETE /images/delete/{name}`

Remove an image by name or tag (`docker rmi`). Returns `404` if the image is not found.

```bash
curl -X DELETE -H "X-API-Key: $KEY" $API/images/delete/my-app:latest
```

**Response — `Schema__Image__Remove__Response`**

```json
{ "name": "my-app:latest", "removed": true, "error": "" }
```

---

### Files added

| File | Description |
|------|-------------|
| `sg_compute/host_plane/images/schemas/Schema__Image__Info.py` | Per-image record |
| `sg_compute/host_plane/images/schemas/Schema__Image__List.py` | List + `List__Schema__Image__Info` collection |
| `sg_compute/host_plane/images/schemas/Schema__Image__Load__Response.py` | load / S3 result |
| `sg_compute/host_plane/images/schemas/Schema__Image__Upload__Response.py` | upload result (adds `size_bytes`) |
| `sg_compute/host_plane/images/schemas/Schema__Image__Remove__Response.py` | rmi result |
| `sg_compute/host_plane/images/service/Image__Runtime__Docker.py` | Docker CLI adapter |
| `sg_compute/host_plane/fast_api/routes/Routes__Host__Images.py` | Route definitions |

### Files modified

| File | Change |
|------|--------|
| `sg_compute/host_plane/fast_api/Fast_API__Host__Control.py` | Mount `Routes__Host__Images` |

---

## 3. Recommended deploy workflow (updated)

The original workflow used sgit as a relay for transferring the image tar to EC2.
With the new `/images/load/from/upload` endpoint the relay is eliminated:

```
Old:
  1. docker buildx build --platform linux/amd64 -t my-app:latest .
  2. docker save -o my-app.tar my-app:latest
  3. sgit share send --file ./my-app.tar          ← relay step 1
  4. (on EC2 via SSM) sgit share receive "token"  ← relay step 2
  5. POST /host/shell/execute  docker load -i ...  ← requires --enable-shell
  6. POST /pods  {name, image, ports}

New:
  1. docker buildx build --platform linux/amd64 -t my-app:latest .
  2. docker save -o my-app.tar my-app:latest
  3. curl -F "file=@my-app.tar" $API/images/load/from/upload
  4. POST /pods  {name, image, ports}
```

Or, if the image is already in S3:

```
  1. docker buildx build --platform linux/amd64 -t my-app:latest .
  2. docker save -o my-app.tar my-app:latest
  3. aws s3 cp my-app.tar s3://my-bucket/images/my-app.tar
  4. POST /images/load/from/s3  {"bucket": "my-bucket", "key": "images/my-app.tar"}
  5. POST /pods  {name, image, ports}
```

---

## 4. Schema reference

### `Schema__Image__Info`

```
id         : str    — 12-char image digest
tags       : list   — ["repo:tag", ...]
size_mb    : float  — compressed size in MiB
created_at : str    — ISO-8601
```

### `Schema__Image__List`

```
images : List[Schema__Image__Info]
count  : int
```

### `Schema__Image__Load__Response`

```
loaded : bool
output : str
error  : str
```

### `Schema__Image__Upload__Response`

```
loaded     : bool
output     : str
error      : str
size_bytes : int   — bytes received before docker load
```

### `Schema__Image__Remove__Response`

```
name    : str
removed : bool
error   : str
```
