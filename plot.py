import os
import json
import glob
import argparse
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from typing import List, Optional

def load_experiments(directory: str) -> pd.DataFrame:
    """
    Loads all JSON files from the specified directory and flattens them
    into a Pandas DataFrame.
    """
    data_records = []
    
    # Check if directory exists
    if not os.path.exists(directory):
        print(f"Error: The directory '{directory}' does not exist.")
        return pd.DataFrame()
    
    # Use glob to find all json files
    # Note: We use os.path.join to handle path separators correctly across OS
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
                # These keys match the structure of your JSON file
                record = {
                    "n_workers": content.get("n_workers"),
                    "n_primes": content.get("n_primes"),
                    "n_iterations": content.get("n_iterations"),
                    "scenario": content.get("scenario"),
                }
                
                # Flatten the 'outcome' dictionary into the main record
                outcome = content.get("outcome", {})
                for key, value in outcome.items():
                    record[key] = value
                    
                data_records.append(record)
        except Exception as e:
            print(f"Warning: Error reading file {file_path}: {e}")

    df = pd.DataFrame(data_records)
    
    if not df.empty:
        # Create a unique readable label for the configuration (X-axis)
        # Example: "local | W:4 P:10000 I:100"
        df['configuration_label'] = df.apply(
            lambda row: f"{row['scenario']} | W:{row['n_workers']} P:{row['n_primes']} I:{row['n_iterations']}", 
            axis=1
        )
    
    return df

def generate_plots(df: pd.DataFrame, output_folder: str):
    """
    Generates bar charts for every numeric metric found in the dataframe.
    """
    if df.empty:
        print("DataFrame is empty. Skipping plot generation.")
        return

    # Create output directory if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    print(f"Generating plots in '{output_folder}'...")

    # Define columns that act as identifiers (not metrics)
    config_cols = ['n_workers', 'n_primes', 'n_iterations', 'scenario', 'configuration_label']
    
    # Identify metric columns automatically
    # (Selects all numeric columns that are not in the config list)
    metric_cols = [c for c in df.columns if c not in config_cols and pd.api.types.is_numeric_dtype(df[c])]

    # Set the visual style for the plots
    sns.set_theme(style="whitegrid")

    for metric in metric_cols:
        plt.figure(figsize=(12, 6))
        
        # Sort values to ensure the x-axis is ordered nicely
        plot_data = df.sort_values(by=['scenario', 'n_workers', 'n_primes'])

        # Create the bar plot
        chart = sns.barplot(
            data=plot_data,
            x='configuration_label',
            y=metric,
            hue='scenario', # Color bars based on the scenario
            palette='viridis'
        )

        plt.title(f"Comparison: {metric}", fontsize=16)
        plt.xlabel("Configuration", fontsize=12)
        plt.ylabel(metric, fontsize=12)
        
        # Rotate x-axis labels to prevent overlap
        plt.xticks(rotation=45, ha='right')
        
        # Adjust layout to make room for rotated labels
        plt.tight_layout()
        
        # Save the plot
        filename = f"{metric}.png"
        save_path = os.path.join(output_folder, filename)
        plt.savefig(save_path)
        plt.close() # Close the figure to free memory
        
        print(f" -> Saved: {filename}")

def main():
    # 1. Setup Argument Parser
    parser = argparse.ArgumentParser(
        description="Analyze experiment results and generate metric comparison plots."
    )
    
    # Positional argument for the data directory
    parser.add_argument(
        "--data-dir", 
        type=str, 
        help="Path to the folder containing the experiment JSON files."
    )
    
    # Optional argument for filtering scenarios
    parser.add_argument(
        "--scenarios", 
        nargs="+", 
        type=str, 
        help="List of scenarios to include (e.g., 'local' 'cloud'). If omitted, all scenarios are used."
    )
    
    # Optional argument for output directory
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default="./plots", 
        help="Path where the plots will be saved (default: ./plots)."
    )

    args = parser.parse_args()

    # 2. Load Data
    df_experiments = load_experiments(args.data_dir)
    
    if df_experiments.empty:
        print("No data loaded. Exiting.")
        return

    # 3. Filter by scenario if the argument is provided
    if args.scenarios:
        print(f"Filtering for scenarios: {args.scenarios}")
        # Filter rows where the 'scenario' column matches one of the provided args
        df_experiments = df_experiments[df_experiments['scenario'].isin(args.scenarios)]
        
        if df_experiments.empty:
            print(f"No data found for the requested scenarios: {args.scenarios}")
            return

    # 4. Generate Plots
    generate_plots(df_experiments, args.output_dir)
    print("All operations completed successfully.")

if __name__ == "__main__":
    main()