import asyncio
from time import sleep
from typing import Dict, List, override
from common.coordinator import Coordinator
from dataclasses import dataclass
from abc import ABC, abstractmethod
import datetime

from experiments.meter.prometheus_meter import ContainerMetrics, PrometheusMeter


@dataclass
class HardwareMetricsExperimentOutcome:
    metrics: ContainerMetrics
    total_time_in_seconds: float




@dataclass
class HardwareMetricsExperimenter(ABC):
    experiment_container_name: str
    meter: PrometheusMeter

    @abstractmethod
    async def run_experiment(self):
        pass

    async def run_experiments(self, n_iterations: int) -> HardwareMetricsExperimentOutcome:

        start_time = datetime.datetime.now()

        results = []
        for _ in range(n_iterations):
            result = self.run_experiment()
            results.append(result)

        await asyncio.gather(*results)

        end_time = datetime.datetime.now()
        total_time = (end_time - start_time).total_seconds()

        metrics = self.meter.measure_all(
            container=self.experiment_container_name,
            start=start_time,
            end=end_time
        )

        return HardwareMetricsExperimentOutcome(
            metrics=metrics, 
            total_time_in_seconds=total_time
        )


@dataclass
class NonOrbitalisHardwareMetricsExperimenter(HardwareMetricsExperimenter):
    coordinator: Coordinator
    primes_range_start: int
    primes_range_end: int

    @override
    async def run_experiment(self):
        self.coordinator.execute_distributed_computation(self.primes_range_start, self.primes_range_end)

        while not self.coordinator.done:
            await asyncio.sleep(0)




