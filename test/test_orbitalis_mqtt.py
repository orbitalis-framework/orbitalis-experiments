import asyncio
import unittest

from busline.client.pubsub_client import PubSubClient, PubSubClientBuilder
from busline.mqtt.mqtt_publisher import MqttPublisher
from busline.mqtt.mqtt_subscriber import MqttSubscriber

from with_orbitalis.mqtt.coordinator import MqttCoordinator
from with_orbitalis.mqtt.worker import MqttWorker, PrimeNumbersMessage, RangeMessage
from orbitalis.core.requirement import Constraint, OperationRequirement
from orbitalis.orbiter.schemaspec import Input, Output

import sys
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def build_new_mqtt_client() -> PubSubClient:
    return PubSubClientBuilder().with_subscriber(MqttSubscriber(hostname="127.0.0.1")).with_publisher(
        MqttPublisher(hostname="127.0.0.1")).build()


class TestLocalCoordinator(unittest.TestCase):

    def test_execution(self):
        asyncio.run(self._test_execution_async())

    async def _test_execution_async(self):

        N_WORKERS = 4

        workers = [
            MqttWorker(identifier=f"worker_{i}", eventbus_client=build_new_mqtt_client(), raise_exceptions=True,
                        with_loop=False) for i in range(N_WORKERS)
        ]

        coordinator = MqttCoordinator(eventbus_client=build_new_mqtt_client(), with_loop=False, raise_exceptions=True,
                                       operation_requirements={
                                           "calculate_prime_numbers": OperationRequirement(Constraint(
                                               inputs=[Input.from_schema(RangeMessage.avro_schema())],
                                               outputs=[Output.from_schema(PrimeNumbersMessage.avro_schema())],
                                               mandatory=[worker.identifier for worker in workers],
                                           ))
                                       })

        for worker in workers:
            await worker.start()
        await coordinator.start()

        await asyncio.sleep(2)

        start = 10
        end = 50

        result = await coordinator.execute_distributed_computation(start, end, len(workers))

        expected_primes = [
            11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47
        ]

        self.assertEqual(expected_primes, result)

        for worker in workers:
            await worker.stop()
        await coordinator.stop()


if __name__ == '__main__':
    unittest.main()