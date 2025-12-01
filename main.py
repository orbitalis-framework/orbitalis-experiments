import argparse
import asyncio
import json
import time

from busline.client.pubsub_client import PubSubClient, PubSubClientBuilder
from busline.local.eventbus.local_eventbus import LocalEventBus
from busline.local.local_publisher import LocalPublisher
from busline.local.local_subscriber import LocalSubscriber
from busline.mqtt.mqtt_publisher import MqttPublisher
from busline.mqtt.mqtt_subscriber import MqttSubscriber
from orbitalis.core.requirement import Constraint, OperationRequirement
from orbitalis.orbiter.schemaspec import Input, Output

from experiments.hardware_metrics_experimenter import HardwareMetricsExperimentOutcome, HardwareMetricsExperimenterPrimeNumbers
from experiments.meter.prometheus_meter import PrometheusMeter
from non_orbitalis.local.coordinator import LocalCoordinator
from non_orbitalis.local.worker import LocalWorker
from with_orbitalis.coordinator import OrbitalisCoordinator
from with_orbitalis.worker import OrbitalisWorker, RangeMessage, PrimeNumbersMessage
import paho.mqtt.client as mqtt
from non_orbitalis.mqtt.coordinator import MqttCoordinator
from non_orbitalis.mqtt.worker import MqttWorker

def build_new_local_client() -> PubSubClient:
    return PubSubClientBuilder().with_subscriber(LocalSubscriber(eventbus=LocalEventBus())).with_publisher(
        LocalPublisher(eventbus=LocalEventBus())).build()


def build_new_mqtt_client(hostname: str) -> PubSubClient:
    return PubSubClientBuilder().with_subscriber(MqttSubscriber(hostname=hostname)).with_publisher(
        MqttPublisher(hostname=hostname)).build()


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
        required=True,
        help="MQTT broker host."
    )

    parser.add_argument(
        "--mqtt-broker-port",
        type=int,
        required=True,
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


def dump_experiment(n_workers: int, n_primes: int, n_iterations: int, scenario: str,
                    outcome: HardwareMetricsExperimentOutcome, output_path: str):
    experiment = {
        "n_workers": n_workers,
        "n_primes": n_primes,
        "n_iterations": n_iterations,
        "scenario": scenario,
        "outcome": outcome.to_dict()
    }

    with open(output_path + "/output.json", "w") as f:
        json.dump(experiment, f, indent=4)


async def non_orbitalis_local(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int,
                container_name: str) -> HardwareMetricsExperimentOutcome:
    workers = [
        LocalWorker(identifier=f"worker_{i}") for i in range(n_workers)
    ]

    coordinator = LocalCoordinator(workers=workers)

    experimenter = HardwareMetricsExperimenterPrimeNumbers(
        coordinator=coordinator,
        primes_range_start=1,
        primes_range_end=n_primes,
        experiment_container_name=container_name,
        meter=meter
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    return experiment_outcome


async def non_orbitalis_mqtt(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int, container_name: str, mqtt_broker_host: str, mqtt_broker_port: int) -> HardwareMetricsExperimentOutcome:
    
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
        broker_port=mqtt_broker_port
    )

    experimenter = HardwareMetricsExperimenterPrimeNumbers(
        coordinator=coordinator,
        primes_range_start=1,
        primes_range_end=n_primes,
        experiment_container_name=container_name,
        meter=meter
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    for task in worker_run_tasks:
        task.cancel()

    return experiment_outcome


async def orbitalis_local(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int,
                          container_name: str) -> HardwareMetricsExperimentOutcome:

    workers = [
        OrbitalisWorker(identifier=f"worker_{i}", eventbus_client=build_new_local_client(), raise_exceptions=True,
                        with_loop=False) for i in range(n_workers)
    ]

    coordinator = OrbitalisCoordinator(eventbus_client=build_new_local_client(), with_loop=False, raise_exceptions=True,
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

    await asyncio.sleep(2)

    experimenter = HardwareMetricsExperimenterPrimeNumbers(
        coordinator=coordinator,
        primes_range_start=1,
        primes_range_end=n_primes,
        experiment_container_name=container_name,
        meter=meter
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    for worker in workers:
        await worker.stop()
    await coordinator.stop()

    await asyncio.sleep(1)

    return experiment_outcome


async def orbitalis_mqtt(meter: PrometheusMeter, n_workers: int, n_primes: int, n_iterations: int,
                         container_name: str, emqx_hostname: str) -> HardwareMetricsExperimentOutcome:
    workers = [
        OrbitalisWorker(identifier=f"worker_{i}", eventbus_client=build_new_mqtt_client(emqx_hostname), raise_exceptions=True,
                        with_loop=False) for i in range(n_workers)
    ]

    coordinator = OrbitalisCoordinator(eventbus_client=build_new_mqtt_client(emqx_hostname), with_loop=False, raise_exceptions=True,
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

    await asyncio.sleep(2)

    experimenter = HardwareMetricsExperimenterPrimeNumbers(
        coordinator=coordinator,
        primes_range_start=1,
        primes_range_end=n_primes,
        experiment_container_name=container_name,
        meter=meter
    )

    experiment_outcome = await experimenter.run_experiments(n_iterations=n_iterations)

    for worker in workers:
        await worker.stop()
    await coordinator.stop()

    await asyncio.sleep(1)

    return experiment_outcome


async def main():

    parser = get_cli_parser()

    args = parser.parse_args()

    print("Parsed arguments:", args)

    prometheus_meter = PrometheusMeter(
        base_url=f"http://{args.prometheus_host}:{args.prometheus_port}"
    )

    if args.scenario == "local":
        outcome = await non_orbitalis_local(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name
        )

    elif args.scenario == "mqtt":
        outcome = await non_orbitalis_mqtt(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name,
            mqtt_broker_host=args.mqtt_broker_host,
            mqtt_broker_port=args.mqtt_broker_port
        )

    elif args.scenario == "orbitalis-local":
        outcome = await orbitalis_local(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name
        )

    elif args.scenario == "orbitalis-mqtt":
        outcome = await orbitalis_mqtt(
            meter=prometheus_meter,
            n_workers=args.workers,
            n_primes=args.primes,
            n_iterations=args.iterations,
            container_name=args.container_name,
            emqx_hostname=args.emqx_host
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
    time.sleep(10)  # Wait for dependent services to be up (emqx)
    asyncio.run(main())
