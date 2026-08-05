import concurrent.futures
from typing import Any, Dict

from config.models import Config
from core.runner import run_backtest_with_config
from optimization.base import BaseOptimizer
from research.result_store import ResultStore


def _run_single_job(config: Config, param_set: Dict[str, Any]) -> Dict[str, Any]:
    """wrapper function to execute a single backtest job.
    must be a module level function for multiprocessing pickling."""
    try:
        stats = run_backtest_with_config(config, strategy_params_override=param_set)
        return {"parameters": param_set, "stats": stats, "error": None}
    except Exception as e:
        return {"parameters": param_set, "stats": {}, "error": str(e)}


class OptimizationRunner:
    def __init__(self, config: Config, optimizer: BaseOptimizer, logger: Any = None):
        self.config = config
        self.optimizer = optimizer
        self.logger = logger
        self.result_store = ResultStore()

    def run(self):
        """executes the optimization using multiprocessing."""
        param_sets = self.optimizer.generate_parameter_sets()
        if not param_sets:
            if self.logger:
                self.logger.warning("No parameter combinations generated.")
            return

        workers = self.config.optimization.workers
        if self.logger:
            self.logger.info(
                f"Starting optimization with {len(param_sets)} jobs across {workers} workers."
            )

        results = []

        if workers <= 1:
            for p in param_sets:
                res = _run_single_job(self.config, p)
                if res["error"]:
                    if self.logger:
                        self.logger.error(
                            f"Job failed for params {res['parameters']}: {res['error']}"
                        )
                else:
                    results.append(res)
                    run_id = self.result_store.save_run(
                        strategy_name=self.config.strategy.name,
                        parameters=res["parameters"],
                        stats=res["stats"],
                    )
                    if self.logger:
                        self.logger.info(
                            f"Completed run {run_id}. Return: {res['stats'].get('Return', 0):.2f}%"
                        )
        else:
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {executor.submit(_run_single_job, self.config, p): p for p in param_sets}

                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res["error"]:
                        if self.logger:
                            self.logger.error(
                                f"Job failed for params {res['parameters']}: {res['error']}"
                            )
                    else:
                        results.append(res)
                        run_id = self.result_store.save_run(
                            strategy_name=self.config.strategy.name,
                            parameters=res["parameters"],
                            stats=res["stats"],
                        )
                        if self.logger:
                            self.logger.info(
                                f"Completed run {run_id}. Return: {res['stats'].get('Return', 0):.2f}%"
                            )

        if self.logger:
            self.logger.info(
                f"Optimization finished. Successfully evaluated {len(results)}/{len(param_sets)} combinations."
            )

        # optional sort results by sharpe ratio and return top.
        results.sort(key=lambda x: x["stats"].get("Sharpe", -999.0), reverse=True)
        return results
