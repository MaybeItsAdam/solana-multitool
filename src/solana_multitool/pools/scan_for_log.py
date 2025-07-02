"""
pool_log_scanner.py

Scan the tx history of a DEX program for a specific log message

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
        print("Found pool initialization tx:", result)
    else:
        print("No pool initialization found in the given range.")
"""

from solana_multitool.utils.output_manager import save_working_tx_json
from solana_multitool.auto_config.logging_config import logger
from solana_multitool.utils.solana_rpc import scan_blocks_for_txs

def compose_filters(*filters):
    """
    Compose multiple lambda filters into a single filter that returns True only if all filters return True.
    """
    def composite(tx):
        return all(f(tx) for f in filters)
    return composite

def log_message_filter(log_message_substring):
    """
    Returns a lambda that checks if a tx contains the given log message substring.
    """
    return lambda tx: any(
        log_message_substring in log
        for log in tx.get("meta", {}).get("logMessages", [])
    )

def dex_membership_filter(dex_program_id):
    """
    Returns a lambda that checks if a tx involves the given DEX program ID.
    """
    return lambda tx: any(
        acc.get("pubkey") == dex_program_id
        for acc in tx["tx"]["message"]["accountKeys"]
    )

def scan_for_log_in_interval(log_message_substring, start_slot, end_slot, max_workers=4):
    """
    Scan blocks in the given slot interval for txs containing a specific log message substring.
    Returns a list of matching txs.
    """
    log_filter = log_message_filter(log_message_substring)
    return list(scan_blocks_for_txs(
        start_slot, end_slot, tx_filter=log_filter, max_workers=max_workers
    ))

def scan_for_log_in_dex_in_interval(dex_program_id, log_message_substring, start_slot, end_slot, max_workers=4):
    """
    Scan blocks in the given slot interval for txs that both:
    - Involve the given DEX program ID
    - Contain the specified log message substring
    Returns a list of matching txs.
    """
    log_filter = log_message_filter(log_message_substring)
    dex_filter = dex_membership_filter(dex_program_id)
    composite_filter = compose_filters(dex_filter, log_filter)
    return list(scan_blocks_for_txs(
        start_slot, end_slot, tx_filter=composite_filter, max_workers=max_workers
    ))

def is_log_in_tx(tx, log_message_substring, dex_program_id=None):
    """
    Check if a tx contains a log message substring.
    Optionally restrict to txs involving a specific program ID.
    """
    if dex_program_id and dex_program_id not in tx["tx"]["message"]["accountKeys"]:
        return False
    meta = tx.get("meta", {})
    log_messages = meta.get("logMessages", [])
    for log in log_messages:
        if log_message_substring in log:
            return True
    return False
