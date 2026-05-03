import logging

from dume.logging import get_logger, setup_file_logging


def test_get_logger_uses_dume_namespace() -> None:
    logger = get_logger("control")

    assert logger.name == "dume.control"


def test_setup_file_logging_creates_log_file(tmp_path) -> None:
    log_path = setup_file_logging(tmp_path)
    logger = get_logger("dume")

    logger.info("hello")
    for handler in logger.handlers:
        handler.flush()

    assert log_path.exists()
    assert logging.getLogger("dume") is logger
