#!/bin/bash

N_WORKERS=(1 10 100)
N_RUNS=5

EXPERIMENTS=(
    "local-async 100 1000000"
    "local-async 1000 10000"
    "local-async 10000 100"

    "orbitalis-local 100 100000"
    "orbitalis-local 1000 10000"
    "orbitalis-local 10000 100"

    "local-multithread 100 100000"
    "local-multithread 1000 10000"
    "local-multithread 10000 100"

    "orbitalis-local-ff 100 100000"
    "orbitalis-local-ff 1000 10000"
    "orbitalis-local-ff 10000 100"

    "mqtt 100 1000"
    "mqtt 1000 1000"
    "mqtt 10000 100"

    "orbitalis-mqtt 100 50000"
    "orbitalis-mqtt 1000 10000"
    "orbitalis-mqtt 10000 100"
)

echo "Starting MQTT broker..."
docker compose up -d --build mqttbroker

echo "Starting monitoring services..."
docker compose up -d --build cadvisor prometheus

sleep 10

for experiment in "${EXPERIMENTS[@]}"; do
    read -r scenario primes iterations <<< "$experiment"
    
    for workers in "${N_WORKERS[@]}"; do
        timeout 15m ./run_experiments_batch.sh $scenario $workers $primes $iterations $N_RUNS 0

        status=$?

        if [ $status -eq 124 ]; then
            echo "Timeout reached for scenario: $scenario with $workers workers. Moving to the next configuration."
        fi
    done
done

docker compose down