import shutil
import os
import time

def clean_old_temp_dirs(base_path="/tmp", prefix="chrome-profile-", max_age_seconds=36000):
    """
    Delete temp directories older than max_age_seconds with a certain prefix.

    Args:
        base_path (str): Directory where temp folders live.
        prefix (str): Prefix of temp folders to clean.
        max_age_seconds (int): Age threshold to delete folders.
    """
    now = time.time()
    for item in os.listdir(base_path):
        path = os.path.join(base_path, item)
        if os.path.isdir(path) and item.startswith(prefix):
            age = now - os.path.getmtime(path)
            if age > max_age_seconds:
                try:
                    shutil.rmtree(path)
                    print(f"Deleted old temp dir: {path}")
                except Exception as e:
                    print(f"Failed to delete {path}: {e}")

# Example usage:
clean_old_temp_dirs("/tmp", "chrome-profile-", 36000)  # cleans folders older than 10 hours
