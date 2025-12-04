#!/bin/bash

SCENARIOS=("local-async" "mqtt" "orbitalis-local" "orbitalis-mqtt" "local-multithread" "orbitalis-local-ff")
N_WORKERS=(1)
N_PRIMES=(10000)
ITERATIONS=(5)
N_RUNS=3

echo "Starting MQTT broker..."
docker compose up -d --build mqttbroker

echo "Starting monitoring services..."
docker compose up -d --build cadvisor prometheus

sleep 10  # Give some time for services to start

for iterations in "${ITERATIONS[@]}"; do
    for scenario in "${SCENARIOS[@]}"; do
        for workers in "${N_WORKERS[@]}"; do
            for primes in "${N_PRIMES[@]}"; do
                bash ./run_experiments_batch.sh $scenario $workers $primes $iterations $N_RUNS 0
            done
        done
    done
done

docker compose down