class InstaScrapeError(Exception):
    """Base Exception Class"""


class ExtractError(InstaScrapeError):
    """Raised when failed to extract data from JSON response."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "Failed to extract data from response. (message: {0})".format(self.message)


class RateLimitedError(InstaScrapeError):
    """Raised when got rate limited by Instagram. Can be determined by checking the response message."""

    def __str__(self):
        return "Failed to fetch data. Rate limited by Instagram."


class ConnectionError(InstaScrapeError):
    """Raised when failed to connect to instagram.com. Directly caused by requests.ConnectionError."""

    def __init__(self, url):
        self.url = url

    def __str__(self):
        return "Failed to connect to {0}.".format(self.url)


class LoginError(InstaScrapeError):
    """Raised when failed to login to Instagram."""

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "Failed to login to Instagram. {0}".format(self.message)


class DownloadError(InstaScrapeError):
    """Raised when error occurred while downloading."""


class NotFoundError(InstaScrapeError):
    """Base Exception Class. Rasied when failed to find `Post`, `User`, `Hashtag`, `Story`."""


class UserNotFound(NotFoundError):
    """Raised when failed to find matched user."""

    def __init__(self, username):
        self.username = username

    def __str__(self):
        return "User @{0} not found.".format(self.username)


class PostNotFound(NotFoundError):
    """Raised when failed to find matched post."""

    def __init__(self, shortcode):
        self.shortcode = shortcode

    def __str__(self):
        return "Post :{0} not found.".format(self.shortcode)


class StoryNotFound(NotFoundError):
    """Raised when failed to find story for the user / hashtag."""

    def __init__(self, arg):
        self.arg = arg

    def __str__(self):
        return "No story found for '{0}'.".format(self.arg)
