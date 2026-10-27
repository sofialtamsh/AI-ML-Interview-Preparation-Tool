import logging

# HTTP client libraries log every request URL at INFO. Source URLs can carry an API key in the
# query string, so those loggers only report warnings and errors.
_QUIET_LOGGERS = ("httpx", "httpx2", "httpcore")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    for name in _QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
