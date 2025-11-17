from dataclasses import dataclass, field
from typing import List, Optional
from abc import ABC, abstractmethod


@dataclass
class Coordinator(ABC):

    last_result: Optional[List[int]] = field(default=None, kw_only=True)
    done: bool = field(default=False, kw_only=True)

    @abstractmethod
    def execute_distributed_computation(self, start: int, end: int) -> None:
        raise NotImplementedError()
    
    def reset(self) -> None:
        self.last_result = None
        self.done = False