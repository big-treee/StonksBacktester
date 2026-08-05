from typing import Any, Dict, List


class FactorAnalytics:
    """analytics module for evaluating factor portfolios and performance."""

    @staticmethod
    def calculate_portfolio_exposure(
        portfolio_weights: Dict[str, float], ranked_universe: List[Dict[str, Any]]
    ) -> float:
        """calculates the aggregate factor exposure z score of a weighted portfolio."""
        z_scores = {item["symbol"]: item["z_score"] for item in ranked_universe}

        exposure = 0.0
        for sym, weight in portfolio_weights.items():
            exposure += weight * z_scores.get(sym, 0.0)

        return exposure

    @staticmethod
    def generate_quantile_portfolios(
        ranked_universe: List[Dict[str, Any]], quantiles: int = 5
    ) -> Dict[int, List[str]]:
        """divides the ranked universe into n quantiles default for quintiles .
        quantile is the top tier highest z score ."""
        n = len(ranked_universe)
        if n == 0:
            return {}

        q_size = max(1, n // quantiles)

        result = {}
        for i in range(quantiles):
            start_idx = i * q_size
            # last quantile takes any remaining.
            end_idx = (i + 1) * q_size if i < quantiles - 1 else n

            subset = ranked_universe[start_idx:end_idx]
            result[i + 1] = [item["symbol"] for item in subset]

        return result
