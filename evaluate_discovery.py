import argparse
import json
import os
import statistics
from collections import defaultdict

def calculate_stats(values):
    if not values:
        return 0.0, 0.0
    mean_val = statistics.mean(values)
    if len(values) > 1:
        var_val = statistics.variance(values)
    else:
        var_val = 0.0
    return mean_val, var_val

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory_path", type=str)
    args = parser.parse_args()

    grouped_data = defaultdict(lambda: {"metric_1": [], "metric_2": []})

    if not os.path.isdir(args.directory_path):
        print(f"Error: Directory {args.directory_path} not found.")
        return

    for filename in os.listdir(args.directory_path):
        if filename.endswith(".json"):
            file_path = os.path.join(args.directory_path, filename)
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)

                scenario = data.get("scenario")
                n_workers = data.get("n_workers")
                n_iterations = data.get("n_iterations")
                outcome = data.get("outcome", {})
                total_time = outcome.get("total_time_in_seconds")

                if None in [scenario, n_workers, n_iterations, total_time]:
                    continue

                if n_iterations == 0 or n_workers == 0:
                    continue

                val_1 = total_time / n_iterations
                val_2 = total_time / (n_iterations * n_workers)

                key = (scenario, n_workers)
                grouped_data[key]["metric_1"].append(val_1)
                grouped_data[key]["metric_2"].append(val_2)

            except Exception as e:
                print(f"Skipping {filename}: {e}")

    header = f"{'Scenario':<30} | {'Wrk':<4} | {'Time Mean (s)':<15} | {'Time Var':<12} | {'Time/Wrk Mean (s)':<20} | {'Time/Wrk Var':<12}"
    print(header)
    print("-" * len(header))

    sorted_keys = sorted(grouped_data.keys())

    for key in sorted_keys:
        scenario, n_workers = key
        metrics = grouped_data[key]
        
        m1_mean, m1_var = calculate_stats(metrics["metric_1"])
        m2_mean, m2_var = calculate_stats(metrics["metric_2"])

        print(f"{scenario:<30} | {n_workers:<4} | {m1_mean:<15.6f} | {m1_var:<12.4e} | {m2_mean:<20.6f} | {m2_var:<12.4e}")

if __name__ == "__main__":
    main()