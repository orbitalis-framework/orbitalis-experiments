import argparse
import asyncio
import json
import logging
import os
import yappi
import tracemalloc

from orbitalis.core.requirement import Constraint, OperationRequirement
from orbitalis.orbiter.schemaspec import Input, Output

from experiments.hardware_metrics_experimenter import HardwareMetricsExperimentOutcome, \
    HardwareMetricsExperimenterPrimeNumbers, OrbitalisDiscoveryExperimenter
from experiments.meter.prometheus_meter import PrometheusMeter
from without_orbitalis.local_async.coordinator import LocalAsyncCoordinator
from without_orbitalis.local_async.worker import LocalAsyncWorker
from without_orbitalis.local_multithread.coordinator import LocalMultithreadCoordinator
from without_orbitalis.local_multithread.worker import LocalMultithreadWorker
from with_orbitalis.coordinator import OrbitalisCoordinator
from with_orbitalis.worker import OrbitalisWorker, RangeMessage, PrimeNumbersMessage
from without_orbitalis.mqtt.coordinator import MqttCoordinator
from without_orbitalis.mqtt.worker import MqttWorker
from utils.busline_builder import build_new_local_client, build_new_mqtt_client


logging.basicConfig(level=logging.ERROR)

PROFILE_TYPE = "cpu"

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
        "--mqtt-broker-host",
        type=str,
        required=False,
        help="MQTT broker host."
    )

    parser.add_argument(
        "--mqtt-broker-port",
        type=int,
        required=False,
        help="MQTT broker port."
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
        "--prometheus-scrape-interval",
        type=int,
        required=True,
        help="Prometheus scrape interval."
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
        choices=["local-multithread", "local-async", "mqtt", "orbitalis-local", "orbitalis-local-ff", "orbitalis-mqtt", "orbitalis-mqtt-ff",
                 "orbitalis-local-discovery", "orbitalis-mqtt-discovery"],
        help="Execution scenario."
    )

    parser.add_argument(
        "--output-path",
        type=str,
        required=True,
        help="Output file path."
    )

    parser.add_argument(
        "--profile",
        action="store_true",
        help="If set, enables profiling."
    )

    return parser


def dump_experiment(n_workers: int, n_primes: int, n_iterations: int, scenario: str,
                    outcome: HardwareMetricsExperimentOutcome, output_path: str):
    experiment = {
        "n_workers": n_workers,
        "n_primes": n_primes,
        "n_iterations": n_iterations,
        "scenario": scenario,
        "outcome": outcome.to_dict()
    }

    with open(output_path, "w") as f:
        json.dump(experiment, f, indent=4)


async def without_orbitalis_local_multithread(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int,
                                              container_name: str, profiling: bool = False) -> HardwareMetricsExperimentOutcome:
    workers = [
        LocalMultithreadWorker(identifier=f"worker_{i}") for i in range(n_workers)
    ]

    coordinator = LocalMultithreadCoordinator(workers=workers)

    experimenter = HardwareMetricsExperimenterPrimeNumbers(
        coordinator=coordinator,
        primes_range_start=1,
        primes_range_end=n_primes,
        experiment_container_name=container_name,
        meter=meter,
        profiling=profiling,
        profiling_type=PROFILE_TYPE,
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    return experiment_outcome


async def without_orbitalis_local_async(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int,
                                        container_name: str, profiling: bool = False) -> HardwareMetricsExperimentOutcome:
    workers = [
        LocalAsyncWorker(identifier=f"worker_{i}") for i in range(n_workers)
    ]

    coordinator = LocalAsyncCoordinator(workers=workers)

    experimenter = HardwareMetricsExperimenterPrimeNumbers(
        coordinator=coordinator,
        primes_range_start=1,
        primes_range_end=n_primes,
        experiment_container_name=container_name,
        meter=meter,
        profiling=profiling,
        profiling_type=PROFILE_TYPE,
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    return experiment_outcome


async def without_orbitalis_mqtt(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int,
                                 container_name: str, mqtt_broker_host: str,
                                 mqtt_broker_port: int, profiling: bool = False) -> HardwareMetricsExperimentOutcome:
    # Set up the workers
    workers = [
        MqttWorker(
            input_topic=f"worker/input/{i}",
            broker_host=mqtt_broker_host,
            broker_port=mqtt_broker_port
        )
        for i in range(n_workers)
    ]

    worker_run_tasks = []
    for worker in workers:
        worker_run_tasks.append(asyncio.create_task(worker.run()))

    # Set up the coordinator
    coordinator = MqttCoordinator(
        worker_input_topics=[worker.input_topic for worker in workers],
        worker_output_topic="coordinator/output",
        broker_host=mqtt_broker_host,
        broker_port=mqtt_broker_port,
        profiling_type=PROFILE_TYPE,
    )

    experimenter = HardwareMetricsExperimenterPrimeNumbers(
        coordinator=coordinator,
        primes_range_start=1,
        primes_range_end=n_primes,
        experiment_container_name=container_name,
        meter=meter,
        profiling=profiling,
        profiling_type=PROFILE_TYPE,
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    for task in worker_run_tasks:
        task.cancel()

    return experiment_outcome


async def orbitalis_local(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int,
                          container_name: str, execute_fire_and_forget: bool, profiling: bool = False) -> HardwareMetricsExperimentOutcome:
    workers = [
        OrbitalisWorker(identifier=f"worker_{i}", eventbus_client=build_new_local_client(),
                        raise_exceptions=True,
                        fire_and_forget=execute_fire_and_forget,
                        with_loop=False) for i in range(n_workers)
    ]

    coordinator = OrbitalisCoordinator(
                        eventbus_client=build_new_local_client(), with_loop=False,
                        raise_exceptions=True,
                        operation_requirements={
                            "calculate_prime_numbers": OperationRequirement(Constraint(
                                inputs=[Input.from_schema(RangeMessage.avro_schema())],
                                outputs=[Output.from_schema(PrimeNumbersMessage.avro_schema())],
                                mandatory=[worker.identifier for worker in workers],
                            ))
                        },
                        execute_fire_and_forget=execute_fire_and_forget
                    )

    for worker in workers:
        await worker.start()

    await coordinator.start()

    await coordinator.compliant_event.wait()

    experimenter = HardwareMetricsExperimenterPrimeNumbers(
        coordinator=coordinator,
        primes_range_start=1,
        primes_range_end=n_primes,
        experiment_container_name=container_name,
        meter=meter,
        profiling=profiling,
        profiling_type=PROFILE_TYPE,
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    for worker in workers:
        await worker.stop()

    await coordinator.stop()

    await asyncio.sleep(1)

    return experiment_outcome


async def orbitalis_mqtt(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int,
                         container_name: str, mqtt_broker_host: str,
                         mqtt_broker_port: int, execute_fire_and_forget: bool,
                         profiling: bool = False) -> HardwareMetricsExperimentOutcome:
    workers = [
        OrbitalisWorker(identifier=f"worker_{i}",
                        fire_and_forget=execute_fire_and_forget,
                        eventbus_client=build_new_mqtt_client(mqtt_broker_host, mqtt_broker_port),
                        raise_exceptions=True,
                        with_loop=False) for i in range(n_workers)
    ]

    coordinator = OrbitalisCoordinator(eventbus_client=build_new_mqtt_client(mqtt_broker_host, mqtt_broker_port),
                                       with_loop=False, raise_exceptions=True, execute_fire_and_forget=execute_fire_and_forget,
                                       operation_requirements={
                                           "calculate_prime_numbers": OperationRequirement(Constraint(
                                               inputs=[Input.from_schema(RangeMessage.avro_schema())],
                                               outputs=[Output.from_schema(PrimeNumbersMessage.avro_schema())],
                                               mandatory=[worker.identifier for worker in workers],
                                           ))
                                       })

    for worker in workers:
        await worker.start()
    await coordinator.start()

    await coordinator.compliant_event.wait()

    experimenter = HardwareMetricsExperimenterPrimeNumbers(
        coordinator=coordinator,
        primes_range_start=1,
        primes_range_end=n_primes,
        experiment_container_name=container_name,
        meter=meter,
        profiling=profiling,
        profiling_type=PROFILE_TYPE,
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    for worker in workers:
        await worker.stop()
        
    await coordinator.stop()

    await asyncio.sleep(1)

    return experiment_outcome


async def orbitalis_local_discovery(meter: PrometheusMeter, n_workers: int, n_iterations: int,
                                    container_name: str) -> HardwareMetricsExperimentOutcome:
    workers = [
        OrbitalisWorker(identifier=f"worker_{i}", eventbus_client=build_new_local_client(),
                        raise_exceptions=True,
                        with_loop=False) for i in range(n_workers)
    ]

    for worker in workers:
        await worker.start()

    experimenter = OrbitalisDiscoveryExperimenter(
        workers=workers,
        experiment_container_name=container_name,
        meter=meter,
        build_new_client=lambda: build_new_local_client()
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    return experiment_outcome


async def orbitalis_mqtt_discovery(meter: PrometheusMeter, n_workers: int, n_iterations: int,
                                   container_name: str, mqtt_broker_host: str,
                                   mqtt_broker_port: int) -> HardwareMetricsExperimentOutcome:
    workers = [
        OrbitalisWorker(identifier=f"worker_{i}",
                        eventbus_client=build_new_mqtt_client(mqtt_broker_host, mqtt_broker_port),
                        raise_exceptions=True,
                        with_loop=False) for i in range(n_workers)
    ]

    for worker in workers:
        await worker.start()

    experimenter = OrbitalisDiscoveryExperimenter(
        workers=workers,
        experiment_container_name=container_name,
        meter=meter,
        build_new_client=lambda: build_new_mqtt_client(mqtt_broker_host, mqtt_broker_port)
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    return experiment_outcome


async def main():
    parser = get_cli_parser()

    args = parser.parse_args()

    print("Parsed arguments:", args)

    prometheus_meter = PrometheusMeter(
        base_url=f"http://{args.prometheus_host}:{args.prometheus_port}",
        scrape_interval=args.prometheus_scrape_interval
    )

    if args.scenario == "local-multithread":
        outcome = await without_orbitalis_local_multithread(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name,
            profiling=args.profile,
        )

    elif args.scenario == "local-async":
        outcome = await without_orbitalis_local_async(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name,
            profiling=args.profile,
        )

    elif args.scenario == "mqtt":
        outcome = await without_orbitalis_mqtt(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name,
            mqtt_broker_host=args.mqtt_broker_host,
            mqtt_broker_port=args.mqtt_broker_port,
            profiling=args.profile,
        )

    elif args.scenario == "orbitalis-local":
        outcome = await orbitalis_local(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name,
            execute_fire_and_forget=False,
            profiling=args.profile,
        )

    elif args.scenario == "orbitalis-local-ff":
        outcome = await orbitalis_local(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name,
            execute_fire_and_forget=True,
            profiling=args.profile,
        )
        

    elif args.scenario == "orbitalis-mqtt":
        outcome = await orbitalis_mqtt(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name,
            mqtt_broker_host=args.mqtt_broker_host,
            mqtt_broker_port=args.mqtt_broker_port,
            execute_fire_and_forget=False,
            profiling=args.profile,
        )

    elif args.scenario == "orbitalis-mqtt-ff":
        outcome = await orbitalis_mqtt(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name,
            mqtt_broker_host=args.mqtt_broker_host,
            mqtt_broker_port=args.mqtt_broker_port,
            execute_fire_and_forget=True,
            profiling=args.profile,
        )

    elif args.scenario == "orbitalis-local-discovery":
        outcome = await orbitalis_local_discovery(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_iterations=args.iterations,
            container_name=args.container_name,
        )

    elif args.scenario == "orbitalis-mqtt-discovery":
        outcome = await orbitalis_mqtt_discovery(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_iterations=args.iterations,
            container_name=args.container_name,
            mqtt_broker_host=args.mqtt_broker_host,
            mqtt_broker_port=args.mqtt_broker_port
        )

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
