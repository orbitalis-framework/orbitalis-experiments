from typing import List, override
from dataclasses import dataclass, field
import paho.mqtt.client as mqtt
import asyncio

from common.coordinator import Coordinator
from non_orbitalis.mqtt.base import BaseMqtt

@dataclass
class MqttCoordinator(BaseMqtt, Coordinator):
    worker_input_topics: List[str]
    worker_output_topic: str
    _n_result_received: int = field(default=0, kw_only=True)

    def __post_init__(self):
        self.client.on_message = self._on_message
        self.client.subscribe(self.worker_output_topic)
        self.reset()

    @override
    def reset(self) -> None:
        super().reset()
        self._n_result_received = 0

    def _on_message(self, client, userdata, message):
        if self.last_result is None:
            raise RuntimeError("No computation in progress")
        
        self.last_result.extend([
            int(n)
            for n in message.payload.decode().split(",")    # expected: a,b,c,d,...
        ])

        self._n_result_received += 1
        if self._n_result_received == len(self.worker_input_topics):
            self.done = True

    @override
    def execute_distributed_computation(self, start: int, end: int):

        if self.last_result is not None:
            raise RuntimeError("Computation already in progress")

        self.reset()
        self.last_result = []

        range_size = (end - start + 1) // len(self.worker_input_topics)

        for worker_topic in self.worker_input_topics:
            worker_start = start
            worker_end = start + range_size - 1

            if worker_topic == self.worker_input_topics[-1]:
                worker_end = end

            self.client.publish(
                worker_topic,
                f"{worker_start},{worker_end},{self.worker_output_topic}"
            )

            start += range_size