# 03 — CLI Surface and User-Data Templates

---

## `sp linux` CLI surface

All commands live in `scripts/linux.py`.  The script is mounted onto the
top-level `sp` app in `scripts/provision_ec2.py` (same pattern as
`scripts/elastic.py`).

```
sp linux create [NAME]   [--region R] [--instance-type T] [--max-hours N]
                         [--port N]... [--wait] [--ami AMI-ID]
sp linux list   [REGION]
sp linux info   [NAME]
sp linux delete [NAME]   [-y]
sp linux wait   [NAME]   [--timeout N]
sp linux health [NAME]
sp linux connect [NAME]
sp linux exec   [NAME]  -- COMMAND
```

### `create`

```python
@linux_app.command('create')
def cmd_linux_create(
    name          : Optional[str] = typer.Argument(None),
    region        : Optional[str] = typer.Option(None, '--region'),
    instance_type : str           = typer.Option('t3.medium', '--instance-type'),
    max_hours     : int           = typer.Option(4, '--max-hours'),
    port          : List[int]     = typer.Option([], '--port'),    # repeatable
    wait          : bool          = typer.Option(False, '--wait'),
    ami           : Optional[str] = typer.Option(None, '--ami'),
):
    """Launch a bare Amazon Linux 2023 instance, accessible via SSM."""
```

Renders: stack_name, instance_id, region, public_ip, launch command for
`sp linux connect`.  If `--wait`, polls SSM DescribeInstanceInformation until
the instance appears (typically < 90 s from pending).

### `list`

Renders a Rich table: stack-name | state | instance-type | uptime | public-ip.
Empty state when no stacks found.

### `info`

Renders all `Schema__Linux__Info` fields.

### `delete`

```python
@linux_app.command('delete')
def cmd_linux_delete(
    name    : Optional[str] = typer.Argument(None),
    region  : Optional[str] = typer.Option(None, '--region'),
    all     : bool          = typer.Option(False, '--all'),
    yes     : bool          = typer.Option(False, '-y'),
):
```

Prompts for confirmation unless `-y`.  `--all` terminates every linux stack
in the region (same pattern as `sp el delete --all`).

### `wait`

Polls instance state + SSM availability.  No HTTP probe (unlike Elastic).

```
Checking linux-quiet-fermi  [attempt 1]  state: pending  ssm: not-yet
Checking linux-quiet-fermi  [attempt 4]  state: running  ssm: not-yet
Checking linux-quiet-fermi  [attempt 7]  state: running  ssm: ok
✓  Ready in 47 s
```

### `health`

4 checks (returns `Schema__Linux__Health__Response`):

| # | Check | Detail |
|---|-------|--------|
| 1 | `ec2-state` | Instance in `running` state |
| 2 | `public-ip` | Public IP assigned |
| 3 | `sg-ingress` | Caller IP still in SG ingress (warns if rotated) |
| 4 | `ssm-ping` | Instance appears in SSM DescribeInstanceInformation |

### `connect`

```python
@linux_app.command('connect')
def cmd_linux_connect(name: Optional[str] = typer.Argument(None)):
    """Open an interactive SSM shell session."""
    # Uses os.execvp to replace process with: aws ssm start-session --target {instance_id}
```

### `exec`

```python
@linux_app.command('exec')
def cmd_linux_exec(
    name    : Optional[str] = typer.Argument(None),
    command : List[str]     = typer.Argument(...),   # after '--'
):
    """Run a one-shot command via SSM and print stdout/stderr/exit-code."""
```

---

## `sp docker` CLI surface

All `sp linux` commands plus:

```
sp docker compose-ps   [NAME]
sp docker compose-logs [NAME]  [--tail N]
```

### `create` — extra flags

```python
    image          : Optional[str] = typer.Option(None, '--image'),   # docker image to pull+run
    container_port : int           = typer.Option(0, '--container-port'),
```

If `--image nginx:alpine --container-port 80` is given:
- SG ingress opens `:80/tcp` from caller IP
- User-data runs `docker run -d -p 80:80 nginx:alpine`

### `compose-ps`

Runs `docker compose ps --format table` via SSM on the instance.  Prints raw output.

### `compose-logs`

Runs `docker compose logs --tail {N}` via SSM.  Default tail = 50.

---

## `Linux__User_Data__Builder` — cloud-init template

`render(stack_name, max_hours)` → bash script string.

```bash
#!/bin/bash
set -e

STACK_NAME='{stack_name}'
BOOT_STATUS_FILE='/var/log/sg-linux-boot-status'

echo "PENDING $(date -u +%Y-%m-%dT%H:%M:%SZ)" > $BOOT_STATUS_FILE

# ── auto-terminate timer ────────────────────────────────────────────────
{auto_terminate_block}

echo "OK $(date -u +%Y-%m-%dT%H:%M:%SZ)" > $BOOT_STATUS_FILE
```

Where `{auto_terminate_block}` is:

```bash
# max_hours > 0:
systemd-run --on-active={max_hours}h /sbin/shutdown -h now
# max_hours == 0:
# (no timer — instance runs until explicitly deleted)
```

Boot status file `/var/log/sg-linux-boot-status` is the SSM probe target
for the `wait` command.

---

## `Docker__User_Data__Builder` — cloud-init template

`render(stack_name, max_hours, image='', container_port=0)` → bash script string.

```bash
#!/bin/bash
set -e

STACK_NAME='{stack_name}'
BOOT_STATUS_FILE='/var/log/sg-docker-boot-status'

echo "PENDING $(date -u +%Y-%m-%dT%H:%M:%SZ)" > $BOOT_STATUS_FILE

# ── Docker install (Amazon Linux 2023) ─────────────────────────────────
dnf install -y docker
systemctl enable --now docker
usermod -aG docker ec2-user

# ── Docker compose plugin ───────────────────────────────────────────────
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" \
     -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

{optional_image_block}

# ── auto-terminate timer ────────────────────────────────────────────────
{auto_terminate_block}

echo "OK $(date -u +%Y-%m-%dT%H:%M:%SZ)" > $BOOT_STATUS_FILE
```

Where `{optional_image_block}` when `--image` is provided:

```bash
# Simple single-image run (no compose file needed):
docker pull {image}
docker run -d {port_flag} --restart unless-stopped --name sg-container {image}
```

When a compose spec is provided (`compose_spec` field), the builder writes
the YAML to `/opt/sg-docker/docker-compose.yml` and runs
`docker compose -f /opt/sg-docker/docker-compose.yml up -d`.

---

## Health check implementation notes

### `Linux__Health__Checker`

```python
class Linux__Health__Checker(Type_Safe):
    aws_client : Linux__AWS__Client

    def run(self, stack_name, region) -> Schema__Linux__Health__Response:
        info = self.aws_client.find_by_stack_name(region, stack_name)
        checks = [
            self._check_ec2_state(info),
            self._check_public_ip(info),
            self._check_sg_ingress(region, info),
            self._check_ssm_ping(region, info),
        ]
        return Schema__Linux__Health__Response(
            stack_name = stack_name,
            all_ok     = all(c.status == Enum__Health__Status.OK for c in checks
                             if c.status != Enum__Health__Status.SKIP),
            checks     = checks
        )
```

### `Docker__Health__Checker` — adds two more checks

```python
        checks = [
            self._check_ec2_state(info),
            self._check_public_ip(info),
            self._check_sg_ingress(region, info),
            self._check_ssm_ping(region, info),
            self._check_docker_daemon(region, info),   # SSM: 'docker info' exit code
            self._check_containers_running(region, info),  # SSM: 'docker ps -q | wc -l'
        ]
```

---

## `wait` probe logic

`sp linux wait` polls two things:

1. EC2 instance state == `running` (via `describe_instances`)
2. SSM agent registration (via `ssm.describe_instance_information(Filters=[{Name:'InstanceIds', Values:[id]}])`)

Step 2 typically lags 20-40 s behind step 1 on a fresh instance.  The wait
loop exits on both conditions being true.  Default timeout: 300 s.

`sp docker wait` adds a third check:
3. Boot status file == `OK` (via SSM `cat /var/log/sg-docker-boot-status`), confirming
   Docker install completed.  This takes ~60-90 s on a cold instance.
