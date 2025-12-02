from dataclasses import dataclass
from typing import List, override
from concurrent.futures import ThreadPoolExecutor, as_completed

from common.coordinator import Coordinator
from non_orbitalis.local_async.worker import LocalAsyncWorker


@dataclass
class LocalAsyncCoordinator(Coordinator):

    workers: List[LocalAsyncWorker]

    @override
    async def execute_distributed_computation(self, start: int, end: int):
        self.reset()
        self.last_result = []

        range_size = (end - start + 1) // len(self.workers)
        tasks = []

        for i, worker in enumerate(self.workers):
            worker_start = start + i * range_size
            worker_end = worker_start + range_size - 1

            if i == len(self.workers) - 1:
                worker_end = end

            tasks.append(
                worker.compute_async(worker_start, worker_end)
            )

        for task in tasks:
            self.last_result.extend(await task)

        self.done_event.set()
