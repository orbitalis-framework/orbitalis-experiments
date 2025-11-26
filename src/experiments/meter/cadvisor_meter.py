import time
import requests
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class ContainerMetricResult:
    cpu_percent_avg: float
    cpu_percent_max: float
    cpu_time_seconds: float
    memory_percent_avg: float
    memory_usage_max: int
    network_tx_avg: float
    network_tx_max: int
    network_rx_avg: float
    network_rx_max: int


class CAdvisorMeter:
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.base_url = f"http://{host}:{port}/api/v1.3/docker"

    def _fetch_stats(self, container: str, duration: float) -> List[Dict]:
        """
        Collect multiple samples over a time window.
        Stats are cumulative for CPU/network. RAM is instantaneous.
        """
        url = f"{self.base_url}/{container}"
        end_time = time.time() + duration
        samples = []

        while time.time() < end_time:
            data = requests.get(url).json()
            stats = data["stats"][-1]  # latest sample
            samples.append(stats)
            time.sleep(1)

        return samples

    # ------------------- CPU METRICS -------------------

    def cpu_percent_avg(self, container: str, duration: float) -> float:
        samples = self._fetch_stats(container, duration)
        return self._compute_cpu_percent(samples, duration)["avg"]

    def cpu_percent_max(self, container: str, duration: float) -> float:
        samples = self._fetch_stats(container, duration)
        return self._compute_cpu_percent(samples, duration)["max"]

    def cpu_time_seconds(self, container: str, duration: float) -> float:
        samples = self._fetch_stats(container, duration)
        first = samples[0]["cpu"]["usage"]["total"]
        last = samples[-1]["cpu"]["usage"]["total"]
        return (last - first) / 1e9  # nanoseconds → seconds

    def _compute_cpu_percent(self, samples, duration):
        percents = []
        for i in range(1, len(samples)):
            prev = samples[i - 1]["cpu"]["usage"]["total"]
            curr = samples[i]["cpu"]["usage"]["total"]
            delta = (curr - prev) / 1e9  # ns → seconds
            percent = (delta / 1.0) * 100  # because sampling each second
            percents.append(percent)

        return {
            "avg": sum(percents) / len(percents) if percents else 0.0,
            "max": max(percents) if percents else 0.0,
        }

    # ------------------- MEMORY METRICS -------------------

    def memory_percent_avg(self, container: str, duration: float) -> float:
        samples = self._fetch_stats(container, duration)
        percents = [
            s["memory"]["usage"] / s["memory"]["limit"] * 100 for s in samples
        ]
        return sum(percents) / len(percents)

    def memory_usage_max(self, container: str, duration: float) -> int:
        samples = self._fetch_stats(container, duration)
        return max(s["memory"]["usage"] for s in samples)

    # ------------------- NETWORK METRICS -------------------

    def network_tx_avg(self, container: str, duration: float) -> float:
        samples = self._fetch_stats(container, duration)
        deltas = self._compute_network_deltas(samples, "tx_bytes")
        return sum(deltas) / len(deltas)

    def network_tx_max(self, container: str, duration: float) -> int:
        samples = self._fetch_stats(container, duration)
        deltas = self._compute_network_deltas(samples, "tx_bytes")
        return max(deltas)

    def network_rx_avg(self, container: str, duration: float) -> float:
        samples = self._fetch_stats(container, duration)
        deltas = self._compute_network_deltas(samples, "rx_bytes")
        return sum(deltas) / len(deltas)

    def network_rx_max(self, container: str, duration: float) -> int:
        samples = self._fetch_stats(container, duration)
        deltas = self._compute_network_deltas(samples, "rx_bytes")
        return max(deltas)

    def _compute_network_deltas(self, samples, key):
        deltas = []
        for i in range(1, len(samples)):
            prev = samples[i - 1]["network"][key]
            curr = samples[i]["network"][key]
            deltas.append(curr - prev)
        return deltas if deltas else [0]

    # ------------------- FULL RESULT -------------------

    def measure_all(self, container: str, duration: float) -> ContainerMetricResult:
        samples = self._fetch_stats(container, duration)

        cpu_stats = self._compute_cpu_percent(samples, duration)

        return ContainerMetricResult(
            cpu_percent_avg=cpu_stats["avg"],
            cpu_percent_max=cpu_stats["max"],
            cpu_time_seconds=self.cpu_time_seconds(container, duration),
            memory_percent_avg=sum(
                s["memory"]["usage"] / s["memory"]["limit"] * 100 for s in samples
            ) / len(samples),
            memory_usage_max=max(s["memory"]["usage"] for s in samples),
            network_tx_avg=sum(self._compute_network_deltas(samples, "tx_bytes"))
            / (len(samples) - 1),
            network_tx_max=max(self._compute_network_deltas(samples, "tx_bytes")),
            network_rx_avg=sum(self._compute_network_deltas(samples, "rx_bytes"))
            / (len(samples) - 1),
            network_rx_max=max(self._compute_network_deltas(samples, "rx_bytes")),
        )