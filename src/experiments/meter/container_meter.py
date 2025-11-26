from experiments.meter.prometheus_meter import PrometheusMeter


class ContainerMeter:
    def __init__(self, container_name: str, prometheus_client: PrometheusMeter):
        self.container = container_name
        self.prom = prometheus_client

    def cpu_percent_avg(self, start, end):
        return self.prom.cpu_percent_avg(self.container, start, end)

    def cpu_percent_max(self, start, end):
        return self.prom.cpu_percent_max(self.container, start, end)

    def cpu_time_seconds(self, start, end):
        return self.prom.cpu_time_seconds(self.container, start, end)

    def memory_percent_avg(self, start, end):
        return self.prom.memory_percent_avg(self.container, start, end)

    def memory_usage_max(self, start, end):
        return self.prom.memory_usage_max(self.container, start, end)

    def network_tx_avg(self, start, end):
        return self.prom.network_tx_avg(self.container, start, end)

    def network_tx_max(self, start, end):
        return self.prom.network_tx_max(self.container, start, end)

    def network_rx_avg(self, start, end):
        return self.prom.network_rx_avg(self.container, start, end)

    def network_rx_max(self, start, end):
        return self.prom.network_rx_max(self.container, start, end)

    def measure_all(self, start, end):
        return self.prom.measure_all(self.container, start, end)