#!/usr/bin/env python3
"""
ec2-boot-bench — measure how fast an EC2 instance gets from RunInstances
to the first successful SSM SendCommand.

This is the floor for cold-start latency on ephemeral instances. Nothing in
our boot script can go faster than this number.

Single round-trip per run:
    1. ec2.run_instances(...)
    2. poll ssm.send_command in a tight loop until it accepts AND completes
    3. record elapsed seconds
    4. ec2.terminate_instances(...)

Outputs a human-readable table per run and appends one CSV row to a results
file for cross-run aggregation.

Requires:
    - boto3
    - an IAM instance profile with AmazonSSMManagedInstanceCore attached
    - a security group permitting outbound 443 (for SSM agent → SSM endpoints)
    - an AMI that has SSM Agent pre-installed (AL2023 / Ubuntu SSM AMIs both do)

Usage:
    ec2_boot_bench.py \\
        --instance-type g5.xlarge \\
        --region eu-west-2 \\
        --ami ami-0abcd1234 \\
        --subnet subnet-0abc \\
        --security-group sg-0abc \\
        --instance-profile sg-compute-bench \\
        --runs 5 \\
        --spot

    ec2_boot_bench.py --config bench.yaml --runs 10
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
import uuid
import signal
import socket
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import boto3
    from botocore.config import Config as BotoConfig
    from botocore.exceptions import ClientError, WaiterError
except ImportError:
    sys.stderr.write(
        "FATAL: boto3 not installed. `pip install boto3`\n"
    )
    sys.exit(2)

try:
    import yaml
except ImportError:
    yaml = None  # YAML config is optional


# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

# AWS SSM SendCommand has a hard minimum TimeoutSeconds of 30 (per the service
# model). We learned this the hard way in a previous session — see the bug
# report on silent ParamValidationError swallowing.
SSM_MIN_TIMEOUT = 30

# How long to keep trying SSM SendCommand before giving up on this run.
# Five minutes is generous; a healthy g5.xlarge typically hits SSM-ready in 30-90s.
DEFAULT_SSM_READY_TIMEOUT_SECS = 300

# How often to poll SSM SendCommand. The instance isn't registered with SSM
# until the agent has phoned home, so the early polls all return
# InvalidInstanceId — that's expected.
SSM_POLL_INTERVAL_SECS = 2

# How long to wait for the SendCommand invocation to finish once it's accepted.
# We're running `echo` so it should be near-instant; bound it anyway.
SSM_INVOCATION_TIMEOUT_SECS = 60

# Tag prefix so we can identify and clean up any orphans from this tool.
TAG_TOOL = "ec2-boot-bench"


# ----------------------------------------------------------------------------
# Data classes
# ----------------------------------------------------------------------------

@dataclass
class RunResult:
    """One end-to-end timing run."""
    run_id: str
    timestamp_utc: str
    region: str
    az: Optional[str]
    instance_type: str
    purchase_option: str           # "on-demand" or "spot"
    ami: str
    instance_id: Optional[str]
    success: bool
    elapsed_run_instances_secs: Optional[float]   # API call duration
    elapsed_to_ssm_ready_secs: Optional[float]    # RunInstances return → first SSM ok
    elapsed_total_secs: Optional[float]           # RunInstances call start → SSM ok
    ssm_attempts: int
    error: Optional[str]


# ----------------------------------------------------------------------------
# AWS helpers
# ----------------------------------------------------------------------------

def build_clients(region: str):
    """Build EC2 and SSM clients with tighter timeouts than boto3 defaults.

    The default boto3 read timeout is 60s. For SendCommand polling we want
    snappy failures so a stuck poll doesn't dominate the measurement.
    """
    cfg = BotoConfig(
        region_name=region,
        retries={"max_attempts": 3, "mode": "standard"},
        connect_timeout=5,
        read_timeout=10,
    )
    return boto3.client("ec2", config=cfg), boto3.client("ssm", config=cfg)


def launch_instance(
    ec2,
    *,
    ami: str,
    instance_type: str,
    subnet: str,
    security_group: str,
    instance_profile: str,
    spot: bool,
    run_id: str,
) -> tuple[str, Optional[str], float]:
    """Call RunInstances. Return (instance_id, az, api_elapsed_secs).

    Note: this measures the API call duration. The instance is in 'pending'
    state when RunInstances returns; SSM-ready comes later.
    """
    market_options = {}
    if spot:
        # SpotInstanceType=one-time means: terminate on stop, do not
        # persist the request. Right shape for an ephemeral test.
        market_options = {
            "MarketType": "spot",
            "SpotOptions": {
                "SpotInstanceType": "one-time",
                "InstanceInterruptionBehavior": "terminate",
            },
        }

    kwargs = {
        "ImageId": ami,
        "InstanceType": instance_type,
        "MinCount": 1,
        "MaxCount": 1,
        "SubnetId": subnet,
        "SecurityGroupIds": [security_group],
        "IamInstanceProfile": {"Name": instance_profile},
        "TagSpecifications": [
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": f"{TAG_TOOL}-{run_id}"},
                    {"Key": "tool", "Value": TAG_TOOL},
                    {"Key": "run_id", "Value": run_id},
                ],
            }
        ],
        # No user-data — we want the pure floor. Anything in user-data
        # would add to the measured time and confuse the baseline.
        # InstanceInitiatedShutdownBehavior=terminate gives us a kill
        # switch via `shutdown` from inside if anything ever needs it.
        "InstanceInitiatedShutdownBehavior": "terminate",
    }
    if market_options:
        kwargs["InstanceMarketOptions"] = market_options

    t0 = time.perf_counter()
    resp = ec2.run_instances(**kwargs)
    api_elapsed = time.perf_counter() - t0

    inst = resp["Instances"][0]
    return inst["InstanceId"], inst.get("Placement", {}).get("AvailabilityZone"), api_elapsed


def wait_for_ssm_ready(
    ssm,
    *,
    instance_id: str,
    timeout_secs: int,
    poll_interval_secs: float,
) -> tuple[bool, int, Optional[str]]:
    """Poll SendCommand until it accepts the instance AND the invocation
    completes successfully. Returns (success, attempts, error).

    Sequence of expected states:
      - Early: InvalidInstanceId (instance not yet registered with SSM)
      - Mid:   SendCommand accepted, GetCommandInvocation returns Pending
      - End:   GetCommandInvocation returns Success
    """
    deadline = time.perf_counter() + timeout_secs
    attempts = 0
    marker = f"ssm-ready-{uuid.uuid4().hex[:8]}"

    while time.perf_counter() < deadline:
        attempts += 1
        try:
            send_resp = ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={"commands": [f"echo {marker}"]},
                TimeoutSeconds=SSM_MIN_TIMEOUT,
                Comment=f"{TAG_TOOL}-readiness-probe",
            )
            command_id = send_resp["Command"]["CommandId"]
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("InvalidInstanceId", "InvalidInstanceInformationFilterValue"):
                # Expected: instance hasn't registered with SSM yet.
                time.sleep(poll_interval_secs)
                continue
            # Anything else is a real error — surface it.
            return False, attempts, f"send_command ClientError: {code}: {e}"
        except Exception as e:
            return False, attempts, f"send_command unexpected: {type(e).__name__}: {e}"

        # SendCommand accepted; wait for the invocation to complete.
        inv_deadline = time.perf_counter() + SSM_INVOCATION_TIMEOUT_SECS
        while time.perf_counter() < inv_deadline:
            try:
                inv = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id,
                )
            except ClientError as e:
                code = e.response.get("Error", {}).get("Code", "")
                if code == "InvocationDoesNotExist":
                    # SSM hasn't propagated the invocation record yet; brief wait.
                    time.sleep(0.5)
                    continue
                return False, attempts, f"get_command_invocation ClientError: {code}: {e}"
            except Exception as e:
                return False, attempts, f"get_command_invocation unexpected: {type(e).__name__}: {e}"

            status = inv.get("Status")
            if status == "Success":
                # Sanity-check that the marker actually came back.
                stdout = (inv.get("StandardOutputContent") or "").strip()
                if marker in stdout:
                    return True, attempts, None
                return False, attempts, f"marker not found in stdout: {stdout!r}"
            if status in ("Cancelled", "TimedOut", "Failed"):
                return False, attempts, f"invocation status={status} stderr={inv.get('StandardErrorContent')!r}"
            # Pending / InProgress / Delayed — keep polling.
            time.sleep(0.5)

        # Invocation didn't finish in time. Move on and try a fresh SendCommand.
        # (Don't count this as a hard failure unless the outer deadline passes.)
        time.sleep(poll_interval_secs)

    return False, attempts, f"timed out after {timeout_secs}s waiting for SSM"


def terminate_instance(ec2, instance_id: str) -> None:
    """Best-effort terminate. Never raises — we don't want cleanup failures
    to mask the real result."""
    if not instance_id:
        return
    try:
        ec2.terminate_instances(InstanceIds=[instance_id])
    except Exception as e:
        sys.stderr.write(
            f"[warn] terminate_instances({instance_id}) failed: {type(e).__name__}: {e}\n"
        )


# ----------------------------------------------------------------------------
# One run
# ----------------------------------------------------------------------------

def run_once(args, *, run_number: int, total_runs: int) -> RunResult:
    region = args.region
    instance_type = args.instance_type
    purchase = "spot" if args.spot else "on-demand"
    run_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"

    print(
        f"\n[run {run_number}/{total_runs}] "
        f"region={region} type={instance_type} purchase={purchase} run_id={run_id}",
        flush=True,
    )

    ec2, ssm = build_clients(region)

    result = RunResult(
        run_id=run_id,
        timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        region=region,
        az=None,
        instance_type=instance_type,
        purchase_option=purchase,
        ami=args.ami,
        instance_id=None,
        success=False,
        elapsed_run_instances_secs=None,
        elapsed_to_ssm_ready_secs=None,
        elapsed_total_secs=None,
        ssm_attempts=0,
        error=None,
    )

    t_start = time.perf_counter()
    instance_id = None

    try:
        instance_id, az, api_elapsed = launch_instance(
            ec2,
            ami=args.ami,
            instance_type=instance_type,
            subnet=args.subnet,
            security_group=args.security_group,
            instance_profile=args.instance_profile,
            spot=args.spot,
            run_id=run_id,
        )
        result.instance_id = instance_id
        result.az = az
        result.elapsed_run_instances_secs = round(api_elapsed, 3)
        print(f"  launched: instance_id={instance_id} az={az} ({api_elapsed:.2f}s)", flush=True)

        # Now poll SSM until the instance answers.
        t_ssm_start = time.perf_counter()
        ok, attempts, error = wait_for_ssm_ready(
            ssm,
            instance_id=instance_id,
            timeout_secs=args.ssm_timeout,
            poll_interval_secs=SSM_POLL_INTERVAL_SECS,
        )
        elapsed_to_ssm = time.perf_counter() - t_ssm_start

        result.ssm_attempts = attempts
        result.elapsed_to_ssm_ready_secs = round(elapsed_to_ssm, 3)
        result.elapsed_total_secs = round(time.perf_counter() - t_start, 3)
        result.success = ok
        if not ok:
            result.error = error
            print(f"  FAILED: {error} (after {attempts} SSM attempts, {elapsed_to_ssm:.1f}s)", flush=True)
        else:
            print(
                f"  SSM-ready: {elapsed_to_ssm:.2f}s "
                f"(attempts={attempts}, total={result.elapsed_total_secs:.2f}s)",
                flush=True,
            )

    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        msg = e.response.get("Error", {}).get("Message", str(e))
        result.error = f"{code}: {msg}"
        print(f"  ERROR: {result.error}", flush=True)
    except KeyboardInterrupt:
        result.error = "interrupted"
        print("  interrupted", flush=True)
        raise
    except Exception as e:
        result.error = f"{type(e).__name__}: {e}"
        print(f"  UNEXPECTED: {result.error}", flush=True)
    finally:
        # Always try to terminate, even on partial failure.
        if instance_id:
            print(f"  terminating {instance_id}...", flush=True)
            terminate_instance(ec2, instance_id)

    return result


# ----------------------------------------------------------------------------
# Output
# ----------------------------------------------------------------------------

def print_summary_table(results: list[RunResult]) -> None:
    """Render the per-run summary as a fixed-width table."""
    if not results:
        return

    successes = [r for r in results if r.success and r.elapsed_to_ssm_ready_secs is not None]

    print("\n" + "=" * 78)
    print(f"SUMMARY — {len(results)} run(s), {len(successes)} succeeded")
    print("=" * 78)

    headers = ["#", "instance_type", "purchase", "az", "ssm_ready_s", "total_s", "attempts", "result"]
    widths = [3, 14, 9, 12, 12, 10, 9, 30]
    row_fmt = " ".join(f"{{:<{w}}}" for w in widths)
    print(row_fmt.format(*headers))
    print("-" * 78)
    for i, r in enumerate(results, 1):
        row = [
            i,
            r.instance_type,
            r.purchase_option,
            r.az or "-",
            f"{r.elapsed_to_ssm_ready_secs:.2f}" if r.elapsed_to_ssm_ready_secs is not None else "-",
            f"{r.elapsed_total_secs:.2f}" if r.elapsed_total_secs is not None else "-",
            r.ssm_attempts,
            "OK" if r.success else f"FAIL: {(r.error or '')[:25]}",
        ]
        print(row_fmt.format(*[str(x) for x in row]))

    if successes:
        times = sorted(r.elapsed_to_ssm_ready_secs for r in successes)
        n = len(times)
        mean = sum(times) / n
        median = times[n // 2] if n % 2 else (times[n // 2 - 1] + times[n // 2]) / 2
        p95 = times[min(int(n * 0.95), n - 1)]
        print("-" * 78)
        print(
            f"SSM-ready (success only):  min={times[0]:.2f}s  median={median:.2f}s  "
            f"mean={mean:.2f}s  p95={p95:.2f}s  max={times[-1]:.2f}s"
        )
    print("=" * 78 + "\n")


def append_csv(results: list[RunResult], path: Path) -> None:
    """Append rows to the CSV file, writing a header if it didn't exist."""
    new_file = not path.exists()
    fields = list(asdict(results[0]).keys())
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        if new_file:
            w.writeheader()
        for r in results:
            w.writerow(asdict(r))
    print(f"appended {len(results)} row(s) to {path}", flush=True)


# ----------------------------------------------------------------------------
# Config loading
# ----------------------------------------------------------------------------

def load_yaml_config(path: Path) -> dict:
    if yaml is None:
        sys.exit("FATAL: --config requires PyYAML (`pip install pyyaml`)")
    with path.open() as f:
        return yaml.safe_load(f) or {}


def merge_config_and_args(config: dict, args: argparse.Namespace) -> argparse.Namespace:
    """CLI args override config-file values where both are present."""
    for k, v in config.items():
        key = k.replace("-", "_")
        if not hasattr(args, key):
            continue
        # Argparse defaults are None for missing values; only fill those.
        if getattr(args, key) in (None, False) and v is not None:
            setattr(args, key, v)
    return args


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Measure EC2 RunInstances → first successful SSM SendCommand.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Usage:", 1)[1].strip() if "Usage:" in __doc__ else "",
    )
    p.add_argument("--config", type=Path, help="YAML config (CLI args override)")

    p.add_argument("--region", help="AWS region, e.g. eu-west-2")
    p.add_argument("--instance-type", help="EC2 instance type, e.g. g5.xlarge")
    p.add_argument("--ami", help="AMI ID (must have SSM Agent installed)")
    p.add_argument("--subnet", help="Subnet ID")
    p.add_argument("--security-group", help="Security group ID (egress 443 → SSM endpoints)")
    p.add_argument("--instance-profile", help="IAM instance profile name (AmazonSSMManagedInstanceCore)")

    p.add_argument("--spot", action="store_true", help="Request spot instead of on-demand")
    p.add_argument("--runs", type=int, default=1, help="Number of runs (default 1)")
    p.add_argument(
        "--ssm-timeout",
        type=int,
        default=DEFAULT_SSM_READY_TIMEOUT_SECS,
        help=f"How long to wait for SSM-ready before failing (default {DEFAULT_SSM_READY_TIMEOUT_SECS}s)",
    )

    p.add_argument(
        "--csv",
        type=Path,
        default=Path("ec2_boot_bench_results.csv"),
        help="CSV file to append results to (default ./ec2_boot_bench_results.csv)",
    )
    p.add_argument(
        "--inter-run-sleep",
        type=float,
        default=5.0,
        help="Seconds to wait between runs (lets EC2/SSM state settle; default 5)",
    )
    return p


REQUIRED_FIELDS = ("region", "instance_type", "ami", "subnet", "security_group", "instance_profile")


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.config:
        cfg = load_yaml_config(args.config)
        args = merge_config_and_args(cfg, args)

    missing = [f for f in REQUIRED_FIELDS if not getattr(args, f, None)]
    if missing:
        parser.error("missing required: " + ", ".join("--" + m.replace("_", "-") for m in missing))

    # Install a SIGINT handler so Ctrl-C still terminates any in-flight instance.
    interrupted = {"flag": False}

    def _sigint(_signo, _frame):
        interrupted["flag"] = True
        # Don't raise here; let the run finish its finally-block cleanup.
        sys.stderr.write("\n[interrupt] finishing current run and stopping...\n")

    signal.signal(signal.SIGINT, _sigint)

    results: list[RunResult] = []
    try:
        for i in range(args.runs):
            r = run_once(args, run_number=i + 1, total_runs=args.runs)
            results.append(r)
            # Stream-write so partial results survive a crash.
            append_csv([r], args.csv)
            if interrupted["flag"]:
                break
            if i < args.runs - 1 and args.inter_run_sleep > 0:
                time.sleep(args.inter_run_sleep)
    finally:
        if results:
            print_summary_table(results)

    # Exit code reflects whether all runs succeeded.
    all_ok = all(r.success for r in results) and not interrupted["flag"]
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
