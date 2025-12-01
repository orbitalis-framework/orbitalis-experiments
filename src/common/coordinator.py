from dataclasses import dataclass, field
from typing import List, Optional
from abc import ABC, abstractmethod
import asyncio


@dataclass
class Coordinator(ABC):

    last_result: Optional[List[int]] = field(default=None, kw_only=True)
    done_event: asyncio.Event = field(default_factory=asyncio.Event, init=False)

    @abstractmethod
    async def execute_distributed_computation(self, start: int, end: int) -> None:
        raise NotImplementedError()
    
    def reset(self) -> None:
        self.last_result = None
        self.done_event.clear()
