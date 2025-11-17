from dataclasses import dataclass
from typing import List
from common.computation.prime_number import compute_prime_numbers_in_range
from common.computation.worker import PrimeNumberComputerWorker


@dataclass
class LocalWorker(PrimeNumberComputerWorker):
    identifier: str