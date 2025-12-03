from dataclasses import dataclass, field
from typing import List, override

import aiomqtt
from common.computation.prime_number import compute_prime_numbers_in_range
from common.computation.worker import PrimeNumberComputerWorker
from without_orbitalis.mqtt.base import BaseMqtt


@dataclass
class MqttWorker(PrimeNumberComputerWorker):
    input_topic: str
    broker_host: str
    broker_port: int
    
    async def run(self) -> None:
        async with aiomqtt.Client(self.broker_host, self.broker_port) as client:
            await client.subscribe(self.input_topic)
            async for message in client.messages:
                payload = message.payload.decode()
                start_str, end_str, response_topic = payload.split(",")
                start = int(start_str)
                end = int(end_str)

                primes = self.compute(start, end)
                primes_str = ",".join(map(str, primes))

                await client.publish(response_topic, primes_str)
