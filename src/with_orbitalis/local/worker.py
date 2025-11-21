from dataclasses import dataclass
from typing import List

from busline.event.message.avro_message import AvroMessageMixin
from orbitalis.orbiter.schemaspec import Input, Output
from orbitalis.plugin.operation import operation
from orbitalis.plugin.plugin import Plugin
from busline.event.event import Event

from common.computation.prime_number import compute_prime_numbers_in_range


@dataclass
class RangeMessage(AvroMessageMixin):
    first_number: int
    second_number: int


@dataclass
class PrimeNumbersMessage(AvroMessageMixin):
    prime_numbers: List[int]


@dataclass
class LocalWorker(Plugin):
    identifier: str

    @operation(
        # operation name
        name="calculate_prime_numbers",

        # operation is fed with Int64Message messages (integer)
        input=Input.from_message(RangeMessage),

        # operation doesn't send any output
        output=Output.from_message(PrimeNumbersMessage)
    )
    async def calculate_prime_numbers_event_handler(self, topic: str, event: Event[...]):
        connections = await self._retrieve_and_touch_connections(input_topic=topic,
                                                                 operation_name="calculate_prime_numbers")

        # Only one connection should be present on inbound topic
        assert len(connections) == 1

        connection = connections[0]

        assert connection.output_topic is not None
        assert connection.output.has_output

        # Manually touch the connection
        async with connection.lock:
            connection.touch()

        prime_numbers = compute_prime_numbers_in_range(event.payload.first_number, event.payload.second_number)

        # Send output to core
        await self.eventbus_client.publish(
            connection.output_topic,
            PrimeNumbersMessage(prime_numbers=prime_numbers)
        )
