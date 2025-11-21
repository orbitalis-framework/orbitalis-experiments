import unittest
        
from experiments.hardware_metrics_experimenter import NonOrbitalisHardwareMetricsExperimenter
from non_orbitalis.local.coordinator import LocalCoordinator
from non_orbitalis.local.worker import LocalWorker


class TestHardwareMetricsExperimenter(unittest.TestCase):
    
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


if __name__ == '__main__':
    unittest.main()