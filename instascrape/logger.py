import logging
import sys
import os

from colorama import (Fore, Style)

from instascrape import DIR_PATH


def set_logger(level: int = 20):
    """Set up logger. If this function is called repeatedly, returns the same logger with no changes.

    Arguments:
        level: logging level of the logger [0, 10, 20, 30, 40, 50]

    Returns:
        logging.Logger
    """
    log_file = os.path.join(DIR_PATH, "instascrape.log")
    # Set the requests logger level to WARNING
    logging.getLogger("requests").setLevel(logging.WARNING)

    logger = logging.getLogger("instascrape")
    logger.propagate = True
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, mode="a+")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] (%(funcName)s in %(filename)s line %(lineno)d) %(msg)s"))

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setFormatter(Formatter())
    stream_handler.setLevel(level)

    if not logger.hasHandlers():
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
    else:
        # restore
        logger.handlers[1].setLevel(level)
        logger.handlers[1].setFormatter(Formatter())
    return logger


class Formatter(logging.Formatter):

    def format(self, record):
        original_fmt = self._fmt

        # Customize format
        if record.levelno == logging.DEBUG:
            self._style._fmt = "    {0}DEBUG: %(msg)s{1}".format(Fore.LIGHTBLACK_EX, Fore.RESET)
        elif record.levelno == logging.INFO:
            self._style._fmt = "- %(msg)s"
        elif record.levelno == logging.WARNING:
            self._style._fmt = "- {0}WARNING:{1} %(msg)s{2}".format(Style.BRIGHT + Fore.LIGHTYELLOW_EX, Style.RESET_ALL + Fore.LIGHTYELLOW_EX, Fore.RESET)
        elif record.levelno == logging.ERROR:
            self._style._fmt = "- {0}ERROR:{1} %(msg)s{2}".format(Style.BRIGHT + Fore.LIGHTMAGENTA_EX, Style.RESET_ALL + Fore.MAGENTA, Fore.RESET)
        elif record.levelno == logging.CRITICAL:
            self._style._fmt = "- {0}CRITIC:{1} %(msg)s{2}".format(Style.BRIGHT + Fore.RED, Style.RESET_ALL + Fore.RED, Fore.RESET)

        result = logging.Formatter.format(self, record)

        # Restore the original format configured
        self._fmt = original_fmt
        return result
