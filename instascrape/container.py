"""
=================
    Typenames
=================
[User]
* GraphUser
[Hashtag]
* GraphHashtag
[Post]
* GraphSidecar -> combination of videos or/and images
  - GraphImage
  - GraphVideo
[Story]
* GraphReel -> user story
* GraphHighlightReel -> user's story highlights
* GraphMASReel -> hashtag story
  - GraphStoryImage
  - GraphStoryVideo
"""
from instascrape.utils import get_biggest_media


class Container:
    """'Adapter' to hold properties of Image / Video (of Stories and Posts)

    Arguments:
        data: dictionary containing information of the object returned by Instagram

    Fields:
        typename: (see docstring)
        thumbnail: url to the thumbnail
        size: x y dimensions of the media
        video_duration: only for 'GraphStoryVideo' and 'GraphVideo', returns None otherwise
        src: biggest in size source url
    """
    def __init__(self, data: dict):
        self.data = data

    def __repr__(self):
        return "<Container({0})>".format(self.typename)

    @property
    def typename(self) -> str:
        """One of [GraphImage, GraphVideo, GraphStoryImage, GraphStoryVideo]."""
        return self.data["__typename"]

    @property
    def thumbnail(self) -> str:
        return self.data.get("thumbnail_src") or self.data.get("display_url", "")

    @property
    def size(self) -> dict:
        """Width and height of Instagram displayed media."""
        return self.data["dimensions"]

    @property
    def video_duration(self) -> float or None:
        """Only for GraphStoryVideo or GraphVideo"""
        return self.data.get("video_duration")

    @property
    def src(self) -> str:
        """List of dictionaries to the source and dimensions info of media.

        Returns:
            src: source url of the media
        """
        assert self.typename in ("GraphImage", "GraphStoryImage", "GraphVideo", "GraphStoryVideo"), "Invalid typename {0}".format(self.typename)

        if self.typename in ("GraphImage", "GraphStoryImage"):
            return get_biggest_media(self.data["display_resources"])["src"]

        elif self.typename in ("GraphVideo", "GraphStoryVideo"):
            media = self.data.get("video_resources", [])
            if not media:
                # just url
                return self.data["video_url"]  # undefined config width & height
            return get_biggest_media(media)["src"]


def container(typename: str, data: dict) -> list:
    """"Factory function for generating Container objects according to the typename."""

    if typename in ("GraphImage", "GraphStoryImage", "GraphVideo", "GraphStoryVideo"):
        return [Container(data)]

    results = []
    if typename in ("GraphReel", "GraphMASReel", "GraphHighlightReel"):
        data = data["items"]
    if typename == "GraphSidecar":
        data = data["edge_sidecar_to_children"]["edges"]

    # convert mutliple items into their types respectively
    for node in data:
        if typename == "GraphSidecar":
            node = node["node"]
        results.append(Container(node))
    return results
