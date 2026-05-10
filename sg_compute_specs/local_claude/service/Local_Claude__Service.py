# ═══════════════════════════════════════════════════════════════════════════════
# Ephemeral EC2 — Local_Claude__Service
# Orchestrator for the local-claude stack. Extends Spec__Service__Base —
# health/exec/connect_target inherited; spec-specific bits below.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import time

from typing import Optional

from sg_compute.core.spec.Spec__Service__Base                                  import Spec__Service__Base
from sg_compute.platforms.ec2.networking.Caller__IP__Detector                  import Caller__IP__Detector
from sg_compute.platforms.ec2.networking.Stack__Name__Generator                import Stack__Name__Generator

from sg_compute_specs.local_claude.schemas.Schema__Local_Claude__Create__Request  import Schema__Local_Claude__Create__Request
from sg_compute_specs.local_claude.schemas.Schema__Local_Claude__Create__Response import Schema__Local_Claude__Create__Response
from sg_compute_specs.local_claude.schemas.Schema__Local_Claude__Delete__Response import Schema__Local_Claude__Delete__Response
from sg_compute_specs.local_claude.schemas.Schema__Local_Claude__Info             import Schema__Local_Claude__Info
from sg_compute_specs.local_claude.schemas.Schema__Local_Claude__List             import Schema__Local_Claude__List
from sg_compute_specs.local_claude.service.Local_Claude__AMI__Helper              import Local_Claude__AMI__Helper
from sg_compute_specs.local_claude.service.Local_Claude__AWS__Client              import Local_Claude__AWS__Client
from sg_compute_specs.local_claude.service.Local_Claude__Stack__Mapper            import (Local_Claude__Stack__Mapper ,
                                                                                           STACK_TYPE                 ,
                                                                                           TAG_DISK_GB                ,
                                                                                           TAG_MODEL                  ,
                                                                                           TAG_TOOL_PARSER            )
from sg_compute_specs.local_claude.service.Local_Claude__User_Data__Builder       import Local_Claude__User_Data__Builder

DEFAULT_REGION        = os.environ.get('AWS_DEFAULT_REGION', 'eu-west-2')
DEFAULT_INSTANCE_TYPE = 'g5.xlarge'
PROFILE_NAME          = 'playwright-ec2'             # IAM profile granting SSM + ECR access (L4 lesson)

GPU_INSTANCE_PREFIXES = ('g4dn', 'g5', 'g6', 'p3', 'p4', 'p5')


def _is_gpu_instance(instance_type: str) -> bool:
    prefix = instance_type.split('.')[0] if '.' in instance_type else ''
    return any(prefix.startswith(p) for p in GPU_INSTANCE_PREFIXES)


class Local_Claude__Service(Spec__Service__Base):
    aws_client        : Optional[Local_Claude__AWS__Client]        = None
    user_data_builder : Optional[Local_Claude__User_Data__Builder] = None
    mapper            : Optional[Local_Claude__Stack__Mapper]      = None
    ip_detector       : Optional[Caller__IP__Detector]             = None
    name_gen          : Optional[Stack__Name__Generator]           = None
    ami_helper        : Optional[Local_Claude__AMI__Helper]        = None

    def setup(self) -> 'Local_Claude__Service':
        self.aws_client        = Local_Claude__AWS__Client       ().setup()
        self.user_data_builder = Local_Claude__User_Data__Builder()
        self.mapper            = Local_Claude__Stack__Mapper     ()
        self.ip_detector       = Caller__IP__Detector            ()
        self.name_gen          = Stack__Name__Generator          ()
        self.ami_helper        = Local_Claude__AMI__Helper       ()
        return self

    def cli_spec(self):
        from sg_compute.cli.base.Schema__Spec__CLI__Spec import Schema__Spec__CLI__Spec
        return Schema__Spec__CLI__Spec(
            spec_id               = 'local-claude'                              ,
            display_name          = 'Local Claude'                              ,
            default_instance_type = DEFAULT_INSTANCE_TYPE                       ,
            create_request_cls    = Schema__Local_Claude__Create__Request       ,
            service_factory       = lambda: Local_Claude__Service().setup()     ,
            health_path           = '/v1/models'                                ,
            health_port           = 8000                                        ,
            health_scheme         = 'http'                                      ,
        )

    def create_stack(self, request : Schema__Local_Claude__Create__Request,
                           creator : str = '') -> Schema__Local_Claude__Create__Response:
        t0           = time.monotonic()
        stack_name   = str(request.stack_name)    or self.name_gen.generate()
        region       = str(request.region)        or DEFAULT_REGION
        caller_ip    = str(request.caller_ip)     or self.ip_detector.detect()
        if not caller_ip:
            raise ValueError(
                'Could not detect your public IP automatically.\n'
                '  Pass it explicitly: sg local-claude create --caller-ip <your-ip>')
        ami_id       = str(request.from_ami)      or self.ami_helper.resolve_for_base(region, request.ami_base)
        itype        = str(request.instance_type) or DEFAULT_INSTANCE_TYPE
        gpu_required = request.gpu_required and _is_gpu_instance(itype)

        sg_id = self.aws_client.sg.ensure_security_group(
            region, stack_name, caller_ip,
            inbound_ports=[],
            extra_cidrs={})

        disk_gb = int(request.disk_size_gb)
        extra   = {
            TAG_MODEL      : request.model               ,
            TAG_DISK_GB    : str(disk_gb)                ,
            TAG_TOOL_PARSER: request.tool_parser         ,
        }
        tags = self.aws_client.tags.build(stack_name, caller_ip, creator, extra_tags=extra)

        user_data = self.user_data_builder.render(
            stack_name            = stack_name                      ,
            region                = region                         ,
            model                 = request.model                  ,
            served_model_name     = request.served_model_name      ,
            tool_parser           = request.tool_parser            ,
            max_model_len         = request.max_model_len          ,
            kv_cache_dtype        = request.kv_cache_dtype         ,
            gpu_memory_utilization= request.gpu_memory_utilization ,
            max_hours             = request.max_hours              ,
            gpu_required          = gpu_required                   ,
            with_claude_code      = request.with_claude_code       ,
            with_sgit             = request.with_sgit              ,
        )
        iid = self.aws_client.launch.run_instance(
            region                = region              ,
            ami_id                = ami_id              ,
            sg_id                 = sg_id               ,
            user_data             = user_data           ,
            tags                  = tags                ,
            instance_type         = itype               ,
            max_hours             = request.max_hours   ,
            instance_profile_name = PROFILE_NAME        ,
            disk_size_gb          = disk_gb             ,
            use_spot              = bool(request.use_spot) ,
        )
        info = Schema__Local_Claude__Info(
            instance_id       = iid                          ,
            stack_name        = stack_name                   ,
            region            = region                       ,
            ami_id            = ami_id                       ,
            instance_type     = itype                        ,
            security_group_id = sg_id                        ,
            model_name        = request.model                ,
            tool_parser       = request.tool_parser          ,
            state             = 'pending'                    ,
        )
        return Schema__Local_Claude__Create__Response(
            stack_info = info                                 ,
            message    = f'Instance {iid} launching'         ,
            elapsed_ms = int((time.monotonic() - t0) * 1000) ,
        )

    def list_stacks(self, region: str = '') -> Schema__Local_Claude__List:
        region = region or DEFAULT_REGION
        raw    = self.aws_client.instance.list_by_stack_type(region, STACK_TYPE)
        stacks = [self.mapper.to_info(d, region) for d in raw.values()]
        return Schema__Local_Claude__List(region=region, stacks=stacks, total=len(stacks))

    def get_stack_info(self, region: str, stack_name: str):
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        return self.mapper.to_info(details, region) if details else None

    def delete_stack(self, region: str, stack_name: str) -> Schema__Local_Claude__Delete__Response:
        t0      = time.monotonic()
        details = self.aws_client.instance.find_by_stack_name(region, stack_name)
        if not details:
            return Schema__Local_Claude__Delete__Response(
                stack_name = stack_name       ,
                message    = 'stack not found',
                elapsed_ms = int((time.monotonic() - t0) * 1000))
        iid   = details.get('InstanceId', '')
        sg_id = (details.get('SecurityGroups') or [{}])[0].get('GroupId', '')
        ok    = self.aws_client.instance.terminate(region, iid)
        if ok and sg_id:
            self.aws_client.sg.delete_security_group(region, sg_id)
        return Schema__Local_Claude__Delete__Response(
            stack_name = stack_name                                         ,
            deleted    = ok                                                 ,
            message    = f'terminated {iid}' if ok else 'terminate failed' ,
            elapsed_ms = int((time.monotonic() - t0) * 1000)               ,
        )

    # ── health: vLLM binds to 127.0.0.1 — cannot be reached via public IP.
    #    Use SSM exec to probe from inside the instance instead. ────────────

    def health(self, region: str, name: str, timeout_sec: int = 0, poll_sec: int = 10):
        from sg_compute.cli.base.schemas.Schema__CLI__Health__Probe import Schema__CLI__Health__Probe
        t0       = time.monotonic()
        probe    = Schema__CLI__Health__Probe()
        deadline = time.monotonic() + max(timeout_sec, 0)
        while True:
            # Fail-fast: bail out if the boot script wrote the failure marker.
            try:
                marker = self.exec(region, name,
                                   'test -f /var/lib/sg-compute-boot-failed && '
                                   'tail -n 30 /var/log/ephemeral-ec2-boot.log || true',
                                   timeout_sec=10)
                tail = str(getattr(marker, 'stdout', '') or '').strip()
                if tail:
                    probe.healthy    = False
                    probe.state      = 'failed'
                    probe.last_error = tail[:1500]
                    break
            except Exception:
                pass
            try:
                result = self.exec(region, name,
                                   'curl -sf http://127.0.0.1:8000/v1/models',
                                   timeout_sec=10)
                stdout = str(getattr(result, 'stdout', '') or '')
                if '"data"' in stdout or stdout.strip().startswith('{'):
                    probe.healthy    = True
                    probe.state      = 'running'
                    probe.last_error = ''
                    break
                probe.state      = 'starting'
                probe.last_error = (stdout[:256] if stdout else 'empty response from vLLM')
            except Exception as exc:
                probe.state      = 'starting'
                probe.last_error = str(exc)[:512]
            if time.monotonic() >= deadline:
                break
            time.sleep(poll_sec)
        probe.elapsed_ms = int((time.monotonic() - t0) * 1000)
        return probe

    # ── boot-sequence diagnostic checklist ───────────────────────────────────────
    # Generator protocol: for each active check, yields (name, 'checking', '')
    # first so the CLI can show a live "checking…" indicator, then yields the
    # final (name, status, detail) tuple once the check completes.
    # Skipped checks are yielded directly (no 'checking' prefix — nothing runs).
    # On failures, 'detail' includes enough context to diagnose without SSM.

    def diagnose(self, region: str, name: str):
        # ── check 1: ec2-state ─────────────────────────────────────────────────
        yield ('ec2-state', 'checking', '')
        info      = self.get_stack_info(region, name)
        if info is None:
            yield ('ec2-state', 'fail', 'stack not found')
            return
        ec2_state = str(getattr(info, 'state', '') or '')
        ec2_ok    = ec2_state == 'running'
        yield ('ec2-state', 'ok' if ec2_ok else 'fail', ec2_state or '?')
        if not ec2_ok:
            skip_msg = f'skipped — ec2 is {ec2_state!r}'
            for n in ('ssm-reachable', 'boot-failed', 'boot-ok',
                      'docker', 'docker-access', 'gpu', 'vllm-container', 'vllm-api'):
                yield (n, 'skip', skip_msg)
            return

        # ── check 2: ssm-reachable ─────────────────────────────────────────────
        yield ('ssm-reachable', 'checking', '')
        try:
            self.exec(region, name, 'echo ok', timeout_sec=15)
            ssm_ok = True
            yield ('ssm-reachable', 'ok', 'responsive')
        except Exception as exc:
            ssm_ok = False
            yield ('ssm-reachable', 'fail', str(exc)[:120])
        if not ssm_ok:
            for n in ('boot-failed', 'boot-ok', 'docker', 'docker-access',
                      'gpu', 'vllm-container', 'vllm-api'):
                yield (n, 'skip', 'skipped — SSM unreachable')
            return

        def ssm(cmd, timeout=12):
            r = self.exec(region, name, cmd, timeout_sec=timeout)
            return str(getattr(r, 'stdout', '') or '').strip()

        # ── check 3: boot-failed ───────────────────────────────────────────────
        yield ('boot-failed', 'checking', '')
        try:
            out = ssm('test -f /var/lib/sg-compute-boot-failed && echo YES || echo NO')
            if 'YES' in out:
                tail = ssm('tail -n 15 /var/log/ephemeral-ec2-boot.log 2>/dev/null || true')
                detail = 'boot script error:\n' + tail if tail else 'boot script error'
                yield ('boot-failed', 'fail', detail)
            else:
                yield ('boot-failed', 'ok', 'absent')
        except Exception:
            yield ('boot-failed', 'warn', 'could not check')

        # ── check 4: boot-ok ──────────────────────────────────────────────────
        boot_ok = False
        yield ('boot-ok', 'checking', '')
        try:
            out = ssm('test -f /var/lib/sg-compute-boot-ok && echo YES || echo NO')
            if 'YES' in out:
                boot_ok = True
                yield ('boot-ok', 'ok', 'present')
            else:
                tail = ssm('tail -n 5 /var/log/ephemeral-ec2-boot.log 2>/dev/null || echo "(log not yet available)"')
                yield ('boot-ok', 'warn', f'not yet — last log: {tail[:120]}')
        except Exception:
            yield ('boot-ok', 'warn', 'could not check')

        # ── check 5: docker ───────────────────────────────────────────────────
        yield ('docker', 'checking', '')
        try:
            out = ssm('systemctl is-active docker 2>&1 || true')
            if out == 'active':
                yield ('docker', 'ok', 'active')
            else:
                journal = ssm('journalctl -u docker -n 5 --no-pager 2>/dev/null || true')
                yield ('docker', 'fail', f'state={out!r}  last journal: {journal[:200]}')
        except Exception:
            yield ('docker', 'warn', 'could not check')

        # ── check 6: docker-access ─────────────────────────────────────────────
        yield ('docker-access', 'checking', '')
        try:
            out = ssm('sudo -u ssm-user docker info >/dev/null 2>&1 && echo OK || echo DENIED')
            if 'OK' in out:
                yield ('docker-access', 'ok', 'ssm-user can use docker')
            else:
                groups = ssm('id ssm-user 2>/dev/null || echo "(ssm-user not found)"')
                if 'not found' in groups:
                    if not boot_ok:
                        yield ('docker-access', 'warn', 'not yet — ssm-user not created by SSM agent yet (boot in progress)')
                    else:
                        yield ('docker-access', 'warn', 'ssm-user missing after boot — unexpected; check cloud-init')
                else:
                    yield ('docker-access', 'warn',
                           f'permission denied — ssm-user groups: {groups[:120]}\n'
                           '  fix: reconnect your SSM session (group change takes effect on new login)')
        except Exception:
            yield ('docker-access', 'warn', 'could not check')

        # ── check 7: gpu ──────────────────────────────────────────────────────
        yield ('gpu', 'checking', '')
        try:
            out = ssm('nvidia-smi --query-gpu=name --format=csv,noheader 2>&1 | head -1 || echo MISSING')
            if out and 'MISSING' not in out and 'not found' not in out.lower():
                yield ('gpu', 'ok', out)
            else:
                driver = ssm('modinfo nvidia 2>&1 | head -2 || echo "(kernel module not loaded)"')
                yield ('gpu', 'fail', f'nvidia-smi not found — {driver[:120]}')
        except Exception:
            yield ('gpu', 'warn', 'could not check')

        # ── check 8: vllm-container ───────────────────────────────────────────
        yield ('vllm-container', 'checking', '')
        container_ok = False
        try:
            out = ssm('sudo docker ps --filter name=vllm-claude-code --format "{{.Status}}" 2>&1 || true')
            if out and 'Up' in out:
                container_ok = True
                yield ('vllm-container', 'ok', out)
            elif not boot_ok:
                yield ('vllm-container', 'warn', 'not yet — boot still in progress (docker pull pending)')
            else:
                all_ct = ssm('sudo docker ps -a --format "{{.Names}}  {{.Status}}" 2>&1 | head -5 || true')
                detail = f'not running — all containers: {all_ct}' if all_ct else 'no container named vllm-claude-code'
                yield ('vllm-container', 'fail', detail)
        except Exception:
            yield ('vllm-container', 'warn', 'could not check')

        # ── check 9: vllm-api ─────────────────────────────────────────────────
        if not container_ok:
            yield ('vllm-api', 'skip', 'skipped — container not running')
        else:
            yield ('vllm-api', 'checking', '')
            try:
                out = ssm('curl -sf http://127.0.0.1:8000/v1/models 2>&1 | head -c 200 || echo FAIL', timeout=15)
                if '"data"' in out or out.startswith('{'):
                    yield ('vllm-api', 'ok', 'responding')
                else:
                    yield ('vllm-api', 'fail', out[:120] if out else 'no response')
            except Exception as exc:
                yield ('vllm-api', 'fail', str(exc)[:120])

    # ── local-claude-specific extras ─────────────────────────────────────────

    def claude_session(self, region: str, name: str) -> str:
        return self.connect_target(region, name)

    def create_node(self, base_request, api_key_ssm_path=None) -> 'Schema__Node__Info':
        from sg_compute.core.node.schemas.Schema__Node__Info import Schema__Node__Info
        from sg_compute.primitives.enums.Enum__Node__State   import Enum__Node__State
        lc_req = Schema__Local_Claude__Create__Request(
            stack_name    = str(base_request.node_name)     ,
            region        = str(base_request.region)        ,
            instance_type = str(base_request.instance_type) ,
            from_ami      = str(base_request.ami_id)        ,
            caller_ip     = str(base_request.caller_ip)     ,
            max_hours     = float(base_request.max_hours)   ,
        )
        resp = self.create_stack(lc_req)
        info = resp.stack_info
        return Schema__Node__Info(
            node_id       = str(info.stack_name)      ,
            spec_id       = 'local-claude'            ,
            region        = str(base_request.region)  ,
            state         = Enum__Node__State.BOOTING ,
            instance_id   = str(info.instance_id)     ,
            instance_type = str(info.instance_type)   ,
        )
