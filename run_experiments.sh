#!/bin/bash

N_RUNS=5

EXPERIMENTS=(
    # === Local Async ===
    "local-async 1 500 20000"
    "local-async 1 1000 5000"
    "local-async 1 5000 200"

    "local-async 10 500 20000"
    "local-async 10 1000 5000"
    "local-async 10 5000 200"

    "local-async 50 500 20000"
    "local-async 50 1000 5000"
    "local-async 50 5000 200"

    # === Orbitalis Local ===
    "orbitalis-local 1 500 20000"
    "orbitalis-local 1 1000 5000"
    "orbitalis-local 1 5000 200"

    "orbitalis-local 10 500 20000"
    "orbitalis-local 10 1000 5000"
    "orbitalis-local 10 5000 200"

    "orbitalis-local 50 500 20000"
    "orbitalis-local 50 1000 5000"
    "orbitalis-local 50 5000 200"

    # === Local Multithread ===
    "local-multithread 1 500 20000"
    "local-multithread 1 1000 5000"
    "local-multithread 1 5000 200"

    "local-multithread 10 500 20000"
    "local-multithread 10 1000 5000"
    "local-multithread 10 5000 200"

    "local-multithread 50 500 20000"
    "local-multithread 50 1000 5000"
    "local-multithread 50 5000 200"

    # === Orbitalis Local FF ===
    "orbitalis-local-ff 1 500 20000"
    "orbitalis-local-ff 1 1000 5000"
    "orbitalis-local-ff 1 5000 200"

    "orbitalis-local-ff 10 500 20000"
    "orbitalis-local-ff 10 1000 5000"
    "orbitalis-local-ff 10 5000 200"

    "orbitalis-local-ff 50 500 20000"
    "orbitalis-local-ff 50 1000 5000"
    "orbitalis-local-ff 50 5000 200"

    # === MQTT ===
    "mqtt 1 500 8000"
    "mqtt 1 1000 4000"
    "mqtt 1 5000 300"

    "mqtt 10 500 2000"
    "mqtt 10 1000 2000"
    "mqtt 10 5000 300"

    "mqtt 50 500 800"
    "mqtt 50 1000 1000"
    "mqtt 50 5000 300"

    # === Orbitalis MQTT ===
    "orbitalis-mqtt 1 500 8000"
    "orbitalis-mqtt 1 1000 4000"
    "orbitalis-mqtt 1 5000 300"

    "orbitalis-mqtt 10 500 2000"
    "orbitalis-mqtt 10 1000 2000"
    "orbitalis-mqtt 10 5000 300"

    "orbitalis-mqtt 50 500 800"
    "orbitalis-mqtt 50 1000 1000"
    "orbitalis-mqtt 50 5000 300"

    # === Orbitalis MQTT FF ===
    "orbitalis-mqtt-ff 1 500 8000"
    "orbitalis-mqtt-ff 1 1000 4000"
    "orbitalis-mqtt-ff 1 5000 300"

    "orbitalis-mqtt-ff 10 500 2000"
    "orbitalis-mqtt-ff 10 1000 2000"
    "orbitalis-mqtt-ff 10 5000 300"

    "orbitalis-mqtt-ff 50 500 800"
    "orbitalis-mqtt-ff 50 1000 1000"
    "orbitalis-mqtt-ff 50 5000 300"
)

echo "Starting MQTT broker..."
docker compose up -d --build mqttbroker

echo "Starting monitoring services..."
docker compose up -d --build cadvisor prometheus

sleep 10

for experiment in "${EXPERIMENTS[@]}"; do
    read -r scenario workers primes iterations <<< "$experiment"
    
    timeout 20m ./run_experiments_batch.sh $scenario $workers $primes $iterations $N_RUNS 0

    status=$?

    if [ $status -eq 124 ]; then
        echo "Timeout reached for scenario: $scenario with $workers workers. Moving to the next configuration."
    fi
done

docker compose down