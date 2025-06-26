import requests
import json
import logging
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import network_utils as net
from output_manager import output_manager
from config import get_solana_rpc_url, get_max_requests_per_second

# Configure logging using output manager
log_path = output_manager.setup_logging(logging.INFO, "pool_creation_scanner.log")
logger = logging.getLogger(__name__)

# Get RPC endpoint and rate limiting from config
SOLANA_RPC_URL = get_solana_rpc_url()

# Rate limiter for API requests (using config)
rate_limiter = net.RateLimiter(max_requests=get_max_requests_per_second(), time_window=1.0)

def make_rpc_request(payload, max_retries=3):
    """Make RPC request with rate limiting and retries."""
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

def get_pool_open_time_from_raydium_api(pool_address):
    """
    Get pool open time from Raydium API.
    
    ⚠️  LIMITATION: Many Raydium pools have openTime = 0 or missing openTime field.
    This is especially common for:
    - Older pools (created before ~2023)
    - Manually created pools
    - Pools with non-standard configurations
    
    If openTime is 0 or missing, you must provide manual epoch timestamp.
    """
    try:
        url = f"https://api-v3.raydium.io/pools/info/ids"
        params = {"ids": pool_address}
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'data' in data and data['data']:
            pool_info = data['data'][0]
            open_time = pool_info.get('openTime')
            
            if open_time and int(open_time) > 0:
                open_timestamp = int(open_time)
                readable_time = datetime.fromtimestamp(open_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
                logger.info(f"Pool open time from API: {readable_time} (timestamp: {open_timestamp})")
                return open_timestamp
            elif open_time == 0 or open_time == "0":
                logger.warning(f"Pool {pool_address} has openTime = 0. This pool requires manual timestamp.")
                print(f"⚠️  Pool {pool_address} has openTime = 0")
                print(f"   This is common for older Raydium pools.")
                print(f"   Please provide manual epoch timestamp:")
                print(f"   python find_pool_creation.py {pool_address} <epoch_timestamp>")
                return None
            else:
                logger.warning(f"Pool {pool_address} has missing or invalid openTime field")
                print(f"⚠️  Pool {pool_address} is missing openTime data")
                print(f"   This pool was likely created before Raydium added openTime tracking.")
                print(f"   Please provide manual epoch timestamp from explorer.solana.com")
                return None
                
        logger.error("No pool data found in Raydium API response")
        print(f"❌ Pool {pool_address} not found in Raydium API")
        return None
        
    except Exception as e:
        logger.error(f"Failed to get pool open time from API: {e}")
        print(f"❌ Failed to fetch pool data from Raydium API: {e}")
        return None

def timestamp_to_slot(target_timestamp):
    """Convert Unix timestamp to Solana slot using binary search."""
    logger.info(f"Converting timestamp {target_timestamp} to slot...")

    # Get current slot
    payload = {"jsonrpc": "2.0", "id": 1, "method": "getSlot"}
    data = make_rpc_request(payload)
    if not data:
        return None

    current_slot = data['result']
    logger.info(f"Current slot: {current_slot}")

    # Binary search for target timestamp
    min_slot = 1
    max_slot = current_slot
    best_slot = None
    best_diff = float('inf')

    for _ in range(25):  # Should be enough iterations
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

    if best_slot:
        logger.info(f"Found closest slot: {best_slot} (time difference: {best_diff} seconds)")
        return best_slot

    logger.error("Could not find suitable slot")
    return None

def scan_blocks_for_pool_creation(pool_address, center_slot, block_range=50):
    """
    Scan ±block_range slots around center_slot to find pool creation transaction.

    Args:
        pool_address: The pool address to search for
        center_slot: The slot to center the search around
        block_range: Number of slots to search before and after center_slot (default: 50)
    """
    logger.info(f"Scanning slots {center_slot - block_range} to {center_slot + block_range} for pool {pool_address}")

    start_slot = max(1, center_slot - block_range)
    end_slot = center_slot + block_range

    def scan_block(slot):
        """Scan a single block for transactions involving the pool address."""
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

        data = make_rpc_request(payload)
        if not data or not data.get('result'):
            return []

        block = data['result']
        block_transactions = []

        if 'transactions' in block:
            for tx in block['transactions']:
                # Check if pool address is in account keys
                account_keys = tx['transaction']['message']['accountKeys']
                if pool_address in account_keys:
                    # Add slot and block time info to transaction
                    tx['slot'] = slot
                    tx['blockTime'] = block.get('blockTime')
                    block_transactions.append(tx)
                    logger.info(f"Found transaction in slot {slot}: {tx['transaction']['signatures'][0]}")

        return block_transactions

    # Use threading to scan blocks in parallel
    all_transactions = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all block scanning tasks
        future_to_slot = {
            executor.submit(scan_block, slot): slot
            for slot in range(start_slot, end_slot + 1)
        }

        # Collect results as they complete
        for future in as_completed(future_to_slot):
            slot = future_to_slot[future]
            try:
                transactions = future.result()
                all_transactions.extend(transactions)
            except Exception as e:
                logger.error(f"Error scanning slot {slot}: {e}")

    # Sort transactions by slot (earliest first)
    all_transactions.sort(key=lambda tx: tx.get('slot', 0))

    logger.info(f"Found {len(all_transactions)} total transactions involving pool {pool_address}")

    return all_transactions

def find_pool_creation_transaction(pool_address, open_time_epoch=None):
    """
    Main function to find pool creation transaction.
    
    ⚠️  LIMITATIONS:
    - Only works for pools with valid openTime data or manual timestamp
    - Many older Raydium pools have openTime = 0 or missing
    - Success rate is higher for newer pools (post-2023)
    
    Args:
        pool_address: The Raydium pool address
        open_time_epoch: Optional epoch timestamp. If not provided, will fetch from Raydium API
    
    Returns:
        dict: The pool creation transaction or None if not found
    """
    logger.info(f"=== FINDING POOL CREATION TRANSACTION ===")
    logger.info(f"Pool Address: {pool_address}")
    
    # Step 1: Get open time
    if open_time_epoch:
        open_timestamp = int(open_time_epoch)
        readable_time = datetime.fromtimestamp(open_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
        logger.info(f"Using provided open time: {readable_time} (timestamp: {open_timestamp})")
        print(f"✅ Using manual timestamp: {readable_time}")
    else:
        print(f"🔍 Fetching pool data from Raydium API...")
        open_timestamp = get_pool_open_time_from_raydium_api(pool_address)
        if not open_timestamp:
            logger.error("Could not get pool open time - see messages above for troubleshooting")
            return None

    # Step 2: Convert timestamp to slot
    target_slot = timestamp_to_slot(open_timestamp)
    if not target_slot:
        logger.error("Could not convert timestamp to slot")
        return None

    # Step 3: Scan ±50 blocks around target slot
    transactions = scan_blocks_for_pool_creation(pool_address, target_slot, block_range=50)

    if not transactions:
        logger.warning("No transactions found in the scanned range")
        print(f"\n❌ No transactions found involving pool {pool_address}")
        print(f"   Scanned slots {target_slot - 50} to {target_slot + 50}")
        print(f"   This could mean:")
        print(f"   - Pool creation happened outside the ±50 slot range")
        print(f"   - Incorrect timestamp provided")
        print(f"   - Pool address is incorrect")
        print(f"   - Pool was created differently than expected")
        return None

    # The first transaction is likely the creation transaction
    creation_tx = transactions[0]

    # Save results
    result_data = {
        "pool_address": pool_address,
        "open_time_epoch": open_timestamp,
        "target_slot": target_slot,
        "creation_transaction": creation_tx,
        "all_transactions": transactions
    }

    filename = output_manager.save_pool_creation_scan(pool_address, result_data)
    logger.info(f"Results saved to {filename}")

    # Display summary
    print("\n" + "="*80)
    print(f"POOL CREATION SCAN RESULTS")
    print("="*80)
    print(f"Pool Address: {pool_address}")

    readable_time = datetime.fromtimestamp(open_timestamp).strftime('%Y-%m-%d %H:%M:%S UTC')
    print(f"Open Time: {readable_time} (epoch: {open_timestamp})")
    print(f"Target Slot: {target_slot}")
    print(f"Scan Range: {target_slot - 50} to {target_slot + 50}")
    print(f"Transactions Found: {len(transactions)}")

    if creation_tx:
        creation_slot = creation_tx.get('slot', 'Unknown')
        creation_sig = creation_tx['transaction']['signatures'][0]
        creation_time = creation_tx.get('blockTime')

        print(f"\nCreation Transaction:")
        print(f"  Signature: {creation_sig}")
        print(f"  Slot: {creation_slot}")

        if creation_time:
            readable_creation = datetime.fromtimestamp(creation_time).strftime('%Y-%m-%d %H:%M:%S UTC')
            print(f"  Time: {readable_creation}")

    print("="*80 + "\n")

    return creation_tx

if __name__ == '__main__':
    # Example usage - NOTE: This pool is known to work (has valid openTime)
    test_pool = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"  # SOL/USDC pool
    
    print("⚠️  TESTING NOTE: This example uses a pool known to have valid openTime data.")
    print("   Many other pools may require manual timestamp input.\n")
    
    # Option 1: Use Raydium API to get open time (works only for pools with valid openTime)
    result = find_pool_creation_transaction(test_pool)
    
    # Option 2: Provide open time manually (required for pools with openTime = 0)
    # result = find_pool_creation_transaction(test_pool, open_time_epoch=1234567890)
    
    if result:
        print("SUCCESS: Pool creation transaction found!")
        print(f"Explorer link: https://explorer.solana.com/tx/{result['transaction']['signatures'][0]}")
    else:
        print("FAILED: Could not find pool creation transaction")
        print("For pools with openTime = 0, try providing manual timestamp:")
        print(f"python find_pool_creation.py {test_pool} <epoch_timestamp>")
