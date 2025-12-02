import os
import json
import glob
import argparse
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from typing import List, Optional

# --- Global Lookup Dictionaries ---
# Modify these dictionaries to rename metrics (columns) and scenarios (values)
# Keys should match the raw JSON keys/values, Values are the display names.

METRIC_LABELS = {
    # CPU Metrics
    "cpu_time_seconds": "Total CPU Time (s)",
    "cpu_percent_avg": "Avg CPU Load (%)",
    "cpu_percent_max": "Peak CPU Load (%)",
    
    # Memory Metrics
    "memory_usage_max_bytes": "Peak RAM Usage (Bytes)",
    "memory_percent_avg": "Avg RAM Utilization (%)",
    
    # Network Metrics (TX = Sent, RX = Received)
    "network_tx_total_bytes": "Total Data Sent (Bytes)",
    "network_rx_total_bytes": "Total Data Received (Bytes)",
    "network_tx_avg": "Avg Upload Rate (Bytes/iter)",
    "network_rx_avg": "Avg Download Rate (Bytes/iter)",
    "network_tx_max": "Peak Upload Rate (Bytes/iter)",
    "network_rx_max": "Peak Download Rate (Bytes/iter)",
    
    # Time Metrics
    "total_time_in_seconds": "Total Execution Time (s)"
}

SCENARIO_LABELS = {
    "local-async": "Local Async",
    "local-multithread": "Local Multi-threading",
    "mqtt": "MQTT",
    "orbitalis-local": "Orbitalis Local",
    "orbitalis-mqtt": "Orbitalis MQTT",
}

def load_experiments(directory: str) -> pd.DataFrame:
    """
    Loads all JSON files from the specified directory and flattens them
    into a Pandas DataFrame. Applies global renames for scenarios.
    """
    data_records = []
    
    if not os.path.exists(directory):
        print(f"Error: The directory '{directory}' does not exist.")
        return pd.DataFrame()
    
    json_pattern = os.path.join(directory, "*.json")
    json_files = glob.glob(json_pattern)
    
    if not json_files:
        print(f"No JSON files found in {directory}")
        return pd.DataFrame()

    print(f"Found {len(json_files)} experiment files in '{directory}'. Processing...")

    for file_path in json_files:
        try:
            with open(file_path, 'r') as f:
                content = json.load(f)
                
                # Extract configuration parameters
                raw_scenario = content.get("scenario")
                
                # Apply Scenario Rename
                scenario_name = SCENARIO_LABELS.get(raw_scenario, raw_scenario)

                record = {
                    "n_workers": content.get("n_workers"),
                    "n_primes": content.get("n_primes"),
                    "n_iterations": content.get("n_iterations"),
                    "scenario": scenario_name,
                }
                
                # Flatten the 'outcome' dictionary
                outcome = content.get("outcome", {})
                for key, value in outcome.items():
                    record[key] = value
                    
                data_records.append(record)
        except Exception as e:
            print(f"Warning: Error reading file {file_path}: {e}")

    df = pd.DataFrame(data_records)
    
    if not df.empty:
        # Create a unique readable label for the configuration
        df['configuration_label'] = df.apply(
            lambda row: f"{row['scenario']}\nWorker: {row['n_workers']}\nPrimes: {row['n_primes']}\nIterations: {row['n_iterations']}", 
            axis=1
        )
        
        # Apply Metric Rename to columns
        df.rename(columns=METRIC_LABELS, inplace=True)
    
    return df

def generate_plots(df: pd.DataFrame, output_folder: str):
    """
    Generates bar charts for every numeric metric. Each bar is annotated with the percentage difference
    """
    if df.empty:
        print("DataFrame is empty. Skipping plot generation.")
        return

    os.makedirs(output_folder, exist_ok=True)
    print(f"Generating plots in '{output_folder}'...")

    config_cols = ['n_workers', 'n_primes', 'n_iterations', 'scenario', 'configuration_label']
    metric_cols = [c for c in df.columns if c not in config_cols and pd.api.types.is_numeric_dtype(df[c])]

    sns.set_theme(style="whitegrid")

    for metric in metric_cols:
        plt.figure(figsize=(12, 8))
        
        plot_data = df.sort_values(by=['scenario', 'n_workers', 'n_primes'])

        # Create the bar plot (Seaborn calculates the Means here)
        ax = sns.barplot(
            data=plot_data,
            x='configuration_label',
            y=metric,
            hue='scenario',
            palette='viridis'
        )

        # --- STEP 1: Find the Minimum Bar Height (The Baseline Mean) ---
        # We look at the actual plotted bars to find the lowest average.
        valid_heights = [p.get_height() for p in ax.patches if not pd.isna(p.get_height()) and p.get_height() > 0]
        
        if not valid_heights:
            plt.close()
            continue
            
        min_bar_height = min(valid_heights)

        # --- STEP 2: Map Error Bar Heights ---
        # (Same logic as before to avoid text overlap)
        error_bar_tops = {}
        for line in ax.lines:
            x_data = line.get_xdata()
            y_data = line.get_ydata()
            if len(x_data) > 0:
                x_pos = x_data[0]
                y_max = max(y_data)
                error_bar_tops[round(x_pos, 4)] = y_max

        # --- STEP 3: Annotate ---
        max_y_limit = 0 

        for p in ax.patches:
            bar_height = p.get_height()
            
            if pd.isna(bar_height) or bar_height <= 0:
                continue

            bar_x = p.get_x() + p.get_width() / 2.
            
            # Determine vertical anchor (Bar vs Error Line)
            text_y_anchor = bar_height
            if round(bar_x, 4) in error_bar_tops:
                error_top = error_bar_tops[round(bar_x, 4)]
                if error_top > text_y_anchor:
                    text_y_anchor = error_top

            # Calculate Percentage Difference based on MIN_BAR_HEIGHT (Means)
            # Use a small epsilon for float comparison safety
            if abs(bar_height - min_bar_height) < 0.0001:
                # This is the baseline bar
                label_text = "Best" # Or leave empty "" if you prefer no label
                color = "green"
                weight = "bold"
            else:
                pct_diff = ((bar_height - min_bar_height) / min_bar_height) * 100
                label_text = f"+{pct_diff:.1f}%"
                color = "black"
                weight = "normal"

            ax.annotate(
                label_text,
                (bar_x, text_y_anchor),
                ha='center', 
                va='bottom', 
                xytext=(0, 5),
                textcoords='offset points',
                fontsize=10,
                color=color,
                weight=weight
            )
            
            max_y_limit = max(max_y_limit, text_y_anchor)

        plt.title(f"Comparison: {metric}", fontsize=16)
        plt.xlabel("Configuration", fontsize=12)
        plt.ylabel(metric, fontsize=12)
        
        if max_y_limit > 0:
            plt.ylim(top=max_y_limit * 1.15)

        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        safe_filename = "".join([c if c.isalnum() else "_" for c in metric]) + ".png"
        save_path = os.path.join(output_folder, safe_filename)
        plt.savefig(save_path)
        plt.close()
        
        print(f" -> Saved: {safe_filename}")

def generate_overall_variation_plot(df: pd.DataFrame, metrics: List[str], output_folder: str):
    """
    Generates a single plot showing the average percentage variation 
    for the specific list of metrics provided via command line.
    """
    print(f"Generating overall variation plot for: {metrics}...")
    
    variations = []

    # Map input metrics to actual DataFrame columns (handling potential renames)
    # We check if the input matches a key in METRIC_LABELS, if so, use the value (the new col name)
    # Otherwise, assume the user passed the already-renamed name or a raw name that wasn't renamed.
    actual_cols = []
    for m in metrics:
        if m in METRIC_LABELS:
            actual_cols.append(METRIC_LABELS[m])
        elif m in df.columns:
            actual_cols.append(m)
        else:
            print(f"Warning: Metric '{m}' not found in data. Skipping.")

    if not actual_cols:
        print("No valid metrics found for overall plot.")
        return

    for col in actual_cols:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            min_val = df[col].min()
            max_val = df[col].max()
            
            if min_val > 0:
                pct_diff = ((max_val - min_val) / min_val) * 100
                variations.append({"Metric": col, "Variation (%)": pct_diff})
            else:
                variations.append({"Metric": col, "Variation (%)": 0.0})

    if not variations:
        print("Could not calculate variations (possibly non-numeric data).")
        return

    df_var = pd.DataFrame(variations)

    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_var, x="Metric", y="Variation (%)", palette="magma")
    
    plt.title("Overall Percentage Variation (Max vs Min)", fontsize=16)
    plt.ylabel("Variation (%)", fontsize=12)
    plt.xticks(rotation=30)
    
    # Add labels on top of bars
    for index, row in df_var.iterrows():
        plt.text(index, row["Variation (%)"] + 0.5, f'{row["Variation (%)"]:.1f}%', color='black', ha="center")

    plt.tight_layout()
    save_path = os.path.join(output_folder, "overall_variation_summary.png")
    plt.savefig(save_path)
    plt.close()
    print(f" -> Saved: overall_variation_summary.png")

def main():
    parser = argparse.ArgumentParser(
        description="Analyze experiment results and generate metric comparison plots."
    )
    
    parser.add_argument(
        "--data-dir", 
        type=str, 
        required=True, # Made required for safety
        help="Path to the folder containing the experiment JSON files."
    )
    
    parser.add_argument(
        "--scenarios", 
        nargs="+", 
        type=str, 
        help="List of scenarios (raw keys) to include."
    )
    
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default="./plots", 
        help="Path where the plots will be saved."
    )

    parser.add_argument(
        "--overall",
        nargs="+",
        type=str,
        help="List of metric keys (e.g. 'execution_time') to summarize in an overall variation plot."
    )

    args = parser.parse_args()

    # Load Data
    df_experiments = load_experiments(args.data_dir)
    
    if df_experiments.empty:
        print("No data loaded. Exiting.")
        return

    # Filter by scenario 
    if args.scenarios:
        # Note: We must check against mapped names because mapping happens in load_experiments
        mapped_scenarios = [SCENARIO_LABELS.get(s, s) for s in args.scenarios]
        print(f"Filtering for scenarios: {mapped_scenarios}")
        df_experiments = df_experiments[df_experiments['scenario'].isin(mapped_scenarios)]
        
        if df_experiments.empty:
            print("No data found for the requested scenarios.")
            return

    # Generate Standard Plots
    generate_plots(df_experiments, args.output_dir)

    # --- Generate Overall Plot if requested ---
    if args.overall:
        generate_overall_variation_plot(df_experiments, args.overall, args.output_dir)

    print("All operations completed successfully.")

if __name__ == "__main__":
    main()