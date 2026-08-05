from abc import ABC, abstractmethod
from typing import Any, Dict, List

from config.models import Config


class BaseOptimizer(ABC):
    def __init__(self, config: Config, logger: Any = None):
        self.config = config
        self.logger = logger

    @abstractmethod
    def generate_parameter_sets(self) -> List[Dict[str, Any]]:
        """generates the list of parameter combinations to evaluate."""
        pass
