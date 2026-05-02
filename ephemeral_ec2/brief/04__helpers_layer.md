# Ephemeral EC2 — Helpers Layer Specification

## Design contract

Every helper class:
- Extends `Type_Safe` (osbot-utils)
- Has no `__init__` — all state is declared as class attributes with types
- Has a `setup()` method that wires AWS clients (lazy, called by the parent service)
- Takes only plain primitives (str, int, list[int]) — never stack-specific schema objects
- Returns plain Python types or `Type_Safe` schemas from `helpers/`
- Never calls `event_bus` — that is the stack service's responsibility

---

## helpers/aws/

### EC2__Launch__Helper

Wraps `RunInstances`. Sole responsibility: launch one instance, return its ID.

```
run_instance(
    region            : str,
    ami_id            : str,
    sg_id             : str,
    user_data         : str,          ← raw (pre-gzip) bash script
    tags              : list[dict],
    instance_type     : str = 't3.medium',
    instance_profile  : str = '',
    max_hours         : int = 0,      ← 0 = no InstanceInitiatedShutdownBehavior
    key_name          : str = '',
) -> str                              ← instance ID
```

`max_hours > 0` adds `InstanceInitiatedShutdownBehavior=terminate` to the RunInstances call.
User-data must separately include `Section__Shutdown` to fire the actual timer.

### EC2__SG__Helper

Creates or looks up a per-instance security group. Idempotent: if a group with the given name
already exists in the region it is reused.

```
ensure_security_group(
    region          : str,
    stack_name      : str,
    caller_ip       : str,
    inbound_ports   : list[int],    ← e.g. [443]
    extra_cidrs     : dict[int,str] ← {11434: '10.0.1.5/32'} for internal rules
) -> str                            ← security group ID
```

### EC2__Tags__Builder

Builds the standard EC2 tag list. All instances get the Purpose tag for cost attribution and
the stack-name tag for `find_by_stack_name` lookups.

```
Standard tags always added:
  Name         = <stack_name>
  Purpose      = ephemeral-ec2
  StackName    = <stack_name>
  StackType    = <stack_type>   ← e.g. 'open-design'
  CreatorIP    = <caller_ip>
  CreatedBy    = <creator>      ← optional, defaults to ''
```

### EC2__AMI__Helper

Resolves the latest Amazon Linux 2023 AMI ID for a given region via SSM Parameter Store.
Also supports looking up a stack-specific baked AMI by tag.

```
latest_al2023_ami(region: str) -> str
latest_baked_ami(region: str, stack_type: str) -> str | None
```

### EC2__Instance__Helper

All `DescribeInstances` queries. Filters by the `StackName` tag.

```
find_by_stack_name(region: str, stack_name: str) -> dict | None
list_by_stack_type(region: str, stack_type: str) -> list[dict]
terminate(region: str, instance_id: str) -> bool
wait_for_state(region: str, instance_id: str, state: str, timeout_sec: int) -> bool
```

### EC2__Stack__Mapper

Converts a raw boto3 `DescribeInstances` dict into a standard `Schema__Stack__Info`.

```
to_info(raw: dict, region: str) -> Schema__Stack__Info
```

`Schema__Stack__Info` (defined in `helpers/`) has:
- instance_id, stack_name, stack_type, region, state, public_ip, private_ip,
  instance_type, ami_id, uptime_seconds, tags

---

## helpers/user_data/

Each section is a class with a single `render(**kwargs) -> str` method. Sections are
concatenated by the stack's `User_Data__Builder`.

### Section__Base
Sets hostname, installs essential packages (`git`, `curl`, `jq`, `unzip`, `aws-cli`).
Takes `stack_name: str`.

### Section__Docker
Installs Docker CE or Podman depending on `engine: str = 'docker'`. Enables and starts the
socket. Optionally installs docker-compose-plugin.

### Section__Node
Installs Node.js at a specified major version via NodeSource repo. Installs pnpm globally.
Takes `node_major: int = 24`.

### Section__Nginx
Installs nginx. Writes a server block that proxies `localhost:<app_port>` on `0.0.0.0:443`
with SSL terminated by a self-signed cert (or Let's Encrypt if a domain is provided).
SSE-safe: `proxy_buffering off`, `proxy_read_timeout 3600s`.

Takes `app_port: int`, `domain: str = ''`.

### Section__Env__File
Writes a file of `KEY=VALUE` pairs to `/run/<stack_name>/env` on a tmpfs mount. The env file
is sourced by the app's systemd unit. Content is passed as a string (already assembled by the
stack's builder); this section handles only the mount + write.

Takes `stack_name: str`, `env_content: str`.

### Section__Shutdown
Schedules `systemd-run --on-active={max_hours}h /sbin/shutdown -h now` after the rest of
user-data completes. A no-op when `max_hours == 0`.

Takes `max_hours: int = 1`.

---

## helpers/health/

### Health__Poller
Polls until the instance is `running` (EC2 state) and the app HTTP endpoint returns 2xx.
Calls `EC2__Instance__Helper.wait_for_state` then `Health__HTTP__Probe.check`.

```
wait_healthy(
    region       : str,
    instance_id  : str,
    public_ip    : str,
    health_path  : str  = '/api/health',
    port         : int  = 443,
    timeout_sec  : int  = 300,
    poll_sec     : int  = 10,
) -> bool
```

### Health__HTTP__Probe
Single-responsibility: make one HTTP GET, return success/failure. Used by the poller.

---

## helpers/networking/

### Caller__IP__Detector
Fetches the caller's public IP from `https://ifconfig.me/ip`. Returns a string.

### Stack__Name__Generator
Generates random `adjective-noun` names (e.g. `quiet-fermi`, `brave-curie`).
Identical in spirit to the generators already in `docker/` and `podman/` — this is the
canonical version that those could eventually delegate to.
