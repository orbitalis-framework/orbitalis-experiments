from typing import List, override
from dataclasses import dataclass

from common.coordinator import Coordinator
from non_orbitalis.local.worker import LocalWorker


@dataclass
class LocalCoordinator(Coordinator):

    workers: List[LocalWorker]

    @override
    def execute_distributed_computation(self, start: int, end: int):
        self.reset()
        self.last_result = []

        range_size = (end - start + 1) // len(self.workers)

        for worker in self.workers:
            worker_start = start
            worker_end = start + range_size - 1

            if worker == self.workers[-1]:
                worker_end = end

            self.last_result.extend(
                worker.compute(
                    worker_start, 
                    worker_end
                )
            )

            start += range_size

        self.done = True

