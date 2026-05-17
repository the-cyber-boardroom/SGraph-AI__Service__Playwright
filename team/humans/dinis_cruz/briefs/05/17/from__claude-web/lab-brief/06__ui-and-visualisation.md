---
title: "06 — UI & visualisation"
file: 06__ui-and-visualisation.md
author: Architect (Claude)
date: 2026-05-16 (UTC hour 15)
parent: README.md
---

# 06 — UI & visualisation

A measurement nobody reads is wasted. Each experiment ships **four output forms** by default — terminal table, ASCII timeline, JSON, and (optionally) HTML — so the same data can be skimmed at the terminal, diffed in git, or shared in a doc.

---

## 1. The four output forms

### 1.1 Terminal table (Rich)

The default. Every experiment renders a one-screen Rich table summarising the headline numbers.

```
$ sg aws lab run E11 propagation-timeline --ttl 60

▾ Lab Run  ◇ propagation-timeline  ◇ run-id 2026-05-16T15-20-04Z__a7b2c3
  zone               sg-compute.sgraph.ai
  record             lab-prop-a7b2c3.sg-compute.sgraph.ai
  ttl                60 s
  insync after       4.2 s

  ┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━┓
  ┃ resolver           ┃ first ms   ┃ first-correct  ┃ samples ┃
  ┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━┩
  │ Cloudflare 1.1.1.1 │   6 200 ms │ ✓ 192.0.2.42   │   3 / 3 │
  │ Cloudflare 1.0.0.1 │   6 800 ms │ ✓ 192.0.2.42   │   3 / 3 │
  │ Google 8.8.8.8     │  12 400 ms │ ✓ 192.0.2.42   │   2 / 2 │
  │ Google 8.8.4.4     │  18 200 ms │ ✓ 192.0.2.42   │   2 / 2 │
  │ Quad9 9.9.9.9      │   8 100 ms │ ✓ 192.0.2.42   │   2 / 2 │
  │ AdGuard EU         │   8 400 ms │ ✓ 192.0.2.42   │   2 / 2 │
  └────────────────────┴────────────┴────────────────┴─────────┘

  6/6 resolvers converged within 18.2 s (1.0× TTL)
  max-flip:   18.2 s
  cleanup:    1 record deleted ✓  (ledger empty)
```

### 1.2 ASCII timeline plot

For time-series experiments — propagation, DNS swap, cold-start distributions:

```
0s    5s    10s   15s   20s   25s   30s   35s   40s   45s   50s   55s   60s
│─────│─────│─────│─────│─────│─────│─────│─────│─────│─────│─────│─────│
●─────────upsert→INSYNC                                                          (Route 53 change-batch)
       ●─CF                                                                      (Cloudflare 1.1.1.1)
       ●─CF                                                                      (Cloudflare 1.0.0.1)
              ●─G1                                                               (Google 8.8.8.8)
                     ●─G2                                                        (Google 8.8.4.4)
        ●─QU                                                                     (Quad9)
        ●─AD                                                                     (AdGuard EU)
                       │─────TTL of new record────│
```

One row per resolver, one dot per first-correct observation. Resolution: 0.5 s per character. Width auto-scales.

### 1.3 JSON dump

```json
{
  "run_id": "2026-05-16T15-20-04Z__a7b2c3",
  "experiment": "propagation-timeline",
  "tier": "MUTATING_LOW",
  "started_at": "2026-05-16T15:20:04Z",
  "ended_at": "2026-05-16T15:21:32Z",
  "status": "OK",
  "params": { "ttl": 60, "record_name": "lab-prop-a7b2c3.sg-compute.sgraph.ai" },
  "insync_ms": 4204,
  "observations": [
    { "resolver": "1.1.1.1", "first_correct_ms": 6200, "samples": 3 },
    ...
  ],
  "cleanup": { "ledger_entries": 1, "deleted": 1, "failed": 0 }
}
```

`Schema__Lab__Run__Result.json()` produces it. Use it for git diffs across runs, for spreadsheets, or for posting into a brief.

### 1.4 HTML report (optional viewer)

`sg aws lab serve` starts a small FastAPI app on `localhost:8090` that reads `.sg-lab/runs/` and renders each run as an HTML page. Phase 2 of the harness; not blocking.

The viewer is built with **the existing front-end-design pattern** in the repo — one HTML page per run, plus an index. No SPA framework; static-rendered from server-side templates.

---

## 2. The flow diagram artefacts

The harness publishes **architecture diagrams of the system under test**, derived from the experiment results. These live alongside the brief docs and refresh on each run.

Three diagrams the harness can render (Mermaid in markdown, plus the terminal-ASCII equivalents):

### 2.1 The system-under-test diagram

After E27 runs successfully, the harness emits a diagram that shows the resources it provisioned with their actual measured timings:

```
        DNS                 CF                  Lambda              EC2
       (3.8 s)              (16.4 min)          (180 ms cold)       (1.9 min)
        │                    │                    │                  │
   ─upsert─INSYNC      create─Deployed       deploy─ready      start─running
                                                                          │
                                                                       health ✓
   ─delete─INSYNC      disable─delete         delete            stop─stopped
        │                    │                    │                  │
       (5.1 s)              (18.2 min)          (1 s)              (1.4 min)
```

### 2.2 The propagation map

Per resolver, where they each saw what value when. Useful when explaining Q1 (specific beats wildcard) to a non-architect reader.

### 2.3 The cold-path waterfall

Inspired by browser dev-tools' waterfall view. One row per phase (DNS resolve → TCP → TLS → CF queue → Lambda init → Lambda exec → response).

---

## 3. The "diff two runs" feature

A particularly important workflow: re-run an experiment, see what changed.

```
$ sg aws lab runs diff 2026-05-16T14-30-00Z__a7b2c3 2026-05-16T15-20-04Z__b8c4d2

▾ Diff  ◇ propagation-timeline

  insync_ms              4 204   →   3 891     ▽ -313 ms (−7%)

  per-resolver:
    Cloudflare 1.1.1.1   6 200   →   5 800     ▽ -400 ms
    Cloudflare 1.0.0.1   6 800   →   6 100     ▽ -700 ms
    Google 8.8.8.8      12 400   →  14 200     △ +1 800 ms
    Google 8.8.4.4      18 200   →  17 100     ▽ -1 100 ms
    Quad9                8 100   →   8 400     △ +300 ms
    AdGuard EU           8 400   →   8 300     ▽ -100 ms

  max-flip              18.2 s   →   17.1 s    ▽ -1.1 s
```

Diffing is implemented by sorting result schemas into a known shape and computing per-field deltas. The `Schema__Lab__Run__Result` is the single contract — every experiment writes one, diff knows how to walk it.

---

## 4. Where things land visually

```
              ┌─────────────────────────────────────────┐
              │  sg aws lab run E11 propagation-…       │
              └────────────────────┬────────────────────┘
                                   │
                                   ▼
              ┌─────────────────────────────────────────┐
              │            Lab__Runner                   │
              │  - opens .sg-lab/ledger/<run-id>.jsonl  │
              │  - dispatches experiment.execute(self)  │
              │  - tears down on exit                    │
              └────┬───────────────────────────────┬─────┘
                   │                               │
        runs       ▼                               ▼   writes
        ┌──────────────────┐               ┌─────────────────────┐
        │ Experiment.exec  │──────────────►│ Schema__Lab__Run__  │
        │  - probe()       │   produces    │   Result            │
        │  - measure()     │               └─────────┬───────────┘
        │  - record()      │                         │
        └──────────────────┘                         │
                                                     │
                              renderers ▼ render() ──┘
                          ┌─────┬──────┬──────┬──────┐
                          ▼     ▼      ▼      ▼      ▼
                       table  ASCII  JSON  HTML   diff
                       (Rich) timeline                  (vs prior run)
```

The renderer set is **swappable** — same Schema__Lab__Run__Result, different output. Phase 1 ships just `Render__Table` + `Render__JSON`. ASCII timeline + diff arrive in phase 2; HTML in phase 3.

---

## 5. Discoverability — `sg aws lab list`

```
$ sg aws lab list

┌────────┬──────────────────────────────────┬────────┬────────────────────────┐
│   id   │            name                  │  tier  │       budget           │
├────────┼──────────────────────────────────┼────────┼────────────────────────┤
│ E01    │ dns zone-inventory               │   0    │ 30 s,   0 mutations    │
│ E02    │ dns resolver-latency             │   0    │ 60 s,   0 mutations    │
│ E03    │ dns authoritative-ns-latency     │   0    │ 30 s,   0 mutations    │
│ E04    │ dns wildcard-pre-check           │   0    │ 30 s,   0 mutations    │
│ E10    │ dns insync-distribution          │   1    │ 10 min, 20 records     │
│ E11    │ dns propagation-timeline         │   1    │  5 min,  1 record      │
│ E12    │ dns wildcard-vs-specific         │   1    │  5 min,  2 records     │
│ E13    │ dns ttl-respect                  │   1    │  5 min,  1 record      │
│ E14    │ dns delete-propagation           │   1    │  5 min,  1 record      │
│ E20    │ cf inspect                       │   0    │ 10 s,   0 mutations    │
│ E21    │ cf edge-locality                 │   0    │ 30 s,   0 mutations    │
│ E22    │ cf tls-handshake                 │   0    │ 30 s,   0 mutations    │
│ E25    │ cf cache-policy-enforcement      │   2    │ 25 min, distrib + λ    │
│ E26    │ cf origin-error-handling         │   2    │ 25 min, distrib + λ    │
│ E27    │ e2e cold-path                    │   2    │ 30 min, distrib+λ+ec2  │
│ E30    │ lambda cold-start                │   1    │ 15 min, 1 λ            │
│ E31    │ lambda deps-impact               │   1    │ 30 min, 4 λ            │
│ E32    │ lambda stream-vs-buffer          │   1    │ 10 min, 2 λ            │
│ E33    │ lambda r53-call-latency          │   1    │ 10 min, 1 λ            │
│ E34    │ lambda ec2-curl                  │   1    │ 10 min, 1 λ            │
│ E35    │ lambda url-vs-direct-invoke      │   1    │ 10 min, 1 λ            │
│ E40    │ transition dns-swap-window       │   1    │ 10 min, 1 record       │
│ E41    │ transition stop-race-window      │   1    │ 15 min, ec2 + record   │
│ E42    │ transition concurrent-cold-thunder│   2   │ 25 min, distrib+λ+ec2  │
└────────┴──────────────────────────────────┴────────┴────────────────────────┘

22 experiments total.   Tier 0: 7   Tier 1: 11   Tier 2: 4
```

That's the lab.
