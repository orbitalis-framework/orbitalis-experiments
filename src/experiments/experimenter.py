from dataclasses import dataclass
from abc import ABC, abstractmethod
import datetime
from typing import Dict, List
from tqdm import tqdm
import logging


@dataclass
class ExperimentOutcome:
    results: List[Dict[str, float]]
    total_time_in_seconds: float




@dataclass
class Experimenter(ABC):

    @abstractmethod
    def run_experiment(self) -> Dict[str, float]:
        return NotImplemented

    def run_experiments(self, n_iterations: int) -> ExperimentOutcome:

        start_time = datetime.datetime.now()

        results = []
        for iteration in tqdm(range(n_iterations)):
            result = self.run_experiment()
            results.append(result)

            logging.info(f"Completed iteration {iteration + 1}/{n_iterations}: {result}")

        end_time = datetime.datetime.now()
        total_time = (end_time - start_time).total_seconds()

        return ExperimentOutcome(results=results, total_time_in_seconds=total_time)