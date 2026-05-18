# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Teardown__Dispatcher
# Maps Enum__Lab__Resource_Type → teardown handler; calls teardown() in order.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.enums.Enum__Lab__Resource_Type              import Enum__Lab__Resource_Type
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Ledger__Entry          import Schema__Lab__Ledger__Entry
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__R53         import Lab__Teardown__R53
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__CF          import Lab__Teardown__CF
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__Lambda      import Lab__Teardown__Lambda
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__ACM         import Lab__Teardown__ACM
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__EC2         import Lab__Teardown__EC2
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__SSM         import Lab__Teardown__SSM
from sgraph_ai_service_playwright__cli.aws.lab.service.teardown.Lab__Teardown__IAM         import Lab__Teardown__IAM


class Lab__Teardown__Dispatcher(Type_Safe):
    r53     : Lab__Teardown__R53
    cf      : Lab__Teardown__CF
    lambda_ : Lab__Teardown__Lambda
    acm     : Lab__Teardown__ACM
    ec2     : Lab__Teardown__EC2
    ssm     : Lab__Teardown__SSM
    iam     : Lab__Teardown__IAM

    def setup(self) -> 'Lab__Teardown__Dispatcher':
        if self.r53 is None:
            self.r53     = Lab__Teardown__R53()
            self.r53.setup()
        if self.cf      is None: self.cf      = Lab__Teardown__CF()
        if self.lambda_ is None: self.lambda_ = Lab__Teardown__Lambda()
        if self.acm     is None: self.acm     = Lab__Teardown__ACM()
        if self.ec2     is None: self.ec2     = Lab__Teardown__EC2()
        if self.ssm     is None: self.ssm     = Lab__Teardown__SSM()
        if self.iam     is None: self.iam     = Lab__Teardown__IAM()
        return self

    def teardown(self, entry: Schema__Lab__Ledger__Entry) -> bool:
        handler = self._handler_for(entry.resource_type)
        if handler is None:
            raise ValueError(f'No teardown handler for resource type: {entry.resource_type}')
        return handler.teardown(entry)

    def teardown_all(self, entries: list) -> dict:                                 # dict[entry_id → bool]
        results = {}
        sorted_entries = sorted(entries, key=lambda e: e.resource_type.teardown_order if e.resource_type else 99)
        for entry in sorted_entries:
            try:
                results[str(entry.entry_id)] = self.teardown(entry)
            except Exception as ex:
                results[str(entry.entry_id)] = False
        return results

    def _handler_for(self, resource_type: Enum__Lab__Resource_Type):
        if resource_type is None:
            return None
        _map = {
            Enum__Lab__Resource_Type.R53_RECORD      : self.r53    ,
            Enum__Lab__Resource_Type.CF_DISTRIBUTION : self.cf     ,
            Enum__Lab__Resource_Type.LAMBDA          : self.lambda_,
            Enum__Lab__Resource_Type.LAMBDA_URL      : self.lambda_,
            Enum__Lab__Resource_Type.ACM_CERT        : self.acm    ,
            Enum__Lab__Resource_Type.EC2_INSTANCE    : self.ec2    ,
            Enum__Lab__Resource_Type.SG              : self.ec2    ,
            Enum__Lab__Resource_Type.IAM_ROLE        : self.iam    ,
            Enum__Lab__Resource_Type.SSM_PARAM       : self.ssm    ,
            Enum__Lab__Resource_Type.S3_BUCKET       : None        ,              # not yet implemented
        }
        return _map.get(resource_type)
