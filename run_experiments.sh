#!/bin/bash

SCENARIOS=("orbitalis-local") # ("local-async" "mqtt" "orbitalis-local" "orbitalis-mqtt" "local-multithread" "orbitalis-local-ff")
N_WORKERS=(1 8)
N_PRIMES=(5000) # (5000 10000 20000 30000 40000) 
ITERATIONS=(50)
N_RUNS=2

for iterations in "${ITERATIONS[@]}"; do
    for scenario in "${SCENARIOS[@]}"; do
        for workers in "${N_WORKERS[@]}"; do
            for primes in "${N_PRIMES[@]}"; do
                bash ./run_experiments_batch.sh $scenario $workers $primes $iterations $N_RUNS
            done
        done
    done
done

docker compose down