import unittest
import asyncio
import sys

from busline.client.pubsub_client import PubSubClient, PubSubClientBuilder
from busline.local.eventbus.local_eventbus import LocalEventBus
from busline.local.local_publisher import LocalPublisher
from busline.local.local_subscriber import LocalSubscriber
from busline.mqtt.mqtt_publisher import MqttPublisher
from busline.mqtt.mqtt_subscriber import MqttSubscriber
from orbitalis.core.requirement import Constraint, OperationRequirement
from orbitalis.orbiter.schemaspec import Input, Output

from experiments.hardware_metrics_experimenter import NonOrbitalisHardwareMetricsExperimenter, OrbitalisHardwareMetricsExperimenter
from non_orbitalis.local.coordinator import LocalCoordinator
from non_orbitalis.local.worker import LocalWorker
from with_orbitalis.worker import Worker, RangeMessage, PrimeNumbersMessage
from with_orbitalis.coordinator import Coordinator

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def build_new_local_client() -> PubSubClient:
    return PubSubClientBuilder().with_subscriber(LocalSubscriber(eventbus=LocalEventBus())).with_publisher(
        LocalPublisher(eventbus=LocalEventBus())).build()


def build_new_mqtt_client() -> PubSubClient:
    return PubSubClientBuilder().with_subscriber(MqttSubscriber(hostname="127.0.0.1")).with_publisher(
        MqttPublisher(hostname="127.0.0.1")).build()


class TestHardwareMetricsExperimenter(unittest.IsolatedAsyncioTestCase):

    def test_non_orbitalis_local(self):

        N_WORKERS = 4

        workers = [
            LocalWorker(identifier=f"worker_{i}") for i in range(N_WORKERS)
        ]

        coordinator = LocalCoordinator(workers=workers)

        experimenter = NonOrbitalisHardwareMetricsExperimenter(
            coordinator=coordinator,
            primes_range_start=10,
            primes_range_end=50
        )

        outcome = experimenter.run_experiments(n_iterations=10)
        expected_primes_count = 11  # There are 11 primes between 10 and 50

        for result in outcome.results:
            self.assertEqual(result["num_primes_found"], expected_primes_count)

        self.assertGreater(
            outcome.total_time_in_seconds, 0.0
        )

    def test_non_orbitalis_mqtt(self):

        N_WORKERS = 4

        workers = [
            LocalWorker(identifier=f"worker_{i}") for i in range(N_WORKERS)
        ]

        coordinator = LocalCoordinator(workers=workers)

        experimenter = NonOrbitalisHardwareMetricsExperimenter(
            coordinator=coordinator,
            primes_range_start=10,
            primes_range_end=50
        )

        outcome = experimenter.run_experiments(n_iterations=10)
        expected_primes_count = 11  # There are 11 primes between 10 and 50

        for result in outcome.results:
            self.assertEqual(result["num_primes_found"], expected_primes_count)

        self.assertGreater(
            outcome.total_time_in_seconds, 0.0
        )

    async def test_orbitalis_local(self):

        N_WORKERS = 4

        workers = [
            Worker(identifier=f"worker_{i}", eventbus_client=build_new_local_client(), raise_exceptions=True,
                   with_loop=False) for i in range(N_WORKERS)
        ]

        coordinator = Coordinator(eventbus_client=build_new_local_client(), with_loop=False, raise_exceptions=True,
                                  operation_requirements={
                                      "calculate_prime_numbers": OperationRequirement(Constraint(
                                          inputs=[Input.from_schema(RangeMessage.avro_schema())],
                                          outputs=[Output.from_schema(PrimeNumbersMessage.avro_schema())],
                                          mandatory=[worker.identifier for worker in workers],
                                      ))
                                  })

        experimenter = OrbitalisHardwareMetricsExperimenter(
            coordinator=coordinator,
            primes_range_start=10,
            primes_range_end=50
        )

        for worker in workers:
            await worker.start()
        await coordinator.start()

        await asyncio.sleep(2)

        outcome = await experimenter.run_experiments(n_iterations=10)
        expected_primes_count = 11  # There are 11 primes between 10 and 50

        for result in outcome.results:
            self.assertEqual(result["num_primes_found"], expected_primes_count)

        self.assertGreater(
            outcome.total_time_in_seconds, 0.0
        )

        for worker in workers:
            await worker.stop()
        await coordinator.stop()

    async def test_orbitalis_mqtt(self):

        N_WORKERS = 4

        workers = [
            Worker(identifier=f"worker_{i}", eventbus_client=build_new_mqtt_client(), raise_exceptions=True,
                   with_loop=False) for i in range(N_WORKERS)
        ]

        coordinator = Coordinator(eventbus_client=build_new_mqtt_client(), with_loop=False, raise_exceptions=True,
                                  operation_requirements={
                                      "calculate_prime_numbers": OperationRequirement(Constraint(
                                          inputs=[Input.from_schema(RangeMessage.avro_schema())],
                                          outputs=[Output.from_schema(PrimeNumbersMessage.avro_schema())],
                                          mandatory=[worker.identifier for worker in workers],
                                      ))
                                  })

        experimenter = OrbitalisHardwareMetricsExperimenter(
            coordinator=coordinator,
            primes_range_start=10,
            primes_range_end=50
        )

        for worker in workers:
            await worker.start()
        await coordinator.start()

        await asyncio.sleep(2)

        outcome = await experimenter.run_experiments(n_iterations=10)
        expected_primes_count = 11  # There are 11 primes between 10 and 50

        for result in outcome.results:
            self.assertEqual(result["num_primes_found"], expected_primes_count)

        self.assertGreater(
            outcome.total_time_in_seconds, 0.0
        )

        for worker in workers:
            await worker.stop()
        await coordinator.stop()


if __name__ == '__main__':
    unittest.main()
