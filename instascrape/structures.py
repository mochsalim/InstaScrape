import json
import logging
import time
import random

import requests

from instascrape.constants import *
from instascrape.exceptions import *
from instascrape.container import container

__all__ = ("BaseStructure", "Profile", "Hashtag", "Explore", "Post", "Story", "Highlight")
logger = logging.getLogger("instascrape")


def shortcode_extractor(data: dict, only: str = None, timestamp_limit: dict = None):
    """Called by `self._scrape_pages()` to extract shortcode from node data depending on the typename.

    Returns:
        str: if data satisfies the conditions, extracted data will be returned.
        None: if data does not satisfy the conditions
        False: if need to stop the process
    """
    shortcode = data["shortcode"]
    if not only and not timestamp_limit:  # no filter conditions
        return shortcode

    # filter option `only`
    if only:
        typename = data.get("__typename")
        types = {
            "image": "GraphImage",
            "video": "GraphVideo",
            "sidecar": "GraphSidecar"
        }
        if typename != types.get(only):
            return None

    if timestamp_limit:
        before = timestamp_limit.get("before")
        after = timestamp_limit.get("after")
        if all((before, after)) and after >= before:
            raise ValueError("timestamp limit conflict: `after` is greater than or equal to `before`")

        timestamp = data["taken_at_timestamp"]
        if after and timestamp < after:
            # already at the lowest limit, break the loop
            return False

        if before and timestamp > before:
            return None
        if after and timestamp < after:
            return None

    return shortcode


class BaseStructure:
    """Base Structure Class, providng some basic methods."""

    info_vars = ()

    def __init__(self, session: requests.Session):
        self.__slots__ = self.info_vars  # optimize speed of getting attributes ?
        self._session = session
        self.data = None

    def _get_json(self, url: str) -> dict:
        # logger.debug("Getting json data with url {0}".format(url))
        try:
            resp = self._session.get(url).json()
        except requests.ConnectionError:
            raise ConnectionError(url)
        except json.JSONDecodeError:
            # failed to decode json in first try
            # raise ExtractError for subclasses to handle
            raise ExtractError("response is not json")
        return resp

    def _query_next_page(self, url: str, param: dict) -> dict:
        """Query data of next page using `param` provided.
        * Called by `self._scrape_pages()` to paginate.

        Arguments:
            url: unformatted url
            param: JSON, will be added to url

        Returns:
            dict: node data extracted from response data
        """
        url = url + json.dumps(param)
        initial_data = self._get_json(url)
        logger.debug("getting next page (param: {0})".format(param))
        data = initial_data.get("data") or initial_data.get("graphql") or initial_data

        clstypes = {
            "Profile": "user",
            "Post":    "shortcode_media",
            "Hashtag": "hashtag",
            "Explore": "user"
        }

        k = clstypes.get(self.__class__.__name__)
        if not k:
            raise ValueError("Unknown class type: {}.".format(self.__class__.__name__))

        if k not in data:
            # key not found
            message = data.get("message", "key error")
            logger.debug(json.dumps(data))
            if message == "rate limited":
                raise RateLimitedError()
            raise ExtractError(message)

        d = data[k]
        if not d:  # empty dict
            raise ExtractError("no data")
        return d

    def _scrape_pages(self, extractor, url: str, param: dict, key: str, count: int = 50, new: bool = False, **kwargs):
        """Main method to scrape data by paginating.
        * Calls `self._query_next_page()` to paginate.
        * Calls 'extractor' functions to extract results from data.

        Arguments:
            extractor: behaviour function to extract data from node data
            url: one of the URLs in constants.py
            param: `variables`, added to URL
            key: key to extract node data from response
            count: the maximum count of posts you want to fetch (default: 50 because this is the maximum amount per page)
            new: do not use (or no) initial data and start scraping data of page-1 instead

        Keyword Arguments (**kwargs):
            - All Keyword Arguments will be passed to `extractor` function
            only: (exclusively for `shortcode_extractor`) [image/video/sidecar] filter out other types of posts, only get posts of this particular type

        Returns:
            list: contains results of extracted data
        """
        only = kwargs.get("only")
        if only:
            assert only in ("image", "video", "sidecar"), "Invalid 'only' argument: '{0}'. Should be one of 'image', 'video', 'sidecar'.".format(only)

        if not param.get("first"):
            # amount not provided, set to 50
            # * maximum amount is 50 (per page by Instagram)
            param["first"] = 50 if count >= 50 or only else count

        if new:
            data = self._query_next_page(url, param)  # scrape on page-1 (skip page-0)
            if key in data and data[key].get("count") == 0:
                logger.info("Total: 0 Items")
                yield False
            data = data[key]
        else:
            data = self.data[key]  # extract `key` from initial data

        total = data.get("count")
        if total:
            logger.info("Total: {0} Items".format(total))
        else:
            total = 100000  # if unlimited count of posts found, set max limit to 100 thousands
        logger.debug("Count: {0} Items".format(count))
        if total < count:
            logger.warning("Only {0} items can be fetched.".format(total))

        yield (False) if not data["edges"] else (count if total > count else total)

        page_i = 1 if new else 0
        results = []
        while len(results) < count and len(results) < total and data["edges"]:
            logger.debug("Scraping page-{}...".format(page_i))

            # yield extracted items
            for edge in data["edges"]:
                item = extractor(edge["node"], **kwargs)
                if item is False:
                    logger.debug("broke loop because extractor returned a False")
                    if len(results) < total:
                        logger.warning("Only {0} items found.".format(len(results)))
                    return
                if item:
                    results.append(item)
                    yield item
                # stop ?
                if len(results) >= count:
                    return

            # query next page if not enough
            if data["page_info"]["has_next_page"] and len(results) < count and len(results) < total:
                # update url parameter
                param["first"] = 50  # fixed limit
                param["after"] = data["page_info"]["end_cursor"]
                data = self._query_next_page(url, param)[key]
            else:
                break
            page_i += 1
            time.sleep(random.randrange(3))  # delay: prevent getting rate limited by Instagram

        if len(results) < total:
            logger.warning("Only {0} items found.".format(len(results)))

    def as_dict(self) -> dict:
        """Maps properties to a dictionary"""
        if not self.info_vars:
            raise AttributeError("This class has no attribute: `as_dict`, because of empty `info_vars`.")
        dictionary = {}
        for key in self.__dir__():
            if key in self.info_vars:
                dictionary[key] = getattr(self, key)
        return dictionary


# ==================
#  Pages Structures
# ==================
# That means the structures will fetch media page by page and return a list of post shortcodes.


class Profile(BaseStructure):
    """Interface of a user Profile. Providing information and methods to get data and media of a Profile.

    Methods:
        * as_dict()
        - fetch_timeline_posts()
        - fetch_saved_posts()
        - fetch_tagged_posts()
        - fetch_followers()
        - fetch_followings()
    """

    info_vars = ("url", "user_id", "username", "fullname", "biography", "website", "followers_count", "followings_count", "mutual_followers_count",
                 "is_verified", "is_private", "profile_pic", "story_highlights_count", "timeline_posts_count")

    def __init__(self, session: requests.Session, name: str):
        BaseStructure.__init__(self, session)
        self.name = name
        self._get_user_data()

    def __repr__(self):
        return "<Profile username='{0}' user_id={1}>".format(self.username, self.user_id)

    def _get_user_data(self):
        logger.debug("Getting initial data of Profile(name={0})...".format(self.name))
        try:
            resp = self._get_json(USER_URL.format(username=self.name))
        except ExtractError:
            raise UserNotFound(self.name)
        self.data = resp["graphql"]["user"]

    @property
    def url(self) -> str:
        return "https://instagram.com/" + self.data["username"]

    @property
    def user_id(self) -> str:
        """A unique set of long numbers as an identity for Instagram."""
        return self.data["id"]

    @property
    def username(self) -> str:
        """Lower-cased and no-spaced username of a user."""
        return self.data["username"]

    @property
    def fullname(self) -> str:
        """Full name of a user."""
        return self.data["full_name"]

    @property
    def biography(self) -> str:
        """Brief summary about this user."""
        return self.data["biography"]

    @property
    def website(self) -> str or None:
        """External URL of this user. Can be empty (None)."""
        return self.data["external_url"]

    @property
    def followers_count(self) -> int:
        """Amount of followers this user has."""
        return self.data["edge_followed_by"]["count"]

    @property
    def followings_count(self) -> int:
        """Amount of followees this user has."""
        return self.data["edge_follow"]["count"]

    @property
    def mutual_followers_count(self) -> int:
        """Amount of followers this user has who are also following you."""
        return self.data["edge_mutual_followed_by"]["count"]

    @property
    def is_verified(self) -> bool:
        """Whether this user is verified by Instagram."""
        return self.data["is_verified"]

    @property
    def is_private(self) -> bool:
        """Whether this user is private."""
        return self.data["is_private"]

    @property
    def profile_pic(self) -> str:
        """URL to the source of this user's profile picture."""
        return self.data["profile_pic_url_hd"]

    @property
    def story_highlights_count(self) -> int:
        """Amount of story highlights this user has."""
        return self.data["highlight_reel_count"]

    @property
    def timeline_posts_count(self) -> int:
        """Amount of timeline posts this user has."""
        return self.data["edge_owner_to_timeline_media"]["count"]

    # @property
    # def saved_posts_count(self) -> int:
    #     pass
    # TODO
    # @property
    # def tagged_posts_count(self) -> int:
    #     pass

    def fetch_timeline_posts(self, count: int = 50, only: str = None, timestamp_limit: dict = None):
        """Fetches a user's timeline posts. Call the low-level method `self.fetch_posts`.

        Arguments:
            count: the maximum count of posts you want to fetch
            only: [image/video] filter out other types of posts, only get posts of this particular type
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
        """
        param = {"id": self.user_id}
        return self._scrape_pages(shortcode_extractor, QUERY_USER_MEDIA_URL, param, "edge_owner_to_timeline_media", count, only=only, timestamp_limit=timestamp_limit)

    def fetch_saved_posts(self, count: int = 50, only: str = None, timestamp_limit: dict = None):
        """Fetches self saved posts. Calls the low-level method `self.fetch_posts`.
        * This method only works for self.

        Arguments:
            count: the maximum count of posts you want to fetch
            only: [image/video] filter out other types of posts, only get posts of this particular type
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
        """
        param = {"id": self.user_id}
        return self._scrape_pages(shortcode_extractor, QUERY_USER_SAVED_URL, param, "edge_saved_media", count, only=only, timestamp_limit=timestamp_limit)

    def fetch_tagged_posts(self, count: int = 50, only: str = None, timestamp_limit: dict = None):
        """Fetches posts that tagged this user. Calls the low-level method `self.fetch_posts`.

        Arguments:
            count: the maximum count of posts you want to fetch
            only: [image/video] filter out other types of posts, only get posts of this particular type
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
        """
        param = {"id": self.user_id}
        return self._scrape_pages(shortcode_extractor, QUERY_USER_TAGGED_URL, param, "edge_user_to_photos_of_you", count, new=True, only=only, timestamp_limit=timestamp_limit)

    def fetch_followers(self, count: int = 50):
        """Fetches this user's followers in usernames.

        Arguments:
            count: the maximum count of followers you want to fetch
        """
        param = {"id": self.user_id}
        return self._scrape_pages(lambda node: node["username"], QUERY_FOLLOWERS_URL, param, "edge_followed_by", count, new=True)

    def fetch_followings(self, count: int = 50):
        """Fetches this user's followings in usernames.

        Arguments:
            count: the maximum count of followings you want to fetch
        """
        param = {"id": self.user_id}
        return self._scrape_pages(lambda node: node["username"], QUERY_FOLLOWINGS_URL, param, "edge_follow", count, new=True)

    def fetch_highlights(self) -> list:
        """Fetches this user's all story highlights in titles & highlight reel ids.

        Returns:
            list: [(title, id)]
        """
        param = {"user_id": self.user_id, "include_chaining": False, "include_reel": False,
                 "include_suggested_users": False, "include_logged_out_extras": False, "include_highlight_reels": True}
        data = self._get_json(QUERY_HIGHLIGHTS_URL + json.dumps(param))
        if "data" not in data or "user" not in data["data"]:
            message = data.get("message", "key error")
            logger.debug(json.dumps(data))
            if message == "rate limited":
                raise RateLimitedError()
            raise ExtractError(message)

        data = data["data"]["user"]["edge_highlight_reels"]["edges"]
        results = []
        for item in data:
            title = item["node"]["title"]
            id = item["node"]["id"]
            results.append((title, id))
        return results


class Hashtag(BaseStructure):
    """Provide a method to fetch posts of the given hashtag.

    Methods:
        - fetch_posts()
    """

    info_vars = ()

    def __init__(self, session: requests.Session, tag: str):
        BaseStructure.__init__(self, session)
        self.tag = tag

    def __repr__(self):
        return "<Hashtag tag='{0}'>".format(self.tag)

    def fetch_posts(self, count: int = 50, only: str = None, timestamp_limit: dict = None):
        """Fetches posts that tagged the given hashtag name.

        Arguments:
            count: the maximum count of posts you want to fetch
            only: [image/video] filter out other types of posts, only get posts of this particular type
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
        """
        param = {"tag_name": self.tag}
        return self._scrape_pages(shortcode_extractor, QUERY_HASHTAG_URL, param, "edge_hashtag_to_media", count, new=True, only=only, timestamp_limit=timestamp_limit)


class Explore(BaseStructure):
    """Provide a method to fetch posts in 'discover' feed section.

    Methods:
        - fetch_posts()
    """

    info_vars = ()

    def __init__(self, session: requests.Session):
        BaseStructure.__init__(self, session)

    def __repr__(self):
        return "<Explore>"

    def fetch_posts(self, count: int = 50, only: str = None, timestamp_limit: dict = None):
        """Fetches posts in explore feed.

        Arguments:
            count: the maximum count of posts you want to fetch
            only: [image/video] filter out other types of posts, only get posts of this particular type
            timestamp_limit: only get posts created between these timestamps, {"before": <before timestamp>, "after", <after_timestamp>}
        """
        param = {"first": count if count <= 50 else 50}
        return self._scrape_pages(shortcode_extractor, QUERY_DISCOVER_URL, param, "edge_web_discover_media", count, new=True, only=only, timestamp_limit=timestamp_limit)


# ========================
#  Individuals Structures
# ========================
# That means the sturctures will return the contained media as the form of list of `Container` objects in `self.obtain_media` method.


class Post(BaseStructure):
    """Interface of a Post. Providing information and methods to get a Post's data and media.

    Methods:
        * as_dict()
        * obtain_media()
        - fetch_comments()
        - fetch_likes()
    """

    info_vars = ("typename", "url", "shortcode", "post_id", "location_name", "location_id", "owner_username",
                 "owner_user_id", "created_time", "caption", "media_count", "likes_count", "comments_count")

    def __init__(self, session: requests.Session, shortcode: str):
        BaseStructure.__init__(self, session)
        self._shortcode = shortcode
        self._get_post_data()

    def __repr__(self):
        return "<Post shortcode={0} post_id={1} media_count={2}>".format(self.shortcode, self.post_id, self.media_count)

    def __len__(self):
        return self.media_count

    def _get_post_data(self):
        logger.debug("Getting initial data of Post(shortcode={0})...".format(self._shortcode))
        try:
            resp = self._get_json(POST_URL.format(shortcode=self._shortcode))
        except ExtractError:
            raise PostNotFound(self._shortcode)
        self.data = resp["graphql"]["shortcode_media"]

    @property
    def typename(self) -> str:
        """One of 'GraphImage', 'GraphVideo', 'GraphSidecar'."""
        return self.data["__typename"]

    @property
    def url(self) -> str:
        """URL of the post i.e. 'https://instagram.com/p/<shortcode>'."""
        return "https://instagram.com/p/" + self.shortcode

    @property
    def shortcode(self) -> str:
        """A unique set of characters as an identity for Instagram."""
        return self.data["shortcode"]

    @property
    def post_id(self) -> str:
        """A unique set of long numbers as an identity for Instagram."""
        return self.data["id"]

    @property
    def location_name(self) -> str or None:
        """Name of the location tag as an identity for Instagram. Can be empty (None)."""
        location = self.data.get("location")
        if location:
            return location["name"]

    @property
    def location_id(self) -> str or None:
        """Unique ID of the location tag as an identity for Instagram. Can be empty (None)."""
        location = self.data.get("location")
        if location:
            return location["id"]

    @property
    def owner_username(self) -> str:
        """Username of the post owner."""
        return self.data["owner"]["username"]

    @property
    def owner_user_id(self) -> str:
        """User ID of the post owner."""
        return self.data["owner"]["id"]

    @property
    def created_time(self) -> float:
        """Timestamp of the time the post was created."""
        return float(self.data["taken_at_timestamp"])

    @property
    def caption(self) -> str:
        """Caption text of the post."""
        edges = self.data["edge_media_to_caption"]["edges"]
        if not edges:
            return ""
        cap = ""
        for edge in edges:
            cap += edge["node"]["text"]
        return cap

    @property
    def media_count(self) -> int:
        """Amount of media in the post."""
        return len(self.obtain_media())

    @property
    def likes_count(self) -> int:
        """Amount of likes of the post."""
        return self.data["edge_media_preview_like"]["count"]

    @property
    def comments_count(self) -> int:
        """Amount of comments of the post."""
        return self.data["edge_media_to_comment"]["count"]

    def obtain_media(self) -> list:
        """Obtain media of the post in the form of `Container` objects.

        Returns:
            list: `Container` objects (see: container.py)
        """
        return container(self.typename, self.data)

    def fetch_likes(self, count: int = 50):
        """Fetch likes of this post in the form of usernames of users who liked the post.

        Arguments:
            count: maxiumum count of likes you want to fetch

        Returns:
            list: usernames of users who liked this post
        """
        param = {"shortcode": self.shortcode, "include_reel": False}
        return self._scrape_pages(lambda x: x["username"], QUERY_LIKES_URL, param, "edge_liked_by", count, new=True)

    def fetch_comments(self, count: int = 50):
        """Fetch comments of this post in the form of {username: <username>, text: <comment text>, time: <timestamp>}.

        Arguments:
            count: maximum count of comments you want to fetch

        Returns:
            list: dictionaries of comments
        """
        param = {"shortcode": self.shortcode}
        return self._scrape_pages(lambda x: {"username": x["owner"]["username"], "text": x["text"], "time": x["created_at"]},
                                  QUERY_COMMENTS_URl, param, "edge_media_to_comment", count, new=True)


class Story(BaseStructure):
    """Interface of a Story. Providing information of a Story and a method to get the media.

    Methods:
        * obtain_media()
    """

    info_vars = ()

    def __init__(self, session: requests.Session, user_id: str = None, tag: str = None, reel_id: str = None):
        BaseStructure.__init__(self, session)
        if all((user_id, tag, reel_id)) or not any((user_id, tag, reel_id)) or (bool(user_id), bool(tag), bool(reel_id)).count(True) == 2:
            raise ValueError("Invalid arguments: only one of 'user_id', 'tag', 'reel_id' should be specified.")
        self.owner_user_id = user_id
        self.tag = tag
        self.reel_id = reel_id
        self._get_story_data()

    def __repr__(self):
        return "<Story owner_name='{0}'>".format(self.owner_name)

    def __len__(self):
        return len(self.obtain_media())

    def _get_story_data(self):
        logger.debug("Getting initial data of Story({0})...".format(("user_id=" + self.owner_user_id if self.owner_user_id else "tag=" + self.tag) if self.owner_user_id or self.tag else ("reel_id=" + self.reel_id)))
        param = {"reel_ids": [self.owner_user_id] if self.owner_user_id else [],
                 "tag_names": [self.tag] if self.tag else [], "location_ids": [],
                 "highlight_reel_ids": [self.reel_id] if self.reel_id else [], "precomposed_overlay": False}
        data = self._get_json(QUERY_STORIES_URL + json.dumps(param))

        if "data" not in data or "reels_media" not in data["data"]:
            message = data.get("message", "key error")
            logger.debug(json.dumps(data))
            if message == "rate limited":
                raise RateLimitedError()
            raise ExtractError(message)

        data = data["data"]["reels_media"]
        if not data:
            raise StoryNotFound(self.owner_user_id or self.tag or self.reel_id)
        self.data = data[0]

    @property
    def typename(self) -> str:
        """One of 'GraphStoryImage', 'GraphStoryVideo'."""
        return self.data["__typename"]

    @property
    def owner_name(self) -> str:
        """Name (username or hashtag name) of the story."""
        return self.data["owner"].get("username") or self.data["owner"]["name"]

    @property
    def id(self) -> str:
        """ID (user or hashtag) of the story."""
        return self.data["id"]

    @property
    def created_time_list(self) -> list:
        """The created times of each story media."""
        return [float(item["taken_at_timestamp"]) for item in self.data["items"]]

    def obtain_media(self) -> list:
        """Obtain media of the story in the form of `Container` objects.

        Returns:
            a list of Container objects: (see: container.py)
        """
        return container(self.typename, self.data)


class Highlight(Story):
    """Interface of a story Highlight. Providing information of a story Highlight and a method to get the media.

    Methods:
        * obtain_media()
    """

    info_vars = ()

    def __init__(self, session: requests.Session, title: str, reel_id: str):
        Story.__init__(self, session, reel_id=reel_id)
        self._title = title

    def __repr__(self):
        return "<Highlight title='{0}' reel_id={1}>".format(self.title, self.reel_id)

    @property
    def title(self) -> str:
        """Title of this story highlight."""
        return self._title

    @property
    def created_time_list(self) -> list:
        """`Highlight` does not implement this property."""
        return []
