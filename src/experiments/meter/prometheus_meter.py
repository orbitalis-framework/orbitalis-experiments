import requests
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


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
    """
    A client that queries Prometheus for container metrics within a time range.
    All methods receive:
        - container_name
        - start_time (datetime)
        - end_time (datetime)
    """

    def __init__(self, host, port=9090):
        self.base_url = f"http://{host}:{port}/api/v1/query_range"

    # --------------------------
    # INTERNAL UTILITIES
    # --------------------------

    def _query_range(self, query: str, start: datetime, end: datetime, step: str = "1s"):
        params = {
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step,
        }
        response = requests.get(self.base_url, params=params)
        response.raise_for_status()
        data = response.json()

        if data["status"] != "success":
            raise RuntimeError("Prometheus query failed:", data)

        # Return values in the form [(timestamp, value), ...]
        result = data["data"]["result"]
        if not result:
            return []

        return [(float(ts), float(value)) for ts, value in result[0]["values"]]

    def _delta(self, series):
        """Compute difference between the first and last cumulative metric."""
        if len(series) < 2:
            return 0
        return series[-1][1] - series[0][1]

    # --------------------------
    # CPU METRICS
    # --------------------------

    def cpu_time_seconds(self, container: str, start: datetime, end: datetime) -> float:
        q = f'rate(container_cpu_usage_seconds_total{{name="{container}"}}[1s])'
        series = self._query_range(q, start, end)
        # sum of rates * interval length
        return sum(v for _, v in series)

    def cpu_percent_avg(self, container: str, start: datetime, end: datetime) -> float:
        q = f'rate(container_cpu_usage_seconds_total{{name="{container}"}}[1s])'
        series = self._query_range(q, start, end)
        return sum(v for _, v in series) / (end - start).total_seconds() * 100

    def cpu_percent_max(self, container: str, start: datetime, end: datetime) -> float:
        q = f'rate(container_cpu_usage_seconds_total{{name="{container}"}}[1s])'
        series = self._query_range(q, start, end)
        return max((v for _, v in series), default=0) * 100

    # --------------------------
    # MEMORY METRICS
    # --------------------------

    def memory_percent_avg(self, container: str, start: datetime, end: datetime) -> float:
        usage_q = f'container_memory_usage_bytes{{name="{container}"}}'
        limit_q = f'container_spec_memory_limit_bytes{{name="{container}"}}'

        usage_series = self._query_range(usage_q, start, end)
        limit_series = self._query_range(limit_q, start, end)

        # No data at all
        if not usage_series or not limit_series:
            return 0.0

        limit = limit_series[-1][1]

        # Container has no memory limit → avoid division by zero
        if limit == 0:
            return 0.0

        return sum(v for _, v in usage_series) / len(usage_series) / limit * 100

    def memory_usage_max(self, container: str, start: datetime, end: datetime) -> int:
        q = f'container_memory_usage_bytes{{name="{container}"}}'
        series = self._query_range(q, start, end)
        return int(max((v for _, v in series), default=0))

    # --------------------------
    # NETWORK METRICS
    # --------------------------

    def network_tx_avg(self, container: str, start: datetime, end: datetime) -> float:
        q = f'rate(container_network_transmit_bytes_total{{name="{container}"}}[1s])'
        series = self._query_range(q, start, end)
        return sum(v for _, v in series) / len(series) if series else 0

    def network_tx_max(self, container: str, start: datetime, end: datetime) -> int:
        q = f'rate(container_network_transmit_bytes_total{{name="{container}"}}[1s])'
        series = self._query_range(q, start, end)
        return int(max((v for _, v in series), default=0))

    def network_rx_avg(self, container: str, start: datetime, end: datetime) -> float:
        q = f'rate(container_network_receive_bytes_total{{name="{container}"}}[1s])'
        series = self._query_range(q, start, end)
        return sum(v for _, v in series) / len(series) if series else 0

    def network_rx_max(self, container: str, start: datetime, end: datetime) -> int:
        q = f'rate(container_network_receive_bytes_total{{name="{container}"}}[1s])'
        series = self._query_range(q, start, end)
        return int(max((v for _, v in series), default=0))

    # --------------------------
    # FULL RESULT
    # --------------------------

    def measure_all(self, container: str, start: datetime, end: datetime) -> ContainerMetrics:

        return ContainerMetrics(
            cpu_percent_avg=self.cpu_percent_avg(container, start, end),
            cpu_percent_max=self.cpu_percent_max(container, start, end),
            cpu_time_seconds=self.cpu_time_seconds(container, start, end),
            memory_percent_avg=self.memory_percent_avg(container, start, end),
            memory_usage_max_bytes=self.memory_usage_max(container, start, end),
            network_tx_avg=self.network_tx_avg(container, start, end),
            network_tx_max=self.network_tx_max(container, start, end),
            network_rx_avg=self.network_rx_avg(container, start, end),
            network_rx_max=self.network_rx_max(container, start, end)
        )