import datetime
import json
from pathlib import Path

import pandas as pd


class Logger:
    """Logger for tracking scrape operations and timestamps."""

    def __init__(self):
        """Initialize logger with paths to log and last scrapes files."""
        base_dir = Path(__file__).resolve().parent
        runtime_dir = base_dir.parent / "runtime"
        self.log_path = runtime_dir / "log.txt"
        self.last_scrapes_path = runtime_dir / "last_scrapes.json"

    def _write_line(self, line: str) -> None:
        """Write a line to the log file."""
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")

    def update_last_scrapes(self, name: str, timestamp: str) -> None:
        """Update the last scrape timestamp for a given name."""
        with self.last_scrapes_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        data[name] = timestamp

        with self.last_scrapes_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

    def log(self, dataframe: pd.DataFrame, name: str) -> None:
        """Log the number of rows scraped for a given data source."""
        row_count = len(dataframe)
        current_time = datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S")
        line = f"{current_time}: scraped {row_count} {name}"

        self._write_line(line)
        self.update_last_scrapes(name, current_time)


if __name__ == "__main__":
    logger = Logger()
    logger.log(pd.DataFrame(), "manual_run")