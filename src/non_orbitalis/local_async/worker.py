from dataclasses import dataclass
from typing import List
from common.computation.prime_number import compute_prime_numbers_in_range
from common.computation.worker import PrimeNumberComputerWorker


@dataclass
class LocalAsyncWorker(PrimeNumberComputerWorker):
    identifier: str

    async def compute_async(self, start: int, end: int) -> List[int]:
        return compute_prime_numbers_in_range(start, end)