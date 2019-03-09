import re
import logging
import os
import json
from io import IOBase

import requests

from instascrape.constants import *
from instascrape.structures import *
from instascrape.exceptions import *
from instascrape.logger import set_logger
from instascrape.download import (_down_posts, _down_containers, _down_from_src)
from instascrape.utils import (dump_cookie, load_cookie, delete_cookie, instance_worker, instance_generator)


class LoggerMixin:
    """Plug a logger and allows `InstaScraper` to access `self._logger` without having a logger object (attribute) itself.
    * Useful when pickling `InstaScraper` object, since a `thread.lock` object cannot be pickled.
    - https://stackoverflow.com/questions/3375443/how-to-pickle-loggers
    """

    @property
    def _logger(self):
        """
        * `self.level` is defined in subclass.
        * If `self._level` is None, that means to use th preset `level` and get the exising logger.
        """
        if self._level is not None:
            return set_logger(level=self._level)
        return logging.getLogger("instascrape")


class InstaScraper(LoggerMixin):
    """The main context of InstaScrape API, which provides high-level methods for getting `structure` objects by calling low-level methods defined in `structures.py`.

    Arguments:
        username: username for logging in to Instagram (can be email or phone number)
        password: password for logging in to Instagram
        level: set logger's logging level (if the logger has set up already, pass in `None` to get the logger instead of setting it up again)
        user_agent: user provided user_agent
        cookie: user provided cookie data
        save_cookie: call dump_cookie function to save login cookie data to a pickle file for next use if True *(for `contextmanager` only)
        logout: logout from Instagram if True !(for `contextmanager` only)
    """
    def __init__(self, username: str = None, password: str = None,
                 user_agent: str = None, cookie: dict = None,
                 save_cookie: bool = True, logout: bool = True, level: int = None):
        # Initialise variables
        self.username = username
        self._password = password
        self._save_cookie = save_cookie
        self._logout = logout
        self._level = level
        self.my_user_id = ""
        self.my_username = ""
        self.logged_in = False
        # Prepare requests session
        self._session = requests.Session()
        if cookie:
            self._session.cookies = requests.utils.cookiejar_from_dict(cookie)
        self._session.headers.update({"Accept-Encoding": "gzip, deflate", "Accept-Language": "en-US,en;q=0.8",
                                      "Connection": "keep-alive", "Content-Length": "0",
                                      "Host": "www.instagram.com", "Origin": "https://www.instagram.com",
                                      "Referer": "https://www.instagram.com/", "User-Agent": user_agent or UA,
                                      "X-Instagram-AJAX": "1", "X-Requested-With": "XMLHttpRequest"})

    def __enter__(self):
        if self._level is None:
            self._level = 10  # set level to 10 (INFO) if using this class as a context manager (as API)
        # otehrwise if accessed in command line, the logger is already set in `cli.py`
        self.login()
        return self

    def __exit__(self, *args):
        if self._logout:
            self.logout()
        return False

    def _get_my_username(self):
        try:
            r = self._session.get(BASE_URL)
        except requests.ConnectionError:
            raise ConnectionError(BASE_URL)
        r.raise_for_status()
        username = re.findall(r'"username":"(.+?)"', r.text)
        if not username:
            raise LoginError("Failed to find username.")
        return username[0]

    def login(self):
        """Login to Instagram.
        If cookie file is provided, skip POST request login process.
        Get a new cookie by username and password login otherwise.

        Returns:
            self.my_username (str): found by self._get_my_username method using regex
            self.my_user_id (str): retrieve from cookie data
        """
        self._logger.debug("Logging in...")

        cookie = self._session.cookies or load_cookie(self.username) if self.username else None  # cookie already configured in initialise ?

        if cookie:
            # Load saved cookie
            self._logger.debug("using local cookie")
            self._session.headers.update({"X-CSRFToken": cookie["csrftoken"]})
            self._session.cookies = cookie

        else:
            if not all((self.username, self._password)):
                raise LoginError("Cannot load local cookie. All credentials must be provided in this situation.")
            # Get a new cookie by username and password
            self._logger.debug("getting cookie by username and password")
            mid_url = BASE_URL + "/web/__mid"
            try:
                # get initial cookie data
                self._session.get(mid_url)
            except requests.ConnectionError:
                raise ConnectionError(mid_url)

            csrftoken = self._session.cookies.get_dict()["csrftoken"]
            self._session.headers.update({"X-CSRFToken": csrftoken})
            payload = {"username": self.username, "password": self._password}
            resp = self._session.post(LOGIN_URL, data=payload).json()

            if not resp["authenticated"]:
                # Login Failed !
                if resp["status"] is False:
                    raise ConnectionError(LOGIN_URL)
                msg = "Unknown error occurred when logging in to Instagram!"
                if resp["authenticated"] is False and resp["user"] is True:
                    msg = "Wrong password!"
                if resp["authenticated"] is False and resp["user"] is False:
                    msg = "User '{0}' does not exist!".format(self.username)
                raise LoginError(msg)

        self.my_user_id = self._session.cookies["ds_user_id"]
        self.my_username = self._get_my_username()
        if self._save_cookie:
            # save cookie for later use
            dump_cookie(self.my_username, self._session.cookies)
        self.logged_in = True
        self._logger.debug("Logged in as {0} ({1})".format(self.my_username, self.my_user_id))
        return self.my_user_id, self.my_username

    def logout(self):
        """Log out from Instagram by sending a POST request.
        And call delete_cookie utils function to remove cookie from accounts.
        * If you want to reuse session and cookie, do not call this method.

        Returns:
            True if logout success, False otherwise
        """
        if not self.logged_in:
            self._logger.error("You have not logged in.")
            return False
        self._logger.debug("Logging out...")
        # logout Instagram
        param = {"csrfmiddlewaretoken": self._session.headers["X-CSRFToken"]}
        self._session.post(LOGOUT_URL, data=param)
        # logout by removing object pickle file
        if self._save_cookie:  # ensure the cookie exists
            delete_cookie(self.username)
        self._logger.debug("Logged out")
        return True

    # =============Get Methods===============

    # --------------Individuals---------------

    def get_profile(self, name: str) -> Profile:
        """Get a Profile object by a user's username."""
        assert name, "Empty arguments"
        self._logger.info("Getting @{0}'s profile data...".format(name))
        return Profile(self._session, name=name)

    def get_post(self, shortcode: str) -> Post:
        """Get a Post object by a post's shortcode."""
        assert shortcode, "Empty arguments"
        self._logger.info("Getting :{0} post data...".format(shortcode))
        return Post(self._session, shortcode=shortcode)

    def get_story(self, name: str = None, tag: str = None) -> Story:
        """Get a user's Story object by user id via User object or by hashtag name.
        * Either name or tag argument should be given.
        """
        assert (name or tag) and not all((name, tag)), "Empty arguments"
        user_id = None
        if name:
            user_id = self.get_profile(name).user_id
        self._logger.info("Getting {0} story data...".format("#" + tag if tag else "@" + name + "'s"))
        return Story(self._session, user_id=user_id, tag=tag)

    # ------------From File------------------

    def _get_objects_from_file(self, obj, prefix_char: str, file: IOBase, preload: bool = False):
        if not isinstance(file, IOBase):
            raise ValueError("'file' argument must be an opend file")
        try:
            lines = file.readlines()
            lines = [line.strip() for line in lines if line.strip()[0] == prefix_char]  # filter out invalid lines and strip them
            if preload:
                return instance_worker(self._session, obj, lines)
            else:
                return instance_generator(self._session, obj, lines)
        finally:
            file.close()

    def get_profiles_from_file(self, file: IOBase, preload: bool = False):
        """Retrieve `Profile` objects by reading a plain text file that contains one username each line.
        * Line format: `@{username}`.
        * Lines that do not start with this particular prefix character will be ignored.

        Arguments:
            file: an already opend file object to read from
            preload: converts all items yielded from the generator to `Profile` instances and returns a list if True

        Returns:
            list: if preload=True, which contains `Profile` instances
            generator: if preload=False, which yields `Profile` instances
        """
        return self._get_objects_from_file(Profile, "@", file, preload)

    def get_posts_from_file(self, file: IOBase, preload: bool = False):
        """Retrieve `Profile` objects by reading a plain text file that contains one username each line.
        * Line format: `:{shortcode}`.
        * Lines that do not start with this particular prefix character will be ignored.

        Arguments:
            file: an already opend file object to read from
            preload: converts all items yielded from the generator to `Post` instances and returns a list if True

        Returns:
            list: if preload=True, which contains `Post` instances
            generator: if preload=False, which yields `Post` instances
        """
        return self._get_objects_from_file(Post, ":", file, preload)

    # ------------Profile Based--------------

    def get_user_timeline_posts(self, name: str, count: int = 50, only: str = None, timestamp_limit: dict = None, preload: bool = False):
        """Get a user's timeline posts in the form of `Post` objects

        Arguments:
            name: the user's username
            count: maximum limit of posts you want to get
            only: only this type of posts will be downloaded [image, video, sidecar]
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
            preload: converts all items yielded from the generator to `Post` instances and returns a list if True

        Returns:
            list: if preload=True, which contains `Post` instances
            generator: if preload=False, which yields `Post` instances
        """
        assert name, "Empty arguments"
        self._logger.info("Fetching @{0}'s timeline posts...".format(name))
        user = self.get_profile(name)
        posts = user.fetch_timeline_posts(count, only, timestamp_limit)
        if next(posts) is False:
            self._logger.error("No timeline posts found for @{0}.".format(name))
            return []
        if preload:
            return instance_worker(self._session, Post, posts)
        else:
            return instance_generator(self._session, Post, posts)

    def get_self_saved_posts(self, count: int = 50, only: str = None, timestamp_limit: dict = None, preload: bool = False):
        """Get self saved posts in the form of `Post` objects.

        Arguments:
            count: maximum limit of posts you want to get
            only: only this type of posts will be downloaded [image, video, sidecar]
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
            preload: converts all items yielded from the generator to `Post` instances and returns a list if True

        Returns:
            list: if preload=True, which contains `Post` instances
            generator: if preload=False, which yields `Post` instances
        """
        assert self.my_username, "Empty arguments"
        self._logger.info("Fetching @{0}'s saved posts...".format(self.my_username))
        user = self.get_profile(self.my_username)
        posts = user.fetch_saved_posts(count, only, timestamp_limit)
        if next(posts) is False:
            self._logger.error("No saved posts found for @{0}.".format(self.my_username))
            return []
        if preload:
            return instance_worker(self._session, Post, posts)
        else:
            return instance_generator(self._session, Post, posts)

    def get_user_tagged_posts(self, name: str, count: int = 50, only: str = None, timestamp_limit: dict = None, preload: bool = False):
        """Get posts that tagged the user in the form of `Post` objects.

        Arguments:
            name: the user's username
            count: maximum limit of posts you want to get
            only: only this type of posts will be downloaded [image, video, sidecar]
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
            preload: converts all items yielded from the generator to `Post` instances and returns a list if True

        Returns:
            list: if preload=True, which contains `Post` instances
            generator: if preload=False, which yields `Post` instances
        """
        assert name, "Empty arguments"
        self._logger.info("Fetching @{0}'s tagged posts...".format(name))
        user = self.get_profile(name)
        posts = user.fetch_tagged_posts(count, only, timestamp_limit)
        if next(posts) is False:
            self._logger.error("No tagged posts found for @{0}.".format(name))
            return []
        if preload:
            return instance_worker(self._session, Post, posts)
        else:
            return instance_generator(self._session, Post, posts)

    def get_user_followers(self, name: str, count: int = 50, convert: bool = True, preload: bool = False):
        """Get a user's followers in the form of `Profile` objects or just plain usernames.

        Arguments:
            name: the user's username
            count: maximum limit of followers you want to get
            convert: convert fetched usernames to `Profile` objects if True
            preload: converts all items yielded from the generator to `Profile` instances and returns a list if True

        Returns:
            list: if preload=True, which contains `Profile` instances
            generator: if preload=False, which yields `Profile` instances
        """
        assert name, "Empty arguments"
        self._logger.info("Fetching @{0}'s followers...".format(name))
        user = self.get_profile(name)
        usernames = user.fetch_followers(count)
        if next(usernames) is False:
            self._logger.error("No followers found for @{0}.".format(name))
            return []
        if not convert:
            return usernames
        if preload:
            return instance_worker(self._session, Profile, usernames)
        else:
            return instance_generator(self._session, Profile, usernames)

    def get_user_followings(self, name: str, count: int = 50, convert: bool = True, preload: bool = False):
        """Get a user's followings in the form of `Profile` objects or just plain usernames.

        Arguments:
            name: the user's username
            count: maximum limit of followings you want to get
            convert: convert fetched usernames to `Profile` objects if True
            preload: converts all items yielded from the generator to `Profile` instances and returns a list if True

        Returns:
            list: if preload=True, which contains `Profile` instances
            generator: if preload=False, which yields `Profile` instances
        """
        assert name, "Empty arguments"
        self._logger.info("Fetching @{0}'s followings...".format(name))
        user = self.get_profile(name)
        usernames = user.fetch_followings(count)
        if next(usernames) is False:
            self._logger.error("No following users found for @{0}.".format(name))
            return []
        if not convert:
            return usernames
        if preload:
            return instance_worker(self._session, Profile, usernames)
        else:
            return instance_generator(self._session, Profile, usernames)

    # -------------Feed Based---------------

    def get_hashtag_posts(self, tag: str, count: int = 50, only: str = None, timestamp_limit: dict = None, preload: bool = False):
        """Get posts with the hashtag name in the form of `Post` objects.

        Arguments:
            tag: hashtag name
            count: maximum limit of posts you want to get
            only: only this type of posts will be downloaded [image, video, sidecar]
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
            preload: converts all items yielded from the generator to `Post` instances and returns a list if True

        Returns:
            list: if preload=True, which contains `Post` instances
            generator: if preload=False, which yields `Post` instances
        """
        assert tag, "Empty arguments"
        self._logger.info("Fetching hashtag posts of #{0}...".format(tag))
        hashtag = Hashtag(self._session, tag)
        posts = hashtag.fetch_posts(count, only, timestamp_limit)
        if next(posts) is False:
            self._logger.error("No hashtag posts found for #{0}.".format(tag))
            return []
        if preload:
            return instance_worker(self._session, Post, posts)
        else:
            return instance_generator(self._session, Post, posts)

    def get_explore_posts(self, count: int = 50, only: str = None, timestamp_limit: dict = None, preload: bool = False):
        """Get posts in the 'discover' feed section, in the form of `Post` objects.

        Arguments:
            count: maximum limit of posts you want to get
            only: only this type of posts will be downloaded [image, video, sidecar]
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
            preload: converts all items yielded from the generator to `Post` instances and returns a list if True

        Returns:
            list: if preload=True, which contains `Post` instances
            generator: if preload=False, which yields `Post` instances
        """
        self._logger.info("Fetching explore posts...")
        explore = Explore(self._session)
        posts = explore.fetch_posts(count, only, timestamp_limit)
        if next(posts) is False:
            self._logger.error("No explore feed posts found.")
            return []
        if preload:
            return instance_worker(self._session, Post, posts)
        else:
            return instance_generator(self._session, Post, posts)

    # ----------------Post Based---------------

    def get_post_likes(self, shortcode: str = None, count: int = 50, convert: bool = True, preload: bool = False):
        """Get likes of a Post in the form of usernames or `Profile` objects.

        Arguments:
            shortcode: the shortcode of the post
            count: maximum limit of likes you want to get
            convert: convert fetched usernames to `Profile` objects if True
            preload: converts all items yielded from the generator to `Profile` instances and returns a list if True

        Returns:
            list: if preload=True, which contains `Profile` instances
            generator: if preload=False, which yields `Profile` instances
        """
        assert shortcode, "Empty arguments"
        self._logger.info("Fetching likes of :{0}".format(shortcode))
        post = self.get_post(shortcode)
        likes = post.fetch_likes(count)
        if next(likes) is False:
            self._logger.error("No likes found.")
            return []
        if not convert:
            return likes
        if preload:
            return instance_worker(self._session, Profile, likes)
        else:
            return instance_generator(self._session, Profile, likes)

    def get_post_comments(self, shortcode: str = None, count: int = 50):
        """Get comments of a post by shortcode.

        Arguments:
            shortcode: shortcode of the post
            count: maximum limit of comments you want to get

        Returns:
            generator: yields dictionaries of {"username": <string>, "text": <string>, "time": <string>}
        """
        assert shortcode, "Empty arguments"
        self._logger.info("Fetching comments of :{0}".format(shortcode))
        post = self.get_post(shortcode)
        comments = post.fetch_comments(count)
        if next(comments) is False:
            self._logger.error("No comments found.")
            return []
        return comments

    # ===========Download Methods===============

    # -------------Individuals---------------

    def download_post(self, shortcode: str, dest: str = None, dump_metadata: bool = False) -> str:
        p = self.get_post(shortcode)
        self._logger.info("Downloading {0} with {1} media...".format(shortcode, len(p)))
        # subdir = to_datetime(p.created_time) + "_" + p.shortcode
        path = _down_containers(p, dest, subdir=p.shortcode, force_subdir=dump_metadata)
        if dump_metadata:
            filename = p.shortcode + ".json"
            metadata_file = os.path.join(path, p.shortcode, filename)
            self._logger.debug("-> [{0}] dump metadata".format(filename))
            with open(metadata_file, "w+") as f:
                json.dump(p.as_dict(), f, indent=4)
        if path:
            self._logger.info("Destination: {0}".format(path))
        return path

    def download_story(self, name: str = None, tag: str = None, dest: str = None) -> str:
        story = self.get_story(name=name, tag=tag)
        self._logger.info("Downloading stories of {0} with {1} media...".format(name or "#" + tag, len(story)))
        path = _down_containers(story, dest, directory=("@" if name else "#") + story.name + "(story)")
        if path:
            self._logger.info("Destination: {0}".format(path))
        return path

    def download_user_profile_pic(self, name: str, dest: str = None) -> str:
        user = self.get_profile(name)
        self._logger.info("Downloading {0}'s profile picture...".format(name))
        path = _down_from_src(user.profile_pic, name, dest)
        if path:
            self._logger.info("Destination: {0}".format(path))
        return path

    # -------------Profile Based--------------

    def download_user_timeline_posts(self, name: str, count: int = 50, only: str = None, dest: str = None, timestamp_limit: dict = None,
                                     preload: bool = False, dump_metadata: bool = False) -> str or None:
        """Download a user's timeline posts.

        Arguments:
            name: the user's username
            count: maximum limit of posts you want to download
            only: only this type of posts will be downloaded [image, video, sidecar]
            dest: path to the destination of the download files
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
            preload: convert all items in the iterable to `Post` instances before downloading if True
            dump_metadata: force create a sub directory of the post and dump metadata of each post to a file inside if True

        Returns:
            path: full path to the download destination, or None if download failed
        """
        posts = self.get_user_timeline_posts(name, count, only, timestamp_limit, preload)
        if not posts:
            return None
        return _down_posts(posts, dest, directory="@" + name, dump_metadata=dump_metadata)

    def download_self_saved_posts(self, count: int = 50, only: str = None, dest: str = None, timestamp_limit: dict = None,
                                  preload: bool = False, dump_metadata: bool = False) -> str or None:
        """Download self saved posts.

        Arguments:
            count: maximum limit of posts you want to download
            only: only this type of posts will be downloaded [image, video, sidecar]
            dest: path to the destination of the download files
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
            preload: convert all items in the iterable to `Post` instances before downloading if True
            dump_metadata: force create a sub directory of the post and dump metadata of each post to a file inside if True

        Returns:
            path: full path to the download destination, or None if download failed
        """
        posts = self.get_self_saved_posts(count, only, timestamp_limit, preload)
        if not posts:
            return None
        return _down_posts(posts, dest, directory="saved", dump_metadata=dump_metadata)

    def download_user_tagged_posts(self, name: str, count: int = 50, only: str = None, dest: str = None, timestamp_limit: dict = None,
                                   preload: bool = False, dump_metadata: bool = False) -> str or None:
        """Download posts that tagged the user.

        Arguments:
            name: the user's username
            count: maximum limit of posts you want to download
            only: only this type of posts will be downloaded [image, video, sidecar]
            dest: path to the destination of the download files
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
            preload: convert all items in the iterable to `Post` instances before downloading if True
            dump_metadata: force create a sub directory of the post and dump metadata of each post to a file inside if True

        Returns:
            path: full path to the download destination, or None if download failed
        """
        posts = self.get_user_tagged_posts(name, count, only, timestamp_limit, preload)
        if not posts:
            return None
        return _down_posts(posts, dest, directory="@" + name + "(tagged)", dump_metadata=dump_metadata)

    # ----------------Feed Based----------------

    def download_hashtag_posts(self, tag: str, count: int = 50, only: str = None, dest: str = None, timestamp_limit: dict = None,
                               preload: bool = False, dump_metadata: bool = False) -> str or None:
        """Download posts with the given tag.

        Arguments:
            tag: tag name
            count: maximum limit of posts you want to download
            only: only this type of posts will be downloaded [image, video, sidecar]
            dest: path to the destination of the download files
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
            preload: convert all items in the iterable to `Post` instances before downloading if True
            dump_metadata: force create a sub directory of the post and dump metadata of each post to a file inside if True

        Returns:
            path: full path to the download destination, or None if download failed
        """
        posts = self.get_hashtag_posts(tag, count, only, timestamp_limit, preload)
        if not posts:
            return
        return _down_posts(posts, dest, directory="#" + tag, dump_metadata=dump_metadata)

    def download_explore_posts(self, count: int = 50, only: str = None, dest: str = None, timestamp_limit: dict = None,
                               preload: bool = False, dump_metadata: bool = False) -> str or None:
        """Download 'explore' posts feed in the 'discover' section.
        * Download to a directory named

        Arguments:
            count: maximum limit of posts you want to download
            only: only this type of posts will be downloaded [image, video, sidecar]
            dest: path to the destination of the download files
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
            preload: convert all items in the iterable to `Post` instances before downloading if True
            dump_metadata: force create a sub directory of the post and dump metadata of each post to a file inside if True

        Returns:
            path: full path to the download destination, or None if download failed
        """
        posts = self.get_explore_posts(count, only, timestamp_limit, preload)
        if not posts:
            return None
        return _down_posts(posts, dest, directory="explore", dump_metadata=dump_metadata)
