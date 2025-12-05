import os
import json
import glob
import argparse
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from typing import List, Optional
import matplotlib.patches as mpatches

# --- Global Lookup Dictionaries ---
# Modify these dictionaries to rename metrics (columns) and scenarios (values)
# Keys should match the raw JSON keys/values, Values are the display names.

METRIC_LABELS = {
    # CPU Metrics
    "cpu_time_seconds": "Total CPU Time (s)",
    "cpu_percent_avg": "Avg CPU Load (%)",
    "cpu_percent_max": "Peak CPU Load (%)",
    
    # Memory Metrics
    "memory_usage_avg_bytes": "Avg RAM Usage (Bytes)",
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
    "orbitalis-local-ff": "Orbitalis Local (Fire-and-Forget)",
    "orbitalis-mqtt": "Orbitalis MQTT",
    "orbitalis-mqtt-ff": "Orbitalis MQTT (Fire-and-Forget)",
}

NORMALIZE_TO_ITERATIONS = 1_000_000


def value_modifier(record, key, value):
    # Normalize certain metrics to a per-iteration basis
    if key in ["cpu_time_seconds", "memory_usage_max_bytes", "network_tx_total_bytes", "network_rx_total_bytes", "total_time_in_seconds", "memory_usage_avg_bytes"]:
        n_iterations = record.get("n_iterations", 1)
        value = value / n_iterations * NORMALIZE_TO_ITERATIONS
    
    return value

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
                    record[key] = value_modifier(record, key, value)

                if record["total_time_in_seconds"] < 1:
                    print(f"Warning: Skipping file {file_path} due to unrealistically low total_time_in_seconds.")
                    continue
                    
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

def generate_stacked_metrics_plot(
    df: pd.DataFrame, 
    output_folder: str, 
    output_format: str, 
    metrics_to_stack: list[str],
    y_log: bool = False,
    show_pct_diff: bool = True,
    width: int = 6,
    height: int = 8,
):
    """
    Generates a stacked bar chart by summing the specified list of metrics.
    
    How it works:
    - It creates cumulative sums of the metrics.
    - It plots them in reverse order (Largest Total -> Smallest Component).
    - The result is a stacked bar where the colors represent the 'scenario'
      and the hatch patterns (textures) represent the specific 'metric'.
    
    Args:
        metrics_to_stack: A list of column names (e.g., ['cpu_time', 'wait_time', 'io_time']).
                          The first item in the list will be at the bottom of the stack.
    """
    if df.empty:
        print("DataFrame is empty. Skipping plot generation.")
        return

    # 1. Validation
    missing = [m for m in metrics_to_stack if m not in df.columns]
    if missing:
        print(f"Error: The following columns are missing: {missing}")
        return

    os.makedirs(output_folder, exist_ok=True)
    print(f"Generating stacked plot for {metrics_to_stack} in '{output_folder}'...")

    # 2. Data Preparation: Calculate Cumulative Sums
    # We need to plot the Total (A+B+C) first, then (A+B), then (A) to achieve the stacking effect.
    df_temp = df.copy()
    cumulative_cols = []
    current_sum_col = None

    # We iterate in order (A, B, C). 
    # A will be the bottom. A+B will be middle. A+B+C will be top.
    for i, metric in enumerate(metrics_to_stack):
        new_col_name = f"__cum_{i}_{metric}"
        
        if current_sum_col is None:
            df_temp[new_col_name] = df_temp[metric]
        else:
            df_temp[new_col_name] = df_temp[current_sum_col] + df_temp[metric]
        
        cumulative_cols.append(new_col_name)
        current_sum_col = new_col_name

    # We define a list of hatches (textures) for the layers.
    # Top layer (last metric added) gets the first texture.
    # Supported hatches: /, \, |, -, +, x, o, O, ., *
    # We rotate them so the "Bottom" metric is solid (or distinct).
    available_hatches = ['', '///', '...', 'xxx', '+++', '|||']
    
    # Setup Plot
    unique_workers = sorted(df['n_workers'].unique())
    n_subplots = len(unique_workers)
    sns.set_theme(style="whitegrid")
    
    fig, axes = plt.subplots(nrows=1, ncols=n_subplots, figsize=(width * n_subplots, height), sharey=False, constrained_layout=True)
    if n_subplots == 1: axes = [axes]

    for i, worker_count in enumerate(unique_workers):
        ax = axes[i]
        
        subplot_data = df_temp[df_temp['n_workers'] == worker_count].sort_values(by=['n_primes', 'scenario'])
        if subplot_data.empty: continue

        # 3. Plotting Loop (Reverse Order)
        # We plot the LARGEST cumulative column first (the background/total).
        # We plot the SMALLEST cumulative column last (the foreground/bottom).
        
        # Determine max Y for limits (based on the total sum)
        total_col = cumulative_cols[-1] # The last column is the sum of all
        
        # We iterate backwards through the cumulative columns
        for idx in range(len(cumulative_cols) - 1, -1, -1):
            col_name = cumulative_cols[idx]
            
            # Use specific hatch for this layer
            # We want the 'last' metric in the list (top of stack) to have a specific hatch
            # Logic: idx 0 is Bottom Metric. idx N is Top Total.
            # We assign hatches based on the metric index.
            hatch_pattern = available_hatches[idx % len(available_hatches)]
            
            # Determine alpha: The bottom layer (idx 0) should be solid (1.0).
            # Upper layers are drawn *under* it in this loop? No, we draw Largest First.
            # So Largest (Total) is drawn first. It should be semi-transparent if we want to see grid?
            # Actually, standard stacked logic: Draw Big, then Draw Medium on top.
            
            sns.barplot(
                data=subplot_data,
                x='n_primes',
                y=col_name,
                hue='scenario',
                palette='viridis',
                ax=ax,
                dodge=True,
                hatch=hatch_pattern,
                edgecolor='black', # clear borders
                linewidth=0.5,
                alpha=1.0 # Solid colors, the hatch adds the texture
            )

        # 4. Annotations (Applied ONLY to the Total Height / First Layer plotted)
        # Since we plotted the Total (last col) first, the current patches/lines might be mixed.
        # But we can calculate baselines based on the 'total_col' data logic.
        
        if show_pct_diff:
            max_y_limit = 0
            
            # Calculate Visual Baselines for the Total Height
            # We need to manually group the bars by X coordinate to find the min-height (baseline)
            # strictly for the TOTAL bar (which corresponds to the largest values).
            
            # Helper: extract total heights from dataframe to simplify logic, 
            # because 'ax.patches' now contains multiple layers of bars.
            # It's safer to rely on the Visual Patches of the *first* iteration (The Total),
            # but getting them from the axes is hard because they are mixed.
            
            # Alternative: Re-scan all patches, find the tallest one for each X/Hue group?
            # Simpler: Just scan all patches. The Tallest patch at a specific X/Hue is the Total.
            
            # A. Map (X_coord, Scenario_Index) -> Max Height found
            # This identifies the "Total" height for every bar group.
            bar_tops = {} # Key: (x_coord_int, x_position_float) -> height
            
            for p in ax.patches:
                h = p.get_height()
                if pd.isna(h) or h <= 0: continue
                
                # Center X
                mx = p.get_x() + p.get_width() / 2.
                x_idx = int(round(mx))
                
                key = (x_idx, round(mx, 3))
                
                if key not in bar_tops:
                    bar_tops[key] = h
                else:
                    # We want the MAX height because that represents the Total Stack
                    if h > bar_tops[key]:
                        bar_tops[key] = h

            # B. Find the Baseline (Minimum Total Height) for each X group (Number of Primes)
            group_baselines = {} # x_idx -> min_total_height
            
            for (x_idx, mx), h in bar_tops.items():
                if x_idx not in group_baselines:
                    group_baselines[x_idx] = h
                else:
                    if h < group_baselines[x_idx]:
                        group_baselines[x_idx] = h

            # C. Annotate
            for (x_idx, mx), h in bar_tops.items():
                if x_idx in group_baselines:
                    baseline = group_baselines[x_idx]
                    
                    # Apply Epsilon
                    if h > (baseline + 0.0001):
                        pct_diff = ((h - baseline) / baseline) * 100
                        label_text = f"+{pct_diff:.1f}%"
                        
                        # Find Error bar top for this position to avoid overlap
                        # (Simplified: just put it above the bar)
                        text_y = h
                        
                        max_y_limit = max(max_y_limit, text_y)

                        ax.annotate(
                            label_text,
                            (mx, text_y),
                            ha='center', va='bottom', 
                            xytext=(0, 5), textcoords='offset points',
                            fontsize=9, color="black", weight="bold"
                        )
            
            if max_y_limit > 0:
                 mult = 1.5 if y_log else 1.15
                 ax.set_ylim(top=max_y_limit * mult)

        # 5. Formatting
        if y_log: ax.set_yscale('log')
        
        ax.set_title(f"Workers: {worker_count}", fontsize=14)
        ax.set_xlabel("Number of Primes", fontsize=11)
        if i == 0: ax.set_ylabel("Stacked Metric Sum", fontsize=12)
        else: ax.set_ylabel("")

        # 6. Custom Legend
        if i == n_subplots - 1:
            # Clear auto-generated legend
            if ax.get_legend(): ax.get_legend().remove()
            
            handles, labels = ax.get_legend_handles_labels()
            # Extract just the colors (Scenarios) from the first few handles
            # The number of scenarios = len(df['scenario'].unique())
            n_scenarios = len(subplot_data['scenario'].unique())
            
            scenario_handles = handles[:n_scenarios]
            scenario_labels = labels[:n_scenarios]
            
            # Create Pattern handles for the Metrics
            metric_handles = []
            for m_idx, m_name in enumerate(metrics_to_stack):
                # Corresponding hatch used in loop
                hatch = available_hatches[m_idx % len(available_hatches)]
                # Create a proxy patch (white with black hatch)
                patch = mpatches.Patch(facecolor='white', edgecolor='black', hatch=hatch, label=m_name)
                metric_handles.append(patch)

            # Combine
            final_handles = scenario_handles + [mpatches.Patch(alpha=0)] + metric_handles
            final_labels = scenario_labels + [""] + metrics_to_stack
            
            ax.legend(handles=final_handles, labels=final_labels, 
                      title='Scenario & Components', 
                      bbox_to_anchor=(1.05, 1), loc='upper left')

    safe_name = "stacked_" + "_".join([m[:4] for m in metrics_to_stack]) + f".{output_format}"
    plt.suptitle(f"Stacked Sum: {', '.join(metrics_to_stack)}", fontsize=16, y=1.02)
    plt.tight_layout()
    plt.savefig(os.path.join(output_folder, safe_name), bbox_inches='tight')
    plt.close()
    print(f" -> Saved: {safe_name}")

def generate_plots(df: pd.DataFrame, output_folder: str, output_format: str):
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
        
        safe_filename = "".join([c if c.isalnum() else "_" for c in metric]) + f".{output_format}"
        save_path = os.path.join(output_folder, safe_filename)
        plt.savefig(save_path)
        plt.close()
        
        print(f" -> Saved: {safe_filename}")

def generate_plots_by_worker(df: pd.DataFrame, output_folder: str, output_format: str, y_log: bool = False, show_pct_diff: bool = True, width: int = 6, height: int = 8):
    """
    Generates bar charts for every numeric metric using subplots.
    
    Fix implemented:
    - Calculates the baseline strictly from the PLOTTED bars (visual mean), 
      not the raw dataframe data. This ensures the lowest bar in the chart 
      is always treated as the baseline (0% diff) and is NOT annotated.
    """
    if df.empty:
        print("DataFrame is empty. Skipping plot generation.")
        return

    os.makedirs(output_folder, exist_ok=True)
    print(f"Generating plots in '{output_folder}' (Annotations: {show_pct_diff})...")

    # 1. Setup Columns
    config_cols = ['n_workers', 'n_primes', 'n_iterations', 'scenario', 'configuration_label']
    metric_cols = [c for c in df.columns if c not in config_cols and pd.api.types.is_numeric_dtype(df[c])]

    unique_workers = sorted(df['n_workers'].unique())
    n_subplots = len(unique_workers)
    
    sns.set_theme(style="whitegrid")

    for metric in metric_cols:
        # Dynamic figure size
        fig, axes = plt.subplots(nrows=1, ncols=n_subplots, figsize=(width * n_subplots, height), sharey=False, constrained_layout=True)
        
        if n_subplots == 1:
            axes = [axes]

        for i, worker_count in enumerate(unique_workers):
            ax = axes[i]
            
            # Filter Data
            subplot_data = df[df['n_workers'] == worker_count].sort_values(by=['n_primes', 'scenario'])

            if subplot_data.empty:
                continue

            # Create Bar Plot
            sns.barplot(
                data=subplot_data,
                x='n_primes',
                y=metric,
                hue='scenario',
                palette='viridis',
                ax=ax
            )

            if y_log:
                ax.set_yscale('log')

            ax.set_title(f"Workers: {worker_count}", fontsize=14)
            ax.set_xlabel("Number of Primes", fontsize=11)
            
            if i == 0:
                ax.set_ylabel(metric, fontsize=12)
            else:
                ax.set_ylabel("")

            # =========================================================
            # ANNOTATION LOGIC (Two-Pass Approach)
            # =========================================================
            if show_pct_diff:
                max_y_limit = 0 
                
                # --- PASS 1: Map Error Bars & Find Visual Baselines ---
                # We need to find the minimum height PLOTTED for each X-tick (0, 1, 2...)
                
                error_bar_tops = {} # To avoid text overlap
                group_visual_min = {} # Key: x_coord (int), Value: min_height (float)

                # A. Get Error Bar Tops
                for line in ax.lines:
                    x_data = line.get_xdata()
                    y_data = line.get_ydata()
                    if len(x_data) > 0:
                        x_pos = x_data[0]
                        y_max = max(y_data)
                        error_bar_tops[round(x_pos, 4)] = y_max

                # B. Find the Minimum Bar Height per X-Group strictly from the patches
                for p in ax.patches:
                    h = p.get_height()
                    if pd.isna(h) or h <= 0:
                        continue
                    
                    # Identify the X group (0, 1, 2...)
                    # p.get_x() returns the left edge. We add width/2 to find center, then round to nearest integer.
                    x_idx = int(round(p.get_x() + p.get_width() / 2.))
                    
                    if x_idx not in group_visual_min:
                        group_visual_min[x_idx] = h
                    else:
                        if h < group_visual_min[x_idx]:
                            group_visual_min[x_idx] = h

                # --- PASS 2: Annotate based on Visual Baselines ---
                for p in ax.patches:
                    bar_height = p.get_height()
                    
                    if pd.isna(bar_height) or bar_height <= 0:
                        continue

                    bar_x = p.get_x() + p.get_width() / 2.
                    x_idx = int(round(bar_x))
                    
                    # Calculate Y position for text
                    text_y_anchor = bar_height
                    if round(bar_x, 4) in error_bar_tops:
                        error_top = error_bar_tops[round(bar_x, 4)]
                        if error_top > text_y_anchor:
                            text_y_anchor = error_top
                    
                    max_y_limit = max(max_y_limit, text_y_anchor)

                    # Compare against the VISUAL baseline found in Pass 1
                    if x_idx in group_visual_min:
                        baseline = group_visual_min[x_idx]
                        
                        # Apply Epsilon to handle float precision (e.g. 100.0 vs 100.000001)
                        # We ONLY annotate if the bar is clearly taller than the baseline
                        if bar_height > (baseline + 0.0001):
                            pct_diff = ((bar_height - baseline) / baseline) * 100
                            label_text = f"+{pct_diff:.1f}%"
                            
                            ax.annotate(
                                label_text,
                                (bar_x, text_y_anchor),
                                ha='center', 
                                va='bottom', 
                                xytext=(0, 5),
                                textcoords='offset points',
                                fontsize=9,
                                color="black",
                                weight="normal"
                            )
                        # Else: It is the baseline bar (or equal to it), so NO label.

                if max_y_limit > 0:
                    ax.set_ylim(top=max_y_limit * 1.15)
                
            # Legend management
            if i < n_subplots - 1:
                if ax.get_legend():
                    ax.get_legend().remove()
            else:
                ax.legend(title='Scenario', bbox_to_anchor=(1.05, 1), loc='upper left')

        plt.suptitle(f"Metric Comparison: {metric}", fontsize=16, y=1.02)
        plt.tight_layout()
        
        safe_filename = "".join([c if c.isalnum() else "_" for c in metric]) + f".{output_format}"
        save_path = os.path.join(output_folder, safe_filename)
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        
        print(f" -> Saved: {safe_filename}")

def generate_time_split_plot(
    df: pd.DataFrame, 
    output_folder: str, 
    output_format: str, 
    total_time_col: str,
    cpu_time_col: str,
    y_log: bool = False,       # <--- Added back
    show_pct_diff: bool = True,
    width: int = 6,
    height: int = 8
):
    """
    Generates a single plot file focusing ONLY on the time composition.
    
    Visual Logic:
    - Creates a stacked-like effect by overlaying bars:
      1. 'Total Time' (semi-transparent). Top portion = 'Other/Overhead'.
      2. 'CPU Time' (solid) on top.
    
    Args:
        y_log: If True, sets the Y-axis to logarithmic scale.
    """
    if df.empty:
        print("DataFrame is empty. Skipping plot generation.")
        return

    # Validate columns exist
    if total_time_col not in df.columns or cpu_time_col not in df.columns:
        print(f"Error: Columns '{total_time_col}' or '{cpu_time_col}' not found in DataFrame.")
        return

    os.makedirs(output_folder, exist_ok=True)
    print(f"Generating time split plot in '{output_folder}' (Log Scale: {y_log})...")

    # Setup
    unique_workers = sorted(df['n_workers'].unique())
    n_subplots = len(unique_workers)
    
    sns.set_theme(style="whitegrid")

    # Dynamic figure size
    fig, axes = plt.subplots(nrows=1, ncols=n_subplots, figsize=(width * n_subplots, height), sharey=False, constrained_layout=True)
    
    if n_subplots == 1:
        axes = [axes]

    for i, worker_count in enumerate(unique_workers):
        ax = axes[i]
        
        # Filter Data
        subplot_data = df[df['n_workers'] == worker_count].sort_values(by=['n_primes', 'scenario'])

        if subplot_data.empty:
            continue

        # =========================================================
        # PLOT LAYER 1: TOTAL TIME (The container)
        # =========================================================
        sns.barplot(
            data=subplot_data,
            x='n_primes',
            y=total_time_col,
            hue='scenario',
            palette='viridis',
            alpha=0.4,          # Semi-transparent
            ax=ax,
            dodge=True,
            edgecolor=None
        )

        # =========================================================
        # ANNOTATION LOGIC (Calculated on Total Time)
        # =========================================================
        max_y_limit = 0 
        
        if show_pct_diff:
            # --- PASS 1: Find Visual Baselines ---
            error_bar_tops = {} 
            group_visual_min = {} 

            # Map Error Bars
            for line in ax.lines:
                x_data = line.get_xdata()
                y_data = line.get_ydata()
                if len(x_data) > 0:
                    x_pos = x_data[0]
                    y_max = max(y_data)
                    error_bar_tops[round(x_pos, 4)] = y_max

            # Find Min Height (Total Time Baseline)
            for p in ax.patches:
                h = p.get_height()
                if pd.isna(h) or h <= 0: continue
                x_idx = int(round(p.get_x() + p.get_width() / 2.))
                
                if x_idx not in group_visual_min:
                    group_visual_min[x_idx] = h
                else:
                    if h < group_visual_min[x_idx]:
                        group_visual_min[x_idx] = h

            # --- PASS 2: Annotate ---
            for p in ax.patches:
                bar_height = p.get_height()
                if pd.isna(bar_height) or bar_height <= 0: continue

                bar_x = p.get_x() + p.get_width() / 2.
                x_idx = int(round(bar_x))
                
                # Determine Y anchor for text
                text_y_anchor = bar_height
                if round(bar_x, 4) in error_bar_tops:
                    error_top = error_bar_tops[round(bar_x, 4)]
                    if error_top > text_y_anchor:
                        text_y_anchor = error_top
                
                max_y_limit = max(max_y_limit, text_y_anchor)

                # Compare
                if x_idx in group_visual_min:
                    baseline = group_visual_min[x_idx]
                    if bar_height > (baseline + 0.0001):
                        pct_diff = ((bar_height - baseline) / baseline) * 100
                        label_text = f"+{pct_diff:.1f}%"
                        
                        ax.annotate(
                            label_text,
                            (bar_x, text_y_anchor),
                            ha='center', va='bottom', 
                            xytext=(0, 5), textcoords='offset points',
                            fontsize=9, color="black", weight="bold"
                        )

        # =========================================================
        # PLOT LAYER 2: CPU TIME (The core component)
        # =========================================================
        sns.barplot(
            data=subplot_data,
            x='n_primes',
            y=cpu_time_col,
            hue='scenario',
            palette='viridis',
            alpha=1.0,          # Solid color
            ax=ax,
            dodge=True,
            legend=False        # No duplicate legend
        )
        
        # Add a black border to the CPU bars
        n_bars = len(subplot_data)
        for patch in ax.patches[-n_bars:]:
            patch.set_edgecolor('black')
            patch.set_linewidth(1.0)

        # --- Formatting ---
        if y_log:
            ax.set_yscale('log')

        ax.set_title(f"Workers: {worker_count}", fontsize=14)
        ax.set_xlabel("Number of Primes", fontsize=11)
        
        if i == 0:
            ax.set_ylabel("Time (seconds)", fontsize=12)
        else:
            ax.set_ylabel("")
            
        if max_y_limit > 0 and show_pct_diff:
            # Adjust upper limit slightly more for log scale to avoid cutting off text
            mult = 1.5 if y_log else 1.15
            ax.set_ylim(top=max_y_limit * mult)
            
        # Legend management
        if i < n_subplots - 1:
            if ax.get_legend():
                ax.get_legend().remove()
        else:
            handles, labels = ax.get_legend_handles_labels()
            
            # Create explanatory proxy artists
            solid_patch = mpatches.Patch(facecolor='gray', edgecolor='black', label='CPU Time')
            faded_patch = mpatches.Patch(facecolor='gray', alpha=0.4, label='Other/Wait Time')
            
            unique_labels = dict(zip(labels, handles))
            final_handles = list(unique_labels.values()) + [mpatches.Patch(alpha=0)] + [solid_patch, faded_patch] 
            final_labels = list(unique_labels.keys()) + [""] + ["CPU Time (Solid)", "Other Time (Faded)"]
            
            ax.legend(handles=final_handles, labels=final_labels, 
                      title='Scenario & Component', bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.suptitle(f"Time Composition: CPU vs Other ({total_time_col})", fontsize=16, y=1.02)
    plt.tight_layout()
    
    safe_filename = "time_composition_split." + output_format
    save_path = os.path.join(output_folder, safe_filename)
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()
    
    print(f" -> Saved: {safe_filename}")

def generate_pct_diff_boxplots_no_baseline(df: pd.DataFrame, output_folder: str, output_format: str):
    """
    Generates boxplots showing percentage increments relative to the best performing 
    scenario (baseline) for each (Worker + Prime) combination.
    
    CRITICAL CHANGE:
    - The baseline scenario itself (0% diff) is EXCLUDED from the visualization.
    - Only scenarios that have an increment > 0 (or < 0 if strictly faster, though unlikely for baseline) are shown.
    """
    if df.empty:
        print("DataFrame is empty. Skipping plot generation.")
        return

    os.makedirs(output_folder, exist_ok=True)
    print(f"Generating % diff boxplots (hiding baseline) in '{output_folder}'...")

    unique_workers = sorted(df['n_workers'].unique())
    n_subplots = len(unique_workers)
    
    # Identify metric columns
    config_cols = ['n_workers', 'n_primes', 'n_iterations', 'scenario', 'configuration_label']
    metric_cols = [c for c in df.columns if c not in config_cols and pd.api.types.is_numeric_dtype(df[c])]

    sns.set_theme(style="whitegrid")

    for metric in metric_cols:
        # --- 1. DATA PRE-PROCESSING ---
        plot_df = df.copy()
        plot_df['pct_diff'] = 0.0
        plot_df['is_baseline'] = False # Flag to identify and hide the baseline later
        
        # Group by the specific combination of Worker + Prime to find the local baseline
        groups = plot_df.groupby(['n_workers', 'n_primes'])
        
        for (w, p), group_data in groups:
            # Calculate mean per scenario to find the "winner"
            means_by_scenario = group_data.groupby('scenario')[metric].mean()
            
            if means_by_scenario.empty:
                continue
                
            # Identify the baseline scenario (lowest mean) and its value
            baseline_scenario = means_by_scenario.idxmin()
            baseline_val = means_by_scenario.min()
            
            if baseline_val == 0:
                continue

            # Identify rows belonging to this group
            mask = (plot_df['n_workers'] == w) & (plot_df['n_primes'] == p)
            
            # Calculate % diff
            plot_df.loc[mask, 'pct_diff'] = ((plot_df.loc[mask, metric] - baseline_val) / baseline_val) * 100
            
            # Mark the baseline rows for removal
            # We use the scenario name to be precise, ensuring we hide the specific scenario acting as baseline
            baseline_mask = mask & (plot_df['scenario'] == baseline_scenario)
            plot_df.loc[baseline_mask, 'is_baseline'] = True

        # --- 2. FILTERING ---
        # We remove the baseline rows so no box is drawn at 0
        final_plot_df = plot_df[plot_df['is_baseline'] == False].copy()

        # --- 3. PLOTTING ---
        fig, axes = plt.subplots(nrows=1, ncols=n_subplots, figsize=(6 * n_subplots, 8), sharey=False)
        
        if n_subplots == 1:
            axes = [axes]

        for i, worker_count in enumerate(unique_workers):
            ax = axes[i]
            
            # Filter Data for this subplot (Worker) and sort
            subplot_data = final_plot_df[final_plot_df['n_workers'] == worker_count].sort_values(by=['n_primes', 'scenario'])

            if subplot_data.empty:
                # Handle case where perhaps only 1 scenario existed (so it was baseline and removed)
                ax.set_title(f"Workers: {worker_count} (No increments)", fontsize=14)
                continue

            sns.boxplot(
                data=subplot_data,
                x='n_primes',
                y='pct_diff',
                hue='scenario',
                palette='viridis',
                ax=ax,
                showfliers=False
            )

            # Reference line at 0 (represents the hidden baseline)
            ax.axhline(0, color='red', linestyle='--', linewidth=1, alpha=0.5, label='Baseline (0%)')

            ax.set_title(f"Workers: {worker_count}", fontsize=14)
            ax.set_xlabel("Number of Primes", fontsize=11)
            
            if i == 0:
                ax.set_ylabel(f"% Increment vs Group Baseline ({metric})", fontsize=12)
            else:
                ax.set_ylabel("")

            # Fix Legend: Remove duplicates if any
            if i < n_subplots - 1:
                if ax.get_legend():
                    ax.get_legend().remove()
            else:
                ax.legend(title='Scenario', bbox_to_anchor=(1.05, 1), loc='upper left')

        plt.suptitle(f"Relative Performance Cost: {metric}", fontsize=16, y=1.02)
        plt.tight_layout()
        
        safe_filename = "boxplot_diff_" + "".join([c if c.isalnum() else "_" for c in metric]) + f".{output_format}"
        save_path = os.path.join(output_folder, safe_filename)
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        
        print(f" -> Saved: {safe_filename}")

def generate_plots_by_primes(df: pd.DataFrame, output_folder: str, output_format: str, y_log: bool = False, show_pct_diff: bool = True):
    """
    Generates bar charts for every numeric metric using subplots.
    
    INVERTED LOGIC:
    - Subplots are created based on 'n_primes' (Workload size).
    - X-Axis represents 'n_workers' (Parallelism).
    - Baseline calculation remains strictly visual based on the lowest bar per group.
    """
    if df.empty:
        print("DataFrame is empty. Skipping plot generation.")
        return

    os.makedirs(output_folder, exist_ok=True)
    print(f"Generating plots by Primes in '{output_folder}' (Annotations: {show_pct_diff})...")

    # 1. Setup Columns
    config_cols = ['n_workers', 'n_primes', 'n_iterations', 'scenario', 'configuration_label']
    metric_cols = [c for c in df.columns if c not in config_cols and pd.api.types.is_numeric_dtype(df[c])]

    # SWAP: We now find unique Primes for the subplots
    unique_primes = sorted(df['n_primes'].unique())
    n_subplots = len(unique_primes)
    
    sns.set_theme(style="whitegrid")

    for metric in metric_cols:
        # Dynamic figure size
        fig, axes = plt.subplots(nrows=1, ncols=n_subplots, figsize=(6 * n_subplots, 8), sharey=False)
        
        if n_subplots == 1:
            axes = [axes]

        for i, prime_count in enumerate(unique_primes):
            ax = axes[i]
            
            # SWAP: Filter by Prime count, Sort by Workers
            subplot_data = df[df['n_primes'] == prime_count].sort_values(by=['n_workers', 'scenario'])

            if subplot_data.empty:
                continue

            # SWAP: X-axis is now Workers
            sns.barplot(
                data=subplot_data,
                x='n_workers', 
                y=metric,
                hue='scenario',
                palette='viridis',
                ax=ax
            )

            if y_log:
                ax.set_yscale('log')

            ax.set_title(f"Primes (Workload): {prime_count}", fontsize=14)
            ax.set_xlabel("Number of Workers", fontsize=11)
            
            if i == 0:
                ax.set_ylabel(metric, fontsize=12)
            else:
                ax.set_ylabel("")

            # =========================================================
            # ANNOTATION LOGIC (Preserved but acts on new X-axis)
            # =========================================================
            if show_pct_diff:
                max_y_limit = 0 
                
                # --- PASS 1: Map Error Bars & Find Visual Baselines ---
                error_bar_tops = {} 
                group_visual_min = {} # Key now corresponds to x-index of Workers

                # A. Get Error Bar Tops
                for line in ax.lines:
                    x_data = line.get_xdata()
                    y_data = line.get_ydata()
                    if len(x_data) > 0:
                        x_pos = x_data[0]
                        y_max = max(y_data)
                        error_bar_tops[round(x_pos, 4)] = y_max

                # B. Find the Minimum Bar Height per X-Group (Workers)
                for p in ax.patches:
                    h = p.get_height()
                    if pd.isna(h) or h <= 0:
                        continue
                    
                    x_idx = int(round(p.get_x() + p.get_width() / 2.))
                    
                    if x_idx not in group_visual_min:
                        group_visual_min[x_idx] = h
                    else:
                        if h < group_visual_min[x_idx]:
                            group_visual_min[x_idx] = h

                # --- PASS 2: Annotate based on Visual Baselines ---
                for p in ax.patches:
                    bar_height = p.get_height()
                    
                    if pd.isna(bar_height) or bar_height <= 0:
                        continue

                    bar_x = p.get_x() + p.get_width() / 2.
                    x_idx = int(round(bar_x))
                    
                    # Calculate Y position for text
                    text_y_anchor = bar_height
                    if round(bar_x, 4) in error_bar_tops:
                        error_top = error_bar_tops[round(bar_x, 4)]
                        if error_top > text_y_anchor:
                            text_y_anchor = error_top
                    
                    max_y_limit = max(max_y_limit, text_y_anchor)

                    # Compare against the VISUAL baseline found in Pass 1
                    if x_idx in group_visual_min:
                        baseline = group_visual_min[x_idx]
                        
                        # Apply Epsilon
                        if bar_height > (baseline + 0.0001):
                            pct_diff = ((bar_height - baseline) / baseline) * 100
                            label_text = f"+{pct_diff:.1f}%"
                            
                            ax.annotate(
                                label_text,
                                (bar_x, text_y_anchor),
                                ha='center', 
                                va='bottom', 
                                xytext=(0, 5),
                                textcoords='offset points',
                                fontsize=9,
                                color="black",
                                weight="normal"
                            )

                if max_y_limit > 0:
                    ax.set_ylim(top=max_y_limit * 1.15)
                
            # Legend management
            if i < n_subplots - 1:
                if ax.get_legend():
                    ax.get_legend().remove()
            else:
                ax.legend(title='Scenario', bbox_to_anchor=(1.05, 1), loc='upper left')

        plt.suptitle(f"Metric Comparison by Workload: {metric}", fontsize=16, y=1.02)
        plt.tight_layout()
        
        # Modified filename to distinguish from the worker-based plots
        safe_filename = "by_prime_" + "".join([c if c.isalnum() else "_" for c in metric]) + f".{output_format}"
        save_path = os.path.join(output_folder, safe_filename)
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()
        
        print(f" -> Saved: {safe_filename}")

def generate_overall_variation_plot(df: pd.DataFrame, metrics: List[str], output_folder: str, output_format: str):
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
    save_path = os.path.join(output_folder, f"overall_variation_summary.{output_format}")
    plt.savefig(save_path)
    plt.close()
    print(f" -> Saved: {save_path}")

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

    parser.add_argument(
        "--output-format",
        type=str,
        default="png",
        choices=["png", "pdf", "svg"],
        help="Output format for the plots."
    )

    parser.add_argument(
        "--show-pct-diff",
        action="store_true",
        help="If set, percentage difference annotations will be shown."
    )

    parser.add_argument(
        "--width",
        type=int,
        default=6,
        help="Width of individual subplots."
    )

    parser.add_argument(
        "--height",
        type=int,
        default=8,
        help="Height of individual subplots."
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
    # generate_plots(df_experiments, args.output_dir, args.output_format)


    print(df_experiments.columns)

    generate_time_split_plot(df_experiments, os.path.join(args.output_dir, "by_worker_total_cpu_time"), args.output_format, 
                             y_log=True, show_pct_diff=args.show_pct_diff, total_time_col="Total Execution Time (s)", cpu_time_col="Total CPU Time (s)",
                             width=args.width, height=args.height)
    
    generate_stacked_metrics_plot(df_experiments, os.path.join(args.output_dir, "networking"), args.output_format, 
                             y_log=True, show_pct_diff=args.show_pct_diff, metrics_to_stack=["Total Data Sent (Bytes)", "Total Data Received (Bytes)"],
                             width=args.width, height=args.height)
    
    generate_plots_by_worker(df_experiments, os.path.join(args.output_dir, "by_worker"), args.output_format, y_log=False, show_pct_diff=args.show_pct_diff, width=args.width, height=args.height)

    generate_plots_by_worker(df_experiments, os.path.join(args.output_dir, "by_worker_log"), args.output_format, y_log=True, show_pct_diff=args.show_pct_diff, width=args.width, height=args.height)

    # generate_plots_by_primes(df_experiments, os.path.join(args.output_dir, "by_primes"), args.output_format, y_log=True, show_pct_diff=False)

    # generate_pct_diff_boxplots_no_baseline(df_experiments, os.path.join(args.output_dir, "pct_diff_boxplots"), args.output_format)

    # --- Generate Overall Plot if requested ---
    if args.overall:
        generate_overall_variation_plot(df_experiments, args.overall, args.output_dir, args.output_format)
    print("All operations completed successfully.")

if __name__ == "__main__":
    main()