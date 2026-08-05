import random
from typing import Any, Dict, List

from optimization.base import BaseOptimizer


class RandomSearchOptimizer(BaseOptimizer):
    def __init__(self, config, logger=None, iterations=10):
        super().__init__(config, logger)
        # check if iterations is passed via config.optimization.parameters or use default.
        # but wait parameters are the sweep. we can get iterations from the config if we added it.
        # otherwise default to for randomsearch.
        self.iterations = config.optimization.parameters.pop("_iterations", iterations)

    def generate_parameter_sets(self) -> List[Dict[str, Any]]:
        """generates random parameter combinations from the sweeps."""
        params_sweep = self.config.optimization.parameters
        if not params_sweep:
            return [{}]

        keys = list(params_sweep.keys())
        values = [v if isinstance(v, list) else [v] for v in params_sweep.values()]

        results = []
        for _ in range(self.iterations):
            # randomly choose one element from each value list.
            chosen = [random.choice(v_list) for v_list in values]
            param_set = dict(zip(keys, chosen))
            results.append(param_set)

        if self.logger:
            self.logger.info(f"Random Search generated {len(results)} parameter combinations.")

        return results
