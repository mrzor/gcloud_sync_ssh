import logging
import pytest
from _pytest.logging import caplog as _caplog  # noqa:F401
from loguru import logger


# Disable logging to stderr
logger.remove()


@pytest.fixture
def caplog(_caplog):  # noqa:F811
    class PropogateHandler(logging.Handler):
        def emit(self, record):
            logging.getLogger(record.name).handle(record)

    handler_id = logger.add(PropogateHandler(), format="{message}")
    yield _caplog
    logger.remove(handler_id)
