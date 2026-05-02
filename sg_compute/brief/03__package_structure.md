# SG/Compute — Package & Folder Structure

## Repository layout (incubation period)

```
sg_compute/                        ← SDK root (future PyPI package `sg-compute`)
│
├── brief/                            ← this spec (not shipped in the package)
│
├── helpers/                          ← shared helpers, no spec imports
│   ├── aws/
│   │   ├── EC2__Launch__Helper.py    ← RunInstances wrapper
│   │   ├── EC2__SG__Helper.py        ← CreateSecurityGroup / AuthorizeIngress
│   │   ├── EC2__Tags__Builder.py     ← standard tag list construction
│   │   ├── EC2__AMI__Helper.py       ← SSM latest AL2023 AMI lookup
│   │   ├── EC2__Instance__Helper.py  ← DescribeInstances, find-by-tag, terminate
│   │   └── EC2__Stack__Mapper.py     ← boto3 dict → Schema__Stack__Info
│   │
│   ├── user_data/
│   │   ├── Section__Base.py          ← hostname, locale, dnf update
│   │   ├── Section__Docker.py        ← docker or podman install + socket
│   │   ├── Section__Node.py          ← Node 24 + pnpm install
│   │   ├── Section__Nginx.py         ← nginx install + reverse-proxy template
│   │   ├── Section__Env__File.py     ← write /run/<node>/env to tmpfs
│   │   └── Section__Shutdown.py      ← systemd-run auto-terminate
│   │
│   ├── health/
│   │   ├── Health__Poller.py         ← polls EC2 state → running, then app port
│   │   └── Health__HTTP__Probe.py    ← HTTP GET with retry / timeout
│   │
│   └── networking/
│       ├── Caller__IP__Detector.py   ← ifconfig.me lookup
│       └── Stack__Name__Generator.py ← adjective-noun random names
│
└── __init__.py

sg_compute_specs/                  ← spec catalogue (future PyPI package `sg-compute-specs`)
├── ollama/                           ← Ollama GPU spec (incubation)
│   ├── schemas/
│   ├── service/
│   ├── cli/
│   └── version
│
└── open_design/                      ← Open Design host spec (incubation)
    ├── schemas/
    ├── service/
    ├── cli/
    └── version

sg_compute__tests/                 ← all tests, mirrors sg_compute/ layout
├── helpers/
│   ├── aws/
│   │   ├── test_EC2__Launch__Helper.py
│   │   ├── test_EC2__SG__Helper.py
│   │   └── …
│   ├── user_data/
│   │   ├── test_Section__Docker.py
│   │   └── …
│   └── health/
│       └── test_Health__Poller.py
└── specs/
    ├── open_design/
    │   ├── test_Open_Design__Service.py
    │   └── test_Open_Design__User_Data__Builder.py
    └── ollama/
        └── …
```

## Naming conventions

All conventions follow the existing SGraph-AI style:

| Kind              | Pattern                                   | Example                           |
|-------------------|-------------------------------------------|-----------------------------------|
| Schema class      | `Schema__<Spec>__<Purpose>`               | `Schema__Open_Design__Info`       |
| Helper class      | `EC2__<Domain>__Helper`                   | `EC2__SG__Helper`                 |
| Section class     | `Section__<Name>`                         | `Section__Docker`                 |
| Service class     | `<Spec>__Service`                         | `Open_Design__Service`            |
| User-data builder | `<Spec>__User_Data__Builder`              | `Open_Design__User_Data__Builder` |
| Primitive         | `Safe_Str__<Domain>__<Name>`              | `Safe_Str__Node__Name`            |
| Enum              | `Enum__<Domain>__<Name>`                  | `Enum__Node__State`               |
| Collection        | `List__Schema__<Spec>__<Name>`            | `List__Schema__Open_Design__Info` |
| Test file         | `test_<ClassName>.py`                     | `test_EC2__Launch__Helper.py`     |

## What lives in helpers/ vs sg_compute_specs/

**helpers/** — zero knowledge of any specific spec. Takes only primitives (region, node_name,
AMI id, port numbers, tag dicts). Can be imported by any spec without circular imports.

**sg_compute_specs/<name>/** — knows about its own schemas and imports from helpers/. Does NOT
import from other specs. Cross-spec wiring (e.g. open-design pointing at Ollama) is done at
the CLI/service level by passing an IP address string, not by importing the other spec's classes.
