from pathlib import Path
from solana_multitool.auto_config.logging_config import logger
import json
import subprocess

def get_swap_from_tx_signature(signature):
    logger.info(f"Getting formatted swap for signature {signature}")

    """
    Extract swap data from a tx signature using an external process.
    Optionally logs error and/or working txs using the tx data fetched by signature.

    Args:
        signature (str): The tx signature to process.
        log_error (bool): Whether to log error txs.

    Returns:
        dict or None: Parsed swap data if successful, otherwise None.
    """

    current_script_path = Path(__file__).resolve()
    project_root = current_script_path.parents[3]
    getswaps_executable = project_root / "bin" / "getswaps"

    try:
        result = subprocess.run(
            [str(getswaps_executable), signature],
            capture_output=True,
            text=True,
            check=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        if "status code: 429" in e.stderr:
            logger.error("Rate limit hit (429)")
            # TODO: Implement backoff and retry if needed
        else:
            logger.error(f"Error fetching swaps for signature {signature}: {e.stderr}")
    except Exception as e:
        logger.error(f"Unexpected error for signature {signature}: {str(e)}")

    return None
