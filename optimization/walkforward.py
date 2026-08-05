import datetime
from dataclasses import replace
from typing import Any

from dateutil.relativedelta import relativedelta

from config.models import Config
from core.runner import run_backtest_with_config
from optimization.grid_search import GridSearchOptimizer
from optimization.runner import OptimizationRunner
from research.result_store import ResultStore


class WalkForwardAnalyzer:
    def __init__(self, config: Config, logger: Any = None):
        self.config = config
        self.logger = logger
        self.result_store = ResultStore(base_dir="research/results/walkforward")

        # we need these from config or default them.
        # let s say user passes them in optimization parameters as well.
        opt_params = self.config.optimization.parameters
        self.train_months = opt_params.pop("_train_months", 12)
        self.test_months = opt_params.pop("_test_months", 3)
        self.step_months = opt_params.pop(
            "_step_months", 3
        )  # how much to slide the window forward.

    def _parse_date(self, date_str: str) -> datetime.datetime:
        # simplistic parser assumes yyyy mm dd.
        return datetime.datetime.strptime(date_str, "%Y-%m-%d")

    def run(self):
        start_date = self._parse_date(self.config.data.start_date)
        end_date = self._parse_date(self.config.data.end_date)

        current_train_start = start_date
        fold_idx = 1
        results = []

        while True:
            current_train_end = current_train_start + relativedelta(months=self.train_months)
            current_test_start = current_train_end
            current_test_end = current_test_start + relativedelta(months=self.test_months)

            if current_test_end > end_date:
                # we can t form a full test window break out.
                break

            if self.logger:
                self.logger.info(f"--- Fold {fold_idx} ---")
                self.logger.info(
                    f"Train: {current_train_start.strftime('%Y-%m-%d')} to {current_train_end.strftime('%Y-%m-%d')}"
                )
                self.logger.info(
                    f"Test: {current_test_start.strftime('%Y-%m-%d')} to {current_test_end.strftime('%Y-%m-%d')}"
                )

            # . create a config for the training period.
            train_data_config = replace(
                self.config.data,
                start_date=current_train_start.strftime("%Y-%m-%d"),
                end_date=current_train_end.strftime("%Y-%m-%d"),
            )
            train_config = replace(self.config, data=train_data_config)

            # . run optimization on training period.
            # walk forward usually uses gridsearch or randomsearch. we ll default to gridsearch.
            optimizer = GridSearchOptimizer(train_config, self.logger)
            runner = OptimizationRunner(train_config, optimizer, self.logger)

            # the runner automatically saves all runs. it returns sorted results.
            train_results = runner.run()
            if not train_results:
                if self.logger:
                    self.logger.error("No valid combinations found during training. Aborting WFA.")
                break

            best_params = train_results[0]["parameters"]
            if self.logger:
                self.logger.info(
                    f"Best Training Params: {best_params} (Return: {train_results[0]['stats'].get('Return', 0):.2f}%)"
                )

            # . create a config for the testing period.
            test_data_config = replace(
                self.config.data,
                start_date=current_test_start.strftime("%Y-%m-%d"),
                end_date=current_test_end.strftime("%Y-%m-%d"),
            )
            test_config = replace(self.config, data=test_data_config)

            # . run backtest on testing period with best params.
            test_stats = run_backtest_with_config(
                test_config, strategy_params_override=best_params, log_manager=None
            )  # type ignore.

            # . save out of sample result.
            run_id = self.result_store.save_run(
                strategy_name=f"{self.config.strategy.name}_WFA_Fold_{fold_idx}",
                parameters=best_params,
                stats=test_stats,
            )

            results.append(
                {
                    "fold": fold_idx,
                    "train_start": current_train_start.strftime("%Y-%m-%d"),
                    "test_end": current_test_end.strftime("%Y-%m-%d"),
                    "best_params": best_params,
                    "oos_stats": test_stats,
                }
            )

            if self.logger:
                self.logger.info(
                    f"OOS Fold Return: {test_stats.get('Return', 0):.2f}% (Saved as {run_id})"
                )

            # slide window forward.
            current_train_start += relativedelta(months=self.step_months)
            fold_idx += 1

        return results
