import logging
import os
import sys
import json
from contextlib import contextmanager

import requests
from colorama import Fore, Back, Style
from tqdm import tqdm

from instascrape.utils import to_datetime
from instascrape.constants import UA
from instascrape.exceptions import InstaScrapeError

logger = logging.getLogger("instascrape")


@contextmanager
def progress(total: int = None, desc: str = None, ascii: bool = True):
    hide = logger.handlers[1].level < 20 or logger.handlers[1].level >= 40
    if hide:
        class Dummy:
            def dummy(self, *args, **kwargs):
                pass
            def __getattr__(self, item):
                return self.dummy
        bar = Dummy()
    else:
        bar = tqdm(total=total, file=sys.stdout, unit="item", ascii=ascii, dynamic_ncols=True,
                   desc=("\033[7m" + "[" + desc.center(11) + "]" + Style.RESET_ALL) if desc else (Back.LIGHTCYAN_EX + "[" + "Downloading".center(11) + "]" + Style.RESET_ALL),
                   bar_format="{desc} {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} " + Fore.LIGHTBLACK_EX + "[{elapsed}<{remaining}{postfix}]" + Fore.RESET)

    try:
        yield bar
    except (Exception, KeyboardInterrupt):
        bar.set_description_str(Back.LIGHTRED_EX + "[" + "Failed".center(11) + "]" + Back.RESET)
        raise
    else:
        bar.set_description_str(Back.GREEN + "[" + "Completed".center(11) + "]" + Back.RESET)
    finally:
        bar.close()


def _down_from_src(src: str, filename: str, path: str = None) -> str or None:
    """Low-level function to download media from a URL (`src`).
    * Called in `download_user_profile_pic`.
    * Only downloads mp4 and jpeg.

    Arguments:
        src: source of media (URL)
        filename: filename of the file
        path: full path to the download destination

    Returns:
        path: full path to the download destination
    """
    path = path or "./"
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        os.mkdir(path)

    f = None
    try:
        r = requests.get(src, stream=True, headers={"user-agent": UA})
        r.raise_for_status()

        # Get info of the file
        mime = r.headers["Content-Type"]
        size = r.headers["Content-Length"]
        size_in_kb = int(int(size) / 1000)
        if mime == "video/mp4":
            ext = ".mp4"
        elif mime == "image/jpeg":
            ext = ".jpg"
        else:
            raise InstaScrapeError("Invalid MIME type: {0}.".format(mime))

        finish_filename = filename + ext
        part_filename = filename + ext + ".part"

        # Download
        logger.debug("=> [{0}] {1} ({2} kB)".format(finish_filename, mime, size_in_kb))
        f = open(os.path.join(path, part_filename), "wb+")
        for chunk in r.iter_content(1024):
            if chunk:

                f.write(chunk)
    except Exception as e:
        logger.error("Download Error (src: '{0}'): ".format(src) + str(e))
        return None

    finally:
        if f:
            f.close()

    # rename .part file to its real extension
    os.rename(os.path.join(path, part_filename), os.path.join(path, finish_filename))
    return path


def _down_containers(structure, dest: str = None, directory: str = None, subdir: str = None, force_subdir: bool = False) -> str:
    """Download media of containers of a single structure to `dest`. May deecorate the proccess with progress bar.
    - If there is multiple media in the structure, a sub directory will be created to store the media.
    * This function calls `down_from_src` function and wraps it with some interactions with Post object to support downloading post.
    * Containers are obtained by calling `structure.obtain_media()`.
    * Called in `download_story` and `download_post` individualy.
    * If a file with the same path and filename found, it will skip the download process.

    [dest]
        [directory]
            [sub directory] (multi or dump_metadata=True)
            [file]
            ...

    Arguments:
        structure: a structure object that has attrubute `obtain_media()` (`Post` or `Story`)
        dest: destination path, one will be created if directory not found (must be a directory)
        directory: make a new directory inside `dest` to store all files
        subdir: name of the sub directory which is created when downloading multiple media
        force_subdir: force create a sub directory and store all the media (used when dump_metadata=True)

    Returns:
        str: full path to the download destination
    """
    dest = dest or "./"
    path = os.path.abspath(dest)
    if not os.path.isdir(path):
        logger.debug("{0} directory not found. Creating one...".format(path))
        os.mkdir(path)
    if directory:
        path = os.path.join(path, directory)
        if not os.path.isdir(path):
            os.mkdir(path)
    return_path = path

    containers = structure.obtain_media()
    multi = len(containers) > 1
    if multi or force_subdir:
        if subdir:
            # create a sub directory for multiple media of a post
            path = os.path.join(path, subdir)
            if not os.path.isdir(path):
                os.mkdir(path)

    logger.debug("Downloading {0} ({1} media) [{2}]...".format(subdir or directory, len(containers), structure.typename))
    logger.debug("Path: " + path)
    with progress(len(containers)) as bar:
        for i, c in enumerate(containers, start=1):
            bar.set_postfix_str(c.typename)
            if multi:
                filename = str(i)
            else:
                filename = subdir or str(i)

            if structure.__class__.__name__ == "Story":
                # * exclusively and explictly change filename to datetime string for Story
                filename = to_datetime(structure.created_time_list[i-1])

            # check if the file / directory already exists
            if os.path.isfile(os.path.join(path, filename + ".jpg")) or os.path.isfile(os.path.join(path, filename + ".mp4")):
                logger.debug("[{0}] file already exists, skipped !".format(os.path.join(path, filename)))
            else:
                # download
                _down_from_src(c.src, filename, path)
            bar.update(1)
    return return_path


def _down_posts(posts, dest: str = None, directory: str = None, dump_metadata: bool = False):
    """High-level function for downloading media of a list of posts. Decorates the process with tqdm progress bar.
    * This function calls `down_containers` function and wraps it with 'for' loop & progress bar to support downloading multiple posts.

    Arguments:
        posts: a generator which generates `Post` instances or a list that contains preloaded `Post` instances
        dest: download destination (should be a directory)
        directory: make a new directory inside `dest` to store all the files
        dump_metadata: force create a sub directory of the post and dump metadata of each post to a file inside if True

    Returns:
        bool: True if file already exists and skipped the download process
        path: full path to the download destination if download succeeded
    """
    is_preloaded = isinstance(posts, list)
    path = None
    total = len(posts) if is_preloaded else None
    logger.info("Downloading {0} posts {1}...".format(total or "(?)", "with " + str(sum([len(x) for x in posts])) + " media in total" if is_preloaded else ""))
    # prepare progress bar, hide progress bar when quiet and show download details when debugging
    with progress(total=total, desc="Processing", ascii=False) as bar:
        for i, p in enumerate(posts, start=1):
            bar.set_postfix_str("(" + (p.shortcode if len(p.shortcode) <= 11 else p.shortcode[:8] + "...") + ") " + p.typename)
            logger.debug("Downloading {0} of {1} posts...".format(i, total or "(?)"))
            # download
            subdir = to_datetime(p.created_time) + "_" + p.shortcode
            path = _down_containers(p, dest, directory, subdir, force_subdir=dump_metadata)  # `subdir` can also be the filename if the post has only one media
            # dump metadata
            if dump_metadata:
                filename = subdir + ".json"
                metadata_file = os.path.join(path, subdir, filename)  # path inside the sub directory
                logger.debug("-> [{0}] dump metadata".format(filename))
                with open(metadata_file, "w+") as f:
                    json.dump(p.as_dict(), f, indent=4)
            bar.update(1)
    if path:  # path is None if error occurred in `_down_containers()`
        logger.info("Destination: {0}".format(path))
    return path


def download_post(insta, shortcode: str, dest: str = None, dump_metadata: bool = False) -> str:
    p = insta.get_post(shortcode)
    logger.info("Downloading {0} with {1} media...".format(shortcode, len(p)))
    # subdir = to_datetime(p.created_time) + "_" + p.shortcode
    path = _down_containers(p, dest, subdir=p.shortcode, force_subdir=dump_metadata)
    if dump_metadata:
        filename = p.shortcode + ".json"
        metadata_file = os.path.join(path, p.shortcode, filename)
        logger.debug("-> [{0}] dump metadata".format(filename))
        with open(metadata_file, "w+") as f:
            json.dump(p.as_dict(), f, indent=4)
    if path:
        logger.info("Destination: {0}".format(path))
    return path


def download_story(insta, name: str = None, tag: str = None, dest: str = None) -> str:
    story = insta.get_story(name=name, tag=tag)
    logger.info("Downloading stories of {0} with {1} media...".format(name or "#" + tag, len(story)))
    path = _down_containers(story, dest, directory=("@" if name else "#") + story.name + "(story)")
    if path:
        logger.info("Destination: {0}".format(path))
    return path


def download_user_profile_pic(insta, name: str, dest: str = None) -> str:
    user = insta.get_profile(name)
    logger.info("Downloading {0}'s profile picture...".format(name))
    path = _down_from_src(user.profile_pic, name, dest)
    if path:
        logger.info("Destination: {0}".format(path))
    return path


def download_user_timeline_posts(insta, name: str, count: int = 50, only: str = None, dest: str = None, preload: bool = False, dump_metadata: bool = False) -> str or None:
    """Download a user's timeline posts.

    Arguments:
        insta (InstaScraper): the requests session of `InstaScraper` object is used for downloading
        name: the user's username
        count: maximum limit of posts you want to download
        only: only this type of posts will be downloaded [image, video, sidecar]
        dest: path to the destination of the download files
        preload: convert all items in the iterable to `Post` instances before downloading if True
        dump_metadata: force create a sub directory of the post and dump metadata of each post to a file inside if True

    Returns:
        path: full path to the download destination, or None if download failed
    """
    posts = insta.get_user_timeline_posts(name, count, only, preload)
    if not posts:
        return None
    return _down_posts(posts, dest, directory="@" + name, dump_metadata=dump_metadata)


def download_self_saved_posts(insta, count: int = 50, only: str = None, dest: str = None, preload: bool = False, dump_metadata: bool = False) -> str or None:
    """Download self saved posts.

    Arguments:
        insta (InstaScraper): the requests session of `InstaScraper` object is used for downloading
        count: maximum limit of posts you want to download
        only: only this type of posts will be downloaded [image, video, sidecar]
        dest: path to the destination of the download files
        preload: convert all items in the iterable to `Post` instances before downloading if True
        dump_metadata: force create a sub directory of the post and dump metadata of each post to a file inside if True

    Returns:
        path: full path to the download destination, or None if download failed
    """
    posts = insta.get_self_saved_posts(count, only, preload)
    if not posts:
        return None
    return _down_posts(posts, dest, directory="saved", dump_metadata=dump_metadata)


def download_user_tagged_posts(insta, name: str, count: int = 50, only: str = None, dest: str = None, preload: bool = False, dump_metadata: bool = False) -> str or None:
    """Download posts that tagged the user.

    Arguments:
        insta (InstaScraper): the requests session of `InstaScraper` object is used for downloading
        name: the user's username
        count: maximum limit of posts you want to download
        only: only this type of posts will be downloaded [image, video, sidecar]
        dest: path to the destination of the download files
        preload: convert all items in the iterable to `Post` instances before downloading if True
        dump_metadata: force create a sub directory of the post and dump metadata of each post to a file inside if True

    Returns:
        path: full path to the download destination, or None if download failed
    """
    posts = insta.get_user_tagged_posts(name, count, only, preload)
    if not posts:
        return None
    return _down_posts(posts, dest, directory="@" + name + "(tagged)", dump_metadata=dump_metadata)


def download_hashtag_posts(insta, tag: str, count: int = 50, only: str = None, dest: str = None, preload: bool = False, dump_metadata: bool = False) -> str or None:
    """Download posts with the given tag.

    Arguments:
        insta (InstaScraper): the requests session of `InstaScraper` object is used for downloading
        tag: tag name
        count: maximum limit of posts you want to download
        only: only this type of posts will be downloaded [image, video, sidecar]
        dest: path to the destination of the download files
        preload: convert all items in the iterable to `Post` instances before downloading if True
        dump_metadata: force create a sub directory of the post and dump metadata of each post to a file inside if True

    Returns:
        path: full path to the download destination, or None if download failed
    """
    posts = insta.get_hashtag_posts(tag, count, only, preload)
    if not posts:
        return
    return _down_posts(posts, dest, directory="#" + tag, dump_metadata=dump_metadata)


def download_explore_posts(insta, count: int = 50, only: str = None, dest: str = None, preload: bool = False, dump_metadata: bool = False) -> str or None:
    """Download 'explore' posts feed in the 'discover' section.
    * Download to a directory named

    Arguments:
        insta (InstaScraper): the requests session of `InstaScraper` object is used for downloading
        count: maximum limit of posts you want to download
        only: only this type of posts will be downloaded [image, video, sidecar]
        dest: path to the destination of the download files
        preload: convert all items in the iterable to `Post` instances before downloading if True
        dump_metadata: force create a sub directory of the post and dump metadata of each post to a file inside if True

    Returns:
        path: full path to the download destination, or None if download failed
    """
    posts = insta.get_explore_posts(count, only, preload)
    if not posts:
        return None
    return _down_posts(posts, dest, directory="explore", dump_metadata=dump_metadata)
