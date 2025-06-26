"""Orchestrates fetching, extracting, and formatting Solana swaps.

This module is intended to be run as a script or imported as a library.
Relative imports are used for compatibility with Python package structure.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .solana_rpc_utils import get_solana_transactions_with_program_id
from .swap_extractor import get_solana_swap_from_transaction_signature
from .swap_formatter import format_goswap_and_tx_to_coindesk
from ..output_manager import output_manager

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
                future = executor.submit(get_solana_swap_from_transaction_signature, signature, tx)
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