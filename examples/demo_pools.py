from solana_multitool.constants import *
from solana_multitool.pools.find_raydium_pool_creation_tx import find_raydium_pool_creation_tx
from solana_multitool.pools.scan_for_log import scan_for_log_in_dex_in_interval
from solana_multitool.auto_config.environment import *
from solana_multitool.constants import *
from solana_multitool.utils.output_manager import save_output
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

def demo_find_raydium_pool_creation():
    """
    Find a pool creation tx for a pool present on Raydium's swagger API
    https://api-v3.raydium.io/docs/#/
    """
    for i, candidate in enumerate(find_raydium_pool_creation_tx(USDC_SOL_PROGRAM_ID)):
        save_output(candidate, "pools/USDC_SOL_tx_creation_candidates", f"{i}.json")

def demo_scan_for_log():
    for tx in scan_for_log_in_dex_in_interval(RAYDIUM_CLMM_PROGRAM_ID,RAYDIUM_CLMM_INIT_LOG , TEST_START_SLOT, TEST_END_SLOT):
        signature = tx["transaction"]["signatures"][0]
        save_output(tx, "pools/txs_with_logs", f"{signature}.json")


if __name__ == "__main__":
    logger.info("Demonstrating pool capabilities")
    with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
        ) as progress:
        task_id = progress.add_task(description="[blue]Running Pool examples...", total=None)
        demo_find_raydium_pool_creation()
        demo_scan_for_log()
