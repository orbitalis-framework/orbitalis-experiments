import unittest
        
from without_orbitalis.local_async.coordinator import LocalAsyncCoordinator
from without_orbitalis.local_async.worker import LocalAsyncWorker
from without_orbitalis.local_multithread.coordinator import LocalMultithreadCoordinator
from without_orbitalis.local_multithread.worker import LocalMultithreadWorker


class TestLocalCoordinator(unittest.IsolatedAsyncioTestCase):
    
    async def test_execution_multithread(self):

        N_WORKERS = 4

        workers = [
            LocalMultithreadWorker(identifier=f"worker_{i}") for i in range(N_WORKERS)
        ]

        coordinator = LocalMultithreadCoordinator(workers=workers)

        await coordinator.execute_distributed_computation(10, 50)
        
        await coordinator.done_event.wait()
        
        expected_primes = [
            11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47
        ]

        self.assertTrue(coordinator.done_event.is_set())
        self.assertIsNotNone(coordinator.last_result)

        result = coordinator.last_result

        self.assertEqual(sorted(result), expected_primes)

    async def test_execution_async(self):

        N_WORKERS = 4

        workers = [
            LocalAsyncWorker(identifier=f"worker_{i}") for i in range(N_WORKERS)
        ]

        coordinator = LocalAsyncCoordinator(workers=workers)

        await coordinator.execute_distributed_computation(10, 50)
        
        await coordinator.done_event.wait()
        
        expected_primes = [
            11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47
        ]

        self.assertTrue(coordinator.done_event.is_set())
        self.assertIsNotNone(coordinator.last_result)

        result = coordinator.last_result

        self.assertEqual(sorted(result), expected_primes)

if __name__ == '__main__':
    unittest.main()