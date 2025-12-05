import asyncio
import unittest

from busline.client.pubsub_client import PubSubClient, PubSubClientBuilder
from busline.mqtt.mqtt_publisher import MqttPublisher
from busline.mqtt.mqtt_subscriber import MqttSubscriber

from with_orbitalis.coordinator import  OrbitalisCoordinator
from with_orbitalis.worker import OrbitalisWorker
from with_orbitalis.message import PrimeNumbersMessage, RangeMessage
from orbitalis.core.requirement import Constraint, OperationRequirement
from orbitalis.orbiter.schemaspec import Input, Output

def build_new_mqtt_client() -> PubSubClient:
    return PubSubClientBuilder().with_subscriber(MqttSubscriber(hostname="127.0.0.1")).with_publisher(
        MqttPublisher(hostname="127.0.0.1")).build()


class TestOrbitalisMqttCoordinator(unittest.TestCase):

    def test_execution(self):
        asyncio.run(self._test_execution_async())

    async def _test_execution_async(self):

        N_WORKERS = 4

        workers = [
            OrbitalisWorker(identifier=f"worker_{i}", eventbus_client=build_new_mqtt_client(), raise_exceptions=True, fire_and_forget=True,
                   with_loop=False) for i in range(N_WORKERS)
        ]

        coordinator = OrbitalisCoordinator(eventbus_client=build_new_mqtt_client(), with_loop=False, raise_exceptions=True,
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

        START = 10
        END = 50

        result = await coordinator.execute_distributed_computation(START, END)

        expected_primes = [
            11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47
        ]

        self.assertEqual(expected_primes, result)

        for worker in workers:
            await worker.stop()
        await coordinator.stop()

        await asyncio.sleep(1)


if __name__ == '__main__':
    unittest.main()
