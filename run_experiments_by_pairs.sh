SCENARIOS=("local-async" "mqtt" "orbitalis-local" "orbitalis-mqtt" "local-multithread" "orbitalis-local-ff")
N_WORKERS=(1 10 100)
WORKLOAD_PAIRS=("100 50000" "1000 500" "10000 5")
N_RUNS=5

echo "Starting MQTT broker..."
docker compose up -d --build mqttbroker

echo "Starting monitoring services..."
docker compose up -d --build cadvisor prometheus

sleep 10

for scenario in "${SCENARIOS[@]}"; do
    for workers in "${N_WORKERS[@]}"; do
        for pair in "${WORKLOAD_PAIRS[@]}"; do
            read -r primes iterations <<< "$pair"
            bash ./run_experiments_batch.sh $scenario $workers $primes $iterations $N_RUNS 0
        done
    done
done

docker compose down