#!/usr/bin/env python3
"""
Simple CLI tool to find Raydium pool creation transactions.

⚠️  LIMITATIONS:
- Only works for Raydium pools that have valid 'openTime' data in their API response
- Many older pools have openTime = 0 or missing openTime field
- Newer pools (created after ~2023) are more likely to work
- If openTime is missing/invalid, you must provide manual epoch timestamp

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
from pool_creation_scanner import find_pool_creation_transaction

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    pool_address = sys.argv[1]
    open_time_epoch = None

    if len(sys.argv) >= 3:
        try:
            open_time_epoch = int(sys.argv[2])
        except ValueError:
            print("Error: open_time_epoch must be a valid integer (Unix timestamp)")
            return

    print(f"Searching for pool creation transaction...")
    print(f"Pool: {pool_address}")

    if open_time_epoch:
        from datetime import datetime
        readable_time = datetime.fromtimestamp(open_time_epoch).strftime('%Y-%m-%d %H:%M:%S UTC')
        print(f"Open time: {readable_time} (epoch: {open_time_epoch})")
    else:
        print("Open time: Will fetch from Raydium API")

    print("Scanning ±50 blocks around open time...\n")

    result = find_pool_creation_transaction(pool_address, open_time_epoch)

    if result:
        signature = result['transaction']['signatures'][0]
        print(f"\n🎉 SUCCESS!")
        print(f"Creation transaction: {signature}")
        print(f"View on explorer: https://explorer.solana.com/tx/{signature}")
    else:
        print(f"\n❌ FAILED: Could not find pool creation transaction")
        print(f"\n💡 Troubleshooting:")
        print(f"   - Pool may have openTime = 0 (try manual timestamp)")
        print(f"   - Pool may be too old (pre-2023 pools often lack openTime)")
        print(f"   - Check pool address on explorer.solana.com for anchor data")
        print(f"   - Use manual epoch timestamp if available")

if __name__ == '__main__':
    main()
