import argparse
import asyncio
import json
from experiments.hardware_metrics_experimenter import HardwareMetricsExperimentOutcome, NonOrbitalisHardwareMetricsExperimenter
from experiments.meter.prometheus_meter import PrometheusMeter
from non_orbitalis.local.coordinator import LocalCoordinator
from non_orbitalis.local.worker import LocalWorker
import paho.mqtt.client as mqtt
from non_orbitalis.mqtt.coordinator import MqttCoordinator
from non_orbitalis.mqtt.worker import MqttWorker

def get_cli_parser():
    parser = argparse.ArgumentParser(
        description="CLI program for running prime computation scenarios."
    )

    parser.add_argument(
        "--container-name",
        type=str,
        required=True,
        help="Name of the container."
    )

    parser.add_argument(
        "--workers",
        type=int,
        required=True,
        help="Number of workers."
    )

    parser.add_argument(
        "--prometheus-host",
        type=str,
        required=True,
        help="Prometheus host."
    )

    parser.add_argument(
        "--prometheus-port",
        type=int,
        required=True,
        help="Prometheus port."
    )

    parser.add_argument(
        "--primes",
        type=int,
        required=True,
        help="Number of primes to compute."
    )

    parser.add_argument(
        "--iterations",
        type=int,
        required=True,
        help="Number of iterations."
    )

    parser.add_argument(
        "--scenario",
        type=str,
        required=True,
        choices=["local", "mqtt", "orbitalis-local", "orbitalis-mqtt"],
        help="Execution scenario."
    )

    parser.add_argument(
        "--output-path",
        type=str,
        required=True,
        help="Output file path."
    )

    return parser

def dump_experiment(n_workers: int, n_primes: int, n_iterations: int, scenario: str, outcome: HardwareMetricsExperimentOutcome, output_path: str):
    experiment = {
        "n_workers": n_workers,
        "n_primes": n_primes,
        "n_iterations": n_iterations,
        "scenario": scenario,
        "outcome": outcome.to_dict()
    }

    with open(output_path, "w") as f:
        json.dump(experiment, f, indent=4)

async def local(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int, container_name: str) -> HardwareMetricsExperimentOutcome:
    workers = [
        LocalWorker(identifier=f"worker_{i}") for i in range(n_workers)
    ]

    coordinator = LocalCoordinator(workers=workers)

    experimenter = NonOrbitalisHardwareMetricsExperimenter(
        coordinator=coordinator,
        primes_range_start=1,
        primes_range_end=n_primes,
        experiment_container_name=container_name,
        meter=meter
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    return experiment_outcome

async def mqtt(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int, container_name: str) -> HardwareMetricsExperimentOutcome:
    worker_clients = [
            mqtt.Client(client_id=f"worker_{i}") for i in range(n_workers)
        ]

        coordinator_client = mqtt.Client(client_id="coordinator")

        # Connect and start all clients to the MQTT broker
        coordinator_client.connect("brokermqtt", 1883, 60)
        coordinator_client.loop_start()

        for worker_client in worker_clients:
            worker_client.connect("brokermqtt", 1883, 60)
            worker_client.loop_start()

        # Set up the workers
        workers = [
            MqttWorker(
                client=worker_client,
            )
            for worker_client in worker_clients
        ]

        # Set up the coordinator
        coordinator = MqttCoordinator(
            client=coordinator_client,
            worker_input_topics=[worker.input_topic for worker in workers],
            worker_output_topic="coordinator/output"
        )

    experimenter = NonOrbitalisHardwareMetricsExperimenter(
        coordinator=coordinator,
        primes_range_start=1,
        primes_range_end=n_primes,
        experiment_container_name=container_name,
        meter=meter
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    return experiment_outcome

async def main():

    parser = get_cli_parser()

    args = parser.parse_args()

    print("Parsed arguments:", args)

    prometheus_meter = PrometheusMeter(
        base_url=f"http://{args.prometheus_host}:{args.prometheus_port}"
    )

    if args.scenario == "local":
        outcome = await local(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name
        )

    elif args.scenario == "mqtt":
        raise NotImplementedError("MQTT scenario is not implemented yet.")
    
    elif args.scenario == "orbitalis-local":
        raise NotImplementedError("Orbitalis Local scenario is not implemented yet.")
    
    elif args.scenario == "orbitalis-mqtt":
        raise NotImplementedError("Orbitalis MQTT scenario is not implemented yet.")
    
    else:
        raise ValueError(f"Unknown scenario: {args.scenario}")

    dump_experiment(
        n_workers=args.workers,
        n_primes=args.primes,
        n_iterations=args.iterations,
        scenario=args.scenario,
        outcome=outcome,
        output_path=args.output_path
    )


if __name__ == "__main__":
    asyncio.run(main())




