from typing import List, override
from dataclasses import dataclass, field
import aiomqtt
import asyncio

from common.coordinator import Coordinator

@dataclass
class MqttCoordinator(Coordinator):
    worker_input_topics: List[str]
    worker_output_topic: str
    broker_host: str
    broker_port: int
    _n_result_received: int = field(default=0, init=False)

    def reset(self) -> None:
        super().reset()
        self._n_result_received = 0

    async def _message_listener(self, client: aiomqtt.Client):
        async for message in client.messages:
            payload = message.payload.decode()
            partial_results = payload.split(",")
            
            if self.last_result is not None:
                self.last_result.extend(partial_results)
            
            self._n_result_received += 1

            if self._n_result_received == len(self.worker_input_topics):
                self.done_event.set()
                return

    @override
    async def execute_distributed_computation(self, start: int, end: int) -> None:
        self.reset()
        self.last_result = []
        
        async with aiomqtt.Client(self.broker_host, self.broker_port) as client:
            
            listener_task = asyncio.create_task(self._message_listener(client))
            await client.subscribe(self.worker_output_topic)

            range_size = (end - start + 1) // len(self.worker_input_topics)

            for worker_topic in self.worker_input_topics:
                worker_start = start
                worker_end = start + range_size - 1

                if worker_topic == self.worker_input_topics[-1]:
                    worker_end = end

                await client.publish(
                    worker_topic,
                    f"{worker_start},{worker_end},{self.worker_output_topic}"
                )

                start += range_size

            # Wait for the listener to signal completion
            await self.done_event.wait()
            
            # 4. Cleanup: Cancel the listener if it hasn't finished already
            if not listener_task.done():
                listener_task.cancel()