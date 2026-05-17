# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI — CloudTrail__AWS__Client (Foundation interface stub)
# Real bodies owned by Slice F (v0.2.29__sg-aws-cloudtrail).
# Slice H builds against this stub for CloudTrail__Source__Adapter; the
# final rebase before Slice H's PR swaps in Slice F's implementation.
# ═══════════════════════════════════════════════════════════════════════════════

from osbot_utils.type_safe.Type_Safe import Type_Safe


class CloudTrail__AWS__Client(Type_Safe):

    def lookup_events(self,
                      start_time      : str = '',
                      end_time        : str = '',
                      attribute_key   : str = '',
                      attribute_value : str = '',
                      max_results     : int = 50) -> list:
        raise NotImplementedError("Slice F owns this body — see library/dev_packs/v0.2.29__sg-aws-cloudtrail/")

    def list_trails(self) -> list:
        raise NotImplementedError("Slice F owns this body — see library/dev_packs/v0.2.29__sg-aws-cloudtrail/")

    def describe_trail(self, name: str) -> dict:
        raise NotImplementedError("Slice F owns this body — see library/dev_packs/v0.2.29__sg-aws-cloudtrail/")

    def get_trail_status(self, name: str) -> dict:
        raise NotImplementedError("Slice F owns this body — see library/dev_packs/v0.2.29__sg-aws-cloudtrail/")
