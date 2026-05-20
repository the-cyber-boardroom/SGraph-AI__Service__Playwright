---
title: Remote EC2 control over SSH — the OSBot pattern
status: reference
audience: any engineer driving Linux hosts from Python (not SG/Compute-specific)
author: claude-opus-4-7
date: 2026-05-20
scope: portable pattern reference — depends only on osbot-utils + osbot-aws
related:
  - osbot_utils/helpers/ssh/SSH.py
  - osbot_utils/helpers/ssh/SSH__Execute.py
  - osbot_utils/helpers/ssh/SSH__Linux.py
  - osbot_utils/helpers/ssh/SSH__Linux__Amazon.py
  - osbot_utils/helpers/ssh/SSH__Python.py
  - osbot_utils/helpers/ssh/SCP.py
  - osbot_utils/helpers/ssh/SSH__Health_Check.py
  - osbot_aws/aws/ec2/EC2.py
  - osbot_aws/aws/ec2/EC2_Instance.py
---

# Remote EC2 control over SSH — the OSBot pattern

A self-contained reference for driving a remote Linux host from Python using
the OSBot SSH helper classes: create a key-pair, launch an instance that
trusts it, wait for SSH, then run commands / copy files / install packages /
register systemd services — and optionally snapshot the result to an AMI.

This document is **deliberately project-agnostic**. It documents the
`osbot-utils` + `osbot-aws` foundation and the composition pattern, with
runnable code samples you can lift into any codebase. Nothing here depends on
SG/Compute.

> **Why SSH and not SSM?** SSM Session Manager needs an SSM agent, an IAM
> instance profile, and the SSM API reachable. SSH needs only TCP/22 open and
> a key-pair. When you can't easily provision VPC/IAM scaffolding, key-based
> SSH is a low-friction alternative — and with key-only auth (no passwords),
> leaving 22 open to the world is a defensible posture (see
> [Security](#security)). The two are not mutually exclusive; pick per host.

---

## 1. The foundation — class map

Everything lives under `osbot_utils.helpers.ssh` (transport + commands) and
`osbot_aws.aws.ec2` (instance + key-pair lifecycle). All classes are
`Type_Safe` (or `Kwargs_To_Self`), so they compose by attribute injection.

| Class | Role | Key methods |
|---|---|---|
| `SSH__Execute` | The transport. Shells out to the system `ssh` binary via `subprocess`. | `exec(cmd)`, `execute_command(cmd) → {stdout,stderr,status,duration}`, `execute_command__return_stdout/stderr/dict/list`, `ssh_setup_ok()`, `ssh_host_available()` |
| `SSH__Linux` | Generic Linux verbs over `SSH__Execute`. | `apt_update`, `apt_install`, `ls`, `cat`, `mkdir`, `mv`, `rm`, `which`, `whoami`, `disk_space`, `memory_usage`, `running_processes`, `uname`, `dir_exists` |
| `SSH__Linux__Amazon` | Amazon-Linux flavour (yum + pip3.11). Subclass of `SSH__Linux`. | `install_python3()`, `pip_install(pkg)` |
| `SSH__Python` | Remote Python execution + pip. | `execute_python__code(code)`, `execute_python__function(fn)`, `pip_install`, `pip_list`, `python_version` |
| `SCP` | File transfer (subclass of `SSH__Execute`). | `copy_file_to_host(local, remote)`, `copy_file_from_host(remote, local)`, `copy_folder_as_zip_to_host(folder, dest)` |
| `SSH__Health_Check` | Liveness probe (echo round-trip). | `check_connection()`, `env_vars_set_ok()` |
| `SSH` | Facade tying the above together (cached). | `exec(cmd)`, `scp()`, `ssh_execute()`, `ssh_linux()`, `ssh_linux_amazon()`, `ssh_python()` |
| `EC2` (osbot-aws) | Account-level EC2 + key-pair lifecycle. | `key_pair_create`, `key_pair_create_to_file`, `key_pair_delete`, `key_pair_exists`, `key_pairs`, `instance_create` |
| `EC2_Instance` (osbot-aws) | One instance's lifecycle + SSH bootstrap. | `create()`, `ip_address()`, `wait_for_ssh()`, `ssh(key_file, key_user) → SSH` |

### `SSH__Execute` config surface

```python
class SSH__Execute(Type_Safe):
    ssh_host          : str          # IP or DNS of the target
    ssh_port          : int  = 22
    ssh_key_file      : str          # path to the .pem private key
    ssh_key_user      : str          # 'ubuntu' (Ubuntu AMIs) | 'ec2-user' (AL2023)
    strict_host_check : bool = False # False ⇒ adds -o StrictHostKeyChecking=no
    print_after_exec  : bool = False # True  ⇒ pretty-prints each result
```

`execute_command()` returns a dict: `{'stdout', 'stderr', 'status', 'command',
'duration'}`. `ssh_setup_ok()` is `True` only when host + key_file + key_user
are all set.

It can also self-configure from environment variables — this is how
`EC2_Instance.ssh()` wires things up:

| Env var | Field |
|---|---|
| `SSH__HOST` | `ssh_host` |
| `SSH__PORT` | `ssh_port` |
| `SSH__KEY_FILE` | `ssh_key_file` |
| `SSH__USER` | `ssh_key_user` |
| `SSH__STRICT_HOST_CHECK` | `strict_host_check` |

---

## 2. The end-to-end pattern

```
key-pair create ──▶ launch instance (key_name + SG allowing :22)
        │                        │
        │                        ▼
        │                  wait_for_ssh()  (poll TCP/22 until open)
        │                        │
        ▼                        ▼
   store .pem            instance.ssh(key_file, user) ──▶ SSH facade
   (chmod 0400)                  │
                                 ▼
              ssh.ssh_linux() / ssh_linux_amazon() / ssh_python() / scp()
              ── install packages, copy files, register systemd services ──
                                 │
                                 ▼
                    (optional) snapshot to AMI for fast re-launch
```

### Step 1 — create (or reuse) a key-pair

`EC2.key_pair_create_to_file` creates the AWS key-pair *and* writes the
private key to disk with `chmod 0400` (the only time AWS ever returns the
private material):

```python
from osbot_aws.aws.ec2.EC2 import EC2

ec2 = EC2()
result = ec2.key_pair_create_to_file(key_name      = 'my-deploy-key',
                                      target_folder = '/secure/keys',
                                      tags          = {'purpose': 'deploy'})
# result = {'path_key_pair': '/secure/keys/my-deploy-key.pem',
#           'key_pair_id'  : 'key-0abc…',
#           'key_pair'     : {…}}
```

Reuse logic: `ec2.key_pair_exists(key_pair_name='my-deploy-key')` before
creating. **The private key is unrecoverable** after this call — store it
securely (a vault, a secrets manager), never in git.

### Step 2 — launch an instance that trusts the key

The instance must (a) be launched with `key_name=<your key-pair>` and (b) sit
behind a security group that allows inbound TCP/22 from wherever you'll
connect.

```python
from osbot_aws.aws.ec2.EC2_Instance import EC2_Instance

instance = EC2_Instance()
instance.create_kwargs = dict(image_id          = 'ami-0…',      # Ubuntu or AL2023
                              instance_type     = 't3.nano',
                              key_name          = 'my-deploy-key',
                              security_group_id = 'sg-0…',        # must allow :22
                              spot_instance     = True)
instance_id = instance.create(instance_name='my-host')
```

### Step 3 — wait for SSH, then get a configured `SSH`

```python
with EC2_Instance(instance_id=instance_id) as host:
    host.wait_for_ssh()                    # polls TCP/22 until open
    ip = host.ip_address()                 # public IP
    ssh = host.ssh(ssh_key_file='/secure/keys/my-deploy-key.pem',
                   ssh_key_user='ubuntu')  # 'ec2-user' for Amazon Linux
```

`wait_for_ssh()` only proves the *port* is open. The OS may still be
booting — see [the readiness loop gotcha](#readiness-port-open--shell-ready).

### Step 4 — drive the host

```python
# raw commands
ssh.exec('uname -a')

# Linux verbs
ssh.ssh_linux().apt_update()
ssh.ssh_linux().apt_install('python3-pip')

# Amazon-Linux flavour (yum + pip3.11)
ssh.ssh_linux_amazon().install_python3()
ssh.ssh_linux_amazon().pip_install('osbot-aws')

# remote Python
ssh.ssh_python().pip_install('requests')
ssh.ssh_python().execute_python__code__return_stdout('print(1+1)')

# file transfer
ssh.scp().copy_file_to_host('./app.service', 'app.service')
ssh.scp().copy_folder_as_zip_to_host('./dist', '/opt/app')   # zips, scp, unzips

# systemd registration
ssh.exec('sudo mv app.service /etc/systemd/system/app.service')
ssh.exec('sudo systemctl daemon-reload')
ssh.exec('sudo systemctl enable app')
ssh.exec('sudo systemctl start  app')
```

### Step 5 (optional) — snapshot to an AMI

Once a host is provisioned the way you want, bake an AMI so the next launch
skips the install steps:

```python
ami_id = EC2().create_image(instance_id=instance_id, name='my-host-baked')
```

---

## 3. Worked example — provision + deploy in one class

A complete, generic deployer distilled from real usage. Swap the
package/service names for your own.

```python
from osbot_utils.type_safe.Type_Safe   import Type_Safe
from osbot_aws.aws.ec2.EC2              import EC2
from osbot_aws.aws.ec2.EC2_Instance     import EC2_Instance


class Remote__Deployer(Type_Safe):
    ec2          : EC2
    image_id     : str = 'ami-0…'          # Ubuntu 22.04 in your region
    instance_type: str = 't3.small'
    key_name     : str = 'my-deploy-key'
    key_file     : str = '/secure/keys/my-deploy-key.pem'
    key_user     : str = 'ubuntu'
    sg_id        : str = 'sg-0…'           # allows inbound :22 (+ your app port)

    def launch(self, name: str) -> str:
        instance = EC2_Instance()
        instance.create_kwargs = dict(image_id          = self.image_id,
                                       instance_type     = self.instance_type,
                                       key_name          = self.key_name,
                                       security_group_id = self.sg_id,
                                       spot_instance     = True)
        return instance.create(instance_name=name)

    def connect(self, instance_id: str):
        host = EC2_Instance(instance_id=instance_id)
        host.wait_for_ssh()
        return host.ssh(ssh_key_file=self.key_file, ssh_key_user=self.key_user)

    def deploy(self, instance_id: str, app_port: int = 3000) -> str:
        ssh = self.connect(instance_id)
        ssh.ssh_execute().print_after_exec = True             # echo each step

        ssh.exec('sudo apt-get update')
        ssh.exec('sudo apt-get install -y python3-pip python3-venv')
        ssh.scp().copy_file_to_host('./app.service', 'app.service')
        ssh.scp().copy_folder_as_zip_to_host('./dist', '/opt/app')

        ssh.exec('sudo mv app.service /etc/systemd/system/app.service')
        ssh.exec('sudo systemctl daemon-reload')
        ssh.exec('sudo systemctl enable app')
        ssh.exec('sudo systemctl start  app')

        ip = EC2_Instance(instance_id=instance_id).ip_address()
        return f'http://{ip}:{app_port}'

    def run(self, name: str) -> dict:
        instance_id = self.launch(name)
        url         = self.deploy(instance_id)
        ami_id      = self.ec2.create_image(instance_id=instance_id, name=name)
        return dict(instance_id=instance_id, url=url, ami_id=ami_id)
```

---

## 4. Exposing remote control as an HTTP API

The pattern composes cleanly into a service + route layer so a host can be
driven over HTTP (handy for an admin console or another service). Two thin
layers:

**Service layer** — wraps `SSH__Execute` + `SSH__Linux` + `SCP`, returns
plain dicts, and supports a "twin mode" where `ssh_execute` is swapped for a
fake that records commands instead of running them (your test seam):

```python
from osbot_utils.helpers.ssh.SSH__Execute import SSH__Execute
from osbot_utils.helpers.ssh.SCP          import SCP


class Service__EC2_SSH:                       # twin mode: inject a fake ssh_execute
    def __init__(self, ssh_execute=None):
        self.ssh_execute = ssh_execute or SSH__Execute()

    def configure(self, host, key_file, key_user='ubuntu', port=22) -> dict:
        self.ssh_execute.ssh_host     = host
        self.ssh_execute.ssh_key_file = key_file
        self.ssh_execute.ssh_key_user = key_user
        self.ssh_execute.ssh_port     = port
        return dict(status='configured', host=host, user=key_user, port=port)

    def exec(self, command: str) -> dict:
        if not self.ssh_execute.ssh_setup_ok():
            return dict(status='error', message='SSH not configured')
        r = self.ssh_execute.execute_command(command)
        return dict(status=r.get('status',''), stdout=r.get('stdout',''),
                    stderr=r.get('stderr',''), command=command)

    def apt_install(self, packages: str) -> dict:
        return self.exec(f'sudo apt-get install -y {packages}')

    def systemctl(self, action: str, service: str) -> dict:
        return self.exec(f'sudo systemctl {action} {service}')

    def upload_file(self, local_path: str, remote_path: str) -> dict:
        if not self.ssh_execute.ssh_setup_ok():
            return dict(status='error', message='SSH not configured')
        scp = SCP(ssh_host=self.ssh_execute.ssh_host, ssh_port=self.ssh_execute.ssh_port,
                  ssh_key_file=self.ssh_execute.ssh_key_file, ssh_key_user=self.ssh_execute.ssh_key_user)
        stderr = scp.copy_file_to_host(local_path, remote_path)
        return dict(status='error' if stderr else 'uploaded', remote_path=remote_path)
```

**Route layer** — maps each service method to an endpoint
(`POST /ssh/configure`, `POST /ssh/exec`, `GET /ssh/whoami`,
`POST /ssh/apt-install`, `POST /ssh/systemctl`, `POST /ssh/upload-file`, …).
A FastAPI surface over `Service__EC2_SSH` turns "remote control" into a
documented API: configure once, then drive the host with REST calls. Note
that exposing a raw `exec` endpoint is effectively remote code execution —
gate it (auth + allow-list) before anything but a trusted operator can reach
it.

---

## 5. Security

Key-based SSH with port 22 open to the internet is a **defensible** posture
*if* you follow these rules. The risk profile is very different from
password SSH (which you must never enable).

| Control | Why |
|---|---|
| **Key-only auth, `PasswordAuthentication no`** | Removes brute-force as an attack vector. AWS Ubuntu/AL2023 AMIs ship this way by default. |
| **Private key never in git** | `key_pair_create_to_file` writes `chmod 0400`; keep it in a vault / secrets manager. A leaked `.pem` is a full host compromise. |
| **One key-pair per purpose/environment**, tagged | Lets you revoke (`key_pair_delete`) blast-radius-limited. |
| **Narrow the SG when you can** | `0.0.0.0/0` on :22 is acceptable for key-only auth but tighter (your egress IP, a bastion CIDR) is strictly better. |
| **`strict_host_check`** | OSBot defaults to `StrictHostKeyChecking=no` for first-connect ergonomics. That trades away MITM detection. For long-lived hosts, pin the host key and set `strict_host_check=True`. |
| **Rotate + snapshot** | Bake an AMI, then you can terminate/relaunch hosts cheaply and rotate keys without re-deploying. |
| **Treat any `exec` HTTP endpoint as RCE** | If you expose the route layer, require auth and an allow-list. A raw `exec` endpoint is arbitrary code execution by design. |

---

## 6. Gotchas

### Readiness: port-open ≠ shell-ready
`wait_for_ssh()` only confirms TCP/22 accepts connections. A freshly-booted
host can still reject commands with `System is booting up`. Wrap a readiness
loop around a trivial command:

```python
def wait_until_ready(ssh, tries=20, delay=1):
    from osbot_utils.utils.Misc import wait_for
    for i in range(tries):
        r = ssh.exec('pwd')                       # via execute_command
        if 'System is booting up' in r.get('stderr', ''):
            wait_for(delay); continue
        if r.get('stdout', '').strip():           # got a real prompt back
            return True
    raise Exception('host never became shell-ready')
```

### SCP uses `-P`, ssh uses `-p` for the port
A real footgun in the underlying CLIs. OSBot's `SCP` handles the swap
internally, but if you build scp args by hand, remember scp wants
upper-case `-P`.

### `which()` / string-interpolated commands are injection-prone
`SSH__Linux.which(target)` (and any helper that f-strings user input into a
command) will execute whatever you pass. Never interpolate untrusted input
into a command string — quote/validate at the boundary.

### Config via env vars is process-global
`EC2_Instance.ssh()` configures the transport by writing `SSH__HOST` /
`SSH__KEY_FILE` / `SSH__USER` into `os.environ`. That's global mutable state —
driving two hosts from one process via this path will clobber each other.
For multi-host work, construct `SSH__Execute` objects directly and set the
fields, rather than going through the env-var path.

### `print_after_exec`
Set `ssh.ssh_execute().print_after_exec = True` to get a boxed
status/stderr/stdout dump after every command — invaluable when debugging a
deploy, noisy in production.

---

## 7. Testing without a live host (the "twin")

The transport is the only thing that touches the network, so fake *it* and
everything above composes for free — no mocks/patches of the helper classes:

```python
class Fake__SSH__Execute:                       # records instead of running
    def __init__(self):
        self.commands = []
        self.ssh_host = self.ssh_key_file = self.ssh_key_user = 'set'
        self.ssh_port = 22
    def ssh_setup_ok(self):
        return True
    def execute_command(self, command):
        self.commands.append(command)
        return dict(status='ok', stdout='', stderr='', command=command)

svc = Service__EC2_SSH(ssh_execute=Fake__SSH__Execute())
svc.apt_install('nginx')
assert svc.ssh_execute.commands == ['sudo apt-get install -y nginx']
```

This is exactly how the service layer's "twin mode" works: assert on the
*commands that would run* rather than standing up an instance. Keep a single
real-host smoke test behind an env-gate for the genuine round-trip.

---

## 8. API quick-reference

```python
# ── key-pair lifecycle (osbot_aws EC2) ──────────────────────────────────────
EC2().key_pair_create(key_name, tags=None)               # → AWS key-pair (no file)
EC2().key_pair_create_to_file(key_name, folder, tags)    # → writes .pem chmod 0400
EC2().key_pair_exists(key_pair_name='…')                 # → bool
EC2().key_pair_delete(key_pair_name='…')                 # → bool (revoke)
EC2().key_pairs()                                        # → list

# ── instance bootstrap (osbot_aws EC2_Instance) ─────────────────────────────
inst = EC2_Instance(); inst.create_kwargs = {…}; inst.create(name)
EC2_Instance(instance_id=…).wait_for_ssh()               # poll :22
EC2_Instance(instance_id=…).ip_address()                 # public IP
EC2_Instance(instance_id=…).ssh(key_file, key_user)      # → configured SSH

# ── SSH facade (osbot_utils) ────────────────────────────────────────────────
ssh.exec(cmd)                                            # → stdout str
ssh.ssh_execute().execute_command(cmd)                   # → {stdout,stderr,status,duration}
ssh.ssh_linux().apt_install(pkg) / .ls() / .mkdir() / .which()
ssh.ssh_linux_amazon().install_python3() / .pip_install(pkg)   # yum + pip3.11
ssh.ssh_python().pip_install(pkg) / .execute_python__code(code)
ssh.scp().copy_file_to_host(local, remote)
ssh.scp().copy_file_from_host(remote, local)
ssh.scp().copy_folder_as_zip_to_host(folder, dest)

# ── health ──────────────────────────────────────────────────────────────────
SSH__Health_Check(ssh_host=…, ssh_key_file=…, ssh_key_user=…).check_connection()
```
