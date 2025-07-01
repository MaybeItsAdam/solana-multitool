#!/usr/bin/env python3
"""
Simple CLI tool to find Raydium pool creation transactions.

⚠️  WARNING:
- Only works for Raydium pools that have valid 'openTime' data in their API response
- Many older pools have openTime = 0 or missing openTime field
- Newer pools (created after ~2023) are more likely to work
- If openTime is missing/invalid, you must provide manual epoch timestamp
- or scrape for event in

Usage:
    python find_pool_creation.py <pool_address> [open_time_epoch]

Examples:
    # Auto-fetch from API (works only if pool has valid openTime)
    python find_pool_creation.py 58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2

    # Manual timestamp (required for pools with openTime = 0)
    python find_pool_creation.py POOL_ADDRESS 1703123456

Requires openTime to be a field on the pool obtained from raydium's api
"""

import sys
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from solana_multitool.utils import rate_limiter as net
from solana_multitool.utils.output_manager import output_manager
from solana_multitool.auto_config.environment import get_solana_rpc_url, get_max_requests_per_second
from solana_multitool.auto_config.logging_config import logger

SOLANA_RPC_URL = get_solana_rpc_url()
rate_limiter = net.RateLimiter(max_requests=get_max_requests_per_second(), time_window=1.0)
# logger is now imported directly from logging_config

def get_pool_open_time_from_raydium_api(pool_address):
    try:
        url = f"https://api-v3.raydium.io/pools/info/ids"
        params = {"ids": pool_address}
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if 'data' in data and data['data']:
            pool_info = data['data'][0]
            open_time = pool_info.get('openTime')
            logger.info(f"open_time: {open_time}")
            if open_time and int(open_time) > 0:
                return int(open_time)
        return None
    except Exception as e:
        logger.error(f"Failed to get pool open time from API: {e}")
        return None

def make_rpc_request_with_rate_limit(payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            rate_limiter.acquire()
            response = requests.post(SOLANA_RPC_URL, json=payload, timeout=30)
            if response.status_code == 429:
                logger.warning(f"Rate limited on attempt {attempt + 1}")
                net.exponential_backoff_sleep(attempt)
                continue
            response.raise_for_status()
            data = response.json()
            if 'error' in data:
                logger.error(f"RPC Error: {data['error']}")
                return None
            return data
        except Exception as e:
            logger.error(f"Request failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                net.exponential_backoff_sleep(attempt)
    return None

def timestamp_to_slot(target_timestamp):
    logger.info(f"Converting timestamp {target_timestamp} to slot...")
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getSlot"}
    data = make_rpc_request_with_rate_limit(payload)
    if not data:
        return None
    current_slot = data['result']
    min_slot = 1
    max_slot = current_slot
    best_slot = None
    best_diff = float('inf')
    for _ in range(25):
        if min_slot > max_slot:
            break
        mid_slot = (min_slot + max_slot) // 2
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBlockTime",
            "params": [mid_slot]
        }
        data = make_rpc_request_with_rate_limit(payload)
        if not data or data.get('result') is None:
            min_slot = mid_slot + 1
            continue
        block_time = data['result']
        diff = abs(block_time - target_timestamp)
        if diff < best_diff:
            best_diff = diff
            best_slot = mid_slot
        if block_time < target_timestamp:
            min_slot = mid_slot + 1
        else:
            max_slot = mid_slot - 1
    return best_slot

def scan_blocks_for_pool_creation(pool_address, center_slot, block_range=50):
    logger.info(f"Scanning slots {center_slot - block_range} to {center_slot + block_range} for pool {pool_address}")
    start_slot = max(1, center_slot - block_range)
    end_slot = center_slot + block_range
    def scan_block(slot):
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBlock",
            "params": [slot, {
                "encoding": "json",
                "maxSupportedTransactionVersion": 0,
                "transactionDetails": "full",
                "rewards": False
            }]
        }
        data = make_rpc_request_with_rate_limit(payload)
        if not data or not data.get('result'):
            return []
        block = data['result']
        block_transactions = []
        if 'transactions' in block:
            for tx in block['transactions']:
                account_keys = tx['transaction']['message']['accountKeys']
                if pool_address in account_keys:
                    tx['slot'] = slot
                    tx['blockTime'] = block.get('blockTime')
                    block_transactions.append(tx)
        return block_transactions
    all_transactions = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_slot = {
            executor.submit(scan_block, slot): slot
            for slot in range(start_slot, end_slot + 1)
        }
        for future in as_completed(future_to_slot):
            transactions = future.result()
            all_transactions.extend(transactions)
    all_transactions.sort(key=lambda tx: tx.get('slot', 0))
    return all_transactions

def find_pool_creation_transaction(pool_address, open_time_epoch=None):
    logger.info(f"=== FINDING POOL CREATION TRANSACTION ===")
    logger.info(f"Pool Address: {pool_address}")
    if open_time_epoch:
        open_timestamp = int(open_time_epoch)
    else:
        open_timestamp = get_pool_open_time_from_raydium_api(pool_address)
        if not open_timestamp:
            logger.error("Could not get pool open time - see messages above for troubleshooting")
            return None
    target_slot = timestamp_to_slot(open_timestamp)
    if not target_slot:
        logger.error("Could not convert timestamp to slot")
        return None
    transactions = scan_blocks_for_pool_creation(pool_address, target_slot, block_range=50)
    if not transactions:
        logger.warning("No transactions found in the scanned range")
        return None
    return transactions[0]

def main():
    if len(sys.argv) < 2:
        logger.info(__doc__)
        return
    pool_address = sys.argv[1]
    open_time_epoch = None
    if len(sys.argv) >= 3:
        try:
            open_time_epoch = int(sys.argv[2])
        except ValueError:
            print("Error: open_time_epoch must be a valid integer (Unix timestamp)")
            return
    logger.info(f"Searching for pool creation transaction...")
    logger.info(f"Pool: {pool_address}")
    if open_time_epoch:
        readable_time = datetime.fromtimestamp(open_time_epoch).strftime('%Y-%m-%d %H:%M:%S UTC')
        logger.info(f"Open time: {readable_time} (epoch: {open_time_epoch})")
    else:
        logger.info("Open time: Will fetch from Raydium API")
    logger.info("Scanning ±50 blocks around open time...\n")
    result = find_pool_creation_transaction(pool_address, open_time_epoch)
    if result:
        signature = result['transaction']['signatures'][0]
        logger.info(f"\n🎉 SUCCESS!")
        logger.info(f"Creation transaction: {signature}")
        logger.info(f"View on explorer: https://explorer.solana.com/tx/{signature}")
    else:
        logger.error(f"\n❌ FAILED: Could not find pool creation transaction")
        logger.info(f"\n💡 Troubleshooting:")
        logger.info(f"   - Pool may have openTime = 0 (try manual timestamp)")
        logger.info(f"   - Pool may be too old (pre-2023 pools often lack openTime)")
        logger.info(f"   - Check pool address on explorer.solana.com for anchor data")
        logger.info(f"   - Use manual epoch timestamp if available")

if __name__ == '__main__':
    main()
