import os
import json
import shutil
from pathlib import Path
from time import time

OUTPUT_ROOT = Path(__file__).resolve().parent.parent.parent.parent / "data"

class OutputManager:
    """Centralized output management for all project files."""

    def __init__(self):
        self.output_root = OUTPUT_ROOT
        print(self.output_root)
        wipe = os.environ.get("WIPE_OUTPUT_ON_START", "False").lower() == "true"
        if wipe:
            self.wipe_output()

    def wipe_output(self):
        """Delete all files and folders in the output root directory."""
        if self.output_root.exists():
            for item in self.output_root.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

    def save_output(self, data, subpath, name=None, as_text=False):
        """
        Save data to output_root/subpath/name, auto-generating name if not set.
        If as_text is True or name ends with .txt, saves as plain text, else as JSON.
        Returns the full path to the saved file.
        """
        # Ensure subpath exists
        full_dir = self.output_root / subpath
        full_dir.mkdir(parents=True, exist_ok=True)

        # Determine default name if not provided
        if name is None:
            ts = int(time())
            sig = None
            if isinstance(data, dict):
                if "transaction" in data and "signatures" in data["transaction"]:
                    sig = data["transaction"]["signatures"][0]
                elif "signatures" in data:
                    sig = data["signatures"][0]
                elif "signature" in data:
                    sig = data["signature"]
            if as_text or (isinstance(data, str) and not name):
                name = f"output_{ts}.txt"
            elif sig:
                name = f"{sig}_{ts}.json"
            else:
                name = f"output_{ts}.json"

        # Determine file type
        if as_text or name.endswith('.txt'):
            mode = "w"
            path = full_dir / name
            with open(path, mode) as f:
                f.write(data if isinstance(data, str) else str(data))
            return str(path)
        else:
            if not name.endswith('.json'):
                name += '.json'
            path = full_dir / name
            with open(path, "w") as f:
                json.dump(data, f, indent=4)
            return str(path)

output_manager = OutputManager()

def save_output(data, subpath, name=None, as_text=False):
    """
    Convenience function to save data using the global output_manager.
    """
    return output_manager.save_output(data, subpath, name=name, as_text=as_text)
