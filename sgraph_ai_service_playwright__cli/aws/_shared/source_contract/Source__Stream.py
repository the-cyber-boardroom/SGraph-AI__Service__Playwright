# ═══════════════════════════════════════════════════════════════════════════════
# SP CLI _shared — Source__Stream
# Streaming iterator wrapper returned by Source__Contract.tail().
# Wraps a generator of Schema__AWS__Source__Event rows.
# ═══════════════════════════════════════════════════════════════════════════════

from typing import Generator

from osbot_utils.type_safe.Type_Safe import Type_Safe

from sgraph_ai_service_playwright__cli.aws._shared.schemas.Schema__AWS__Source__Event import Schema__AWS__Source__Event


class Source__Stream(Type_Safe):
    source : str = ''
    stream : str = ''
    _gen   : object = None                                   # Generator[Schema__AWS__Source__Event, None, None]

    def __iter__(self):
        if self._gen is not None:
            yield from self._gen

    def with_generator(self, gen):
        self._gen = gen
        return self
