from dataclasses import dataclass
from time import sleep
from typing import Dict, List, override
from common.coordinator import Coordinator
from experiments.experimenter import Experimenter


@dataclass
class NonOrbitalisHardwareMetricsExperimenter(Experimenter):
    coordinator: Coordinator
    primes_range_start: int
    primes_range_end: int

    @override
    def run_experiment(self) -> Dict[str, float]:
        self.coordinator.execute_distributed_computation(self.primes_range_start, self.primes_range_end)

        while not self.coordinator.done:
            sleep(0)

        return {"num_primes_found": len(self.coordinator.last_result)}




