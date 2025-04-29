# Block Timestamp Analysis Guide

This guide explains how to analyze the data collected by the block-timestamp-logger to understand timestamp accuracy across different chains.

## Running the Analysis Script

1. Install required Python packages:
```bash
pip install pandas matplotlib numpy
```

2. Run the analysis script:
```bash
python analyze_timestamps.py --logs-dir ./logs --output-dir ./analysis
```

Options:
- `--logs-dir`: Directory containing the CSV files (default: ./logs)
- `--output-dir`: Directory to save plots (default: ./analysis)
- `--chains`: Specific chains to analyze (optional, defaults to all found)
- `--batch-window`: Batch window in milliseconds for simulation (default: 15000ms/15s)

## Interpreting the Results

### 1. Timestamp Statistical Summary

This shows the core statistics for each chain:
- Percentage of blocks with past vs future timestamps
- Average time delta (positive = past, negative = future)
- Maximum deviations in either direction

**Key insights:**
- Ideally, most timestamps should be in the past (block.timestamp ≤ current time)
- High percentage of future timestamps may indicate clock synchronization issues
- Large average deltas suggest consistent timing offsets

### 2. Timestamp Distributions

The histogram shows the distribution of timestamp deltas:
- X-axis: Time difference in milliseconds (positive = block timestamp is in the past)
- Y-axis: Frequency (number of blocks)

**Key insights:**
- Width of distribution shows timestamp variability
- Multiple peaks may indicate different validator behaviors
- Location relative to zero line shows bias toward past or future

### 3. Percentile Analysis

This graph shows percentiles of timestamp deltas:
- X-axis: Percentile (1st through 99th)
- Y-axis: Time delta in milliseconds

**Key insights:**
- Steepness indicates variability in timestamps
- Distance from zero line shows systematic bias
- Extreme percentiles (95th+) show worst-case scenarios

### 4. Batch Simulation Results

This analysis simulates how blocks would be assigned to time-based batches:
- Percentage of blocks that would be assigned to wrong batches
- 99th percentile absolute delta
- Recommended minimum batch window size

**Key insights:**
- Low wrong-batch percentage is critical for reliable time-based batching
- Recommended batch window provides a conservative estimate for reliability
- Different window sizes can be simulated by changing the `--batch-window` parameter

## What to Look For

### For Time-Based Batching (sigma-batch)

1. **Consistency**: Chains with narrower distributions make better candidates for time-based batching

2. **Accuracy**: Chains with timestamps closer to zero (less bias) are more reliable

3. **Predictability**: Lower percentages of wrong batch assignments mean fewer edge cases to handle

4. **Chain Comparisons**: Significant differences between chains may require chain-specific parameters

## Example Interpretation

"If Base shows an average delta of +500ms with 98% past timestamps, while Optimism shows -200ms with 30% future timestamps, this suggests:

1. Base has more conservative timestamp assignment (slightly in the past)
2. Optimism has more variability in timestamps, with a significant portion in the future
3. Sigma-batch implementation might need larger time windows for Optimism than for Base
4. Base might be more reliable for time-critical applications"

## Next Steps

Based on your analysis results, you might want to:

1. Adjust your sigma-batch time window based on the 99th percentile recommendation
2. Implement chain-specific parameters if timestamp behaviors differ significantly
3. Consider fallback mechanisms for blocks that fall outside expected time windows
4. Run longer monitoring sessions during different network conditions for more robust data
