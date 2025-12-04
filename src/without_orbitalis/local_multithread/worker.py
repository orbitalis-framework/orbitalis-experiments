from dataclasses import dataclass
from typing import List, override
from common.computation.worker import PrimeNumberComputerWorker


@dataclass
class LocalMultithreadWorker(PrimeNumberComputerWorker):
    identifier: str

    @override
    def compute(self, start: int, end: int) -> List[int]:
        return super().compute(start, end)