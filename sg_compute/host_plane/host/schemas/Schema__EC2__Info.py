# ═══════════════════════════════════════════════════════════════════════════════
# Host Control Plane — Schema__EC2__Info
# Returned by GET /host/ec2-info. Populated via boto3 + IMDS on the host.
# All fields are plain strings/lists/dicts so they serialise cleanly.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class Schema__EC2__Info(Type_Safe):
    instance_id       : str  = ''
    instance_type     : str  = ''
    region            : str  = ''
    availability_zone : str  = ''
    ami_id            : str  = ''
    launch_time       : str  = ''
    state             : str  = ''

    # network
    public_ip         : str  = ''
    private_ip        : str  = ''
    public_dns        : str  = ''
    private_dns       : str  = ''
    vpc_id            : str  = ''
    subnet_id         : str  = ''

    # iam
    iam_profile_arn   : str  = ''
    iam_profile_name  : str  = ''

    # security groups  [{"id": "sg-xxx", "name": "...", "rules": [...]}]
    security_groups   : list = None

    # storage  [{"device": "/dev/xvda", "volume_id": "vol-xxx", "size_gb": 30, ...}]
    volumes           : list = None

    # tags  {"Name": "...", ...}
    tags              : dict = None

    # error — non-empty when AWS calls failed
    error             : str  = ''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.security_groups is None:
            self.security_groups = []
        if self.volumes is None:
            self.volumes = []
        if self.tags is None:
            self.tags = {}
