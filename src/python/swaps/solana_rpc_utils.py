# solana-multitool/src/python/swaps/solana_rpc_utils.py

"""
solana_rpc_utils.py

Utility functions for interacting with the Solana RPC API, including
fetching transactions by program ID and handling rate limiting.

This module is intended to be imported as part of the swaps package.
"""

import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..config import get_solana_rpc_url, get_max_requests_per_second
import network_utils as net

# Set up rate limiter using config
rate_limiter = net.RateLimiter(max_requests=get_max_requests_per_second(), time_window=1.0)

def get_solana_transactions_with_program_id(program_id, start_slot, end_slot):
    """
    Generator that yields transactions containing the specified program_id
    from Solana blocks in the given slot range.

    Args:
        program_id (str): The Solana program ID to filter transactions.
        start_slot (int): The starting block slot.
        end_slot (int): The ending block slot (inclusive).

    Yields:
        dict: Transaction objects containing the specified program_id.
    """
    url = get_solana_rpc_url()
    headers = {"Content-Type": "application/json"}

    def fetch_block(slot):
        retries = 0
        max_retries = 7
        while retries < max_retries:
            rate_limiter.acquire()
            logging.info(f"Fetching block {slot}...")
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
            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                if 'result' in data and data['result']:
                    block = data['result']
                    if 'transactions' in block:
                        return [tx for tx in block['transactions']
                                if program_id in tx['transaction']['message']['accountKeys']]
                elif 'result' in data and data['result'] is None:
                    print(f"Block {slot} not found. Skipping.")
                    return []
                else:
                    print(f"Unexpected response for block {slot}: {data}")
                    return []
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    retries += 1
                    net.exponential_backoff_sleep(retries)
                else:
                    logging.error(f"HTTP Error fetching block {slot}: {str(e)}")
                    return []
            except Exception as e:
                logging.error(f"General Error fetching block {slot}: {str(e)}")
                return []
        logging.error(f"Failed to fetch block {slot} after {max_retries} retries.")
        return []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_block, slot): slot for slot in range(start_slot, end_slot + 1)}
        for future in as_completed(futures):
            for tx in future.result():
                yield tx