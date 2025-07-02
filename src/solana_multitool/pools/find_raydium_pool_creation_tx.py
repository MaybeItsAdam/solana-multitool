#!/usr/bin/env python3
"""
Find Raydium pool creation txs.

⚠️  WARNING:
- Only works for Raydium pools that have valid 'openTime' data in their API response
- Many older pools have openTime = 0 or missing openTime field
- Newer pools (created after ~2023) are more likely to work
- If openTime is missing/invalid, you must provide manual epoch timestamp
"""

import requests
from solana_multitool.auto_config.logging_config import logger
from solana_multitool.utils.solana_rpc import make_rpc_request
from solana_multitool.utils.solana_rpc import scan_blocks_for_txs

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


def find_block_candidates_for_pool_creation_given_slot(pool_address, center_slot, block_range=50):
    logger.info(f"Scanning slots {center_slot - block_range} to {center_slot + block_range} for pool {pool_address}")
    start_slot = max(1, center_slot - block_range)
    end_slot = center_slot + block_range

    def pool_address_filter(tx):
        account_keys = tx['transaction']['message']['accountKeys']
        # Handles both dict and string accountKeys
        if isinstance(account_keys[0], dict):
            return any(acc.get("pubkey") == pool_address for acc in account_keys)
        return pool_address in account_keys

    txs = list(scan_blocks_for_txs(start_slot, end_slot, tx_filter=pool_address_filter))
    txs.sort(key=lambda tx: tx.get('slot', 0))
    return txs

def find_raydium_pool_creation_tx(pool_address, open_time_epoch=None):
    logger.info(f"=== FINDING POOL CREATION tx ===")
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
    txs = find_block_candidates_for_pool_creation_given_slot(pool_address, target_slot, block_range=50)
    if not txs:
        logger.warning("No txs found in the scanned range")
        return None
    return txs[0]

def timestamp_to_slot(target_timestamp):
    """
    Convert a Unix timestamp to the closest Solana slot using binary search.

    Args:
        target_timestamp (int): The Unix timestamp to convert.

    Returns:
        int or None: The slot number closest to the timestamp, or None on failure.
    """
    if logger:
        logger.info(f"Converting timestamp {target_timestamp} to slot...")
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getSlot"}
    data = make_rpc_request(payload)
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
        data = make_rpc_request(payload)
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
