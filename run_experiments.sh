#!/bin/bash

SCENARIOS=("local-async" "mqtt" "orbitalis-local" "orbitalis-mqtt" "local-multithread")
N_WORKERS=(1 2 4 8)
N_PRIMES=(5000 10000 20000 30000 40000 50000)
ITERATIONS=(50 100)
N_RUNS=10


for iterations in "${ITERATIONS[@]}"; do
    for scenario in "${SCENARIOS[@]}"; do
        for workers in "${N_WORKERS[@]}"; do
            for primes in "${N_PRIMES[@]}"; do
                    bash ./run_experiments_batch.sh $scenario $workers $primes $iterations $N_RUNS
                done
            done
        done
    done
done
