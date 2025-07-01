"""
solana_rpc_utils.py

General utility functions for interacting with the Solana RPC API, including
making RPC requests with rate limiting and fetching transactions by program ID.

This module is intended to be imported wherever Solana RPC utilities are needed.
"""

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..auto_config.environment import get_solana_rpc_url, get_max_requests_per_second
from solana_multitool.utils import rate_limiter as net
from solana_multitool.auto_config.logging_config import logger

rate_limiter = net.RateLimiter(max_requests=get_max_requests_per_second(), time_window=1.0)

def make_rpc_request(payload, max_retries=3):
    """
    Make a Solana RPC request with rate limiting and retries.

    Args:
        payload (dict): The JSON-RPC payload to send.
        max_retries (int): Number of retry attempts.

    Returns:
        dict or None: The parsed JSON response, or None on failure.
    """

    rpc_url = get_solana_rpc_url()

    for attempt in range(max_retries):
        try:
            rate_limiter.acquire()
            response = requests.post(rpc_url, json=payload, timeout=30)

            if response.status_code == 429:
                if logger:
                    logger.warning(f"Rate limited on attempt {attempt + 1}")
                net.exponential_backoff_sleep(attempt)
                continue

            response.raise_for_status()
            data = response.json()

            if 'error' in data:
                if logger:
                    logger.error(f"RPC Error: {data['error']}")
                return None

            return data

        except Exception as e:
            if logger:
                logger.error(f"Request failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                net.exponential_backoff_sleep(attempt)

    return None

def get_block(slot, max_retries=7):
    """
    Fetch a block from Solana RPC by slot.
    Returns the block data dict or None.
    """

    rpc_url = get_solana_rpc_url()
    for attempt in range(max_retries):
        rate_limiter.acquire()
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
            response = requests.post(rpc_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            if 'result' in data and data['result']:
                return data['result']
            elif 'result' in data and data['result'] is None:
                if logger:
                    logger.info(f"Block {slot} not found. Skipping.")
                return None
            else:
                if logger:
                    logger.warning(f"Unexpected response for block {slot}: {data}")
                return None
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                net.exponential_backoff_sleep(attempt)
            else:
                if logger:
                    logger.error(f"HTTP Error fetching block {slot}: {str(e)}")
                return None
        except Exception as e:
            if logger:
                logger.error(f"General Error fetching block {slot}: {str(e)}")
            return None
    if logger:
        logger.error(f"Failed to fetch block {slot} after {max_retries} retries.")
    return None

def scan_blocks_for_transactions(start_slot, end_slot, tx_filter=lambda tx: True, max_workers=4):
    """
    Scan blocks in the given slot interval and yield working transactions matching tx_filter.
    Only transactions with meta.err == None are yielded.
    """
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(get_block, slot): slot for slot in range(start_slot, end_slot + 1)}
        for future in as_completed(futures):
            block = future.result()
            if block and 'transactions' in block:
                for tx in block['transactions']:
                    # Only yield transactions with no error (working transactions)
                    if tx.get('meta') and tx['meta'].get('err') is None and tx_filter(tx):
                        yield tx

def get_solana_transactions_with_program_id_in_interval(program_id, start_slot, end_slot):
    def program_id_filter(tx):
        return program_id in tx['transaction']['message']['accountKeys']
    yield from scan_blocks_for_transactions(
        start_slot, end_slot, tx_filter=program_id_filter
    )

def get_transaction_by_signature(signature):
    """
    Args:
        signature (str): The transaction signature.

    Returns:
        dict or None: The transaction data, or None if not found.
    """

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
    }
    return make_rpc_request(payload)
