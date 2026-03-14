import datetime
import pandas as pd
import json
from pathlib import Path

class Logger:

    def __init__(self):
        base_dir = Path(__file__).resolve().parent
        self.log_path = base_dir / "log.txt"
        self.last_scrapes_path = base_dir / "last_scrapes.json"

    def _write_line(self, line: str):

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def update_last_scrapes(self, name, time):

        with self.last_scrapes_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        data[name] = time

        with self.last_scrapes_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def log(self, df, name):

        n = len(df)
        date = datetime.datetime.now().strftime("%d.%m.%y %H:%M:%S")

        line = f"{date}: scraped {n} {name}"

        self._write_line(line)

        self.update_last_scrapes(name, date)
        
if __name__ == "__main__":
    logger = Logger()
    logger.log(pd.DataFrame(), "manual_run")