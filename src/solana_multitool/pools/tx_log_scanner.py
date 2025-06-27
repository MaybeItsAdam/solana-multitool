"""
pool_log_scanner.py

Scan the transaction history of a DEX program for a specific log message

Usage:
    from pool_log_scanner import scan_dex_for_pool_initialization_log

    result = scan_dex_for_pool_initialization_log(
        dex_program_id="DEX_PROGRAM_ID_HERE",
        log_message_substring="Pool initialized",
        start_slot=START_SLOT,
        end_slot=END_SLOT,
        logger=your_logger_instance  # optional
    )
    if result:
        print("Found pool initialization transaction:", result)
    else:
        print("No pool initialization found in the given range.")
"""

from solana_multitool.auto_config.logging import logging_config
from concurrent.futures import ThreadPoolExecutor, as_completed
from solana_multitool.utils.solana_rpc import make_rpc_request
from solana_multitool.auto_config.environment import get_solana_rpc_url
from solana_multitool.utils.output_manager import save_working_transaction_json

logger = logging_config.get_logger(__name__)

def scan_dex_for_pool_initialization_log(
    dex_program_id,
    log_message_substring,
    start_slot,
    end_slot,
    log=True
):
    """
    Scan the transaction history of a DEX program for a specific log message
    that denotes the initialization of a new pool.

    Args:
        dex_program_id (str): The program ID of the DEX to scan.
        log_message_substring (str): The substring to search for in transaction logs.
        start_slot (int): The starting block slot.
        end_slot (int): The ending block slot (inclusive).
        logger (logging.Logger, optional): Logger for progress and results.

    Returns:
        dict or None: The first transaction dict containing the log message, or None if not found.
    """
    url = get_solana_rpc_url()
    headers = {"Content-Type": "application/json"}

    total_slots = end_slot - start_slot + 1
    processed_slots = 0
    failed_slots = 0

    logger = logging_config.get_logger(__name__)

    if logger:
        logger.info(f"Starting scan for DEX program {dex_program_id}")
        logger.info(f"Looking for log substring: '{log_message_substring}'")
        logger.info(f"Scanning {total_slots} slots from {start_slot} to {end_slot}")
        logger.info(f"Using RPC URL: {url}")

    # TODO refactor this so that it uses the utils

    def fetch_block_logs(slot):
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
        data = make_rpc_request(payload)
        if not data or "result" not in data or not data["result"]:
            if logger:
                logger.debug(f"No data returned for slot {slot}")
            return []
        block = data["result"]
        found = []
        tx_count = 0
        relevant_tx_count = 0

        if "transactions" in block:
            tx_count = len(block["transactions"])
            if logger:
                logger.debug(f"Slot {slot}: Processing {tx_count} transactions")
            for tx in block["transactions"]:
                # Only consider transactions involving the DEX program
                if dex_program_id not in tx["transaction"]["message"]["accountKeys"]:
                    continue
                relevant_tx_count += 1
                meta = tx.get("meta", {})
                log_messages = meta.get("logMessages", [])
                for log in log_messages:
                    if log_message_substring in log:
                        found.append(tx)
                        # Save to working_txs using output_manager
                        signature = tx["transaction"]["signatures"][0]
                        save_working_transaction_json(tx, signature)
                        if logger:
                            logger.info(f"Found matching log in slot {slot}, tx signature: {signature} (saved to working_txs)")
                        break

        if logger and relevant_tx_count > 0:
            logger.debug(f"Slot {slot}: {relevant_tx_count}/{tx_count} transactions involved DEX program")
        elif logger and tx_count > 0:
            logger.debug(f"Slot {slot}: No transactions involved DEX program (out of {tx_count} total)")
        elif logger:
            logger.debug(f"Slot {slot}: No transactions in block")
        return found

    found_transactions = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(fetch_block_logs, slot): slot for slot in range(start_slot, end_slot + 1)}
        for future in as_completed(futures):
            slot = futures[future]
            try:
                txs = future.result()
                processed_slots += 1

                if txs:
                    found_transactions.extend(txs)

                # Log progress every 100 slots or at completion
                if logger and (processed_slots % 100 == 0 or processed_slots == total_slots):
                    progress = (processed_slots / total_slots) * 100
                    logger.info(f"Progress: {processed_slots}/{total_slots} slots processed ({progress:.1f}%)")
                    if failed_slots > 0:
                        logger.warning(f"Failed to process {failed_slots} slots so far")

            except Exception as e:
                failed_slots += 1
                if logger:
                    logger.error(f"Error scanning slot {slot}: {e}")

    # Final summary
    if logger:
        logger.info(f"Scan completed: {processed_slots}/{total_slots} slots processed")
        if failed_slots > 0:
            logger.warning(f"Failed to process {failed_slots} slots")
        logger.info(f"Total transactions found with matching logs: {len(found_transactions)}")


    if found_transactions:
        if logger:
            logger.info(f"Returning first matching transaction from slot {found_transactions[0].get('slot', 'unknown')}")

        return found_transactions[0]  # Return the first found
    else:
        if logger:
            logger.info("No pool initialization log found in the given slot range.")

        return None
