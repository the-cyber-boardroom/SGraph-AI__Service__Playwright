# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI aws/lab — Lab__Experiment
# Abstract base class for all lab experiments. Agents A–D subclass this.
# Delta B.2: execute() takes NO runner argument; runner is injected via setup().
# ═══════════════════════════════════════════════════════════════════════════════

from abc import ABC, abstractmethod

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Experiment__Metadata import Schema__Lab__Experiment__Metadata
from sgraph_ai_service_playwright__cli.aws.lab.schemas.Schema__Lab__Run__Result           import Schema__Lab__Run__Result


class Lab__Experiment(Type_Safe, ABC):
    runner : object                                                                # Lab__Runner — injected by setup(); type hint avoids circular import

    def setup(self, runner) -> 'Lab__Experiment':
        self.runner = runner
        return self

    @abstractmethod
    def execute(self) -> Schema__Lab__Run__Result:
        ...

    @abstractmethod
    def metadata(self) -> Schema__Lab__Experiment__Metadata:
        ...
