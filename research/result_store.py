import csv
import json
import os
import time
from typing import Any, Dict


class ResultStore:
    def __init__(self, base_dir: str = "research/results"):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

        self.csv_path = os.path.join(self.base_dir, "optimization_log.csv")

        # initialize csv with headers if it doesn t exist.
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, mode="w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Run_ID",
                        "Timestamp",
                        "Strategy",
                        "Parameters",
                        "Return",
                        "Sharpe",
                        "Max_Drawdown",
                        "Final_Equity",
                    ]
                )

    def save_run(
        self, strategy_name: str, parameters: Dict[str, Any], stats: Dict[str, Any]
    ) -> str:
        """saves the optimization run results to a csv log and a detailed json file.
        returns the unique run id."""
        run_id = f"run_{int(time.time() * 1000)}"
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        # save to csv.
        with open(self.csv_path, mode="a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    run_id,
                    timestamp,
                    strategy_name,
                    json.dumps(parameters),
                    stats.get("Return", 0.0),
                    stats.get("Sharpe", 0.0),
                    stats.get("Max Drawdown", 0.0),
                    stats.get("Final Equity", 0.0),
                ]
            )

        # save detailed json.
        json_path = os.path.join(self.base_dir, f"{run_id}.json")
        detailed_data = {
            "run_id": run_id,
            "timestamp": timestamp,
            "strategy": strategy_name,
            "parameters": parameters,
            "stats": stats,
        }
        with open(json_path, mode="w") as f:
            json.dump(detailed_data, f, indent=4)

        return run_id
