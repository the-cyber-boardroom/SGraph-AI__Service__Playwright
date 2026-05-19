# ═══════════════════════════════════════════════════════════════════════════════
# tests/unit — test_Vault_App__Fargate__Setup
# Covers Vault_App__Fargate__Setup: all six phases × four ops (check/create/
# update/delete), idempotency (second-create → SKIPPED), error-stop, reverse
# delete order, and full happy-path runs.
#
# No mocks.  No patches.  In-memory clients injected via _make_setup().
# ═══════════════════════════════════════════════════════════════════════════════

from unittest import TestCase

from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Phase__Status         import Enum__VAF__Phase__Status
from sg_compute_specs.vault_app.fargate.enums.Enum__VAF__Setup__Phase          import Enum__VAF__Setup__Phase
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Setup__Report     import Schema__VAF__Setup__Report
from sg_compute_specs.vault_app.fargate.schemas.Schema__VAF__Setup__Request    import Schema__VAF__Setup__Request
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Image__Mirror import Vault_App__Fargate__Image__Mirror
from sg_compute_specs.vault_app.fargate.service.Vault_App__Fargate__Setup      import Vault_App__Fargate__Setup

from tests.unit.sgraph_ai_service_playwright__cli.aws.ecr.service.ECR__AWS__Client__In_Memory     import ECR__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.fargate.service.Fargate__AWS__Client__In_Memory import Fargate__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.iam.service.IAM__AWS__Client__In_Memory    import IAM__AWS__Client__In_Memory
from tests.unit.sgraph_ai_service_playwright__cli.aws.logs.service.Logs__AWS__Client__In_Memory  import Logs__AWS__Client__In_Memory


# ── factory helper ────────────────────────────────────────────────────────────

def _make_setup(ecr=None, logs=None, fargate=None, iam=None,
                image_runner=None) -> Vault_App__Fargate__Setup:
    ecr_client     = ecr     if ecr     is not None else ECR__AWS__Client__In_Memory()
    logs_client    = logs    if logs    is not None else Logs__AWS__Client__In_Memory()
    fargate_client = fargate if fargate is not None else Fargate__AWS__Client__In_Memory()
    iam_client     = iam     if iam     is not None else IAM__AWS__Client__In_Memory()

    mirror = Vault_App__Fargate__Image__Mirror()
    if image_runner is not None:
        mirror._runner = image_runner

    return Vault_App__Fargate__Setup(
        ecr_client     = ecr_client,
        fargate_client = fargate_client,
        logs_client    = logs_client,
        iam_client     = iam_client,
        image_mirror   = mirror,
    )


def _base_request(**kwargs) -> Schema__VAF__Setup__Request:
    defaults = dict(
        cluster_name  = 'test-cluster',
        ecr_repo_name = 'sg-send-vault',
        log_group     = '/ecs/vault-app',
        region        = 'us-east-1',
        subnets       = 'subnet-aaa',
        security_group= 'sg-xxx',
    )
    defaults.update(kwargs)
    return Schema__VAF__Setup__Request(**defaults)


def _ok_runner(cmd: list) -> tuple:                                              # succeeds for all docker commands
    if 'inspect' in cmd:
        return (0, 'sha256:abc123deadbeef', '')
    return (0, '', '')


def _fail_runner(cmd: list) -> tuple:                                            # fails on docker pull
    if 'pull' in cmd:
        return (1, '', 'pull failed: network error')
    return (0, '', '')


# ══════════════════════════════════════════════════════════════════════════════
# ECR phase
# ══════════════════════════════════════════════════════════════════════════════

class Test__VAF__Setup__ECR(TestCase):

    # ── check ─────────────────────────────────────────────────────────────────

    def test_check_missing_repo_detail_is_missing(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.ECR])
        report = setup.check(req)
        result = report.phases[0]
        assert result.detail == 'missing'

    def test_check_existing_repo_detail_is_exists(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup  = _make_setup(ecr=ecr)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.ECR])
        report = setup.check(req)
        result = report.phases[0]
        assert result.detail == 'exists'

    def test_check_status_is_ok(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.ECR])
        report = setup.check(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_new_repo_status_ok(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.ECR])
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_create_new_repo_detail_contains_created(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.ECR])
        report = setup.create(req)
        assert 'created' in report.phases[0].detail

    def test_create_repo_exists_in_ecr_after_create(self):
        ecr   = ECR__AWS__Client__In_Memory()
        setup = _make_setup(ecr=ecr)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.ECR])
        setup.create(req)
        assert ecr.describe_repository('sg-send-vault') is not None

    # ── create idempotent ─────────────────────────────────────────────────────

    def test_create_idempotent_second_call_status_skipped(self):
        ecr   = ECR__AWS__Client__In_Memory()
        setup = _make_setup(ecr=ecr)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.ECR])
        setup.create(req)                                                        # first call creates repo
        report = setup.create(req)                                               # second call — same ecr instance
        assert report.phases[0].status == Enum__VAF__Phase__Status.SKIPPED

    def test_create_idempotent_second_call_detail_already_exists(self):
        ecr   = ECR__AWS__Client__In_Memory()
        setup = _make_setup(ecr=ecr)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.ECR])
        setup.create(req)
        report = setup.create(req)
        assert report.phases[0].detail == 'already exists'

    # ── delete ────────────────────────────────────────────────────────────────

    def test_delete_existing_repo_status_ok(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup  = _make_setup(ecr=ecr)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.ECR])
        report = setup.delete(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_delete_missing_repo_status_skipped(self):
        ecr   = ECR__AWS__Client__In_Memory()
        setup = _make_setup(ecr=ecr)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.ECR])
        report = setup.delete(req)                                               # nothing to delete
        assert report.phases[0].status == Enum__VAF__Phase__Status.SKIPPED

    def test_delete_removes_repo_from_ecr(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup = _make_setup(ecr=ecr)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.ECR])
        setup.delete(req)
        assert ecr.describe_repository('sg-send-vault') is None


# ══════════════════════════════════════════════════════════════════════════════
# IAM phase
# ══════════════════════════════════════════════════════════════════════════════

class Test__VAF__Setup__IAM(TestCase):

    # ── check ─────────────────────────────────────────────────────────────────

    def test_check_missing_role_detail_is_missing(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IAM])
        report = setup.check(req)
        assert report.phases[0].detail == 'missing'

    def test_check_existing_role_detail_is_exists(self):
        iam = IAM__AWS__Client__In_Memory()
        from sgraph_ai_service_playwright__cli.aws.iam.enums.Enum__IAM__Trust__Service      import Enum__IAM__Trust__Service
        from sgraph_ai_service_playwright__cli.aws.iam.schemas.Schema__IAM__Role__Create__Request import Schema__IAM__Role__Create__Request
        iam.create_role(Schema__IAM__Role__Create__Request(
            role_name     = 'vault-app-fargate-execution',
            trust_service = Enum__IAM__Trust__Service.ECS_TASKS,
        ))
        setup  = _make_setup(iam=iam)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IAM])
        report = setup.check(req)
        assert report.phases[0].detail == 'exists'

    def test_check_status_ok(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IAM])
        report = setup.check(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_role_status_ok(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IAM])
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_create_role_detail_contains_created(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IAM])
        report = setup.create(req)
        assert 'created' in report.phases[0].detail

    def test_create_role_exists_in_iam_after_create(self):
        iam   = IAM__AWS__Client__In_Memory()
        setup = _make_setup(iam=iam)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.IAM])
        setup.create(req)
        assert iam.role_exists('vault-app-fargate-execution')

    # ── create idempotent ─────────────────────────────────────────────────────

    def test_create_idempotent_second_call_status_skipped(self):
        iam   = IAM__AWS__Client__In_Memory()
        setup = _make_setup(iam=iam)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.IAM])
        setup.create(req)
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.SKIPPED

    def test_create_idempotent_second_call_detail_already_exists(self):
        iam   = IAM__AWS__Client__In_Memory()
        setup = _make_setup(iam=iam)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.IAM])
        setup.create(req)
        report = setup.create(req)
        assert report.phases[0].detail == 'already exists'

    # ── delete ────────────────────────────────────────────────────────────────

    def test_delete_existing_role_status_ok(self):
        iam   = IAM__AWS__Client__In_Memory()
        setup = _make_setup(iam=iam)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.IAM])
        setup.create(req)                                                        # create first
        report = setup.delete(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_delete_missing_role_status_skipped(self):
        iam   = IAM__AWS__Client__In_Memory()
        setup = _make_setup(iam=iam)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.IAM])
        report = setup.delete(req)                                               # nothing to delete
        assert report.phases[0].status == Enum__VAF__Phase__Status.SKIPPED

    def test_no_iam_client_skips_phase(self):
        setup = Vault_App__Fargate__Setup(                                       # no iam_client
            ecr_client     = ECR__AWS__Client__In_Memory(),
            fargate_client = Fargate__AWS__Client__In_Memory(),
            logs_client    = Logs__AWS__Client__In_Memory(),
        )
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.IAM])
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.SKIPPED


# ══════════════════════════════════════════════════════════════════════════════
# LOGS phase
# ══════════════════════════════════════════════════════════════════════════════

class Test__VAF__Setup__LOGS(TestCase):

    # ── check ─────────────────────────────────────────────────────────────────

    def test_check_missing_group_detail_is_missing(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        report = setup.check(req)
        assert report.phases[0].detail == 'missing'

    def test_check_existing_group_detail_is_exists(self):
        logs = Logs__AWS__Client__In_Memory()
        logs.seed_group('/ecs/vault-app')
        setup  = _make_setup(logs=logs)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        report = setup.check(req)
        assert report.phases[0].detail == 'exists'

    def test_check_status_ok(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        report = setup.check(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_log_group_status_ok(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_create_log_group_detail_contains_created(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        report = setup.create(req)
        assert 'created' in report.phases[0].detail

    def test_create_log_group_exists_after_create(self):
        logs  = Logs__AWS__Client__In_Memory()
        setup = _make_setup(logs=logs)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        setup.create(req)
        assert logs.describe_log_group('/ecs/vault-app') is not None

    # ── create idempotent ─────────────────────────────────────────────────────

    def test_create_idempotent_second_call_status_skipped(self):
        logs  = Logs__AWS__Client__In_Memory()
        setup = _make_setup(logs=logs)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        setup.create(req)
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.SKIPPED

    def test_create_idempotent_second_call_detail_already_exists(self):
        logs  = Logs__AWS__Client__In_Memory()
        setup = _make_setup(logs=logs)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        setup.create(req)
        report = setup.create(req)
        assert report.phases[0].detail == 'already exists'

    # ── update ────────────────────────────────────────────────────────────────

    def test_update_existing_group_status_ok(self):
        logs = Logs__AWS__Client__In_Memory()
        logs.seed_group('/ecs/vault-app')
        setup  = _make_setup(logs=logs)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        report = setup.update(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_update_retention_policy_is_set(self):
        logs = Logs__AWS__Client__In_Memory()
        logs.seed_group('/ecs/vault-app', retention_days=0)             # no retention initially
        setup = _make_setup(logs=logs)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        setup.update(req)
        group = logs.describe_log_group('/ecs/vault-app')
        assert group.retention_days == 7

    # ── delete ────────────────────────────────────────────────────────────────

    def test_delete_existing_group_status_ok(self):
        logs = Logs__AWS__Client__In_Memory()
        logs.seed_group('/ecs/vault-app')
        setup  = _make_setup(logs=logs)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        report = setup.delete(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_delete_missing_group_status_skipped(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        report = setup.delete(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.SKIPPED

    def test_delete_removes_group(self):
        logs = Logs__AWS__Client__In_Memory()
        logs.seed_group('/ecs/vault-app')
        setup = _make_setup(logs=logs)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.LOGS])
        setup.delete(req)
        assert logs.describe_log_group('/ecs/vault-app') is None


# ══════════════════════════════════════════════════════════════════════════════
# CLUSTER phase
# ══════════════════════════════════════════════════════════════════════════════

class Test__VAF__Setup__CLUSTER(TestCase):

    # ── check ─────────────────────────────────────────────────────────────────

    def test_check_missing_cluster_detail_is_missing(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        report = setup.check(req)
        assert report.phases[0].detail == 'missing'

    def test_check_existing_cluster_detail_is_active(self):
        fargate = Fargate__AWS__Client__In_Memory()
        fargate.seed_cluster_with_tags('test-cluster', {})
        setup  = _make_setup(fargate=fargate)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        report = setup.check(req)
        assert report.phases[0].detail == 'active'

    def test_check_status_ok(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        report = setup.check(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_cluster_status_ok(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_create_cluster_detail_contains_created(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        report = setup.create(req)
        assert 'created' in report.phases[0].detail

    def test_create_cluster_exists_after_create(self):
        fargate = Fargate__AWS__Client__In_Memory()
        setup   = _make_setup(fargate=fargate)
        req     = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        setup.create(req)
        assert fargate.describe_cluster('test-cluster') is not None

    def test_create_cluster_has_stack_tag(self):
        fargate = Fargate__AWS__Client__In_Memory()
        setup   = _make_setup(fargate=fargate)
        req     = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        setup.create(req)
        cluster = fargate.describe_cluster('test-cluster')
        assert cluster.tags.get('Stack') == 'sg-vault-app-fargate'

    # ── create idempotent ─────────────────────────────────────────────────────

    def test_create_idempotent_second_call_status_skipped(self):
        fargate = Fargate__AWS__Client__In_Memory()
        setup   = _make_setup(fargate=fargate)
        req     = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        setup.create(req)
        report  = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.SKIPPED

    def test_create_idempotent_second_call_detail_already_exists(self):
        fargate = Fargate__AWS__Client__In_Memory()
        setup   = _make_setup(fargate=fargate)
        req     = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        setup.create(req)
        report  = setup.create(req)
        assert report.phases[0].detail == 'already exists'

    # ── delete ────────────────────────────────────────────────────────────────

    def test_delete_existing_cluster_status_ok(self):
        fargate = Fargate__AWS__Client__In_Memory()
        fargate.seed_cluster_with_tags('test-cluster', {})
        setup  = _make_setup(fargate=fargate)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        report = setup.delete(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_delete_missing_cluster_status_skipped(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        report = setup.delete(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.SKIPPED

    def test_delete_removes_cluster(self):
        fargate = Fargate__AWS__Client__In_Memory()
        fargate.seed_cluster_with_tags('test-cluster', {})
        setup   = _make_setup(fargate=fargate)
        req     = _base_request(phases=[Enum__VAF__Setup__Phase.CLUSTER])
        setup.delete(req)
        assert fargate.describe_cluster('test-cluster') is None


# ══════════════════════════════════════════════════════════════════════════════
# IMAGE_MIRROR phase
# ══════════════════════════════════════════════════════════════════════════════

class Test__VAF__Setup__IMAGE_MIRROR(TestCase):

    # ── check ─────────────────────────────────────────────────────────────────

    def test_check_no_images_detail_no_images(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup  = _make_setup(ecr=ecr)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IMAGE_MIRROR])
        report = setup.check(req)
        assert report.phases[0].detail == 'no images'

    def test_check_with_images_detail_images_present(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        ecr.seed_image('sg-send-vault', tags=['latest'])
        setup  = _make_setup(ecr=ecr)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IMAGE_MIRROR])
        report = setup.check(req)
        assert report.phases[0].detail == 'images present'

    def test_check_status_ok(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup  = _make_setup(ecr=ecr)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IMAGE_MIRROR])
        report = setup.check(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_check_no_ecr_client_status_skipped(self):
        setup             = _make_setup()
        setup.ecr_client  = None
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IMAGE_MIRROR])
        report = setup.check(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.SKIPPED

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_mirror_success_status_ok(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup  = _make_setup(ecr=ecr, image_runner=_ok_runner)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IMAGE_MIRROR])
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_create_mirror_success_detail_contains_sha(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup  = _make_setup(ecr=ecr, image_runner=_ok_runner)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IMAGE_MIRROR])
        report = setup.create(req)
        assert 'sha=' in report.phases[0].detail

    def test_create_mirror_failure_status_error(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup  = _make_setup(ecr=ecr, image_runner=_fail_runner)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IMAGE_MIRROR])
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.ERROR

    def test_create_no_ecr_uri_status_error(self):
        # ecr_client present but repo doesn't exist → ecr_uri empty → ERROR
        ecr   = ECR__AWS__Client__In_Memory()                                   # empty — repo not seeded
        setup = _make_setup(ecr=ecr, image_runner=_ok_runner)
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.IMAGE_MIRROR])
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.ERROR

    # ── delete skipped ────────────────────────────────────────────────────────

    def test_delete_image_mirror_is_always_skipped(self):
        setup  = _make_setup(image_runner=_ok_runner)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IMAGE_MIRROR])
        report = setup.delete(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.SKIPPED

    # ── update re-mirrors ─────────────────────────────────────────────────────

    def test_update_mirror_success_status_ok(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup  = _make_setup(ecr=ecr, image_runner=_ok_runner)
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.IMAGE_MIRROR])
        report = setup.update(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK


# ══════════════════════════════════════════════════════════════════════════════
# TASK_DEF phase
# ══════════════════════════════════════════════════════════════════════════════

class Test__VAF__Setup__TASK_DEF(TestCase):

    # ── check ─────────────────────────────────────────────────────────────────

    def test_check_missing_task_def_detail_is_missing(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.TASK_DEF])
        report = setup.check(req)
        assert report.phases[0].detail == 'missing'

    def test_check_existing_task_def_detail_has_revision(self):
        fargate = Fargate__AWS__Client__In_Memory()
        setup   = _make_setup(fargate=fargate)
        req     = _base_request(phases=[Enum__VAF__Setup__Phase.TASK_DEF])
        setup.create(req)                                                        # register task def first
        report  = setup.check(req)
        assert 'revision' in report.phases[0].detail

    def test_check_status_ok(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.TASK_DEF])
        report = setup.check(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    # ── create ────────────────────────────────────────────────────────────────

    def test_create_task_def_status_ok(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.TASK_DEF])
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK

    def test_create_task_def_detail_has_revision(self):
        setup  = _make_setup()
        req    = _base_request(phases=[Enum__VAF__Setup__Phase.TASK_DEF])
        report = setup.create(req)
        assert 'revision' in report.phases[0].detail

    def test_create_task_def_exists_after_create(self):
        fargate = Fargate__AWS__Client__In_Memory()
        setup   = _make_setup(fargate=fargate)
        req     = _base_request(phases=[Enum__VAF__Setup__Phase.TASK_DEF])
        setup.create(req)
        td = fargate.describe_task_definition('test-cluster')
        assert td is not None

    def test_create_task_def_uses_spec_ports(self):
        fargate = Fargate__AWS__Client__In_Memory()
        ecr     = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup   = _make_setup(fargate=fargate, ecr=ecr)
        req     = _base_request(phases=[Enum__VAF__Setup__Phase.TASK_DEF])
        setup.create(req)
        td = fargate.describe_task_definition('test-cluster')
        assert td.port_mappings is not None

    # ── create idempotent (registers new revision) ────────────────────────────

    def test_create_second_call_registers_new_revision(self):
        fargate = Fargate__AWS__Client__In_Memory()
        setup   = _make_setup(fargate=fargate)
        req     = _base_request(phases=[Enum__VAF__Setup__Phase.TASK_DEF])
        setup.create(req)
        setup.create(req)
        all_tds = fargate.list_task_definitions(family='test-cluster')
        assert len(all_tds) == 2

    def test_create_second_call_status_ok(self):
        setup = _make_setup()
        req   = _base_request(phases=[Enum__VAF__Setup__Phase.TASK_DEF])
        setup.create(req)
        report = setup.create(req)
        assert report.phases[0].status == Enum__VAF__Phase__Status.OK


# ══════════════════════════════════════════════════════════════════════════════
# Full orchestration
# ══════════════════════════════════════════════════════════════════════════════

class Test__VAF__Setup__Full(TestCase):

    def _full_setup(self, image_runner=None) -> Vault_App__Fargate__Setup:
        return _make_setup(image_runner=image_runner or _ok_runner)

    def _full_request(self, **kwargs) -> Schema__VAF__Setup__Request:
        return _base_request(**kwargs)

    # ── report shape ─────────────────────────────────────────────────────────

    def test_create_all_returns_report_type(self):
        setup  = self._full_setup()
        req    = self._full_request()
        report = setup.create(req)
        assert isinstance(report, Schema__VAF__Setup__Report)

    def test_create_all_report_has_six_phase_results(self):
        setup  = self._full_setup()
        req    = self._full_request()
        report = setup.create(req)
        assert len(report.phases) == 6

    def test_create_all_ok_is_true(self):
        setup  = self._full_setup()
        req    = self._full_request()
        report = setup.create(req)
        assert report.ok is True

    def test_create_all_total_ms_non_negative(self):
        setup  = self._full_setup()
        req    = self._full_request()
        report = setup.create(req)
        assert report.total_ms >= 0

    def test_create_all_operation_is_create(self):
        setup  = self._full_setup()
        req    = self._full_request()
        report = setup.create(req)
        assert report.operation == 'create'

    def test_create_all_cluster_name_in_report(self):
        setup  = self._full_setup()
        req    = self._full_request()
        report = setup.create(req)
        assert report.cluster_name == 'test-cluster'

    def test_create_all_phase_names_match_enum_order(self):
        setup  = self._full_setup()
        req    = self._full_request()
        report = setup.create(req)
        expected = [p.value for p in Enum__VAF__Setup__Phase]
        actual   = [r.name for r in report.phases]
        assert actual == expected

    # ── check all ─────────────────────────────────────────────────────────────

    def test_check_all_returns_six_results(self):
        setup  = self._full_setup()
        req    = self._full_request()
        report = setup.check(req)
        assert len(report.phases) == 6

    def test_check_all_operation_is_check(self):
        setup  = self._full_setup()
        req    = self._full_request()
        report = setup.check(req)
        assert report.operation == 'check'

    def test_check_all_never_stops_on_error(self):
        # image mirror will fail (no ECR repo + ok runner), but check should still return all 6 phases
        setup             = self._full_setup()
        setup.ecr_client  = None
        req    = self._full_request()
        report = setup.check(req)
        assert len(report.phases) == 6

    # ── error stops chain ────────────────────────────────────────────────────

    def test_create_stops_at_first_error_by_default(self):
        # fail on IMAGE_MIRROR — phases after it should not run
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup  = _make_setup(ecr=ecr, image_runner=_fail_runner)
        req    = self._full_request()
        report = setup.create(req)
        # IMAGE_MIRROR is phase 5 (index 4) — TASK_DEF should not be present
        phase_names = [r.name for r in report.phases]
        assert Enum__VAF__Setup__Phase.TASK_DEF.value not in phase_names

    def test_create_continue_on_error_runs_all_phases(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup  = _make_setup(ecr=ecr, image_runner=_fail_runner)
        req    = self._full_request(continue_on_error=True)
        report = setup.create(req)
        assert len(report.phases) == 6

    def test_create_continue_on_error_ok_is_false(self):
        ecr = ECR__AWS__Client__In_Memory()
        ecr.seed_repo('sg-send-vault')
        setup  = _make_setup(ecr=ecr, image_runner=_fail_runner)
        req    = self._full_request(continue_on_error=True)
        report = setup.create(req)
        assert report.ok is False

    # ── delete reverses phase order ───────────────────────────────────────────

    def test_delete_all_runs_phases_in_reverse(self):
        setup  = self._full_setup()
        req    = self._full_request()
        setup.create(req)                                                        # create first
        report = setup.delete(req)
        expected_names = [p.value for p in reversed(list(Enum__VAF__Setup__Phase))]
        actual_names   = [r.name for r in report.phases]
        assert actual_names == expected_names

    def test_delete_all_operation_is_delete(self):
        setup  = self._full_setup()
        req    = self._full_request()
        report = setup.delete(req)
        assert report.operation == 'delete'

    def test_delete_ecr_phase_appears_last(self):
        setup  = self._full_setup()
        req    = self._full_request()
        report = setup.delete(req)
        assert report.phases[-1].name == Enum__VAF__Setup__Phase.ECR.value

    # ── idempotent full create ────────────────────────────────────────────────

    def test_second_create_all_ok_is_true(self):
        setup  = self._full_setup()
        req    = self._full_request()
        setup.create(req)
        report = setup.create(req)
        assert report.ok is True

    def test_second_create_all_phases_skipped_or_ok(self):
        setup  = self._full_setup()
        req    = self._full_request()
        setup.create(req)
        report = setup.create(req)
        for r in report.phases:
            assert r.status in (Enum__VAF__Phase__Status.OK,
                                Enum__VAF__Phase__Status.SKIPPED)

    # ── phase subset ─────────────────────────────────────────────────────────

    def test_create_subset_phases_only_runs_those(self):
        setup  = self._full_setup()
        req    = self._full_request(phases=[Enum__VAF__Setup__Phase.ECR,
                                            Enum__VAF__Setup__Phase.LOGS])
        report = setup.create(req)
        assert len(report.phases) == 2
        assert report.phases[0].name == Enum__VAF__Setup__Phase.ECR.value
        assert report.phases[1].name == Enum__VAF__Setup__Phase.LOGS.value

    # ── progress callback ─────────────────────────────────────────────────────

    def test_progress_cb_called_for_each_phase(self):
        calls  = []
        setup  = self._full_setup()
        setup.progress_cb = lambda name, status, detail='': calls.append((name, status))
        req    = self._full_request()
        setup.create(req)
        phase_names_called = {name for name, _ in calls}
        for phase in Enum__VAF__Setup__Phase:
            assert phase.value in phase_names_called

    # ── default cluster name ──────────────────────────────────────────────────

    def test_empty_cluster_name_uses_spec_default(self):
        setup  = self._full_setup()
        req    = self._full_request(cluster_name='')
        report = setup.create(req)
        assert report.cluster_name == 'vault-app'                                # spec.default_cluster
