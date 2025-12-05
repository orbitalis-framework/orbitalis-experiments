import asyncio
from dataclasses import dataclass
from typing import List

from orbitalis.utils.task import fire_and_forget_task
from orbitalis.plugin.operation import operation
from orbitalis.plugin.plugin import Plugin
from busline.event.event import Event

from common.computation.worker import PrimeNumberComputerWorker
from with_orbitalis.message import PrimeNumbersMessage, RangeMessage





@dataclass
class OrbitalisWorker(Plugin, PrimeNumberComputerWorker):

    fire_and_forget: bool

    @operation(
        name="calculate_prime_numbers",
        input=RangeMessage,
        output=PrimeNumbersMessage
    )
    async def calculate_prime_numbers_event_handler(self, topic: str, event: Event[RangeMessage]):
        connections = self.retrieve_connections(input_topic=topic, operation_name="calculate_prime_numbers")

        # Only one connection should be present on inbound topic
        assert len(connections) == 1

        connection = connections[0]

        assert connection.output_topic is not None
        assert connection.output.has_output

        # Compute prime numbers in the given range
        prime_numbers = self.compute(event.payload.first_number, event.payload.second_number)

        # Send output to core
        task = self.eventbus_client.publish(
                connection.output_topic,
                PrimeNumbersMessage(prime_numbers=prime_numbers)
            )

        if self.fire_and_forget:
            fire_and_forget_task(task)
        else:
            await task
