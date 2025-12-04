import asyncio
from dataclasses import dataclass
import itertools
from typing import List, override

from common.coordinator import Coordinator
from without_orbitalis.local_async.worker import LocalAsyncWorker


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
                asyncio.create_task(
                    worker.compute_async(worker_start, worker_end)
                )
            )

        results = await asyncio.gather(*tasks)

        self.last_result = list(itertools.chain.from_iterable(results))

        self.done_event.set()
