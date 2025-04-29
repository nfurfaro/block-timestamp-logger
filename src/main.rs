// use anyhow::{anyhow, Result};
// use chrono::{DateTime, Utc};
// use clap::Parser;
// use log::{debug, error, info};
// use serde::{Deserialize, Serialize};
// use std::collections::HashMap;
// use std::fs::OpenOptions;
// use std::path::PathBuf;
// use std::time::Instant;
// use tokio::time;
//
// /// Command line arguments for the block timestamp logger
// #[derive(Parser, Debug)]
// #[clap(author, version, about)]
// struct Args {
//     /// RPC URL for Optimism
//     #[clap(long, env)]
//     op_rpc_url: String,
//
//     /// RPC URL for Base
//     #[clap(long, env)]
//     base_rpc_url: String,
//
//     /// RPC URL for Unichain
//     #[clap(long, env)]
//     uni_rpc_url: String,
//
//     /// Output directory for logs and reports
//     #[clap(long, default_value = "./logs")]
//     output_dir: PathBuf,
//
//     /// Duration to run logger in minutes (0 for indefinite)
//     #[clap(long, default_value = "60")]
//     duration_minutes: u64,
//
//     /// Polling interval in milliseconds
//     #[clap(long, default_value = "500")]
//     poll_interval_ms: u64,
// }
//
// /// Chain information
// struct ChainInfo {
//     name: String,
//     rpc_url: String,
// }
//
// /// Statistical data collected for each chain
// #[derive(Debug, Default, Clone)]
// struct ChainStats {
//     chain_name: String,
//     total_blocks: usize,
//     timestamp_future_blocks: usize,
//     timestamp_past_blocks: usize,
//     max_future_delta_ms: i64,
//     max_past_delta_ms: i64,
//     avg_time_delta_ms: i64,
//     deltas: Vec<i64>, // Time differences in milliseconds
// }
//
// impl ChainStats {
//     fn new(chain_name: &str) -> Self {
//         Self {
//             chain_name: chain_name.to_string(),
//             ..Default::default()
//         }
//     }
//
//     fn update(&mut self, block_timestamp: u64, received_time: DateTime<Utc>) {
//         self.total_blocks += 1;
//
//         // Convert block timestamp to DateTime
//         let block_time =
//             DateTime::from_timestamp(block_timestamp as i64, 0).unwrap_or_else(|| Utc::now());
//
//         // Calculate time difference
//         let delta = received_time.signed_duration_since(block_time);
//         let delta_ms = delta.num_milliseconds();
//         self.deltas.push(delta_ms);
//
//         // Update stats
//         if delta.num_milliseconds() > 0 {
//             // Block timestamp is in the past
//             self.timestamp_past_blocks += 1;
//             if delta_ms > self.max_past_delta_ms {
//                 self.max_past_delta_ms = delta_ms;
//             }
//         } else {
//             // Block timestamp is in the future
//             self.timestamp_future_blocks += 1;
//             let abs_delta = -delta_ms;
//             if abs_delta > self.max_future_delta_ms {
//                 self.max_future_delta_ms = abs_delta;
//             }
//         }
//
//         // Recalculate average
//         self.avg_time_delta_ms = self.deltas.iter().sum::<i64>() / self.total_blocks as i64;
//     }
//
//     fn write_to_csv(&self, output_dir: &PathBuf) -> Result<()> {
//         // Ensure directory exists
//         std::fs::create_dir_all(output_dir)?;
//
//         let file_path = output_dir.join(format!("{}_stats.csv", self.chain_name));
//         let file = OpenOptions::new()
//             .write(true)
//             .create(true)
//             .truncate(true)
//             .open(&file_path)?;
//
//         let mut wtr = csv::Writer::from_writer(file);
//
//         // Write header
//         wtr.write_record(&[
//             "Chain",
//             "Total Blocks",
//             "Past Timestamp Blocks",
//             "Future Timestamp Blocks",
//             "Max Past Delta (ms)",
//             "Max Future Delta (ms)",
//             "Avg Delta (ms)",
//         ])?;
//
//         // Write data
//         wtr.write_record(&[
//             &self.chain_name,
//             &self.total_blocks.to_string(),
//             &self.timestamp_past_blocks.to_string(),
//             &self.timestamp_future_blocks.to_string(),
//             &self.max_past_delta_ms.to_string(),
//             &self.max_future_delta_ms.to_string(),
//             &self.avg_time_delta_ms.to_string(),
//         ])?;
//
//         // Write all time deltas to a separate file for histogram analysis
//         let deltas_path = output_dir.join(format!("{}_deltas.csv", self.chain_name));
//         let deltas_file = OpenOptions::new()
//             .write(true)
//             .create(true)
//             .truncate(true)
//             .open(&deltas_path)?;
//
//         let mut deltas_wtr = csv::Writer::from_writer(deltas_file);
//         deltas_wtr.write_record(&["Delta (ms)"])?;
//
//         for delta in &self.deltas {
//             deltas_wtr.write_record(&[&delta.to_string()])?;
//         }
//
//         deltas_wtr.flush()?;
//         wtr.flush()?;
//
//         info!(
//             "Stats for {} written to {}",
//             self.chain_name,
//             file_path.display()
//         );
//         Ok(())
//     }
// }
//
// // JSON-RPC request
// #[derive(Serialize)]
// struct JsonRpcRequest {
//     jsonrpc: String,
//     method: String,
//     params: Vec<serde_json::Value>,
//     id: u64,
// }
//
// // JSON-RPC response
// #[derive(Deserialize, Debug)]
// struct JsonRpcResponse<T> {
//     jsonrpc: String,
//     id: u64,
//     result: Option<T>,
//     error: Option<JsonRpcError>,
// }
//
// // JSON-RPC error
// #[derive(Deserialize, Debug)]
// struct JsonRpcError {
//     code: i64,
//     message: String,
// }
//
// // Block structure for JSON-RPC responses
// #[derive(Deserialize, Debug)]
// struct Block {
//     number: String, // Hex-encoded block number
//     timestamp: String, // Hex-encoded timestamp
//                     // Other fields we don't need
// }
//
// /// Monitors a chain for block timestamps
// struct ChainMonitor {
//     chain_info: ChainInfo,
//     client: reqwest::Client,
//     last_block_number: Option<u64>,
//     stats: ChainStats,
//     request_id: u64,
// }
//
// impl ChainMonitor {
//     fn new(chain_info: ChainInfo) -> Self {
//         let name = &chain_info.name.clone();
//         Self {
//             client: reqwest::Client::new(),
//             chain_info,
//             last_block_number: None,
//             stats: ChainStats::new(name),
//             request_id: 1,
//         }
//     }
//
//     async fn check_new_blocks(&mut self) -> Result<()> {
//         // Get the latest block number
//         let latest_block = self.get_block_number().await?;
//
//         // If this is our first check, initialize with current block and return
//         if self.last_block_number.is_none() {
//             self.last_block_number = Some(latest_block);
//             info!(
//                 "{}: Starting at block {}",
//                 self.chain_info.name, latest_block
//             );
//             return Ok(());
//         }
//
//         // Process any new blocks
//         let last_known = self.last_block_number.unwrap();
//         if latest_block > last_known {
//             for block_num in (last_known + 1)..=latest_block {
//                 match self.process_block(block_num).await {
//                     Ok(_) => {}
//                     Err(e) => error!(
//                         "{}: Error processing block {}: {}",
//                         self.chain_info.name, block_num, e
//                     ),
//                 }
//             }
//             self.last_block_number = Some(latest_block);
//         }
//
//         Ok(())
//     }
//
//     async fn get_block_number(&mut self) -> Result<u64> {
//         let request = JsonRpcRequest {
//             jsonrpc: "2.0".to_string(),
//             method: "eth_blockNumber".to_string(),
//             params: vec![],
//             id: self.request_id,
//         };
//         self.request_id += 1;
//
//         let response: JsonRpcResponse<String> = self
//             .client
//             .post(&self.chain_info.rpc_url)
//             .json(&request)
//             .send()
//             .await?
//             .json()
//             .await?;
//
//         if let Some(err) = response.error {
//             return Err(anyhow!("RPC error: {}", err.message));
//         }
//
//         let block_number_hex = response.result.ok_or_else(|| anyhow!("Missing result"))?;
//         let block_number = u64::from_str_radix(block_number_hex.trim_start_matches("0x"), 16)?;
//
//         Ok(block_number)
//     }
//
//     async fn process_block(&mut self, block_number: u64) -> Result<()> {
//         let now = Utc::now();
//
//         // Get the block by number
//         let block = self.get_block_by_number(block_number).await?;
//
//         // Parse timestamp
//         let timestamp_hex = block.timestamp.trim_start_matches("0x");
//         let timestamp = u64::from_str_radix(timestamp_hex, 16)?;
//
//         // Update stats
//         self.stats.update(timestamp, now);
//
//         debug!(
//             "{}: Block {} | Timestamp: {} | Received: {} | Delta: {}ms",
//             self.chain_info.name,
//             block_number,
//             DateTime::from_timestamp(timestamp as i64, 0)
//                 .unwrap_or_else(|| Utc::now())
//                 .format("%H:%M:%S"),
//             now.format("%H:%M:%S"),
//             now.timestamp_millis() - (timestamp as i64 * 1000)
//         );
//
//         Ok(())
//     }
//
//     async fn get_block_by_number(&mut self, block_number: u64) -> Result<Block> {
//         // Format block number as hex string
//         let block_number_hex = format!("0x{:x}", block_number);
//
//         let request = JsonRpcRequest {
//             jsonrpc: "2.0".to_string(),
//             method: "eth_getBlockByNumber".to_string(),
//             params: vec![
//                 serde_json::Value::String(block_number_hex),
//                 serde_json::Value::Bool(false),
//             ],
//             id: self.request_id,
//         };
//         self.request_id += 1;
//
//         let response: JsonRpcResponse<Block> = self
//             .client
//             .post(&self.chain_info.rpc_url)
//             .json(&request)
//             .send()
//             .await?
//             .json()
//             .await?;
//
//         if let Some(err) = response.error {
//             return Err(anyhow!("RPC error: {}", err.message));
//         }
//
//         response.result.ok_or_else(|| anyhow!("Missing result"))
//     }
//
//     fn get_stats(&self) -> ChainStats {
//         self.stats.clone()
//     }
// }
//
// #[tokio::main]
// async fn main() -> Result<()> {
//     // Initialize logging
//     env_logger::init_from_env(env_logger::Env::default().default_filter_or("info"));
//
//     // Parse command line arguments
//     let args = Args::parse();
//
//     // Create output directory
//     std::fs::create_dir_all(&args.output_dir)?;
//
//     info!("Block Timestamp Logger starting up");
//     info!("Monitoring Base, Unichain and Optimism chains");
//
//     // Create chain monitors
//     let chains = vec![
//         ChainInfo {
//             name: "Optimism".to_string(),
//             rpc_url: args.op_rpc_url,
//         },
//         ChainInfo {
//             name: "Base".to_string(),
//             rpc_url: args.base_rpc_url,
//         },
//         ChainInfo {
//             name: "Unichain".to_string(),
//             rpc_url: args.uni_rpc_url,
//         },
//     ];
//
//     let mut monitors: Vec<ChainMonitor> = chains.into_iter().map(ChainMonitor::new).collect();
//
//     // Keep track of stats for each chain
//     let mut chain_stats: HashMap<String, ChainStats> = HashMap::new();
//
//     // Convert poll interval to Duration
//     let poll_interval = time::Duration::from_millis(args.poll_interval_ms);
//
//     // Set up intervals
//     let mut poll_ticker = time::interval(poll_interval);
//     let mut report_ticker = time::interval(time::Duration::from_secs(60));
//
//     // Track start time for duration limit
//     let start_time = Instant::now();
//     let duration_limit = if args.duration_minutes > 0 {
//         Some(time::Duration::from_secs(args.duration_minutes * 60))
//     } else {
//         None
//     };
//
//     // Main loop
//     loop {
//         tokio::select! {
//             // Regular polling
//             _ = poll_ticker.tick() => {
//                 for monitor in &mut monitors {
//                     if let Err(e) = monitor.check_new_blocks().await {
//                         error!("{}: Error checking blocks: {}", monitor.chain_info.name, e);
//                     }
//
//                     // Update stats
//                     let stats = monitor.get_stats();
//                     chain_stats.insert(stats.chain_name.clone(), stats);
//                 }
//
//                 // Check if we've exceeded the duration limit
//                 if let Some(limit) = duration_limit {
//                     if start_time.elapsed() > limit {
//                         info!("Monitoring duration complete, shutting down");
//                         break;
//                     }
//                 }
//             }
//
//             // Report stats periodically
//             _ = report_ticker.tick() => {
//                 info!("Current Stats:");
//                 for (name, stats) in &chain_stats {
//                     info!(
//                         "{}: {} blocks | Avg delta: {}ms | Past: {} | Future: {}",
//                         name,
//                         stats.total_blocks,
//                         stats.avg_time_delta_ms,
//                         stats.timestamp_past_blocks,
//                         stats.timestamp_future_blocks
//                     );
//
//                     // Write current stats to file
//                     if let Err(e) = stats.write_to_csv(&args.output_dir) {
//                         error!("Failed to write stats for {}: {}", name, e);
//                     }
//                 }
//             }
//         }
//     }
//
//     // Final stats reporting
//     info!("Final Statistics:");
//     for (name, stats) in &chain_stats {
//         info!("{}: {} blocks analyzed", name, stats.total_blocks);
//         info!(
//             "  - Past timestamps: {} blocks (max delta: {}ms)",
//             stats.timestamp_past_blocks, stats.max_past_delta_ms
//         );
//         info!(
//             "  - Future timestamps: {} blocks (max delta: {}ms)",
//             stats.timestamp_future_blocks, stats.max_future_delta_ms
//         );
//         info!("  - Average time delta: {}ms", stats.avg_time_delta_ms);
//
//         // Write final stats to file
//         if let Err(e) = stats.write_to_csv(&args.output_dir) {
//             error!("Failed to write final stats for {}: {}", name, e);
//         }
//     }
//
//     Ok(())
// }

use anyhow::{anyhow, Result};
use chrono::{DateTime, Utc};
use log::{debug, error, info};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::fs::OpenOptions;
use std::path::PathBuf;
use std::time::Instant;
use tokio::time;

/// Chain information
struct ChainInfo {
    name: String,
    rpc_url: String,
}

/// Statistical data collected for each chain
#[derive(Debug, Default, Clone)]
struct ChainStats {
    chain_name: String,
    total_blocks: usize,
    timestamp_future_blocks: usize,
    timestamp_past_blocks: usize,
    max_future_delta_ms: i64,
    max_past_delta_ms: i64,
    avg_time_delta_ms: i64,
    deltas: Vec<i64>, // Time differences in milliseconds
}

impl ChainStats {
    fn new(chain_name: &str) -> Self {
        Self {
            chain_name: chain_name.to_string(),
            ..Default::default()
        }
    }

    fn update(&mut self, block_timestamp: u64, received_time: DateTime<Utc>) {
        self.total_blocks += 1;

        // Convert block timestamp to DateTime
        let block_time =
            DateTime::from_timestamp(block_timestamp as i64, 0).unwrap_or_else(|| Utc::now());

        // Calculate time difference
        let delta = received_time.signed_duration_since(block_time);
        let delta_ms = delta.num_milliseconds();
        self.deltas.push(delta_ms);

        // Update stats
        if delta.num_milliseconds() > 0 {
            // Block timestamp is in the past
            self.timestamp_past_blocks += 1;
            if delta_ms > self.max_past_delta_ms {
                self.max_past_delta_ms = delta_ms;
            }
        } else {
            // Block timestamp is in the future
            self.timestamp_future_blocks += 1;
            let abs_delta = -delta_ms;
            if abs_delta > self.max_future_delta_ms {
                self.max_future_delta_ms = abs_delta;
            }
        }

        // Recalculate average
        self.avg_time_delta_ms = self.deltas.iter().sum::<i64>() / self.total_blocks as i64;
    }

    fn write_to_csv(&self, output_dir: &PathBuf) -> Result<()> {
        // Ensure directory exists
        std::fs::create_dir_all(output_dir)?;

        let file_path = output_dir.join(format!("{}_stats.csv", self.chain_name));
        let file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(&file_path)?;

        let mut wtr = csv::Writer::from_writer(file);

        // Write header
        wtr.write_record(&[
            "Chain",
            "Total Blocks",
            "Past Timestamp Blocks",
            "Future Timestamp Blocks",
            "Max Past Delta (ms)",
            "Max Future Delta (ms)",
            "Avg Delta (ms)",
        ])?;

        // Write data
        wtr.write_record(&[
            &self.chain_name,
            &self.total_blocks.to_string(),
            &self.timestamp_past_blocks.to_string(),
            &self.timestamp_future_blocks.to_string(),
            &self.max_past_delta_ms.to_string(),
            &self.max_future_delta_ms.to_string(),
            &self.avg_time_delta_ms.to_string(),
        ])?;

        // Write all time deltas to a separate file for histogram analysis
        let deltas_path = output_dir.join(format!("{}_deltas.csv", self.chain_name));
        let deltas_file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(&deltas_path)?;

        let mut deltas_wtr = csv::Writer::from_writer(deltas_file);
        deltas_wtr.write_record(&["Delta (ms)"])?;

        for delta in &self.deltas {
            deltas_wtr.write_record(&[&delta.to_string()])?;
        }

        deltas_wtr.flush()?;
        wtr.flush()?;

        info!(
            "Stats for {} written to {}",
            self.chain_name,
            file_path.display()
        );
        Ok(())
    }
}

// JSON-RPC request
#[derive(Serialize)]
struct JsonRpcRequest {
    jsonrpc: String,
    method: String,
    params: Vec<serde_json::Value>,
    id: u64,
}

// JSON-RPC response
#[derive(Deserialize, Debug)]
struct JsonRpcResponse<T> {
    jsonrpc: String,
    id: u64,
    result: Option<T>,
    error: Option<JsonRpcError>,
}

// JSON-RPC error
#[derive(Deserialize, Debug)]
struct JsonRpcError {
    code: i64,
    message: String,
}

// Block structure for JSON-RPC responses
#[derive(Deserialize, Debug)]
struct Block {
    number: String, // Hex-encoded block number
    timestamp: String, // Hex-encoded timestamp
                    // Other fields we don't need
}

/// Monitors a chain for block timestamps
struct ChainMonitor {
    chain_info: ChainInfo,
    client: reqwest::Client,
    last_block_number: Option<u64>,
    stats: ChainStats,
    request_id: u64,
}

impl ChainMonitor {
    fn new(chain_info: ChainInfo) -> Self {
        let name = &chain_info.name.clone();
        Self {
            client: reqwest::Client::new(),
            chain_info,
            last_block_number: None,
            stats: ChainStats::new(name),
            request_id: 1,
        }
    }

    async fn check_new_blocks(&mut self) -> Result<()> {
        // Get the latest block number
        let latest_block = self.get_block_number().await?;

        // If this is our first check, initialize with current block and return
        if self.last_block_number.is_none() {
            self.last_block_number = Some(latest_block);
            info!(
                "{}: Starting at block {}",
                self.chain_info.name, latest_block
            );
            return Ok(());
        }

        // Process any new blocks
        let last_known = self.last_block_number.unwrap();
        if latest_block > last_known {
            for block_num in (last_known + 1)..=latest_block {
                match self.process_block(block_num).await {
                    Ok(_) => {}
                    Err(e) => error!(
                        "{}: Error processing block {}: {}",
                        self.chain_info.name, block_num, e
                    ),
                }
            }
            self.last_block_number = Some(latest_block);
        }

        Ok(())
    }

    async fn get_block_number(&mut self) -> Result<u64> {
        let request = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            method: "eth_blockNumber".to_string(),
            params: vec![],
            id: self.request_id,
        };
        self.request_id += 1;

        let response: JsonRpcResponse<String> = self
            .client
            .post(&self.chain_info.rpc_url)
            .json(&request)
            .send()
            .await?
            .json()
            .await?;

        if let Some(err) = response.error {
            return Err(anyhow!("RPC error: {}", err.message));
        }

        let block_number_hex = response.result.ok_or_else(|| anyhow!("Missing result"))?;
        let block_number = u64::from_str_radix(block_number_hex.trim_start_matches("0x"), 16)?;

        Ok(block_number)
    }

    async fn process_block(&mut self, block_number: u64) -> Result<()> {
        let now = Utc::now();

        // Get the block by number
        let block = self.get_block_by_number(block_number).await?;

        // Parse timestamp
        let timestamp_hex = block.timestamp.trim_start_matches("0x");
        let timestamp = u64::from_str_radix(timestamp_hex, 16)?;

        // Update stats
        self.stats.update(timestamp, now);

        debug!(
            "{}: Block {} | Timestamp: {} | Received: {} | Delta: {}ms",
            self.chain_info.name,
            block_number,
            DateTime::from_timestamp(timestamp as i64, 0)
                .unwrap_or_else(|| Utc::now())
                .format("%H:%M:%S"),
            now.format("%H:%M:%S"),
            now.timestamp_millis() - (timestamp as i64 * 1000)
        );

        Ok(())
    }

    async fn get_block_by_number(&mut self, block_number: u64) -> Result<Block> {
        // Format block number as hex string
        let block_number_hex = format!("0x{:x}", block_number);

        let request = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            method: "eth_getBlockByNumber".to_string(),
            params: vec![
                serde_json::Value::String(block_number_hex),
                serde_json::Value::Bool(false),
            ],
            id: self.request_id,
        };
        self.request_id += 1;

        let response: JsonRpcResponse<Block> = self
            .client
            .post(&self.chain_info.rpc_url)
            .json(&request)
            .send()
            .await?
            .json()
            .await?;

        if let Some(err) = response.error {
            return Err(anyhow!("RPC error: {}", err.message));
        }

        response.result.ok_or_else(|| anyhow!("Missing result"))
    }

    fn get_stats(&self) -> ChainStats {
        self.stats.clone()
    }
}

// Load an environment variable as a u64 with a default value
fn get_env_as_u64(key: &str, default: u64) -> u64 {
    match env::var(key) {
        Ok(val) => val.parse().unwrap_or(default),
        Err(_) => default,
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    env_logger::init_from_env(env_logger::Env::default().default_filter_or("info"));

    // Get configuration from environment variables
    let output_dir = env::var("OUTPUT_DIR").unwrap_or_else(|_| "./logs".to_string());
    let duration_minutes = get_env_as_u64("DURATION_MINUTES", 60);
    let poll_interval_ms = get_env_as_u64("POLL_INTERVAL_MS", 500);

    // Create output directory
    let output_path = PathBuf::from(output_dir);
    std::fs::create_dir_all(&output_path)?;

    info!("Block Timestamp Logger starting up");
    info!("Using RPC URLs from environment variables");

    // Create chain monitors from environment variables
    let mut chains = Vec::new();

    // Add Optimism if URL is in environment
    if let Ok(op_url) = env::var("OP_RPC_URL") {
        chains.push(ChainInfo {
            name: "Optimism".to_string(),
            rpc_url: op_url,
        });
        info!("Added Optimism to monitoring");
    } else {
        error!("OP_RPC_URL environment variable is missing");
    }

    // Add Base if URL is in environment
    if let Ok(base_url) = env::var("BASE_RPC_URL") {
        chains.push(ChainInfo {
            name: "Base".to_string(),
            rpc_url: base_url,
        });
        info!("Added Base to monitoring");
    } else {
        error!("BASE_RPC_URL environment variable is missing");
    }

    // Add Unichain if URL is in environment
    if let Ok(uni_url) = env::var("UNI_RPC_URL") {
        chains.push(ChainInfo {
            name: "Unichain".to_string(),
            rpc_url: uni_url,
        });
        info!("Added Unichain to monitoring");
    }

    if chains.is_empty() {
        return Err(anyhow!("No RPC URLs provided in environment variables. Set at least OP_RPC_URL and BASE_RPC_URL."));
    }

    let mut monitors: Vec<ChainMonitor> = chains.into_iter().map(ChainMonitor::new).collect();

    // Keep track of stats for each chain
    let mut chain_stats: HashMap<String, ChainStats> = HashMap::new();

    // Convert poll interval to Duration
    let poll_interval = time::Duration::from_millis(poll_interval_ms);

    // Set up intervals
    let mut poll_ticker = time::interval(poll_interval);
    let mut report_ticker = time::interval(time::Duration::from_secs(60));

    // Track start time for duration limit
    let start_time = Instant::now();
    let duration_limit = if duration_minutes > 0 {
        Some(time::Duration::from_secs(duration_minutes * 60))
    } else {
        None
    };

    // Main loop
    loop {
        tokio::select! {
            // Regular polling
            _ = poll_ticker.tick() => {
                for monitor in &mut monitors {
                    if let Err(e) = monitor.check_new_blocks().await {
                        error!("{}: Error checking blocks: {}", monitor.chain_info.name, e);
                    }

                    // Update stats
                    let stats = monitor.get_stats();
                    chain_stats.insert(stats.chain_name.clone(), stats);
                }

                // Check if we've exceeded the duration limit
                if let Some(limit) = duration_limit {
                    if start_time.elapsed() > limit {
                        info!("Monitoring duration complete, shutting down");
                        break;
                    }
                }
            }

            // Report stats periodically
            _ = report_ticker.tick() => {
                info!("Current Stats:");
                for (name, stats) in &chain_stats {
                    info!(
                        "{}: {} blocks | Avg delta: {}ms | Past: {} | Future: {}",
                        name,
                        stats.total_blocks,
                        stats.avg_time_delta_ms,
                        stats.timestamp_past_blocks,
                        stats.timestamp_future_blocks
                    );

                    // Write current stats to file
                    if let Err(e) = stats.write_to_csv(&output_path) {
                        error!("Failed to write stats for {}: {}", name, e);
                    }
                }
            }
        }
    }

    // Final stats reporting
    info!("Final Statistics:");
    for (name, stats) in &chain_stats {
        info!("{}: {} blocks analyzed", name, stats.total_blocks);
        info!(
            "  - Past timestamps: {} blocks (max delta: {}ms)",
            stats.timestamp_past_blocks, stats.max_past_delta_ms
        );
        info!(
            "  - Future timestamps: {} blocks (max delta: {}ms)",
            stats.timestamp_future_blocks, stats.max_future_delta_ms
        );
        info!("  - Average time delta: {}ms", stats.avg_time_delta_ms);

        // Write final stats to file
        if let Err(e) = stats.write_to_csv(&output_path) {
            error!("Failed to write final stats for {}: {}", name, e);
        }
    }

    Ok(())
}
