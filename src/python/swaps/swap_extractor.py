"""
swap_extractor.py

Provides functionality to extract swap data from Solana transaction signatures.
Intended for use as part of the swaps package.

Relative imports are used for compatibility with package-based execution.
"""

import logging
import json
import subprocess
from ..output_manager import save_error_transaction_json, save_working_transaction_json

def get_solana_swap_from_transaction_signature(signature, tx):
    """
    Extract swap data from a transaction signature using an external process.
    Saves error transactions and logs appropriately.

    Args:
        signature (str): The transaction signature to process.
        tx (dict): The transaction data.

    Returns:
        dict or None: Parsed swap data if successful, otherwise None.
    """
    logging.info(f"Processing signature: {signature}")
    result = subprocess.run(["./getswaps", signature], capture_output=True, text=True)

    if result.returncode == 0:
        # Uncomment to save working transactions if needed
        # save_working_transaction_json(tx, signature)
        return json.loads(result.stdout.strip())
    elif "status code: 429" in result.stderr:
        logging.error("Rate limit hit (429)")
        # TODO: Implement backoff and retry if needed
    else:
        logging.error(f"Error fetching swaps for signature {signature}: {result.stderr}")
        # Save error transaction to centralized output
        save_error_transaction_json(tx, signature)

    return None
