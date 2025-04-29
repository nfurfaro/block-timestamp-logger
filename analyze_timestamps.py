#!/usr/bin/env python3
"""
Analyze block timestamp data from the block-timestamp-logger

Usage:
    python analyze_timestamps.py [--chains CHAIN1 CHAIN2 ...]

The script uses hardcoded paths:
    - Logs directory: ./logs
    - Output directory: ./analysis
    - Batch window: 15000ms (15 seconds)
    - Bin width: 100ms

Optional arguments:
    --chains: Specific chains to analyze (e.g., "Optimism" "Base")
              If not specified, all available chains will be analyzed
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
        
        past_blocks = df['Past Timestamp Blocks'].values[0]
        total_blocks = df['Total Blocks'].values[0]
        past_percent = past_blocks/total_blocks*100
        
        future_blocks = df['Future Timestamp Blocks'].values[0]
        future_percent = future_blocks/total_blocks*100
        
        print(f"  Block timestamp vs. receipt time:")
        print(f"  ✓ Honest timestamps (in the past): {past_blocks} blocks ({past_percent:.1f}%)")
        print(f"  ⚠ Potentially dishonest timestamps (in the future): {future_blocks} blocks ({future_percent:.1f}%)")
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
        
        # Split data into past and future timestamps
        past_deltas = deltas[deltas > 0]
        future_deltas = deltas[deltas <= 0]
        
        # Create histogram with color-coded regions
        if len(past_deltas) > 0:
            plt.hist(past_deltas, bins=40, alpha=0.6, color=colors[i % len(colors)], 
                     label=f"{chain} - Honest (Past, {len(past_deltas)/len(deltas)*100:.1f}%)")
        
        if len(future_deltas) > 0:
            plt.hist(future_deltas, bins=20, alpha=0.6, color='red', 
                     label=f"{chain} - Future ({len(future_deltas)/len(deltas)*100:.1f}%)")
        
        # Add vertical line at mean
        plt.axvline(deltas.mean(), color=colors[i % len(colors)], linestyle='dashed', linewidth=2)
    
    # Add zero line
    plt.axvline(0, color='black', linestyle='--', alpha=0.7, linewidth=2, 
                label='Zero (exact timestamp)')
    
    plt.title('Block Receipt Time vs. Block Timestamp', fontsize=16)
    plt.xlabel('Time Delta (ms) - Positive means honest timestamps (block.timestamp < receipt time)', fontsize=12)
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
    
    plt.axhline(0, color='black', linestyle='--', alpha=0.7, linewidth=2, 
                label='Zero (honest/dishonest boundary)')
    
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

def frequency_distribution(data, bin_width=100):
    """Display a simple frequency distribution as text"""
    print("\n===== Timestamp Delta Distribution =====")
    
    for chain, df in data.items():
        deltas = df['Delta (ms)']
        
        # Determine range of bins
        min_val = int(deltas.min() - (deltas.min() % bin_width))
        max_val = int(deltas.max() + bin_width - (deltas.max() % bin_width))
        
        # Create bins
        bins = list(range(min_val, max_val + bin_width, bin_width))
        
        # Count values in each bin
        hist = pd.cut(deltas, bins).value_counts().sort_index()
        
        # Display as text
        print(f"\n{chain} (bin width: {bin_width}ms):")
        print("  Range (ms)      | Count | Distribution")
        print("  ----------------|-------|------------")
        
        max_count = hist.max()
        bar_length = 40  # Max length of the bar
        
        for bin_range, count in hist.items():
            # Format bin range 
            range_str = f"  {bin_range.left:7.0f} to {bin_range.right:7.0f}"
            # Create a bar
            bar = "#" * int(count / max_count * bar_length)
            print(f"{range_str} | {count:5d} | {bar}")

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
        
        # Future blocks that would be assigned too early (dishonest timestamps)
        future_wrong = ((deltas < 0) & (abs(deltas) > batch_window_ms)).sum()
        future_wrong_pct = future_wrong / len(deltas) * 100
        
        # Past blocks that would be assigned too late
        past_wrong = ((deltas > 0) & (abs(deltas) > batch_window_ms)).sum()
        past_wrong_pct = past_wrong / len(deltas) * 100
        
        print(f"\n{chain}:")
        print(f"  Total blocks that would be assigned to the wrong batch: {wrong_batch_count} ({wrong_batch_pct:.2f}%)")
        print(f"  ⚠ Future timestamps causing early assignment: {future_wrong} ({future_wrong_pct:.2f}%)")
        print(f"  Past timestamps causing late assignment: {past_wrong} ({past_wrong_pct:.2f}%)")
        
        # Calculate the 99th percentile of absolute deltas
        percentile_99 = np.percentile(abs(deltas), 99)
        print(f"  99th percentile of absolute delta: {percentile_99:.2f}ms")
        print(f"  Recommended minimum batch window: {percentile_99 * 2:.2f}ms")

def main():
    # Hardcoded paths
    logs_dir = "./logs"
    output_dir = "./analysis"
    batch_window = 15000  # 15 seconds in milliseconds
    bin_width = 100  # 100ms bins for distribution
    
    # Parse any remaining arguments
    parser = argparse.ArgumentParser(description='Analyze block timestamp data')
    parser.add_argument('--chains', nargs='+', help='Chain names to analyze (defaults to all)')
    args = parser.parse_args()
    
    # Load the data
    data, stats = load_data(logs_dir, args.chains)
    
    if not data:
        print(f"No data found. Make sure the log files exist in '{logs_dir}'.")
        return
    
    # Print summary statistics
    if stats:
        print_summary(stats)
    
    # Plot the distributions
    plot_distributions(data, output_dir)
    
    # Plot percentiles
    plot_percentiles(data, output_dir)
    
    # Show basic frequency distribution
    frequency_distribution(data, bin_width)
    
    # Run batch simulation
    batch_simulation(data, batch_window)
    
    # Output recommendations
    print("\n===== Recommendations for Sigma-Batch =====")
    
    for chain, df in data.items():
        deltas = df['Delta (ms)']
        percentile_99 = np.percentile(abs(deltas), 99)
        
        # Calculate timestamp honesty rate
        future_pct = ((deltas < 0).sum() / len(deltas)) * 100
        honest_pct = 100 - future_pct
        
        print(f"\n{chain}:")
        print(f"  Timestamp Honesty Analysis for {chain}:")
        print(f"  → {honest_pct:.1f}% of timestamps are honest (in the past)")
        print(f"  → {future_pct:.1f}% of timestamps are potentially dishonest (in the future)")
        
        # Suggest batch window
        suggested_window = max(percentile_99 * 2, 5000)  # At least 5 seconds
        print(f"  Recommended batch window: at least {suggested_window:.0f}ms ({suggested_window/1000:.1f}s)")
        
        # Honest timestamps assessment
        if honest_pct >= 95:
            print(f"  ✅ EXCELLENT: {chain} has very honest timestamps ({honest_pct:.1f}%)")
            print(f"    Highly reliable for time-based batching")
        elif honest_pct >= 90:
            print(f"  ✓ GOOD: {chain} generally has honest timestamps ({honest_pct:.1f}%)")
            print(f"    Reliable for time-based batching with appropriate buffers")
        elif honest_pct >= 80:
            print(f"  ⚠ MODERATE: {chain} has a noticeable rate of future timestamps ({future_pct:.1f}%)")
            print(f"    Use conservative batch windows and consider additional verification")
        else:
            print(f"  ❌ POOR: {chain} has a high rate of future timestamps ({future_pct:.1f}%)")
            print(f"    Not recommended for time-critical batching without additional measures")
        
        # Suggest based on variability
        std_dev = deltas.std()
        if std_dev > 1000:
            print(f"  Timestamp variability: High (stddev: {std_dev:.1f}ms)")
        elif std_dev > 500:
            print(f"  Timestamp variability: Moderate (stddev: {std_dev:.1f}ms)")
        else:
            print(f"  Timestamp variability: Low (stddev: {std_dev:.1f}ms)")

if __name__ == "__main__":
    main()
