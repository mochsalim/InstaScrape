import os
import pickle
import logging
from threading import Thread
from datetime import datetime
from contextlib import contextmanager

import requests

from instascrape import (DIR_PATH, ACCOUNT_DIR)
from instascrape.exceptions import InstaScrapeError

logger = logging.getLogger("instascrape")


def get_biggest_media(images: list) -> dict:
    """Sort the given 'display_resources' list by key 'config_height' and 'config_width' in descending order. Choose the first element.

    Arguments:
        images: the list to be sorted

    Returns:
        dict: the element with the biggest size
    """
    return sorted(images, key=lambda x: x["config_width"], reverse=True)[0]


def to_datetime(timestamp: float) -> str:
    """Convert a timestamp to a datetime format: YY-mm-dd-h:m:s."""
    return str(datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d-%X"))


def to_timestamp(date: str) -> float:
    """Convert a datetime string to a timestamp."""
    return datetime.strptime(str(date), "%Y-%m-%d-%X").timestamp()


def dump_cookie(username: str, cookie: requests.sessions.cookielib.CookieJar):
    """Dump InstaScraper session cookie to a pickle file in ~/.instascrape/accounts/.

    Arguments:
        username: the login username
        cookie: the CookieJar object that will be dumped

    Returns:
        True if success
    """
    path = os.path.join(ACCOUNT_DIR, username + ".cookie")
    logger.debug("dumping cookie to {0}...".format(path))
    if os.path.isfile(path):
        logger.warning("Cookie file already exists. Overwriting...")
    # Convert cookie to dict
    cookie_dict = requests.utils.dict_from_cookiejar(cookie)

    with open(path, "wb+") as pkl:
        pickle.dump(cookie_dict, pkl)
    return True


def load_cookie(username: str):
    """Load a cookie pickle file from ~/.instascrape/accounts/.

    Arguments:
        username: the login username

    Returns:
        CookieJar if found matched cookie file
    """
    path = os.path.join(ACCOUNT_DIR, username + ".cookie")
    logger.debug("trying to load cookie from {0}...".format(path))
    if not os.path.isfile(path):
        logger.debug("cookie file for {0} not found".format(username))
        return False
    with open(path, "rb") as pkl:
        cookie_dict = pickle.load(pkl)
        cookie = requests.utils.cookiejar_from_dict(cookie_dict)
    return cookie


def delete_cookie(username: str):
    """Delete a cookie file from ~/.instascrape/accounts/, given the username.

    Arguments:
        username: the login username

    Returns:
        True if success

    Raises:
        InstaScrapeError if cookie file not found
    """
    path = os.path.join(ACCOUNT_DIR, username + ".cookie")
    logger.debug("deleting cookie in {0}...".format(path))
    if not os.path.isfile(path):
        raise InstaScrapeError("Cookie file for {0} not found".format(username))
    os.remove(path)
    return True


def dump_obj(obj):
    """Dump the `InstaScraper` object into a pickle file for later 'cli' use.

    Arguments:
        obj: `InstaScraper` object
    """
    path = os.path.join(DIR_PATH, "insta.pkl")
    logger.debug("dumping object to {0}...".format(path))
    if os.path.isfile(path):
        logger.debug("pickle file already exists, overwrite.")
    with open(path, "wb+") as pkl:
        pickle.dump(obj, pkl)


def load_obj():
    """Load the `InstaScraper` object stored in the pickle file.

    Returns:
        insta: `InstaScraper` object if one is found, None otherwise
    """
    path = os.path.join(DIR_PATH, "insta.pkl")
    logger.debug("loading object from {0}...".format(path))
    if not os.path.isfile(path):
        logger.debug("{0} pickle file not found.".format(path))
        return
    with open(path, "rb") as pkl:
        insta = pickle.load(pkl)
    return insta


def remove_obj():
    """Remove the pickle file that stored the `InstaScraper` object."""
    path = os.path.join(DIR_PATH, "insta.pkl")
    logger.debug("removing object in {0}".format(path))
    if not os.path.isfile(path):
        logger.warning("{0} pickle file not found".format(path))
        return
    os.remove(path)


@contextmanager
def protection(*args):
    """Protects behaviour within this context from exceptions thrown. Continue the job instead of crashing the program."""
    try:
        yield
    except Exception as e:
        logger.error("{0} ({1}): {2}".format(args[0], args[1], e))
    finally:
        pass


def instance_worker(session: requests.Session, instance, generator) -> list:
    """Spawn threads to produce instances by looping through a generator. (with protection)
    - Passes items that are yielded from the generator as arguments to the instance.
    * `instance`: one of `Post` or `Profile`.
    """
    logger.info("==========[Preload Started]==========")
    results = []
    # collect itmes from generator
    logger.info("[1] Collecting items...")
    items = []
    for i in generator:
        if i:
            items.append(i)
    # job
    def job(item: str):
        with protection(instance.__name__, item):
            results.append(instance(session, item))
    # spawn threads
    logger.info("[2] Spawning workers...")
    threads = []
    for item in items:
        thread = Thread(target=job, args=(item,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    logger.info("==========[Preload Completed]========")
    return results


def instance_generator(session: requests.Session, instance, generator):
    """Yields an instance produced from each item in a generator. (with protection)"""
    for index, item in enumerate(generator):
        with protection(instance.__name__, item):
            yield instance(session, item)
