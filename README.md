# Block Timestamp Logger

A lightweight Rust utility for monitoring block timestamp accuracy across different EVM chains. This tool helps understand timestamp reliability for time-based batching systems like sigma-batch.

## Features

- Monitors Optimism, Base, and Unichain chains
- Records block timestamps vs. actual block receipt times
- Calculates key statistics:
  - Past vs. future timestamp frequency
  - Maximum deviations in both directions
  - Average time deltas
- Generates CSV reports for analysis
- Simple configuration via environment variables

## Quick Start

### Prerequisites

- Rust toolchain installed
- RPC URLs for the chains you want to monitor

### Setup and Run

1. Clone this repository
2. Create a `.env` file:

```
# Required RPC endpoints
OP_RPC_URL=https://mainnet.optimism.io
BASE_RPC_URL=https://mainnet.base.org

# Optional RPC endpoints
UNI_RPC_URL=https://rpc.unichain.network

# Optional configuration
OUTPUT_DIR=./logs
DURATION_MINUTES=60
POLL_INTERVAL_MS=500
RUST_LOG=info
```

3. Build and run:

```bash
cargo build --release
RUST_LOG=info ./target/release/block-timestamp-logger
```

## Configuration Options

All configuration is done through environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OP_RPC_URL` | RPC URL for Optimism | (Required) |
| `BASE_RPC_URL` | RPC URL for Base | (Required) |
| `UNI_RPC_URL` | RPC URL for Unichain | (Optional) |
| `OUTPUT_DIR` | Directory for log files | `./logs` |
| `DURATION_MINUTES` | How long to run the logger (0 for indefinite) | `60` |
| `POLL_INTERVAL_MS` | Polling interval in milliseconds | `500` |
| `RUST_LOG` | Logging level (`error`, `warn`, `info`, `debug`, `trace`) | `info` |

## Analyzing Results

The logger generates CSV files in the output directory:

1. `{Chain}_stats.csv`: Summary statistics about timestamp accuracy
2. `{Chain}_deltas.csv`: Raw time delta values for further analysis

Use the provided Python script to analyze these results:

```bash
python3 analyze_timestamps.py --logs-dir ./logs --output-dir ./analysis
```

This will generate visualizations and provide detailed analysis of the timestamp data.

## Understanding the Results

The most important metrics to focus on:

1. **Past vs. Future Timestamps**:
   - Past timestamps (positive delta) indicate honest timestamps
   - Future timestamps (negative delta) indicate potentially dishonest timestamps
   - Chains with higher percentages of past timestamps are more reliable for time-based batching

2. **Timestamp Variability**:
   - Standard deviation and percentile analysis show how consistent timestamps are
   - Chains with narrower distributions make better candidates for time-based batching

3. **Required Batch Window**:
   - The analysis provides recommendations for minimum batch window sizes
   - This helps ensure reliable operation of a sigma-batch implementation
