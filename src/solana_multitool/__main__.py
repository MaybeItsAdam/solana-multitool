from solana_multitool.pools.tx_log_scanner import scan_dex_for_pool_initialization_log
from solana_multitool.constants import *
from solana_multitool.auto_config.logging_config import logger
from solana_multitool.swaps.swap_extractor import get_swap_from_tx_signature
from solana_multitool.utils.solana_rpc import get_solana_transactions_with_program_id_in_interval
from solana_multitool.utils.output_manager import save_swap

# TODO: make this a cli interactive space

def find_pool_creation_demo():
    """Main function to scan for Raydium CLMM pool initialization logs."""

    logger.info(f"Scanning slots {TEST_START_SLOT} to {TEST_END_SLOT} for Raydium CLMM pool initialization logs...")

    result = scan_dex_for_pool_initialization_log(
        dex_program_id=RAYDIUM_CLMM_PROGRAM_ID,
        log_message_substring=RAYDIUM_CLMM_INIT_LOG,
        start_slot=TEST_START_SLOT,
        end_slot=TEST_END_SLOT,
        log=True
    )
    if result:
        logger.info("Found pool initialization transaction:")
        logger.info(result)
    else:
        logger.info("No pool initialization found in the given range.")



def parse_swaps_by_id_demo(program_id, start_slot, end_slot):
    """
    Demo function to extract all transactions with a specified program id and parse them as swaps.
    """
    logger.info(f"Extracting transactions with program id {program_id} from slots {start_slot} to {end_slot}...")

    tx_count = 0
    swap_count = 0

    for tx in get_solana_transactions_with_program_id_in_interval(program_id, start_slot, end_slot):
        tx_count += 1
        signature = tx["transaction"]["signatures"][0]
        swap_data = get_swap_from_tx_signature(signature, log_error=False)
        if swap_data:
            swap_count += 1
            logger.info(f"Swap found for signature {signature}")
            save_swap(swap_data, signature)
        else:
            logger.debug(f"No swap found for signature {signature}")

    logger.info(f"Processed {tx_count} transactions, found {swap_count} swaps.")

if __name__ == "__main__":

    # find_pool_creation_demo()
    parse_swaps_by_id_demo(USDC_SOL_PROGRAM_ID, TEST_START_SLOT, TEST_END_SLOT)
