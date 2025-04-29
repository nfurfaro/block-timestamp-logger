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
            if file.endswith("_detailed.csv") or file.endswith("_deltas.csv"):
                chain_name = file.split("_")[0]
                if chain_name not in chains:
                    chains.append(chain_name)
    
    data = {}
    stats = {}
    detailed_data = {}
    
    for chain in chains:
        # Try to load detailed data first
        detailed_file = os.path.join(logs_dir, f"{chain}_detailed.csv")
        deltas_file = os.path.join(logs_dir, f"{chain}_deltas.csv")
        stats_file = os.path.join(logs_dir, f"{chain}_stats.csv")
        
        # First priority: Check for detailed data with raw timestamps
        if os.path.exists(detailed_file):
            detailed_data[chain] = pd.read_csv(detailed_file)
            # Create delta data from detailed data for backward compatibility
            data[chain] = pd.DataFrame({'Delta (ms)': detailed_data[chain]['Delta (ms)']})
            print(f"Loaded {len(detailed_data[chain])} blocks with detailed timestamps for {chain}")
        # Second priority: Fall back to deltas-only data
        elif os.path.exists(deltas_file):
            data[chain] = pd.read_csv(deltas_file)
            print(f"Loaded {len(data[chain])} blocks (deltas only) for {chain}")
            print(f"Note: No raw timestamps available for {chain}")
        else:
            print(f"Warning: No data file found for {chain}")
            continue
        
        # Load summary stats
        if os.path.exists(stats_file):
            stats[chain] = pd.read_csv(stats_file)
            print(f"Loaded summary stats for {chain}")
    
    return data, stats, detailed_data

def print_summary(stats):
    """Print a readable summary of timestamp statistics with focus on accuracy"""
    print("\n===== Timestamp Accuracy Summary =====")
    
    for chain, df in stats.items():
        print(f"\n{chain}:")
        print(f"  Total blocks analyzed: {df['Total Blocks'].values[0]}")
        
        past_blocks = df['Past Timestamp Blocks'].values[0]
        total_blocks = df['Total Blocks'].values[0]
        past_percent = past_blocks/total_blocks*100
        
        future_blocks = df['Future Timestamp Blocks'].values[0]
        future_percent = future_blocks/total_blocks*100
        
        avg_delta = df['Avg Delta (ms)'].values[0]
        avg_abs_delta = abs(avg_delta)  # Average absolute deviation
        
        print(f"  Timestamp Direction:")
        print(f"  • Past timestamps: {past_blocks} blocks ({past_percent:.1f}%)")
        print(f"  • Future timestamps: {future_blocks} blocks ({future_percent:.1f}%)")
        
        print(f"  Timestamp Accuracy:")
        print(f"  • Average deviation from receipt time: {avg_abs_delta:.1f} ms")
        print(f"  • Max past deviation: {df['Max Past Delta (ms)'].values[0]:.1f} ms")
        print(f"  • Max future deviation: {df['Max Future Delta (ms)'].values[0]:.1f} ms")

def plot_distributions(data, output_dir=None):
    """Plot timestamp accuracy distributions"""
    # Create figure
    plt.figure(figsize=(12, 8))
    
    # Create a subplot for each chain
    colors = ['blue', 'green', 'red', 'orange', 'purple']
    all_chains = list(data.keys())
    
    for i, chain in enumerate(all_chains):
        deltas = data[chain]['Delta (ms)']
        abs_deltas = deltas.abs()
        
        # Create histogram of absolute deviations (accuracy)
        plt.hist(abs_deltas, bins=50, alpha=0.6, color=colors[i % len(colors)], 
                 label=f"{chain} (median: {abs_deltas.median():.1f}ms)")
        
        # Add vertical line at median absolute deviation
        plt.axvline(abs_deltas.median(), color=colors[i % len(colors)], 
                    linestyle='dashed', linewidth=2)
    
    plt.title('Timestamp Accuracy (Deviation from Receipt Time)', fontsize=16)
    plt.xlabel('Absolute Time Delta (ms) - Lower is better (closer to receipt time)', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(os.path.join(output_dir, f"timestamp_accuracy_{timestamp}.png"), dpi=300)
    
    plt.tight_layout()
    plt.show()
    
    # Also create the direction plot (separate figure)
    plt.figure(figsize=(12, 8))
    
    for i, chain in enumerate(all_chains):
        deltas = data[chain]['Delta (ms)']
        
        # Split data into past and future timestamps
        past_deltas = deltas[deltas > 0]
        future_deltas = deltas[deltas <= 0]
        
        # Create histogram with color-coded regions
        if len(past_deltas) > 0:
            plt.hist(past_deltas, bins=40, alpha=0.6, color='green', 
                     label=f"{chain} - Past ({len(past_deltas)/len(deltas)*100:.1f}%)")
        
        if len(future_deltas) > 0:
            plt.hist(future_deltas, bins=20, alpha=0.6, color='red', 
                     label=f"{chain} - Future ({len(future_deltas)/len(deltas)*100:.1f}%)")
        
        # Add vertical line at mean
        plt.axvline(deltas.mean(), color=colors[i % len(colors)], linestyle='dashed', linewidth=2)
    
    # Add zero line
    plt.axvline(0, color='black', linestyle='--', alpha=0.7, linewidth=2, 
                label='Zero (exact timestamp)')
    
    plt.title('Timestamp Direction (Past vs. Future)', fontsize=16)
    plt.xlabel('Time Delta (ms) - Positive: Past, Negative: Future', fontsize=12)
    plt.ylabel('Frequency', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(os.path.join(output_dir, f"timestamp_direction_{timestamp}.png"), dpi=300)
    
    plt.tight_layout()
    plt.show()

def plot_percentiles(data, output_dir=None):
    """Plot percentile analysis of timestamp accuracy"""
    plt.figure(figsize=(14, 8))
    
    # Calculate percentiles for absolute deltas (accuracy)
    percentiles = list(range(1, 100))
    
    for chain, df in data.items():
        # Calculate absolute deltas (accuracy)
        abs_deltas = df['Delta (ms)'].abs()
        abs_delta_percentiles = [np.percentile(abs_deltas, p) for p in percentiles]
        
        plt.plot(percentiles, abs_delta_percentiles, label=f"{chain} Accuracy", 
                 linewidth=2, alpha=0.7)
    
    plt.title('Timestamp Accuracy Percentiles', fontsize=16)
    plt.xlabel('Percentile', fontsize=12)
    plt.ylabel('Absolute Time Delta (ms) - Lower is better', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(os.path.join(output_dir, f"timestamp_accuracy_percentiles_{timestamp}.png"), dpi=300)
    
    plt.tight_layout()
    plt.show()
    
    # Also create direction percentiles plot
    plt.figure(figsize=(14, 8))
    
    for chain, df in data.items():
        deltas = df['Delta (ms)']
        delta_percentiles = [np.percentile(deltas, p) for p in percentiles]
        plt.plot(percentiles, delta_percentiles, label=f"{chain} Direction", 
                 linewidth=2, alpha=0.7)
    
    plt.axhline(0, color='black', linestyle='--', alpha=0.7, linewidth=2, 
                label='Zero (Past/Future boundary)')
    
    plt.title('Timestamp Direction Percentiles', fontsize=16)
    plt.xlabel('Percentile', fontsize=12)
    plt.ylabel('Time Delta (ms) - Positive: Past, Negative: Future', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(os.path.join(output_dir, f"timestamp_direction_percentiles_{timestamp}.png"), dpi=300)
    
    plt.tight_layout()
    plt.show()

def frequency_distribution(data, bin_width=100):
    """Display a simple frequency distribution of accuracy as text"""
    print("\n===== Timestamp Accuracy Distribution =====")
    
    for chain, df in data.items():
        # Calculate absolute deltas (accuracy)
        abs_deltas = df['Delta (ms)'].abs()
        
        # Determine range of bins
        min_val = 0  # Start at 0 for absolute values
        max_val = int(abs_deltas.max() + bin_width - (abs_deltas.max() % bin_width))
        
        # Create bins
        bins = list(range(min_val, max_val + bin_width, bin_width))
        
        # Count values in each bin
        hist = pd.cut(abs_deltas, bins).value_counts().sort_index()
        
        # Display as text
        print(f"\n{chain} Accuracy (bin width: {bin_width}ms):")
        print("  Deviation (ms)   | Count | Distribution")
        print("  ----------------|-------|------------")
        
        max_count = hist.max()
        bar_length = 40  # Max length of the bar
        
        for bin_range, count in hist.items():
            # Format bin range 
            range_str = f"  {bin_range.left:7.0f} to {bin_range.right:7.0f}"
            # Create a bar
            bar = "#" * int(count / max_count * bar_length)
            print(f"{range_str} | {count:5d} | {bar}")
        
        # Also report quantiles
        print(f"\n  Accuracy Quantiles:")
        print(f"  • 25% of blocks: within {abs_deltas.quantile(0.25):.1f}ms of receipt time")
        print(f"  • 50% of blocks: within {abs_deltas.median():.1f}ms of receipt time")
        print(f"  • 75% of blocks: within {abs_deltas.quantile(0.75):.1f}ms of receipt time")
        print(f"  • 95% of blocks: within {abs_deltas.quantile(0.95):.1f}ms of receipt time")
        print(f"  • 99% of blocks: within {abs_deltas.quantile(0.99):.1f}ms of receipt time")

def batch_simulation(data, batch_window_ms=15000):
    """
    Simulate how blocks would be assigned to time-based batches
    with focus on timestamp accuracy
    """
    print(f"\n===== Batch Simulation (Window: {batch_window_ms}ms) =====")
    
    for chain, df in data.items():
        # Calculate absolute deltas (accuracy)
        deltas = df['Delta (ms)']
        abs_deltas = deltas.abs()
        
        # A block would be assigned to the wrong batch if abs(delta) > batch_window_ms
        wrong_batch_count = (abs_deltas > batch_window_ms).sum()
        wrong_batch_pct = wrong_batch_count / len(deltas) * 100
        
        # Direction analysis
        future_wrong = ((deltas < 0) & (abs_deltas > batch_window_ms)).sum()
        future_wrong_pct = future_wrong / len(deltas) * 100
        
        past_wrong = ((deltas > 0) & (abs_deltas > batch_window_ms)).sum()
        past_wrong_pct = past_wrong / len(deltas) * 100
        
        print(f"\n{chain}:")
        print(f"  Batch Assignment Accuracy:")
        print(f"  • Correctly assigned blocks: {len(deltas) - wrong_batch_count} ({100 - wrong_batch_pct:.2f}%)")
        print(f"  • Incorrectly assigned blocks: {wrong_batch_count} ({wrong_batch_pct:.2f}%)")
        print(f"    - Due to future timestamps: {future_wrong} ({future_wrong_pct:.2f}%)")
        print(f"    - Due to past timestamps: {past_wrong} ({past_wrong_pct:.2f}%)")
        
        # Calculate accuracy metrics
        median_accuracy = abs_deltas.median()
        percentile_95 = abs_deltas.quantile(0.95)
        percentile_99 = abs_deltas.quantile(0.99)
        
        print(f"  Timestamp Accuracy Metrics:")
        print(f"  • Median deviation: {median_accuracy:.2f}ms")
        print(f"  • 95th percentile deviation: {percentile_95:.2f}ms")
        print(f"  • 99th percentile deviation: {percentile_99:.2f}ms")
        
        # Recommended batch window based on accuracy
        suggested_window = max(percentile_99 * 2, 5000)  # At least 5 seconds
        print(f"  Recommended minimum batch window: {suggested_window:.2f}ms ({suggested_window/1000:.1f}s)")
        
        # Calculate "reliability score" based on accuracy
        if wrong_batch_pct < 1:
            reliability = "Extremely Reliable"
        elif wrong_batch_pct < 2:
            reliability = "Very Reliable"
        elif wrong_batch_pct < 5:
            reliability = "Reliable"
        elif wrong_batch_pct < 10:
            reliability = "Moderately Reliable"
        else:
            reliability = "Less Reliable"
            
        print(f"  Reliability for batching: {reliability} ({100-wrong_batch_pct:.2f}% accuracy with {batch_window_ms}ms window)")

def plot_time_series(detailed_data, output_dir=None):
    """Plot timestamp accuracy and direction over time"""
    if not detailed_data:
        print("No detailed data with timestamps available for time series analysis.")
        return
    
    plt.figure(figsize=(16, 10))
    
    # Create a subplot for each chain
    colors = ['blue', 'green', 'red', 'orange', 'purple']
    all_chains = list(detailed_data.keys())
    
    for i, chain in enumerate(all_chains):
        df = detailed_data[chain]
        
        # Convert block timestamps to datetime for better x-axis labels
        block_times = pd.to_datetime(df['Block Timestamp (s)'], unit='s')
        
        # Plot the deltas over time
        plt.plot(block_times, df['Delta (ms)'], 
                 label=f"{chain}", color=colors[i % len(colors)],
                 marker='.', linestyle='-', alpha=0.7, markersize=4)
    
    # Add zero line to distinguish past/future timestamps
    plt.axhline(0, color='black', linestyle='--', alpha=0.5, 
                label='Zero (Past/Future boundary)')
    
    plt.title('Timestamp Accuracy Over Time', fontsize=16)
    plt.xlabel('Block Timestamp', fontsize=12)
    plt.ylabel('Time Delta (ms) - Positive: Past, Negative: Future', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Format x-axis to show dates nicely
    plt.gcf().autofmt_xdate()
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(os.path.join(output_dir, f"timestamp_time_series_{timestamp}.png"), dpi=300)
    
    plt.tight_layout()
    plt.show()
    
    # Now create a second plot with absolute deviations (accuracy only)
    plt.figure(figsize=(16, 10))
    
    for i, chain in enumerate(all_chains):
        df = detailed_data[chain]
        
        # Convert block timestamps to datetime for better x-axis labels
        block_times = pd.to_datetime(df['Block Timestamp (s)'], unit='s')
        
        # Plot the absolute deltas over time
        plt.plot(block_times, abs(df['Delta (ms)']), 
                 label=f"{chain} Accuracy", color=colors[i % len(colors)],
                 marker='.', linestyle='-', alpha=0.7, markersize=4)
    
    plt.title('Timestamp Accuracy Over Time', fontsize=16)
    plt.xlabel('Block Timestamp', fontsize=12)
    plt.ylabel('Absolute Time Delta (ms) - Lower is better', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend()
    
    # Format x-axis to show dates nicely
    plt.gcf().autofmt_xdate()
    
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plt.savefig(os.path.join(output_dir, f"timestamp_accuracy_time_series_{timestamp}.png"), dpi=300)
    
    plt.tight_layout()
    plt.show()

def analyze_trends(detailed_data):
    """Analyze trends and patterns in timestamp data"""
    if not detailed_data:
        print("No detailed data with timestamps available for trend analysis.")
        return
    
    print("\n===== Timestamp Trend Analysis =====")
    
    for chain, df in detailed_data.items():
        print(f"\n{chain}:")
        
        # Calculate rolling statistics to detect trends
        window_size = min(20, len(df) // 2)  # Use smaller window for small datasets
        if len(df) < 10:
            print("  Not enough data points for trend analysis")
            continue
            
        # Sort by block number to ensure chronological order
        df = df.sort_values('Block Number')
        
        # Calculate rolling averages
        df['Rolling_Avg'] = df['Delta (ms)'].rolling(window=window_size).mean()
        df['Rolling_Std'] = df['Delta (ms)'].rolling(window=window_size).std()
        
        # Detect if accuracy is improving or degrading over time
        first_half = df.iloc[:len(df)//2]['Delta (ms)'].abs().mean()
        second_half = df.iloc[len(df)//2:]['Delta (ms)'].abs().mean()
        
        abs_trend = second_half - first_half
        rel_trend = (abs_trend / first_half) * 100 if first_half > 0 else 0
        
        print(f"  Timestamp Accuracy Trend:")
        if abs(rel_trend) < 5:
            print(f"  • STABLE: Timestamp accuracy is consistent over the recording period")
        elif rel_trend < 0:
            print(f"  • IMPROVING: Timestamps are {abs(rel_trend):.1f}% more accurate in the recent half")
        else:
            print(f"  • DEGRADING: Timestamps are {rel_trend:.1f}% less accurate in the recent half")
        
        # Check for patterns related to block timing
        # Correlation between timestamp deltas and time between blocks
        if len(df) > 2:
            df['Block_Time_Diff'] = df['Block Timestamp (s)'].diff()
            corr = df['Block_Time_Diff'].corr(df['Delta (ms)'].abs())
            
            print(f"  Block Time Analysis:")
            if abs(corr) < 0.2:
                print(f"  • NO CORRELATION: Timestamp accuracy is not related to block timing")
            elif corr > 0:
                print(f"  • CORRELATION DETECTED: Slower blocks tend to have less accurate timestamps")
            else:
                print(f"  • INVERSE CORRELATION: Faster blocks tend to have less accurate timestamps")
            
            # Average block time
            avg_block_time = df['Block_Time_Diff'].mean()
            print(f"  • Average block time: {avg_block_time:.2f} seconds")
        
        # Check for outliers
        q1 = df['Delta (ms)'].abs().quantile(0.25)
        q3 = df['Delta (ms)'].abs().quantile(0.75)
        iqr = q3 - q1
        outlier_threshold = q3 + 1.5 * iqr
        outliers = df[df['Delta (ms)'].abs() > outlier_threshold]
        
        if len(outliers) > 0:
            outlier_pct = (len(outliers) / len(df)) * 100
            print(f"  Outlier Analysis:")
            print(f"  • {len(outliers)} outliers detected ({outlier_pct:.1f}% of blocks)")
            if outlier_pct > 10:
                print(f"  • HIGH OUTLIER RATE: Consider a larger batch window for reliability")
            elif outlier_pct > 5:
                print(f"  • MODERATE OUTLIER RATE: Some adjustments to batch window recommended")
            else:
                print(f"  • LOW OUTLIER RATE: Timestamp behavior is generally predictable")
            
        # Detect any sudden changes or shifts in accuracy
        if len(df) > 30:
            threshold = df['Delta (ms)'].abs().std() * 2
            shifts = []
            
            for i in range(window_size, len(df) - window_size):
                before = df.iloc[i-window_size:i]['Delta (ms)'].abs().mean()
                after = df.iloc[i:i+window_size]['Delta (ms)'].abs().mean()
                
                if abs(after - before) > threshold:
                    shifts.append(i)
            
            if shifts:
                print(f"  • SHIFTS DETECTED: Sudden changes in timestamp accuracy at blocks:")
                for shift in shifts[:3]:  # Show at most 3 shifts
                    block_num = df.iloc[shift]['Block Number']
                    block_time = pd.to_datetime(df.iloc[shift]['Block Timestamp (s)'], unit='s')
                    print(f"    - Block {block_num} at {block_time}")
                
                if len(shifts) > 3:
                    print(f"    - And {len(shifts) - 3} more...")

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
    data, stats, detailed_data = load_data(logs_dir, args.chains)
    
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
    
    # Time series analysis if detailed data is available
    if detailed_data:
        plot_time_series(detailed_data, output_dir)
        analyze_trends(detailed_data)
    
    # Output recommendations
    print("\n===== Recommendations for Sigma-Batch =====")
    
    for chain, df in data.items():
        deltas = df['Delta (ms)']
        abs_deltas = deltas.abs()
        
        # Calculate accuracy metrics
        median_accuracy = abs_deltas.median()
        percentile_95 = abs_deltas.quantile(0.95)
        percentile_99 = abs_deltas.quantile(0.99)
        
        # Calculate direction metrics (% past vs future)
        future_pct = ((deltas < 0).sum() / len(deltas)) * 100
        past_pct = 100 - future_pct
        
        print(f"\n{chain}:")
        print(f"  Timestamp Analysis for {chain}:")
        
        # Accuracy summary
        print(f"  Accuracy Summary:")
        print(f"  → Median deviation from receipt time: {median_accuracy:.1f}ms")
        print(f"  → 95% of blocks within {percentile_95:.1f}ms of receipt time")
        print(f"  → 99% of blocks within {percentile_99:.1f}ms of receipt time")
        
        # Direction summary
        print(f"  Direction Summary:")
        print(f"  → {past_pct:.1f}% of timestamps are in the past")
        print(f"  → {future_pct:.1f}% of timestamps are in the future")
        
        # Suggest batch window based on accuracy
        suggested_window = max(percentile_99 * 2, 5000)  # At least 5 seconds
        buffer_window = suggested_window * 0.2  # 20% buffer
        
        print(f"  Batch Window Recommendations:")
        print(f"  • Minimum recommended window: {suggested_window:.0f}ms ({suggested_window/1000:.1f}s)")
        print(f"  • With safety buffer: {suggested_window + buffer_window:.0f}ms ({(suggested_window + buffer_window)/1000:.1f}s)")
        
        # Overall assessment
        print(f"  Overall Assessment:")
        
        # Assess accuracy
        if median_accuracy < 200:
            print(f"  ✅ EXCELLENT ACCURACY: Timestamps typically within {median_accuracy:.1f}ms of receipt time")
        elif median_accuracy < 500:
            print(f"  ✓ GOOD ACCURACY: Timestamps generally within {median_accuracy:.1f}ms of receipt time")
        elif median_accuracy < 1000:
            print(f"  ⚠ MODERATE ACCURACY: Timestamps average {median_accuracy:.1f}ms from receipt time")
        else:
            print(f"  ⚠ LOWER ACCURACY: Timestamps often {median_accuracy:.1f}ms from receipt time")
        
        # Variability assessment
        std_dev = abs_deltas.std()
        if std_dev < 300:
            print(f"  ✅ LOW VARIABILITY: Very consistent timestamps (stddev: {std_dev:.1f}ms)")
        elif std_dev < 800:
            print(f"  ✓ MODERATE VARIABILITY: Fairly consistent timestamps (stddev: {std_dev:.1f}ms)")
        else:
            print(f"  ⚠ HIGH VARIABILITY: Less consistent timestamps (stddev: {std_dev:.1f}ms)")
        
        # Direction assessment
        if future_pct < 5:
            print(f"  ✅ HIGHLY COMPLIANT: Very few future timestamps ({future_pct:.1f}%)")
        elif future_pct < 15:
            print(f"  ✓ MOSTLY COMPLIANT: Reasonable number of future timestamps ({future_pct:.1f}%)")
        else:
            print(f"  ⚠ LESS COMPLIANT: Significant number of future timestamps ({future_pct:.1f}%)")
            
        # For sigma-batch suitability
        wrong_batch_pct = (abs_deltas > batch_window).sum() / len(deltas) * 100
        if wrong_batch_pct < 2:
            print(f"  ✅ HIGHLY SUITABLE for sigma-batch with {batch_window/1000:.1f}s window")
        elif wrong_batch_pct < 5:
            print(f"  ✓ SUITABLE for sigma-batch with {batch_window/1000:.1f}s window")
        elif wrong_batch_pct < 10:
            print(f"  ⚠ MODERATELY SUITABLE for sigma-batch with {batch_window/1000:.1f}s window")
        else:
            print(f"  ⚠ USE CAUTION with sigma-batch, consider {suggested_window/1000:.1f}s+ window")

if __name__ == "__main__":
    main()
