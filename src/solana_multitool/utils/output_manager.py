import os
import json
import shutil
from datetime import datetime
from pathlib import Path

# Root output directory - relative to project root
OUTPUT_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "data"

class OutputManager:
    """Centralized output management for all project files."""

    def __init__(self):
        self.output_root = OUTPUT_ROOT
        print(self.output_root)
        wipe = os.environ.get("WIPE_OUTPUT_ON_START", "False").lower() == "true"
        if wipe:
            self.wipe_output()
        self.setup_directories()

    def wipe_output(self):
        """Delete all files and folders in the output root directory."""
        if self.output_root.exists():
            for item in self.output_root.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

    def setup_directories(self):
        """Create all necessary output directories."""
        directories = [
            "transactions/error_txs",
            "transactions/working_txs",
            "pool_scans",
            "swap_data",
            "raw_data",
            "text"
        ]

        for dir_path in directories:
            full_path = self.output_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)

    def get_output_path(self, category, filename=None):
        """
        Get the full path for an output file.

        Args:
            category: Type of output (e.g., 'logs', 'pool_scans', 'transactions/error_txs')
            filename: Optional filename to append

        Returns:
            Path object for the output location
        """
        base_path = self.output_root / category

        if filename:
            return base_path / filename
        return base_path

    def save_json(self, data, category, filename, indent=2):
        """
        Save data as JSON to the appropriate output directory.

        Args:
            data: Data to save
            category: Output category (e.g., 'pool_scans', 'swap_data')
            filename: Filename (will add .json if not present)
            indent: JSON indentation level

        Returns:
            String path to saved file
        """
        if not filename.endswith('.json'):
            filename += '.json'

        filepath = self.get_output_path(category, filename)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=indent)

        return str(filepath)

    def save_transaction_json(self, tx, signature, is_error=False):
        """
        Save transaction data to appropriate directory.

        Args:
            tx: Transaction data
            signature: Transaction signature
            is_error: Whether this is an error transaction

        Returns:
            String path to saved file
        """
        category = "transactions/error_txs" if is_error else "transactions/working_txs"
        filename = f"{signature}.json"

        return self.save_json([tx], category, filename, indent=4)

    def save_pool_creation_scan(self, pool_address, result_data):
        """
        Save pool creation scan results.

        Args:
            pool_address: Pool address being scanned
            result_data: Scan results

        Returns:
            String path to saved file
        """
        filename = f"pool_creation_scan_{pool_address}.json"

        return self.save_json(result_data, "pool_scans", filename)

    def save_swap_data(self, swap_data, identifier=None):
        """
        Save swap analysis data.

        Args:
            swap_data: Swap data to save
            identifier: Optional identifier for the filename

        Returns:
            String path to saved file
        """

        if identifier:
            filename = f"swaps_{identifier}.json"
        else:
            filename = f"swaps.json"

        return self.save_json(swap_data, "swap_data", filename)

    def save_raw_data(self, data, filename):
        """
        Save raw data (blocks, transactions, etc.) for debugging.

        Args:
            data: Raw data to save
            filename: Filename for the data

        Returns:
            String path to saved file
        """
        return self.save_json(data, "raw_data", filename)

    def save_text(self, data, filename):
        """
        Save data as plain text to the 'text' output directory.

        Args:
            data: String or text to save
            filename: Filename (will add .txt if not present)

        Returns:
            String path to saved file
        """
        if not filename.endswith('.txt'):
            filename += '.txt'

        filepath = self.get_output_path("text", filename)

        with open(filepath, 'w') as f:
            f.write(data)

        return str(filepath)

# Global instance for easy access
output_manager = OutputManager()

# Convenience functions for easy importing
def save_error_transaction_json(tx, signature):
    """Save error transaction JSON."""
    return output_manager.save_transaction_json(tx, signature, is_error=True)

def save_text(data, filename):
    """Save data as plain text to the 'text' output directory."""
    return output_manager.save_text(data, filename)

def save_working_transaction_json(tx, signature):
    """Save working transaction JSON."""
    return output_manager.save_transaction_json(tx, signature, is_error=False)

def dump_transactions_to_json(transactions, filename):
    """Dump transactions to JSON file."""
    return output_manager.save_json(transactions, "transactions", filename, indent=4)

def save_swap(swap_data, identifier=None):
    """Convenience function to save swap data."""
    return output_manager.save_swap_data(swap_data, identifier)

def get_output_path(category, filename=None):
    """Get output path for a category and optional filename."""
    return str(output_manager.get_output_path(category, filename))

# Initialize directories on import
output_manager.setup_directories()
