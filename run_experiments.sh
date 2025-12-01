#!/bin/bash

SCENARIOS=("local" "mqtt" "orbitalis-local", "orbitalis-mqtt")

N_WORKERS=4
PRIMES=1000
ITERATIONS=100    


N_SAMPLES=2

docker compose up -d cadvisor prometheus mqttbroker

for scenario in "${SCENARIOS[@]}"; do
    for sample in $(seq 1 $N_SAMPLES); do
        OUTPUT_FILE_NAME="experiment_${scenario}_sample${sample}.json"
        echo "Running experiment: Scenario=${scenario}, Workers=${N_WORKERS}, Primes=${PRIMES}, Iterations=${ITERATIONS}, Sample=${sample}"
        
        export NUM_WORKERS=$N_WORKERS
        export PRIMES=$PRIMES
        export ITERATIONS=$ITERATIONS
        export SCENARIO=$scenario
        export OUTPUT_FILE_NAME=$OUTPUT_FILE_NAME

        docker compose up -d --build --abort-on-container-exit experiment
    done

done

docker compose down
