import itertools
from typing import Any, Dict, List

from optimization.base import BaseOptimizer


class GridSearchOptimizer(BaseOptimizer):
    def generate_parameter_sets(self) -> List[Dict[str, Any]]:
        """generates all combinations of the parameter sweeps."""
        params_sweep = self.config.optimization.parameters
        if not params_sweep:
            return [{}]

        keys = list(params_sweep.keys())
        # ensure values are lists.
        values = [v if isinstance(v, list) else [v] for v in params_sweep.values()]

        combinations = list(itertools.product(*values))

        results = []
        for combo in combinations:
            param_set = dict(zip(keys, combo))
            results.append(param_set)

        if self.logger:
            self.logger.info(f"Grid Search generated {len(results)} parameter combinations.")

        return results
