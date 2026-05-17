# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Source__Contract
# ABC that every observability source adapter implements.
# Slices A (S3), F (CloudTrail), and H (Observe, via CloudWatch wrapper) all
# build against this contract; Foundation ships it so they can build in
# parallel.
# ═══════════════════════════════════════════════════════════════════════════════

from abc import ABC, abstractmethod

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Query       import Source__Query
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Result__Page import Source__Result__Page
from sgraph_ai_service_playwright__cli.aws._shared.source_contract.Source__Stream      import Source__Stream


class Source__Contract(Type_Safe, ABC):

    @abstractmethod
    def connect(self) -> bool:
        ...

    @abstractmethod
    def list_streams(self) -> list:
        ...

    @abstractmethod
    def tail(self, stream: str, since: str) -> Source__Stream:
        ...

    @abstractmethod
    def query(self, q: Source__Query) -> Source__Result__Page:
        ...

    @abstractmethod
    def stats(self, stream: str, agg: str) -> dict:
        ...

    @abstractmethod
    def schema(self, stream: str) -> dict:
        ...
