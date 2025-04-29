#!/bin/bash

# Load environment variables if .env file exists
if [ -f .env ]; then
  echo "Loading environment from .env file..."
  export $(grep -v '^#' .env | xargs)
fi

# Check if RPC URLs are set
if [ -z "$OP_RPC_URL" ] || [ -z "$BASE_RPC_URL" ]; then
  echo "Error: RPC URLs are not set. Please set OP_RPC_URL and BASE_RPC_URL."
  echo "You can create a .env file based on .env.example or set them directly."
  exit 1
fi

# Set default logging level if not specified
export RUST_LOG=${RUST_LOG:-info}

# Build if binary doesn't exist
if [ ! -f ./target/release/block-timestamp-logger ]; then
  echo "Building project..."
  cargo build --release
fi

# Run the logger
echo "Starting Block Timestamp Logger..."
./target/release/block-timestamp-logger "$@"
