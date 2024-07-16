import warnings
import logging


class Colors:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"


class Formatter(logging.Formatter):
    COLORS = {
        "DEBUG": Colors.BLUE,
        "INFO": Colors.GREEN,
        "WARNING": Colors.YELLOW,
        "ERROR": Colors.RED,
        "CRITICAL": Colors.MAGENTA,
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, Colors.RESET)
        message = super().format(record)
        time, rest = message.split("[", 1)
        return f"{time}{Colors.RESET} {color}[{rest}{Colors.RESET}"


class TransformersFilter(logging.Filter):
    def filter(self, record):
        return not record.name.startswith("transformers")


def create_logger(
    name: str = __name__,
    level: int = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()

    formatter = Formatter(
        "%(asctime)s [%(levelname)-8s %(name)-12s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)

    warnings.filterwarnings("ignore", category=UserWarning)

    return logger


if __name__ == "__main__":
    log = create_logger(__name__)
    log.debug("debug message")
    log.info("info message")
    log.warning("warning message")
    log.error("error message")
    log.critical("critical message %s", "test")
