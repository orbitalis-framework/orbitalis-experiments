#!/bin/bash

N_WORKERS=(1 10 50)
N_RUNS=5

EXPERIMENTS=(
    "local-async 500 40000"
    "local-async 1000 10000"
    "local-async 5000 400"

    "orbitalis-local 500 40000"
    "orbitalis-local 1000 10000"
    "orbitalis-local 5000 400"

    "local-multithread 500 40000"
    "local-multithread 1000 10000"
    "local-multithread 5000 400"

    "orbitalis-local-ff 500 40000"
    "orbitalis-local-ff 1000 10000"
    "orbitalis-local-ff 5000 400"

    "mqtt 500 8000"
    "mqtt 1000 1000"
    "mqtt 5000 400"

    "orbitalis-mqtt 500 8000"
    "orbitalis-mqtt 1000 1000"
    "orbitalis-mqtt 5000 400"
)

echo "Starting MQTT broker..."
docker compose up -d --build mqttbroker

echo "Starting monitoring services..."
docker compose up -d --build cadvisor prometheus

sleep 10

for experiment in "${EXPERIMENTS[@]}"; do
    read -r scenario primes iterations <<< "$experiment"
    
    for workers in "${N_WORKERS[@]}"; do
        timeout 20m ./run_experiments_batch.sh $scenario $workers $primes $iterations $N_RUNS 0

        status=$?

        if [ $status -eq 124 ]; then
            echo "Timeout reached for scenario: $scenario with $workers workers. Moving to the next configuration."
        fi
    done
done

docker compose down