'''
demonstrate the swaps directory which currently features the following 2 files

swap_extractor
    - contains only get_swap_from_tx_signature(signature)
    - gets the go binary executable wraps its usage
    - returns the swap data in json format
    - unless an error occured, it then returns none

swap_coindesk - incomplete
    - address_to_TLA - placeholder to convert address to a TLA
    - format_goswap_and_tx_to_coindesk - takes a swap formatted as such from the go subroutine and the tx info to form coindesk-style formatted data
    - get_coindesk_formatted_swaps_in_interval_given_instrument -
    - fill this in

TODO
    - port usage of swap_extractor more of this project to go because in usage cases:
        - the tx is fetched, the signature is extracted
        - then the tx is fetched again
    - any function that goes over an interval should dump swaps as found, so swap_coindesk should be redone

'''

from solana_multitool.swaps.swap_coindesk import *
from solana_multitool.swaps.swap_extractor import *
from solana_multitool.utils.output_manager import save_swap
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from solana_multitool.auto_config.logging_config import logger

def demo_coindesk():
    instrument = "3ucNos4NbumPLZNWztqGHNFFgkHeRMBQAVemeeomsUxv" # USDC-SOL pool on Raydium
    start_block = 324551590
    end_block = 324551980

    swaps = get_coindesk_formatted_swaps_in_interval_given_instrument(instrument, start_block, end_block)

    if swaps:
        output_file = save_swap(swaps, "test_coindesk_formatted_swaps_interval")
        print(f"Swap data saved to: {output_file}")

def demo_extractor():
    signature = "4P6jLPkh8Gm48excTDmnBAhvtbV6WqYwrucc4LYHwBTzoFkGAhsTdxTxvLfrJqnvWRBZ3FELuZPRWhBMHqBq7pnA"
    swap = get_swap_from_tx_signature(signature)
    save_swap(swap, "test_extracted_swap")


if __name__ == "__main__":
    logger.info("Demonstrating swap capabilities")
    with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
        ) as progress:
        task_id = progress.add_task(description="[blue]Running Swap tests...", total=None)
        demo_coindesk();
        demo_extractor();
