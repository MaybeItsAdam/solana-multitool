"""
swap_coindesk.py

Combines formatting utilities and orchestration logic for Solana swap and transaction data,
including Coindesk formatting and batch extraction.

This module provides:
- Functions to format swaps found within transactions for Coindesk ingestion.
- Orchestration to fetch, extract, and format swaps for a given instrument and block interval.

Relative imports are used for compatibility with Python package structure.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from solana_multitool.auto_config.environment import get_provider_key
from solana_multitool.utils.solana_rpc import get_solana_transactions_with_program_id
from solana_multitool.swaps.swap_extractor import get_swap_from_tx_signature
from solana_multitool.utils.output_manager import output_manager

def address_to_TLA(address: str) -> str:
    """
    Placeholder for address-to-TLA (Three Letter Acronym) mapping.
    """
    return address

def format_goswap_and_tx_to_coindesk(swap: dict, tx: dict) -> dict:
    """
    Formats swap and transaction data into the structure expected by Coindesk.

    Args:
        swap (dict): The swap data extracted from the transaction.
        tx (dict): The original transaction data.

    Returns:
        dict: A dictionary formatted for Coindesk ingestion.
    """
    formatted = {
        "TYPE": None,
        "MARKET": None,
        "CHAIN_ASSET": None,
        "INSTRUMENT": swap["transaction_data"][1]["Data"]["info"]["authority"],
        "MAPPED_INSTRUMENT": swap["transaction_data"][1]["Data"]["info"]["authority"],
        "BASE": address_to_TLA(swap["swap_data"]["TokenInMint"]),
        "QUOTE": address_to_TLA(swap["swap_data"]["TokenOutMint"]),
        "SIDE": None,  # BUY OR SELL
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
        "BLOCK_NUMBER": None,
        "FROM": swap["transaction_data"][0]["Data"]["info"]["authority"],
        "MARKET_FEE_PERCENTAGE": None,
        "MARKET_FEE_VALUE": str(tx["meta"]["fee"]),
        "PROVIDER_KEY": get_provider_key(),
        "SIGNATURE_TEMP": tx['transaction']['signatures'][0]
    }
    return formatted

def get_coindesk_formatted_swaps_in_interval_given_instrument(instrument: str, start_block: int, end_block: int):
    """
    Orchestrates fetching, extracting, and formatting swaps for a given instrument and block interval.
    Returns a list of formatted swap data, including error indicators for failed transactions.
    """
    results_with_order = {}
    futures_map = {}

    with ThreadPoolExecutor(max_workers=4) as executor:
        for idx, tx in enumerate(get_solana_transactions_with_program_id(instrument, start_block, end_block)):
            status = tx['meta']['status']
            signature = tx['transaction']['signatures'][0]

            if status is not None and "Err" in status:
                results_with_order[idx] = {
                    "signature": signature,
                    "status": status
                }
            elif (tx["meta"]["innerInstructions"] is None or len(tx["meta"]["innerInstructions"]) == 0):
                results_with_order[idx] = {
                    "signature": signature,
                    "status": "no inner instructions"
                }
            else:
                future = executor.submit(get_swap_from_tx_signature, signature) # THIS WONT SAVE
                futures_map[future] = (idx, tx)

        for future in as_completed(futures_map):
            original_idx, original_tx = futures_map[future]
            try:
                swap_data = future.result()
                if swap_data is None:
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
    # Example usage: replace with actual instrument and block range as needed
    instrument = "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv"
    start_block = 324551590
    end_block = 324554980

    swaps = get_coindesk_formatted_swaps_in_interval_given_instrument(instrument, start_block, end_block)

    # Save swap data to centralized output
    if swaps:
        output_file = output_manager.save_swap_data(swaps, "interval_swaps")
        print(f"Swap data saved to: {output_file}")
