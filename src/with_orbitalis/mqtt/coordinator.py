from dataclasses import dataclass, field

from orbitalis.core.core import Core
from typing import List
from with_orbitalis.mqtt.worker import PrimeNumbersMessage, RangeMessage
from orbitalis.core.sink import sink
from busline.event.event import Event

import asyncio


@dataclass
class MqttCoordinator(Core):

    last_result: List[int] = field(default_factory=list)

    done: bool = field(default=False)

    counter: int = field(default=0)

    n_workers: int = field(default=0)

    @sink(
        operation_name="calculate_prime_numbers"
    )
    async def calculate_prime_numbers_sink(self, topic: str, event: Event[PrimeNumbersMessage]):
        self.last_result.extend(event.payload.prime_numbers)
        self.counter += 1
        if self.counter == self.n_workers:
            self.done = True

    async def execute_distributed_computation(self, start: int, end: int, n_workers: int):

        self.n_workers = n_workers

        connections = self.retrieve_connections(operation_name="calculate_prime_numbers")
        validConnections = [c for c in connections if c.has_input and c.input.is_compatible_with_schema(RangeMessage.avro_schema())]

        range_size = (end - start + 1) // len(validConnections)


        for connection in validConnections:
            worker_start = start
            worker_end = start + range_size - 1

            if connection == validConnections[-1]:
                worker_end = end

            await self.eventbus_client.publish(
                connection.input_topic,
                RangeMessage(
                    first_number=worker_start,
                    second_number=worker_end
                )
            )
            start += range_size

        while not self.done:
            await asyncio.sleep(0.1)

        return self.last_result
