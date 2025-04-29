#!/usr/bin/env python3
"""
Analyze block timestamp data from the block-timestamp-logger
"""
import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime

def load_data(logs_dir, chains=None):
    """Load timestamp data for specified chains"""
    if chains is None:
        # Auto-detect chains from available files
        chains = []
        for file in os.listdir(logs_dir):
            if file.endswith("_deltas.csv"):
                chains.append(file.split("_deltas.csv")[0])
    
    data = {}
    stats = {}
    
    for chain in chains:
        deltas_file = os.path.join(logs_dir, f"{chain}_deltas.csv")
        stats_file = os.path.join(logs_dir, f"{chain}_stats.csv")
        
        if os.path.exists(deltas_file):
            data[chain] = pd.read_csv(deltas_file)
            print(f"Loaded {len(data[chain])} blocks for {chain}")
        else:
            print(f"Warning: No data file found for {chain}")
        
        if os.path.exists(stats_file):
            stats[chain] = pd.read_csv(stats_file)
            print(f"Loaded summary stats for {chain}")
    
    return data, stats

def print_summary(stats):
    """Print a readable summary of timestamp statistics"""
    print("\n===== Timestamp Statistics Summary =====")
    
    for chain, df in stats.items():
        print(f"\n{chain}:")
        print(f"  Total blocks analyzed: {df['Total Blocks'].values[0]}")
        print(f"  Past timestamps: {df['Past Timestamp Blocks'].values[0]} blocks ({df['Past Timestamp Blocks'].values[0]/df['Total Blocks'].values[0]*100:.1f}%)")
        print(f"  Future timestamps: {df['Future Timestamp Blocks'].values[0]} blocks ({df['Future Timestamp Blocks'].values[0]/df['Total Blocks'].values[0]*100:.1f}%)")
        print(f"  Average time delta: {df['Avg Delta (ms)'].values[0]:.1f} ms")
        print(f"  Max past delta: {df['Max Past Delta (ms)'].values[0]:.1f} ms")
        print(f"  Max future delta: {df['Max Future Delta (ms)'].values[0]:.1f} ms")

def plot_distributions(data, output_dir=None):
    """Plot timestamp delta distributions"""
    # Create figure
    plt.figure(figsize=(12, 8))
    
    # Create a subplot for each chain
    colors = ['blue', 'green', 'red', 'orange', 'purple']
    all_chains = list(data.keys())
    
    for i, chain in enumerate(all_chains):
        deltas = data[chain]['Delta (ms)']
        
        # Create histogram
        plt.hist(deltas, bins=50, alpha=0.6, color=colors[i % len(colors)], 
                 label=f"{chain} (avg: {deltas.mean():.1f}ms)")
        
        # Add vertical line at mean
        plt.axvline(deltas.mean(), color=colors[i % len(colors)], linestyle='dashed', linewidth=2)
    
    # Add zero line
    plt.axvline(0, color='red', linestyle='--', alpha=0.5, label='Zero (exact timestamp)')
    
    plt.title('Block Timestamp Delta Distributions', fontsize=16)
    plt.xlabel('Time Delta (ms) - Positive means block timestamp is in the past', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(os.path.join(output_dir, f"timestamp_distribution_{timestamp}.png"), dpi=300)
    
    plt.tight_layout()
    plt.show()

def plot_percentiles(data, output_dir=None):
    """Plot percentile analysis of deltas"""
    plt.figure(figsize=(14, 8))
    
    # Calculate percentiles
    percentiles = list(range(1, 100))
    
    for chain, df in data.items():
        delta_percentiles = [np.percentile(df['Delta (ms)'], p) for p in percentiles]
        plt.plot(percentiles, delta_percentiles, label=chain, linewidth=2, marker='', alpha=0.7)
    
    plt.axhline(0, color='red', linestyle='--', alpha=0.5, label='Zero (exact timestamp)')
    
    plt.title('Timestamp Delta Percentiles', fontsize=16)
    plt.xlabel('Percentile', fontsize=12)
    plt.ylabel('Time Delta (ms)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(os.path.join(output_dir, f"timestamp_percentiles_{timestamp}.png"), dpi=300)
    
    plt.tight_layout()
    plt.show()

def batch_simulation(data, batch_window_ms=15000):
    """
    Simulate how blocks would be assigned to time-based batches
    and analyze potential issues
    """
    print(f"\n===== Batch Simulation (Window: {batch_window_ms}ms) =====")
    
    for chain, df in data.items():
        # Calculate how often blocks would be assigned to the wrong batch
        deltas = df['Delta (ms)']
        
        # A block would be assigned to the wrong batch if abs(delta) > batch_window_ms
        wrong_batch_count = (abs(deltas) > batch_window_ms).sum()
        wrong_batch_pct = wrong_batch_count / len(deltas) * 100
        
        # Future blocks that would be assigned too early
        future_wrong = ((deltas < 0) & (abs(deltas) > batch_window_ms)).sum()
        future_wrong_pct = future_wrong / len(deltas) * 100
        
        # Past blocks that would be assigned too late
        past_wrong = ((deltas > 0) & (abs(deltas) > batch_window_ms)).sum()
        past_wrong_pct = past_wrong / len(deltas) * 100
        
        print(f"\n{chain}:")
        print(f"  Total blocks that would be assigned to the wrong batch: {wrong_batch_count} ({wrong_batch_pct:.2f}%)")
        print(f"  Future blocks assigned too early: {future_wrong} ({future_wrong_pct:.2f}%)")
        print(f"  Past blocks assigned too late: {past_wrong} ({past_wrong_pct:.2f}%)")
        
        # Calculate the 99th percentile of absolute deltas
        percentile_99 = np.percentile(abs(deltas), 99)
        print(f"  99th percentile of absolute delta: {percentile_99:.2f}ms")
        print(f"  Recommended minimum batch window: {percentile_99 * 2:.2f}ms")

def main():
    parser = argparse.ArgumentParser(description='Analyze block timestamp data')
    parser.add_argument('--logs-dir', default='./logs', help='Directory containing timestamp CSV files')
    parser.add_argument('--output-dir', default='./analysis', help='Directory to save plots')
    parser.add_argument('--chains', nargs='+', help='Chain names to analyze (defaults to all)')
    parser.add_argument('--batch-window', type=int, default=15000, help='Batch window in milliseconds for simulation')
    
    args = parser.parse_args()
    
    # Load the data
    data, stats = load_data(args.logs_dir, args.chains)
    
    if not data:
        print("No data found. Make sure the log files exist in the specified directory.")
        return
    
    # Print summary statistics
    if stats:
        print_summary(stats)
    
    # Plot the distributions
    plot_distributions(data, args.output_dir)
    
    # Plot percentiles
    plot_percentiles(data, args.output_dir)
    
    # Run batch simulation
    batch_simulation(data, args.batch_window)

if __name__ == "__main__":
    main()
