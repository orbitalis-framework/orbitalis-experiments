import asyncio
from typing import Dict, override

from common.coordinator import Coordinator
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import datetime
from orbitalis.core.state import CoreState
from experiments.meter.prometheus_meter import ContainerMetrics, PrometheusMeter
from utils.busline_builder import build_new_mqtt_client
from with_orbitalis.coordinator import OrbitalisCoordinator
from with_orbitalis.worker import OrbitalisWorker
from orbitalis.core.requirement import Constraint, OperationRequirement
from orbitalis.orbiter.schemaspec import Input, Output
from with_orbitalis.worker import OrbitalisWorker, RangeMessage, PrimeNumbersMessage


@dataclass
class HardwareMetricsExperimentOutcome:
    metrics: ContainerMetrics
    total_time_in_seconds: float

    def to_csv(self) -> str:
        return (
            ",".join(self.metrics.__dataclass_fields__.keys()) + ",total_time_in_seconds\n" +
            ",".join(str(getattr(self.metrics, field)) for field in self.metrics.__dataclass_fields__.keys()) +
            f",{self.total_time_in_seconds}\n"
        )
    
    def to_dict(self) -> Dict[str, float]:
        return {
            **asdict(self.metrics),
            "total_time_in_seconds": self.total_time_in_seconds
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'HardwareMetricsExperimentOutcome':
        return HardwareMetricsExperimentOutcome(
            metrics=ContainerMetrics(
                **{k: data[k] for k in ContainerMetrics.__dataclass_fields__.keys()}
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

        print("Cooling down pre-experiment...")
        await asyncio.sleep(self.meter.scrape_interval * 2)

        start_time = datetime.datetime.now(tz=datetime.timezone.utc)

        results = []
        for _ in range(n_iterations):
            result = await self.run_experiment()
            results.append(result)

        end_time = datetime.datetime.now(tz=datetime.timezone.utc)
        total_time = (end_time - start_time).total_seconds()

        print("Waiting for Prometheus ingestion...")
        await asyncio.sleep(self.meter.scrape_interval * 2)

        metrics = self.meter.get_container_metrics(
            container=self.experiment_container_name,
            start_time=start_time,
            end_time=end_time
        )

        return HardwareMetricsExperimentOutcome(
            metrics=metrics, 
            total_time_in_seconds=total_time
        )


@dataclass
class HardwareMetricsExperimenterPrimeNumbers(HardwareMetricsExperimenter):
    coordinator: Coordinator
    primes_range_start: int
    primes_range_end: int

    @override
    async def run_experiment(self):
        await self.coordinator.execute_distributed_computation(self.primes_range_start, self.primes_range_end)
        await self.coordinator.done_event.wait()
        self.coordinator.reset()


@dataclass
class OrbitalisDiscoveryExperimenter(HardwareMetricsExperimenter):
    build_new_client: callable
    workers: list[OrbitalisWorker]

    @override
    async def run_experiment(self):

        coordinator = OrbitalisCoordinator(eventbus_client=self.build_new_client(),
                                       with_loop=False,
                                       raise_exceptions=True,
                                       operation_requirements={
                                           "calculate_prime_numbers": OperationRequirement(Constraint(
                                               inputs=[Input.from_schema(RangeMessage.avro_schema())],
                                               outputs=[Output.from_schema(PrimeNumbersMessage.avro_schema())],
                                               mandatory=[worker.identifier for worker in self.workers],
                                           ))
                                       })
        
        assert coordinator.state == CoreState.NOT_COMPLIANT

        await coordinator.start()

        await coordinator.compliant_event.wait()

        assert coordinator.state == CoreState.COMPLIANT

