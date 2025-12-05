from dataclasses import dataclass
from typing import List, Optional
import requests
from datetime import datetime, timezone

@dataclass
class ContainerMetrics:
    # --- CPU ---
    cpu_time_seconds: float      # Absolute cost: Total CPU seconds used
    cpu_percent_avg: float       # Calculated: (cpu_time_seconds / duration) * 100
    cpu_percent_max: float       # Peak load: Max instant usage

    # --- Memory ---
    memory_usage_max_bytes: int  # Peak footprint
    memory_percent_avg: float    # Average utilization over time
    memory_usage_avg_bytes: int  # Average absolute memory footprint in bytes

    # --- Network ---
    network_tx_total_bytes: int  # Absolute cost: Total bytes sent
    network_rx_total_bytes: int  # Absolute cost: Total bytes received
    network_tx_avg: float        # Calculated: Total bytes / duration
    network_rx_avg: float        # Calculated: Total bytes / duration
    network_tx_max: int          # Peak bandwidth usage
    network_rx_max: int          # Peak bandwidth usage


@dataclass
class PrometheusMeter:
    base_url: str
    scrape_interval: int

    def __post_init__(self):
        self.base_url = self.base_url.rstrip("/")

    # ----------------------------------------------------------------------
    # Helper Methods
    # ----------------------------------------------------------------------

    def _format_dt(self, dt: datetime) -> str:
        """Ensure the datetime is UTC and ISO formatted."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()

    def _query_range(self, query: str, start: datetime, end: datetime, step: Optional[int] = None):
        """
        Query Prometheus range API using absolute timestamps.
        """
        if step is None:
            step = self.scrape_interval

        params = {
            "query": query, 
            "start": self._format_dt(start), 
            "end": self._format_dt(end), 
            "step": f"{step}s"
        }
        
        url = f"{self.base_url}/api/v1/query_range"
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def _extract_values(self, result: dict) -> List[float]:
        try:
            series = result["data"]["result"]
            if not series:
                return []
            # values is a list of [timestamp, value]
            return [float(v[1]) for v in series[0]["values"]]
        except Exception:
            return []

    def _extract_last_value(self, result: dict) -> float:
        """Helper to get the last value from a series (useful for increase/totals)."""
        values = self._extract_values(result)
        return values[-1] if values else 0.0

    def _get_duration(self, start: datetime, end: datetime) -> int:
        """Calculates duration in seconds, ensuring at least 1s to avoid division by zero."""
        duration = int((end - start).total_seconds())
        return max(duration, 1)

    # ----------------------- CPU METRICS -----------------------

    def get_cpu_time_seconds(self, container: str, start: datetime, end: datetime) -> float:
        """
        Returns the total CPU seconds consumed (User + System).
        Uses 'increase' over the exact duration to get the absolute delta.
        """
        duration = self._get_duration(start, end)
        query = (
            f'increase(container_cpu_usage_seconds_total{{name="{container}"}}[{duration}s])'
        )
        data = self._query_range(query, start, end)
        return self._extract_last_value(data)

    def get_cpu_percent_avg(self, container: str, start: datetime, end: datetime) -> float:
        """
        Mathematically precise average: Total CPU Time / Total Duration.
        Avoids the smoothing issues of rate() averages.
        """
        total_cpu = self.get_cpu_time_seconds(container, start, end)
        duration = self._get_duration(start, end)
        return (total_cpu / duration) * 100

    def get_cpu_percent_max(self, container: str, start: datetime, end: datetime) -> float:
        """
        Returns the peak CPU usage.
        Uses 'irate' (instant rate) instead of 'rate' to catch short-lived spikes 
        without smoothing them over 1 minute.
        """
        # [2m] lookback is just to find the last 2 scrape points for irate calculation
        query = (
            f'irate(container_cpu_usage_seconds_total{{name="{container}"}}[2m]) * 100'
        )
        data = self._query_range(query, start, end)
        values = self._extract_values(data)
        return max(values) if values else 0.0

    # ----------------------- MEMORY METRICS -----------------------

    def get_memory_percent_series(self, container: str, start: datetime, end: datetime) -> List[float]:
        query = (
            f'(container_memory_usage_bytes{{name="{container}"}} / '
            f' container_spec_memory_limit_bytes{{name="{container}"}}) * 100'
        )
        data = self._query_range(query, start, end)
        return self._extract_values(data)

    def get_memory_percent_avg(self, container: str, start: datetime, end: datetime) -> float:
        values = self.get_memory_percent_series(container, start, end)
        return sum(values) / len(values) if values else 0.0

    def get_memory_usage_max_bytes(self, container: str, start: datetime, end: datetime) -> int:
        query = f'container_memory_usage_bytes{{name="{container}"}}'
        data = self._query_range(query, start, end)
        values = self._extract_values(data)
        return int(max(values)) if values else 0
    
    def get_memory_usage_avg_bytes(self, container: str, start: datetime, end: datetime) -> int:
        """
        Returns the average absolute memory footprint in bytes over the time range.
        """
        query = f'container_memory_usage_bytes{{name="{container}"}}'
        data = self._query_range(query, start, end)
        values = self._extract_values(data)
        
        if not values:
            return 0
        
        # Calculate average (Sum of all data points / Count of data points)
        avg_bytes = sum(values) / len(values)
        return int(avg_bytes)



    # ----------------------- NETWORK METRICS -----------------------

    def get_network_total_bytes(self, container: str, start: datetime, end: datetime, direction: str) -> int:
        """
        Returns the total bytes transferred (absolute count) during the interval.
        """
        metric = "transmit" if direction == "tx" else "receive"
        duration = self._get_duration(start, end)
        
        # Uses increase to calculate the exact counter delta
        query = (
            f'increase(container_network_{metric}_bytes_total{{name="{container}"}}[{duration}s])'
        )
        data = self._query_range(query, start, end)
        return int(self._extract_last_value(data))

    def get_network_peak_rate(self, container: str, start: datetime, end: datetime, direction: str) -> int:
        """
        Returns the maximum bandwidth usage in Bytes/sec.
        Uses irate for instant peak detection.
        """
        metric = "transmit" if direction == "tx" else "receive"
        query = (
            f'irate(container_network_{metric}_bytes_total{{name="{container}"}}[2m])'
        )
        data = self._query_range(query, start, end)
        values = self._extract_values(data)
        return int(max(values)) if values else 0

    # ----------------------- AGGREGATOR -----------------------

    def get_container_metrics(self, container: str, start_time: datetime, end_time: datetime) -> ContainerMetrics:
        
        # Pre-calculate totals to reuse for averages
        cpu_total = self.get_cpu_time_seconds(container, start_time, end_time)
        tx_total = self.get_network_total_bytes(container, start_time, end_time, "tx")
        rx_total = self.get_network_total_bytes(container, start_time, end_time, "rx")
        duration = self._get_duration(start_time, end_time)

        return ContainerMetrics(
            # CPU
            cpu_time_seconds=cpu_total,
            cpu_percent_avg=(cpu_total / duration) * 100,
            cpu_percent_max=self.get_cpu_percent_max(container, start_time, end_time),

            # Memory
            memory_percent_avg=self.get_memory_percent_avg(container, start_time, end_time),
            memory_usage_max_bytes=self.get_memory_usage_max_bytes(container, start_time, end_time),
            memory_usage_avg_bytes=self.get_memory_usage_avg_bytes(container, start_time, end_time),

            # Network Totals (The requested absolute values)
            network_tx_total_bytes=tx_total,
            network_rx_total_bytes=rx_total,

            # Network Averages (Calculated from totals for precision)
            network_tx_avg=float(tx_total) / duration,
            network_rx_avg=float(rx_total) / duration,

            # Network Peaks
            network_tx_max=self.get_network_peak_rate(container, start_time, end_time, "tx"),
            network_rx_max=self.get_network_peak_rate(container, start_time, end_time, "rx"),
        )