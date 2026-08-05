import concurrent.futures
import datetime
import random
from typing import Any

from config.models import Config
from core.events import FillEvent, OrderEvent
from core.runner import run_backtest_with_config
from execution.simulated_broker import SimulatedBroker
from research.result_store import ResultStore


class MonteCarloBroker(SimulatedBroker):
    """a broker that injects random slippage commissions and execution latency."""

    def __init__(
        self, events, data_handler, slippage_std=0.001, commission_base=1.0, latency_prob=0.1
    ):
        super().__init__(events, data_handler)
        self.slippage_std = slippage_std
        self.commission_base = commission_base
        self.latency_prob = latency_prob

    def execute_order(self, event: OrderEvent) -> None:
        if event.type == "ORDER":
            # . random execution latency drop order or delay by not acting on it immediately.
            # for simplicity we just skip it with latency prob simulating a dropped rejected order.
            if random.random() < self.latency_prob:
                return

            fill_cost = self.data_handler.get_latest_bar_value(event.symbol, "Close")

            # . random slippage log normal or normal perturbation.
            slippage = random.gauss(0, self.slippage_std) * fill_cost
            if event.direction == "BUY":
                fill_cost += abs(slippage)  # worse fill.
            else:
                fill_cost -= abs(slippage)  # worse fill.

            # . random commission.
            commission = self.commission_base * (1.0 + random.uniform(-0.2, 0.2))

            fill_event = FillEvent(
                timeindex=datetime.datetime.now(datetime.timezone.utc),
                symbol=event.symbol,
                exchange="NSE",
                quantity=event.quantity,
                direction=event.direction,
                fill_cost=fill_cost,
                commission=commission,
            )
            self.events.put(fill_event)


def _run_mc_job(config: Config, iter_idx: int) -> dict[str, Any]:
    """runs a single monte carlo iteration."""
    return _run_mc_job_safe(config, iter_idx)


class MCBrokerFactory:
    def __init__(self, slippage_std, commission_base, latency_prob):
        self.slippage_std = slippage_std
        self.commission_base = commission_base
        self.latency_prob = latency_prob

    def __call__(self, events, data_handler):
        return MonteCarloBroker(
            events, data_handler, self.slippage_std, self.commission_base, self.latency_prob
        )


def _run_mc_job_safe(config: Config, iter_idx: int) -> dict:
    random.seed(42 + iter_idx)
    factory = MCBrokerFactory(
        slippage_std=config.optimization.parameters.get("_slippage_std", 0.001),
        commission_base=config.optimization.parameters.get("_commission_base", 1.0),
        latency_prob=config.optimization.parameters.get("_latency_prob", 0.05),
    )

    try:
        stats = run_backtest_with_config(config, broker_override=factory)
        return {"iteration": iter_idx, "stats": stats, "error": None}
    except Exception as e:
        return {"iteration": iter_idx, "stats": {}, "error": str(e)}


class MonteCarloAnalyzer:
    def __init__(self, config: Config, logger: Any = None):
        self.config = config
        self.logger = logger
        self.result_store = ResultStore(base_dir="research/results/montecarlo")
        self.iterations = self.config.optimization.parameters.get("_mc_iterations", 100)

    def run(self):
        workers = self.config.optimization.workers
        if self.logger:
            self.logger.info(f"Starting Monte Carlo Simulation with {self.iterations} iterations.")

        results = []
        if workers <= 1:
            for i in range(self.iterations):
                res = _run_mc_job_safe(self.config, i)
                if res["error"]:
                    if self.logger:
                        self.logger.error(f"MC Iteration {res['iteration']} failed: {res['error']}")
                else:
                    results.append(res)
                    self.result_store.save_run(
                        strategy_name=f"{self.config.strategy.name}_MC_Iter_{res['iteration']}",
                        parameters={},
                        stats=res["stats"],
                    )
        else:
            with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(_run_mc_job_safe, self.config, i): i
                    for i in range(self.iterations)
                }

                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res["error"]:
                        if self.logger:
                            self.logger.error(
                                f"MC Iteration {res['iteration']} failed: {res['error']}"
                            )
                    else:
                        results.append(res)
                        self.result_store.save_run(
                            strategy_name=f"{self.config.strategy.name}_MC_Iter_{res['iteration']}",
                            parameters={},
                            stats=res["stats"],
                        )

        if self.logger:
            self.logger.info(f"Monte Carlo Simulation completed {len(results)} iterations.")
            # calculate basic stats on the distribution.
            returns = [r["stats"].get("Return", 0) for r in results]
            if returns:
                mean_ret = sum(returns) / len(returns)
                sorted_returns = sorted(returns)
                p05 = sorted_returns[int(len(sorted_returns) * 0.05)]
                p95 = sorted_returns[int(len(sorted_returns) * 0.95)]
                self.logger.info(f"Mean Return: {mean_ret:.2f}% | 90% CI: [{p05:.2f}%, {p95:.2f}%]")

        return results
