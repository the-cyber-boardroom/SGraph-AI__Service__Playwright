# SG Playwright — Observability Dashboards

Two ready-to-import dashboard files for the SG Playwright observability stack.

---

## 1. OpenSearch Dashboards — Instance Lifecycle

**File:** `opensearch-instance-lifecycle.ndjson`  
**Import into:** `https://search-sg-playwright-logs-pffstr2ko4b7k7kuaxlhmykk7m.aos.eu-west-2.on.aws/_dashboards`

### What's included

| Object | Type | Description |
|--------|------|-------------|
| `sg-playwright-logs` | Index pattern | Maps `sg-playwright-logs` index, time field `@timestamp` |
| Log Volume | Visualization | Histogram of all log lines — the spike pattern shows EC2 boot events |
| Logs by Container | Visualization | Donut chart — which container emits the most logs |
| Errors & Warnings | Visualization | Histogram filtered to `ERROR`, `WARN`, `error`, `warning` — split by container |
| Proxy Traffic | Visualization | HTTP requests through mitmproxy (filters out header-normalisation noise) |
| Instance Boot Events | Visualization | Lines matching `"SG Playwright"` — each spike = a new instance booted |
| SG Playwright — Instance Lifecycle | **Dashboard** | All 5 panels, 24h window, auto-refresh 30s |

### How to import

1. Open **OpenSearch Dashboards** → Stack Management → Saved Objects
2. Click **Import**
3. Select `opensearch-instance-lifecycle.ndjson`
4. Choose **Automatically overwrite conflicts** → **Import**
5. Navigate to **Dashboards** → **SG Playwright — Instance Lifecycle**

> **Note:** If the `sg-playwright-logs` index pattern already exists, the import will update it in place — no data is affected.

---

## 2. Grafana — Container & Host Metrics

**File:** `grafana-sg-playwright-metrics.json`  
**Import into:** Amazon Managed Grafana (AMG) workspace

### What's included

| Panel | Source | Description |
|-------|--------|-------------|
| Instances Up (stat) | `up{stack="sg-playwright"}` | Green/red badge per instance |
| Active Instances (stat) | `up{stack="sg-playwright"}` | Lists all instances and their status |
| Container CPU Usage | cadvisor | 5m rate per container per instance |
| Container Memory Usage | cadvisor | Bytes per container per instance |
| Host Free Memory | node-exporter | Available vs total RAM |
| Root Disk Used % | node-exporter | Gauge with yellow @ 70%, red @ 85% |
| Host CPU Usage | node-exporter | 5m average across all cores |
| Container Network Receive | cadvisor | Bytes/s inbound per container |
| Container Network Transmit | cadvisor | Bytes/s outbound per container |

### How to import

1. Open **AMG** → Dashboards → **+ Import**
2. Upload `grafana-sg-playwright-metrics.json`
3. On the import screen, map **DS_AMP** → `grafana-amazonprometheus-datasource` (your existing AMP data source)
4. Click **Import**

### Data source requirements

The dashboard uses `${DS_AMP}` as the data source variable. Your AMP data source must be configured as:

- Plugin: **Amazon Managed Service for Prometheus**
- Authentication: **Workspace IAM Role**
- SigV4 region: `eu-west-2`
- URL: your AMP workspace remote query endpoint (same workspace as `AMP_REMOTE_WRITE_URL` but path `/api/v1/query`)

---

## DQL Queries — Copy-Paste Reference

These work in OpenSearch Dashboards → Discover with the `sg-playwright-logs` index pattern:

```
# All logs
(empty — shows everything)

# Boot events only (one cluster per EC2 start)
log: "SG Playwright"

# Errors and warnings
log: ERROR OR log: WARN OR log: error OR log: warning

# mitmproxy HTTP traffic (no header noise)
log: "HTTP/" AND NOT log: "Lowercased"

# Specific container
container_name: playwright

# Dev environment only
environment: dev
```

## PromQL Queries — Copy-Paste Reference

These work in Grafana Explore with the AMP data source:

```promql
# All instances up/down
up{stack="sg-playwright"}

# Container CPU (5m rate)
rate(container_cpu_usage_seconds_total{stack="sg-playwright", container_label_com_docker_compose_service!=""}[5m])

# Container memory
container_memory_usage_bytes{stack="sg-playwright", container_label_com_docker_compose_service!=""}

# Host free memory
node_memory_MemAvailable_bytes{stack="sg-playwright"}

# Root disk used %
1 - node_filesystem_avail_bytes{stack="sg-playwright", mountpoint="/"} / node_filesystem_size_bytes{stack="sg-playwright", mountpoint="/"}

# Host CPU usage (all cores, 5m avg)
1 - avg by (instance) (rate(node_cpu_seconds_total{stack="sg-playwright", mode="idle"}[5m]))

# Container network rx rate
rate(container_network_receive_bytes_total{stack="sg-playwright", container_label_com_docker_compose_service!=""}[5m])
```
