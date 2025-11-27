from dataclasses import dataclass
from typing import List
import requests
from datetime import datetime, timedelta, timezone


@dataclass
class ContainerMetrics:
    cpu_percent_avg: float
    cpu_percent_max: float
    cpu_time_seconds: float
    memory_percent_avg: float
    memory_usage_max_bytes: int
    network_tx_avg: float
    network_tx_max: int
    network_rx_avg: float
    network_rx_max: int


class PrometheusMeter:

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    # ----------------------------------------------------------------------

    def _compute_range(self, lookback_seconds: int) -> tuple[str, str]:
        """
        Compute RFC3339 timestamps for the Prometheus range query.
        """
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=lookback_seconds)
        return start.isoformat(), end.isoformat()

    def _query_range(self, query: str, lookback_seconds: int, step: str = "30s"):
        start, end = self._compute_range(lookback_seconds)
        url = f"{self.base_url}/api/v1/query_range"
        params = {"query": query, "start": start, "end": end, "step": step}
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _extract_values(self, result: dict) -> List[float]:
        try:
            series = result["data"]["result"]
            if not series:
                return []
            return [float(v[1]) for v in series[0]["values"]]
        except Exception:
            return []

    # ----------------------- CPU METRICS -----------------------

    def get_cpu_percent_series(self, container: str, lookback_seconds: int) -> List[float]:
        query = (
            f'rate(container_cpu_usage_seconds_total{{name="{container}"}}[1m]) * 100'
        )
        data = self._query_range(query, lookback_seconds)
        return self._extract_values(data)

    def get_cpu_percent_avg(self, container: str, lookback_seconds: int) -> float:
        values = self.get_cpu_percent_series(container, lookback_seconds)
        return sum(values) / len(values) if values else 0.0

    def get_cpu_percent_max(self, container: str, lookback_seconds: int) -> float:
        values = self.get_cpu_percent_series(container, lookback_seconds)
        return max(values) if values else 0.0

    def get_cpu_time_seconds(self, container: str, lookback_seconds: int) -> float:
        # CPU time is a counter, so use increase()
        query = (
            f'increase(container_cpu_usage_seconds_total{{name="{container}"}}[{lookback_seconds}s])'
        )
        result = self._query_range(query, lookback_seconds)
        values = self._extract_values(result)
        return values[-1] if values else 0.0

    # ----------------------- MEMORY METRICS -----------------------

    def get_memory_percent_series(self, container: str, lookback_seconds: int) -> List[float]:
        query = (
            f'(container_memory_usage_bytes{{name="{container}"}} / '
            f' container_spec_memory_limit_bytes{{name="{container}"}}) * 100'
        )
        data = self._query_range(query, lookback_seconds)
        return self._extract_values(data)

    def get_memory_percent_avg(self, container: str, lookback_seconds: int) -> float:
        values = self.get_memory_percent_series(container, lookback_seconds)
        return sum(values) / len(values) if values else 0.0

    def get_memory_usage_max_bytes(self, container: str, lookback_seconds: int) -> int:
        query = f'container_memory_usage_bytes{{name="{container}"}}'
        data = self._query_range(query, lookback_seconds)
        values = self._extract_values(data)
        return int(max(values)) if values else 0

    # ----------------------- NETWORK METRICS -----------------------

    def get_network_series(self, container: str, lookback_seconds: int, direction: str) -> List[float]:
        metric = "transmit" if direction == "tx" else "receive"
        query = (
            f'rate(container_network_{metric}_bytes_total{{name="{container}"}}[1m])'
        )
        data = self._query_range(query, lookback_seconds)
        return self._extract_values(data)

    def get_network_tx_avg(self, container: str, lookback_seconds: int) -> float:
        values = self.get_network_series(container, lookback_seconds, "tx")
        return sum(values) / len(values) if values else 0.0

    def get_network_tx_max(self, container: str, lookback_seconds: int) -> int:
        values = self.get_network_series(container, lookback_seconds, "tx")
        return int(max(values)) if values else 0

    def get_network_rx_avg(self, container: str, lookback_seconds: int) -> float:
        values = self.get_network_series(container, lookback_seconds, "rx")
        return sum(values) / len(values) if values else 0.0

    def get_network_rx_max(self, container: str, lookback_seconds: int) -> int:
        values = self.get_network_series(container, lookback_seconds, "rx")
        return int(max(values)) if values else 0

    # ----------------------- AGGREGATOR -----------------------

    def get_container_metrics(self, container: str, lookback_seconds: int) -> ContainerMetrics:
        return ContainerMetrics(
            cpu_percent_avg=self.get_cpu_percent_avg(container, lookback_seconds),
            cpu_percent_max=self.get_cpu_percent_max(container, lookback_seconds),
            cpu_time_seconds=self.get_cpu_time_seconds(container, lookback_seconds),

            memory_percent_avg=self.get_memory_percent_avg(container, lookback_seconds),
            memory_usage_max_bytes=self.get_memory_usage_max_bytes(container, lookback_seconds),

            network_tx_avg=self.get_network_tx_avg(container, lookback_seconds),
            network_tx_max=self.get_network_tx_max(container, lookback_seconds),
            network_rx_avg=self.get_network_rx_avg(container, lookback_seconds),
            network_rx_max=self.get_network_rx_max(container, lookback_seconds),
        )