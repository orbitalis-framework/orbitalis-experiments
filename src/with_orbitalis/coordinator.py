from dataclasses import dataclass, field
from orbitalis.core.core import Core
from typing import override

from common.coordinator import Coordinator
from with_orbitalis.message import PrimeNumbersMessage, RangeMessage
from orbitalis.core.sink import sink
from busline.event.event import Event


@dataclass
class OrbitalisCoordinator(Core, Coordinator):
    counter: int = field(default=0)
    n_workers: int = field(default=0)

    @sink(operation_name="calculate_prime_numbers")
    async def calculate_prime_numbers_sink(self, topic: str, event: Event[PrimeNumbersMessage]):
        self.last_result.extend(event.payload.prime_numbers)
        self.counter += 1
        if self.counter >= self.n_workers:
            self.done_event.set()

    @override
    async def execute_distributed_computation(self, start: int, end: int) -> None:

        self.last_result = []
        self.done_event.clear()
        self.counter = 0

        self.n_workers = len(self.remote_identifiers)

        initial_first = start
        range_size = (end - start + 1) // self.n_workers

        messages = [
            RangeMessage(
                first_number=initial_first + i * range_size,
                second_number=end if i == self.n_workers - 1 else initial_first + (i + 1) * range_size - 1
            )
            for i in range(self.n_workers)
        ]

        await self.execute_distributed(
            "calculate_prime_numbers",
            messages,
            fire_and_forget=True
        )
