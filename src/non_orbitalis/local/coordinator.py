from dataclasses import dataclass
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from common.coordinator import Coordinator
from non_orbitalis.local.worker import LocalWorker

@dataclass
class LocalCoordinator(Coordinator):

    workers: List[LocalWorker]

    def execute_distributed_computation(self, start: int, end: int):
        self.reset()
        self.last_result = []

        range_size = (end - start + 1) // len(self.workers)
        tasks = []

        with ThreadPoolExecutor(max_workers=len(self.workers)) as executor:
            for i, worker in enumerate(self.workers):
                worker_start = start + i * range_size
                worker_end = worker_start + range_size - 1

                if i == len(self.workers) - 1:
                    worker_end = end

                tasks.append(
                    executor.submit(worker.compute, worker_start, worker_end)
                )

        for future in as_completed(tasks):
            self.last_result.extend(future.result())

        self.done = True
