#!/bin/bash

SCENARIO=$1
N_WORKERS=$2
PRIMES=$3
ITERATIONS=$4
N_RUNS=$5

echo "Starting monitoring services..."
docker compose up -d --build cadvisor prometheus

echo "Starting MQTT broker..."
docker compose up -d --build mqttbroker

sleep 10  # Give some time for services to start

echo "Running experiments..."
for run in $(seq 1 $N_RUNS); do

    export NUM_WORKERS=$N_WORKERS
    export PRIMES=$PRIMES
    export ITERATIONS=$ITERATIONS
    export SCENARIO=$SCENARIO
    export EXPERIMENT_CONTAINER_NAME="experiment_${SCENARIO}_w${N_WORKERS}_p${PRIMES}_i${ITERATIONS}_run${run}"

    now=$(date +"%Y%m%d_%H%M%S")
    export OUTPUT_FILE_NAME="${EXPERIMENT_CONTAINER_NAME}_${now}.json"

    echo "Running experiment: Scenario=${SCENARIO}, Workers=${N_WORKERS}, Primes=${PRIMES}, Iterations=${ITERATIONS}, Run=${run}"

    docker compose up --build --abort-on-container-exit experiment

    sleep 2  # Short pause between experiments

done

docker compose down