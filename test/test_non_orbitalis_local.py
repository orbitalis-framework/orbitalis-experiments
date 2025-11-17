import unittest
        
from non_orbitalis.local.coordinator import LocalCoordinator
from non_orbitalis.local.worker import LocalWorker


class TestLocalCoordinator(unittest.TestCase):
    
    def test_execution(self):

        N_WORKERS = 4

        workers = [
            LocalWorker(identifier=f"worker_{i}") for i in range(N_WORKERS)
        ]

        coordinator = LocalCoordinator(workers=workers)

        coordinator.execute_distributed_computation(10, 50)
        expected_primes = [
            11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47
        ]

        self.assertTrue(coordinator.done)
        self.assertIsNotNone(coordinator.last_result)

        result = coordinator.last_result

        self.assertEqual(sorted(result), expected_primes)

if __name__ == '__main__':
    unittest.main()