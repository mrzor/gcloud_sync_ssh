from loguru import logger
from .cli import cli

try:
    cli()
except SystemExit:
    raise
except:  # noqa: E722
    logger.exception("Uncaught exception")
    exit(51)
