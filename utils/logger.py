import logging
import os
import sys


def setup_logger(name: str, log_level: str, log_file: str | None = None) -> logging.Logger:
    """sets up a logger with a console handler and an optional file handler."""
    logger = logging.getLogger(name)

    # avoid adding multiple handlers if the logger is already configured.
    if logger.hasHandlers():
        logger.handlers.clear()

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # console handler.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # file handler.
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # prevent log messages from propagating to the root logger and being printed twice.
    logger.propagate = False

    return logger


class LogManager:
    """manages the creation of dedicated loggers for different application components."""

    def __init__(self, log_level: str, log_dir: str = "logs"):
        self.log_level = log_level
        self.log_dir = log_dir

    def get_logger(self, name: str, file_name: str | None = None) -> logging.Logger:
        if file_name:
            file_path = os.path.join(self.log_dir, file_name)
        else:
            file_path = None
        return setup_logger(name, self.log_level, file_path)

    @property
    def engine(self) -> logging.Logger:
        return self.get_logger("Engine", "app.log")

    @property
    def portfolio(self) -> logging.Logger:
        return self.get_logger("Portfolio", "trades.log")

    @property
    def execution(self) -> logging.Logger:
        return self.get_logger("Execution", "trades.log")

    @property
    def strategy(self) -> logging.Logger:
        return self.get_logger("Strategy", "app.log")
