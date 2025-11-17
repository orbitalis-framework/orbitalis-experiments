from time import sleep
import unittest
import paho.mqtt.client as mqtt
from non_orbitalis.mqtt.coordinator import MqttCoordinator
from non_orbitalis.mqtt.worker import MqttWorker


class TestLocalCoordinator(unittest.TestCase):
    
    def test_execution(self):
        N_WORKERS = 4

        worker_clients = [
            mqtt.Client(client_id=f"worker_{i}") for i in range(N_WORKERS)
        ]

        coordinator_client = mqtt.Client(client_id="coordinator")

        # Connect and start all clients to the MQTT broker
        coordinator_client.connect("localhost", 1883, 60)
        coordinator_client.loop_start()

        for worker_client in worker_clients:
            worker_client.connect("localhost", 1883, 60)
            worker_client.loop_start()

        # Set up the workers
        workers = [
            MqttWorker(
                client=worker_client,
            )
            for worker_client in worker_clients
        ]

        # Set up the coordinator
        coordinator = MqttCoordinator(
            client=coordinator_client,
            worker_input_topics=[worker.input_topic for worker in workers],
            worker_output_topic="coordinator/output"
        )
        
        # Execute the distributed computation
        coordinator.execute_distributed_computation(10, 50)

        while not coordinator.done:
            sleep(0.1)
            
        self.assertIsNotNone(coordinator.last_result)

        result = coordinator.last_result
        expected_primes = [
            11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47
        ]

        self.assertEqual(sorted(result), expected_primes)


if __name__ == '__main__':
    unittest.main()