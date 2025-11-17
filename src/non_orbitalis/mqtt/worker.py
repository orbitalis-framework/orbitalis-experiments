from dataclasses import dataclass, field
from typing import List, override
from common.computation.prime_number import compute_prime_numbers_in_range
from common.computation.worker import PrimeNumberComputerWorker
from non_orbitalis.mqtt.base import BaseMqtt


@dataclass
class MqttWorker(BaseMqtt, PrimeNumberComputerWorker):

    input_topic: str = field(default="input", kw_only=True)
    
    def __post_init__(self):
        self.input_topic = "worker/" + self.identifier
        self.client.on_message = self._on_message
        self.client.subscribe(self.input_topic)
    
    def _on_message(self, client, userdata, message):
        start, end, output_topic = message.payload.decode().split(",")
        start = int(start)
        end = int(end)

        result = self.compute(start, end)

        self.client.publish(
            output_topic,
            ",".join(str(n) for n in result)
        )
    
