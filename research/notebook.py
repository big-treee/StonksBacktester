import json
import os
import time


class ResearchNotebook:
    def __init__(self, file_path: str = "research/research_notebook.json"):
        self.file_path = file_path
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def log_experiment(self, experiment_data: dict):
        experiment_data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(self.file_path, "r") as f:
            notebook = json.load(f)

        notebook.append(experiment_data)

        with open(self.file_path, "w") as f:
            json.dump(notebook, f, indent=4)
