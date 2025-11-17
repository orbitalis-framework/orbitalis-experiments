from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import List


@dataclass
class Worker(ABC):
    
    @abstractmethod
    def compute(self, start: int, end: int) -> List[int]:
        return NotImplemented