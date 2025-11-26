import argparse
import asyncio
from experiments.hardware_metrics_experimenter import NonOrbitalisHardwareMetricsExperimenter
from experiments.meter.prometheus_meter import PrometheusMeter
from non_orbitalis.local.coordinator import LocalCoordinator
from non_orbitalis.local.worker import LocalWorker


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

    return parser


async def local(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int, container_name: str):
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

    print("Starting local experiment...")

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    print("Done")

    print(experiment_outcome is None)

    print("Experiment Outcome:", experiment_outcome)


async def main():

    parser = get_cli_parser()

    args = parser.parse_args()

    print("Parsed arguments:", args)

    prometheus_meter = PrometheusMeter(
        host=args.prometheus_host,
        port=args.prometheus_port
    )

    if args.scenario == "local":
        await local(
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

    


if __name__ == "__main__":
    asyncio.run(main())




