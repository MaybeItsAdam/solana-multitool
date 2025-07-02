from concurrent.futures import ThreadPoolExecutor, as_completed
from solana_multitool.auto_config.environment import get_provider_key
from solana_multitool.utils.solana_rpc import get_solana_txs_with_program_id_in_interval
from solana_multitool.swaps.swap_extractor import get_swap_from_tx_signature
from solana_multitool.auto_config.logging_config import logger

def address_to_TLA(address: str) -> str:
    """
    Placeholder for address to TLA mapping.
    """
    return address

def format_goswap_and_tx_to_coindesk(swap: dict, tx: dict) -> dict:
    """
    Formats swap and tx data into the structure expected by Coindesk.

    Args:
        swap (dict): The swap data extracted from the tx.
        tx (dict): The original tx data.

    Returns:
        dict: A dictionary formatted for Coindesk ingestion.
    """
    formatted = {
        "TYPE": None,
        "MARKET": None,
        "CHAIN_ASSET": None,
        "INSTRUMENT": swap["tx_data"][1]["Data"]["info"]["authority"],
        "MAPPED_INSTRUMENT": swap["tx_data"][1]["Data"]["info"]["authority"],
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
        "tx_HASH": None,
        "BLOCK_NUMBER": None,
        "FROM": swap["tx_data"][0]["Data"]["info"]["authority"],
        "MARKET_FEE_PERCENTAGE": None,
        "MARKET_FEE_VALUE": str(tx["meta"]["fee"]),
        "PROVIDER_KEY": get_provider_key(),
        "SIGNATURE_TEMP": tx['tx']['signatures'][0]
    }
    return formatted

# could rewrite this to pass functions into the functions to perform actions
# as opposed to wasting time collecting then iterating again
def get_coindesk_formatted_swaps_in_interval_given_instrument(
    instrument: str,
    start_block: int,
    end_block: int
):
    logger.info(f"Streaming and processing swaps in interval {start_block} - {end_block}")
    results_with_order = {}
    futures_map = {}


    with ThreadPoolExecutor(max_workers=4) as executor:
        tx_generator = get_solana_txs_with_program_id_in_interval(instrument, start_block, end_block)

        # --- Submit tasks from the generator ---
        for idx, tx in enumerate(tx_generator):

            status = tx['meta']['status']
            signature = tx['tx']['signatures'][0]

            if status is not None and "Err" in status:
                results_with_order[idx] = {"signature": signature, "status": status}
            elif not tx["meta"].get("innerInstructions"):
                results_with_order[idx] = {"signature": signature, "status": "no inner instructions"}
            else:
                future = executor.submit(get_swap_from_tx_signature, signature)
                futures_map[future] = (idx, tx)

        for future in as_completed(futures_map):

            original_idx, original_tx = futures_map[future]
            try:
                swap_data = future.result()
                if swap_data is not None:
                    coindesk_swap = format_goswap_and_tx_to_coindesk(swap_data, original_tx)
                    results_with_order[original_idx] = coindesk_swap
            except Exception as e:
                logger.error(f"Error processing swap for signature {original_tx['tx']['signatures'][0]}: {e}")
                results_with_order[original_idx] = {
                    "signature": original_tx['tx']['signatures'][0],
                    "status": f"Processing Error: {str(e)}"
                }


    formatted_swaps = [results_with_order[idx] for idx in sorted(results_with_order.keys())]
    return formatted_swaps
