import logging
import requests
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
import network_utils as net
from output_manager import output_manager, save_error_transaction_json, save_working_transaction_json
from config import get_solana_rpc_url, get_max_requests_per_second, get_provider_key

# Setup logging using centralized output manager
log_path = output_manager.setup_logging(logging.ERROR, "solana_swaps_error.log")

# Get rate limiting from config
rate_limiter = net.RateLimiter(max_requests=get_max_requests_per_second(), time_window=1.0)

def get_solana_transactions_with_program_id(program_id, start_slot, end_slot):
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
                    return [] # Return empty list if block not found
                else:
                    print(f"Unexpected response for block {slot}: {data}")
                    return [] # Return empty list for unexpected response
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    retries += 1
                    net.exponential_backoff_sleep(retries)
                else:
                    logging.error(f"HTTP Error fetching block {slot}: {str(e)}")
                    return [] # Return empty list for other HTTP errors
            except Exception as e:
                logging.error(f"General Error fetching block {slot}: {str(e)}")
                return [] # Return empty list for general errors
        logging.error(f"Failed to fetch block {slot} after {max_retries} retries.")
        return []

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_block, slot): slot for slot in range(start_slot, end_slot + 1)}
        for future in as_completed(futures):
            for tx in future.result():
                yield tx


def get_solana_swap_from_transaction_signature(signature, tx):
    logging.info(f"Processing signature: {signature}")
    result = subprocess.run(["./getswaps", signature], capture_output=True, text=True)

    if result.returncode == 0:
        # Uncomment to save working transactions
        # save_working_transaction_json(tx, signature)
        return json.loads(result.stdout.strip())
    elif "status code: 429" in result.stderr:
        logging.error("Rate limit hit (429)")
        # TODO: Implement backoff and retry
    else:
        logging.error(f"Error fetching swaps for signature {signature}: {result.stderr}")
        # Save error transaction to centralized output
        save_error_transaction_json(tx, signature)
    
    return None

def address_to_TLA(address):
    TLA = address

    return TLA

def format_goswap_and_tx_to_coindesk(swap, tx):
    formatted = {
        "TYPE": None,
        "MARKET": None,
        "CHAIN_ASSET": None,
        "INSTRUMENT": swap["transaction_data"][1]["Data"]["info"]["authority"],
        "MAPPED_INSTRUMENT": swap["transaction_data"][1]["Data"]["info"]["authority"],
        "BASE": address_to_TLA(swap["swap_data"]["TokenInMint"]),
        "QUOTE": address_to_TLA(swap["swap_data"]["TokenOutMint"]),
        "SIDE": None, # BUY OR SELL
        "ID": None,
        "TIMESTAMP": None,
        "TIMESTAMP_NS": None,
        "RECEIVED_TIMESTAMP": None,
        "RECEIVED_TIMESTAMP_NS": None,
        "QUANTITY": None,
        "PRICE": None,
        "QUOTE_QUANTITY": None,
        "SOURCE": None,
        "CCSEQ": None,
        "TRANSACTION_HASH": None,
        "BLOCK_NUMBER": None, # FIND A WAY TO KEEP THE INFO TOGETHER - WRAP IT AROUND
        "FROM": swap["transaction_data"][0]["Data"]["info"]["authority"],
        "MARKET_FEE_PERCENTAGE": None,
        "MARKET_FEE_VALUE": str(tx["meta"]["fee"]),
        "PROVIDER_KEY": get_provider_key(),
        "SIGNATURE_TEMP" : tx['transaction']['signatures'][0]
    }

    return formatted

def get_coindesk_formatted_swaps_in_interval_given_instrument(instrument, start_block, end_block):
    # This list will store final formatted swaps, including error indicators for failed transactions
    results_with_order = {}
    futures_map = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        for idx, tx in enumerate(get_solana_transactions_with_program_id(instrument, start_block, end_block)):
            status = tx['meta']['status']
            signature = tx['transaction']['signatures'][0]

            if status is not None and "Err" in status:
                results_with_order[idx] = {
                    "signature" : signature,
                    "status" : status
                }
            elif (tx["meta"]["innerInstructions"] is None or len(tx["meta"]["innerInstructions"]) == 0):
                results_with_order[idx] = {
                    "signature" : signature,
                    "status" : "no inner instructions"
                }
            else:
                future = executor.submit(get_solana_swap_from_transaction_signature, signature, tx)
                futures_map[future] = (idx, tx)


        for future in as_completed(futures_map):
            original_idx, original_tx = futures_map[future]
            try:
                swap_data = future.result()
                if swap_data == None:
                    continue
                coindesk_swap = format_goswap_and_tx_to_coindesk(swap_data, original_tx)
                results_with_order[original_idx] = coindesk_swap
            except Exception as e:
                print(f"Error processing swap for signature {original_tx['transaction']['signatures'][0]}: {str(e)}")
                results_with_order[original_idx] = {
                    "signature": original_tx['transaction']['signatures'][0],
                    "status": "Processing Error: " + str(e)
                }

    formatted_swaps = [results_with_order[idx] for idx in sorted(results_with_order.keys())]
    return formatted_swaps

if __name__ == '__main__':
    swaps = get_coindesk_formatted_swaps_in_interval_given_instrument("3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv", 324551590, 324554980)
    
    # Save swap data to centralized output
    if swaps:
        output_file = output_manager.save_swap_data(swaps, "interval_swaps")
        print(f"Swap data saved to: {output_file}")
