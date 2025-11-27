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

    def to_csv(self) -> str:
        return (
            "cpu_percent_avg,cpu_percent_max,cpu_time_seconds,memory_percent_avg,memory_usage_max_bytes,"
            "network_tx_avg,network_tx_max,network_rx_avg,network_rx_max,total_time_in_seconds\n"
            f"{self.metrics.cpu_percent_avg},"
            f"{self.metrics.cpu_percent_max},"
            f"{self.metrics.cpu_time_seconds},"
            f"{self.metrics.memory_percent_avg},"
            f"{self.metrics.memory_usage_max_bytes},"
            f"{self.metrics.network_tx_avg},"
            f"{self.metrics.network_tx_max},"
            f"{self.metrics.network_rx_avg},"
            f"{self.metrics.network_rx_max},"
            f"{self.total_time_in_seconds}"
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "cpu_percent_avg": self.metrics.cpu_percent_avg,
            "cpu_percent_max": self.metrics.cpu_percent_max,
            "cpu_time_seconds": self.metrics.cpu_time_seconds,
            "memory_percent_avg": self.metrics.memory_percent_avg,
            "memory_usage_max_bytes": self.metrics.memory_usage_max_bytes,
            "network_tx_avg": self.metrics.network_tx_avg,
            "network_tx_max": self.metrics.network_tx_max,
            "network_rx_avg": self.metrics.network_rx_avg,
            "network_rx_max": self.metrics.network_rx_max,
            "total_time_in_seconds": self.total_time_in_seconds
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'HardwareMetricsExperimentOutcome':
        return HardwareMetricsExperimentOutcome(
            metrics=ContainerMetrics(
                cpu_percent_avg=data["cpu_percent_avg"],
                cpu_percent_max=data["cpu_percent_max"],
                cpu_time_seconds=data["cpu_time_seconds"],
                memory_percent_avg=data["memory_percent_avg"],
                memory_usage_max_bytes=data["memory_usage_max_bytes"],
                network_tx_avg=data["network_tx_avg"],
                network_tx_max=data["network_tx_max"],
                network_rx_avg=data["network_rx_avg"],
                network_rx_max=data["network_rx_max"],
            ),
            total_time_in_seconds=data["total_time_in_seconds"]
        )


@dataclass
class HardwareMetricsExperimenter(ABC):
    experiment_container_name: str
    meter: PrometheusMeter

    @abstractmethod
    async def run_experiment(self):
        pass

    async def run_experiments(self, n_iterations: int) -> HardwareMetricsExperimentOutcome:

        start_time = datetime.datetime.now(tz=datetime.timezone.utc)

        results = []
        for _ in range(n_iterations):
            result = self.run_experiment()
            results.append(result)

        await asyncio.gather(*results)

        end_time = datetime.datetime.now(tz=datetime.timezone.utc)
        total_time = (end_time - start_time).total_seconds()

        metrics = self.meter.get_container_metrics(
            container=self.experiment_container_name,
            lookback_seconds=int(total_time) + 60  # Adding buffer time
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




