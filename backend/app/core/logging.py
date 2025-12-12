import logging
from .settings import settings


def setup_logging() -> None:
    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
