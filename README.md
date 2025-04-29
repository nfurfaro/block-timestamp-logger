# Block Timestamp Logger

A lightweight Rust utility for monitoring block timestamp accuracy across different EVM chains (currently Base and Optimism). This tool helps understand timestamp reliability for time-based batching systems like sigma-batch.

## Features

- Monitors Optimism and Base chains simultaneously
- Records block timestamps vs. actual block receipt times
- Calculates key statistics:
  - Past vs. future timestamp frequency
  - Maximum deviations in both directions
  - Average time deltas
- Generates CSV reports for analysis
- Simple direct JSON-RPC implementation with minimal dependencies

## Quick Start

### Prerequisites

- Rust toolchain installed
- RPC URLs for Base and Optimism

### Running the Logger

1. Clone this repository
2. Build the project:

```bash
cargo build --release
```

3. Set up your RPC URLs:

Option A - Use the provided shell script:
```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your RPC URLs
nano .env  # or use any editor

# Make the run script executable
chmod +x run-logger.sh

# Run the logger
./run-logger.sh
```

Option B - Set environment variables:
```bash
# Set environment variables for your RPC endpoints
export OP_RPC_URL=https://your-optimism-rpc-url
export BASE_RPC_URL=https://your-base-rpc-url

# Run with detailed logging
RUST_LOG=info ./target/release/block-timestamp-logger
```

Option C - Provide URLs directly:
```bash
RUST_LOG=info ./target/release/block-timestamp-logger \
  --op-rpc-url=https://your-optimism-rpc-url \
  --base-rpc-url=https://your-base-rpc-url
```

## Command Line Options

```
Options:
  --op-rpc-url <OP_RPC_URL>                RPC URL for Optimism [env: OP_RPC_URL=]
  --base-rpc-url <BASE_RPC_URL>            RPC URL for Base [env: BASE_RPC_URL=]
  --output-dir <OUTPUT_DIR>                Output directory for logs and reports [default: ./logs]
  --duration-minutes <DURATION_MINUTES>    Duration to run logger in minutes (0 for indefinite) [default: 60]
  --poll-interval-ms <POLL_INTERVAL_MS>    Polling interval in milliseconds [default: 500]
  -h, --help                               Print help
  -V, --version                            Print version
```

## Output

The logger generates CSV files in the output directory with:

1. Summary statistics for each chain
2. Raw time deltas for deeper analysis

## Next Steps

- Add support for more chains
- Create a Nix flake for better dependency management
