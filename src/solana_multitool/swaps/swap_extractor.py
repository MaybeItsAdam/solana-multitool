"""
swap_extractor.py

Provides functionality to extract swap data from Solana transaction signatures.
Intended for use as part of the swaps package.

"""
from pathlib import Path
from ..auto_config.logging import logging_config
import json
import subprocess
from solana_multitool.utils.output_manager import save_swap, save_text

logger = logging_config.get_logger(__name__)

def get_swap_from_tx_signature(signature, log_error=False):
    """
    Extract swap data from a transaction signature using an external process.
    Optionally logs error and/or working transactions using the transaction data fetched by signature.

    Args:
        signature (str): The transaction signature to process.
        log_error (bool): Whether to log error transactions.
        log_working (bool): Whether to log working transactions.

    Returns:
        dict or None: Parsed swap data if successful, otherwise None.
    """

    current_script_path = Path(__file__).resolve()
    project_root = current_script_path.parents[3]
    getswaps_executable = project_root / "bin" / "getswaps"


    logger.info(f"Processing signature: {signature}")
    result = subprocess.run(
            [str(getswaps_executable), signature],
            capture_output=True,
            text=True,
            check=True
    )

    if result.returncode == 0:
        return json.loads(result.stdout.strip())
    elif "status code: 429" in result.stderr:
        logger.error("Rate limit hit (429)")
        # TODO: Implement backoff and retry if needed
    else:
        logger.error(f"Error fetching swaps for signature {signature}: {result.stderr}")

    return result
