import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path

# Root output directory - relative to project root
OUTPUT_ROOT = "../../out"

class OutputManager:
    """Centralized output management for all project files."""
    
    def __init__(self):
        self.output_root = Path(__file__).parent / OUTPUT_ROOT
        self.setup_directories()
        
    def setup_directories(self):
        """Create all necessary output directories."""
        directories = [
            "logs",
            "transactions/error_txs", 
            "transactions/working_txs",
            "pool_scans",
            "swap_data",
            "raw_data"
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pool_creation_scan_{pool_address}_{timestamp}.json"
        
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if identifier:
            filename = f"swaps_{identifier}_{timestamp}.json"
        else:
            filename = f"swaps_{timestamp}.json"
            
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
    
    def get_log_file_path(self, log_name="error_log.txt"):
        """
        Get path for log files.
        
        Args:
            log_name: Name of the log file
            
        Returns:
            String path to log file
        """
        return str(self.get_output_path("logs", log_name))
    
    def setup_logging(self, log_level=logging.ERROR, log_name="error_log.txt"):
        """
        Setup logging to output directory.
        
        Args:
            log_level: Logging level
            log_name: Log file name
            
        Returns:
            String path to log file
        """
        log_path = self.get_log_file_path(log_name)
        
        logging.basicConfig(
            filename=log_path,
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filemode='w'
        )
        
        return log_path
    
    def list_files(self, category):
        """
        List all files in a category.
        
        Args:
            category: Category to list
            
        Returns:
            List of file paths
        """
        category_path = self.get_output_path(category)
        return [str(f) for f in category_path.glob("*") if f.is_file()]
    
    def get_latest_file(self, category, pattern="*"):
        """
        Get the most recently modified file in a category.
        
        Args:
            category: Category to search
            pattern: File pattern to match
            
        Returns:
            Path to latest file or None
        """
        category_path = self.get_output_path(category)
        files = list(category_path.glob(pattern))
        
        if not files:
            return None
            
        latest_file = max(files, key=lambda f: f.stat().st_mtime)
        return str(latest_file)
    
    def clean_old_files(self, category, days_old=7):
        """
        Clean up old files in a category.
        
        Args:
            category: Category to clean
            days_old: Remove files older than this many days
            
        Returns:
            Number of files removed
        """
        category_path = self.get_output_path(category)
        current_time = time.time()
        cutoff_time = current_time - (days_old * 24 * 3600)
        
        cleaned_count = 0
        
        for file_path in category_path.glob("*"):
            if file_path.is_file():
                file_time = file_path.stat().st_mtime
                if file_time < cutoff_time:
                    file_path.unlink()
                    cleaned_count += 1
                    
        return cleaned_count

# Global instance for easy access
output_manager = OutputManager()

# Convenience functions for easy importing
def save_error_transaction_json(tx, signature):
    """Save error transaction JSON."""
    return output_manager.save_transaction_json(tx, signature, is_error=True)

def save_working_transaction_json(tx, signature):
    """Save working transaction JSON."""
    return output_manager.save_transaction_json(tx, signature, is_error=False)

def dump_transactions_to_json(transactions, filename):
    """Dump transactions to JSON file."""
    return output_manager.save_json(transactions, "transactions", filename, indent=4)

def get_output_path(category, filename=None):
    """Get output path for a category and optional filename."""
    return str(output_manager.get_output_path(category, filename))

def setup_project_logging(log_level=logging.ERROR, log_name="error_log.txt"):
    """Setup project-wide logging to output directory."""
    return output_manager.setup_logging(log_level, log_name)

# Initialize directories on import
output_manager.setup_directories()