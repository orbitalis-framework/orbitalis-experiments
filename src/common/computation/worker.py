from typing import List, override
from common.computation.prime_number import compute_prime_numbers_in_range
from common.worker import Worker


class PrimeNumberComputerWorker(Worker):

    @override
    def compute(self, start: int, end: int) -> List[int]:
        return compute_prime_numbers_in_range(start, end)