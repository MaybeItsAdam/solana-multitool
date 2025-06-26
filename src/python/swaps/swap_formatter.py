# swap_formatter.py
"""Formatting utilities for Solana swap and transaction data.

This module provides functions to format swap and transaction data
for downstream consumers (e.g., Coindesk format).

Relative imports are used for compatibility with Python package structure.
"""

from ..config import get_provider_key

def address_to_TLA(address: str) -> str:
    """
    Placeholder for address to TLA (Three-Letter Acronym) mapping.
    Currently returns the address as-is.
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